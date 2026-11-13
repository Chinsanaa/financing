"""Dashboard route group: overview."""
import asyncio
from fastapi import HTTPException, Request
from typing import Optional
from config import supabase_client
from db import fetch_all_async, run_query
from errors import internal_error
from datetime import date, datetime, timedelta
import pandas as pd
from src.translate import merchant_label_stored
from translations import request_translation_if_missing, request_translation_periodic

from budget import (  # shared with alerts.py
    _month_bounds,
    _month_start,
    _now_cn,
)
from ._shared import router, _home_currency, _load_rates, _monthly_income, _months_ago_start, _r2, _reference_rate, _strict_sum

async def _daily_flows(user_id: str, start: Optional[datetime], end: Optional[datetime]) -> list:
    """Per-day sums by flow (migration 20261011000200, daily_flows_for_user):
    day, spend, categorized_spend, income, transfers_in, transfers_out,
    own_account_moved. A flow is None on a day with no rows of it. Paged —
    an all-time history can exceed PostgREST's 1,000-row cap."""
    params = {
        "p_user_id": user_id,
        "p_start": start.isoformat() if start else None,
        "p_end": end.isoformat() if end else None,
    }
    rows = await fetch_all_async(lambda: supabase_client.rpc("daily_flows_for_user", params))
    for row in rows:
        row["day"] = date.fromisoformat(str(row["day"])[:10])
        for key in ("spend", "categorized_spend", "income", "transfers_in", "transfers_out", "own_account_moved"):
            if row.get(key) is not None:
                row[key] = float(row[key])
    return rows


def _flow_total(rows: list, key: str) -> float:
    return sum(r[key] for r in rows if r.get(key) is not None)


def _summary_home(home, rates, all_flows, month_flows, month_start, month_income, month_income_source) -> dict:
    """The summary's `home` block (contract §3.3 / §2)."""
    today = _now_cn().date()
    rate_asof, rate = rates.latest(today)

    # All-time total is LENIENT: any stored rate at or before the day (no
    # age limit; the earliest stored rate for days before the cache), so a
    # long history still gets a total. `approx` flags any such fallback.
    # Null only when no rate at all is stored for the currency.
    total_spend_home, approx = None, False
    if rates.lenient(today)[0] is not None:
        total_spend_home = 0.0
        for row in all_flows:
            if row["spend"] is None:
                continue
            day_rate, approx_used = rates.lenient(row["day"])
            if day_rate is None:
                total_spend_home, approx = None, False
                break
            total_spend_home += row["spend"] * day_rate
            approx = approx or approx_used

    if month_income_source == "statements":
        month_income_home = _strict_sum(((r["day"], r["income"]) for r in month_flows), rates)
    elif month_income_source == "settings":
        ref_rate = _reference_rate(rates, month_start)
        month_income_home = month_income * ref_rate if ref_rate is not None else None
    else:
        month_income_home = None

    return {
        "currency": home,
        "total_spend_home": _r2(total_spend_home),
        "month_spend_home": _r2(_strict_sum(((r["day"], r["spend"]) for r in month_flows), rates)),
        "month_income_home": _r2(month_income_home),
        "rate_asof": rate_asof.isoformat() if rate_asof else None,
        "rate": rate,
        "approx": approx,
    }


