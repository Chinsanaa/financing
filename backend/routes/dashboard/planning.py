"""Dashboard route group: planning."""
import asyncio
from fastapi import HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from config import supabase_client
from db import fetch_all_async, run_query
from errors import internal_error
from datetime import date
from src.categories import CATEGORY_BUCKET

from budget import (  # shared with alerts.py
    _budget_crossings,
    _month_bounds,
    _month_start,
    _now_cn,
    _spend_by_category,
    alert_threshold_pct,
)
from ._shared import router, _home_currency, _load_rates, _monthly_income, _months_ago_start, _r2, _reference_rate, _strict_sum

async def _budget_config(user_id: str):
    resp = await run_query(lambda: supabase_client.table("budget_config").select("*").eq("user_id", user_id).execute())
    return resp.data[0] if resp.data else None


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
        threshold_pct = alert_threshold_pct(profile_row)
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
