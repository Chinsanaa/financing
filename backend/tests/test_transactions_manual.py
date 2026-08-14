"""POST /transactions/: manual expense entry from the Upload tab."""
USER_A = "user-a-id"
USER_B = "user-b-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def _payload(**overrides):
    payload = {
        "timestamp": "2026-08-10T00:00:00",
        "merchant": "Corner Store",
        "description": "Snacks",
        "amount": 12.5,
        "category_id": "cat-1",
    }
    payload.update(overrides)
    return payload


def test_create_manual_transaction(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Food"}])

    response = client.post("/transactions/", json=_payload(), headers=_headers(make_token))

    assert response.status_code == 200
    txn = response.json()["transaction"]
    assert txn["merchant"] == "Corner Store"
    assert txn["amount"] == 12.5
    assert txn["source"] == "manual"
    assert txn["category_id"] == "cat-1"
    assert txn["is_manually_labeled"] is True
    assert txn["needs_review"] is False
    assert txn["upload_id"] is None


def test_create_manual_transaction_rejects_blank_merchant(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Food"}])

    response = client.post(
        "/transactions/", json=_payload(merchant="   "), headers=_headers(make_token)
    )

    assert response.status_code == 422


def test_create_manual_transaction_rejects_non_positive_amount(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Food"}])

    response = client.post(
        "/transactions/", json=_payload(amount=0), headers=_headers(make_token)
    )

    assert response.status_code == 422


def test_create_manual_transaction_rejects_category_owned_by_another_user(
    client, patch_jwks, make_token, fake_db
):
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_B, "name": "Food"}])

    response = client.post("/transactions/", json=_payload(), headers=_headers(make_token, sub=USER_A))

    assert response.status_code == 404


def test_create_manual_transaction_rejects_unknown_category(client, patch_jwks, make_token, fake_db):
    response = client.post(
        "/transactions/", json=_payload(category_id="does-not-exist"), headers=_headers(make_token)
    )

    assert response.status_code == 404
