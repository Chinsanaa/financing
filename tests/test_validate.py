"""Data-validation checks: schema, amounts, dates, duplicates."""
import pandas as pd
import validate


def _base():
    return pd.DataFrame({
        "timestamp": ["2025-09-01 08:00:00", "2025-09-02 09:00:00"],
        "merchant": ["A", "B"],
        "description": ["x", "y"],
        "amount": [10.0, 20.0],
        "source": ["alipay", "wechat"],
    })


def test_clean_frame_has_no_violations():
    assert validate.validate_transactions(_base()) == []


def test_missing_column_is_error():
    df = _base().drop(columns=["amount"])
    vs = validate.validate_transactions(df)
    assert validate.has_errors(vs)
    assert vs[0].check == "schema"


def test_zero_amount_flagged():
    df = _base(); df.loc[0, "amount"] = 0
    vs = validate.validate_transactions(df)
    assert any(v.check == "amount_zero" and v.severity == "error" for v in vs)


def test_negative_amount_is_warning_not_error():
    df = _base(); df.loc[0, "amount"] = -5.0  # refund
    vs = validate.validate_transactions(df)
    assert any(v.check == "amount_negative" and v.severity == "warning" for v in vs)
    assert not validate.has_errors(vs)


def test_future_and_ancient_dates_flagged():
    df = _base()
    df.loc[0, "timestamp"] = "1970-01-01 00:00:00"
    df.loc[1, "timestamp"] = "2999-01-01 00:00:00"
    vs = validate.validate_transactions(df)
    checks = {v.check for v in vs}
    assert "date_too_old" in checks and "date_future" in checks
