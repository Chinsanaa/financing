"""Dashboard route group: tour."""
from fastapi import HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from config import supabase_client
from db import run_query
from errors import internal_error
from datetime import datetime, timezone

from ._shared import router

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
