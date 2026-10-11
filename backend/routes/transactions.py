"""Manual transaction entry — the Upload tab's "add expense manually" form —
and fixing a transaction's kind (expense / income / transfer).

Unlike CSV/Excel uploads, a manual entry requires the user to pick a
category directly (no ML classification pass), so every column is filled
at insert time and the row never lands in the review queue. Manual entries
are always expenses (kind='expense' via the column default).
"""
from datetime import datetime
from typing import Literal, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator, model_validator
from config import supabase_client
from translations import request_translation
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
        request_translation(user_id)

        return {"transaction": resp.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "transactions/create_manual_transaction")


# Allowed (kind, flow_subtype) pairs — contract §1.1, mirrors
# SUBTYPES_BY_KIND in frontend/src/types/v5.ts. A NULL subtype is always ok.
SUBTYPES_BY_KIND = {
    "expense": {"refund"},
    "income": {"salary", "interest", "other"},
    "transfer": {
        "p2p_transfer", "red_packet", "aa_collection", "own_account",
        "repayment", "top_up", "withdrawal", "other",
    },
}


class KindUpdate(BaseModel):
    kind: Literal["expense", "income", "transfer"]
    flow_subtype: Optional[str] = None

    @model_validator(mode="after")
    def _allowed_pair(self):
        if self.flow_subtype is not None and self.flow_subtype not in SUBTYPES_BY_KIND[self.kind]:
            raise ValueError(f"flow_subtype '{self.flow_subtype}' is not allowed for kind '{self.kind}'")
        return self


_KIND_RESPONSE_FIELDS = ("id", "kind", "flow_subtype", "category_id", "needs_review")


@router.patch("/{transaction_id}/kind")
@limiter.limit("120/hour")
async def update_transaction_kind(request: Request, transaction_id: str, body: KindUpdate):
    """Fix a parser misjudgement, e.g. rent paid by WeChat transfer
    (transfer → expense) or a large red packet that is really income.

    Amount is never changed, no merchant rule is written and nothing is
    retrained: a row that stops being an expense simply drops out of
    training, subscriptions and alerts on their next run (they all filter
    kind='expense').
    """
    user_id = request.state.user_id

    try:
        current_resp = await run_query(
            lambda: supabase_client.table("transactions")
            .select("id, kind, flow_subtype, category_id, needs_review, is_split")
            .eq("id", transaction_id).eq("user_id", user_id).execute()
        )
        if not current_resp.data:
            raise HTTPException(status_code=404, detail="Transaction not found")
        current = current_resp.data[0]

        # Splits are per-category line-items, which only expenses have.
        if current.get("is_split") and body.kind != "expense":
            raise HTTPException(status_code=409, detail="Unsplit this transaction before changing its kind")

        if current.get("kind") == body.kind and current.get("flow_subtype") == body.flow_subtype:
            return {"transaction": {k: current.get(k) for k in _KIND_RESPONSE_FIELDS}}

        update = {"kind": body.kind, "flow_subtype": body.flow_subtype}
        if body.kind != "expense":
            # Income/transfer rows are never categorized or reviewed.
            update.update({"category_id": None, "needs_review": False, "label_source": "none", "confidence": None})
        elif current.get("kind") != "expense":
            # Becomes an expense: queue it for review/classification like a
            # freshly imported row (no category yet, not user-confirmed).
            update.update({"needs_review": True, "label_source": "none", "is_manually_labeled": False})

        resp = await run_query(
            lambda: supabase_client.table("transactions")
            .update(update).eq("id", transaction_id).eq("user_id", user_id).execute()
        )
        if not resp.data:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return {"transaction": {k: resp.data[0].get(k) for k in _KIND_RESPONSE_FIELDS}}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "transactions/update_transaction_kind")
