"""GET /dashboard/reports: search, date range, and amount range filters —
all additive to the existing pagination/uncategorized_only/category_id
behavior and independently combinable."""
USER_A = "user-a-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def _seed_txn(fake_db, txn_id, merchant, description, amount, timestamp, user_id=USER_A):
    fake_db.seed("transactions", [{
        "id": txn_id, "user_id": user_id, "merchant": merchant, "description": description,
        "amount": amount, "timestamp": timestamp, "category_id": None, "categories": None,
        "label_source": "none",
    }])


def test_search_matches_merchant_case_insensitively(client, patch_jwks, make_token, fake_db):
    _seed_txn(fake_db, "t1", "Starbucks Coffee", "latte", 30, "2026-06-01T00:00:00")
    _seed_txn(fake_db, "t2", "Local Grocer", "veggies", 50, "2026-06-01T00:00:00")

    response = client.get("/dashboard/reports?search=starbucks", headers=_headers(make_token))

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 1
    assert body["transactions"][0]["merchant"] == "Starbucks Coffee"


def test_search_also_matches_description(client, patch_jwks, make_token, fake_db):
    _seed_txn(fake_db, "t1", "Some Cafe", "birthday latte", 30, "2026-06-01T00:00:00")
    _seed_txn(fake_db, "t2", "Other Shop", "groceries", 50, "2026-06-01T00:00:00")

    response = client.get("/dashboard/reports?search=birthday", headers=_headers(make_token))

    assert response.status_code == 200
    assert response.json()["total_count"] == 1


def test_date_range_filters_transactions(client, patch_jwks, make_token, fake_db):
    _seed_txn(fake_db, "t1", "Old Shop", "x", 10, "2026-01-01T00:00:00")
    _seed_txn(fake_db, "t2", "New Shop", "y", 20, "2026-06-15T00:00:00")

    response = client.get(
        "/dashboard/reports?date_from=2026-06-01&date_to=2026-07-01", headers=_headers(make_token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 1
    assert body["transactions"][0]["merchant"] == "New Shop"


def test_amount_range_filters_transactions(client, patch_jwks, make_token, fake_db):
    _seed_txn(fake_db, "t1", "Cheap Shop", "x", 5, "2026-06-01T00:00:00")
    _seed_txn(fake_db, "t2", "Mid Shop", "y", 50, "2026-06-01T00:00:00")
    _seed_txn(fake_db, "t3", "Pricey Shop", "z", 500, "2026-06-01T00:00:00")

    response = client.get(
        "/dashboard/reports?min_amount=10&max_amount=100", headers=_headers(make_token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 1
    assert body["transactions"][0]["merchant"] == "Mid Shop"


def test_filters_only_apply_to_the_authenticated_user(client, patch_jwks, make_token, fake_db):
    _seed_txn(fake_db, "t1", "Starbucks Coffee", "x", 30, "2026-06-01T00:00:00", user_id="user-b-id")

    response = client.get("/dashboard/reports?search=starbucks", headers=_headers(make_token, sub=USER_A))

    assert response.status_code == 200
    assert response.json()["total_count"] == 0


def test_filters_combine(client, patch_jwks, make_token, fake_db):
    _seed_txn(fake_db, "t1", "Starbucks Coffee", "x", 30, "2026-06-01T00:00:00")
    _seed_txn(fake_db, "t2", "Starbucks Coffee", "x", 3000, "2026-06-01T00:00:00")  # matches search, not amount
    _seed_txn(fake_db, "t3", "Other Shop", "x", 30, "2026-06-01T00:00:00")  # matches amount, not search

    response = client.get(
        "/dashboard/reports?search=starbucks&max_amount=100", headers=_headers(make_token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 1
    assert body["transactions"][0]["id"] == "t1"


def test_split_transaction_shows_split_badge_and_breakdown(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [
        {"id": "cat-1", "user_id": USER_A, "name": "Groceries"},
        {"id": "cat-2", "user_id": USER_A, "name": "Household"},
    ])
    fake_db.seed("transactions", [{
        "id": "t1", "user_id": USER_A, "merchant": "Costco", "description": "",
        "amount": 120.0, "timestamp": "2026-06-01T00:00:00", "category_id": None,
        "categories": None, "is_split": True, "label_source": "override",
    }])
    fake_db.seed("transaction_splits", [
        {"id": "s1", "user_id": USER_A, "transaction_id": "t1", "category_id": "cat-1",
         "categories": {"name": "Groceries"}, "amount": 80.0},
        {"id": "s2", "user_id": USER_A, "transaction_id": "t1", "category_id": "cat-2",
         "categories": {"name": "Household"}, "amount": 40.0},
    ])

    response = client.get("/dashboard/reports", headers=_headers(make_token))

    assert response.status_code == 200
    txn = response.json()["transactions"][0]
    assert txn["category"] == "Split (2)"
    assert txn["is_split"] is True
    assert txn["amount"] == 120.0
    assert {s["category_name"] for s in txn["splits"]} == {"Groceries", "Household"}


def test_non_split_transaction_has_null_splits_field(client, patch_jwks, make_token, fake_db):
    _seed_txn(fake_db, "t1", "Shop", "x", 30, "2026-06-01T00:00:00")

    response = client.get("/dashboard/reports", headers=_headers(make_token))

    assert response.status_code == 200
    txn = response.json()["transactions"][0]
    assert txn["is_split"] is False
    assert txn["splits"] is None
