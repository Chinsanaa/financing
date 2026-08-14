"""GET /dashboard/by-category: correctness with a mix of split and
non-split transactions, via the spend_by_category_for_user RPC."""
USER_A = "user-a-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def test_by_category_mixes_split_and_non_split_contributions(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [
        {"id": "cat-groceries", "user_id": USER_A, "name": "Groceries"},
        {"id": "cat-household", "user_id": USER_A, "name": "Household"},
        {"id": "cat-dining", "user_id": USER_A, "name": "Dining"},
    ])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_A, "category_id": "cat-dining", "amount": 25.0, "timestamp": "2026-06-01T00:00:00", "is_split": False},
        {"id": "t2", "user_id": USER_A, "category_id": None, "amount": 120.0, "timestamp": "2026-06-02T00:00:00", "is_split": True},
    ])
    fake_db.seed("transaction_splits", [
        {"id": "s1", "user_id": USER_A, "transaction_id": "t2", "category_id": "cat-groceries", "amount": 80.0},
        {"id": "s2", "user_id": USER_A, "transaction_id": "t2", "category_id": "cat-household", "amount": 40.0},
    ])

    response = client.get("/dashboard/by-category", headers=_headers(make_token))

    assert response.status_code == 200
    by_cat = {c["category"]: c for c in response.json()["categories"]}
    assert by_cat["Dining"]["total_amount"] == 25.0
    assert by_cat["Dining"]["transaction_count"] == 1
    assert by_cat["Groceries"]["total_amount"] == 80.0
    assert by_cat["Household"]["total_amount"] == 40.0


def test_by_category_excludes_other_users_splits(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Groceries"}])
    fake_db.seed("categories", [{"id": "cat-2", "user_id": "user-b-id", "name": "Groceries"}])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": "user-b-id", "category_id": None, "amount": 999.0, "timestamp": "2026-06-01T00:00:00", "is_split": True},
    ])
    fake_db.seed("transaction_splits", [
        {"id": "s1", "user_id": "user-b-id", "transaction_id": "t1", "category_id": "cat-2", "amount": 999.0},
    ])

    response = client.get("/dashboard/by-category", headers=_headers(make_token))

    assert response.status_code == 200
    assert response.json()["categories"] == []
