"""Parser v2 (API v5 §1.1 / §3.9): kind + flow_subtype for every settled row.

All data is SYNTHETIC (tests/fixtures/statements/). Each expected-row table
below glosses the Chinese merchant/description in English.
"""
import csv
import math
from pathlib import Path

import pandas as pd
import pytest

import parse

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "statements"


def _rows(df: pd.DataFrame) -> list:
    """(merchant, amount, kind, flow_subtype) in file order."""
    return [
        (m, round(a, 2), k, s)
        for m, a, k, s in zip(df["merchant"], df["amount"], df["kind"], df["flow_subtype"])
    ]


# ---------------------------------------------------------------------------
# Alipay (Chinese export)
# ---------------------------------------------------------------------------

ALIPAY_CN_EXPECTED = [
    ("麦当劳", 38.0, "expense", None),               # McDonald's, Big Mac meal
    ("淘宝店铺A", 100.0, "expense", None),           # Taobao shop A, storage box (partly refunded below)
    ("淘宝店铺A", -30.0, "expense", "refund"),       # refund row 退款成功 "refund successful" for 30 of it
    ("优衣库", 129.0, "expense", None),              # Uniqlo shirt, 交易关闭 "closed" but paid (full refund row follows)
    ("优衣库", -129.0, "expense", "refund"),         # the full refund
    # 星巴克 (Starbucks) 交易关闭 "closed" with no payment -> ignored
    ("招商银行", 500.0, "transfer", "repayment"),    # China Merchants Bank, 信用卡还款 credit card repayment
    ("花呗", 300.0, "transfer", "repayment"),        # Huabei, 花呗主动还款 Huabei repayment
    ("余额宝", 1.23, "income", "interest"),          # Yu'e Bao 收益发放 earnings paid out
    ("余额宝", 1000.0, "transfer", "own_account"),   # Yu'e Bao 转入 transfer in (money leaves the wallet)
    ("余额宝", -200.0, "transfer", "own_account"),   # Yu'e Bao 转出到余额 transfer out to balance
    ("中国移动", 50.0, "expense", None),             # China Mobile 话费充值 phone credit top-up = spending
    ("支付宝", -500.0, "transfer", "top_up"),        # Alipay 余额充值 balance top-up from bank card
    ("支付宝", 200.0, "transfer", "withdrawal"),     # Alipay 余额提现 balance withdrawal to bank card
    ("张三", 88.0, "transfer", "p2p_transfer"),      # Zhang San, 转账 transfer sent
    ("李四", -66.0, "transfer", "p2p_transfer"),     # Li Si, 转账 transfer received
    ("王五", -20.0, "transfer", "red_packet"),       # Wang Wu, 红包 red packet received
    ("赵六", 10.0, "transfer", "red_packet"),        # Zhao Liu, 发红包 red packet sent
    ("示例科技有限公司", 15000.0, "income", "salary"),  # "Example Tech Co.", 9月工资 September wages
    ("闲鱼买家", 25.0, "income", "other"),            # Xianyu (second-hand) buyer, 二手书 used book
    # 滴滴出行 (DiDi) 等待付款 "awaiting payment" -> not settled, dropped
]


def test_alipay_cn_kinds_and_subtypes():
    df = parse.parse_alipay(str(FIXTURES / "alipay_cn.csv"))
    assert list(df.columns) == parse.OUTPUT_COLUMNS
    assert _rows(df) == ALIPAY_CN_EXPECTED
    assert df["source"].eq("alipay").all()


def test_alipay_cn_gbk_matches_utf8(tmp_path):
    gbk = tmp_path / "alipay_gbk.csv"
    gbk.write_bytes((FIXTURES / "alipay_cn.csv").read_text(encoding="utf-8").encode("gbk"))
    a = parse.parse_alipay(str(FIXTURES / "alipay_cn.csv"))
    b = parse.parse_alipay(str(gbk))
    pd.testing.assert_frame_equal(a, b)


