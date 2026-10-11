"""Settings: account management, profile updates, account deletion."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
from config import supabase_client
from db import run_query
from errors import internal_error, logger
import fx

router = APIRouter()


class ProfileUpdate(BaseModel):
    monthly_income: Optional[float] = None
    alert_email_enabled: Optional[bool] = None
    # "Approaching budget" threshold, e.g. 80 = warn/email at 80% of a
    # category's monthly budget. "Over budget" (100%) is not configurable.
    alert_threshold_pct: Optional[float] = Field(default=None, ge=0, le=100)
    # Notification preferences (Settings > Notifications). In-app toggles
    # control GET /dashboard/action item visibility (bell + Action plan
    # tab); monthly_overview_email_enabled is preference-only today — no
    # sending logic exists yet.
    budget_inapp_enabled: Optional[bool] = None
    pending_review_inapp_enabled: Optional[bool] = None
    monthly_overview_email_enabled: Optional[bool] = None
    # Home currency (API v5 §3.2): ISO code from GET /fx/currencies, or
    # null to clear. Validated in the handler (exact 422 messages).
    home_currency: Optional[str] = None


def _normalize_home_currency(value: Optional[str]) -> Optional[str]:
    """Trim + upper-case; None clears. 'CNY' and unsupported codes → 422."""
    if value is None:
        return None
    code = value.strip().upper()
    if code == fx.BASE:
        raise HTTPException(
            status_code=422,
            detail="CNY is the base currency; clear home_currency with null instead",
        )
    if code not in fx.SUPPORTED:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported home currency '{code}'. See GET /fx/currencies.",
        )
    return code


def _with_defaults(profile: dict) -> dict:
    """v5 fields a profile row always carries (even before the migration)."""
    profile.setdefault("home_currency", None)
    return profile


class BudgetSettingsUpdate(BaseModel):
    saving_goal_monthly: Optional[float] = None
    currency: Optional[str] = None


@router.get("/profile")
async def get_profile(request: Request):
    """Get user profile (from profiles table)."""
    user_id = request.state.user_id

    try:
        response = await run_query(lambda: supabase_client.table("profiles").select("*").eq("id", user_id).execute())
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")

        return {"profile": _with_defaults(response.data[0])}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "settings/get_profile")


@router.patch("/profile")
async def update_profile(request: Request, data: ProfileUpdate):
    """Update user profile (monthly income, etc)."""
    user_id = request.state.user_id

    try:
        update_data = data.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        if "home_currency" in update_data:
            update_data["home_currency"] = _normalize_home_currency(update_data["home_currency"])
        response = await run_query(
            lambda: supabase_client.table("profiles").update(update_data).eq("id", user_id).execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")

        if update_data.get("home_currency"):
            # Contract §2 trigger 1: respond now, backfill rates in the
            # background (non-blocking, never raises).
            fx.request_backfill_for_user(user_id)

        return {"profile": _with_defaults(response.data[0])}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "settings/update_profile")


@router.patch("/budget")
async def update_budget_settings(request: Request, data: BudgetSettingsUpdate):
    """Update budget settings (savings goal, currency) in budget_config.

    Monthly income lives on profiles.monthly_income (PATCH /settings/profile);
    budget_config keeps only goal/currency to avoid a second income field.
    """
    user_id = request.state.user_id

    try:
        update_data = data.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        update_data["user_id"] = user_id
        response = await run_query(
            lambda: supabase_client.table("budget_config")
            .upsert(update_data, on_conflict="user_id")
            .execute()
        )
        return {"budget_config": response.data[0] if response.data else update_data}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "settings/update_budget_settings")


@router.delete("/account")
async def delete_account(request: Request):
    """Delete account and all associated data.

    Order: Storage (user-scoped prefix) → Auth. Deleting the auth user
    cascades through the profiles FK (ON DELETE CASCADE) to transactions,
    categories, uploads, model_runs, budget tables.
    """
    user_id = request.state.user_id

    try:
        # Step 1: Delete all Storage objects under the user's folder in every
        # bucket the app writes to. Storage list() is not recursive, so walk
        # the folder tree (model artifacts live at {user_id}/models/{run_id}/).
        for bucket_name in ('model_artifacts', 'uploads'):
            try:
                storage_client = supabase_client.storage.from_(bucket_name)
                _delete_prefix(storage_client, user_id)
            except Exception as storage_err:
                logger.warning("Storage cleanup warning (%s) for user %s: %s",
                               bucket_name, user_id, storage_err)
                # Don't fail on storage errors, proceed to Auth deletion

        # Step 2: Delete auth user (FK cascade removes all user rows)
        try:
            supabase_client.auth.admin.delete_user(user_id)
        except Exception as auth_err:
            logger.error("Failed to delete auth user %s: %s", user_id, auth_err)
            raise HTTPException(
                status_code=500,
                detail="Failed to delete authentication record"
            )

        return {"message": "Account and all associated data deleted"}

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "settings/delete_account")


def _delete_prefix(storage_client, prefix: str) -> None:
    """Recursively delete every object under `prefix/` in a bucket.

    Supabase Storage's list() returns one level: files have an 'id',
    folders don't. Recurse into folders, remove files in batches.
    """
    entries = storage_client.list(prefix) or []
    files, folders = [], []
    for entry in entries:
        name = entry.get('name')
        if not name:
            continue
        full = f"{prefix}/{name}"
        if entry.get('id'):
            files.append(full)
        else:
            folders.append(full)
    if files:
        storage_client.remove(files)
    for folder in folders:
        _delete_prefix(storage_client, folder)
