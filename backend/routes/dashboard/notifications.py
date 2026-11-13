"""Dashboard route group: notifications."""
from fastapi import HTTPException, Request
from config import supabase_client
from db import run_query
from errors import internal_error
from datetime import datetime, timedelta, timezone

from ._shared import router

def _parse_utc(ts: str) -> datetime:
    """Parse a `timestamp with time zone` column's ISO string into an
    aware UTC datetime — for comparing against `datetime.now(timezone.utc)`
    (never `_now_cn()`, which is naive and on a different clock)."""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


WELCOME_WINDOW = timedelta(hours=48)


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
