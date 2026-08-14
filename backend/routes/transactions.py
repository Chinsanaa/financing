"""Manual transaction entry — the Upload tab's "add expense manually" form.

Unlike CSV/Excel uploads, a manual entry requires the user to pick a
category directly (no ML classification pass), so every column is filled
at insert time and the row never lands in the review queue.
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator
from config import supabase_client
from db import run_query
from errors import internal_error
from limiter import limiter

router = APIRouter()


class ManualTransactionCreate(BaseModel):
    timestamp: datetime
    merchant: str
    description: str
    amount: float
    category_id: str

    @field_validator("merchant", "description", "category_id")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("amount")
    @classmethod
    def _positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return round(v, 2)


@router.post("/")
@limiter.limit("60/hour")
async def create_manual_transaction(request: Request, body: ManualTransactionCreate):
    """Insert a single manually-entered expense."""
    user_id = request.state.user_id

    try:
        cat_resp = await run_query(
            lambda: supabase_client.table("categories")
            .select("id").eq("id", body.category_id).eq("user_id", user_id).execute()
        )
        if not cat_resp.data:
            raise HTTPException(status_code=404, detail="Category not found")

        row = {
            "user_id": user_id,
            "timestamp": body.timestamp.isoformat(),
            "merchant": body.merchant,
            "description": body.description,
            "amount": body.amount,
            "source": "manual",
            "category_id": body.category_id,
            "label_source": "override",
            "needs_review": False,
            "is_manually_labeled": True,
            "upload_id": None,
        }
        resp = await run_query(
            lambda: supabase_client.table("transactions").insert(row).execute()
        )
        if not resp.data:
            raise HTTPException(status_code=500, detail="Failed to create transaction")

        return {"transaction": resp.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "transactions/create_manual_transaction")
