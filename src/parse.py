"""CSV/Excel parsers for Alipay, WeChat, and generic bank/card exports.

Parser version 2 (API v5, docs/contracts/API_V5.md §1.1 / §3.9).

Every parser returns the same schema:

    timestamp | merchant | description | amount | source | kind | flow_subtype

`kind` is 'expense' | 'income' | 'transfer'; `flow_subtype` is one of the
contract's subtypes or None. Sign convention (contract §1.1): for expense and
transfer rows `+` = money left the user and `-` = money came in; income rows
are `+`. Refunds are negative expense rows with flow_subtype 'refund'.

Version 1 kept only expense + refund rows. Version 2 keeps every settled row
and types it, but expense and refund rows keep exactly the
(timestamp, merchant, description) that version 1 produced - only amounts may
differ (partial refunds, see `_classify_wallet_rows`). The re-import algorithm
in backend/routes/uploads.py matches on that key.

The ML pipeline (training, classification) must only ever see expense rows:
`load_transactions` filters kind == 'expense'.
"""
import csv
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

PARSER_VERSION = 2
OUTPUT_COLUMNS = ['timestamp', 'merchant', 'description', 'amount', 'source', 'kind', 'flow_subtype']
_ENCODINGS = ('utf-8-sig', 'utf-8', 'gbk', 'gb18030')
_PREVIEW_ROWS = 60

# ---------------------------------------------------------------------------
# Keyword tables. Every Chinese literal carries its English meaning.
# Matching is substring-based on the wallet's own transaction-type column plus
# the counterparty and description text, so the SAME tables serve Alipay
# (CN + EN exports) and WeChat (XLSX + CSV) - W-13 parity by construction.
# ---------------------------------------------------------------------------

# Direction column values (收/支 = "income/expense").
_DIR_OUT = {'支出', 'expense', 'expenses'}        # 支出 = expense (money out)
_DIR_IN = {'收入', 'income'}                       # 收入 = income (money in)
# Anything else (不计收支 = "not counted", '/', empty) is neutral.

# Credit card / consumer-credit repayment -> transfer/repayment.
_REPAYMENT_RE = re.compile(
    r'(信用卡|花呗|还呗|借呗|白条|贷款).*还款'   # credit card | Huabei | Huanbei | Jiebei | Baitiao | loan ... repayment
    r'|还款.*(信用卡|花呗|借呗)'                # repayment ... credit card | Huabei | Jiebei
    r'|信用借还'                                # "credit & loans" (Alipay category)
    r'|repayment',
    re.IGNORECASE,
)
_WITHDRAWAL_RE = re.compile(r'提现|withdraw', re.IGNORECASE)          # 提现 = withdraw to bank card
_TOPUP_RE = re.compile(r'充值|top-?\s?up|recharge', re.IGNORECASE)   # 充值 = top-up / recharge
_WALLET_TOPUP_RE = re.compile(r'零钱充值|balance top-?\s?up', re.IGNORECASE)  # 零钱充值 = WeChat wallet top-up
# Money-market funds held inside the wallet: moving money in/out of them is
# moving between the user's own accounts.
_MONEY_MARKET_RE = re.compile(
    r"余额宝|零钱通|理财通|yu'?e\s?bao|yuebao|lingqiantong|licaitong",   # 余额宝 = Yu'e Bao, 零钱通 = WeChat Lingqiantong, 理财通 = WeChat Licaitong
    re.IGNORECASE,
)
_EARNINGS_RE = re.compile(r'收益|利息|结息|earning|interest|yield', re.IGNORECASE)  # 收益 = earnings, 利息 = interest, 结息 = interest settlement
_OUTFLOW_FROM_FUND_RE = re.compile(r'转出|transfer out|withdrawn', re.IGNORECASE)  # 转出 = transfer out (of the fund, back into the wallet)
_AA_RE = re.compile(r'群收款|aa收款|aa制|group collection|split bill', re.IGNORECASE)  # 群收款 = group collection, AA收款 = split-bill collection, AA制 = going Dutch
_RED_PACKET_RE = re.compile(r'红包|red packet|red envelope|hongbao', re.IGNORECASE)  # 红包 = red packet
_TRANSFER_RE = re.compile(r'转账|transfer', re.IGNORECASE)                          # 转账 = transfer (to/from a person)
# A credit-card statement's "payment received" line: money IN to the card.
_CARD_PAYMENT_RECEIVED_RE = re.compile(r'payment\s+(thank\s*you|received)|还款入账', re.IGNORECASE)  # 还款入账 = repayment credited
_SALARY_RE = re.compile(r'工资|薪资|薪酬|薪金|代发|奖金|salary|payroll|wage', re.IGNORECASE)  # 工资 = wages, 薪资/薪酬/薪金 = salary, 代发 = payroll disbursement, 奖金 = bonus
# Alipay's combined category 转账红包 ("transfers & red packets") must not by
# itself make every row a red packet - the description decides.
_COMBINED_TRANSFER_CATEGORY_RE = re.compile(r'转账红包|transfers?\s*&\s*red packets?', re.IGNORECASE)

# Status text (交易状态 / 当前状态 = "transaction status" / "current status").
_REFUND_RE = re.compile(r'退款|refund', re.IGNORECASE)                # 退款 = refund
_PARTIAL_RE = re.compile(r'部分|partial', re.IGNORECASE)              # 部分 = partial
_FULL_REFUND_RE = re.compile(r'全额|full', re.IGNORECASE)             # 全额 = full amount
_CLOSED_RE = re.compile(r'交易关闭|已关闭|\bclosed\b', re.IGNORECASE)  # 交易关闭 = transaction closed, 已关闭 = closed
_STATUS_AMOUNT_RE = re.compile(r'[￥¥]\s*([0-9][0-9,]*(?:\.[0-9]+)?)')  # e.g. 已退款(￥30.00) = "refunded (¥30.00)"
_SETTLED_RE = re.compile(
    r'成功'          # success (交易成功 trade successful, 支付成功 paid, 还款成功 repaid, 充值成功 topped up, 提现成功 withdrawn)
    r'|已完成'       # completed
    r'|已到账'       # arrived (提现已到账 = withdrawal arrived)
    r'|已收款'       # payment received
    r'|已支付'       # paid
    r'|已转账'       # transferred
    r'|已存入'       # deposited (已存入零钱 = deposited to wallet balance)
    r'|已收钱'       # received the money (已收钱; also 朋友已收钱 = friend has received the money, 对方已收钱 = other party received)
    r'|充值完成'     # top-up complete
    r'|success|completed|transferred|received|deposited|arrived|\bpaid\b',
    re.IGNORECASE,
)
_UNSETTLED_RE = re.compile(
    r'失败'          # failed
    r'|等待'         # waiting (等待付款 = awaiting payment)
    r'|处理中'       # processing
    r'|未支付|未付款' # unpaid
    r'|已撤销'       # cancelled
    r'|已退还'       # returned (对方已退还 = the recipient sent the transfer back)
    r'|fail|pending|waiting|processing|cancel|returned|unpaid',
    re.IGNORECASE,
)

