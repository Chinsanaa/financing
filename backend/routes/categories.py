"""Categories CRUD: list, create, update, delete user categories."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from config import supabase_client
from errors import internal_error

router = APIRouter()


class CategoryCreate(BaseModel):
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


@router.get("/")
async def list_categories(request: Request):
    """List all categories for the authenticated user."""
    user_id = request.state.user_id
    try:
        response = (
            supabase_client.table("categories")
            .select("*")
            .eq("user_id", user_id)
            .order("name")
            .execute()
        )
        return {"categories": response.data}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "categories/list")


@router.post("/")
async def create_category(request: Request, cat: CategoryCreate):
    """Create a new category for the authenticated user."""
    user_id = request.state.user_id
    try:
        response = supabase_client.table("categories").insert({
            "user_id": user_id,
            "name": cat.name,
            "icon": cat.icon,
            "color": cat.color,
        }).execute()
        return {"category": response.data[0] if response.data else None}
    except HTTPException:
        raise
    except Exception as e:
        # Most likely a duplicate name (unique constraint)
        raise HTTPException(status_code=400, detail="Could not create category (does it already exist?)")


@router.put("/{category_id}")
async def update_category(request: Request, category_id: str, cat: CategoryUpdate):
    """Update a category (user can only update their own)."""
    user_id = request.state.user_id
    try:
        update_data = cat.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        response = supabase_client.table("categories").update(update_data).eq("id", category_id).eq("user_id", user_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Category not found or not authorized")
        return {"category": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "categories/update")


@router.delete("/{category_id}")
async def delete_category(request: Request, category_id: str):
    """Delete a category (user can only delete their own).

    A database trigger reassigns any transactions in this category to the
    user's catch-all category. Retraining stays explicit (Training tab) —
    the old auto-"queue" here only inserted model_runs rows that nothing
    ever consumed.
    """
    user_id = request.state.user_id
    try:
        response = supabase_client.table("categories").delete().eq("id", category_id).eq("user_id", user_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Category not found or not authorized")
        return {"message": "Category deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "categories/delete")
