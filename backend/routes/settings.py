"""Settings: account management, profile updates, account deletion."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from config import supabase_client
from errors import internal_error, logger

router = APIRouter()


class ProfileUpdate(BaseModel):
    monthly_income: Optional[float] = None


@router.get("/profile")
async def get_profile(request: Request):
    """Get user profile (from profiles table)."""
    user_id = request.state.user_id

    try:
        response = supabase_client.table("profiles").select("*").eq("id", user_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")

        return {"profile": response.data[0]}
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
        response = supabase_client.table("profiles").update(update_data).eq("id", user_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")

        return {"profile": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "settings/update_profile")


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
