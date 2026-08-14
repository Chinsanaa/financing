"""Labeling or accepting a transaction (any label_source) must write back a
new per-user merchant_rules row — the "generalization" loop: the next
transaction from that merchant hits the fast rule path instead of needing
review again (llm-sourced labels get source='llm_confirmed', everything
else gets source='user_created')."""

USER_A = "user-a-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def _merchant_rule_rows(fake_db):
    table = fake_db._tables.get("merchant_rules")
    return table.rows if table else []


def test_labeling_an_llm_transaction_creates_a_merchant_rule(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-eat", "user_id": USER_A, "name": "Eating Out"}])
    fake_db.seed("transactions", [{
        "id": "t1", "user_id": USER_A, "merchant": "Obscure Ramen Shop",
        "label_source": "llm", "needs_review": True,
    }])

    response = client.post(
        "/classify/t1/label",
        json={"category_id": "cat-eat", "label_source": "override"},
        headers=_headers(make_token),
    )

    assert response.status_code == 200
    rules = fake_db._tables["merchant_rules"].rows
    assert len(rules) == 1
    assert rules[0]["merchant_pattern"] == "obscure ramen shop"
    assert rules[0]["category_name"] == "Eating Out"
    assert rules[0]["source"] == "llm_confirmed"
    assert rules[0]["user_id"] == USER_A


def test_labeling_a_non_llm_transaction_also_creates_a_rule(client, patch_jwks, make_token, fake_db):
    """Manual labels promote a rule too now (source='user_created'), not
    just llm-confirmed ones — so this merchant never needs re-labeling."""
    fake_db.seed("categories", [{"id": "cat-eat", "user_id": USER_A, "name": "Eating Out"}])
    fake_db.seed("transactions", [{
        "id": "t1", "user_id": USER_A, "merchant": "Known Chain",
        "label_source": "model", "needs_review": True,
    }])

    response = client.post(
        "/classify/t1/label",
        json={"category_id": "cat-eat", "label_source": "override"},
        headers=_headers(make_token),
    )

    assert response.status_code == 200
    rules = _merchant_rule_rows(fake_db)
    assert len(rules) == 1
    assert rules[0]["merchant_pattern"] == "known chain"
    assert rules[0]["source"] == "user_created"


def test_accepting_an_llm_suggestion_creates_a_rule_and_stays_confirmed_llm_source(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-eat", "user_id": USER_A, "name": "Eating Out"}])
    fake_db.seed("transactions", [{
        "id": "t1", "user_id": USER_A, "merchant": "Obscure Ramen Shop",
        "category_id": "cat-eat", "label_source": "llm", "needs_review": True,
    }])

    response = client.post("/classify/t1/accept", headers=_headers(make_token))

    assert response.status_code == 200
    txn = response.json()["transaction"]
    assert txn["needs_review"] is False
    assert txn["label_source"] == "llm"

    rules = fake_db._tables["merchant_rules"].rows
    assert len(rules) == 1
    assert rules[0]["category_name"] == "Eating Out"
    assert rules[0]["source"] == "llm_confirmed"


def test_accepting_a_model_suggestion_also_creates_a_rule(client, patch_jwks, make_token, fake_db):
    """Accepting a model (non-llm) suggestion promotes a rule too now."""
    fake_db.seed("categories", [{"id": "cat-eat", "user_id": USER_A, "name": "Eating Out"}])
    fake_db.seed("transactions", [{
        "id": "t1", "user_id": USER_A, "merchant": "Known Chain",
        "category_id": "cat-eat", "label_source": "model", "needs_review": True,
    }])

    response = client.post("/classify/t1/accept", headers=_headers(make_token))

    assert response.status_code == 200
    txn = response.json()["transaction"]
    assert txn["label_source"] == "model_agreed"
    rules = _merchant_rule_rows(fake_db)
    assert len(rules) == 1
    assert rules[0]["merchant_pattern"] == "known chain"
    assert rules[0]["source"] == "user_created"


def test_second_transaction_from_same_merchant_now_matches_the_new_rule(client, patch_jwks, make_token, fake_db, monkeypatch):
    """End-to-end proof of the generalization loop: after confirming one LLM
    suggestion, ml._fetch_rules picks up the new rule for the next
    transaction from that merchant (no second LLM call needed)."""
    import ml
    monkeypatch.setattr(ml, "supabase_client", fake_db)

    fake_db.seed("categories", [{"id": "cat-eat", "user_id": USER_A, "name": "Eating Out"}])
    fake_db.seed("transactions", [{
        "id": "t1", "user_id": USER_A, "merchant": "Obscure Ramen Shop",
        "label_source": "llm", "needs_review": True,
    }])

    client.post(
        "/classify/t1/label",
        json={"category_id": "cat-eat", "label_source": "override"},
        headers=_headers(make_token),
    )

    patterns = ml._fetch_rules(USER_A)
    assert patterns.get("obscure ramen shop") == "Eating Out"