ALIPAY_EN_EXPECTED = [
    ("McDonalds", 38.0, "expense", None),
    ("Shop A", 100.0, "expense", None),
    ("Shop A", -30.0, "expense", "refund"),
    ("Uniqlo", 129.0, "expense", None),           # closed but paid (full refund row follows)
    ("Uniqlo", -129.0, "expense", "refund"),
    # Starbucks closed, unpaid -> ignored
    ("CMB", 500.0, "transfer", "repayment"),
    ("Yu'e Bao", 1.23, "income", "interest"),
    ("Yu'e Bao", 1000.0, "transfer", "own_account"),
    ("Zhang San", 88.0, "transfer", "p2p_transfer"),
    ("Wang Wu", -20.0, "transfer", "red_packet"),
    ("Example Tech Ltd", 15000.0, "income", "salary"),
    # DiDi "Waiting for payment" -> dropped
]


def test_alipay_en_kinds_and_subtypes():
    df = parse.parse_alipay(str(FIXTURES / "alipay_en.csv"))
    assert _rows(df) == ALIPAY_EN_EXPECTED


# ---------------------------------------------------------------------------
# WeChat (CSV + XLSX)
# ---------------------------------------------------------------------------

WECHAT_EXPECTED = [
    ("美团", 45.0, "expense", None),                   # Meituan, 外卖订单 food delivery order
    ("便利店", 12.5, "expense", None),                 # convenience store, 扫二维码付款 QR-code payment
    ("京东", 70.0, "expense", None),                   # JD 耳机 headphones 100, status 已退款(￥30.00) "refunded (¥30)" -> 70
    ("拼多多", 60.0, "expense", None),                 # Pinduoduo T-shirt, 已全额退款 "fully refunded" (refund row follows)
    ("拼多多", -60.0, "expense", "refund"),            # 拼多多-退款 Pinduoduo refund row
    ("张三", 2000.0, "transfer", "p2p_transfer"),      # transfer to Zhang San (rent), 朋友已收钱 "friend has received the money"
    ("李四", -150.0, "transfer", "p2p_transfer"),      # transfer from Li Si, 已收钱 "received"
    ("王五", 8.88, "transfer", "red_packet"),          # 微信红包（单发） WeChat red packet (single) sent
    ("赵六", -6.66, "transfer", "red_packet"),         # 微信红包 red packet received, 已存入零钱 "deposited to wallet"
    ("钱七", -75.0, "transfer", "aa_collection"),      # 群收款 group collection, AA聚餐 split-bill dinner
    ("招商银行(0000)", 500.0, "transfer", "withdrawal"),  # 零钱提现 wallet withdrawal to CMB card
    ("招商银行(0000)", -300.0, "transfer", "top_up"),     # 零钱充值 wallet top-up from CMB card
    ("/", 1000.0, "transfer", "own_account"),           # 转入零钱通 into Lingqiantong (money-market)
    ("/", -200.0, "transfer", "own_account"),           # 零钱通转出 out of Lingqiantong
    ("招商银行", 800.0, "transfer", "repayment"),       # 信用卡还款 credit card repayment (W-13)
    # 星巴克 (Starbucks) 支付失败 "payment failed" -> dropped
    # 孙八 (Sun Ba) 对方已退还 "recipient returned it" -> dropped
    ("周九", 20.0, "income", "other"),                  # 二维码收款 QR-code collection from Zhou Jiu
]


