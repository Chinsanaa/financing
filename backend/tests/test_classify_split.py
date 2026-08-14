"""POST/DELETE /classify/{id}/split: split a transaction across multiple categories."""
USER_A = "user-a-id"
USER_B = "user-b-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def test_split_transaction_success(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [
        {"id": "cat-1", "user_id": USER_A, "name": "Groceries"},
        {"id": "cat-2", "user_id": USER_A, "name": "Household"},
    ])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_A, "merchant": "Costco", "amount": 120.0, "category_id": None, "is_split": False, "needs_review": True},
    ])

    response = client.post(
        "/classify/t1/split",
        json={"splits": [{"category_id": "cat-1", "amount": 80.0}, {"category_id": "cat-2", "amount": 40.0}]},
        headers=_headers(make_token),
    )

    assert response.status_code == 200
    txn = response.json()["transaction"]
    assert txn["category_id"] is None
    assert txn["is_split"] is True
    assert txn["needs_review"] is False

    splits = fake_db._tables["transaction_splits"].rows
    assert len(splits) == 2
    assert {s["category_id"] for s in splits} == {"cat-1", "cat-2"}
    assert sum(s["amount"] for s in splits) == 120.0


def test_split_rejects_fewer_than_two_entries(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Groceries"}])
    fake_db.seed("transactions", [{"id": "t1", "user_id": USER_A, "amount": 100.0, "category_id": None}])

    response = client.post(
        "/classify/t1/split",
        json={"splits": [{"category_id": "cat-1", "amount": 100.0}]},
        headers=_headers(make_token),
    )

    assert response.status_code == 400


def test_split_rejects_amount_sum_mismatch(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [
        {"id": "cat-1", "user_id": USER_A, "name": "Groceries"},
        {"id": "cat-2", "user_id": USER_A, "name": "Household"},
    ])
    fake_db.seed("transactions", [{"id": "t1", "user_id": USER_A, "amount": 100.0, "category_id": None}])

    response = client.post(
        "/classify/t1/split",
        json={"splits": [{"category_id": "cat-1", "amount": 80.0}, {"category_id": "cat-2", "amount": 40.0}]},
        headers=_headers(make_token),
    )

    assert response.status_code == 400
    assert fake_db._tables.get("transaction_splits", None) is None or fake_db._tables["transaction_splits"].rows == []


def test_split_rejects_unowned_category(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [
        {"id": "cat-1", "user_id": USER_A, "name": "Groceries"},
        {"id": "cat-2", "user_id": USER_B, "name": "Household"},
    ])
    fake_db.seed("transactions", [{"id": "t1", "user_id": USER_A, "amount": 100.0, "category_id": None}])

    response = client.post(
        "/classify/t1/split",
        json={"splits": [{"category_id": "cat-1", "amount": 60.0}, {"category_id": "cat-2", "amount": 40.0}]},
        headers=_headers(make_token),
    )

    assert response.status_code == 404


def test_split_rejects_duplicate_category(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Groceries"}])
    fake_db.seed("transactions", [{"id": "t1", "user_id": USER_A, "amount": 100.0, "category_id": None}])

    response = client.post(
        "/classify/t1/split",
        json={"splits": [{"category_id": "cat-1", "amount": 60.0}, {"category_id": "cat-1", "amount": 40.0}]},
        headers=_headers(make_token),
    )

    assert response.status_code == 400


def test_split_rejects_another_users_transaction(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [
        {"id": "cat-1", "user_id": USER_A, "name": "Groceries"},
        {"id": "cat-2", "user_id": USER_A, "name": "Household"},
    ])
    fake_db.seed("transactions", [{"id": "t1", "user_id": USER_B, "amount": 100.0, "category_id": None}])

    response = client.post(
        "/classify/t1/split",
        json={"splits": [{"category_id": "cat-1", "amount": 60.0}, {"category_id": "cat-2", "amount": 40.0}]},
        headers=_headers(make_token, sub=USER_A),
    )

    assert response.status_code == 404


def test_unsplit_clears_splits_and_resets_flags(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [
        {"id": "cat-1", "user_id": USER_A, "name": "Groceries"},
        {"id": "cat-2", "user_id": USER_A, "name": "Household"},
    ])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_A, "amount": 100.0, "category_id": None, "is_split": True, "needs_review": False},
    ])
    fake_db.seed("transaction_splits", [
        {"id": "s1", "user_id": USER_A, "transaction_id": "t1", "category_id": "cat-1", "amount": 60.0},
        {"id": "s2", "user_id": USER_A, "transaction_id": "t1", "category_id": "cat-2", "amount": 40.0},
    ])

    response = client.delete("/classify/t1/split", headers=_headers(make_token))

    assert response.status_code == 200
    txn = response.json()["transaction"]
    assert txn["category_id"] is None
    assert txn["is_split"] is False
    assert txn["needs_review"] is True
    assert fake_db._tables["transaction_splits"].rows == []


def test_unsplit_nonexistent_transaction_returns_404(client, patch_jwks, make_token, fake_db):
    response = client.delete("/classify/does-not-exist/split", headers=_headers(make_token))
    assert response.status_code == 404


def test_label_transaction_collapses_prior_split(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [
        {"id": "cat-1", "user_id": USER_A, "name": "Groceries"},
        {"id": "cat-2", "user_id": USER_A, "name": "Household"},
        {"id": "cat-3", "user_id": USER_A, "name": "Dining"},
    ])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_A, "merchant": "Costco", "amount": 100.0, "category_id": None, "is_split": True, "label_source": "override"},
    ])
    fake_db.seed("transaction_splits", [
        {"id": "s1", "user_id": USER_A, "transaction_id": "t1", "category_id": "cat-1", "amount": 60.0},
        {"id": "s2", "user_id": USER_A, "transaction_id": "t1", "category_id": "cat-2", "amount": 40.0},
    ])

    response = client.post(
        "/classify/t1/label",
        json={"category_id": "cat-3"},
        headers=_headers(make_token),
    )

    assert response.status_code == 200
    txn = response.json()["transaction"]
    assert txn["category_id"] == "cat-3"
    assert txn["is_split"] is False
    assert fake_db._tables["transaction_splits"].rows == []


def test_bulk_label_collapses_prior_split_per_row(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [
        {"id": "cat-1", "user_id": USER_A, "name": "Groceries"},
        {"id": "cat-2", "user_id": USER_A, "name": "Household"},
        {"id": "cat-3", "user_id": USER_A, "name": "Dining"},
    ])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_A, "merchant": "Costco", "amount": 100.0, "category_id": None, "is_split": True, "label_source": "override"},
        {"id": "t2", "user_id": USER_A, "merchant": "Shop B", "amount": 20.0, "category_id": None, "is_split": False, "label_source": "none"},
    ])
    fake_db.seed("transaction_splits", [
        {"id": "s1", "user_id": USER_A, "transaction_id": "t1", "category_id": "cat-1", "amount": 60.0},
        {"id": "s2", "user_id": USER_A, "transaction_id": "t1", "category_id": "cat-2", "amount": 40.0},
    ])

    response = client.post(
        "/classify/bulk-label",
        json={"transaction_ids": ["t1", "t2"], "category_id": "cat-3"},
        headers=_headers(make_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["updated"]) == 2
    for t in fake_db._tables["transactions"].rows:
        assert t["category_id"] == "cat-3"
        assert t["is_split"] is False
    assert fake_db._tables["transaction_splits"].rows == []
