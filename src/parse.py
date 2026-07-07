"""CSV/Excel parsers for Alipay, WeChat, and generic bank/card exports."""
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Header aliases for auto-detecting generic bank / credit-card CSV columns
_COLUMN_ALIASES: Dict[str, List[str]] = {
    'timestamp': [
        '交易时间', '交易日期', '记账日期', '入账日期', '发生时间',
        'Transaction Time', 'Transaction Date', 'Date', 'Posting Date',
    ],
    'amount': [
        '金额', '交易金额', '支出金额', '入账金额', 'Amount', 'Amount (CNY)',
        'Debit', '交易金额(元)', '金额(元)',
    ],
    'merchant': [
        '交易对方', '对方户名', '商户名称', '商户', 'Counterparty', 'Merchant',
        'Payee', 'Description',
    ],
    'description': [
        '商品说明', '商品', '摘要', '交易摘要', '备注', '用途',
        'Product Description', 'Product', 'Memo', 'Narrative',
    ],
    'direction': [
        '收/支', '借贷标志', '收支类型', 'Income/Expense', 'Type', 'Dr/Cr',
    ],
}

# 交易类型/交易分类 values that move money between your own accounts (credit
# card repayment, cash withdrawal) rather than spend it. Excluded entirely so
# they don't inflate totals. Deliberately NOT included: 转账/红包 (transfers to
# other people) — whether that counts as "spending" is a judgment call, not
# something to decide silently. Add to this list if you want those excluded too.
_TRANSFER_KEYWORDS = ('信用卡还款', '花呗还款', '还呗还款', '提现')

# Status text marking a transaction as refunded. Refund rows are kept (not
# dropped) with a negated amount, so a purchase and its refund net out in
# category/merchant totals instead of the purchase silently overstating spend.
_REFUND_KEYWORDS = ('退款',)
_REFUND_KEYWORDS_EN = ('Refund',)


def _category_column(df: pd.DataFrame) -> Optional[str]:
    """Find Alipay/WeChat's own transaction-type column, if present."""
    for col in ('交易分类', '交易类型'):
        if col in df.columns:
            return col
    return None


def _find_column(df: pd.DataFrame, field: str, override: Optional[str] = None) -> Optional[str]:
    """Resolve a dataframe column name from aliases or explicit mapping."""
    if override and override in df.columns:
        return override
    for candidate in _COLUMN_ALIASES.get(field, []):
        if candidate in df.columns:
            return candidate
    return None