def _wechat_xlsx_from_csv(csv_path: Path, xlsx_path: Path) -> Path:
    """Build a WeChat XLSX export from the CSV fixture (same metadata block,
    header on row 18, amounts as numbers like the real Excel export)."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    with open(csv_path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    header_idx = next(i for i, r in enumerate(rows) if r and r[0] == "交易时间")   # transaction time
    for i, row in enumerate(rows):
        cells = list(row)
        while cells and cells[-1] == "":
            cells.pop()
        if i > header_idx:
            cells[5] = float(cells[5])   # 金额(元) amount (CNY)
        ws.append(cells)
    wb.save(xlsx_path)
    return xlsx_path


def test_wechat_csv_kinds_and_subtypes():
    df = parse.parse_wechat_csv(str(FIXTURES / "wechat_cn.csv"))
    assert _rows(df) == WECHAT_EXPECTED
    assert df["source"].eq("wechat").all()


def test_wechat_xlsx_kinds_and_subtypes(tmp_path):
    xlsx = _wechat_xlsx_from_csv(FIXTURES / "wechat_cn.csv", tmp_path / "wechat.xlsx")
    df = parse.parse_wechat_excel(str(xlsx))
    assert _rows(df) == WECHAT_EXPECTED


def test_w13_wechat_csv_xlsx_parity(tmp_path):
    """W-13: the CSV path classifies exactly like the XLSX path (credit card
    repayment, withdrawals, top-ups ... all typed the same)."""
    xlsx = _wechat_xlsx_from_csv(FIXTURES / "wechat_cn.csv", tmp_path / "wechat.xlsx")
    a = parse.parse_wechat_csv(str(FIXTURES / "wechat_cn.csv"))
    b = parse.parse_wechat_excel(str(xlsx))
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))
    repay = a[a["merchant"] == "招商银行"]   # China Merchants Bank
    assert repay[["kind", "flow_subtype"]].values.tolist() == [["transfer", "repayment"]]


def test_wechat_csv_gbk_and_yuan_sign(tmp_path):
    """GBK-encoded CSV with full-width-yuan-prefixed amounts parses the same."""
    text = (FIXTURES / "wechat_cn.csv").read_text(encoding="utf-8")
    lines = text.splitlines()
    out = []
    header_seen = False
    for line in lines:
        if line.startswith("交易时间"):   # transaction time (header row)
            header_seen = True
            out.append(line)
            continue
        if header_seen:
            cells = next(csv.reader([line]))
            cells[5] = "￥" + cells[5]   # full-width yuan sign, as in GBK exports
            line = ",".join(cells)
        out.append(line)
    gbk = tmp_path / "wechat_gbk.csv"
    gbk.write_bytes(("\n".join(out) + "\n").encode("gbk"))
    assert _rows(parse.parse_wechat_csv(str(gbk))) == WECHAT_EXPECTED


def test_wechat_english_csv(tmp_path):
    path = tmp_path / "wechat_en.csv"
    path.write_text(
        "WeChat Pay bill details\n"
        "Export Type: [All]\n"
        "Transaction Time,Transaction Type,Counterparty,Product,Income/Expense,Amount (CNY),Payment Method,Current Status,Transaction ID,Merchant ID,Remark\n"
        "2025-09-01 08:00:00,Merchant Payment,KFC,Burger,Expense,¥30.00,Balance,Payment successful,T1,M1,/\n"
        "2025-09-02 08:00:00,Red Packet,Friend A,/,Income,¥8.00,/,Deposited to Balance,T2,/,/\n"
        "2025-09-03 08:00:00,Transfer,Friend B,/,Expense,¥50.00,Balance,Transferred,T3,/,/\n"
        "2025-09-04 08:00:00,Credit Card Repayment,CMB,/,Expense,¥200.00,Balance,Payment successful,T4,/,/\n"
        "2025-09-05 08:00:00,Group Collection,Friend C,Dinner,Income,¥40.00,/,Received,T5,/,/\n",
        encoding="utf-8",
    )
    assert _rows(parse.parse_wechat_csv(str(path))) == [
        ("KFC", 30.0, "expense", None),
        ("Friend A", -8.0, "transfer", "red_packet"),
        ("Friend B", 50.0, "transfer", "p2p_transfer"),
        ("CMB", 200.0, "transfer", "repayment"),
        ("Friend C", -40.0, "transfer", "aa_collection"),
    ]


# ---------------------------------------------------------------------------
# The three approved W-10 fixes, stated as the audit's acceptance tests
# ---------------------------------------------------------------------------

def _net(df, merchant):
    return round(df.loc[(df["merchant"] == merchant) & (df["kind"] == "expense"), "amount"].sum(), 2)


def test_fix_a_partial_refund_nets_70_without_refund_row():
    # WeChat: one row, ¥100 purchase with status 已退款(￥30.00) "refunded (¥30)".
    df = parse.parse_wechat_csv(str(FIXTURES / "wechat_cn.csv"))
    assert _net(df, "京东") == 70.0   # JD


def test_fix_a_partial_refund_nets_70_with_refund_row():
    # Alipay: ¥100 purchase (交易成功 success) + separate ¥30 退款成功 refund row.
    df = parse.parse_alipay(str(FIXTURES / "alipay_cn.csv"))
    assert _net(df, "淘宝店铺A") == 70.0   # Taobao shop A


def test_fix_a_partial_refund_with_matching_refund_row_is_not_double_counted(tmp_path):
    """WeChat status 已退款(￥30.00) AND a separate 30.00 refund row: the
    original stays at +100 and the refund row carries -30 (net 70, not 40)."""
    text = (FIXTURES / "wechat_cn.csv").read_text(encoding="utf-8").rstrip("\n")
    text += "\n2025-09-03 19:00:00,京东-退款,京东,退款,收入,30.00,招商银行(0000),已退款,W0099,MW0003,/\n"   # JD refund row, 已退款 "refunded"
    path = tmp_path / "wechat_pair.csv"
    path.write_text(text, encoding="utf-8")
    df = parse.parse_wechat_csv(str(path))
    jd = df[df["merchant"] == "京东"]
    assert jd["amount"].tolist() == [100.0, -30.0]
    assert _net(df, "京东") == 70.0


def test_fix_a_full_refund_without_refund_row_keeps_v1_behaviour(tmp_path):
    text = (FIXTURES / "wechat_cn.csv").read_text(encoding="utf-8").rstrip("\n")
    text += "\n2025-09-20 10:00:00,商户消费,饿了么,午餐,支出,25.00,零钱,已全额退款,W0100,MW0100,/\n"   # Ele.me lunch, 已全额退款 "fully refunded"
    path = tmp_path / "wechat_full.csv"
    path.write_text(text, encoding="utf-8")
    df = parse.parse_wechat_csv(str(path))
    row = df[df["merchant"] == "饿了么"]
    assert row[["amount", "kind", "flow_subtype"]].values.tolist() == [[-25.0, "expense", "refund"]]


def test_fix_b_friend_received_counts_as_outgoing_p2p():
    df = parse.parse_wechat_csv(str(FIXTURES / "wechat_cn.csv"))
    row = df[df["merchant"] == "张三"]   # Zhang San, status 朋友已收钱 "friend has received the money"
    assert row[["amount", "kind", "flow_subtype"]].values.tolist() == [[2000.0, "transfer", "p2p_transfer"]]


def test_fix_c_closed_order_counts_only_when_paid():
    df = parse.parse_alipay(str(FIXTURES / "alipay_cn.csv"))
    assert "星巴克" not in set(df["merchant"])     # Starbucks: closed, never paid -> ignored
    assert _net(df, "优衣库") == 0.0               # Uniqlo: closed after a full refund -> +129 / -129


# ---------------------------------------------------------------------------
# v1 key regression: expense/refund rows keep (timestamp, merchant, description)
# ---------------------------------------------------------------------------

def _v1_alipay_native_keys(path: Path) -> dict:
    """Re-implementation of the v1 parser's row filter (parse.py before v5):
    keep 支出 (expense) rows with status 交易成功/交易关闭 (success/closed) that
    are not 信用卡还款/花呗还款/还呗还款/提现 (repayments, withdrawal), plus every
    row whose status contains 退款 (refund), negated."""
    skip, enc, _ = parse._find_alipay_header(str(path))
    df = pd.read_csv(path, encoding=enc, skiprows=skip)
    status = df["交易状态"].astype(str)                                 # transaction status
    settled = status.str.contains("交易成功|交易关闭")                   # success | closed
    refund = status.str.contains("退款")                                 # refund
    transfer = df["交易分类"].astype(str).str.contains("信用卡还款|花呗还款|还呗还款|提现")
    expense = (df["收/支"] == "支出") & settled & ~transfer              # income/expense == expense
    keep = df[expense | refund]
    out = {}
    for _, r in keep.iterrows():
        amount = float(r["金额"]) * (-1 if "退款" in str(r["交易状态"]) else 1)   # amount
        key = (pd.Timestamp(r["交易时间"]), str(r["交易对方"]).strip(), str(r["商品说明"]).strip())
        out[key] = amount
    return out


def _v1_wechat_keys(path: Path) -> dict:
    """v1 WeChat XLSX filter: 支出 with status 支付成功/已转账 (paid/transferred),
    not a transfer keyword, plus any 退款 (refund) status row, negated."""
    rows = list(csv.reader(open(path, encoding="utf-8", newline="")))
    h = next(i for i, r in enumerate(rows) if r and r[0] == "交易时间")
    df = pd.DataFrame(rows[h + 1:], columns=rows[h])
    status = df["当前状态"]                                               # current status
    settled = status.isin(["支付成功", "已转账"])                          # paid, transferred
    refund = status.str.contains("退款")
    transfer = df["交易类型"].str.contains("信用卡还款|花呗还款|还呗还款|提现")
    expense = (df["收/支"] == "支出") & settled & ~transfer
    keep = df[expense | refund]
    out = {}
    for _, r in keep.iterrows():
        amount = float(r["金额(元)"]) * (-1 if "退款" in r["当前状态"] else 1)
        out[(pd.Timestamp(r["交易时间"]), r["交易对方"].strip(), r["商品"].strip())] = amount
    return out


def _v2_keys(df: pd.DataFrame) -> dict:
    return {
        (pd.Timestamp(t), m, d): (a, k)
        for t, m, d, a, k in zip(df["timestamp"], df["merchant"], df["description"], df["amount"], df["kind"])
    }


def test_v1_keys_preserved_alipay():
    v1 = _v1_alipay_native_keys(FIXTURES / "alipay_cn.csv")
    v2 = _v2_keys(parse.parse_alipay(str(FIXTURES / "alipay_cn.csv")))
    dropped = {k for k in v1 if k not in v2}
    # Only the closed, unpaid Starbucks order disappears (fix c).
    assert {k[1] for k in dropped} == {"星巴克"}
    for key, amount in v1.items():
        if key in v2:
            assert v2[key][1] in ("expense", "transfer")
            # Amounts identical for every Alipay row v1 kept.
            assert math.isclose(v2[key][0], amount)


def test_v1_keys_preserved_wechat():
    v1 = _v1_wechat_keys(FIXTURES / "wechat_cn.csv")
    v2 = _v2_keys(parse.parse_wechat_csv(str(FIXTURES / "wechat_cn.csv")))
    assert set(v1) <= set(v2)
    changed = {k[1]: (v1[k], v2[k][0]) for k in v1 if not math.isclose(v1[k], v2[k][0])}
    # Only refund-annotated originals change amount:
    assert changed == {
        "京东": (-100.0, 70.0),     # JD: partial refund now nets the unrefunded 70
        "拼多多": (-60.0, 60.0),    # Pinduoduo: original stays +60, its refund row is -60
    }


# ---------------------------------------------------------------------------
# Generic bank statements (W-08)
# ---------------------------------------------------------------------------

def test_bank_direction_column_and_wallet_counterparty():
    df = parse.parse_generic_bank_csv(str(FIXTURES / "bank_direction.csv"))
    assert _rows(df) == [
        ("美团", 25.0, "expense", None),                           # Meituan, 借 debit
        ("示例科技有限公司", 15000.0, "income", "salary"),          # "Example Tech Co.", 代发工资 payroll
        ("支付宝(中国)网络技术有限公司", 500.0, "transfer", "own_account"),  # Alipay (China) Network Technology
        ("财付通支付科技有限公司", -300.0, "transfer", "own_account"),     # Tenpay Payment Technology
        ("招商银行", 2.1, "income", "interest"),                    # CMB, 活期结息 current-account interest
        ("招商银行信用卡中心", 1200.0, "transfer", "repayment"),     # CMB credit card centre, 信用卡还款 repayment
    ]
    # 交易日期 (date) + 交易时间 (time) combined; 合计 (total) footer dropped.
    assert df["timestamp"].iloc[0] == pd.Timestamp("2025-09-01 08:30:00")
    assert df["source"].eq("bank").all()


def test_bank_debit_credit_columns():
    df = parse.parse_generic_bank_csv(str(FIXTURES / "bank_debit_credit.csv"))
    assert _rows(df) == [
        ("STARBUCKS SHANGHAI", 32.0, "expense", None),
        ("PAYROLL ACME LTD", 20000.0, "income", "salary"),
        ("ALIPAY TOPUP", 1000.0, "transfer", "own_account"),
        ("WECHAT PAY", 200.0, "transfer", "own_account"),
        ("INTEREST", 1.5, "income", "interest"),
    ]


def test_bank_signed_amounts():
    df = parse.parse_generic_bank_csv(str(FIXTURES / "bank_signed.csv"))
    assert _rows(df) == [
        ("Metro", 4.0, "expense", None),
        ("Employer Inc", 8000.0, "income", "salary"),
        ("Tenpay", 300.0, "transfer", "own_account"),
        ("Uniqlo", 129.0, "expense", None),
    ]


def test_bank_all_positive_amounts_are_expenses(tmp_path):
    path = tmp_path / "card.csv"
    path.write_text("Posting Date,Merchant,Amount\n2025-09-01,Cafe,18.00\n2025-09-02,Bookshop,45.50\n", encoding="utf-8")
    df = parse.parse_generic_bank_csv(str(path))
    assert _rows(df) == [("Cafe", 18.0, "expense", None), ("Bookshop", 45.5, "expense", None)]


def test_bank_xlsx_and_gbk(tmp_path):
    raw = pd.read_csv(FIXTURES / "bank_debit_credit.csv")
    xlsx = tmp_path / "bank.xlsx"
    raw.to_excel(xlsx, index=False)
    assert _rows(parse.parse_generic_bank_csv(str(xlsx))) == _rows(
        parse.parse_generic_bank_csv(str(FIXTURES / "bank_debit_credit.csv")))

    gbk = tmp_path / "bank_gbk.csv"
    gbk.write_bytes((FIXTURES / "bank_direction.csv").read_text(encoding="utf-8").encode("gbk"))
    assert _rows(parse.parse_generic_bank_csv(str(gbk))) == _rows(
        parse.parse_generic_bank_csv(str(FIXTURES / "bank_direction.csv")))


def test_bank_expense_rows():
    df = parse.parse_generic_bank_csv(str(FIXTURES / "bank_debit_credit.csv"), source="bank")
    assert df.loc[df["kind"] == "expense", "merchant"].tolist() == ["STARBUCKS SHANGHAI"]


# ---------------------------------------------------------------------------
# Detection order + filtered exports
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("wechat_cn.csv", "wechat"),          # has 交易时间 + 收/支 too, but WeChat markers win
    ("alipay_cn.csv", "alipay"),
    ("alipay_en.csv", "alipay"),
    ("bank_direction.csv", "bank"),       # has 交易类型 (transaction type) but no WeChat status column
    ("bank_debit_credit.csv", "bank"),
    ("bank_signed.csv", "bank"),
])
def test_detection_order(name, expected):
    assert parse.detect_statement_source(str(FIXTURES / name)) == expected


def test_detection_wechat_xlsx(tmp_path):
    xlsx = _wechat_xlsx_from_csv(FIXTURES / "wechat_cn.csv", tmp_path / "wechat.xlsx")
    assert parse.detect_statement_source(str(xlsx)) == "wechat"


def test_undetectable_file(tmp_path):
    path = tmp_path / "x.csv"
    path.write_text("not,a,real,statement\nfoo,bar,baz,qux\n", encoding="utf-8")
    assert parse.detect_statement_source(str(path)) is None


def test_filtered_export_detection(tmp_path):
    assert parse.detect_export_filter(str(FIXTURES / "alipay_cn.csv")) is None
    assert parse.detect_export_filter(str(FIXTURES / "wechat_cn.csv")) is None
    text = (FIXTURES / "alipay_cn.csv").read_text(encoding="utf-8")
    filtered = tmp_path / "alipay_filtered.csv"
    # 导出交易类型：[支出] = "export transaction type: [expense]"
    filtered.write_text(text.replace("导出交易类型：[全部]", "导出交易类型：[支出]"), encoding="utf-8")
    assert parse.detect_export_filter(str(filtered)) == "支出"


# --- Integration follow-ups (backend review, 2026-10-11) ---------------------

def test_aa_payment_out_is_spending_aa_collection_in_is_transfer():
    # 群收款 = group collection (AA split). Paying your share is real spending
    # (user decision); receiving shares back stays a transfer.
    assert parse.classify_wallet_flow("out", "群收款", "Friend", "Dinner AA") == ("expense", None, 1)
    assert parse.classify_wallet_flow("in", "群收款", "Friend", "Dinner AA") == ("transfer", "aa_collection", -1)


def test_money_market_withdrawal_is_own_account_not_withdrawal():
    # 余额宝 = Yu'e Bao money-market fund; 提现 = withdraw.
    kind, subtype, _ = parse.classify_wallet_flow("neutral", "余额宝-提现", "Yu'e Bao", "")
    assert (kind, subtype) == ("transfer", "own_account")
    # A plain wallet withdrawal to a bank card is still a withdrawal.
    assert parse.classify_wallet_flow("neutral", "零钱提现", "", "")[:2] == ("transfer", "withdrawal")


def test_bank_credit_card_style_signs_use_majority_as_spending(tmp_path):
    # Credit-card exports: charges positive, the monthly payment negative.
    path = tmp_path / "cc.csv"
    path.write_text(
        "Posting Date,Merchant,Amount\n"
        "2025-09-01,Cafe,18.00\n2025-09-02,Bookshop,45.50\n"
        "2025-09-03,Grocer,120.00\n2025-09-20,Payment Thank You,-183.50\n",
        encoding="utf-8")
    rows = _rows(parse.parse_generic_bank_csv(str(path)))
    assert [r[2] for r in rows[:3]] == ["expense", "expense", "expense"]
    assert rows[3][2] != "expense"   # the payment is money in for this statement


def test_bank_export_with_wechat_like_columns_is_not_wechat(tmp_path):
    # 交易时间 transaction time, 交易类型 transaction type, 金额(元) amount (CNY) —
    # without 当前状态 (current status) or 交易对方 (counterparty) this is a bank file.
    path = tmp_path / "bank_like.csv"
    path.write_text("交易时间,交易类型,金额(元),摘要\n2025-09-01 10:00:00,消费,18.00,Cafe\n", encoding="utf-8")
    assert parse.detect_statement_source(str(path)) != "wechat"


def test_bank_mostly_incoming_account_is_not_flipped(tmp_path):
    # More money in than out, debit convention (negative = out): the salary
    # anchor (positive) decides, so the majority rule doesn't flip the file.
    path = tmp_path / "savings.csv"
    path.write_text(
        "Date,Description,Amount\n"
        "2025-09-01,Salary September,8000.00\n2025-09-05,Refund Taobao,30.00\n"
        "2025-09-07,Refund Meituan,12.00\n2025-09-10,Cafe,-18.00\n",
        encoding="utf-8")
    rows = _rows(parse.parse_generic_bank_csv(str(path)))
    assert rows[0][2] == "income" and rows[3][2] == "expense"


def test_bank_sign_tie_uses_debit_convention(tmp_path):
    path = tmp_path / "tie.csv"
    path.write_text("Date,Description,Amount\n2025-09-01,Cafe,-18.00\n2025-09-02,Friend,50.00\n", encoding="utf-8")
    rows = _rows(parse.parse_generic_bank_csv(str(path)))
    assert rows[0][2] == "expense" and rows[1][2] != "expense"