# Payment-wallet counterparties on a BANK statement (contract §3.9): the
# purchase itself is already in the Alipay/WeChat statement, so the bank leg
# is an own-account transfer.
_WALLET_COUNTERPARTY_RE = re.compile(
    r'支付宝|财付通|微信支付|微信零钱|微信转账|alipay|tenpay|wechat\s?pay|weixin',  # 支付宝 = Alipay, 财付通 = Tenpay, 微信支付 = WeChat Pay, 微信零钱 = WeChat balance, 微信转账 = WeChat transfer
    re.IGNORECASE,
)

# Header metadata line marking a filtered export, e.g. Alipay
# "导出交易类型：[全部]" (export transaction type: [all]) or WeChat
# "导出类型：[全部]" (export type: [all]). Anything other than "all" means the
# user filtered by type before exporting, so rows missing from the file are not
# evidence that they never happened (backend skips re-import deletions).
_FILTER_LINE_RE = re.compile(
    r'(导出交易类型|导出类型|交易类型|收/支|export (?:transaction )?type|transaction type)\s*[：:]\s*\[([^\]]*)\]',  # 导出交易类型 = export transaction type, 导出类型 = export type, 交易类型 = transaction type, 收/支 = income/expense
    re.IGNORECASE,
)
_UNFILTERED_VALUES = {'全部', 'all', ''}   # 全部 = all


# ---------------------------------------------------------------------------
# Column aliases
# ---------------------------------------------------------------------------

# Generic bank / credit-card statement headers.
_COLUMN_ALIASES: Dict[str, List[str]] = {
    'timestamp': [
        '交易时间',   # transaction time
        '交易日期',   # transaction date
        '记账日期',   # booking date
        '入账日期',   # posting date
        '发生时间',   # occurred at
        '发生日期',   # occurred on
        '交易日',     # trade day
        '日期',       # date
        'Transaction Time', 'Transaction Date', 'Date', 'Posting Date',
        'Booking Date', 'Value Date', 'Trans Date', 'Post Date',
    ],
    'time': ['交易时间', '时间', 'Time', 'Transaction Time'],   # 交易时间 = transaction time, 时间 = time
    'amount': [
        '金额',          # amount
        '交易金额',      # transaction amount
        '入账金额',      # posted amount
        '发生额',        # amount incurred
        '交易金额(元)',  # transaction amount (CNY)
        '金额(元)',      # amount (CNY)
        'Amount', 'Amount (CNY)', 'Transaction Amount',
    ],
    'debit': [
        '支出',          # expense
        '支出金额',      # expense amount
        '借方金额',      # debit amount
        '借方发生额',    # debit turnover
        '借方',          # debit
        '付款金额',      # payment amount
        '转出金额',      # amount transferred out
        'Debit', 'Debit Amount', 'Withdrawal', 'Withdrawals',
        'Withdrawal Amount', 'Money Out', 'Paid Out',
    ],
    'credit': [
        '收入',          # income
        '收入金额',      # income amount
        '存入金额',      # deposit amount
        '贷方金额',      # credit amount
        '贷方发生额',    # credit turnover
        '贷方',          # credit
        '收款金额',      # amount received
        '转入金额',      # amount transferred in
        'Credit', 'Credit Amount', 'Deposit', 'Deposits', 'Deposit Amount',
        'Money In', 'Paid In',
    ],
    'merchant': [
        '交易对方',      # counterparty
        '对方户名',      # counterparty account name
        '对方账户名',    # counterparty account name
        '对方名称',      # counterparty name
        '对方账号名称',  # counterparty account name
        '收/付款方',     # payee/payer
        '商户名称',      # merchant name
        '商户',          # merchant
        'Counterparty', 'Counterparty Name', 'Merchant', 'Payee',
        'Payee Name', 'Payer/Payee',
    ],
    'description': [
        '商品说明',      # product description
        '商品',          # product
        '摘要',          # summary
        '交易摘要',      # transaction summary
        '交易备注',      # transaction note
        '备注',          # note
        '用途',          # purpose
        '附言',          # remark
        '交易说明',      # transaction description
        'Product Description', 'Product', 'Memo', 'Narrative', 'Details',
        'Description', 'Reference', 'Remarks',
    ],
    'direction': [
        '收/支',         # income/expense
        '借贷标志',      # debit/credit flag
        '借贷',          # debit/credit
        '借/贷',         # debit/credit
        '收支类型',      # income/expense type
        '收支',          # income/expense
        'Income/Expense', 'Dr/Cr', 'D/C', 'Debit/Credit', 'Type',
    ],
    'type': [
        '交易类型',      # transaction type
        '交易种类',      # transaction kind
        '业务类型',      # business type
        'Transaction Type',
    ],
}

# Bank direction-column values.
_BANK_OUT = {'支出', '借', '借方', '出', 'd', 'dr', 'debit', 'expense', 'out', 'withdrawal'}  # 支出 = expense, 借/借方 = debit, 出 = out
_BANK_IN = {'收入', '贷', '贷方', '入', 'c', 'cr', 'credit', 'income', 'in', 'deposit'}       # 收入 = income, 贷/贷方 = credit, 入 = in


def _norm_header(value) -> str:
    return str(value).replace('﻿', '').strip().strip('\t').strip().lower()


