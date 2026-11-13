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


def test_bulk_label_five_rows_two_merchants_one_foreign(client, patch_jwks, make_token, fake_db):
    """Response shape and final DB state must match the old per-row loop."""
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Eating Out"}])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_A, "merchant": "Ramen Shop", "label_source": "llm", "category_id": None, "needs_review": True},
        {"id": "t2", "user_id": USER_A, "merchant": "ramen shop ", "label_source": "model", "category_id": None, "needs_review": True},
        {"id": "t3", "user_id": USER_A, "merchant": "Known Chain", "label_source": "model", "category_id": None, "needs_review": True, "is_split": True},
        {"id": "t4", "user_id": USER_A, "merchant": "Known Chain", "label_source": "none", "category_id": None, "needs_review": True},
        {"id": "t5", "user_id": USER_B, "merchant": "Other Person", "label_source": "none", "category_id": None, "needs_review": True},
        {"id": "t6", "user_id": USER_A, "merchant": "Untouched", "label_source": "none", "category_id": None, "needs_review": True},
    ])
    fake_db.seed("transaction_splits", [
        {"id": "s1", "user_id": USER_A, "transaction_id": "t3", "category_id": "cat-1", "amount": 1.0},
        {"id": "s2", "user_id": USER_B, "transaction_id": "t5", "category_id": "cat-1", "amount": 1.0},
    ])

    response = client.post(
        "/classify/bulk-label",
        json={"transaction_ids": ["t4", "t5", "t1", "t3", "t2"], "category_id": "cat-1"},
        headers=_headers(make_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"updated", "not_found"}
    assert [t["id"] for t in body["updated"]] == ["t4", "t1", "t3", "t2"]  # request order
    assert body["not_found"] == ["t5"]
    rows = {r["id"]: r for r in fake_db._tables["transactions"].rows}
    for tid in ("t1", "t2", "t3", "t4"):
        assert rows[tid]["category_id"] == "cat-1"
        assert rows[tid]["label_source"] == "override"
        assert rows[tid]["needs_review"] is False
        assert rows[tid]["is_manually_labeled"] is True
        assert rows[tid]["is_split"] is False
    assert rows["t5"]["category_id"] is None and rows["t5"]["user_id"] == USER_B
    assert rows["t6"]["category_id"] is None and rows["t6"]["needs_review"] is True
    # Only the other user's split survives.
    assert [s["id"] for s in fake_db._tables["transaction_splits"].rows] == ["s2"]
    # One rule per distinct merchant; t1 (llm) came first in the request.
    rules = {(r["merchant_pattern"], r["category_name"]): r["source"] for r in fake_db._tables["merchant_rules"].rows}
    assert rules == {
        ("known chain", "Eating Out"): "user_created",
        ("ramen shop", "Eating Out"): "llm_confirmed",
    }


def test_bulk_label_query_count_is_constant_in_id_count(client, patch_jwks, make_token, fake_db, monkeypatch):
    from fake_supabase import FakeQueryBuilder
    import routes.classify as classify_routes

    # The budget-alert background task runs inside TestClient; keep its
    # queries out of the count (it is a single call either way).
    async def _noop(user_id):
        return None
    monkeypatch.setattr(classify_routes, "check_budget_alerts", _noop)

    calls = []
    real_execute = FakeQueryBuilder.execute
    monkeypatch.setattr(FakeQueryBuilder, "execute", lambda self: (calls.append(self._op), real_execute(self))[1])

    def run(n):
        fake_db._tables.pop("transactions", None)
        fake_db._tables.pop("merchant_rules", None)
        fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Shopping"}])
        fake_db.seed("transactions", [
            {"id": f"t{i}", "user_id": USER_A, "merchant": f"Shop {i % 2}", "label_source": "none", "category_id": None}
            for i in range(n)
        ])
        calls.clear()
        response = client.post(
            "/classify/bulk-label",
            json={"transaction_ids": [f"t{i}" for i in range(n)], "category_id": "cat-1"},
            headers=_headers(make_token),
        )
        assert response.status_code == 200
        assert len(response.json()["updated"]) == n
        return len(calls)

    small, large = run(4), run(50)
    # category check + select + splits delete + update + 2 merchant upserts
    assert small == large == 6
