"""File upload and parsing: accept CSV/Excel, normalize to common schema.

API v5 (docs/contracts/API_V5.md §1.4, §3.9): the v2 parser keeps every
settled row with a `kind` (expense / income / transfer) and `flow_subtype`;
bank statements are accepted as source 'bank'; uploads that overlap rows
imported by the v1 parser are reconciled in place (the "re-import" below).
"""
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from pydantic import BaseModel
from typing import Dict, List, Optional
from pathlib import Path
from starlette.concurrency import run_in_threadpool
from config import supabase_client
from db import run_query
from errors import internal_error, logger
from limiter import limiter
import pandas as pd
from uuid import uuid4
import re
import tempfile
import hashlib

from src.parse import (
    PARSER_VERSION,
    detect_export_filter,
    detect_statement_source,
    parse_alipay,
    parse_generic_bank_csv,
    parse_wechat_csv,
    parse_wechat_excel,
)

router = APIRouter()

MAX_SIZE = 10 * 1024 * 1024  # 10MB
MAX_ROWS = 50000
UNDETECTED_MESSAGE = "Could not detect file source. Expected an Alipay, WeChat or bank statement export."
NON_EXPENSE_DEFAULTS = {
    "category_id": None,
    "needs_review": False,
    "label_source": "none",
    "confidence": None,
}

# XLSX (like all modern Office formats) is a ZIP container — a real one
# always starts with a ZIP local-file-header signature. An empty/spanned
# archive uses a different signature, but a just-created XLSX always has at
# least one entry, so PK\x03\x04 is the one to expect here.
XLSX_MAGIC = b"PK\x03\x04"


def _validate_file_content(filename: str, content: bytes) -> None:
    """Reject a file whose actual content doesn't match its declared
    extension, before it's parsed. Best-effort — not a hard content-type
    guarantee (a CSV has no reliable magic bytes of its own), but it catches
    the case that matters: a file claiming to be .csv/.xlsx that's actually
    something else, parsed downstream as if it were trusted.
    """
    if filename.endswith('.xlsx') and not content.startswith(XLSX_MAGIC):
        raise ValueError("File does not look like a valid Excel (.xlsx) file")
    if filename.endswith('.csv') and content.startswith(XLSX_MAGIC):
        raise ValueError("File extension is .csv but content looks like a binary/Excel file")


class UploadResponse(BaseModel):
    upload_id: str
    file_name: str
    file_type: str
    status: str
    message: str
    rows_imported: int
    rows_skipped: int
    rows_updated: int
    rows_removed: int
    reimported: bool
    rows_by_kind: Dict[str, int]


