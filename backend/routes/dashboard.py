"""Dashboard endpoints: stats, trends, category breakdowns.

Notes on postgrest-py usage: negated filters use the `.not_` PROPERTY
(e.g. `.not_.is_("category_id", "null")`). Calling `.not_(...)` raises
TypeError — it is not a method.
"""
import asyncio
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from config import supabase_client
from db import fetch_all_async, run_query
from errors import internal_error
from limiter import limiter
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pandas as pd
from src.translate import merchant_label_stored, description_label_stored
from translations import request_translation_if_missing, request_translation_periodic
from src.categories import CATEGORY_BUCKET

router = APIRouter()


def _now_cn() -> datetime:
    """Naive China-clock 'now'. Transaction timestamps come from Alipay/WeChat
    exports in China local time and are stored naive, so month boundaries and
    cutoffs must use the same clock — not the server's (UTC on Render)."""
    return datetime.now(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)


def _month_start(now: datetime = None) -> datetime:
    now = now or _now_cn()
    return datetime(now.year, now.month, 1)


def _parse_utc(ts: str) -> datetime:
    """Parse a `timestamp with time zone` column's ISO string into an
    aware UTC datetime — for comparing against `datetime.now(timezone.utc)`
    (never `_now_cn()`, which is naive and on a different clock)."""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _months_ago_start(n: int, now: datetime = None) -> datetime:
    """First-of-month, n months before `now` (or the current month)."""
    now = now or _now_cn()
    total_months = now.year * 12 + (now.month - 1) - n
    return datetime(total_months // 12, total_months % 12 + 1, 1)


# ── Transaction kinds & home currency (API v5) ──────────────────────────
# "Spend" is always kind='expense' (refunds are negative expense rows).
# Income/transfer rows exist since parser v2; they only show up in cash
# flow, reports (kind filter) and the export.
KINDS = ("expense", "income", "transfer")
KIND_LABELS = {"expense": "Expense", "income": "Income", "transfer": "Transfer"}
# Same English labels as FLOW_SUBTYPE_LABELS in frontend/src/types/v5.ts.
FLOW_SUBTYPE_LABELS = {
    "refund": "Refund",
    "red_packet": "Red packet",
    "p2p_transfer": "Transfer to/from a person",
    "aa_collection": "Split-bill collection",
    "salary": "Salary",
    "interest": "Interest",
    "own_account": "Between own accounts",
    "repayment": "Credit repayment",
    "top_up": "Top-up",
    "withdrawal": "Withdrawal",
    "other": "Other",
}
FX_LOOKBACK = timedelta(days=7)  # strict lookup: rate_date in [d - 7, d]


def _fx():
    """backend/fx.py, imported lazily (it reads only the fx_rates cache —
    never the network — on every GET). Returns None if the module is absent,
    which then behaves exactly like "no home currency"."""
    try:
        import fx
        return fx
    except ImportError:
        return None


async def _home_currency(user_id: str) -> Optional[str]:
    fx = _fx()
    return await fx.get_home_currency(user_id) if fx else None


async def _load_rates(home: Optional[str], days) -> Optional[object]:
    """ONE fx_rates range read covering every date in `days` (plus the
    7-day strict lookback, and up to today for rate_asof). None without a
    home currency."""
    if not home:
        return None
    today = _now_cn().date()
    days = [d for d in days if d is not None]
    start = (min(days) if days else today) - FX_LOOKBACK
    end = max(max(days) if days else today, today)
    return await _fx().load_rates(home, start, end)


def _row_day(ts: str) -> date:
    """Calendar date of a transaction row — ("timestamp" AT TIME ZONE 'UTC')::date."""
    fx = _fx()
    if fx:
        return fx.row_date(ts)
    return _parse_utc(ts).astimezone(timezone.utc).date()


def _r2(value: Optional[float]) -> Optional[float]:
    return None if value is None else round(value, 2)


def _strict_sum(day_amounts, rates) -> Optional[float]:
    """Σ amount × strict rate(day), unrounded. `day_amounts` yields
    (date, amount-or-None); None amounts mean "no rows of this flow that
    day" and need no rate. Any contributing day without a rate makes the
    whole aggregate None — never a partial sum. Zero rows → 0."""
    total = 0.0
    for day, amount in day_amounts:
        if amount is None:
            continue
        rate = rates.strict(day)
        if rate is None:
            return None
        total += float(amount) * rate
    return total


def _reference_rate(rates, month_start: datetime) -> Optional[float]:
    """Rate for undated amounts (budgets, settings income): strict lookup at
    min(last day of the month, today)."""
    if rates is None:
        return None
    _, next_month = _month_bounds(f"{month_start.year:04d}-{month_start.month:02d}")
    ref_day = min((next_month - timedelta(days=1)).date(), _now_cn().date())
    return rates.strict(ref_day)


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


async def _monthly_income(user_id: str) -> float:
    """Monthly income from profiles.monthly_income (the only written source)."""
    resp = await run_query(lambda: supabase_client.table("profiles").select("monthly_income").eq("id", user_id).execute())
    if resp.data and resp.data[0].get("monthly_income") is not None:
        return float(resp.data[0]["monthly_income"])
    return 0.0


async def _budget_config(user_id: str):
    resp = await run_query(lambda: supabase_client.table("budget_config").select("*").eq("user_id", user_id).execute())
    return resp.data[0] if resp.data else None


async def _spend_by_category(user_id: str, start: datetime, end: datetime) -> dict:
    """Spend per category name within [start, end) — a single month window.

    Monthly budgets compare against one month's spend, so callers pass that
    month's bounds. Includes both plain-categorized transactions and
    transaction_splits line-items (see spend_by_category_for_user RPC in
    supabase/migrations/20260814000000_add_transaction_splits.sql), so a
    split transaction's per-category contributions count toward budgets the
    same as an unsplit one's.
    """
    resp = await run_query(
        lambda: supabase_client.rpc(
            "spend_by_category_for_user",
            {"p_user_id": user_id, "p_start": start.isoformat(), "p_end": end.isoformat()},
        ).execute()
    )
    return {row["category_name"]: float(row["amount"]) for row in (resp.data or [])}


def _month_bounds(month: Optional[str] = None) -> tuple:
    """Parse a 'YYYY-MM' string into (first-of-month, first-of-next-month).

    None → the current month. Raises HTTPException(400) on malformed input."""
    if not month:
        start = _month_start()
    else:
        try:
            start = datetime(int(month[:4]), int(month[5:7]), 1)
            if len(month) != 7 or month[4] != "-":
                raise ValueError
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="month must be formatted as YYYY-MM")
    end = datetime(start.year + (start.month == 12), (start.month % 12) + 1, 1)
    return start, end


