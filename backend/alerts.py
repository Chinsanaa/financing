"""Reactive budget-alert email check (no cron — see docs/context.md for why).

Triggered as a FastAPI BackgroundTask from backend/routes/classify.py right
after a transaction's category is durably set, so it fires shortly after
spending actually changes rather than on a schedule.
"""
from config import supabase_client
from db import run_query
from mailer import send_alert_email
from errors import logger
from routes.dashboard import _budget_crossings, _month_bounds

DEFAULT_ALERT_THRESHOLD_PCT = 80


async def check_budget_alerts(user_id: str) -> None:
    """Email newly-crossed over/approaching-budget categories for this user.

    De-duplicated via the `budget_alerts` table (unique on user_id,
    category_id, month, kind) so the same crossing is never emailed twice
    in a month, no matter how many times this fires. Never raises — a
    failure here must not affect the request that triggered it.
    """
    try:
        profile_resp = await run_query(
            lambda: supabase_client.table("profiles")
            .select("alert_email_enabled, alert_threshold_pct")
            .eq("id", user_id)
            .execute()
        )
        if not profile_resp.data or not profile_resp.data[0].get("alert_email_enabled"):
            return
        threshold_pct = float(profile_resp.data[0].get("alert_threshold_pct") or DEFAULT_ALERT_THRESHOLD_PCT)

        crossings = await _budget_crossings(user_id, threshold_pct)
        if not crossings:
            return

        month_start, _ = _month_bounds(None)
        month = month_start.date().isoformat()

        newly_crossed = []
        for crossing in crossings:
            insert_resp = await run_query(
                lambda c=crossing: supabase_client.table("budget_alerts")
                .upsert(
                    {
                        "user_id": user_id,
                        "category_id": c["category_id"],
                        "month": month,
                        "kind": c["kind"],
                    },
                    on_conflict="user_id,category_id,month,kind",
                    ignore_duplicates=True,
                )
                .execute()
            )
            if insert_resp.data:
                newly_crossed.append(crossing)

        if not newly_crossed:
            return  # every crossing was already emailed this month

        user_resp = await run_query(lambda: supabase_client.auth.admin.get_user_by_id(user_id))
        to_email = getattr(getattr(user_resp, "user", None), "email", None)
        if not to_email:
            return

        await send_alert_email(to_email, *_email_content(newly_crossed))
    except Exception as e:
        logger.exception("check_budget_alerts failed for user %s: %s", user_id, e)


def _email_content(crossings: list) -> tuple:
    subject = "Budget alert" + ("s" if len(crossings) > 1 else "")
    lines = []
    for c in crossings:
        if c["kind"] == "over":
            lines.append(
                f"{c['category']}: spent {c['current']:.2f} of {c['limit']:.2f} budget "
                f"(over by {c['overage']:.2f})"
            )
        else:
            lines.append(
                f"{c['category']}: spent {c['current']:.2f} of {c['limit']:.2f} budget "
                f"({c['pct']}% used)"
            )
    return subject, "\n".join(lines)