@router.post("/")
@limiter.limit("20/hour")
async def upload_file(request: Request, file: UploadFile = File(...)):
    """Upload a CSV/Excel file (Alipay, WeChat or bank statement).

    1. Extension, size and magic-byte checks.
    2. Duplicate file check by content hash: a match on a parser-v2 upload
       409s; a match on a parser-v1 upload re-imports into that upload.
    3. Detect the source, parse with the v2 parser (all kinds).
    4. Re-import over overlapping parser-v1 rows (contract §3.9 steps 1-6).
    5. Normal row-level dedup + insert of the remaining rows.

    Failed uploads stay in history with status='failed' and an error_message,
    so the user can see what happened and retry.
    """
    user_id = request.state.user_id
    upload_id = None
    created_upload = False

    if not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")

    tmp_path = None
    try:
        content = await file.read()

        if len(content) > MAX_SIZE:
            raise ValueError(f"File exceeds 10MB limit ({len(content) / 1024 / 1024:.1f}MB)")

        _validate_file_content(file.filename, content)

        file_hash = calculate_file_hash(content)
        existing = await check_duplicate_upload(user_id, file_hash)
        hash_match_v1 = None
        if existing:
            if _parser_version(existing) >= PARSER_VERSION:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"This file was already uploaded on {existing['created_at'][:10]} "
                        f"as \"{existing['original_filename']}\". Delete it from the upload "
                        f"history first if you want to re-import it."
                    ),
                )
            # Same bytes as an upload made by the v1 parser: re-import it
            # into that upload (the per-user unique hash index forbids a
            # second row with this hash).
            hash_match_v1 = existing
            upload_id = existing['id']
        else:
            # Record the upload FIRST so it always appears in history — even
            # when detection/parsing fails below, the row survives with
            # status='failed'. If this insert fails, the whole upload fails
            # loudly: transactions must never exist without a history row.
            upload_id = await create_upload_record(
                user_id, file.filename, file_type=None,
                size_bytes=len(content), file_hash=file_hash, status='uploaded',
            )
            created_upload = True

        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        file_type = detect_source(tmp_path)
        if not file_type:
            raise ValueError(UNDETECTED_MESSAGE)

        df = parse_with_src(tmp_path, file_type)
        if df is None or len(df) == 0:
            raise ValueError(f"Could not parse {file_type} file. Check format and encoding.")

        if len(df) > MAX_ROWS:
            raise ValueError(f"File exceeds {MAX_ROWS} rows limit ({len(df)} rows)")

        df_normalized = normalize_schema(df, file_type)
        export_filter = detect_export_filter(tmp_path)

        # Re-import over parser-v1 rows (steps 2-4 and 6 inside).
        reimport = await reimport_v1_rows(
            user_id, df_normalized, file_type,
            hash_match_upload_id=hash_match_v1['id'] if hash_match_v1 else None,
            skip_deletions=export_filter is not None,
        )
        if export_filter is not None:
            logger.info(
                "Upload %s is a filtered export (%s): re-import deletions skipped",
                upload_id, export_filter,
            )
        df_remaining = df_normalized[~df_normalized.index.isin(reimport['matched_index'])]

        # Store the original file in the private 'uploads' bucket, under the
        # user's folder (first path segment = user_id, required by the
        # bucket's RLS policies and by account-deletion cleanup).
        storage_path = None
        if created_upload:
            storage_path = await store_original(user_id, file.filename, content)

        # Step 5: normal dedup + insert of unmatched rows.
        df_new, skipped = await dedup_new_rows(user_id, df_remaining, file_type)
        if len(df_new) > 0:
            await insert_transactions(user_id, df_new, upload_id, file_type)

        if created_upload:
            await finalize_upload_record(upload_id, file_type, storage_path, len(df_new))
        else:
            await refresh_upload_row_count(upload_id)

        # Step 6 (amended): flip touched v1 uploads to parser_version 2 only
        # when this file's window covers their whole row range — and never
        # from a filtered export: its step-4 deletions were skipped, so rows
        # v1 wrongly kept (e.g. closed unpaid orders) would otherwise be
        # frozen in place forever, since v2 uploads are never re-reconciled.
        if export_filter is None:
            await promote_covered_uploads(
                user_id, reimport['touched_uploads'], reimport['t_min'], reimport['t_max'],
            )

        schedule_classification(request, user_id)
        schedule_fx_backfill(user_id, df_normalized['timestamp'].min())

        rows_by_kind = {
            kind: int((df_new['kind'] == kind).sum()) for kind in ('expense', 'income', 'transfer')
        }
        message = _upload_message(len(df_new), skipped, rows_by_kind, reimport)

        return {
            "upload_id": upload_id,
            "file_name": file.filename,
            "file_type": file_type,
            "status": "parsed",
            "message": message,
            "rows_imported": len(df_new),
            "rows_skipped": skipped,
            "rows_updated": reimport['rows_updated'],
            "rows_removed": reimport['rows_removed'],
            "reimported": reimport['reimported'],
            "rows_by_kind": rows_by_kind,
        }

    except ValueError as e:
        error_msg = str(e)
        # Only mark OUR new history row failed — never an earlier, successful
        # upload that this file merely hash-matched.
        if upload_id and created_upload:
            await update_upload_error(upload_id, error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        if upload_id and created_upload:
            await update_upload_error(upload_id, "Upload failed due to an internal error")
        raise internal_error(e, "uploads/upload_file")
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def _upload_message(imported: int, skipped: int, rows_by_kind: Dict[str, int], reimport: dict) -> str:
    message = f"Imported {_plural(imported, 'transaction', 'transactions')}"
    extras = []
    if rows_by_kind.get('income'):
        extras.append(f"{rows_by_kind['income']} income")
    if rows_by_kind.get('transfer'):
        extras.append(_plural(rows_by_kind['transfer'], 'transfer', 'transfers'))
    if extras:
        message += f" ({', '.join(extras)})"
    if skipped:
        message += f" ({_plural(skipped, 'duplicate', 'duplicates')} skipped)"
    message += "."
    if reimport['reimported']:
        message += (
            f" Updated {reimport['rows_updated']} and removed {reimport['rows_removed']} "
            f"earlier transactions from this statement."
        )
    message += " Categorization is running."
    return message


def schedule_classification(request: Request, user_id: str) -> None:
    """Kick off background classification for a user's unlabeled rows.

    Imported lazily so uploads keep working even if the ML layer has an
    import-time problem; classification then simply doesn't run. Delegates
    to `ml.request_classification`, which runs at most one worker thread per
    user — a multi-file upload batch calls this once per file, and without
    coalescing that would mean N threads each rescanning the user's entire
    needs_review set.
    """
    try:
        from ml import request_classification
        request_classification(user_id)
    except Exception as e:
        logger.warning("Could not schedule classification for %s: %s", user_id, e)
    # Translate the new rows' merchant/description once, in the background,
    # so Reports/Review never call Google Translate on page load.
    from translations import request_translation
    request_translation(user_id)


def schedule_fx_backfill(user_id: str, earliest) -> None:
    """Ask the FX module to backfill rates from the earliest uploaded row's
    date (contract §2 trigger 2). Imported lazily: uploads keep working if
    the FX module is missing or broken; it is non-blocking by contract."""
    try:
        from fx import request_backfill_for_user
    except ImportError:
        return
    try:
        start = pd.Timestamp(earliest).date() if earliest is not None and not pd.isna(earliest) else None
        request_backfill_for_user(user_id, start=start)
    except Exception as e:
        logger.warning("Could not schedule FX backfill for %s: %s", user_id, e)


@router.get("/{upload_id}")
async def get_upload_status(request: Request, upload_id: str):
    """Poll upload status."""
    user_id = request.state.user_id
    try:
        response = await run_query(
            lambda: supabase_client.table("uploads").select("*").eq("id", upload_id).eq("user_id", user_id).execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Upload not found")
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "uploads/get_upload_status")


@router.get("/")
async def list_uploads(request: Request):
    """List uploads for the user, newest first."""
    user_id = request.state.user_id
    try:
        response = await run_query(
            lambda: supabase_client.table("uploads")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        return {"uploads": response.data}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "uploads/list_uploads")


@router.delete("/{upload_id}")
async def delete_upload(request: Request, upload_id: str):
    """Delete an upload and all its associated transactions.

    This removes:
    - The upload record from the uploads table
    - All transactions imported from this upload (cascade delete)
    - The original file from storage (if stored)
    """
    user_id = request.state.user_id
    try:
        upload_resp = await run_query(
            lambda: supabase_client.table("uploads").select("*").eq("id", upload_id).eq("user_id", user_id).execute()
        )
        if not upload_resp.data:
            raise HTTPException(status_code=404, detail="Upload not found")

        upload = upload_resp.data[0]

        # Delete the transactions explicitly (the FK is also ON DELETE CASCADE
        # since 20260708000000, but being explicit keeps the behavior correct
        # even on a database where that migration hasn't been applied yet).
        await run_query(
            lambda: supabase_client.table("transactions").delete().eq("user_id", user_id).eq("upload_id", upload_id).execute()
        )

        await run_query(
            lambda: supabase_client.table("uploads").delete().eq("id", upload_id).eq("user_id", user_id).execute()
        )

        if upload.get("storage_path"):
            try:
                await run_in_threadpool(lambda: supabase_client.storage.from_("uploads").remove([upload["storage_path"]]))
            except Exception as e:
                logger.warning("Failed to delete upload file from storage: %s", e)

        return {"success": True, "message": f"Deleted upload {upload_id} and all its transactions"}

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "uploads/delete_upload")


