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
