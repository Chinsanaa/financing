"""GET /dashboard/review-queue: split transactions render "Split" for
category/suggested_category in the show_labeled=True (manually labeled) view."""
USER_A = "user-a-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def test_split_transaction_shows_as_split_in_labeled_review(client, patch_jwks, make_token, fake_db):
    fake_db.seed("transactions", [{
        "id": "t1", "user_id": USER_A, "merchant": "Costco", "description": "",
        "amount": 120.0, "timestamp": "2026-06-01T00:00:00", "confidence": None,
        "category_id": None, "categories": None, "is_split": True,
        "is_manually_labeled": True,
    }])

    response = client.get("/dashboard/review-queue?show_labeled=true", headers=_headers(make_token))

    assert response.status_code == 200
    txn = response.json()["transactions"][0]
    assert txn["category"] == "Split"
    assert txn["suggested_category"] == "Split"