# --- Helpers ---

def detect_source(file_path: str) -> Optional[str]:
    """'wechat' | 'alipay' | 'bank' | None (see src/parse.py
    detect_statement_source for the marker rules and order)."""
    source = detect_statement_source(file_path)
    logger.info("Detected statement source: %s", source)
    return source


def parse_with_src(file_path: str, file_type: str) -> Optional[pd.DataFrame]:
    """Parse CSV/Excel based on detected source using src/parse.py."""
    try:
        if file_type == 'alipay':
            return parse_alipay(file_path)
        if file_type == 'wechat':
            if file_path.endswith('.xlsx'):
                return parse_wechat_excel(file_path)
            return parse_wechat_csv(file_path)
        if file_type == 'bank':
            return parse_generic_bank_csv(file_path, source='bank')
        return None
    except Exception as e:
        logger.warning("Parse error (%s): %s", file_type, e)
        return None


def normalize_schema(df: pd.DataFrame, file_type: str = None) -> pd.DataFrame:
    """Normalize parsed df to the transactions table's common schema:
    timestamp, merchant, description, amount, kind, flow_subtype
    (source/category_id/etc. are added in insert_transactions)."""
    df = df.copy()

    if 'timestamp' not in df.columns:
        raise ValueError("Missing 'timestamp' column after parsing")

    df['timestamp'] = pd.to_datetime(df['timestamp'])

    for col in ['merchant', 'description', 'amount']:
        if col not in df.columns:
            df[col] = ''
    if 'kind' not in df.columns:
        df['kind'] = 'expense'
    if 'flow_subtype' not in df.columns:
        df['flow_subtype'] = None
    df['flow_subtype'] = df['flow_subtype'].astype(object).where(df['flow_subtype'].notna(), None)

    return df[['timestamp', 'merchant', 'description', 'amount', 'kind', 'flow_subtype']].reset_index(drop=True)


