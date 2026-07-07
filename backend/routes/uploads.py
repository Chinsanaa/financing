"""File upload and parsing: accept CSV/Excel, normalize to common schema."""
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from config import supabase_client
from errors import internal_error, logger
import pandas as pd
from datetime import datetime
from uuid import uuid4
import re
import tempfile
import os
import shutil
import hashlib

from src.parse import parse_alipay, parse_wechat_excel, parse_wechat_csv

router = APIRouter()

MAX_SIZE = 10 * 1024 * 1024  # 10MB
MAX_ROWS = 50000


class UploadResponse(BaseModel):
    upload_id: str
    file_name: str
    file_type: str
    status: str
    message: str


@router.post("/")
async def upload_file(request: Request, file: UploadFile = File(...)):
    """Upload a CSV/Excel file (Alipay or WeChat format) with strict validation.

    Validations:
    1. Extension check (CSV or XLSX only)
    2. Size limit (10MB max)
    3. Duplicate file check (same file already uploaded)
    4. Content sniffing (read headers to detect format)
    5. Row limit (50k max post-parse)
    6. Normalize to common schema
    7. Store original in Storage, insert into transactions table

    Returns upload_id. Failed uploads logged with error_message.
    """
    user_id = request.state.user_id
    upload_id = None

    # Validation 1: Extension check
    if not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")

    tmp_path = None
    try:
        content = await file.read()

        # Validation 2: Size limit
        if len(content) > MAX_SIZE:
            raise ValueError(f"File exceeds 10MB limit ({len(content) / 1024 / 1024:.1f}MB)")

        # Validation 3: Duplicate file check
        file_hash = calculate_file_hash(content)
        existing = check_duplicate_upload(user_id, file_hash)
        if existing:
            raise ValueError(
                f"This file was already uploaded on {existing['created_at'][:10]}. "
                f"To upload again and add duplicate transactions, use a different file."
            )

        # Save to a temporary location for the parsers (always cleaned up in finally)
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # Validation 4: Content sniffing - detect format
        file_type = detect_source(tmp_path)
        if not file_type:
            raise ValueError("Could not detect file source. Expected Alipay or WeChat format.")

        # Validation 5: Parse and check row count
        df = parse_with_src(tmp_path, file_type)
        if df is None or len(df) == 0:
            raise ValueError(f"Could not parse {file_type} file. Check format and encoding.")

        if len(df) > MAX_ROWS:
            raise ValueError(f"File exceeds {MAX_ROWS} rows limit ({len(df)} rows)")

        # Normalize to common schema
        df_normalized = normalize_schema(df, file_type)

        # Store the original file in the private 'uploads' bucket, under the
        # user's folder (first path segment = user_id, required by the
        # bucket's RLS policies and by account-deletion cleanup).
        storage_path = store_original(user_id, file.filename, content)

        # Create upload record (before inserting transactions)
        upload_id = create_upload_record(
            user_id, file.filename, file_type,
            storage_path=storage_path, size_bytes=len(content),
            row_count=len(df_normalized), file_hash=file_hash,
        )

        # Insert transactions
        insert_transactions(user_id, df_normalized, upload_id, file_type)

        # Classify the new rows in the background (rules first, then the
        # user's trained model if one exists) so the review queue fills up
        # with suggestions without blocking the upload response.
        schedule_classification(request, user_id)

        return {
            "upload_id": upload_id,
            "file_name": file.filename,
            "file_type": file_type,
            "status": "parsed",
            "message": f"Uploaded {len(df_normalized)} transactions. Categorization is running.",
        }

    except ValueError as e:
        # Validation failed - log with error message
        error_msg = str(e)
        if upload_id:
            update_upload_error(upload_id, error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        if upload_id:
            update_upload_error(upload_id, "Upload failed due to an internal error")
        raise internal_error(e, "uploads/upload_file")
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


def schedule_classification(request: Request, user_id: str) -> None:
    """Kick off background classification for a user's unlabeled rows.

    Imported lazily so uploads keep working even if the ML layer has an
    import-time problem; classification then simply doesn't run.
    """
    try:
        from ml import classify_user_transactions
        import threading
        # A daemon thread (not BackgroundTasks) because this runs after the
        # response and may take seconds on large uploads; the sync supabase
        # client would otherwise occupy the request threadpool slot.
        threading.Thread(
            target=classify_user_transactions, args=(user_id,), daemon=True
        ).start()
    except Exception as e:
        logger.warning("Could not schedule classification for %s: %s", user_id, e)


@router.get("/{upload_id}")
async def get_upload_status(request: Request, upload_id: str):
    """Poll upload status."""
    user_id = request.state.user_id
    try:
        response = supabase_client.table("uploads").select("*").eq("id", upload_id).eq("user_id", user_id).execute()
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
        response = (
            supabase_client.table("uploads")
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
        # Verify the upload exists and belongs to the user
        upload_resp = supabase_client.table("uploads").select("*").eq("id", upload_id).eq("user_id", user_id).execute()
        if not upload_resp.data:
            raise HTTPException(status_code=404, detail="Upload not found")

        upload = upload_resp.data[0]

        # Delete the upload record (cascade deletes transactions via foreign key)
        supabase_client.table("uploads").delete().eq("id", upload_id).eq("user_id", user_id).execute()

        # Delete the original file from storage if it was stored
        if upload.get("storage_path"):
            try:
                supabase_client.storage.from_("uploads").remove([upload["storage_path"]])
            except Exception as e:
                logger.warning("Failed to delete upload file from storage: %s", e)
                # Don't fail the whole operation if storage deletion fails

        return {"success": True, "message": f"Deleted upload {upload_id} and all its transactions"}

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "uploads/delete_upload")


# --- Helpers ---

def _read_headers(file_path: str) -> list:
    """Read just the column headers, using the reader that matches the file
    format — pd.read_csv on an .xlsx file raises, which used to make Excel
    uploads undetectable."""
    if file_path.endswith('.xlsx'):
        # WeChat Excel files may have metadata rows before the actual headers
        # Read all sheets and look for transaction table headers
        try:
            # Try reading first sheet with no header, look for header row
            df = pd.read_excel(file_path, header=None, nrows=50)
            for idx, row in df.iterrows():
                row_str = ' '.join(str(v) for v in row.dropna() if pd.notna(v))
                if '交易时间' in row_str or 'Transaction Time' in row_str:
                    return row.dropna().tolist()
        except Exception:
            pass

        # Fallback: try reading with default header
        try:
            return pd.read_excel(file_path, nrows=0).columns.tolist()
        except Exception:
            return []

    # WeChat CSVs have metadata rows before the actual headers.
    # Read first 50 rows and find the row with transaction table headers.
    try:
        df = pd.read_csv(file_path, nrows=50, encoding='utf-8', header=None)
        # Look for row containing WeChat transaction headers (Chinese or English)
        for idx, row in df.iterrows():
            row_str = ' '.join(str(v) for v in row.dropna() if pd.notna(v))
            if '交易时间' in row_str or 'Transaction Time' in row_str:
                return row.dropna().tolist()
    except Exception:
        pass

    # Fallback: assume headers are in the first row
    return pd.read_csv(file_path, nrows=0, encoding='utf-8').columns.tolist()


def detect_source(file_path: str) -> Optional[str]:
    """Detect if a file is an Alipay or WeChat export by its headers."""
    try:
        columns = _read_headers(file_path)
        logger.info(f"Detected columns: {columns}")

        # Alipay: has '交易时间' (Transaction Time), '交易对方' (Counterparty), etc.
        # WeChat: has '交易类型' (Transaction Type), '当前状态' (Current Status), '金额(元)' (Amount CNY)
        has_alipay_markers = any(c in columns for c in ['交易时间', '交易对方', 'Transaction Time', 'Transaction Counterparty'])
        has_wechat_markers = any(c in columns for c in ['交易类型', '当前状态', '金额(元)'])

        logger.info(f"Alipay markers: {has_alipay_markers}, WeChat markers: {has_wechat_markers}")

        # WeChat markers are unique to WeChat exports, so check them first;
        # Alipay markers alone (e.g. English-only Alipay headers with no
        # WeChat-specific columns) are otherwise sufficient for 'alipay'.
        if has_wechat_markers:
            return 'wechat'
        elif has_alipay_markers:
            return 'alipay'
        return None
    except Exception as e:
        logger.error(f"Error detecting source: {e}", exc_info=True)
        return None


def parse_with_src(file_path: str, file_type: str) -> Optional[pd.DataFrame]:
    """Parse CSV/Excel based on detected source using src/parse.py."""
    try:
        if file_type == 'alipay':
            return parse_alipay(file_path)
        elif file_type == 'wechat':
            if file_path.endswith('.xlsx'):
                return parse_wechat_excel(file_path)
            return parse_wechat_csv(file_path)
        return None
    except Exception as e:
        logger.warning("Parse error (%s): %s", file_type, e)
        return None


def normalize_schema(df: pd.DataFrame, file_type: str = None) -> pd.DataFrame:
    """Normalize parsed df to the transactions table's common schema:
    timestamp, merchant, description, amount (source/category_id/etc. are
    added separately in insert_transactions, since they depend on upload
    metadata, not the parsed file content).
    """
    df = df.copy()

    if 'timestamp' not in df.columns:
        raise ValueError("Missing 'timestamp' column after parsing")

    df['timestamp'] = pd.to_datetime(df['timestamp'])

    for col in ['merchant', 'description', 'amount']:
        if col not in df.columns:
            df[col] = ''

    return df[['timestamp', 'merchant', 'description', 'amount']]


def store_original(user_id: str, file_name: str, content: bytes) -> Optional[str]:
    """Upload the original file bytes to the 'uploads' bucket.

    Best-effort: a storage failure must not block the transactions import.
    Path layout {user_id}/... matches the bucket RLS policies and the
    account-deletion cleanup prefix.
    """
    safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', file_name)[-80:]
    storage_path = f"{user_id}/{uuid4().hex}_{safe_name}"
    try:
        supabase_client.storage.from_("uploads").upload(storage_path, content)
        return storage_path
    except Exception as e:
        logger.warning("Failed to store original upload for %s: %s", user_id, e)
        return None


def create_upload_record(user_id: str, file_name: str, file_type: str,
                         storage_path: Optional[str] = None, size_bytes: int = 0,
                         row_count: int = 0, error: str = None, file_hash: str = None) -> Optional[str]:
    """Create an uploads table entry."""
    try:
        response = supabase_client.table("uploads").insert({
            "user_id": user_id,
            "original_filename": file_name,
            "file_type": file_type,
            "storage_path": storage_path,
            "size_bytes": size_bytes,
            "status": "failed" if error else "parsed",
            "row_count": row_count,
            "error_message": error,
            "file_hash": file_hash,
        }).execute()
        return response.data[0]['id'] if response.data else None
    except Exception as e:
        logger.warning("Error creating upload record: %s", e)
        return None


def update_upload_error(upload_id: str, error_msg: str) -> None:
    """Update upload record with error status."""
    try:
        supabase_client.table("uploads").update({
            "status": "failed",
            "error_message": error_msg,
        }).eq("id", upload_id).execute()
    except Exception as e:
        logger.warning("Error updating upload record: %s", e)


def insert_transactions(user_id: str, df: pd.DataFrame, upload_id: str, file_type: str):
    """Insert normalized transactions into transactions table.

    file_type ('alipay'/'wechat') maps directly to the transaction_source
    enum. category_id starts null and needs_review=True; the background
    classification pass fills in rule matches and model suggestions.
    """
    df = df.copy()
    df['timestamp'] = df['timestamp'].apply(lambda ts: ts.isoformat())
    df['user_id'] = user_id
    df['upload_id'] = upload_id
    df['source'] = file_type
    df['label_source'] = 'none'
    df['needs_review'] = True
    df['is_manually_labeled'] = False

    rows = df.to_dict('records')
    supabase_client.table("transactions").insert(rows).execute()


def calculate_file_hash(content: bytes) -> str:
    """Calculate SHA256 hash of file contents for duplicate detection."""
    return hashlib.sha256(content).hexdigest()


def check_duplicate_upload(user_id: str, file_hash: str) -> Optional[dict]:
    """Check if a file with this hash was already uploaded by the user.

    Returns the existing upload record if found, None otherwise.
    """
    try:
        response = (
            supabase_client.table("uploads")
            .select("id, created_at, original_filename, file_hash")
            .eq("user_id", user_id)
            .eq("file_hash", file_hash)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.warning("Error checking for duplicate upload: %s", e)
        return None
