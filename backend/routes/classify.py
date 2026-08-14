"""Classification actions on individual transactions (label / accept).

Bulk classification (rules + model + LLM fallback inference on unlabeled
rows) lives in backend/ml.py and runs automatically after uploads and
training runs.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel
from alerts import check_budget_alerts
from config import supabase_client
from db import run_query
from errors import internal_error, logger
from limiter import limiter

router = APIRouter()


class LabelRequest(BaseModel):
    """Request to label/recategorize a transaction."""
    category_id: str
    label_source: str = "override"


async def _promote_llm_suggestion_to_rule(user_id: str, transaction: dict, category_id: str) -> None:
    """When a user confirms a transaction that was an LLM suggestion
    (label_source == 'llm'), write it back as a per-user merchant rule.

    This is the "generalization" loop: the next transaction from this exact
    merchant hits the fast, free, trusted rule path instead of calling the
    LLM again. Best-effort — a failure here (e.g. a duplicate pattern) must
    never block the label/accept action itself.
    """
    if transaction.get("label_source") != "llm":
        return
    merchant = str(transaction.get("merchant") or "").strip().lower()
    if not merchant:
        return
    try:
        cat_resp = await run_query(
            lambda: supabase_client.table("categories").select("name").eq("id", category_id).eq("user_id", user_id).execute()
        )
        if not cat_resp.data:
            return
        category_name = cat_resp.data[0]["name"]
        await run_query(
            lambda: supabase_client.table("merchant_rules").insert({
                "user_id": user_id,
                "merchant_pattern": merchant,
                "category_name": category_name,
                "source": "llm_confirmed",
            }).execute()
        )
    except Exception as e:
        logger.warning("Failed to promote LLM suggestion to a rule for user %s: %s", user_id, e)


@router.post("/{transaction_id}/label")
@limiter.limit("60/hour")
async def label_transaction(request: Request, transaction_id: str, req: LabelRequest, background_tasks: BackgroundTasks):
    """Label a transaction from the review queue (recategorize)."""
    user_id = request.state.user_id

    try:
        # Verify category belongs to this user
        cat_response = await run_query(
            lambda: supabase_client.table("categories").select("id").eq("id", req.category_id).eq("user_id", user_id).execute()
        )
        if not cat_response.data:
            raise HTTPException(status_code=404, detail="Category not found")

        # Fetch the current row first so we know if it was an LLM suggestion.
        before_response = await run_query(
            lambda: supabase_client.table("transactions").select("merchant, label_source").eq("id", transaction_id).eq("user_id", user_id).execute()
        )
        if not before_response.data:
            raise HTTPException(status_code=404, detail="Transaction not found")
        # Copy: the client may hand back a live row reference (true of the
        # real supabase-py response object too in some cases), and the
        # update below must not retroactively change what "before" saw.
        before = dict(before_response.data[0])

        # Update transaction
        response = await run_query(
            lambda: supabase_client.table("transactions").update({
                "category_id": req.category_id,
                "label_source": req.label_source,
                "needs_review": False,
                "is_manually_labeled": True,
            }).eq("id", transaction_id).eq("user_id", user_id).execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Transaction not found")

        await _promote_llm_suggestion_to_rule(user_id, before, req.category_id)
        background_tasks.add_task(check_budget_alerts, user_id)

        return {"transaction": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "classify/label_transaction")


@router.post("/{transaction_id}/accept")
@limiter.limit("60/hour")
async def accept_model_suggestion(request: Request, transaction_id: str, background_tasks: BackgroundTasks):
    """Accept the model's or LLM's category suggestion for a review queue
    transaction."""
    user_id = request.state.user_id

    try:
        before_response = await run_query(
            lambda: supabase_client.table("transactions").select("merchant, label_source, category_id").eq("id", transaction_id).eq("user_id", user_id).execute()
        )
        if not before_response.data:
            raise HTTPException(status_code=404, detail="Transaction not found")
        before = dict(before_response.data[0])
        # Keep 'llm' as the recorded source when accepting an LLM suggestion
        # (it's a confirmation, not a model agreement) — needs_review=False
        # is what marks it as settled either way.
        confirmed_label_source = "llm" if before.get("label_source") == "llm" else "model_agreed"

        response = await run_query(
            lambda: supabase_client.table("transactions").update({
                "needs_review": False,
                "is_manually_labeled": True,
                "label_source": confirmed_label_source,
            }).eq("id", transaction_id).eq("user_id", user_id).execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Transaction not found")

        if before.get("category_id"):
            await _promote_llm_suggestion_to_rule(user_id, before, before["category_id"])
        background_tasks.add_task(check_budget_alerts, user_id)

        return {"transaction": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "classify/accept_model_suggestion")
