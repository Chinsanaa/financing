"""File upload and parsing: accept CSV, normalize to common schema."""
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from config import supabase_client
import io
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

# Add src to path so we can import parsers
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from parse import parse_alipay, parse_wechat_excel, parse_wechat_csv

router = APIRouter()


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
    3. Content sniffing (attempt parse to detect format)
    4. Row limit (50k max post-parse)
    5. Normalize to common schema
    6. Insert into transactions table

    Returns upload_id. Failed uploads logged with error_message.
    """
    user_id = request.state.user_id
    upload_id = None

    # Validation 1: Extension check
    if not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")

    try:
        # Read content into memory
        content = await file.read()

        # Validation 2: Size limit (10MB)
        MAX_SIZE = 10 * 1024 * 1024  # 10MB
        if len(content) > MAX_SIZE:
            raise ValueError(f"File exceeds 10MB limit ({len(content) / 1024 / 1024:.1f}MB)")

        # Save to temporary location
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # Validation 3: Content sniffing - detect format
        file_type = detect_csv_source(tmp_path)
        if not file_type:
            raise ValueError("Could not detect file source. Expected Alipay or WeChat format.")

        # Validation 4: Parse and check row count
        df = parse_csv_with_src(tmp_path, file_type)
        if df is None or len(df) == 0:
            raise ValueError(f"Could not parse {file_type} file. Check format and encoding.")

        MAX_ROWS = 50000
        if len(df) > MAX_ROWS:
            raise ValueError(f"File exceeds {MAX_ROWS} rows limit ({len(df)} rows)")

        # Normalize to common schema
        df_normalized = normalize_schema(df, file_type)

        # Create upload record (before inserting transactions)
        upload_id = create_upload_record(user_id, file.filename, file_type, row_count=len(df_normalized), error=None)

        # Insert transactions
        insert_transactions(user_id, df_normalized, upload_id)

        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)

        return {
            "upload_id": upload_id,
            "file_name": file.filename,
            "file_type": file_type,
            "status": "parsed",
            "message": f"Uploaded {len(df_normalized)} transactions. Ready to label.",
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
        # Unexpected error - log with error message
        error_msg = f"Upload failed: {str(e)}"
        if upload_id:
            update_upload_error(upload_id, error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/{upload_id}")
async def get_upload_status(request: Request, upload_id: str):
    """Poll upload status."""
    user_id = request.state.user_id
    try:
        response = supabase_client.table("uploads").select("*").eq("id", upload_id).eq("user_id", user_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Upload not found")
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_uploads(request: Request):
    """List all uploads for the user."""
    user_id = request.state.user_id
    try:
        response = supabase_client.table("uploads").select("*").eq("user_id", user_id).execute()
        return {"uploads": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Helpers ---

def detect_csv_source(file_path: str) -> Optional[str]:
    """Detect if CSV is Alipay or WeChat by reading header."""
    try:
        df = pd.read_csv(file_path, nrows=0, encoding='utf-8')
        columns = df.columns.tolist()

        # Alipay: has '交易时间', '交易对方', '金额', etc.
        # WeChat Excel/CSV: has '交易时间', '交易类型', '交易对方', '商品', etc.
        has_alipay_markers = any(c in columns for c in ['交易时间', '交易对方', 'Transaction Time', 'Transaction Counterparty'])
        has_wechat_markers = any(c in columns for c in ['交易类型', '当前状态', '金额(元)'])

        if has_alipay_markers and '交易对方' in columns:
            return 'alipay'
        elif has_wechat_markers or has_alipay_markers:
            return 'wechat'
        return None
    except Exception:
        return None


def parse_csv_with_src(file_path: str, file_type: str) -> Optional[pd.DataFrame]:
    """Parse CSV/Excel based on detected source using src/parse.py."""
    try:
        if file_type == 'alipay':
            return parse_alipay(file_path)
        elif file_type == 'wechat':
            # Auto-detect: if .xlsx, use Excel parser; else CSV
            if file_path.endswith('.xlsx'):
                return parse_wechat_excel(file_path)
            else:
                return parse_wechat_csv(file_path)
        return None
    except Exception as e:
        print(f"Parse error ({file_type}): {e}")
        return None


def normalize_schema(df: pd.DataFrame, file_type: str = None) -> pd.DataFrame:
    """Normalize parsed df to common schema.

    Input (from src/parse.py) has columns: timestamp, merchant, description, amount, source.
    Output adds: time (extracted hour), date, category (default='Other'), labeled=False.
    """
    df = df.copy()

    # Ensure timestamp is datetime
    if 'timestamp' not in df.columns:
        raise ValueError("Missing 'timestamp' column after parsing")

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['timestamp'].dt.date
    df['time'] = df['timestamp'].dt.time

    # Ensure required columns
    for col in ['merchant', 'description', 'amount']:
        if col not in df.columns:
            df[col] = ''

    return df[['timestamp', 'date', 'time', 'merchant', 'description', 'amount']]


def create_upload_record(user_id: str, file_name: str, file_type: str, row_count: int = 0, error: str = None) -> str:
    """Create an uploads table entry."""
    try:
        response = supabase_client.table("uploads").insert({
            "user_id": user_id,
            "original_filename": file_name,
            "file_type": file_type,
            "status": "failed" if error else "parsed",
            "row_count": row_count,
            "error_message": error,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
        return response.data[0]['id'] if response.data else None
    except Exception as e:
        print(f"Error creating upload record: {e}")
        return None


def update_upload_error(upload_id: str, error_msg: str) -> None:
    """Update upload record with error status."""
    try:
        supabase_client.table("uploads").update({
            "status": "failed",
            "error_message": error_msg,
        }).eq("id", upload_id).execute()
    except Exception as e:
        print(f"Error updating upload record: {e}")


def insert_transactions(user_id: str, df: pd.DataFrame, upload_id: str):
    """Insert normalized transactions into transactions table."""
    try:
        # Add user_id and upload_id to each row
        df['user_id'] = user_id
        df['upload_id'] = upload_id
        df['labeled'] = False
        df['category'] = 'Other'  # Default
        df['label_source'] = 'none'
        df['confidence'] = 0.0

        rows = df.to_dict('records')
        supabase_client.table("transactions").insert(rows).execute()
    except Exception as e:
        print(f"Error inserting transactions: {e}")
        raise
