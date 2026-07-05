"""Settings: account management, profile updates, account deletion."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from config import supabase_client

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/profile")
async def update_profile(request: Request, data: ProfileUpdate):
    """Update user profile (monthly income, etc)."""
    user_id = request.state.user_id

    try:
        update_data = data.dict(exclude_unset=True)
        response = supabase_client.table("profiles").update(update_data).eq("id", user_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")

        return {"profile": response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/account")
async def delete_account(request: Request):
    """Delete account and all associated data.

    Order: Storage (user-scoped prefix) → Auth (cascades through RLS to all user tables).
    """
    user_id = request.state.user_id

    try:
        # Step 1: Delete all files from Storage under user_id/* prefix, in
        # every bucket the app actually writes to.
        # This prevents orphaned Storage objects if Auth delete fails
        for bucket_name in ('model_artifacts', 'uploads'):
            try:
                storage_client = supabase_client.storage.from_(bucket_name)
                # List all files under user_id/
                response = storage_client.list(f"{user_id}/")
                # Delete each file
                for file_obj in response:
                    storage_client.remove([f"{user_id}/{file_obj['name']}"])
            except Exception as storage_err:
                print(f"Storage cleanup warning ({bucket_name}) for user {user_id}: {storage_err}")
                # Don't fail on storage errors, proceed to Auth deletion

        # Step 2: Delete auth user (cascades through RLS to profiles, transactions, categories, etc)
        try:
            supabase_client.auth.admin.delete_user(user_id)
        except Exception as auth_err:
            # If auth delete fails, at least user data is deleted from Storage
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete authentication record: {str(auth_err)}"
            )

        return {"message": "Account and all associated data deleted"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
