"""Classification actions on individual transactions (label / accept).

Bulk classification (rules + model inference on unlabeled rows) lives in
backend/ml.py and runs automatically after uploads and training runs.
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from config import supabase_client
from errors import internal_error

router = APIRouter()


class LabelRequest(BaseModel):
    """Request to label/recategorize a transaction."""
    category_id: str
    label_source: str = "override"


@router.post("/{transaction_id}/label")
async def label_transaction(request: Request, transaction_id: str, req: LabelRequest):
    """Label a transaction from the review queue (recategorize)."""
    user_id = request.state.user_id

    try:
        # Verify category belongs to this user
        cat_response = supabase_client.table("categories").select("id").eq("id", req.category_id).eq("user_id", user_id).execute()
        if not cat_response.data:
            raise HTTPException(status_code=404, detail="Category not found")

        # Update transaction
        response = supabase_client.table("transactions").update({
            "category_id": req.category_id,
            "label_source": req.label_source,
            "needs_review": False,
            "is_manually_labeled": True,
        }).eq("id", transaction_id).eq("user_id", user_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Transaction not found")

        return {"transaction": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "classify/label_transaction")


@router.post("/{transaction_id}/accept")
async def accept_model_suggestion(request: Request, transaction_id: str):
    """Accept model's category suggestion for a review queue transaction."""
    user_id = request.state.user_id

    try:
        response = supabase_client.table("transactions").update({
            "needs_review": False,
            "is_manually_labeled": True,
            "label_source": "model_agreed",
        }).eq("id", transaction_id).eq("user_id", user_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Transaction not found")

        return {"transaction": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "classify/accept_model_suggestion")
