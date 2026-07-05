"""Classification: classify unlabeled transactions using trained model."""
from fastapi import APIRouter, HTTPException, Request
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


class ClassifyRequest(BaseModel):
    """Request to classify unlabeled transactions."""
    limit: Optional[int] = 100


class ClassifyResult(BaseModel):
    """Single classified transaction."""
    transaction_id: str
    merchant: str
    description: str
    amount: float
    category: str
    confidence: float
    label_source: str
    needs_review: bool


@router.post("/")
async def classify_transactions(request: Request, req: ClassifyRequest):
    """Classify unlabeled transactions (labeled=False) using trained model.

    Returns top N predictions sorted by needs_review (review-first).
    """
    user_id = request.state.user_id

    try:
        # Fetch unlabeled transactions
        response = supabase_client.table("transactions").select("*").eq("user_id", user_id).eq("labeled", False).limit(req.limit).execute()
        if not response.data:
            return {"transactions": [], "count": 0}

        df = pd.DataFrame(response.data)

        # Load trained model artifacts
        bundle = load_model_bundle()
        if bundle.classifier is None:
            raise HTTPException(status_code=400, detail="No trained model found. Train first.")

        # Fetch user's categories
        categories_response = supabase_client.table("categories").select("name").eq("user_id", user_id).execute()
        user_categories = [cat['name'] for cat in categories_response.data] if categories_response.data else ['Other']

        # Classify with user's categories
        df_classified = classify_all(
            df,
            bundle=bundle,
            valid_categories=user_categories,
            catch_all='Other'
        )

        # Sort by needs_review (True first) then by confidence descending
        df_classified['sort_key'] = df_classified['needs_review'].astype(int) * -1 + df_classified['confidence']
        df_classified = df_classified.sort_values('sort_key', ascending=False)

        results = [
            ClassifyResult(
                transaction_id=row.get('id'),
                merchant=row.get('merchant', ''),
                description=row.get('description', ''),
                amount=float(row.get('amount', 0)),
                category=row.get('category', 'Other'),
                confidence=float(row.get('confidence', 0)),
                label_source=row.get('label_source', 'none'),
                needs_review=bool(row.get('needs_review', True)),
            )
            for _, row in df_classified.iterrows()
        ]

        return {"transactions": results, "count": len(results)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{transaction_id}")
async def accept_classification(request: Request, transaction_id: str):
    """Accept a classification suggestion (mark as labeled)."""
    user_id = request.state.user_id

    try:
        response = supabase_client.table("transactions").update({
            "labeled": True,
            "label_source": "accepted_model"
        }).eq("id", transaction_id).eq("user_id", user_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Transaction not found")

        return {"transaction": response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{transaction_id}/override")
async def override_classification(request: Request, transaction_id: str, category: str):
    """Override a classification with a manual label."""
    user_id = request.state.user_id

    try:
        response = supabase_client.table("transactions").update({
            "category": category,
            "labeled": True,
            "label_source": "manual_override"
        }).eq("id", transaction_id).eq("user_id", user_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Transaction not found")

        return {"transaction": response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
