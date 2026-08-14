"""GET /dashboard/trends: split transactions (own category_id NULL, but
is_split=True) must still count as "labeled" in the bucket totals."""
USER_A = "user-a-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def test_split_transaction_counts_toward_trend_bucket_total(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [
        {"id": "cat-1", "user_id": USER_A, "name": "Groceries"},
        {"id": "cat-2", "user_id": USER_A, "name": "Household"},
    ])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_A, "category_id": "cat-1", "amount": 30.0, "timestamp": "2026-06-01T00:00:00", "is_split": False},
        {"id": "t2", "user_id": USER_A, "category_id": None, "amount": 100.0, "timestamp": "2026-06-01T00:00:00", "is_split": True},
    ])

    response = client.get("/dashboard/trends?granularity=day&days=365", headers=_headers(make_token))

    assert response.status_code == 200
    trends = response.json()["trends"]
    bucket = next(t for t in trends if t["date"] == "2026-06-01")
    assert bucket["total_spend"] == 130.0


def test_uncategorized_unsplit_transaction_excluded_from_trends(client, patch_jwks, make_token, fake_db):
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_A, "category_id": None, "amount": 50.0, "timestamp": "2026-06-01T00:00:00", "is_split": False},
    ])

    response = client.get("/dashboard/trends?granularity=day&days=365", headers=_headers(make_token))

    assert response.status_code == 200
    assert response.json()["trends"] == []