async def _available_months(user_id: str) -> list:
    """Distinct 'YYYY-MM' values that actually have transactions, newest first,
    so the frontend can populate a month selector."""
    # Computed in Postgres (migration 20260927020000_dashboard_aggregate_rpcs.sql)
    # — used to page the user's ENTIRE history here on every Budget load.
    resp = await run_query(
        lambda: supabase_client.rpc("available_months_for_user", {"p_user_id": user_id}).execute()
    )
    return [m if isinstance(m, str) else m["available_months_for_user"] for m in (resp.data or [])]


@router.get("/budget")
async def get_budget(request: Request, month: Optional[str] = None):
    """Budget info: limits by category, spend vs budget for a chosen month.

    `month` is 'YYYY-MM'; omitted → current month (preserves prior behavior).
    Budgets themselves are global (one value per category, no per-month history),
    so for past months the *spend* is real but it's compared against today's
    budget — the response carries `month` + `available_months` so the UI can
    offer a selector and label the caveat.
    """
    user_id = request.state.user_id

    try:
        start, end = _month_bounds(month)
        resolved_month = f"{start.year:04d}-{start.month:02d}"
        # Independent reads, run concurrently. Monthly income's single source
        # of truth is profiles.monthly_income (written by PATCH
        # /settings/profile); budget_config.income is legacy, never written.
        available_months, budget_config, cat_budget_resp, monthly_income, spending_by_cat, home = await asyncio.gather(
            _available_months(user_id),
            _budget_config(user_id),
            run_query(
                lambda: supabase_client.table("budget_category_config")
                .select("*, categories(name)")
                .eq("user_id", user_id)
                .execute()
            ),
            _monthly_income(user_id),
            _spend_by_category(user_id, start, end),
            _home_currency(user_id),
        )

        # Legacy display setting — unrelated to the home currency.
        budget_config_out = {
            "monthly_income": monthly_income,
            "currency": budget_config["currency"] if budget_config else "CNY",
        }

        if not cat_budget_resp.data:
            zero_home = 0.0 if home else None
            return {
                "budget_config": budget_config_out,
                "category_budgets": [],
                "month": resolved_month,
                "available_months": available_months,
                "total_budget": 0,
                "total_spent": 0,
                "currency_home": home,
                "total_budget_home": zero_home,
                "total_spent_home": zero_home,
            }

        spend_home_by_cat: dict = {}
        ref_rate = None
        if home:
            # Each line-item converts at its own day's rate (split items use
            # the parent transaction's day); budgets at the month's rate.
            daily = await fetch_all_async(
                lambda: supabase_client.rpc(
                    "spend_by_category_daily_for_user",
                    {"p_user_id": user_id, "p_start": start.isoformat(), "p_end": end.isoformat()},
                )
            )
            pairs_by_cat: dict = {}
            for r in daily:
                day = date.fromisoformat(str(r["day"])[:10])
                pairs_by_cat.setdefault(r["category_name"], []).append((day, float(r["amount"])))
            rates = await _load_rates(home, [d for pairs in pairs_by_cat.values() for d, _ in pairs] + [start.date()])
            spend_home_by_cat = {name: _strict_sum(pairs, rates) for name, pairs in pairs_by_cat.items()}
            ref_rate = _reference_rate(rates, start)

        def to_home(amount: float) -> Optional[float]:
            return amount * ref_rate if ref_rate is not None else None

        category_budgets = []
        for row in cat_budget_resp.data:
            cat_name = row["categories"]["name"] if row["categories"] else "Unknown"
            monthly_budget = float(row["monthly_budget"]) if row["monthly_budget"] else 0
            item = {
                "category": cat_name,
                "monthly_budget": monthly_budget,
                "current_spend": float(spending_by_cat.get(cat_name, 0)),
                "type": row["type"],
                "monthly_budget_home": None,
                "current_spend_home": None,
            }
            if home:
                item["monthly_budget_home"] = to_home(monthly_budget)
                item["current_spend_home"] = spend_home_by_cat.get(cat_name, 0.0)
            category_budgets.append(item)

        total_budget = sum(c["monthly_budget"] for c in category_budgets)
        total_spent = sum(c["current_spend"] for c in category_budgets)
        total_budget_home = total_spent_home = None
        if home:
            budget_homes = [c["monthly_budget_home"] for c in category_budgets]
            spent_homes = [c["current_spend_home"] for c in category_budgets]
            total_budget_home = None if None in budget_homes else sum(budget_homes)
            total_spent_home = None if None in spent_homes else sum(spent_homes)
            # Totals were summed unrounded; round every home figure once now.
            for c in category_budgets:
                c["monthly_budget_home"] = _r2(c["monthly_budget_home"])
                c["current_spend_home"] = _r2(c["current_spend_home"])

        return {
            "budget_config": budget_config_out,
            "category_budgets": category_budgets,
            "month": resolved_month,
            "available_months": available_months,
            "total_budget": round(total_budget, 2),
            "total_spent": round(total_spent, 2),
            "currency_home": home,
            "total_budget_home": _r2(total_budget_home),
            "total_spent_home": _r2(total_spent_home),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/budget")


class CategoryBudgetItem(BaseModel):
    category_id: str
    monthly_budget: Optional[float] = None
    type: str = "Need"  # budget_type enum: 'Need' | 'Want'


class CategoryBudgetsUpdate(BaseModel):
    budgets: List[CategoryBudgetItem]


@router.put("/budget/categories")
async def put_category_budgets(request: Request, data: CategoryBudgetsUpdate):
    """Set per-category monthly budgets (upsert on user_id + category_id).

    This is the writer budget_category_config never had — the Budget tab and
    the over-budget Action items read from it but nothing could populate it.
    """
    user_id = request.state.user_id

    try:
        if not data.budgets:
            raise HTTPException(status_code=400, detail="No budgets provided")

        # Only allow the user's own categories
        cat_resp = await run_query(lambda: supabase_client.table("categories").select("id").eq("user_id", user_id).execute())
        own_ids = {c["id"] for c in (cat_resp.data or [])}

        rows = []
        for item in data.budgets:
            if item.category_id not in own_ids:
                raise HTTPException(status_code=400, detail="Unknown category")
            if item.type not in ("Need", "Want"):
                raise HTTPException(status_code=400, detail="type must be 'Need' or 'Want'")
            rows.append({
                "user_id": user_id,
                "category_id": item.category_id,
                "type": item.type,
                "monthly_budget": item.monthly_budget,
            })

        response = await run_query(
            lambda: supabase_client.table("budget_category_config")
            .upsert(rows, on_conflict="user_id,category_id")
            .execute()
        )
        return {"updated": len(response.data or rows)}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/put_category_budgets")


@router.get("/rule-503020")
async def get_rule_503020(request: Request, month: Optional[str] = None):
    """50/30/20 rule breakdown: Needs/Wants/Savings vs income-derived targets.

    Buckets every categorized transaction for the month via the static
    `CATEGORY_BUCKET` mapping (src/categories.py) — unlike
    `budget_category_config.type`, this covers ALL spend, not just categories
    the user happened to set a $ budget for, and it's the only place a
    'Savings' bucket exists (that table's enum is still just Need/Want).

    Savings = money spent in the Investments category + unspent income
    (income minus everything actually spent that month, floored at 0) — the
    standard "what you didn't spend also counts as saved" definition.
    """
    user_id = request.state.user_id

    try:
        start, end = _month_bounds(month)
        resolved_month = f"{start.year:04d}-{start.month:02d}"
        available_months, income, spend_by_cat = await asyncio.gather(
            _available_months(user_id),
            _monthly_income(user_id),
            _spend_by_category(user_id, start, end),
        )

        bucket_totals = {"Need": 0.0, "Want": 0.0, "Savings": 0.0}
        bucket_categories: dict = {"Need": [], "Want": [], "Savings": []}
        for cat_name, amount in spend_by_cat.items():
            bucket = CATEGORY_BUCKET.get(cat_name)
            if not bucket or amount <= 0:
                continue
            bucket_totals[bucket] += amount
            bucket_categories[bucket].append({"category": cat_name, "amount": amount})

        total_spend = sum(spend_by_cat.values())
        unspent = max(income - total_spend, 0.0)
        if unspent > 0:
            bucket_totals["Savings"] += unspent
            bucket_categories["Savings"].append({"category": "Unspent income", "amount": unspent})

        for cats in bucket_categories.values():
            cats.sort(key=lambda c: c["amount"], reverse=True)

        def _bucket(name: str, target_pct: int) -> dict:
            return {
                "target_pct": target_pct,
                "target_amount": round(income * target_pct / 100, 2) if income > 0 else None,
                "spent": round(bucket_totals[name], 2),
                "categories": bucket_categories[name],
            }

        return {
            "month": resolved_month,
            "available_months": available_months,
            "income": income,
            "buckets": {
                "needs": _bucket("Need", 50),
                "wants": _bucket("Want", 30),
                "savings": _bucket("Savings", 20),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/rule-503020")


@router.get("/savings")
async def get_savings(request: Request):
    """Savings info: goals, current savings, anomalies."""
    user_id = request.state.user_id

    try:
        now = _now_cn()
        month_start = _month_start(now)
        # Simple anomaly detection: compare to average of last 3 months
        three_months_ago = _months_ago_start(3, now)

        # All independent — run concurrently. Current-month spend and
        # per-month totals are computed in Postgres (migration
        # 20260811090000_transaction_sum_rpcs.sql).
        budget_config, spend_resp, monthly_resp, income = await asyncio.gather(
            _budget_config(user_id),
            run_query(
                lambda: supabase_client.rpc(
                    "sum_user_transactions", {"p_user_id": user_id, "p_start": month_start.isoformat()}
                ).execute()
            ),
            run_query(
                lambda: supabase_client.rpc(
                    "monthly_spend_by_user",
                    {
                        "p_user_id": user_id,
                        "p_start": three_months_ago.isoformat(),
                        "p_end": month_start.isoformat(),
                    },
                ).execute()
            ),
            _monthly_income(user_id),
        )
        current_spend = float(spend_resp.data or 0)

        monthly_totals = [float(row["total"]) for row in (monthly_resp.data or [])]
        avg_monthly = sum(monthly_totals) / len(monthly_totals) if monthly_totals else 0

        savings_goal = float(budget_config["saving_goal_monthly"]) if budget_config and budget_config["saving_goal_monthly"] else 0

        return {
            "savings_goal_monthly": savings_goal,
            "income": income,
            "current_spend": float(current_spend),
            "projected_savings": max(0, income - current_spend),
            "average_monthly_spend": avg_monthly,
            "is_anomaly": current_spend > (avg_monthly * 1.3) if avg_monthly > 0 else False,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/savings")


DEFAULT_APPROACHING_BUDGET_THRESHOLD_PCT = 80  # used when profiles.alert_threshold_pct is unset
WELCOME_WINDOW = timedelta(hours=48)


async def _budget_crossings(user_id: str, threshold_pct: float) -> list:
    """Categories currently over, or approaching (>= threshold_pct%), their
    monthly budget. Shared by `get_action` (in-app, always computed fresh) and
    `backend/alerts.py::check_budget_alerts` (email side effect, gated by the
    `budget_alerts` de-dup table) — kept as one function so the two never
    drift out of sync on what counts as a crossing.

    Returns dicts with `kind` ('over' | 'approaching'), `category_id`,
    `category` (name), `current`, `limit`, and either `overage` (kind='over')
    or `pct` (kind='approaching').
    """
    cat_budget_resp = await run_query(
        lambda: supabase_client.table("budget_category_config")
        .select("*, categories(name)")
        .eq("user_id", user_id)
        .execute()
    )
    if not cat_budget_resp.data:
        return []

    # Crossings are always about the current month.
    start, end = _month_bounds(None)
    spending_by_cat = await _spend_by_category(user_id, start, end)

    crossings = []
    for budget_row in cat_budget_resp.data:
        cat_name = budget_row["categories"]["name"] if budget_row["categories"] else "Unknown"
        budget = float(budget_row["monthly_budget"]) if budget_row["monthly_budget"] else 0
        spend = float(spending_by_cat.get(cat_name, 0))

        if budget > 0 and spend > budget:
            crossings.append({
                "kind": "over",
                "category_id": budget_row["category_id"],
                "category": cat_name,
                "current": spend,
                "limit": budget,
                "overage": spend - budget,
            })
        elif budget > 0 and spend >= (threshold_pct / 100) * budget:
            crossings.append({
                "kind": "approaching",
                "category_id": budget_row["category_id"],
                "category": cat_name,
                "current": spend,
                "limit": budget,
                "pct": round(100 * spend / budget, 1),
            })

    return crossings


_CROSSING_KIND_TO_ACTION_TYPE = {"over": "over_budget", "approaching": "approaching_budget"}


@router.get("/action")
async def get_action(request: Request):
    """Action items: over-budget / approaching-budget categories, review queue count."""
    user_id = request.state.user_id

    try:
        actions = []

        profile_resp = await run_query(
            lambda: supabase_client.table("profiles")
            .select("alert_threshold_pct, budget_inapp_enabled, pending_review_inapp_enabled")
            .eq("id", user_id)
            .execute()
        )
        profile_row = profile_resp.data[0] if profile_resp.data else {}
        threshold_pct = (
            float(profile_row["alert_threshold_pct"])
            if profile_row.get("alert_threshold_pct") is not None
            else DEFAULT_APPROACHING_BUDGET_THRESHOLD_PCT
        )
        # Both default true (Settings > Notifications) — preserves the
        # always-on behavior these items had before the toggles existed.
        budget_inapp_enabled = profile_row.get("budget_inapp_enabled", True)
        pending_review_inapp_enabled = profile_row.get("pending_review_inapp_enabled", True)

        async def _review_count():
            if not pending_review_inapp_enabled:
                return 0
            resp = await run_query(
                lambda: supabase_client.table("transactions")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .eq("kind", "expense")
                .eq("needs_review", True)
                .limit(1)
                .execute()
            )
            return resp.count if resp.count is not None else len(resp.data)

        async def _crossings():
            return await _budget_crossings(user_id, threshold_pct) if budget_inapp_enabled else []

        crossings, review_count = await asyncio.gather(_crossings(), _review_count())

        if budget_inapp_enabled:
            for crossing in crossings:
                action = {
                    "type": _CROSSING_KIND_TO_ACTION_TYPE[crossing["kind"]],
                    "category": crossing["category"],
                    "current": crossing["current"],
                    "limit": crossing["limit"],
                }
                if crossing["kind"] == "over":
                    action["overage"] = crossing["overage"]
                else:
                    action["pct"] = crossing["pct"]
                actions.append(action)

        if pending_review_inapp_enabled:
            if review_count > 0:
                actions.append({
                    "type": "pending_review",
                    "count": review_count,
                    "message": f"{review_count} transactions need review",
                })

        return {"actions": actions}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/action")


async def _ensure_welcome_notification(user_id: str) -> None:
    """Lazily insert the one-time 'welcome' notification on first fetch,
    if the account is still within WELCOME_WINDOW of signup. Avoids
    touching the signup trigger/migration for a single row; the
    (user_id, dedup_key) unique constraint means this only ever inserts
    once per account regardless of how many times it's called."""
    profile_resp = await run_query(
        lambda: supabase_client.table("profiles").select("created_at").eq("id", user_id).execute()
    )
    if not profile_resp.data or not profile_resp.data[0].get("created_at"):
        return
    account_age = datetime.now(timezone.utc) - _parse_utc(profile_resp.data[0]["created_at"])
    if account_age > WELCOME_WINDOW:
        return
    await run_query(
        lambda: supabase_client.table("notifications")
        .upsert(
            {
                "user_id": user_id,
                "type": "welcome",
                "dedup_key": "welcome",
                "payload": {
                    "message": "Welcome to Financing! Upload your first Alipay or WeChat "
                               "statement to get started.",
                },
            },
            on_conflict="user_id,dedup_key",
            ignore_duplicates=True,
        )
        .execute()
    )


@router.get("/notifications")
async def get_notifications(request: Request):
    """Persisted notification history for the header bell: over_budget /
    approaching_budget / welcome / training_complete. Distinct from
    GET /dashboard/action (Planning -> Action plan), which stays fully
    live-computed and unaffected by read/cleared state."""
    user_id = request.state.user_id

    try:
        await _ensure_welcome_notification(user_id)

        resp = await run_query(
            lambda: supabase_client.table("notifications")
            .select("*")
            .eq("user_id", user_id)
            .is_("cleared_at", "null")
            .order("created_at", desc=True)
            .execute()
        )
        notifications = resp.data or []
        unread_count = sum(1 for n in notifications if not n.get("read_at"))

        return {"notifications": notifications, "unread_count": unread_count}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/notifications")


@router.post("/notifications/read")
async def mark_notifications_read(request: Request):
    """Mark every active, unread notification as read — called when the
    bell dropdown opens."""
    user_id = request.state.user_id

    try:
        await run_query(
            lambda: supabase_client.table("notifications")
            .update({"read_at": datetime.now(timezone.utc).isoformat()})
            .eq("user_id", user_id)
            .is_("cleared_at", "null")
            .is_("read_at", "null")
            .execute()
        )
        return {"message": "Notifications marked read"}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/notifications/read")


@router.post("/notifications/clear")
async def clear_notifications(request: Request):
    """Remove every active notification from the bell — a cleared
    notification never reappears; only a genuinely new event does."""
    user_id = request.state.user_id

    try:
        now = datetime.now(timezone.utc).isoformat()
        await run_query(
            lambda: supabase_client.table("notifications")
            .update({"cleared_at": now, "read_at": now})
            .eq("user_id", user_id)
            .is_("cleared_at", "null")
            .execute()
        )
        return {"message": "Notifications cleared"}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/notifications/clear")


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


@router.get("/reports")
async def get_reports(
    request: Request,
    page: int = 1,
    per_page: int = 100,
    uncategorized_only: bool = False,
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    sort_by: Optional[str] = "date",
    sort_dir: Optional[str] = "desc",
    bucket: Optional[str] = None,
    kind: Optional[str] = "expense",
):
    """Detailed reports: paginated transaction list.

    `kind` (`expense` default | `income` | `transfer` | `all`; anything else
    → `expense`) picks which transaction kinds are listed, so the v4
    Reports tab (no `kind`) is unchanged. Category, bucket and
    uncategorized filters only match expense rows: combined with
    `income`/`transfer` they return an empty page, and with `all` they
    restrict to expense rows. Each row carries `kind`, `flow_subtype`,
    `source` and `amount_home` (per-row conversion, or null).

    Now includes uncategorized rows (so users can categorize anything from the
    table) and returns each row's `id`/`category_id` so the frontend can edit
    the category inline via POST /classify/{id}/label. Optional filters:
    `uncategorized_only`/`category_id` (mutually exclusive, as before), plus
    `search` (merchant/description substring), a `date_from`/`date_to`
    (`YYYY-MM-DD`) range, and a `min_amount`/`max_amount` range — all
    independent of each other and of the category filters, so any
    combination can apply at once. `sort_by` (`date`/`category`) and
    `sort_dir` (`asc`/`desc`) control ordering; unrecognized values fall back
    to the defaults (date, newest first) rather than erroring. `bucket`
    (`Need`/`Want`/`Savings`) filters to categories in that CATEGORY_BUCKET
    group (see the 50/30/20 endpoint below for what that mapping is/isn't);
    unrecognized values are ignored rather than erroring.
    """
    user_id = request.state.user_id
    page = max(1, page)
    per_page = min(max(1, per_page), 500)
    if sort_by not in ("date", "category"):
        sort_by = "date"
    if sort_dir not in ("asc", "desc"):
        sort_dir = "desc"
    if bucket not in ("Need", "Want", "Savings"):
        bucket = None
    if kind not in KINDS + ("all",):
        kind = "expense"

    try:
        async def empty_page():
            return {"transactions": [], "total_count": 0, "page": page, "per_page": per_page,
                    "kind": kind, "currency_home": await _home_currency(user_id)}

        expense_only_filter = uncategorized_only or bool(category_id) or bool(bucket)
        if expense_only_filter and kind in ("income", "transfer"):
            return await empty_page()  # non-expense rows have no category at all

        start = (page - 1) * per_page
        query = (
            supabase_client.table("transactions")
            .select("id, timestamp, merchant, description, merchant_en, description_en, amount, category_id, categories(name), is_split, label_source, kind, flow_subtype, source",
                    count="exact")
            .eq("user_id", user_id)
        )
        if kind != "all":
            query = query.eq("kind", kind)
        elif expense_only_filter:
            query = query.eq("kind", "expense")
        if uncategorized_only:
            query = query.is_("category_id", "null")
        elif category_id:
            query = query.eq("category_id", category_id)
        if search:
            escaped = search.replace(",", "").replace("%", "")
            query = query.or_(f"merchant.ilike.%{escaped}%,description.ilike.%{escaped}%")
        if date_from:
            query = query.gte("timestamp", date_from)
        if date_to:
            query = query.lt("timestamp", date_to)
        if min_amount is not None:
            query = query.gte("amount", min_amount)
        if max_amount is not None:
            query = query.lte("amount", max_amount)

        if bucket:
            bucket_category_names = [name for name, b in CATEGORY_BUCKET.items() if b == bucket]
            bucket_cat_resp = await run_query(
                lambda: supabase_client.table("categories")
                .select("id")
                .eq("user_id", user_id)
                .in_("name", bucket_category_names)
                .execute()
            )
            bucket_category_ids = [c["id"] for c in (bucket_cat_resp.data or [])]
            if not bucket_category_ids:
                # None of this user's categories fall in the requested bucket —
                # short-circuit rather than pass an empty list to .in_().
                return await empty_page()
            query = query.in_("category_id", bucket_category_ids)

        if sort_by == "category":
            query = query.order("name", desc=(sort_dir == "desc"), foreign_table="categories")
        else:
            query = query.order("timestamp", desc=(sort_dir != "asc"))

        response, home = await asyncio.gather(
            run_query(
                lambda: query
                .range(start, start + per_page - 1)
                .execute()
            ),
            _home_currency(user_id),
        )

        total_count = response.count if response.count is not None else len(response.data or [])

        # Per-row home amounts: one rate read covering this page's dates.
        row_days = {t["id"]: _row_day(t["timestamp"]) for t in (response.data or []) if t.get("timestamp")}
        rates = await _load_rates(home, list(row_days.values())) if home and row_days else None

        def amount_home(txn) -> Optional[float]:
            day = row_days.get(txn["id"])
            rate = rates.strict(day) if rates is not None and day is not None else None
            return round(float(txn["amount"]) * rate, 2) if rate is not None else None

        split_txn_ids = [t["id"] for t in (response.data or []) if t.get("is_split")]
        splits_by_txn: dict = {}
        split_counts: dict = {}
        if split_txn_ids:
            split_resp = await run_query(
                lambda: supabase_client.table("transaction_splits")
                .select("transaction_id, category_id, amount, categories(name)")
                .in_("transaction_id", split_txn_ids)
                .execute()
            )
            for row in (split_resp.data or []):
                tid = row["transaction_id"]
                splits_by_txn.setdefault(tid, []).append({
                    "category_id": row["category_id"],
                    "category_name": row["categories"]["name"] if row["categories"] else "Unknown",
                    "amount": float(row["amount"]),
                })
                split_counts[tid] = split_counts.get(tid, 0) + 1

        def build_rows():
            rows = []
            for txn in (response.data or []):
                txn_kind = txn.get("kind") or "expense"
                is_expense = txn_kind == "expense"
                is_split = is_expense and bool(txn.get("is_split"))
                category_name = txn["categories"]["name"] if txn["categories"] and is_expense else None
                if not is_expense:
                    category_label = KIND_LABELS[txn_kind]  # "Income" / "Transfer"
                elif is_split:
                    n = split_counts.get(txn["id"], 0)
                    category_label = f"Split ({n})"
                else:
                    category_label = category_name or "Uncategorized"
                rows.append({
                    "id": txn["id"],
                    "date": txn["timestamp"],
                    "merchant": merchant_label_stored(txn["merchant"], txn.get("merchant_en")),
                    "description": description_label_stored(txn["description"], txn.get("description_en")),
                    "amount": float(txn["amount"]),
                    "category": category_label,
                    "category_id": txn["category_id"] if is_expense else None,
                    "is_split": is_split,
                    "splits": splits_by_txn.get(txn["id"], []) if is_split else None,
                    "label_source": txn["label_source"],
                    # No single bucket for a split (spans categories) or an
                    # uncategorized row (no category at all); custom
                    # categories not in CATEGORY_BUCKET also fall back to None.
                    "bucket": None if is_split or category_name is None else CATEGORY_BUCKET.get(category_name),
                    "kind": txn_kind,
                    "flow_subtype": txn.get("flow_subtype"),
                    "source": txn.get("source"),
                    "amount_home": amount_home(txn),
                })
            return rows

        # Labels come from stored translations (no network); rows still
        # missing one get filled in the background for the next load.
        request_translation_if_missing(user_id, response.data or [])
        transactions = build_rows()

        return {
            "transactions": transactions,
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
            "kind": kind,
            "currency_home": home,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/reports")


@router.get("/export")
@limiter.limit("10/hour")
async def export_transactions(request: Request):
    """Export all user transactions as XLSX workbook.

    Every kind is exported. Columns:
    Date | Merchant | Description | Category | Kind | Amount | Home amount |
    Home currency | Label Source
    All text is translated to English; Amount and Home amount are formatted
    as #,##0.00. Category is empty for income/transfer rows; Home amount is
    an empty cell when no rate (or no home currency) exists.
    """
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    user_id = request.state.user_id

    try:
        def make_query():
            return (
                supabase_client.table("transactions")
                .select("id, timestamp, merchant, description, merchant_en, description_en, amount, category_id, categories(name), is_split, label_source, kind, flow_subtype")
                .eq("user_id", user_id)
                .order("timestamp", desc=True)
            )

        all_txns, home = await asyncio.gather(fetch_all_async(make_query), _home_currency(user_id))

        row_days = {t["id"]: _row_day(t["timestamp"]) for t in all_txns if t.get("timestamp")}
        rates = await _load_rates(home, list(row_days.values())) if home and row_days else None

        def amount_home(txn):
            day = row_days.get(txn["id"])
            rate = rates.strict(day) if rates is not None and day is not None else None
            return round(float(txn["amount"]) * rate, 2) if rate is not None else None

        def kind_label(txn) -> str:
            label = KIND_LABELS.get(txn.get("kind") or "expense", "Expense")
            subtype = txn.get("flow_subtype")
            return f"{label} ({FLOW_SUBTYPE_LABELS.get(subtype, subtype)})" if subtype else label

        def category_label(txn) -> str:
            if (txn.get("kind") or "expense") != "expense":
                return ""
            if txn.get("is_split"):
                return f"Split ({split_counts.get(txn['id'], 0)})"
            return txn["categories"]["name"] if txn["categories"] else "Uncategorized"

        split_counts_resp = await run_query(
            lambda: supabase_client.table("transaction_splits")
            .select("transaction_id")
            .eq("user_id", user_id)
            .execute()
        )
        split_counts: dict = {}
        for row in (split_counts_resp.data or []):
            split_counts[row["transaction_id"]] = split_counts.get(row["transaction_id"], 0) + 1

        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Transactions"

        # Headers
        headers = ["Date", "Merchant", "Description", "Category", "Kind", "Amount",
                   "Home amount", "Home currency", "Label Source"]
        ws.append(headers)

        # Format header row
        header_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
        header_font = Font(bold=True)
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font

        # Freeze header
        ws.freeze_panes = "A2"

        # Add data rows (labels from stored translations — no network).
        def _fmt_date(ts):
            if not ts:
                return ""
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y/%m/%d")

        def build_rows():
            return [
                [
                    _fmt_date(txn["timestamp"]),
                    merchant_label_stored(txn["merchant"], txn.get("merchant_en")),
                    description_label_stored(txn["description"], txn.get("description_en")),
                    category_label(txn),
                    kind_label(txn),
                    float(txn["amount"]),
                    amount_home(txn),  # None → empty cell
                    home or "",
                    txn["label_source"] or "",
                ]
                for txn in all_txns
            ]

        request_translation_if_missing(user_id, all_txns)
        for row in build_rows():
            ws.append(row)

        # Format the Amount (F) and Home amount (G) columns
        for row in ws.iter_rows(min_row=2, max_row=len(all_txns) + 1, min_col=6, max_col=7):
            for cell in row:
                cell.number_format = '#,##0.00'

        # Adjust column widths
        for col, width in zip("ABCDEFGHI", (12, 20, 30, 18, 26, 12, 14, 14, 14)):
            ws.column_dimensions[col].width = width

        # Write to bytes
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        # Return as attachment
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=transactions_{now}.xlsx"}
        )
    except Exception as e:
        raise internal_error(e, "dashboard/export")


@router.get("/review-queue")
async def get_review_queue(request: Request, show_labeled: bool = False):
    """Transactions needing review.

    By default (show_labeled=False): model suggestions with needs_review=True,
    sorted by confidence (lowest first — least confident suggestions).

    When show_labeled=True: manually labeled transactions (is_manually_labeled=True),
    so user can audit their own labels and catch human errors. Useful for catching
    accidental miscategorizations before retraining.
    """
    user_id = request.state.user_id

    try:
        if show_labeled:
            # Show manually labeled transactions for user review/correction
            response = await run_query(
                lambda: supabase_client.table("transactions")
                .select("id, timestamp, merchant, description, merchant_en, description_en, amount, confidence, category_id, categories(name), is_split")
                .eq("user_id", user_id)
                # A row re-kinded to income/transfer keeps its old
                # is_manually_labeled flag but has no category any more.
                .eq("kind", "expense")
                .eq("is_manually_labeled", True)
                .order("timestamp", desc=True)  # Most recent labels first
                .limit(50)
                .execute()
            )
            label_type = "manually_labeled"
            rows = response.data or []
        else:
            # Show model suggestions needing review. Pull a larger pool than we
            # need, then dedupe by merchant in Python (PostgREST has no
            # DISTINCT ON) so a handful of high-volume merchants don't flood
            # the queue — unique merchants make better labeling coverage.
            pool = await run_query(
                lambda: supabase_client.table("transactions")
                .select("id, timestamp, merchant, description, merchant_en, description_en, amount, confidence, category_id, categories(name), is_split")
                .eq("user_id", user_id)
                .eq("kind", "expense")
                .eq("needs_review", True)
                .order("confidence")  # Least confident first
                .limit(500)
                .execute()
            )
            label_type = "model_suggestion"

            seen_merchants: set = set()
            rows = []
            for txn in pool.data or []:
                if txn["merchant"] in seen_merchants:
                    continue
                seen_merchants.add(txn["merchant"])
                rows.append(txn)
                if len(rows) >= 50:
                    break

        if not rows:
            return {"transactions": [], "count": 0, "type": label_type}

        # In suggestion mode the row's category_id IS the model's suggestion —
        # report it only as suggested_category so the UI can distinguish
        # "this is what it's labeled" from "this is what the model proposes".
        def build_rows():
            return [
                {
                    "id": txn["id"],
                    "date": txn["timestamp"],
                    "merchant": merchant_label_stored(txn["merchant"], txn.get("merchant_en")),
                    "description": description_label_stored(txn["description"], txn.get("description_en")),
                    "amount": float(txn["amount"]),
                    "confidence": float(txn["confidence"]) if txn["confidence"] else 0,
                    "category": (("Split" if txn.get("is_split") else (txn["categories"]["name"] if txn["categories"] else None)) if show_labeled else None),
                    "suggested_category": "Split" if txn.get("is_split") else (txn["categories"]["name"] if txn["categories"] else None),
                }
                for txn in rows
            ]

        request_translation_if_missing(user_id, rows)
        transactions = build_rows()

        return {
            "transactions": transactions,
            "count": len(transactions),
            "type": label_type,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/review-queue")


# ── Onboarding tour ─────────────────────────────────────────────────────
# Progress lives on the account (profiles.tour_step / tour_finished_at —
# migration 20260927040000), not in the browser, so the tour shows exactly
# once per signup on any device. Steps advance only through
# POST /tour/advance with the step the user just completed, and only when it
# IS the current step (compare-and-set) — a step can never be skipped by
# stale data, a second tab, or a double click. "Skip tour" is the only early
# exit. Replaces the never-called /onboarding-status + /onboarding-complete.
TOUR_STEPS = ("upload", "categories", "label", "train")


def _tour_state(row: Optional[dict]) -> dict:
    if not row or row.get("tour_finished_at"):
        return {"finished": True, "step": None}
    idx = int(row.get("tour_step") or 0)
    if idx >= len(TOUR_STEPS):
        return {"finished": True, "step": None}
    return {"finished": False, "step": TOUR_STEPS[idx]}


async def _read_tour(user_id: str) -> Optional[dict]:
    resp = await run_query(
        lambda: supabase_client.table("profiles")
        .select("tour_step, tour_finished_at").eq("id", user_id).execute()
    )
    return resp.data[0] if resp.data else None


@router.get("/tour")
async def get_tour(request: Request):
    """Current onboarding-tour step, or finished."""
    try:
        return _tour_state(await _read_tour(request.state.user_id))
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/tour")


class TourAdvance(BaseModel):
    completed: str  # the step the user just finished, e.g. "upload"


@router.post("/tour/advance")
async def advance_tour(request: Request, body: TourAdvance):
    """Move to the next step, but only if `completed` is the current step.

    Anything else (a later step, an earlier one, a finished tour) is a no-op
    that just returns the current state — never an error, so callers can
    fire this after every upload/label/training without checking first.
    """
    user_id = request.state.user_id
    if body.completed not in TOUR_STEPS:
        raise HTTPException(status_code=400, detail="Unknown tour step")
    idx = TOUR_STEPS.index(body.completed)
    try:
        update = {"tour_step": idx + 1}
        if idx + 1 >= len(TOUR_STEPS):
            update["tour_finished_at"] = datetime.now(timezone.utc).isoformat()
        await run_query(
            lambda: supabase_client.table("profiles")
            .update(update)
            .eq("id", user_id)
            .eq("tour_step", idx)
            .is_("tour_finished_at", "null")
            .execute()
        )
        return _tour_state(await _read_tour(user_id))
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/tour/advance")


@router.post("/tour/skip")
async def skip_tour(request: Request):
    """End the tour for good ("Skip tour")."""
    user_id = request.state.user_id
    try:
        await run_query(
            lambda: supabase_client.table("profiles")
            .update({"tour_finished_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", user_id)
            .is_("tour_finished_at", "null")
            .execute()
        )
        return {"finished": True, "step": None}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/tour/skip")
