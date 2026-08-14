"""Dashboard endpoints: stats, trends, category breakdowns.

Notes on postgrest-py usage: negated filters use the `.not_` PROPERTY
(e.g. `.not_.is_("category_id", "null")`). Calling `.not_(...)` raises
TypeError — it is not a method.
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from starlette.concurrency import run_in_threadpool
from config import supabase_client
from db import fetch_all_async, run_query
from errors import internal_error
from limiter import limiter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
from translate import merchant_label_english, description_label_english

router = APIRouter()


def _now_cn() -> datetime:
    """Naive China-clock 'now'. Transaction timestamps come from Alipay/WeChat
    exports in China local time and are stored naive, so month boundaries and
    cutoffs must use the same clock — not the server's (UTC on Render)."""
    return datetime.now(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)


def _month_start(now: datetime = None) -> datetime:
    now = now or _now_cn()
    return datetime(now.year, now.month, 1)


def _months_ago_start(n: int, now: datetime = None) -> datetime:
    """First-of-month, n months before `now` (or the current month)."""
    now = now or _now_cn()
    total_months = now.year * 12 + (now.month - 1) - n
    return datetime(total_months // 12, total_months % 12 + 1, 1)


@router.get("/summary")
async def get_summary(request: Request):
    """Overall summary: total transactions, labeled%, total spend."""
    user_id = request.state.user_id

    try:
        # Total transactions
        total = await run_query(
            lambda: supabase_client.table("transactions").select("id", count="exact").eq("user_id", user_id).execute()
        )
        total_count = total.count if total.count is not None else len(total.data)

        # Labeled = has a trusted category (not still pending review)
        labeled = await run_query(
            lambda: supabase_client.table("transactions")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("needs_review", False)
            .not_.is_("category_id", "null")
            .execute()
        )
        labeled_count = labeled.count if labeled.count is not None else len(labeled.data)

        # Total spend, summed in Postgres (see migration
        # 20260811090000_transaction_sum_rpcs.sql) instead of pulling every
        # row and summing in Python.
        spend_resp = await run_query(
            lambda: supabase_client.rpc("sum_user_transactions", {"p_user_id": user_id}).execute()
        )
        total_spend = float(spend_resp.data or 0)

        return {
            "total_transactions": total_count,
            "labeled_transactions": labeled_count,
            "labeling_percentage": round(100 * labeled_count / total_count, 1) if total_count > 0 else 0,
            "total_spend": total_spend,
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

        # Filter server-side; never pull the full transaction history.
        rows = await fetch_all_async(
            lambda: supabase_client.table("transactions")
            .select("timestamp, amount")
            .eq("user_id", user_id)
            .or_("category_id.not.is.null,is_split.eq.true")
            .gte("timestamp", cutoff.isoformat())
        )

        if not rows:
            return {"trends": []}

        df = pd.DataFrame(rows)
        if granularity == "month":
            df["bucket"] = pd.to_datetime(df["timestamp"]).dt.to_period("M").astype(str)
        else:
            df["bucket"] = pd.to_datetime(df["timestamp"]).dt.date.astype(str)
        grouped = df.groupby("bucket")["amount"].sum().sort_index().reset_index()

        return {
            "trends": [
                {
                    "date": str(row["bucket"]),
                    "total_spend": float(row["amount"]),
                }
                for _, row in grouped.iterrows()
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/trends")


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
    rows = await fetch_all_async(
        lambda: supabase_client.table("transactions")
        .select("timestamp")
        .eq("user_id", user_id)
    )
    if not rows:
        return []
    months = pd.to_datetime(pd.DataFrame(rows)["timestamp"]).dt.to_period("M").astype(str)
    return sorted(months.unique().tolist(), reverse=True)


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
        available_months = await _available_months(user_id)

        # Monthly income's single source of truth is profiles.monthly_income
        # (written by PATCH /settings/profile). budget_config.income is legacy
        # and was never written by anything.
        budget_config = await _budget_config(user_id)

        cat_budget_resp = await run_query(
            lambda: supabase_client.table("budget_category_config")
            .select("*, categories(name)")
            .eq("user_id", user_id)
            .execute()
        )

        budget_config_out = {
            "monthly_income": await _monthly_income(user_id),
            "currency": budget_config["currency"] if budget_config else "CNY",
        }

        if not cat_budget_resp.data:
            return {
                "budget_config": budget_config_out,
                "category_budgets": [],
                "month": resolved_month,
                "available_months": available_months,
            }

        spending_by_cat = await _spend_by_category(user_id, start, end)

        category_budgets = []
        for row in cat_budget_resp.data:
            cat_name = row["categories"]["name"] if row["categories"] else "Unknown"
            category_budgets.append({
                "category": cat_name,
                "monthly_budget": float(row["monthly_budget"]) if row["monthly_budget"] else 0,
                "current_spend": float(spending_by_cat.get(cat_name, 0)),
                "type": row["type"],
            })

        return {
            "budget_config": budget_config_out,
            "category_budgets": category_budgets,
            "month": resolved_month,
            "available_months": available_months,
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


@router.get("/savings")
async def get_savings(request: Request):
    """Savings info: goals, current savings, anomalies."""
    user_id = request.state.user_id

    try:
        budget_config = await _budget_config(user_id)

        now = _now_cn()
        month_start = _month_start(now)

        # Current month spend, summed in Postgres (see migration
        # 20260811090000_transaction_sum_rpcs.sql) instead of pulling every
        # row and summing in Python.
        spend_resp = await run_query(
            lambda: supabase_client.rpc(
                "sum_user_transactions", {"p_user_id": user_id, "p_start": month_start.isoformat()}
            ).execute()
        )
        current_spend = float(spend_resp.data or 0)

        # Simple anomaly detection: compare to average of last 3 months
        three_months_ago = _months_ago_start(3, now)

        # Per-month totals computed in Postgres — a handful of rows (one per
        # month) instead of every raw transaction in the window.
        monthly_resp = await run_query(
            lambda: supabase_client.rpc(
                "monthly_spend_by_user",
                {
                    "p_user_id": user_id,
                    "p_start": three_months_ago.isoformat(),
                    "p_end": month_start.isoformat(),
                },
            ).execute()
        )
        monthly_totals = [float(row["total"]) for row in (monthly_resp.data or [])]
        avg_monthly = sum(monthly_totals) / len(monthly_totals) if monthly_totals else 0

        savings_goal = float(budget_config["saving_goal_monthly"]) if budget_config and budget_config["saving_goal_monthly"] else 0
        income = await _monthly_income(user_id)

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
            lambda: supabase_client.table("profiles").select("alert_threshold_pct").eq("id", user_id).execute()
        )
        threshold_pct = (
            float(profile_resp.data[0]["alert_threshold_pct"])
            if profile_resp.data and profile_resp.data[0].get("alert_threshold_pct") is not None
            else DEFAULT_APPROACHING_BUDGET_THRESHOLD_PCT
        )

        for crossing in await _budget_crossings(user_id, threshold_pct):
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

        # Review queue count
        review_resp = await run_query(
            lambda: supabase_client.table("transactions")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("needs_review", True)
            .execute()
        )
        review_count = review_resp.count if review_resp.count is not None else len(review_resp.data)
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
            .select("id, merchant, amount, timestamp, is_split, categories(name)")
            .eq("user_id", user_id)
            .not_.is_("category_id", "null")
            .gte("timestamp", window_start.isoformat())
        )
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
                    "merchant": txn["merchant"],
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
):
    """Detailed reports: paginated transaction list.

    Now includes uncategorized rows (so users can categorize anything from the
    table) and returns each row's `id`/`category_id` so the frontend can edit
    the category inline via POST /classify/{id}/label. Optional filters:
    `uncategorized_only`/`category_id` (mutually exclusive, as before), plus
    `search` (merchant/description substring), a `date_from`/`date_to`
    (`YYYY-MM-DD`) range, and a `min_amount`/`max_amount` range — all
    independent of each other and of the category filters, so any
    combination can apply at once.
    """
    user_id = request.state.user_id
    page = max(1, page)
    per_page = min(max(1, per_page), 500)

    try:
        start = (page - 1) * per_page
        query = (
            supabase_client.table("transactions")
            .select("id, timestamp, merchant, description, amount, category_id, categories(name), is_split, label_source",
                    count="exact")
            .eq("user_id", user_id)
        )
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

        response = await run_query(
            lambda: query
            .order("timestamp", desc=True)
            .range(start, start + per_page - 1)
            .execute()
        )

        total_count = response.count if response.count is not None else len(response.data or [])

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
                is_split = bool(txn.get("is_split"))
                if is_split:
                    n = split_counts.get(txn["id"], 0)
                    category_label = f"Split ({n})"
                else:
                    category_label = txn["categories"]["name"] if txn["categories"] else "Uncategorized"
                rows.append({
                    "id": txn["id"],
                    "date": txn["timestamp"],
                    "merchant": merchant_label_english(txn["merchant"]),
                    "description": description_label_english(txn["description"]),
                    "amount": float(txn["amount"]),
                    "category": category_label,
                    "category_id": txn["category_id"],
                    "is_split": is_split,
                    "splits": splits_by_txn.get(txn["id"], []) if is_split else None,
                    "label_source": txn["label_source"],
                })
            return rows

        # merchant/description labeling can hit a live Google Translate call
        # per untranslated string (see src/translate.py) — run the whole
        # batch off the event loop so it doesn't block other requests.
        transactions = await run_in_threadpool(build_rows)

        return {
            "transactions": transactions,
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/reports")


@router.get("/export")
@limiter.limit("10/hour")
async def export_transactions(request: Request):
    """Export all user transactions as XLSX workbook.

    Columns: Date | Merchant | Description | Category | Amount | Label source
    All text is translated to English; amounts formatted as #,##0.00
    """
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from datetime import datetime

    user_id = request.state.user_id

    try:
        def make_query():
            return (
                supabase_client.table("transactions")
                .select("id, timestamp, merchant, description, amount, category_id, categories(name), is_split, label_source")
                .eq("user_id", user_id)
                .order("timestamp", desc=True)
            )

        all_txns = await fetch_all_async(make_query)

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
        headers = ["Date", "Merchant", "Description", "Category", "Amount", "Label Source"]
        ws.append(headers)

        # Format header row
        header_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
        header_font = Font(bold=True)
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font

        # Freeze header
        ws.freeze_panes = "A2"

        # Add data rows. Building the rows can hit a live Google Translate
        # call per untranslated merchant/description (see src/translate.py)
        # over the user's ENTIRE transaction history — run the whole batch
        # off the event loop so it doesn't block other requests, then append
        # to the workbook (cheap, no network calls) back on the loop.
        def build_rows():
            return [
                [
                    txn["timestamp"],
                    merchant_label_english(txn["merchant"]),
                    description_label_english(txn["description"]),
                    f"Split ({split_counts.get(txn['id'], 0)})" if txn.get("is_split") else (txn["categories"]["name"] if txn["categories"] else "Uncategorized"),
                    float(txn["amount"]),
                    txn["label_source"] or "",
                ]
                for txn in all_txns
            ]

        for row in await run_in_threadpool(build_rows):
            ws.append(row)

        # Format amount column
        for row in ws.iter_rows(min_row=2, max_row=len(all_txns) + 1, min_col=5, max_col=5):
            for cell in row:
                cell.number_format = '#,##0.00'

        # Adjust column widths
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 30
        ws.column_dimensions['D'].width = 18
        ws.column_dimensions['E'].width = 12
        ws.column_dimensions['F'].width = 14

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
                .select("id, timestamp, merchant, description, amount, confidence, category_id, categories(name), is_split")
                .eq("user_id", user_id)
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
                .select("id, timestamp, merchant, description, amount, confidence, category_id, categories(name), is_split")
                .eq("user_id", user_id)
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
                    "merchant": merchant_label_english(txn["merchant"]),
                    "description": description_label_english(txn["description"]),
                    "amount": float(txn["amount"]),
                    "confidence": float(txn["confidence"]) if txn["confidence"] else 0,
                    "category": (("Split" if txn.get("is_split") else (txn["categories"]["name"] if txn["categories"] else None)) if show_labeled else None),
                    "suggested_category": "Split" if txn.get("is_split") else (txn["categories"]["name"] if txn["categories"] else None),
                }
                for txn in rows
            ]

        # merchant/description labeling can hit a live Google Translate call
        # per untranslated string — run the batch off the event loop.
        transactions = await run_in_threadpool(build_rows)

        return {
            "transactions": transactions,
            "count": len(transactions),
            "type": label_type,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/review-queue")


@router.get("/onboarding-status")
async def get_onboarding_status(request: Request):
    """Check user's onboarding progress."""
    user_id = request.state.user_id

    try:
        # profiles.id IS the auth user id (PK referencing auth.users)
        response = await run_query(
            lambda: supabase_client.table("profiles").select("onboarding_phase").eq("id", user_id).execute()
        )
        if not response.data:
            # 'upload' is the enum's first phase; 'signup' is not a valid value
            return {"onboarding_phase": "upload"}

        return {"onboarding_phase": response.data[0]["onboarding_phase"]}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/onboarding-status")


@router.post("/onboarding-complete")
async def complete_onboarding(request: Request):
    """Mark onboarding as complete."""
    user_id = request.state.user_id

    try:
        await run_query(
            lambda: supabase_client.table("profiles").update({
                "onboarding_phase": "complete"
            }).eq("id", user_id).execute()
        )

        return {"message": "Onboarding complete"}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/onboarding-complete")
