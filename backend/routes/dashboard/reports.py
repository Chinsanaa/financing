"""Dashboard route group: reports."""
import asyncio
from fastapi import HTTPException, Request
from typing import Optional
import fx
from config import supabase_client
from db import fetch_all_async, run_query
from errors import internal_error
from limiter import limiter
from datetime import date, datetime
from src.translate import merchant_label_stored, description_label_stored
from translations import request_translation_if_missing
from src.categories import CATEGORY_BUCKET

from ._shared import router, _home_currency, _load_rates

# ── Transaction kinds & home currency (API v5) ──────────────────────────
# "Spend" is always kind='expense' (refunds are negative expense rows).
# Income/transfer rows exist since parser v2; they only show up in cash
# flow, reports (kind filter) and the export.
KINDS = ("expense", "income", "transfer")
KIND_LABELS = {"expense": "Expense", "income": "Income", "transfer": "Transfer"}
# Same English labels as FLOW_SUBTYPE_LABELS in frontend/src/types/v5.ts.
FLOW_SUBTYPE_LABELS = {
    "refund": "Refund",
    "red_packet": "Red packet",
    "p2p_transfer": "Transfer to/from a person",
    "aa_collection": "Split-bill collection",
    "salary": "Salary",
    "interest": "Interest",
    "own_account": "Between own accounts",
    "repayment": "Credit repayment",
    "top_up": "Top-up",
    "withdrawal": "Withdrawal",
    "other": "Other",
}


def _row_day(ts: str) -> date:
    """Calendar date of a transaction row — ("timestamp" AT TIME ZONE 'UTC')::date."""
    return fx.row_date(ts)


_SEARCH_STRIP = str.maketrans("", "", ',%()":*\\')


def _sanitize_search(search: str) -> str:
    """Remove characters that are structural in a PostgREST `or=(...)` filter.
    `.` is kept: it only separates column/operator/value, and the value of an
    `ilike` clause is everything after the 2nd dot up to the next `,` (which
    is stripped), so a dot inside the value cannot end the clause."""
    return search.translate(_SEARCH_STRIP)