def _parse_amount_series(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace(',', '', regex=False)
        .str.replace('¥', '', regex=False)
        .str.replace('￥', '', regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors='coerce')


def parse_generic_bank_csv(
    csv_path: str,
    source: str = 'bank',
    column_map: Optional[Dict[str, str]] = None,
    encoding: Optional[str] = None,
) -> pd.DataFrame:
    """
    Parse a bank transfer or credit-card CSV export into the unified schema.

  Auto-detects common Chinese/English column headers. Pass column_map to
  override detection, e.g. {"timestamp": "记账日期", "amount": "支出金额"}.
    """
    column_map = column_map or {}
    last_error = None

    for enc in ([encoding] if encoding else []) + ['utf-8-sig', 'utf-8', 'gbk', 'gb18030']:
        try:
            raw = pd.read_csv(csv_path, encoding=enc)
            break
        except (UnicodeDecodeError, LookupError) as exc:
            last_error = exc
            raw = None
    else:
        raise ValueError(f"Cannot read bank CSV encoding: {csv_path} ({last_error})")

    ts_col = _find_column(raw, 'timestamp', column_map.get('timestamp'))
    amt_col = _find_column(raw, 'amount', column_map.get('amount'))
    if not ts_col or not amt_col:
        raise ValueError(
            f"Cannot detect date/amount columns in {csv_path}. "
            f"Found: {list(raw.columns)}. Add column_map in source_config.json."
        )

    merchant_col = _find_column(raw, 'merchant', column_map.get('merchant'))
    desc_col = _find_column(raw, 'description', column_map.get('description'))
    direction_col = _find_column(raw, 'direction', column_map.get('direction'))

    df = raw.copy()
    if direction_col:
        expense_markers = {'支出', '借', 'Debit', 'Expense', '出', 'D'}
        df = df[df[direction_col].astype(str).str.strip().isin(expense_markers)]

    amount = _parse_amount_series(df[amt_col]).abs()
    df = df[amount > 0].copy()
    amount = amount[amount > 0]

    merchant = (
        df[merchant_col].fillna('').astype(str).str.strip()
        if merchant_col else pd.Series([''] * len(df), index=df.index)
    )
    description = (
        df[desc_col].fillna('').astype(str).str.strip()
        if desc_col else pd.Series([''] * len(df), index=df.index)
    )

    return pd.DataFrame({
        'timestamp': pd.to_datetime(df[ts_col]),
        'merchant': merchant.values,
        'description': description.values,
        'amount': amount.values,
        'source': source,
    })


def load_source_config(config_path: Path) -> List[dict]:
    """Load optional additional source definitions from JSON."""
    if not config_path.exists():
        return []
    with open(config_path, encoding='utf-8') as f:
        data = json.load(f)
    return data.get('additional_sources', [])


def _find_alipay_header(csv_path: str) -> Tuple[int, str, bool]:
    """
    Locate the Alipay data header row and encoding.

    Returns:
        (skiprows, encoding, is_chinese_format)
    """
    for encoding in ('utf-8-sig', 'utf-8', 'gbk', 'gb18030'):
        try:
            with open(csv_path, encoding=encoding) as f:
                for i, line in enumerate(f):
                    if 'Transaction Time' in line and 'Type' in line:
                        return i, encoding, False
                    if '交易时间' in line and '收/支' in line:
                        return i, encoding, True
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Cannot detect Alipay CSV format: {csv_path}")


def parse_alipay_english(csv_path: str, encoding: str = 'utf-8', skiprows: int = 0) -> pd.DataFrame:
    """
    Parse English-translated Alipay export CSV.

    No transaction-type column in this format, so internal transfers
    (credit card repayment, withdrawal) can't be detected/excluded here —
    use the native Chinese export (parse_alipay_native) for that split.
    """
    df = pd.read_csv(csv_path, encoding=encoding, skiprows=skiprows)

    status = df['Transaction Status'].astype(str)
    is_settled = status.str.contains('Successful|Closed', case=False, na=False)
    is_refund = status.str.contains('|'.join(_REFUND_KEYWORDS_EN), case=False, na=False)

    is_expense = (df['Type'] == 'Expense') & is_settled
    df = df[is_expense | is_refund].copy()
    is_refund = is_refund.loc[df.index]

    amount = df['Amount'].astype(float)
    amount = amount.mask(is_refund.values, -amount)

    if is_refund.sum():
        print(f"  Netted {is_refund.sum()} refund(s) as negative spend")

    return pd.DataFrame({
        'timestamp': pd.to_datetime(df['Transaction Time']),
        'merchant': df['Transaction Counterparty'].fillna('').str.strip(),
        'description': df['Product Description'].fillna('').str.strip(),
        'amount': amount,
        'source': 'alipay',
    })


def parse_alipay_native(csv_path: str, encoding: str = 'gbk', skiprows: int = 0) -> pd.DataFrame:
    """Parse native Chinese Alipay export CSV (GBK/UTF-8)."""
    df = pd.read_csv(csv_path, encoding=encoding, skiprows=skiprows)

    status = df['交易状态'].astype(str)
    is_settled = status.str.contains('交易成功|交易关闭', na=False)
    is_refund = status.str.contains('|'.join(_REFUND_KEYWORDS), na=False)

    cat_col = _category_column(df)
    is_transfer = (
        df[cat_col].astype(str).str.contains('|'.join(_TRANSFER_KEYWORDS), na=False)
        if cat_col else pd.Series(False, index=df.index)
    )

    is_expense = (df['收/支'] == '支出') & is_settled & ~is_transfer
    df = df[is_expense | is_refund].copy()
    is_refund = is_refund.loc[df.index]

    amount = df['金额'].astype(str).str.replace(',', '', regex=False).astype(float)
    amount = amount.mask(is_refund.values, -amount)

    if is_refund.sum():
        print(f"  Netted {is_refund.sum()} refund(s) as negative spend")
    if is_transfer.sum():
        print(f"  Excluded {is_transfer.sum()} internal transfer(s) (credit card repayment, withdrawal, etc.)")

    return pd.DataFrame({
        'timestamp': pd.to_datetime(df['交易时间']),
        'merchant': df['交易对方'].fillna('').astype(str).str.strip(),
        'description': df['商品说明'].fillna('').astype(str).str.strip(),
        'amount': amount,
        'source': 'alipay',
    })


def parse_alipay(csv_path: str) -> pd.DataFrame:
    """Parse Alipay CSV — auto-detects English vs native Chinese export."""
    skiprows, encoding, is_chinese = _find_alipay_header(csv_path)
    if is_chinese:
        return parse_alipay_native(csv_path, encoding=encoding, skiprows=skiprows)
    return parse_alipay_english(csv_path, encoding=encoding, skiprows=skiprows)


def parse_wechat_excel(xlsx_path: str) -> pd.DataFrame:
    """Parse WeChat export Excel file (native Chinese format with original texts)."""
    df = pd.read_excel(xlsx_path, sheet_name=0, skiprows=17)

    expected_cols = [
        '交易时间', '交易类型', '交易对方', '商品', '收/支',
        '金额(元)', '支付方式', '当前状态', '交易单号', '商户单号', '备注',
    ]

    first_val = str(df.iloc[0, 0])
    if '交易时间' in first_val:
        df = df.iloc[1:].reset_index(drop=True)
        df.columns = expected_cols
    else:
        df.columns = expected_cols

    status = df['当前状态'].astype(str)
    is_settled = status.isin(['支付成功', '已转账'])
    is_refund = status.str.contains('|'.join(_REFUND_KEYWORDS), na=False)

    is_transfer = df['交易类型'].astype(str).str.contains('|'.join(_TRANSFER_KEYWORDS), na=False)

    is_expense = (df['收/支'] == '支出') & is_settled & ~is_transfer
    df = df[is_expense | is_refund].copy()
    is_refund = is_refund.loc[df.index]

    amount_clean = df['金额(元)'].astype(str).str.replace(',', '').astype(float)
    amount_clean = amount_clean.mask(is_refund.values, -amount_clean)

    if is_refund.sum():
        print(f"  Netted {is_refund.sum()} refund(s) as negative spend")
    if is_transfer.sum():
        print(f"  Excluded {is_transfer.sum()} internal transfer(s) (credit card repayment, withdrawal, etc.)")

    return pd.DataFrame({
        'timestamp': pd.to_datetime(df['交易时间']),
        'merchant': df['交易对方'].fillna('').str.strip(),
        'description': df['商品'].fillna('').str.strip(),
        'amount': amount_clean,
        'source': 'wechat',
    })


def parse_wechat_csv(csv_path: str) -> pd.DataFrame:
    """
    Parse WeChat export CSV (handles both Chinese and English versions with metadata).
    """
    # Read all rows to find where the actual table headers are
    df_raw = pd.read_csv(csv_path, encoding='utf-8', header=None)

    # Find the header row (contains 交易时间 or Transaction Time)
    header_row = None
    for idx, row in df_raw.iterrows():
        row_str = ' '.join(str(v) for v in row.dropna() if pd.notna(v))
        if '交易时间' in row_str or 'Transaction Time' in row_str:
            header_row = idx
            break

    if header_row is None:
        raise ValueError("Could not find WeChat transaction table headers")

    # Re-read starting from the header row
    df = pd.read_csv(csv_path, encoding='utf-8', skiprows=header_row)

    # Map Chinese column names to English (if needed)
    column_map = {
        '交易时间': 'Transaction Time',
        '当前状态': 'Current Status',
        '收/支': 'Income/Expense',
        '金额(元)': 'Amount (CNY)',
        '交易对方': 'Counterparty',
        '商品': 'Product',
    }

    # Rename columns if they're in Chinese
    df = df.rename(columns=column_map)

    # Use "Current Status" or try Chinese name
    status_col = 'Current Status' if 'Current Status' in df.columns else '当前状态'
    status = df[status_col].astype(str)
    is_settled = status.str.contains('successful|Transferred|已完成', case=False, na=False)
    is_refund = status.str.contains('|'.join(_REFUND_KEYWORDS_EN + _REFUND_KEYWORDS), case=False, na=False)

    # Income/Expense column
    ie_col = 'Income/Expense' if 'Income/Expense' in df.columns else '收/支'
    is_expense = ((df[ie_col] == 'Expense') | (df[ie_col] == '支出')) & is_settled
    df = df[is_expense | is_refund].copy()
    is_refund = is_refund.loc[df.index]

    # Amount column
    amount_col = 'Amount (CNY)' if 'Amount (CNY)' in df.columns else '金额(元)'
    amount = df[amount_col].astype(float)
    amount = amount.mask(is_refund.values, -amount)

    if is_refund.sum():
        print(f"  Netted {is_refund.sum()} refund(s) as negative spend")

    # Get merchant/description columns
    merchant_col = 'Counterparty' if 'Counterparty' in df.columns else '交易对方'
    desc_col = 'Product' if 'Product' in df.columns else '商品'
    time_col = 'Transaction Time' if 'Transaction Time' in df.columns else '交易时间'

    return pd.DataFrame({
        'timestamp': pd.to_datetime(df[time_col]),
        'merchant': df[merchant_col].fillna('').str.strip(),
        'description': df[desc_col].fillna('').str.strip(),
        'amount': amount,
        'source': 'wechat',
    })


def resolve_raw_paths(base_path: Optional[Path] = None) -> Tuple[Optional[Path], Optional[Path], List[dict]]:
    """
    Resolve default Alipay, WeChat, and optional extra sources under data/raw/.

    Returns:
        (alipay_path or None, wechat_path or None, additional_source_configs)
    """
    base = base_path or Path(__file__).parent.parent
    raw_dir = base / 'data' / 'raw'

    alipay_path = None
    for name in ('alipay.csv', 'alipay_expenses.csv'):
        candidate = raw_dir / name
        if candidate.exists():
            alipay_path = candidate
            break

    wechat_path = None
    for name in ('raw-wechat.xlsx', 'wechat.xlsx', 'wechat.csv'):
        candidate = raw_dir / name
        if candidate.exists():
            wechat_path = candidate
            break

    config_path = raw_dir / 'source_config.json'
    additional = load_source_config(config_path)

    # Auto-discover bank/card CSVs when not listed in config
    configured_paths = {entry.get('path', '') for entry in additional}
    for name in ('bank.csv', 'credit_card.csv', 'bank_export.csv'):
        if name in configured_paths:
            continue
        candidate = raw_dir / name
        if candidate.exists():
            source_label = 'credit_card' if 'credit' in name else 'bank'
            additional.append({'path': name, 'source': source_label})

    return alipay_path, wechat_path, additional


def load_transactions(alipay_path: Optional[str] = None,
                    wechat_path: Optional[str] = None,
                    additional_sources: Optional[List[dict]] = None,
                    raw_dir: Optional[Path] = None) -> pd.DataFrame:
    """Load and combine transactions from Alipay, WeChat, and optional bank/card exports."""
    dfs = []
    raw_dir = raw_dir or Path(__file__).parent.parent / 'data' / 'raw'

    if alipay_path and Path(alipay_path).exists():
        try:
            print("Parsing Alipay CSV...")
            df_alipay = parse_alipay(alipay_path)
            print(f"  OK - Loaded {len(df_alipay)} transactions")
            dfs.append(df_alipay)
        except Exception as e:
            print(f"  FAIL - Error: {e}")

    if wechat_path and Path(wechat_path).exists():
        try:
            wechat_path_obj = Path(wechat_path)
            if wechat_path_obj.suffix.lower() == '.xlsx':
                print("Parsing WeChat Excel...")
                df_wechat = parse_wechat_excel(wechat_path)
            else:
                print("Parsing WeChat CSV...")
                df_wechat = parse_wechat_csv(wechat_path)
            print(f"  OK - Loaded {len(df_wechat)} transactions")
            dfs.append(df_wechat)
        except Exception as e:
            print(f"  FAIL - Error: {e}")

    for entry in additional_sources or []:
        rel_path = entry.get('path', '')
        full_path = raw_dir / rel_path if not Path(rel_path).is_absolute() else Path(rel_path)
        if not full_path.exists():
            print(f"Skipping missing source: {full_path}")
            continue
        try:
            label = entry.get('source', 'bank')
            print(f"Parsing {label} export ({full_path.name})...")
            df_extra = parse_generic_bank_csv(
                str(full_path),
                source=label,
                column_map=entry.get('column_map'),
                encoding=entry.get('encoding'),
            )
            print(f"  OK - Loaded {len(df_extra)} transactions")
            dfs.append(df_extra)
        except Exception as e:
            print(f"  FAIL - {full_path.name}: {e}")

    if not dfs:
        raise ValueError("Must provide at least one valid file path")

    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.sort_values('timestamp').reset_index(drop=True)

    return combined


def save_processed(df: pd.DataFrame, output_path: str) -> None:
    """Save processed transactions to CSV."""
    df.to_csv(output_path, index=False)
    print(f"Saved processed data to {output_path}")


if __name__ == '__main__':
    base_path = Path(__file__).parent.parent
    alipay_path, wechat_path, additional = resolve_raw_paths(base_path)

    if not alipay_path and not wechat_path and not additional:
        print("Error: No raw files found in data/raw/")
        print("  Expected: alipay.csv, raw-wechat.xlsx, and/or bank.csv")
        print("  Optional: data/raw/source_config.json for custom column mappings")
        raise SystemExit(1)

    print(f"Alipay: {alipay_path or '(not found)'}")
    print(f"WeChat: {wechat_path or '(not found)'}")
    if additional:
        print(f"Extra sources: {', '.join(e.get('path', '?') for e in additional)}")

    try:
        df = load_transactions(
            str(alipay_path) if alipay_path else None,
            str(wechat_path) if wechat_path else None,
            additional_sources=additional,
            raw_dir=base_path / 'data' / 'raw',
        )

        print(f"\n{'='*70}")
        print(f"Successfully loaded {len(df)} total transactions")
        print(f"Date range: {df['timestamp'].min().date()} to {df['timestamp'].max().date()}")

        for src in sorted(df['source'].unique()):
            src_df = df[df['source'] == src]
            print(f"  - {src}: {len(src_df)} transactions (¥{src_df['amount'].sum():,.2f})")

        print(f"Total spend: {df['amount'].sum():,.2f}")

        print(f"\n{'='*70}")
        stats = df['amount'].describe()
        print(f"  Count: {int(stats['count'])}")
        print(f"  Mean: {stats['mean']:.2f}")
        print(f"  Median: {df['amount'].median():.2f}")

        output_file = base_path / 'data' / 'processed' / 'transactions.csv'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        save_processed(df, str(output_file))

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        raise SystemExit(1)