async def store_original(user_id: str, file_name: str, content: bytes) -> Optional[str]:
    """Upload the original file bytes to the 'uploads' bucket.

    Best-effort: a storage failure must not block the transactions import.
    Path layout {user_id}/... matches the bucket RLS policies and the
    account-deletion cleanup prefix.
    """
    safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', file_name)[-80:]
    storage_path = f"{user_id}/{uuid4().hex}_{safe_name}"
    try:
        await run_in_threadpool(lambda: supabase_client.storage.from_("uploads").upload(storage_path, content))
        return storage_path
    except Exception as e:
        logger.warning("Failed to store original upload for %s: %s", user_id, e)
        return None


async def create_upload_record(user_id: str, file_name: str, file_type: Optional[str],
                               storage_path: Optional[str] = None, size_bytes: int = 0,
                               row_count: int = 0, file_hash: str = None,
                               status: str = 'uploaded') -> str:
    """Create an uploads table entry (parser_version = 2).

    Fails LOUDLY on any error: an upload without a history row is unmanageable
    (the user can't see or delete it), so a broken insert must abort the whole
    upload rather than being logged and ignored.
    """
    response = await run_query(
        lambda: supabase_client.table("uploads").insert({
            "user_id": user_id,
            "original_filename": file_name,
            "file_type": file_type,
            "storage_path": storage_path,
            "size_bytes": size_bytes,
            "status": status,
            "row_count": row_count,
            "file_hash": file_hash,
            "parser_version": PARSER_VERSION,
        }).execute()
    )
    if not response.data:
        raise RuntimeError("uploads insert returned no row")
    return response.data[0]['id']


async def finalize_upload_record(upload_id: str, file_type: str,
                                 storage_path: Optional[str], row_count: int) -> None:
    """Mark an upload as successfully parsed and fill in detected metadata."""
    await run_query(
        lambda: supabase_client.table("uploads").update({
            "status": "parsed",
            "file_type": file_type,
            "storage_path": storage_path,
            "row_count": row_count,
        }).eq("id", upload_id).execute()
    )


