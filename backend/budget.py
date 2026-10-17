"""Month windows, budget spend and budget crossings.

Shared by routes/dashboard.py (in-app budget views and actions) and alerts.py
(budget alert emails), so the two never disagree on what counts as "over" or
"approaching" a budget. Lives outside routes/ so alerts.py doesn't depend on
a route module.
"""
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from config import supabase_client
from db import run_query

# Used when profiles.alert_threshold_pct is unset (NULL). An explicit 0 is a
# valid choice ("tell me as soon as I spend anything") and is kept.
DEFAULT_ALERT_THRESHOLD_PCT = 80


def alert_threshold_pct(profile_row: Optional[dict]) -> float:
    value = (profile_row or {}).get("alert_threshold_pct")
    return float(value) if value is not None else float(DEFAULT_ALERT_THRESHOLD_PCT)


def _now_cn() -> datetime:
    """Naive China-clock 'now'. Transaction timestamps come from Alipay/WeChat
    exports in China local time and are stored naive, so month boundaries and
    cutoffs must use the same clock — not the server's (UTC on Render)."""
    return datetime.now(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)


def _month_start(now: datetime = None) -> datetime:
    now = now or _now_cn()
    return datetime(now.year, now.month, 1)


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