@router.get("/summary")
async def get_summary(request: Request):
    """Overall summary: total transactions, labeled%, total spend."""
    user_id = request.state.user_id
    # Every Overview load hits this: keep the English-label backfill moving
    # even if Reports/Review are never opened (throttled, background-only).
    request_translation_periodic(user_id)

    try:
        month_start, month_end = _month_bounds(None)
        # Independent queries, run concurrently (one round-trip of latency
        # instead of seven). Counts use limit(1): count="exact" gives the
        # total in the header, so there's no need to ship up to 1,000 ids.
        total, expense_total, labeled, spend_resp, monthly_income, home, month_flows = await asyncio.gather(
            # Every kind: shown as "transactions imported".
            run_query(
                lambda: supabase_client.table("transactions")
                .select("id", count="exact").eq("user_id", user_id).limit(1).execute()
            ),
            # Labeling % is over expense rows only — income/transfer rows
            # are never categorized, so they'd drag the % down forever.
            run_query(
                lambda: supabase_client.table("transactions")
                .select("id", count="exact").eq("user_id", user_id).eq("kind", "expense").limit(1).execute()
            ),
            # Labeled = has a trusted category (not still pending review)
            run_query(
                lambda: supabase_client.table("transactions")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .eq("kind", "expense")
                .eq("needs_review", False)
                .not_.is_("category_id", "null")
                .limit(1)
                .execute()
            ),
            # Total spend (expense only), summed in Postgres (migrations
            # 20260811090000 / 20261011000200).
            run_query(lambda: supabase_client.rpc("sum_user_transactions", {"p_user_id": user_id}).execute()),
            _monthly_income(user_id),
            _home_currency(user_id),
            _daily_flows(user_id, month_start, month_end),
        )
        total_count = total.count if total.count is not None else len(total.data)
        expense_count = expense_total.count if expense_total.count is not None else len(expense_total.data)
        labeled_count = labeled.count if labeled.count is not None else len(labeled.data)
        total_spend = float(spend_resp.data or 0)

        month_spend = _flow_total(month_flows, "spend")
        # Income from statements wins; the Settings figure is the fallback
        # for users whose statements carry no income rows (all v1 users).
        statement_income = _flow_total(month_flows, "income")
        if statement_income != 0:
            month_income, month_income_source = statement_income, "statements"
        elif monthly_income > 0:
            month_income, month_income_source = monthly_income, "settings"
        else:
            month_income, month_income_source = None, None

        home_block = None
        if home:
            # total_spend_home converts every expense day, so this needs the
            # whole history (one row per active day, not per transaction).
            all_flows = await _daily_flows(user_id, None, None)
            rates = await _load_rates(home, [r["day"] for r in all_flows])
            home_block = _summary_home(
                home, rates, all_flows, month_flows, month_start, month_income, month_income_source
            )

        return {
            "total_transactions": total_count,
            "labeled_transactions": labeled_count,
            "labeling_percentage": round(100 * labeled_count / expense_count, 1) if expense_count > 0 else 0,
            "total_spend": total_spend,
            "monthly_income": monthly_income,
            "month": f"{month_start.year:04d}-{month_start.month:02d}",
            "month_spend": round(month_spend, 2),
            "month_income": _r2(month_income),
            "month_income_source": month_income_source,
            "home": home_block,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/summary")


@router.get("/by-category")
async def get_by_category(request: Request):
    """Spending breakdown by category (includes both transactions with
    category_id set directly and split transactions' transaction_splits
    line-items — see spend_by_category_for_user RPC in migration
    20260814000000_add_transaction_splits.sql).

    `transaction_count` for a category that includes split transactions
    counts contributing split line-items, not distinct transactions — an
    approximation for split transactions, not a distinct-transaction count.
    """
    user_id = request.state.user_id

    try:
        resp = await run_query(
            lambda: supabase_client.rpc("spend_by_category_for_user", {"p_user_id": user_id}).execute()
        )
        return {
            "categories": [
                {
                    "category": row["category_name"],
                    "total_amount": float(row["amount"]),
                    "transaction_count": int(row["txn_count"]),
                }
                for row in (resp.data or [])
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/by-category")


@router.get("/trends")
async def get_trends(request: Request, days: int = 30, granularity: str = "day", months: int = 12):
    """Spending trends.

    - granularity="day" (default): daily spend over the last `days` days. Keeps
      the original behavior/response shape intact.
    - granularity="month": monthly spend over the last `months` months, so the
      Overview can show each month's progression. Buckets are "YYYY-MM".

    Both return {"trends": [{"date": ..., "total_spend": ...}]}; only the `date`
    string format differs (day vs month).
    """
    user_id = request.state.user_id
    # Clamp so absurd values can't overflow datetime math into a 500.
    days = max(1, min(days, 3650))
    months = max(1, min(months, 120))

    try:
        if granularity == "month":
            # First day of the month (months-1) back, so we return `months`
            # buckets inclusive of the current month.
            start = _month_start()
            year = start.year + (start.month - 1 - (months - 1)) // 12
            month = (start.month - 1 - (months - 1)) % 12 + 1
            cutoff = datetime(year, month, 1)
        else:
            cutoff = _now_cn() - timedelta(days=days)

        # Bucketed and summed in Postgres (migration
        # 20260927020000_dashboard_aggregate_rpcs.sql): ~12 rows back
        # instead of every transaction in the window, 1,000 per round trip.
        resp, home = await asyncio.gather(
            run_query(
                lambda: supabase_client.rpc(
                    "spend_trend_for_user",
                    {
                        "p_user_id": user_id,
                        "p_start": cutoff.isoformat(),
                        "p_granularity": "month" if granularity == "month" else "day",
                    },
                ).execute()
            ),
            _home_currency(user_id),
        )

        home_by_bucket: dict = {}
        if home:
            # Same rows as the trend RPC (categorized/split expense rows),
            # per day, so each day converts at its own rate.
            flows = await _daily_flows(user_id, cutoff, None)
            rates = await _load_rates(home, [r["day"] for r in flows])
            width = 7 if granularity == "month" else 10
            days_by_bucket: dict = {}
            for r in flows:
                days_by_bucket.setdefault(r["day"].isoformat()[:width], []).append((r["day"], r["categorized_spend"]))
            home_by_bucket = {b: _r2(_strict_sum(pairs, rates)) for b, pairs in days_by_bucket.items()}

        return {
            "currency_home": home,
            "trends": [
                {
                    "date": row["bucket"],
                    "total_spend": float(row["total"]),
                    "total_spend_home": home_by_bucket.get(row["bucket"]) if home else None,
                }
                for row in (resp.data or [])
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/trends")


@router.get("/cashflow")
async def get_cashflow(request: Request, months: int = 12):
    """Monthly money in vs out (contract §3.5).

    net = income − spend; transfers are shown but EXCLUDED from net (paying
    a friend back isn't spending, a red packet isn't salary). Transfers
    between the user's own accounts (own_account, repayment, top_up,
    withdrawal) are neither in nor out — they're summed, absolute, into
    `own_account_moved` for the whole window. Income comes only from
    statements, never from the Settings figure.
    """
    user_id = request.state.user_id
    months = min(max(1, months), 36)

    try:
        # Same window as trends?granularity=month: `months` calendar months
        # ending with the current China-time month.
        start = _months_ago_start(months - 1)
        _, end = _month_bounds(None)
        flows, home = await asyncio.gather(_daily_flows(user_id, start, end), _home_currency(user_id))
        rates = await _load_rates(home, [r["day"] for r in flows]) if home else None

        by_month: dict = {}
        for r in flows:
            by_month.setdefault(r["day"].isoformat()[:7], []).append(r)

        result = []
        for i in range(months):
            m = _months_ago_start(months - 1 - i)
            key = f"{m.year:04d}-{m.month:02d}"
            rows = by_month.get(key, [])
            spend = _flow_total(rows, "spend")
            income = _flow_total(rows, "income")
            spend_home = income_home = net_home = None
            if home:
                spend_home = _strict_sum(((r["day"], r["spend"]) for r in rows), rates)
                income_home = _strict_sum(((r["day"], r["income"]) for r in rows), rates)
                if spend_home is not None and income_home is not None:
                    net_home = income_home - spend_home  # from unrounded parts
            result.append({
                "month": key,
                "spend": round(spend, 2),
                "income": round(income, 2),
                "transfers_in": round(_flow_total(rows, "transfers_in"), 2),
                "transfers_out": round(_flow_total(rows, "transfers_out"), 2),
                "net": round(income - spend, 2),
                "spend_home": _r2(spend_home),
                "income_home": _r2(income_home),
                "net_home": _r2(net_home),
            })

        return {
            "currency_home": home,
            "months": result,
            "own_account_moved": round(_flow_total(flows, "own_account_moved"), 2),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/cashflow")


MIN_TRANSACTIONS_FOR_ANOMALY = 5  # per category, within the trailing window
ANOMALY_STD_MULTIPLIER = 2


@router.get("/insights")
async def get_insights(request: Request):
    """Per-category spending trend (this month vs. trailing 3-month average)
    and per-transaction amount anomalies within that same window.

    Read-only, nothing persisted — same "compute fresh every call" approach
    as `get_action`/`_budget_crossings`, just per-category and per-transaction
    instead of per-budget-limit.

    category_trends includes both plain-categorized transactions and
    transaction_splits line-items (fetched separately and concatenated in
    pandas before the groupby, since transaction_splits has no timestamp of
    its own and must be filtered against its parent transaction's
    timestamp).

    flagged_transactions (per-transaction anomaly detection) excludes
    transactions where is_split=True — a split transaction's whole amount
    isn't attributable to one category, so anomaly-flagging it against any
    single category's mean would be wrong. Known limitation: split
    transactions are never flagged as anomalies, even if a large one would
    otherwise qualify.
    """
    user_id = request.state.user_id

    try:
        now = _now_cn()
        month_start = _month_start(now)
        window_start = _months_ago_start(3, now)

        plain_rows = await fetch_all_async(
            lambda: supabase_client.table("transactions")
            .select("id, merchant, merchant_en, amount, timestamp, is_split, categories(name)")
            .eq("user_id", user_id)
            .eq("kind", "expense")
            .not_.is_("category_id", "null")
            .gte("timestamp", window_start.isoformat())
        )
        # Splits only ever exist on expense rows (DB CHECK
        # transactions_split_only_expense), so no kind filter is needed here.
        split_rows_raw = await fetch_all_async(
            lambda: supabase_client.table("transaction_splits")
            .select("transaction_id, amount, categories(name), transactions(timestamp)")
            .eq("user_id", user_id)
        )
        split_rows = [
            {
                "id": r["transaction_id"],
                "merchant": None,
                "amount": r["amount"],
                "timestamp": r["transactions"]["timestamp"],
                "is_split": True,
                "category_name": r["categories"]["name"] if r["categories"] else "Unknown",
            }
            for r in split_rows_raw
            if r["transactions"] and r["transactions"]["timestamp"] >= window_start.isoformat()
        ]

        if not plain_rows and not split_rows:
            return {"category_trends": [], "flagged_transactions": []}

        # English display names (stored translations, no network) — raw
        # merchant text can be Chinese, which the UI must never show.
        merchant_labels = {
            r["id"]: merchant_label_stored(r["merchant"], r.get("merchant_en")) for r in plain_rows
        }
        request_translation_if_missing(user_id, plain_rows)

        plain_df = pd.DataFrame(plain_rows)
        if not plain_df.empty:
            plain_df["category_name"] = plain_df["categories"].apply(lambda x: x["name"] if x else "Unknown")
            # reindex (not a plain column-list select): "is_split" may be
            # absent from older seeded/legacy rows that predate this column,
            # and reindex fills a missing column with NaN instead of raising.
            plain_df = plain_df.reindex(columns=["id", "merchant", "amount", "timestamp", "is_split", "category_name"])
            plain_df["is_split"] = plain_df["is_split"].fillna(False)
        split_df = pd.DataFrame(split_rows)
        df = pd.concat([plain_df, split_df], ignore_index=True) if not split_df.empty else plain_df

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["month"] = df["timestamp"].dt.to_period("M")

        current_period = pd.Period(month_start, freq="M")
        current_df = df[df["month"] == current_period]
        prior_df = df[df["month"] != current_period]

        current_by_cat = current_df.groupby("category_name")["amount"].sum()
        prior_avg_by_cat = (
            prior_df.groupby(["category_name", "month"])["amount"].sum().groupby("category_name").mean()
        )

        category_trends = []
        for cat in set(current_by_cat.index) | set(prior_avg_by_cat.index):
            avg = float(prior_avg_by_cat.get(cat, 0))
            if avg <= 0:
                continue  # no prior-month baseline to compare against
            current = float(current_by_cat.get(cat, 0))
            category_trends.append({
                "category": cat,
                "current": round(current, 2),
                "avg_3mo": round(avg, 2),
                "pct_change": round(100 * (current - avg) / avg, 1),
            })
        category_trends.sort(key=lambda t: abs(t["pct_change"]), reverse=True)

        # Anomaly flagging excludes split transactions (is_split=True) — see
        # docstring.
        flag_df = df[df["is_split"] != True]  # noqa: E712
        flagged_transactions = []
        for cat, group in flag_df.groupby("category_name"):
            if len(group) < MIN_TRANSACTIONS_FOR_ANOMALY:
                continue
            std = group["amount"].std()
            if not std or pd.isna(std):
                continue
            threshold = group["amount"].mean() + ANOMALY_STD_MULTIPLIER * std
            for _, txn in group[group["amount"] > threshold].iterrows():
                flagged_transactions.append({
                    "id": txn["id"],
                    "merchant": merchant_labels.get(txn["id"], txn["merchant"]),
                    "category": cat,
                    "amount": float(txn["amount"]),
                    "timestamp": txn["timestamp"].isoformat(),
                })
        flagged_transactions.sort(key=lambda t: t["amount"], reverse=True)

        return {"category_trends": category_trends, "flagged_transactions": flagged_transactions}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/insights")
