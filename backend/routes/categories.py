"""Categories CRUD: list, create, update, delete user categories."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from config import supabase_client
from errors import internal_error

router = APIRouter()


# The categories table columns are: name, is_catch_all, sort_order, color.
# `color` is a design-system palette KEY (see frontend categoryColors.ts),
# not a hex — the frontend maps keys to theme-aware light/dark values.
# Must stay in sync with the CHECK constraint in migration
# 20260709120000_add_category_color.sql and the frontend CATEGORY_COLORS.
ALLOWED_COLORS = frozenset({
    "lime", "violet", "cyan", "pink", "amber", "sky",
    "emerald", "rose", "indigo", "teal", "orange", "fuchsia",
})


class CategoryCreate(BaseModel):
    name: str
    sort_order: Optional[int] = None
    color: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None
    color: Optional[str] = None


def _validate_color(user_id: str, color: str, exclude_id: Optional[str] = None):
    """Reject unknown palette keys and colors already used by another of the
    user's categories (the picker disables taken swatches; this is defense in
    depth — a partial unique index enforces it at the DB level too)."""
    if color not in ALLOWED_COLORS:
        raise HTTPException(status_code=400, detail="Invalid color")
    q = (
        supabase_client.table("categories")
        .select("id, name")
        .eq("user_id", user_id)
        .eq("color", color)
    )
    if exclude_id:
        q = q.neq("id", exclude_id)
    taken = q.execute().data
    if taken:
        raise HTTPException(
            status_code=400,
            detail=f"Color already used by \"{taken[0]['name']}\"",
        )


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
        row = {"user_id": user_id, "name": cat.name}
        if cat.sort_order is not None:
            row["sort_order"] = cat.sort_order
        if cat.color is not None:
            _validate_color(user_id, cat.color)
            row["color"] = cat.color
        response = supabase_client.table("categories").insert(row).execute()
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
        # `color: null` passes exclude_unset and clears the column ("Auto").
        if update_data.get("color") is not None:
            _validate_color(user_id, update_data["color"], exclude_id=category_id)
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
