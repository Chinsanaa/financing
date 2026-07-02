"""Parser tests: encoding, refund netting, transfer filtering, schema, duplicates."""
import pandas as pd
import parse
import validate


def test_schema_normalization_columns(alipay_native_utf8):
    df = parse.parse_alipay(str(alipay_native_utf8))
    assert list(df.columns) == ["timestamp", "merchant", "description", "amount", "source"]
    assert df["source"].eq("alipay").all()
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])


def test_encoding_utf8_and_gbk_agree(alipay_native_utf8, alipay_native_gbk):
    a = parse.parse_alipay(str(alipay_native_utf8)).reset_index(drop=True)
    b = parse.parse_alipay(str(alipay_native_gbk)).reset_index(drop=True)
    # Same logical data, different on-disk encodings → identical parsed output.
    pd.testing.assert_frame_equal(a, b)


def test_refund_netted_as_negative(alipay_native_utf8):
    df = parse.parse_alipay(str(alipay_native_utf8))
    refund = df[df["merchant"] == "淘宝店铺"]
    assert len(refund) == 1
    assert refund["amount"].iloc[0] == -20.0  # 退款 kept but negated


def test_internal_transfer_excluded(alipay_native_utf8):
    df = parse.parse_alipay(str(alipay_native_utf8))
    # 信用卡还款 (credit-card repayment) must not appear as spend.
    assert (df["merchant"] == "招商银行").sum() == 0


def test_income_row_excluded(alipay_native_utf8):
    df = parse.parse_alipay(str(alipay_native_utf8))
    assert (df["merchant"] == "张三").sum() == 0
    # Only the McDonald's expense + the refund survive.
    assert len(df) == 2


def test_generic_bank_direction_and_amount_filter(generic_bank_csv):
    df = parse.parse_generic_bank_csv(str(generic_bank_csv), source="bank")
    # Income row filtered by Type; only the two Expense rows remain.
    assert set(df["merchant"]) == {"Starbucks", "Metro"}
    assert (df["amount"] > 0).all()


def test_duplicate_handling_reported_not_crashed(generic_bank_csv):
    df = parse.parse_generic_bank_csv(str(generic_bank_csv), source="bank")
    dup = pd.concat([df, df.iloc[[0]]], ignore_index=True)  # inject a duplicate
    violations = validate.validate_transactions(dup)
    dup_v = [v for v in violations if v.check == "duplicate_rows"]
    assert dup_v and dup_v[0].count == 1
