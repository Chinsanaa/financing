"""GET /dashboard/insights: per-category trend vs 3-month average, and
per-transaction amount anomalies. Dates are computed relative to the real
`_now_cn()` clock (not hardcoded) so the tests aren't month-boundary-fragile.
"""
from routes.dashboard import _now_cn, _month_start

USER_A = "user-a-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def _month_offset_date(months_back: int, day: int = 15):
    now = _now_cn()
    month_start = _month_start(now)
    total = month_start.year * 12 + (month_start.month - 1) - months_back
    year, month = total // 12, total % 12 + 1
    return f"{year:04d}-{month:02d}-{day:02d}T00:00:00"


def _seed_category(fake_db, name="Eating Out"):
    cat_id = f"cat-{name}"
    fake_db.seed("categories", [{"id": cat_id, "user_id": USER_A, "name": name}])
    return cat_id


def _seed_txn(fake_db, cat_id, cat_name, amount, months_back, txn_id):
    fake_db.seed("transactions", [{
        "id": txn_id, "user_id": USER_A, "category_id": cat_id,
        "categories": {"name": cat_name}, "merchant": "Some Merchant",
        "amount": amount, "timestamp": _month_offset_date(months_back),
    }])


def test_category_trend_flags_a_spending_increase(client, patch_jwks, make_token, fake_db):
    cat_id = _seed_category(fake_db, "Eating Out")
    # Prior 3 months: steady ~100/month. Current month: 300 (3x).
    for i, months_back in enumerate([1, 2, 3]):
        _seed_txn(fake_db, cat_id, "Eating Out", 100, months_back, f"prior-{i}")
    _seed_txn(fake_db, cat_id, "Eating Out", 300, 0, "current-1")

    response = client.get("/dashboard/insights", headers=_headers(make_token))

    assert response.status_code == 200
    trends = response.json()["category_trends"]
    assert len(trends) == 1
    assert trends[0]["category"] == "Eating Out"
    assert trends[0]["current"] == 300
    assert trends[0]["avg_3mo"] == 100
    assert trends[0]["pct_change"] == 200.0


def test_category_with_no_prior_months_is_not_flagged(client, patch_jwks, make_token, fake_db):
    cat_id = _seed_category(fake_db, "Shopping")
    _seed_txn(fake_db, cat_id, "Shopping", 500, 0, "current-only")

    response = client.get("/dashboard/insights", headers=_headers(make_token))

    assert response.status_code == 200
    assert response.json()["category_trends"] == []


def test_flags_a_single_large_transaction_as_anomalous(client, patch_jwks, make_token, fake_db):
    cat_id = _seed_category(fake_db, "Groceries")
    for i in range(6):
        _seed_txn(fake_db, cat_id, "Groceries", 20 + i, 1, f"normal-{i}")
    _seed_txn(fake_db, cat_id, "Groceries", 5000, 1, "outlier-1")

    response = client.get("/dashboard/insights", headers=_headers(make_token))

    assert response.status_code == 200
    flagged = response.json()["flagged_transactions"]
    assert len(flagged) == 1
    assert flagged[0]["id"] == "outlier-1"
    assert flagged[0]["category"] == "Groceries"


def test_category_with_too_few_transactions_is_never_flagged(client, patch_jwks, make_token, fake_db):
    cat_id = _seed_category(fake_db, "Transportation")
    _seed_txn(fake_db, cat_id, "Transportation", 10, 1, "t1")
    _seed_txn(fake_db, cat_id, "Transportation", 9999, 1, "t2")  # would be an outlier with more history

    response = client.get("/dashboard/insights", headers=_headers(make_token))

    assert response.status_code == 200
    assert response.json()["flagged_transactions"] == []


def test_empty_when_no_transactions(client, patch_jwks, make_token, fake_db):
    response = client.get("/dashboard/insights", headers=_headers(make_token))

    assert response.status_code == 200
    assert response.json() == {"category_trends": [], "flagged_transactions": []}


def test_split_transaction_contributes_to_category_trends_per_line_item(client, patch_jwks, make_token, fake_db):
    groceries_id = _seed_category(fake_db, "Groceries")
    household_id = _seed_category(fake_db, "Household")
    # Prior 3 months: steady 100/month in Groceries via plain transactions.
    for i, months_back in enumerate([1, 2, 3]):
        _seed_txn(fake_db, groceries_id, "Groceries", 100, months_back, f"prior-{i}")

    # Current month: a split transaction contributing 250 to Groceries and
    # 50 to Household — should count toward both categories' current totals.
    fake_db.seed("transactions", [{
        "id": "split-txn", "user_id": USER_A, "category_id": None, "is_split": True,
        "merchant": "Costco", "amount": 300, "timestamp": _month_offset_date(0),
    }])
    split_timestamp = _month_offset_date(0)
    fake_db.seed("transaction_splits", [
        {"id": "s1", "user_id": USER_A, "transaction_id": "split-txn", "category_id": groceries_id,
         "categories": {"name": "Groceries"}, "transactions": {"timestamp": split_timestamp}, "amount": 250},
        {"id": "s2", "user_id": USER_A, "transaction_id": "split-txn", "category_id": household_id,
         "categories": {"name": "Household"}, "transactions": {"timestamp": split_timestamp}, "amount": 50},
    ])

    response = client.get("/dashboard/insights", headers=_headers(make_token))

    assert response.status_code == 200
    trends = {t["category"]: t for t in response.json()["category_trends"]}
    assert trends["Groceries"]["current"] == 250


def test_split_transaction_never_appears_in_flagged_transactions(client, patch_jwks, make_token, fake_db):
    cat_id = _seed_category(fake_db, "Groceries")
    for i in range(6):
        _seed_txn(fake_db, cat_id, "Groceries", 20 + i, 1, f"normal-{i}")

    # A split transaction whose own amount would clear the anomaly threshold
    # by a wide margin — must never be flagged (is_split=True is excluded).
    fake_db.seed("transactions", [{
        "id": "split-outlier", "user_id": USER_A, "category_id": None, "is_split": True,
        "merchant": "Costco", "amount": 5000, "timestamp": _month_offset_date(1),
    }])
    fake_db.seed("transaction_splits", [
        {"id": "s1", "user_id": USER_A, "transaction_id": "split-outlier", "category_id": cat_id,
         "categories": {"name": "Groceries"}, "transactions": {"timestamp": _month_offset_date(1)}, "amount": 5000},
    ])

    response = client.get("/dashboard/insights", headers=_headers(make_token))

    assert response.status_code == 200
    flagged_ids = {t["id"] for t in response.json()["flagged_transactions"]}
    assert "split-outlier" not in flagged_ids
