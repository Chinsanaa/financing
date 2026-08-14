"""Recurring/subscription detection: cadence classification and amount stability."""
import random

import pandas as pd

from recurring import detect_recurring_merchants


def test_monthly_subscription_detected():
    rows = [
        {"merchant": "Netflix", "amount": 39.9, "timestamp": pd.Timestamp("2026-02-15") + pd.Timedelta(days=30 * i), "category_id": "cat-shopping"}
        for i in range(6)
    ]
    df = pd.DataFrame(rows)
    out = detect_recurring_merchants(df, now=pd.Timestamp("2026-08-01"))

    assert list(out["merchant"]) == ["Netflix"]
    assert out.iloc[0]["cadence"] == "monthly"
    assert out.iloc[0]["typical_amount"] == 39.9
    assert out.iloc[0]["category_id"] == "cat-shopping"


def test_weekly_recurring_detected():
    rows = [
        {"merchant": "City Gym", "amount": 25.0, "timestamp": pd.Timestamp("2026-02-01") + pd.Timedelta(days=7 * i), "category_id": "cat-other"}
        for i in range(20)
    ]
    df = pd.DataFrame(rows)
    out = detect_recurring_merchants(df, now=pd.Timestamp("2026-08-01"))

    assert list(out["merchant"]) == ["City Gym"]
    assert out.iloc[0]["cadence"] == "weekly"


def test_irregular_merchant_not_flagged():
    random.seed(0)
    rows = []
    d = pd.Timestamp("2026-01-01")
    for _ in range(15):
        d += pd.Timedelta(days=random.randint(1, 10))
        rows.append({"merchant": "Local Market", "amount": random.uniform(10, 120), "timestamp": d, "category_id": "cat-groceries"})
    df = pd.DataFrame(rows)
    out = detect_recurring_merchants(df, now=pd.Timestamp("2026-08-01"))

    assert out.empty


def test_too_few_occurrences_not_flagged():
    df = pd.DataFrame(
        [
            {"merchant": "One-off Store", "amount": 50, "timestamp": pd.Timestamp("2026-03-01"), "category_id": None},
            {"merchant": "One-off Store", "amount": 55, "timestamp": pd.Timestamp("2026-04-01"), "category_id": None},
        ]
    )
    out = detect_recurring_merchants(df, now=pd.Timestamp("2026-08-01"))

    assert out.empty


def test_unstable_amount_not_flagged():
    """Monthly cadence but amount varies wildly -> not a subscription (e.g. groceries)."""
    rows = [
        {"merchant": "Variable Shop", "amount": amt, "timestamp": pd.Timestamp("2026-02-15") + pd.Timedelta(days=30 * i), "category_id": None}
        for i, amt in enumerate([20, 200, 15, 300, 10, 250])
    ]
    df = pd.DataFrame(rows)
    out = detect_recurring_merchants(df, now=pd.Timestamp("2026-08-01"))

    assert out.empty


def test_transactions_outside_lookback_window_ignored():
    """Old recurring merchant that stopped >6 months ago should not still show up."""
    rows = [
        {"merchant": "Cancelled Sub", "amount": 9.99, "timestamp": pd.Timestamp("2024-01-15") + pd.Timedelta(days=30 * i), "category_id": None}
        for i in range(6)
    ]
    df = pd.DataFrame(rows)
    out = detect_recurring_merchants(df, now=pd.Timestamp("2026-08-01"))

    assert out.empty


def test_empty_input_returns_empty_dataframe_with_expected_columns():
    out = detect_recurring_merchants(pd.DataFrame(columns=["merchant", "amount", "timestamp", "category_id"]))
    assert out.empty
    assert list(out.columns) == ["merchant", "category_id", "cadence", "typical_amount", "last_seen", "occurrences"]
