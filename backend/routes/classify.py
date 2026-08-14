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


class SplitItem(BaseModel):
    category_id: str
    amount: float


class SplitRequest(BaseModel):
    """Request to split a transaction's amount across multiple categories."""
    splits: List[SplitItem]


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

    Applying a plain single-category label always collapses/clears a prior
    split: any existing transaction_splits rows for this transaction are
    deleted and is_split is reset to False.
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

    await run_query(
        lambda: supabase_client.table("transaction_splits").delete().eq("transaction_id", transaction_id).eq("user_id", user_id).execute()
    )

    response = await run_query(
        lambda: supabase_client.table("transactions").update({
            "category_id": category_id,
            "label_source": label_source,
            "needs_review": False,
            "is_manually_labeled": True,
            "is_split": False,
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


@router.post("/{transaction_id}/split")
@limiter.limit("60/hour")
async def split_transaction(request: Request, transaction_id: str, req: SplitRequest, background_tasks: BackgroundTasks):
    """Split a transaction's amount across multiple categories.

    Validates: at least 2 split entries, no duplicate category_id, every
    category_id belongs to this user, and the split amounts sum to the
    transaction's own amount (within 0.01, same sign convention as
    transactions.amount — see src/parse.py). On success: replaces any
    existing splits, clears the transaction's own category_id, and sets
    is_split=True. Does NOT run _promote_llm_suggestion_to_rule — ambiguous
    which category to promote from a multi-category split.
    """
    user_id = request.state.user_id

    try:
        if len(req.splits) < 2:
            raise HTTPException(status_code=400, detail="A split requires at least 2 categories")

        category_ids = [s.category_id for s in req.splits]
        if len(set(category_ids)) != len(category_ids):
            raise HTTPException(status_code=400, detail="Duplicate category in split")

        txn_resp = await run_query(
            lambda: supabase_client.table("transactions").select("amount").eq("id", transaction_id).eq("user_id", user_id).execute()
        )
        if not txn_resp.data:
            raise HTTPException(status_code=404, detail="Transaction not found")
        txn_amount = float(txn_resp.data[0]["amount"])

        cat_resp = await run_query(
            lambda: supabase_client.table("categories").select("id").eq("user_id", user_id).in_("id", category_ids).execute()
        )
        owned_ids = {c["id"] for c in (cat_resp.data or [])}
        if owned_ids != set(category_ids):
            raise HTTPException(status_code=404, detail="Category not found")

        total = sum(s.amount for s in req.splits)
        if abs(total - txn_amount) >= 0.01:
            raise HTTPException(status_code=400, detail="Split amounts must sum to the transaction amount")

        await run_query(
            lambda: supabase_client.table("transaction_splits").delete().eq("transaction_id", transaction_id).eq("user_id", user_id).execute()
        )
        await run_query(
            lambda: supabase_client.table("transaction_splits").insert([
                {"user_id": user_id, "transaction_id": transaction_id, "category_id": s.category_id, "amount": s.amount}
                for s in req.splits
            ]).execute()
        )
        response = await run_query(
            lambda: supabase_client.table("transactions").update({
                "category_id": None,
                "is_split": True,
                "needs_review": False,
                "is_manually_labeled": True,
                "label_source": "override",
            }).eq("id", transaction_id).eq("user_id", user_id).execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Transaction not found")

        background_tasks.add_task(check_budget_alerts, user_id)

        return {"transaction": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "classify/split_transaction")


@router.delete("/{transaction_id}/split")
@limiter.limit("60/hour")
async def unsplit_transaction(request: Request, transaction_id: str):
    """Remove a transaction's splits; it goes back to needing review (no
    fallback category is guessed)."""
    user_id = request.state.user_id

    try:
        await run_query(
            lambda: supabase_client.table("transaction_splits").delete().eq("transaction_id", transaction_id).eq("user_id", user_id).execute()
        )
        response = await run_query(
            lambda: supabase_client.table("transactions").update({
                "category_id": None,
                "is_split": False,
                "needs_review": True,
            }).eq("id", transaction_id).eq("user_id", user_id).execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return {"transaction": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "classify/unsplit_transaction")


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
