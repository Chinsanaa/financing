"""Classification: classify unlabeled transactions using trained model."""
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from config import supabase_client
import pandas as pd
from pathlib import Path
import sys

router = APIRouter()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from classify import classify_all, load_model_bundle


class LabelRequest(BaseModel):
    """Request to label/recategorize a transaction."""
    category_id: str
    label_source: str = "override"


@router.post("/{transaction_id}/label")
async def label_transaction(request: Request, transaction_id: str, req: LabelRequest, bg_tasks: BackgroundTasks):
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

        # Enqueue background retrain since labels changed
        bg_tasks.add_task(queue_user_retrain, user_id)

        return {"transaction": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{transaction_id}/accept")
async def accept_model_suggestion(request: Request, transaction_id: str, bg_tasks: BackgroundTasks):
    """Accept model's category suggestion for a review queue transaction."""
    user_id = request.state.user_id

    try:
        response = supabase_client.table("transactions").update({
            "needs_review": False,
            "label_source": "model_agreed",
        }).eq("id", transaction_id).eq("user_id", user_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Transaction not found")

        bg_tasks.add_task(queue_user_retrain, user_id)

        return {"transaction": response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def queue_user_retrain(user_id: str):
    """Queue a background retrain for this user (stub for now)."""
    try:
        supabase_client.table("model_runs").insert({
            "user_id": user_id,
            "status": "queued",
            "trigger": "label_batch",
        }).execute()
    except Exception as e:
        print(f"Failed to queue retrain for user {user_id}: {e}")
