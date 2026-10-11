"""PATCH /transactions/{id}/kind (contract §3.8), and the expense-only
guards on manual entry and /classify/*."""
USER_A = "user-a-id"
USER_B = "user-b-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def _seed(fake_db, **overrides):
    row = {
        "id": "t1", "user_id": USER_A, "merchant": "Landlord", "description": "rent",
        "amount": 3000, "timestamp": "2026-09-01T00:00:00+00:00", "category_id": "cat-1",
        "needs_review": False, "is_manually_labeled": True, "label_source": "override",
        "confidence": 0.9, "is_split": False, "kind": "expense", "flow_subtype": None,
        "categories": None,  # PostgREST embed; the fake doesn't join
    }
    row.update(overrides)
    fake_db.seed("transactions", [row])
    return fake_db._tables["transactions"].rows[-1]


def _patch(client, make_token, body, tid="t1", sub=USER_A):
    return client.patch(f"/transactions/{tid}/kind", json=body, headers=_headers(make_token, sub))


def test_expense_to_transfer_clears_category_and_review(client, patch_jwks, make_token, fake_db):
    row = _seed(fake_db)

    response = _patch(client, make_token, {"kind": "transfer", "flow_subtype": "p2p_transfer"})

    assert response.status_code == 200
    assert response.json() == {"transaction": {
        "id": "t1", "kind": "transfer", "flow_subtype": "p2p_transfer",
        "category_id": None, "needs_review": False}}
    assert row["label_source"] == "none" and row["confidence"] is None
    assert row["amount"] == 3000  # never changed


def test_transfer_to_expense_lands_in_review_queue(client, patch_jwks, make_token, fake_db):
    row = _seed(fake_db, kind="transfer", flow_subtype="p2p_transfer", category_id=None,
                label_source="none", is_manually_labeled=True)

    response = _patch(client, make_token, {"kind": "expense"})

    assert response.status_code == 200
    assert response.json()["transaction"]["needs_review"] is True
    assert row["kind"] == "expense" and row["flow_subtype"] is None
    assert row["is_manually_labeled"] is False and row["label_source"] == "none"
    queue = client.get("/dashboard/review-queue", headers=_headers(make_token)).json()
    assert [t["id"] for t in queue["transactions"]] == ["t1"]


def test_expense_subtype_change_keeps_category(client, patch_jwks, make_token, fake_db):
    row = _seed(fake_db, amount=-30)

    response = _patch(client, make_token, {"kind": "expense", "flow_subtype": "refund"})

    assert response.status_code == 200
    assert row["flow_subtype"] == "refund" and row["category_id"] == "cat-1"
    assert row["is_manually_labeled"] is True and row["needs_review"] is False


def test_unchanged_kind_is_a_no_op(client, patch_jwks, make_token, fake_db):
    row = _seed(fake_db, kind="income", flow_subtype="salary", category_id=None)
    row["label_source"] = "sentinel"  # would be overwritten by any write

    response = _patch(client, make_token, {"kind": "income", "flow_subtype": "salary"})

    assert response.status_code == 200
    assert response.json()["transaction"]["kind"] == "income"
    assert row["label_source"] == "sentinel"


def test_disallowed_pair_is_422(client, patch_jwks, make_token, fake_db):
    _seed(fake_db)
    assert _patch(client, make_token, {"kind": "income", "flow_subtype": "refund"}).status_code == 422
    assert _patch(client, make_token, {"kind": "expense", "flow_subtype": "salary"}).status_code == 422
    assert _patch(client, make_token, {"kind": "loan"}).status_code == 422


def test_other_users_row_is_404(client, patch_jwks, make_token, fake_db):
    row = _seed(fake_db)
    response = _patch(client, make_token, {"kind": "income"}, sub=USER_B)
    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found"
    assert row["kind"] == "expense"


def test_split_row_cannot_leave_expense(client, patch_jwks, make_token, fake_db):
    row = _seed(fake_db, is_split=True, category_id=None)
    response = _patch(client, make_token, {"kind": "transfer"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Unsplit this transaction before changing its kind"
    assert row["kind"] == "expense"


def test_manual_entry_is_always_an_expense(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Food"}])
    response = client.post("/transactions/", json={
        "timestamp": "2026-08-10T00:00:00", "merchant": "Corner Store", "description": "Snacks",
        "amount": 12.5, "category_id": "cat-1"}, headers=_headers(make_token))
    assert response.status_code == 200
    assert response.json()["transaction"]["kind"] == "expense"


def test_classify_label_refuses_non_expense_rows(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Food"}])
    row = _seed(fake_db, kind="income", flow_subtype="salary", category_id=None, is_manually_labeled=False)

    label = client.post("/classify/t1/label", json={"category_id": "cat-1"}, headers=_headers(make_token))
    split = client.post("/classify/t1/split", json={"splits": [
        {"category_id": "cat-1", "amount": 1000}, {"category_id": "cat-2", "amount": 2000}]},
        headers=_headers(make_token))
    accept = client.post("/classify/t1/accept", headers=_headers(make_token))

    assert (label.status_code, split.status_code, accept.status_code) == (404, 404, 404)
    assert row["category_id"] is None and row["needs_review"] is False


def test_training_set_excludes_rekinded_rows(client, patch_jwks, make_token, fake_db):
    # Labeled expense → income: keeps is_manually_labeled, loses its category.
    _seed(fake_db, kind="income", category_id=None)
    response = client.post("/training/retrain", headers=_headers(make_token))
    assert response.status_code == 400
    assert response.json()["detail"] == "No labeled transactions to train on"