@router.get("/reports")
async def get_reports(
    request: Request,
    page: int = 1,
    per_page: int = 100,
    uncategorized_only: bool = False,
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    sort_by: Optional[str] = "date",
    sort_dir: Optional[str] = "desc",
    bucket: Optional[str] = None,
    kind: Optional[str] = "expense",
):
    """Detailed reports: paginated transaction list.

    `kind` (`expense` default | `income` | `transfer` | `all`; anything else
    → `expense`) picks which transaction kinds are listed, so the v4
    Reports tab (no `kind`) is unchanged. Category, bucket and
    uncategorized filters only match expense rows: combined with
    `income`/`transfer` they return an empty page, and with `all` they
    restrict to expense rows. Each row carries `kind`, `flow_subtype`,
    `source` and `amount_home` (per-row conversion, or null).

    Now includes uncategorized rows (so users can categorize anything from the
    table) and returns each row's `id`/`category_id` so the frontend can edit
    the category inline via POST /classify/{id}/label. Optional filters:
    `uncategorized_only`/`category_id` (mutually exclusive, as before), plus
    `search` (merchant/description substring), a `date_from`/`date_to`
    (`YYYY-MM-DD`) range, and a `min_amount`/`max_amount` range — all
    independent of each other and of the category filters, so any
    combination can apply at once. `sort_by` (`date`/`category`) and
    `sort_dir` (`asc`/`desc`) control ordering; unrecognized values fall back
    to the defaults (date, newest first) rather than erroring. `bucket`
    (`Need`/`Want`/`Savings`) filters to categories in that CATEGORY_BUCKET
    group (see the 50/30/20 endpoint below for what that mapping is/isn't);
    unrecognized values are ignored rather than erroring.
    """
    user_id = request.state.user_id
    page = max(1, page)
    per_page = min(max(1, per_page), 500)
    if sort_by not in ("date", "category"):
        sort_by = "date"
    if sort_dir not in ("asc", "desc"):
        sort_dir = "desc"
    if bucket not in ("Need", "Want", "Savings"):
        bucket = None
    if kind not in KINDS + ("all",):
        kind = "expense"

    try:
        async def empty_page():
            return {"transactions": [], "total_count": 0, "page": page, "per_page": per_page,
                    "kind": kind, "currency_home": await _home_currency(user_id)}

        expense_only_filter = uncategorized_only or bool(category_id) or bool(bucket)
        if expense_only_filter and kind in ("income", "transfer"):
            return await empty_page()  # non-expense rows have no category at all

        start = (page - 1) * per_page
        query = (
            supabase_client.table("transactions")
            .select("id, timestamp, merchant, description, merchant_en, description_en, amount, category_id, categories(name), is_split, label_source, kind, flow_subtype, source",
                    count="exact")
            .eq("user_id", user_id)
        )
        if kind != "all":
            query = query.eq("kind", kind)
        elif expense_only_filter:
            query = query.eq("kind", "expense")
        if uncategorized_only:
            query = query.is_("category_id", "null")
        elif category_id:
            query = query.eq("category_id", category_id)
        if search:
            escaped = _sanitize_search(search)
            query = query.or_(f"merchant.ilike.%{escaped}%,description.ilike.%{escaped}%")
        for label, value in (("date_from", date_from), ("date_to", date_to)):
            if value:
                try:
                    date.fromisoformat(value)
                except ValueError:
                    raise HTTPException(
                        status_code=422,
                        detail=f"{label} must be an ISO date (YYYY-MM-DD)",
                    )
        if date_from:
            query = query.gte("timestamp", date_from)
        if date_to:
            query = query.lt("timestamp", date_to)
        if min_amount is not None:
            query = query.gte("amount", min_amount)
        if max_amount is not None:
            query = query.lte("amount", max_amount)

        if bucket:
            bucket_category_names = [name for name, b in CATEGORY_BUCKET.items() if b == bucket]
            bucket_cat_resp = await run_query(
                lambda: supabase_client.table("categories")
                .select("id")
                .eq("user_id", user_id)
                .in_("name", bucket_category_names)
                .execute()
            )
            bucket_category_ids = [c["id"] for c in (bucket_cat_resp.data or [])]
            if not bucket_category_ids:
                # None of this user's categories fall in the requested bucket —
                # short-circuit rather than pass an empty list to .in_().
                return await empty_page()
            query = query.in_("category_id", bucket_category_ids)

        if sort_by == "category":
            query = query.order("name", desc=(sort_dir == "desc"), foreign_table="categories")
        else:
            query = query.order("timestamp", desc=(sort_dir != "asc"))

        response, home = await asyncio.gather(
            run_query(
                lambda: query
                .range(start, start + per_page - 1)
                .execute()
            ),
            _home_currency(user_id),
        )

        total_count = response.count if response.count is not None else len(response.data or [])

        # Per-row home amounts: one rate read covering this page's dates.
        row_days = {t["id"]: _row_day(t["timestamp"]) for t in (response.data or []) if t.get("timestamp")}
        rates = await _load_rates(home, list(row_days.values())) if home and row_days else None

        def amount_home(txn) -> Optional[float]:
            day = row_days.get(txn["id"])
            rate = rates.strict(day) if rates is not None and day is not None else None
            return round(float(txn["amount"]) * rate, 2) if rate is not None else None

        split_txn_ids = [t["id"] for t in (response.data or []) if t.get("is_split")]
        splits_by_txn: dict = {}
        split_counts: dict = {}
        if split_txn_ids:
            split_resp = await run_query(
                lambda: supabase_client.table("transaction_splits")
                .select("transaction_id, category_id, amount, categories(name)")
                .in_("transaction_id", split_txn_ids)
                .execute()
            )
            for row in (split_resp.data or []):
                tid = row["transaction_id"]
                splits_by_txn.setdefault(tid, []).append({
                    "category_id": row["category_id"],
                    "category_name": row["categories"]["name"] if row["categories"] else "Unknown",
                    "amount": float(row["amount"]),
                })
                split_counts[tid] = split_counts.get(tid, 0) + 1

        def build_rows():
            rows = []
            for txn in (response.data or []):
                txn_kind = txn.get("kind") or "expense"
                is_expense = txn_kind == "expense"
                is_split = is_expense and bool(txn.get("is_split"))
                category_name = txn["categories"]["name"] if txn["categories"] and is_expense else None
                if not is_expense:
                    category_label = KIND_LABELS[txn_kind]  # "Income" / "Transfer"
                elif is_split:
                    n = split_counts.get(txn["id"], 0)
                    category_label = f"Split ({n})"
                else:
                    category_label = category_name or "Uncategorized"
                rows.append({
                    "id": txn["id"],
                    "date": txn["timestamp"],
                    "merchant": merchant_label_stored(txn["merchant"], txn.get("merchant_en")),
                    "description": description_label_stored(txn["description"], txn.get("description_en")),
                    "amount": float(txn["amount"]),
                    "category": category_label,
                    "category_id": txn["category_id"] if is_expense else None,
                    "is_split": is_split,
                    "splits": splits_by_txn.get(txn["id"], []) if is_split else None,
                    "label_source": txn["label_source"],
                    # No single bucket for a split (spans categories) or an
                    # uncategorized row (no category at all); custom
                    # categories not in CATEGORY_BUCKET also fall back to None.
                    "bucket": None if is_split or category_name is None else CATEGORY_BUCKET.get(category_name),
                    "kind": txn_kind,
                    "flow_subtype": txn.get("flow_subtype"),
                    "source": txn.get("source"),
                    "amount_home": amount_home(txn),
                })
            return rows

        # Labels come from stored translations (no network); rows still
        # missing one get filled in the background for the next load.
        request_translation_if_missing(user_id, response.data or [])
        transactions = build_rows()

        return {
            "transactions": transactions,
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
            "kind": kind,
            "currency_home": home,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/reports")


@router.get("/export")
@limiter.limit("10/hour")
async def export_transactions(request: Request):
    """Export all user transactions as XLSX workbook.

    Every kind is exported. Columns:
    Date | Merchant | Description | Category | Kind | Amount | Home amount |
    Home currency | Label Source
    All text is translated to English; Amount and Home amount are formatted
    as #,##0.00. Category is empty for income/transfer rows; Home amount is
    an empty cell when no rate (or no home currency) exists.
    """
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    user_id = request.state.user_id

    try:
        def make_query():
            return (
                supabase_client.table("transactions")
                .select("id, timestamp, merchant, description, merchant_en, description_en, amount, category_id, categories(name), is_split, label_source, kind, flow_subtype")
                .eq("user_id", user_id)
                .order("timestamp", desc=True)
            )

        all_txns, home = await asyncio.gather(fetch_all_async(make_query), _home_currency(user_id))

        row_days = {t["id"]: _row_day(t["timestamp"]) for t in all_txns if t.get("timestamp")}
        rates = await _load_rates(home, list(row_days.values())) if home and row_days else None

        def amount_home(txn):
            day = row_days.get(txn["id"])
            rate = rates.strict(day) if rates is not None and day is not None else None
            return round(float(txn["amount"]) * rate, 2) if rate is not None else None

        def kind_label(txn) -> str:
            label = KIND_LABELS.get(txn.get("kind") or "expense", "Expense")
            subtype = txn.get("flow_subtype")
            return f"{label} ({FLOW_SUBTYPE_LABELS.get(subtype, subtype)})" if subtype else label

        def category_label(txn) -> str:
            if (txn.get("kind") or "expense") != "expense":
                return ""
            if txn.get("is_split"):
                return f"Split ({split_counts.get(txn['id'], 0)})"
            return txn["categories"]["name"] if txn["categories"] else "Uncategorized"

        split_counts_resp = await run_query(
            lambda: supabase_client.table("transaction_splits")
            .select("transaction_id")
            .eq("user_id", user_id)
            .execute()
        )
        split_counts: dict = {}
        for row in (split_counts_resp.data or []):
            split_counts[row["transaction_id"]] = split_counts.get(row["transaction_id"], 0) + 1

        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Transactions"

        # Headers
        headers = ["Date", "Merchant", "Description", "Category", "Kind", "Amount",
                   "Home amount", "Home currency", "Label Source"]
        ws.append(headers)

        # Format header row
        header_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
        header_font = Font(bold=True)
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font

        # Freeze header
        ws.freeze_panes = "A2"

        # Add data rows (labels from stored translations — no network).
        def _fmt_date(ts):
            if not ts:
                return ""
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y/%m/%d")

        def build_rows():
            return [
                [
                    _fmt_date(txn["timestamp"]),
                    merchant_label_stored(txn["merchant"], txn.get("merchant_en")),
                    description_label_stored(txn["description"], txn.get("description_en")),
                    category_label(txn),
                    kind_label(txn),
                    float(txn["amount"]),
                    amount_home(txn),  # None → empty cell
                    home or "",
                    txn["label_source"] or "",
                ]
                for txn in all_txns
            ]

        request_translation_if_missing(user_id, all_txns)
        for row in build_rows():
            ws.append(row)

        # Format the Amount (F) and Home amount (G) columns
        for row in ws.iter_rows(min_row=2, max_row=len(all_txns) + 1, min_col=6, max_col=7):
            for cell in row:
                cell.number_format = '#,##0.00'

        # Adjust column widths
        for col, width in zip("ABCDEFGHI", (12, 20, 30, 18, 26, 12, 14, 14, 14)):
            ws.column_dimensions[col].width = width

        # Write to bytes
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        # Return as attachment
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=transactions_{now}.xlsx"}
        )
    except Exception as e:
        raise internal_error(e, "dashboard/export")