async def refresh_upload_row_count(upload_id: str) -> None:
    """Re-import into an existing upload: row_count = its current row count."""
    resp = await run_query(
        lambda: supabase_client.table("transactions").select("id", count="exact").eq("upload_id", upload_id).execute()
    )
    count = resp.count if resp.count is not None else len(resp.data or [])
    await run_query(
        lambda: supabase_client.table("uploads").update({"row_count": count}).eq("id", upload_id).execute()
    )


async def update_upload_error(upload_id: str, error_msg: str) -> None:
    """Update upload record with error status.

    Clears file_hash so the per-user unique index doesn't block re-uploading
    the same file after the user fixes whatever failed.
    """
    try:
        await run_query(
            lambda: supabase_client.table("uploads").update({
                "status": "failed",
                "error_message": error_msg,
                "file_hash": None,
            }).eq("id", upload_id).execute()
        )
    except Exception as e:
        logger.warning("Error updating upload record: %s", e)


def _norm_ts(ts) -> str:
    """Naive wall-clock ISO string, comparable between parsed rows and
    timestamptz strings read back from Postgres."""
    return pd.to_datetime(ts, utc=True).tz_convert(None).isoformat(timespec='seconds')


def _dedup_key(ts, merchant, description, amount, source) -> tuple:
    """Normalized identity of a transaction row, comparable between a parsed
    file (naive timestamps) and rows read back from Postgres (UTC-suffixed
    timestamptz strings)."""
    return (
        _norm_ts(ts),
        str(merchant or '').strip(),
        str(description or '').strip(),
        f"{float(amount):.2f}",
        source,
    )


def _content_key(ts, merchant, description) -> tuple:
    """Re-import key: (timestamp, merchant, description), amount ignored."""
    return (_norm_ts(ts), str(merchant or '').strip(), str(description or '').strip())


def _parser_version(row: dict) -> int:
    """Rows written before the parser_version column existed read as 1 (the
    column default)."""
    v = row.get('parser_version')
    return int(v) if v is not None else 1


def _window(df: pd.DataFrame):
    t_min = pd.to_datetime(df['timestamp'].min(), utc=True).tz_convert(None)
    t_max = pd.to_datetime(df['timestamp'].max(), utc=True).tz_convert(None)
    return t_min, t_max


def _chunks(items: list, size: int = 200):
    for i in range(0, len(items), size):
        yield items[i:i + size]


