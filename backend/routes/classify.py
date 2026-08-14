"""Classification actions on individual transactions (label / accept).

Bulk classification (rules + model + LLM fallback inference on unlabeled
rows) lives in backend/ml.py and runs automatically after uploads and
training runs.
"""
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel
from alerts import check_budget_alerts
from config import supabase_client
from db import run_query
from errors import internal_error, logger
from limiter import limiter

router = APIRouter()

MAX_BULK_LABEL_TRANSACTIONS = 500


class LabelRequest(BaseModel):
    """Request to label/recategorize a transaction."""
    category_id: str
    label_source: str = "override"


class BulkLabelRequest(BaseModel):
    """Request to recategorize multiple transactions at once (Reports bulk action)."""
    transaction_ids: List[str]
    category_id: str


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


async def _label_one(user_id: str, transaction_id: str, category_id: str, label_source: str) -> Optional[dict]:
    """Fetch-before, update, and best-effort LLM-rule-promotion for a single
    transaction. Returns the updated row, or None if no matching transaction
    was found for this user. Callers are responsible for the category
    ownership check themselves — done once per request, not once per
    transaction, by both `label_transaction` and `bulk_label_transactions`.
    """
    # Fetch the current row first so we know if it was an LLM suggestion.
    before_response = await run_query(
        lambda: supabase_client.table("transactions").select("merchant, label_source").eq("id", transaction_id).eq("user_id", user_id).execute()
    )
    if not before_response.data:
        return None
    # Copy: the client may hand back a live row reference (true of the real
    # supabase-py response object too in some cases), and the update below
    # must not retroactively change what "before" saw.
    before = dict(before_response.data[0])

    response = await run_query(
        lambda: supabase_client.table("transactions").update({
            "category_id": category_id,
            "label_source": label_source,
            "needs_review": False,
            "is_manually_labeled": True,
        }).eq("id", transaction_id).eq("user_id", user_id).execute()
    )
    if not response.data:
        return None

    await _promote_llm_suggestion_to_rule(user_id, before, category_id)
    return response.data[0]


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

        updated = await _label_one(user_id, transaction_id, req.category_id, req.label_source)
        if not updated:
            raise HTTPException(status_code=404, detail="Transaction not found")

        background_tasks.add_task(check_budget_alerts, user_id)

        return {"transaction": updated}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "classify/label_transaction")


@router.post("/bulk-label")
@limiter.limit("60/hour")
async def bulk_label_transactions(request: Request, req: BulkLabelRequest, background_tasks: BackgroundTasks):
    """Recategorize multiple transactions at once (Reports bulk action).

    Reuses `_label_one`'s per-transaction fetch/update/promote sequence in a
    loop rather than a single `.in_("id", ids)` update — each transaction's
    own prior `label_source` needs fetching individually for the
    LLM-rule-promotion check to stay correct per-row.
    """
    user_id = request.state.user_id

    if not req.transaction_ids:
        raise HTTPException(status_code=400, detail="transaction_ids must not be empty")
    if len(req.transaction_ids) > MAX_BULK_LABEL_TRANSACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Too many transactions in one bulk request (max {MAX_BULK_LABEL_TRANSACTIONS})",
        )

    try:
        cat_response = await run_query(
            lambda: supabase_client.table("categories").select("id").eq("id", req.category_id).eq("user_id", user_id).execute()
        )
        if not cat_response.data:
            raise HTTPException(status_code=404, detail="Category not found")

        updated = []
        not_found = []
        for transaction_id in req.transaction_ids:
            result = await _label_one(user_id, transaction_id, req.category_id, "override")
            if result:
                updated.append(result)
            else:
                not_found.append(transaction_id)

        # One check for the whole batch, not once per transaction — already
        # de-duplicated per category/month by the budget_alerts table, so
        # queuing it N times would just be N redundant no-op re-checks.
        if updated:
            background_tasks.add_task(check_budget_alerts, user_id)

        return {"updated": updated, "not_found": not_found}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "classify/bulk_label_transactions")


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
