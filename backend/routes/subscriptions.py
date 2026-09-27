"""Recurring/subscription detection: list detected merchants, confirm/dismiss.

Detection itself (src/recurring.py) is a pure pandas function; this route
fetches the user's transactions, runs detection, and upserts the result into
`recurring_merchants` (a derived cache — `transactions` stays the source of
truth, this table only adds user confirm/dismiss state on top).

Detection needs the user's whole history, so the list endpoint serves the
cached table immediately and refreshes it in the background
(stale-while-revalidate: at most one visit stale). Only a user with nothing
cached yet waits for detection inline, so a first visit is never empty.
"""
import asyncio

from fastapi import APIRouter, HTTPException, Request
import pandas as pd
from config import supabase_client
from db import fetch_all_async, run_query
from errors import internal_error, logger
from recurring import detect_recurring_merchants
from src.translate import merchant_label_stored

router = APIRouter()

# Users with a background re-detection in flight (coalesces rapid reloads),
# plus strong refs so pending tasks aren't garbage-collected mid-run.
_refreshing_users: set = set()
_background_tasks: set = set()


async def _detect_and_upsert(user_id: str) -> None:
    rows = await fetch_all_async(
        lambda: supabase_client.table("transactions")
        .select("merchant, merchant_en, amount, timestamp, category_id")
        .eq("user_id", user_id)
    )
    detected = detect_recurring_merchants(pd.DataFrame(rows))
    if detected.empty:
        return

    # Stored English translation per merchant (see backend/translations.py).
    merchant_en = {r["merchant"]: r.get("merchant_en") for r in rows if r.get("merchant_en")}
    upsert_rows = [
        {
            "user_id": user_id,
            "merchant": row["merchant"],
            "merchant_en": merchant_en.get(row["merchant"]),
            "category_id": row["category_id"],
            "cadence": row["cadence"],
            "typical_amount": row["typical_amount"],
            "last_seen": row["last_seen"].isoformat(),
        }
        for _, row in detected.iterrows()
    ]
    await run_query(
        lambda: supabase_client.table("recurring_merchants")
        .upsert(upsert_rows, on_conflict="user_id,merchant")
        .execute()
    )


async def _refresh_in_background(user_id: str) -> None:
    try:
        await _detect_and_upsert(user_id)
    except Exception as e:
        logger.warning("Background subscription detection failed for %s: %s", user_id, e)
    finally:
        _refreshing_users.discard(user_id)


def _schedule_refresh(user_id: str) -> None:
    if user_id in _refreshing_users:
        return
    _refreshing_users.add(user_id)
    task = asyncio.create_task(_refresh_in_background(user_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _cached_rows(user_id: str) -> list:
    return (
        await run_query(
            lambda: supabase_client.table("recurring_merchants")
            .select("*, categories(name)")
            .eq("user_id", user_id)
            .execute()
        )
    ).data or []


@router.get("/")
async def list_subscriptions(request: Request):
    """Detected recurring merchants for the authenticated user, plus their
    combined estimated monthly cost (weekly cadence normalized to ~4.33x)."""
    user_id = request.state.user_id
    try:
        all_rows = await _cached_rows(user_id)
        if all_rows:
            _schedule_refresh(user_id)
        else:
            await _detect_and_upsert(user_id)
            all_rows = await _cached_rows(user_id)

        # Filtered in Python rather than `.eq("is_dismissed", False)`: a
        # freshly-upserted row relies on the column's DB-side DEFAULT false,
        # which only applies once actually committed — filtering here avoids
        # any dependency on that round-trip.
        rows = sorted(
            (r for r in all_rows if not r.get("is_dismissed")),
            key=lambda r: r["typical_amount"] or 0,
            reverse=True,
        )

        monthly_total = 0.0
        for row in rows:
            multiplier = 4.33 if row["cadence"] == "weekly" else 1
            monthly_total += float(row["typical_amount"] or 0) * multiplier

        # English display name — raw merchant text can be Chinese.
        for row in rows:
            row["merchant"] = merchant_label_stored(row["merchant"], row.get("merchant_en"))

        return {
            "subscriptions": rows,
            "monthly_total": round(monthly_total, 2),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "subscriptions/list")


@router.post("/{subscription_id}/confirm")
async def confirm_subscription(request: Request, subscription_id: str):
    """Mark a detected subscription as user-confirmed (real, expected)."""
    user_id = request.state.user_id
    try:
        response = await run_query(
            lambda: supabase_client.table("recurring_merchants")
            .update({"is_confirmed": True, "updated_at": "now()"})
            .eq("id", subscription_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Subscription not found or not authorized")
        return {"subscription": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "subscriptions/confirm")


@router.post("/{subscription_id}/dismiss")
async def dismiss_subscription(request: Request, subscription_id: str):
    """Mark a detected subscription as dismissed (not actually recurring, or
    the user doesn't want it tracked). Dismissal survives re-detection since
    `_detect_and_upsert` only upserts cadence/amount/last_seen, not the
    confirm/dismiss flags."""
    user_id = request.state.user_id
    try:
        response = await run_query(
            lambda: supabase_client.table("recurring_merchants")
            .update({"is_dismissed": True, "updated_at": "now()"})
            .eq("id", subscription_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Subscription not found or not authorized")
        return {"subscription": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "subscriptions/dismiss")
