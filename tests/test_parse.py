"""Parser tests: encoding, refund netting, transfer typing, schema, duplicates.

Parser v2 keeps every settled row with a `kind`; see tests/test_parse_v2.py
for the full kind/subtype mapping tables."""
import pandas as pd
import parse


def test_schema_normalization_columns(alipay_native_utf8):
    df = parse.parse_alipay(str(alipay_native_utf8))
    assert list(df.columns) == parse.OUTPUT_COLUMNS
    assert df["source"].eq("alipay").all()
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])


def test_encoding_utf8_and_gbk_agree(alipay_native_utf8, alipay_native_gbk):
    a = parse.parse_alipay(str(alipay_native_utf8)).reset_index(drop=True)
    b = parse.parse_alipay(str(alipay_native_gbk)).reset_index(drop=True)
    # Same logical data, different on-disk encodings → identical parsed output.
    pd.testing.assert_frame_equal(a, b)


def test_refund_netted_as_negative(alipay_native_utf8):
    df = parse.parse_alipay(str(alipay_native_utf8))
    refund = df[df["merchant"] == "淘宝店铺"]   # "Taobao shop"
    assert len(refund) == 1
    assert refund["amount"].iloc[0] == -20.0  # 退款 (refund) kept but negated
    assert refund["kind"].iloc[0] == "expense"
    assert refund["flow_subtype"].iloc[0] == "refund"


def test_internal_transfer_typed_not_spend(alipay_native_utf8):
    df = parse.parse_alipay(str(alipay_native_utf8))
    # 信用卡还款 (credit-card repayment) is kept but typed as an own-account
    # transfer, so it never counts as spend.
    row = df[df["merchant"] == "招商银行"]   # "China Merchants Bank"
    assert row[["kind", "flow_subtype"]].values.tolist() == [["transfer", "repayment"]]
    assert row["amount"].iloc[0] == 500.0


def test_income_row_kept_as_transfer_in(alipay_native_utf8):
    df = parse.parse_alipay(str(alipay_native_utf8))
    # 张三 ("Zhang San") sent a 转账 (transfer): money in from a person.
    row = df[df["merchant"] == "张三"]
    assert row[["kind", "flow_subtype"]].values.tolist() == [["transfer", "p2p_transfer"]]
    assert row["amount"].iloc[0] == -100.0
    # Only the McDonald's expense + the refund are expense rows.
    assert (df["kind"] == "expense").sum() == 2


def test_expense_rows_only_for_ml(alipay_native_utf8):
    df = parse.parse_alipay(str(alipay_native_utf8))
    assert set(df.loc[df["kind"] == "expense", "merchant"]) == {"麦当劳", "淘宝店铺"}   # McDonald's, Taobao shop


def test_generic_bank_direction_and_amount_filter(generic_bank_csv):
    df = parse.parse_generic_bank_csv(str(generic_bank_csv), source="bank")
    expense = df[df["kind"] == "expense"]
    assert set(expense["merchant"]) == {"Starbucks", "Metro"}
    assert (expense["amount"] > 0).all()
    salary = df[df["merchant"] == "Salary Corp"]
    assert salary[["kind", "flow_subtype"]].values.tolist() == [["income", "salary"]]