async def reimport_v1_rows(user_id: str, df: pd.DataFrame, file_type: str,
                           hash_match_upload_id: Optional[str] = None,
                           skip_deletions: bool = False) -> dict:
    """Contract §3.9 re-import, steps 2-4.

    Returns {reimported, rows_updated, rows_removed, matched_index (df index
    labels consumed in step 3, not to be inserted), touched_uploads, t_min,
    t_max}. Step 5 (insert) and step 6 (parser_version) are done by the
    caller.
    """
    from db import fetch_all_async

    t_min, t_max = _window(df)
    result = {
        'reimported': hash_match_upload_id is not None,
        'rows_updated': 0, 'rows_removed': 0,
        'matched_index': set(), 'touched_uploads': set(),
        't_min': t_min, 't_max': t_max,
    }
    if hash_match_upload_id is not None:
        result['touched_uploads'].add(hash_match_upload_id)

    uploads_resp = await run_query(
        lambda: supabase_client.table("uploads")
        .select("id, parser_version, status, file_type")
        .eq("user_id", user_id)
        .neq("status", "failed")
        .execute()
    )
    v1_ids = {
        u['id'] for u in (uploads_resp.data or [])
        if _parser_version(u) == 1 and (u.get('file_type') == file_type or u['id'] == hash_match_upload_id)
    }
    if not v1_ids:
        return result

    # Step 2: v1 rows in [t_min, t_max], same user + source, v1 upload.
    window_rows = await fetch_all_async(
        lambda: supabase_client.table("transactions")
        .select("id, timestamp, merchant, description, amount, kind, flow_subtype, upload_id, is_split")
        .eq("user_id", user_id)
        .eq("source", file_type)
        .gte("timestamp", t_min.isoformat())
        .lte("timestamp", t_max.isoformat())
    )
    v1_rows = [r for r in window_rows if r.get('upload_id') in v1_ids]
    if not v1_rows:
        return result
    result['reimported'] = True

    v1_rows.sort(key=lambda r: (_norm_ts(r['timestamp']), str(r['id'])))
    index: Dict[tuple, List[dict]] = {}
    for r in v1_rows:
        index.setdefault(_content_key(r['timestamp'], r['merchant'], r['description']), []).append(r)

    # Step 3: match in file order. Group identical updates into one request.
    updates: Dict[tuple, List[str]] = {}
    unsplit_ids: List[str] = []
    consumed = set()
    for idx, row in df.iterrows():
        bucket = index.get(_content_key(row['timestamp'], row['merchant'], row['description']))
        if not bucket:
            continue
        stored = bucket.pop(0)
        consumed.add(stored['id'])
        result['matched_index'].add(idx)
        result['touched_uploads'].add(stored['upload_id'])

        new_amount = round(float(row['amount']), 2)
        amount_differs = f"{float(stored['amount']):.2f}" != f"{new_amount:.2f}"
        stored_kind = stored.get('kind') or 'expense'
        if row['kind'] == 'expense':
            if not amount_differs:
                continue
            payload = {'amount': new_amount}
            if stored_kind == 'expense':
                payload['flow_subtype'] = 'refund' if new_amount < 0 else None
        else:
            if (not amount_differs and stored_kind == row['kind']
                    and stored.get('flow_subtype') == row['flow_subtype']):
                continue
            payload = {
                'kind': row['kind'], 'flow_subtype': row['flow_subtype'], 'amount': new_amount,
                'is_split': False, **NON_EXPENSE_DEFAULTS,
            }
            if stored.get('is_split'):
                unsplit_ids.append(stored['id'])
        updates.setdefault(tuple(sorted(payload.items())), []).append(stored['id'])
        result['rows_updated'] += 1

    for ids in _chunks(unsplit_ids):
        await run_query(
            lambda ids=ids: supabase_client.table("transaction_splits")
            .delete().eq("user_id", user_id).in_("transaction_id", ids).execute()
        )
    for payload_items, ids in updates.items():
        payload = dict(payload_items)
        for chunk in _chunks(ids):
            await run_query(
                lambda chunk=chunk, payload=payload: supabase_client.table("transactions")
                .update(payload).eq("user_id", user_id).in_("id", chunk).execute()
            )

    # Step 4: unconsumed v1 expense rows in the window have no counterpart in
    # the new statement (e.g. a closed, unpaid order v1 wrongly kept).
    to_delete = [
        r for r in v1_rows
        if r['id'] not in consumed and (r.get('kind') or 'expense') == 'expense'
    ]
    if to_delete and skip_deletions:
        logger.info(
            "Re-import for %s: filtered export, keeping %d unmatched v1 row(s)",
            user_id, len(to_delete),
        )
    elif to_delete:
        for chunk in _chunks([r['id'] for r in to_delete]):
            await run_query(
                lambda chunk=chunk: supabase_client.table("transactions")
                .delete().eq("user_id", user_id).in_("id", chunk).execute()
            )
        result['rows_removed'] = len(to_delete)
        result['touched_uploads'].update(r['upload_id'] for r in to_delete)

    return result


async def promote_covered_uploads(user_id: str, upload_ids: set, t_min, t_max) -> None:
    """Step 6, as amended: set parser_version = 2 on a touched v1 upload only
    when [t_min, t_max] covers that upload's ENTIRE row timestamp range.
    Partially covered uploads stay at 1; re-processing their already
    reconciled rows on a later upload is harmless (identical matches are
    no-ops)."""
    lo, hi = _norm_ts(t_min), _norm_ts(t_max)
    for upload_id in upload_ids:
        first = await run_query(
            lambda: supabase_client.table("transactions").select("timestamp")
            .eq("user_id", user_id).eq("upload_id", upload_id)
            .order("timestamp").limit(1).execute()
        )
        last = await run_query(
            lambda: supabase_client.table("transactions").select("timestamp")
            .eq("user_id", user_id).eq("upload_id", upload_id)
            .order("timestamp", desc=True).limit(1).execute()
        )
        if first.data and last.data:
            row_min, row_max = _norm_ts(first.data[0]['timestamp']), _norm_ts(last.data[0]['timestamp'])
            if row_min < lo or row_max > hi:
                logger.info("Upload %s only partially covered; stays parser_version 1", upload_id)
                continue
        await run_query(
            lambda: supabase_client.table("uploads").update({"parser_version": PARSER_VERSION})
            .eq("id", upload_id).eq("user_id", user_id).execute()
        )


