"""Shared router, FX/month helpers and constants used by more than one dashboard route group."""
from fastapi import APIRouter
from typing import Optional
import fx
from config import supabase_client
from db import run_query
from datetime import datetime, timedelta

from budget import (  # shared with alerts.py
    _month_bounds,
    _now_cn,
)

router = APIRouter()


def _months_ago_start(n: int, now: datetime = None) -> datetime:
    """First-of-month, n months before `now` (or the current month)."""
    now = now or _now_cn()
    total_months = now.year * 12 + (now.month - 1) - n
    return datetime(total_months // 12, total_months % 12 + 1, 1)


FX_LOOKBACK = timedelta(days=7)  # strict lookup: rate_date in [d - 7, d]


async def _home_currency(user_id: str) -> Optional[str]:
    return await fx.get_home_currency(user_id)


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
    return await fx.load_rates(home, start, end)


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


async def _monthly_income(user_id: str) -> float:
    """Monthly income from profiles.monthly_income (the only written source)."""
    resp = await run_query(lambda: supabase_client.table("profiles").select("monthly_income").eq("id", user_id).execute())
    if resp.data and resp.data[0].get("monthly_income") is not None:
        return float(resp.data[0]["monthly_income"])
    return 0.0