def _find_column(df: pd.DataFrame, field: str, override: Optional[str] = None,
                 exclude: Tuple[str, ...] = ()) -> Optional[str]:
    """Resolve a dataframe column name from aliases (case-insensitive) or an
    explicit mapping."""
    if override and override in df.columns:
        return override
    by_norm = {}
    for col in df.columns:
        by_norm.setdefault(_norm_header(col), col)
    for candidate in _COLUMN_ALIASES.get(field, []):
        col = by_norm.get(_norm_header(candidate))
        if col is not None and col not in exclude:
            return col
    return None


def _clean_text(series: pd.Series) -> pd.Series:
    """Exactly v1's text normalisation (keeps the re-import key stable)."""
    return series.fillna('').astype(str).str.strip()


def _parse_amount_series(series: pd.Series) -> pd.Series:
    """'¥1,234.50' / '(30.00)' / ' 12 ' -> float (NaN when not a number)."""
    cleaned = (
        series.astype(str)
        .str.replace(',', '', regex=False)
        .str.replace('¥', '', regex=False)
        .str.replace('￥', '', regex=False)
        .str.replace('\t', '', regex=False)
        .str.strip()
    )
    negative_parens = cleaned.str.match(r'^\(.*\)$')
    cleaned = cleaned.str.replace(r'^\((.*)\)$', r'\1', regex=True)
    numbers = pd.to_numeric(cleaned, errors='coerce')
    return numbers.mask(negative_parens, -numbers)