async def dedup_new_rows(user_id: str, df: pd.DataFrame, file_type: str):
    """Drop rows that already exist for this user (and intra-file duplicates).

    Compares against existing transactions in the new file's timestamp window,
    so overlapping export date ranges don't double-import — not just re-uploads
    of the exact same file (those are caught earlier by the file hash).

    Returns (df_new, skipped_count).
    """
    from db import fetch_all_async

    if len(df) == 0:
        return df, 0

    keys = [
        _dedup_key(row.timestamp, row.merchant, row.description, row.amount, file_type)
        for row in df.itertuples()
    ]

    t_min, t_max = _window(df)
    existing = await fetch_all_async(
        lambda: supabase_client.table("transactions")
        .select("timestamp, merchant, description, amount, source")
        .eq("user_id", user_id)
        .gte("timestamp", t_min.isoformat())
        .lte("timestamp", t_max.isoformat())
    )
    existing_keys = {
        _dedup_key(r['timestamp'], r['merchant'], r['description'], r['amount'], r['source'])
        for r in existing
    }

    seen = set()
    keep = []
    for key in keys:
        keep.append(key not in existing_keys and key not in seen)
        seen.add(key)

    df_new = df[pd.Series(keep, index=df.index)]
    return df_new, len(df) - len(df_new)


INSERT_CHUNK = 500  # rows per insert request (keeps request bodies small)


async def insert_transactions(user_id: str, df: pd.DataFrame, upload_id: str, file_type: str):
    """Insert normalized transactions into transactions table.

    file_type ('alipay'/'wechat'/'bank') maps directly to the
    transaction_source enum. Expense rows start with category_id null and
    needs_review=True; the background classification pass fills in rule
    matches and model suggestions. Income/transfer rows are never classified:
    category_id NULL, needs_review=false, label_source='none', confidence
    NULL (contract §1.1).
    """
    rows = []
    for rec in df.to_dict('records'):
        kind = rec.get('kind') or 'expense'
        subtype = rec.get('flow_subtype')
        row = {
            'timestamp': pd.Timestamp(rec['timestamp']).isoformat(),
            'merchant': rec['merchant'],
            'description': rec['description'],
            'amount': round(float(rec['amount']), 2),
            'user_id': user_id,
            'upload_id': upload_id,
            'source': file_type,
            'kind': kind,
            'flow_subtype': None if subtype is None or (isinstance(subtype, float) and pd.isna(subtype)) else subtype,
            'label_source': 'none',
            'needs_review': kind == 'expense',
            'is_manually_labeled': False,
        }
        if kind != 'expense':
            row.update(NON_EXPENSE_DEFAULTS)
        rows.append(row)

    for i in range(0, len(rows), INSERT_CHUNK):
        chunk = rows[i:i + INSERT_CHUNK]
        await run_query(lambda chunk=chunk: supabase_client.table("transactions").insert(chunk).execute())


def calculate_file_hash(content: bytes) -> str:
    """Calculate SHA256 hash of file contents for duplicate detection."""
    return hashlib.sha256(content).hexdigest()


async def check_duplicate_upload(user_id: str, file_hash: str) -> Optional[dict]:
    """Check if a file with this hash was already uploaded by the user.

    Returns the existing upload record (incl. parser_version) if found.
    """
    try:
        response = await run_query(
            lambda: supabase_client.table("uploads")
            .select("id, created_at, original_filename, file_hash, file_type, parser_version")
            .eq("user_id", user_id)
            .eq("file_hash", file_hash)
            .neq("status", "failed")
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.warning("Error checking for duplicate upload: %s", e)
        return None
