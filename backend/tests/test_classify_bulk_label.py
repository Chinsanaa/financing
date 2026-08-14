"""POST /classify/bulk-label: recategorize multiple transactions at once."""
USER_A = "user-a-id"
USER_B = "user-b-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def test_bulk_label_updates_all_transactions(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Shopping"}])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_A, "merchant": "Shop A", "label_source": "none", "category_id": None},
        {"id": "t2", "user_id": USER_A, "merchant": "Shop B", "label_source": "none", "category_id": None},
    ])

    response = client.post(
        "/classify/bulk-label",
        json={"transaction_ids": ["t1", "t2"], "category_id": "cat-1"},
        headers=_headers(make_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["updated"]) == 2
    assert body["not_found"] == []
    updated_ids = {t["id"] for t in body["updated"]}
    assert updated_ids == {"t1", "t2"}
    for t in fake_db._tables["transactions"].rows:
        assert t["category_id"] == "cat-1"
        assert t["needs_review"] is False


def test_bulk_label_reports_transactions_not_found(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Shopping"}])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_A, "merchant": "Shop A", "label_source": "none", "category_id": None},
    ])

    response = client.post(
        "/classify/bulk-label",
        json={"transaction_ids": ["t1", "does-not-exist"], "category_id": "cat-1"},
        headers=_headers(make_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["updated"]) == 1
    assert body["not_found"] == ["does-not-exist"]


def test_bulk_label_rejects_a_category_owned_by_another_user(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_B, "name": "Shopping"}])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_A, "merchant": "Shop A", "label_source": "none", "category_id": None},
    ])

    response = client.post(
        "/classify/bulk-label",
        json={"transaction_ids": ["t1"], "category_id": "cat-1"},
        headers=_headers(make_token, sub=USER_A),
    )

    assert response.status_code == 404


def test_bulk_label_cannot_touch_another_users_transactions(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Shopping"}])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_B, "merchant": "Shop A", "label_source": "none", "category_id": None},
    ])

    response = client.post(
        "/classify/bulk-label",
        json={"transaction_ids": ["t1"], "category_id": "cat-1"},
        headers=_headers(make_token, sub=USER_A),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["updated"] == []
    assert body["not_found"] == ["t1"]


def test_bulk_label_rejects_empty_list(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Shopping"}])

    response = client.post(
        "/classify/bulk-label",
        json={"transaction_ids": [], "category_id": "cat-1"},
        headers=_headers(make_token),
    )

    assert response.status_code == 400


def test_bulk_label_promotes_a_merchant_rule_per_transaction(client, patch_jwks, make_token, fake_db):
    """Every bulk-labeled transaction gets its merchant promoted to a rule
    now, not just llm-sourced ones — "unique merchants only" means labeling
    a merchant once (by any means) should be enough."""
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Eating Out"}])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_A, "merchant": "Obscure Ramen Shop", "label_source": "llm", "category_id": None},
        {"id": "t2", "user_id": USER_A, "merchant": "Known Chain", "label_source": "model", "category_id": None},
    ])

    response = client.post(
        "/classify/bulk-label",
        json={"transaction_ids": ["t1", "t2"], "category_id": "cat-1"},
        headers=_headers(make_token),
    )

    assert response.status_code == 200
    rules = fake_db._tables["merchant_rules"].rows
    assert len(rules) == 2
    rules_by_merchant = {r["merchant_pattern"]: r for r in rules}
    assert rules_by_merchant["obscure ramen shop"]["source"] == "llm_confirmed"
    assert rules_by_merchant["known chain"]["source"] == "user_created"