def _to_timestamp(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    return pd.to_datetime(series.map(lambda v: v.strip() if isinstance(v, str) else v), errors='coerce')


def _empty_output(source: str) -> pd.DataFrame:
    df = pd.DataFrame({c: pd.Series(dtype='object') for c in OUTPUT_COLUMNS})
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['amount'] = df['amount'].astype(float)
    return df


# ---------------------------------------------------------------------------
# Shared wallet (Alipay / WeChat) classification
# ---------------------------------------------------------------------------

def _direction(value) -> str:
    v = _norm_header(value)
    if v in _DIR_OUT:
        return 'out'
    if v in _DIR_IN:
        return 'in'
    return 'neutral'


def _dir_sign(direction: str, text: str = '') -> int:
    """+1 = money left the user, -1 = money came in."""
    if direction == 'in':
        return -1
    if direction == 'out':
        return 1
    return -1 if _OUTFLOW_FROM_FUND_RE.search(text) else 1


def classify_wallet_flow(direction: str, type_text: str, merchant: str,
                         description: str) -> Tuple[str, Optional[str], int]:
    """(kind, flow_subtype, sign) for a settled, non-refund wallet row.

    `direction` is 'out' / 'in' / 'neutral'. The returned sign is applied to
    the absolute amount. Rules, first match wins:

    1. repayment (credit card / Huabei / loan)   -> transfer/repayment, +
    2. money-market earnings (余额宝 收益 ...)     -> income/interest, +
    3. money-market move (余额宝/零钱通/理财通)    -> transfer/own_account, +/-
       (checked before withdrawal so "Yu'e Bao ... withdrawn" stays a move
       between the user's own balances, not a wallet withdrawal)
    4. withdrawal (提现)                          -> transfer/withdrawal, +
    5. wallet top-up (零钱充值, or 充值 when not
       counted as income/expense)                 -> transfer/top_up, -
    6. group collection (群收款/AA)               -> in: transfer/aa_collection, -
                                                     out: expense, +
       Paying your share into a friend's group collection is your real
       spending (user decision 2026-10-11), so it is an expense to label like
       any purchase; receiving shares back stays a transfer.
    7. red packet (红包)                          -> transfer/red_packet, +/-
    8. transfer (转账)                            -> transfer/p2p_transfer, +/-
    9. by direction: out -> expense; in -> income/salary | interest | other;
       neutral (不计收支 "not counted", '/') -> transfer/own_account. The wallet
       itself puts a row in the neutral bucket precisely because it does not
       change the user's money (moves between own balances, fund purchases).
    """
    type_text = type_text or ''
    type_clean = _COMBINED_TRANSFER_CATEGORY_RE.sub(' ', type_text)
    text = ' '.join([type_text, merchant or '', description or ''])
    type_desc = ' '.join([type_text, description or ''])
    sign = _dir_sign(direction, type_desc)

    if _REPAYMENT_RE.search(type_desc):
        return 'transfer', 'repayment', 1
    if _MONEY_MARKET_RE.search(text):
        if _EARNINGS_RE.search(type_desc):
            return 'income', 'interest', 1
        return 'transfer', 'own_account', sign
    if _WITHDRAWAL_RE.search(type_desc):
        return 'transfer', 'withdrawal', 1
    if _WALLET_TOPUP_RE.search(type_text) or (direction == 'neutral' and _TOPUP_RE.search(type_desc)):
        return 'transfer', 'top_up', -1
    if _AA_RE.search(type_desc):
        if direction == 'out':
            return 'expense', None, 1
        return 'transfer', 'aa_collection', -1
    is_combined_category = type_clean != type_text
    if _RED_PACKET_RE.search(type_clean) or (
        (is_combined_category or not type_text.strip()) and _RED_PACKET_RE.search(description or '')
    ):
        return 'transfer', 'red_packet', sign
    if _TRANSFER_RE.search(type_text) or _TRANSFER_RE.search(description or ''):
        return 'transfer', 'p2p_transfer', sign

    if direction == 'out':
        return 'expense', None, 1
    if direction == 'in':
        if _SALARY_RE.search(text):
            return 'income', 'salary', 1
        if _EARNINGS_RE.search(type_desc):
            return 'income', 'interest', 1
        return 'income', 'other', 1
    return 'transfer', 'own_account', sign


def _refund_row_flow(type_text: str, description: str) -> Tuple[str, Optional[str]]:
    """A row that IS money coming back. A returned red packet / transfer
    reverses a transfer, so it stays a transfer (negative); anything else is a
    purchase refund (negative expense)."""
    type_clean = _COMBINED_TRANSFER_CATEGORY_RE.sub(' ', type_text or '')
    if _RED_PACKET_RE.search(type_clean):
        return 'transfer', 'red_packet'
    if _TRANSFER_RE.search(type_clean) and not _COMBINED_TRANSFER_CATEGORY_RE.search(type_text or ''):
        return 'transfer', 'p2p_transfer'
    return 'expense', 'refund'


def _status_refund_amount(status: str) -> Optional[float]:
    m = _STATUS_AMOUNT_RE.search(status or '')
    if not m:
        return None
    try:
        return float(m.group(1).replace(',', ''))
    except ValueError:
        return None


def _link_ids(row: dict, other: dict) -> bool:
    """Order-number link between an original row and a refund row."""
    a, b = row.get('order_id') or '', other.get('order_id') or ''
    if len(a) >= 8 and len(b) >= 8 and (b.startswith(a) or a.startswith(b)):
        return True
    ma, mb = row.get('merchant_order_id') or '', other.get('merchant_order_id') or ''
    return bool(ma) and ma not in ('/', '-') and ma == mb


def _pair_refunds(row: dict, target: float, refund_rows: List[dict]) -> bool:
    """Consume refund rows (same counterparty or linked order number, dated at
    or after `row`) whose amounts add up to `target`. Returns True on success."""
    candidates = [
        r for r in refund_rows
        if not r['consumed'] and r['ts'] >= row['ts']
        and (r['merchant'] == row['merchant'] or _link_ids(row, r))
    ]
    picked, total = [], 0.0
    for r in candidates:   # refund_rows are in time order
        if total + r['abs_amount'] <= target + 0.005:
            picked.append(r)
            total += r['abs_amount']
        if abs(total - target) < 0.005:
            for p in picked:
                p['consumed'] = True
            return True
    return False


def _classify_wallet_rows(frame: pd.DataFrame, source: str) -> pd.DataFrame:
    """Turn the canonical wallet frame into the output schema.

    `frame` columns: ts (datetime), merchant, description (v1-normalised
    text), direction ('out'/'in'/'neutral'), type_text, status, abs_amount,
    order_id, merchant_order_id.

    Refund handling (W-10 fixes a and c):

    * A **refund row** is a row whose status says 退款 (refund) and which is not
      itself a purchase - i.e. its direction is not 支出 (expense), or its type
      says 退款. It becomes -amount (expense/refund, or a negative transfer for a
      returned red packet / transfer). Unchanged from v1 apart from that typing.
    * An **annotated original** is a 支出 (expense) row whose status carries a
      refund note, e.g. WeChat 已退款(￥30.00) "refunded (¥30.00)" or 已全额退款
      "fully refunded". Refunded amount R = the amount in the status, else the
      whole amount (full refund).
        - If refund rows for it exist in the same file (same counterparty or
          linked order number, dated at/after it, amounts summing to R) the
          refund is already carried by those rows: the original stays a normal
          purchase at +amount (net = amount - R).
        - Otherwise a partial refund keeps only the unrefunded part:
          amount - R (approved fix a: "negate only the refunded amount").
        - Otherwise a full refund keeps v1's behaviour: -amount (refund).
    * A **closed** row (交易关闭 "transaction closed") counts only when it was
      paid. Evidence of payment = refund rows in the same file adding up to its
      amount (Alipay closes an order after a full refund). Without them the
      order was never paid and the row is ignored (approved fix c).
    * Anything else must have a settled status (incl. 朋友已收钱 "friend has
      received the money", fix b) and is typed by `classify_wallet_flow`.
    """
    if frame.empty:
        return _empty_output(source)

    records = frame.to_dict('records')
    for i, r in enumerate(records):
        r['idx'] = i
        r['consumed'] = False
        status = r['status']
        has_refund_status = bool(_REFUND_RE.search(status))
        type_says_refund = bool(_REFUND_RE.search(r['type_text']))
        r['is_refund_row'] = (has_refund_status or type_says_refund) and (
            r['direction'] != 'out' or type_says_refund
        )
        r['is_annotated_original'] = has_refund_status and not r['is_refund_row']
        r['is_closed'] = (
            not has_refund_status and not r['is_refund_row'] and bool(_CLOSED_RE.search(status))
        )

    refund_rows = sorted((r for r in records if r['is_refund_row']), key=lambda r: (r['ts'], r['idx']))

    # Pairing pass, oldest first so each refund row backs at most one original.
    paired = set()
    for r in sorted(records, key=lambda r: (r['ts'], r['idx'])):
        if r['is_annotated_original']:
            refunded = _status_refund_amount(r['status'])
            target = refunded if refunded is not None else r['abs_amount']
            r['refunded'] = min(target, r['abs_amount'])
        elif r['is_closed']:
            target = r['abs_amount']
        else:
            continue
        if target > 0 and _pair_refunds(r, target, refund_rows):
            paired.add(r['idx'])

    out = []
    skipped_closed = 0
    for r in records:
        amt = r['abs_amount']
        if r['is_refund_row']:
            kind, subtype = _refund_row_flow(r['type_text'], r['description'])
            out.append((r, kind, subtype, -amt))
            continue

        if r['is_closed']:
            if r['idx'] not in paired:
                skipped_closed += 1
                continue
        elif not r['is_annotated_original']:
            status = r['status']
            if _UNSETTLED_RE.search(status) or not _SETTLED_RE.search(status):
                continue

        kind, subtype, sign = classify_wallet_flow(
            r['direction'], r['type_text'], r['merchant'], r['description'],
        )

        if r['is_annotated_original'] and r['idx'] not in paired:
            refunded = r['refunded']
            partial = refunded < amt - 0.005 or (
                _PARTIAL_RE.search(r['status']) and not _FULL_REFUND_RE.search(r['status'])
                and _status_refund_amount(r['status']) is None
            )
            if partial and _status_refund_amount(r['status']) is None:
                # "partial refund" with no amount we can read: the refund
                # itself is not in this file, so keep the purchase as-is.
                out.append((r, kind, subtype, sign * amt))
            elif partial:
                out.append((r, kind, subtype, sign * round(amt - refunded, 2)))
            elif kind == 'expense':
                out.append((r, 'expense', 'refund', -amt))      # v1 behaviour for a full refund
            # A fully refunded transfer nets to zero: nothing to keep.
            continue

        out.append((r, kind, subtype, sign * amt))

    if skipped_closed:
        logger.info("%s: ignored %d closed, unpaid order(s)", source, skipped_closed)

    if not out:
        return _empty_output(source)

    out.sort(key=lambda item: item[0]['idx'])   # file order
    result = pd.DataFrame({
        'timestamp': pd.to_datetime([o[0]['ts'] for o in out]),
        'merchant': [o[0]['merchant'] for o in out],
        'description': [o[0]['description'] for o in out],
        'amount': [round(float(o[3]), 2) for o in out],
        'source': source,
        'kind': [o[1] for o in out],
        'flow_subtype': pd.Series([o[2] for o in out], dtype='object'),
    })
    result['flow_subtype'] = result['flow_subtype'].astype(object).where(result['flow_subtype'].notna(), None)
    return result


def _wallet_frame(df: pd.DataFrame, cols: Dict[str, Optional[str]]) -> pd.DataFrame:
    """Build the canonical wallet frame from a raw export dataframe.

    cols: ts, merchant, description, direction, amount, status (required);
    type, order_id, merchant_order_id (optional).
    """
    def text(key):
        col = cols.get(key)
        if col is None or col not in df.columns:
            return pd.Series([''] * len(df), index=df.index)
        return _clean_text(df[col])

    frame = pd.DataFrame({
        'ts': _to_timestamp(df[cols['ts']]),
        'merchant': _clean_text(df[cols['merchant']]),
        'description': _clean_text(df[cols['description']]),
        'direction': df[cols['direction']].map(_direction),
        'type_text': text('type'),
        'status': text('status'),
        'abs_amount': _parse_amount_series(df[cols['amount']]).abs(),
        'order_id': text('order_id'),
        'merchant_order_id': text('merchant_order_id'),
    }, index=df.index)
    return frame[frame['ts'].notna() & frame['abs_amount'].notna()]


# ---------------------------------------------------------------------------
# Reading helpers
# ---------------------------------------------------------------------------

def _read_preview(path: str, n: int = _PREVIEW_ROWS) -> Tuple[List[List[str]], Optional[str]]:
    """First `n` rows of a CSV or XLSX file as lists of cell strings, plus the
    CSV encoding that worked (None for XLSX)."""
    if str(path).lower().endswith('.xlsx'):
        raw = pd.read_excel(path, header=None, nrows=n, dtype=object)
        rows = [['' if pd.isna(v) else str(v) for v in row] for row in raw.itertuples(index=False)]
        return rows, None
    for enc in _ENCODINGS:
        try:
            with open(path, encoding=enc, newline='') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= n:
                        break
                    lines.append(line)
        except (UnicodeDecodeError, LookupError):
            continue
        rows = []
        for line in lines:
            try:
                rows.append(next(csv.reader([line])))
            except (csv.Error, StopIteration):
                rows.append([line])
        return rows, enc
    raise ValueError(f"Cannot read file encoding: {path}")


def _cells(row: List[str]) -> set:
    return {_norm_header(c) for c in row if str(c).strip()}


def _is_wechat_header(cells: set) -> bool:
    # 交易时间 = transaction time, 当前状态 = current status, 交易类型 = transaction type,
    # 金额(元) = amount (CNY), 交易对方 = counterparty
    # 交易类型 + 金额(元) alone also appear in some Chinese bank exports, so
    # that variant additionally needs WeChat's 交易对方 (counterparty) column.
    if '交易时间' in cells and ('当前状态' in cells or (
            '交易类型' in cells and '金额(元)' in cells and '交易对方' in cells)):
        return True
    return 'transaction time' in cells and 'current status' in cells


def _is_alipay_header(cells: set) -> bool:
    # 交易时间 = transaction time, 收/支 = income/expense, 交易状态 = transaction status
    if '交易时间' in cells and '收/支' in cells and '交易状态' in cells:
        return True
    return 'transaction time' in cells and 'transaction status' in cells


def _alias_set(field: str) -> set:
    return {_norm_header(a) for a in _COLUMN_ALIASES[field]}


def _is_bank_header(cells: set) -> bool:
    has_date = bool(cells & _alias_set('timestamp'))
    has_money = bool(cells & (_alias_set('amount') | _alias_set('debit') | _alias_set('credit')))
    return has_date and has_money


def _find_header(rows: List[List[str]], predicate) -> Optional[int]:
    for i, row in enumerate(rows):
        if predicate(_cells(row)):
            return i
    return None


def detect_statement_source(path: str) -> Optional[str]:
    """'wechat' | 'alipay' | 'bank' | None, by header row content.

    Order (contract §3.9): WeChat markers, then Alipay markers, then a bank
    statement (a recognisable date column AND an amount or debit/credit
    column). Each check looks at the same header row the parser will use."""
    try:
        rows, _ = _read_preview(path)
    except Exception as e:
        logger.warning("Could not read %s for detection: %s", path, e)
        return None
    if _find_header(rows, _is_wechat_header) is not None:
        return 'wechat'
    if _find_header(rows, _is_alipay_header) is not None:
        return 'alipay'
    if _find_header(rows, _is_bank_header) is not None:
        return 'bank'
    return None


def detect_export_filter(path: str) -> Optional[str]:
    """Return the filter text (e.g. '支出' "expense") when the export's header
    metadata says it was filtered by type before exporting, else None."""
    try:
        rows, _ = _read_preview(path)
    except Exception:
        return None
    for row in rows:
        line = ' '.join(str(c) for c in row)
        for m in _FILTER_LINE_RE.finditer(line):
            value = m.group(2).strip()
            if value.lower() not in _UNFILTERED_VALUES:
                return value
    return None


def _read_table(path: str, header_idx: int, encoding: Optional[str]) -> pd.DataFrame:
    """Read the statement table whose header is at row `header_idx`."""
    if str(path).lower().endswith('.xlsx'):
        raw = pd.read_excel(path, header=None, dtype=object)
        header = [str(c).strip() if not pd.isna(c) else f'col{i}' for i, c in enumerate(raw.iloc[header_idx])]
        df = raw.iloc[header_idx + 1:].reset_index(drop=True)
        df.columns = _dedupe_headers(header)
        return df.dropna(how='all')
    df = pd.read_csv(path, encoding=encoding, skiprows=header_idx, dtype=str,
                     keep_default_na=False, na_values=[''])
    df.columns = _dedupe_headers([str(c).replace('﻿', '').strip() for c in df.columns])
    return df.dropna(how='all')


def _dedupe_headers(names: List[str]) -> List[str]:
    seen: Dict[str, int] = {}
    out = []
    for n in names:
        if n in seen:
            seen[n] += 1
            out.append(f"{n}.{seen[n]}")
        else:
            seen[n] = 0
            out.append(n)
    return out


# ---------------------------------------------------------------------------
# Alipay
# ---------------------------------------------------------------------------

def _find_alipay_header(csv_path: str) -> Tuple[int, str, bool]:
    """Locate the Alipay data header row and encoding.

    Returns (skiprows, encoding, is_chinese_format)."""
    for encoding in _ENCODINGS:
        try:
            with open(csv_path, encoding=encoding) as f:
                for i, line in enumerate(f):
                    if 'Transaction Time' in line and 'Type' in line:
                        return i, encoding, False
                    if '交易时间' in line and '收/支' in line:   # transaction time, income/expense
                        return i, encoding, True
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Cannot detect Alipay CSV format: {csv_path}")


def _read_alipay_csv(csv_path: str, encoding: str, skiprows: int) -> pd.DataFrame:
    df = pd.read_csv(csv_path, encoding=encoding, skiprows=skiprows, dtype=str,
                     keep_default_na=False, na_values=[''])
    df.columns = [str(c).replace('﻿', '').strip() for c in df.columns]
    return df


def parse_alipay_english(csv_path: str, encoding: str = 'utf-8', skiprows: int = 0) -> pd.DataFrame:
    """Parse an English-header Alipay export CSV (all settled rows, typed)."""
    df = _read_alipay_csv(csv_path, encoding, skiprows)
    frame = _wallet_frame(df, {
        'ts': 'Transaction Time',
        'merchant': 'Transaction Counterparty',
        'description': 'Product Description',
        'direction': 'Type',
        'amount': 'Amount',
        'status': 'Transaction Status',
        'type': _find_column(df, 'type') or next(
            (c for c in ('Transaction Category', 'Category') if c in df.columns), None),
        'order_id': next((c for c in ('Transaction Order Number', 'Transaction ID', 'Order Number') if c in df.columns), None),
        'merchant_order_id': next((c for c in ('Merchant Order Number', 'Merchant Order ID') if c in df.columns), None),
    })
    return _classify_wallet_rows(frame, 'alipay')


def parse_alipay_native(csv_path: str, encoding: str = 'gbk', skiprows: int = 0) -> pd.DataFrame:
    """Parse a native Chinese Alipay export CSV (GBK/UTF-8)."""
    df = _read_alipay_csv(csv_path, encoding, skiprows)
    type_col = next((c for c in ('交易分类', '交易类型') if c in df.columns), None)   # transaction category, transaction type
    frame = _wallet_frame(df, {
        'ts': '交易时间',            # transaction time
        'merchant': '交易对方',      # counterparty
        'description': '商品说明',   # product description
        'direction': '收/支',        # income/expense
        'amount': '金额',            # amount
        'status': '交易状态',        # transaction status
        'type': type_col,
        'order_id': next((c for c in ('交易订单号', '交易号') if c in df.columns), None),        # transaction order number, transaction number
        'merchant_order_id': next((c for c in ('商家订单号', '商户订单号') if c in df.columns), None),  # merchant order number
    })
    return _classify_wallet_rows(frame, 'alipay')


def parse_alipay(csv_path: str) -> pd.DataFrame:
    """Parse Alipay CSV - auto-detects English vs native Chinese export."""
    skiprows, encoding, is_chinese = _find_alipay_header(csv_path)
    if is_chinese:
        return parse_alipay_native(csv_path, encoding=encoding, skiprows=skiprows)
    return parse_alipay_english(csv_path, encoding=encoding, skiprows=skiprows)


# ---------------------------------------------------------------------------
# WeChat
# ---------------------------------------------------------------------------

# WeChat header -> canonical key. Chinese and English exports.
_WECHAT_COLUMNS = {
    'ts': ('交易时间', 'Transaction Time'),                       # transaction time
    'type': ('交易类型', 'Transaction Type', 'Type'),             # transaction type
    'merchant': ('交易对方', 'Counterparty'),                     # counterparty
    'description': ('商品', 'Product', 'Goods'),                  # product
    'direction': ('收/支', 'Income/Expense', 'Income/Expenditure'),  # income/expense
    'amount': ('金额(元)', '金额（元）', 'Amount (CNY)', 'Amount(CNY)', 'Amount'),  # amount (CNY)
    'status': ('当前状态', 'Current Status', 'Status'),           # current status
    'order_id': ('交易单号', 'Transaction ID', 'Transaction No.'),  # transaction number
    'merchant_order_id': ('商户单号', 'Merchant ID', 'Merchant Order No.'),  # merchant order number
}


def _wechat_frame(df: pd.DataFrame) -> pd.DataFrame:
    cols = {key: next((c for c in names if c in df.columns), None) for key, names in _WECHAT_COLUMNS.items()}
    missing = [k for k in ('ts', 'merchant', 'description', 'direction', 'amount', 'status') if cols[k] is None]
    if missing:
        raise ValueError(f"WeChat export is missing columns {missing}; found {list(df.columns)}")
    return _wallet_frame(df, cols)


def parse_wechat_excel(xlsx_path: str) -> pd.DataFrame:
    """Parse a WeChat export Excel file (metadata block, then the table)."""
    rows, _ = _read_preview(xlsx_path)
    header_idx = _find_header(rows, _is_wechat_header)
    if header_idx is None:
        raise ValueError("Could not find WeChat transaction table headers")
    df = _read_table(xlsx_path, header_idx, None)
    return _classify_wallet_rows(_wechat_frame(df), 'wechat')


def parse_wechat_csv(csv_path: str) -> pd.DataFrame:
    """Parse a WeChat export CSV (Chinese or English headers, any encoding).

    Same column mapping and the SAME classifier as the XLSX path (W-13)."""
    rows, encoding = _read_preview(csv_path)
    header_idx = _find_header(rows, _is_wechat_header)
    if header_idx is None:
        raise ValueError("Could not find WeChat transaction table headers")
    df = _read_table(csv_path, header_idx, encoding)
    return _classify_wallet_rows(_wechat_frame(df), 'wechat')


# ---------------------------------------------------------------------------
# Generic bank / card statements (W-08)
# ---------------------------------------------------------------------------

_DATE_ONLY_8 = re.compile(r'^\d{8}$')
_TIME_ONLY = re.compile(r'^\d{1,2}:\d{2}(:\d{2})?$')


def _parse_bank_dates(series: pd.Series) -> pd.Series:
    values = series.map(lambda v: '' if pd.isna(v) else str(v).strip().replace('\t', ''))
    # Excel may hand back 20250901 as 20250901.0
    values = values.str.replace(r'^(\d{8})\.0$', r'\1', regex=True)
    non_empty = values[values != '']
    if len(non_empty) and non_empty.str.match(_DATE_ONLY_8).all():
        return pd.to_datetime(values, format='%Y%m%d', errors='coerce')
    return pd.to_datetime(values.where(values != ''), errors='coerce', format='mixed')


def _has_year(series: pd.Series) -> bool:
    sample = series.dropna().astype(str).str.strip()
    sample = sample[sample != ''].head(20)
    if sample.empty:
        return False
    return bool(sample.str.contains(r'\d{4}').mean() >= 0.5)


def _bank_timestamps(df: pd.DataFrame, column_map: Dict[str, str]) -> Optional[pd.Series]:
    override = column_map.get('timestamp')
    candidates = [override] if override and override in df.columns else []
    by_norm = {_norm_header(c): c for c in df.columns}
    for alias in _COLUMN_ALIASES['timestamp']:
        col = by_norm.get(_norm_header(alias))
        if col is not None and col not in candidates:
            candidates.append(col)
    for col in candidates:
        if not _has_year(df[col]):
            continue
        ts = _parse_bank_dates(df[col])
        if ts.notna().sum() == 0:
            continue
        # Date-only column + a separate time-only column (e.g. 交易日期 + 交易时间,
        # "transaction date" + "transaction time") -> combine them.
        if (ts.dropna().dt.normalize() == ts.dropna()).all():
            for tcol in (by_norm.get(_norm_header(a)) for a in _COLUMN_ALIASES['time']):
                if tcol is None or tcol == col:
                    continue
                times = df[tcol].astype(str).str.strip()
                if times[times != ''].str.match(_TIME_ONLY).mean() >= 0.8:
                    combined = pd.to_datetime(
                        ts.dt.strftime('%Y-%m-%d') + ' ' + times.where(times.str.match(_TIME_ONLY), '00:00:00'),
                        errors='coerce',
                    )
                    return combined.fillna(ts)
        return ts
    return None


def classify_bank_flow(direction: str, merchant: str, description: str,
                       type_text: str = '') -> Tuple[str, Optional[str], int]:
    """(kind, flow_subtype, sign) for a bank statement row.

    1. Counterparty/description names a payment wallet (支付宝 Alipay, 财付通
       Tenpay, 微信支付 WeChat Pay) -> transfer/own_account (contract §3.9).
    2. Credit card repayment -> transfer/repayment.
    3. Money in: salary keywords -> income/salary; interest -> income/interest;
       else income/other.
    4. Money out -> expense.
    """
    text = ' '.join([merchant or '', description or '', type_text or ''])
    sign = 1 if direction == 'out' else -1
    if _WALLET_COUNTERPARTY_RE.search(text):
        return 'transfer', 'own_account', sign
    if direction == 'out' and (_REPAYMENT_RE.search(text) or '还款' in text):   # 还款 = repayment
        return 'transfer', 'repayment', 1
    if direction == 'in':
        if _SALARY_RE.search(text):
            return 'income', 'salary', 1
        if _EARNINGS_RE.search(text):
            return 'income', 'interest', 1
        return 'income', 'other', 1
    return 'expense', None, 1


def _bank_direction_value(value) -> Optional[str]:
    v = _norm_header(value)
    if v in _BANK_OUT:
        return 'out'
    if v in _BANK_IN:
        return 'in'
    return None


def _read_bank_table(path: str, encoding: Optional[str], column_map: Dict[str, str]) -> pd.DataFrame:
    if str(path).lower().endswith('.xlsx'):
        rows, enc = _read_preview(path)
    elif encoding:
        rows, enc = _read_preview_with(path, encoding)
    else:
        rows, enc = _read_preview(path)
    override_cells = {_norm_header(v) for v in column_map.values()} if column_map else set()

    def is_header(cells):
        return _is_bank_header(cells) or (override_cells and override_cells <= cells)

    header_idx = _find_header(rows, is_header)
    if header_idx is None:
        header_idx = 0
    return _read_table(path, header_idx, enc)


def _read_preview_with(path: str, encoding: str) -> Tuple[List[List[str]], str]:
    with open(path, encoding=encoding, newline='') as f:
        lines = [line for _, line in zip(range(_PREVIEW_ROWS), f)]
    return [next(csv.reader([line])) if line.strip() else [] for line in lines], encoding


def parse_generic_bank_csv(
    csv_path: str,
    source: str = 'bank',
    column_map: Optional[Dict[str, str]] = None,
    encoding: Optional[str] = None,
) -> pd.DataFrame:
    """Parse a bank / credit-card statement (CSV or XLSX) into the schema.

    Auto-detects common Chinese/English headers (preamble lines are skipped).
    Pass column_map to override detection, e.g.
    {"timestamp": "记账日期", "amount": "支出金额"} ("booking date", "expense amount").

    Direction, first rule that applies:
      1. a direction column (支出/借 debit, 收入/贷 credit, Debit/Credit, D/C);
      2. separate debit / credit columns;
      3. signed amounts when the file mixes signs: the MAJORITY sign is money
         out (most rows on both debit-card and credit-card statements are
         spending, but the two use opposite sign conventions);
      4. otherwise every row is money out (expense).
    """
    column_map = column_map or {}
    try:
        raw = _read_bank_table(csv_path, encoding, column_map)
    except (UnicodeDecodeError, LookupError) as exc:
        raise ValueError(f"Cannot read bank CSV encoding: {csv_path} ({exc})")

    ts = _bank_timestamps(raw, column_map)
    debit_col = _find_column(raw, 'debit', column_map.get('debit'))
    credit_col = _find_column(raw, 'credit', column_map.get('credit'))
    amt_col = _find_column(raw, 'amount', column_map.get('amount'), exclude=tuple(c for c in (debit_col, credit_col) if c))
    if column_map.get('amount') in raw.columns:
        amt_col = column_map['amount']
        debit_col = credit_col = None
    if ts is None or not (amt_col or debit_col or credit_col):
        raise ValueError(
            f"Cannot detect date/amount columns in {csv_path}. "
            f"Found: {list(raw.columns)}. Add column_map in source_config.json."
        )

    merchant_col = _find_column(raw, 'merchant', column_map.get('merchant'))
    desc_col = _find_column(raw, 'description', column_map.get('description'), exclude=(merchant_col,) if merchant_col else ())
    direction_col = _find_column(raw, 'direction', column_map.get('direction'),
                                 exclude=tuple(c for c in (debit_col, credit_col, amt_col) if c))
    type_col = _find_column(raw, 'type', column_map.get('type'), exclude=(direction_col,) if direction_col else ())

    n = len(raw)
    blank = pd.Series([''] * n, index=raw.index)
    description = _clean_text(raw[desc_col]) if desc_col else blank
    if merchant_col:
        merchant = _clean_text(raw[merchant_col])
    else:
        # No counterparty column (e.g. "Date, Description, Amount"): the
        # description IS the merchant text.
        merchant, description = description, blank
    type_text = _clean_text(raw[type_col]) if type_col else blank

    directions: List[Optional[str]] = [None] * n
    amounts = pd.Series([float('nan')] * n, index=raw.index)

    dir_values = raw[direction_col].map(_bank_direction_value) if direction_col else None
    use_direction = dir_values is not None and amt_col is not None and dir_values.notna().any()

    if use_direction or (amt_col and not (debit_col or credit_col)):
        signed = _parse_amount_series(raw[amt_col])
        nz = signed[signed.notna() & (signed != 0)]
        mixed = bool((nz < 0).any() and (nz > 0).any())
        # Which sign means "money out"? Rows that are unmistakably money IN
        # (salary, interest, a card payment received) anchor it first; only
        # without anchors does the majority sign decide (see docstring). This
        # keeps an account that mostly receives money from being flipped.
        anchor_text = (merchant + ' ' + description + ' ' + type_text)
        anchor_in = anchor_text.str.contains(_SALARY_RE) | anchor_text.str.contains(_EARNINGS_RE) | \
            anchor_text.str.contains(_CARD_PAYMENT_RECEIVED_RE)
        anchors = signed[anchor_in & signed.notna() & (signed != 0)]
        if len(anchors) and ((anchors > 0).all() or (anchors < 0).all()):
            out_is_negative = bool((anchors > 0).all())
        else:
            out_is_negative = bool((nz < 0).sum() >= (nz > 0).sum())
        for i, idx in enumerate(raw.index):
            a = signed[idx]
            if pd.isna(a) or a == 0:
                continue
            d = dir_values[idx] if use_direction else None
            if d is None:
                d = ('out' if (a < 0) == out_is_negative else 'in') if mixed else 'out'
            directions[i] = d
            amounts[idx] = abs(a)
    else:
        debit = _parse_amount_series(raw[debit_col]) if debit_col else pd.Series(float('nan'), index=raw.index)
        credit = _parse_amount_series(raw[credit_col]) if credit_col else pd.Series(float('nan'), index=raw.index)
        for i, idx in enumerate(raw.index):
            d, c = debit[idx], credit[idx]
            if pd.notna(d) and d != 0:
                directions[i] = 'out' if d > 0 else 'in'
                amounts[idx] = abs(d)
            elif pd.notna(c) and c != 0:
                directions[i] = 'in' if c > 0 else 'out'
                amounts[idx] = abs(c)

    out = []
    for i, idx in enumerate(raw.index):
        d = directions[i]
        if d is None or pd.isna(ts[idx]) or pd.isna(amounts[idx]):
            continue
        kind, subtype, sign = classify_bank_flow(d, merchant[idx], description[idx], type_text[idx])
        out.append((ts[idx], merchant[idx], description[idx], round(sign * float(amounts[idx]), 2), kind, subtype))

    if not out:
        return _empty_output(source)
    return pd.DataFrame({
        'timestamp': pd.to_datetime([o[0] for o in out]),
        'merchant': [o[1] for o in out],
        'description': [o[2] for o in out],
        'amount': [o[3] for o in out],
        'source': source,
        'kind': [o[4] for o in out],
        'flow_subtype': pd.Series([o[5] for o in out], dtype='object'),
    })


# ---------------------------------------------------------------------------
# CLI pipeline (training / classification): expense rows only
# ---------------------------------------------------------------------------

def load_source_config(config_path: Path) -> List[dict]:
    """Load optional additional source definitions from JSON."""
    if not config_path.exists():
        return []
    with open(config_path, encoding='utf-8') as f:
        data = json.load(f)
    return data.get('additional_sources', [])


def expense_only(df: pd.DataFrame) -> pd.DataFrame:
    """Keep kind == 'expense' rows (refunds included) in the v1 5-column
    shape the ML pipeline expects."""
    if 'kind' in df.columns:
        df = df[df['kind'] == 'expense']
    return df[['timestamp', 'merchant', 'description', 'amount', 'source']].reset_index(drop=True)


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
    """Load and combine EXPENSE transactions (refunds netted) from Alipay,
    WeChat, and optional bank/card exports, for the ML pipeline. Income and
    transfer rows are dropped here - they are never trained on or classified."""
    dfs = []
    raw_dir = raw_dir or Path(__file__).parent.parent / 'data' / 'raw'

    if alipay_path and Path(alipay_path).exists():
        try:
            print("Parsing Alipay CSV...")
            df_alipay = expense_only(parse_alipay(alipay_path))
            print(f"  OK - Loaded {len(df_alipay)} expense transactions")
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
            df_wechat = expense_only(df_wechat)
            print(f"  OK - Loaded {len(df_wechat)} expense transactions")
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
            df_extra = expense_only(parse_generic_bank_csv(
                str(full_path),
                source=label,
                column_map=entry.get('column_map'),
                encoding=entry.get('encoding'),
            ))
            print(f"  OK - Loaded {len(df_extra)} expense transactions")
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