@router.get("/review-queue")
async def get_review_queue(request: Request, show_labeled: bool = False):
    """Transactions needing review.

    By default (show_labeled=False): model suggestions with needs_review=True,
    sorted by confidence (lowest first — least confident suggestions).

    When show_labeled=True: manually labeled transactions (is_manually_labeled=True),
    so user can audit their own labels and catch human errors. Useful for catching
    accidental miscategorizations before retraining.
    """
    user_id = request.state.user_id

    try:
        if show_labeled:
            # Show manually labeled transactions for user review/correction
            response = await run_query(
                lambda: supabase_client.table("transactions")
                .select("id, timestamp, merchant, description, merchant_en, description_en, amount, confidence, category_id, categories(name), is_split")
                .eq("user_id", user_id)
                # A row re-kinded to income/transfer keeps its old
                # is_manually_labeled flag but has no category any more.
                .eq("kind", "expense")
                .eq("is_manually_labeled", True)
                .order("timestamp", desc=True)  # Most recent labels first
                .limit(50)
                .execute()
            )
            label_type = "manually_labeled"
            rows = response.data or []
        else:
            # Show model suggestions needing review. Pull a larger pool than we
            # need, then dedupe by merchant in Python (PostgREST has no
            # DISTINCT ON) so a handful of high-volume merchants don't flood
            # the queue — unique merchants make better labeling coverage.
            pool = await run_query(
                lambda: supabase_client.table("transactions")
                .select("id, timestamp, merchant, description, merchant_en, description_en, amount, confidence, category_id, categories(name), is_split")
                .eq("user_id", user_id)
                .eq("kind", "expense")
                .eq("needs_review", True)
                .order("confidence")  # Least confident first
                .limit(500)
                .execute()
            )
            label_type = "model_suggestion"

            seen_merchants: set = set()
            rows = []
            for txn in pool.data or []:
                if txn["merchant"] in seen_merchants:
                    continue
                seen_merchants.add(txn["merchant"])
                rows.append(txn)
                if len(rows) >= 50:
                    break

        if not rows:
            return {"transactions": [], "count": 0, "type": label_type}

        # In suggestion mode the row's category_id IS the model's suggestion —
        # report it only as suggested_category so the UI can distinguish
        # "this is what it's labeled" from "this is what the model proposes".
        def build_rows():
            return [
                {
                    "id": txn["id"],
                    "date": txn["timestamp"],
                    "merchant": merchant_label_stored(txn["merchant"], txn.get("merchant_en")),
                    "description": description_label_stored(txn["description"], txn.get("description_en")),
                    "amount": float(txn["amount"]),
                    "confidence": float(txn["confidence"]) if txn["confidence"] else 0,
                    "category": (("Split" if txn.get("is_split") else (txn["categories"]["name"] if txn["categories"] else None)) if show_labeled else None),
                    "suggested_category": "Split" if txn.get("is_split") else (txn["categories"]["name"] if txn["categories"] else None),
                }
                for txn in rows
            ]

        request_translation_if_missing(user_id, rows)
        transactions = build_rows()

        return {
            "transactions": transactions,
            "count": len(transactions),
            "type": label_type,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "dashboard/review-queue")
