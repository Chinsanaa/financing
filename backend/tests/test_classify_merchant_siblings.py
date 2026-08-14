"""Labeling or accepting one transaction from a merchant must immediately
resolve every other still-`needs_review` transaction from that same
merchant too — "unique merchants only": a merchant shouldn't need labeling
more than once, and shouldn't keep resurfacing in the review queue just
because it has multiple pending rows.
"""

USER_A = "user-a-id"
USER_B = "user-b-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def test_labeling_one_transaction_resolves_other_pending_rows_from_same_merchant(
    client, patch_jwks, make_token, fake_db
):
    fake_db.seed("categories", [{"id": "cat-eat", "user_id": USER_A, "name": "Eating Out"}])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_A, "merchant": "Starbucks", "label_source": "model", "needs_review": True},
        {"id": "t2", "user_id": USER_A, "merchant": "Starbucks", "label_source": "model", "needs_review": True},
        {"id": "t3", "user_id": USER_A, "merchant": "Starbucks", "label_source": "model", "needs_review": True},
    ])

    response = client.post(
        "/classify/t1/label",
        json={"category_id": "cat-eat", "label_source": "override"},
        headers=_headers(make_token),
    )
    assert response.status_code == 200

    rows = {t["id"]: t for t in fake_db._tables["transactions"].rows}
    for tid in ("t1", "t2", "t3"):
        assert rows[tid]["needs_review"] is False
        assert rows[tid]["category_id"] == "cat-eat"
        assert rows[tid]["is_manually_labeled"] is True


def test_accepting_a_suggestion_resolves_other_pending_rows_from_same_merchant(
    client, patch_jwks, make_token, fake_db
):
    fake_db.seed("categories", [{"id": "cat-eat", "user_id": USER_A, "name": "Eating Out"}])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_A, "merchant": "Starbucks", "category_id": "cat-eat",
         "label_source": "model", "needs_review": True},
        {"id": "t2", "user_id": USER_A, "merchant": "Starbucks", "label_source": "model", "needs_review": True},
    ])

    response = client.post("/classify/t1/accept", headers=_headers(make_token))
    assert response.status_code == 200

    t2 = next(t for t in fake_db._tables["transactions"].rows if t["id"] == "t2")
    assert t2["needs_review"] is False
    assert t2["category_id"] == "cat-eat"


def test_sibling_apply_does_not_touch_other_merchants_or_already_resolved_rows(
    client, patch_jwks, make_token, fake_db
):
    fake_db.seed("categories", [{"id": "cat-eat", "user_id": USER_A, "name": "Eating Out"}])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_A, "merchant": "Starbucks", "label_source": "model", "needs_review": True},
        {"id": "t2", "user_id": USER_A, "merchant": "Costco", "label_source": "model", "needs_review": True},
        {"id": "t3", "user_id": USER_A, "merchant": "Starbucks", "category_id": "cat-other",
         "label_source": "override", "needs_review": False},
    ])

    response = client.post(
        "/classify/t1/label",
        json={"category_id": "cat-eat", "label_source": "override"},
        headers=_headers(make_token),
    )
    assert response.status_code == 200

    rows = {t["id"]: t for t in fake_db._tables["transactions"].rows}
    assert rows["t2"]["needs_review"] is True
    assert rows["t2"].get("category_id") is None
    # Already-resolved row for the same merchant is left as-is, not clobbered.
    assert rows["t3"]["category_id"] == "cat-other"


def test_sibling_apply_only_affects_the_authenticated_user(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-eat", "user_id": USER_A, "name": "Eating Out"}])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_A, "merchant": "Starbucks", "label_source": "model", "needs_review": True},
        {"id": "t2", "user_id": USER_B, "merchant": "Starbucks", "label_source": "model", "needs_review": True},
    ])

    response = client.post(
        "/classify/t1/label",
        json={"category_id": "cat-eat", "label_source": "override"},
        headers=_headers(make_token, sub=USER_A),
    )
    assert response.status_code == 200

    t2 = next(t for t in fake_db._tables["transactions"].rows if t["id"] == "t2")
    assert t2["needs_review"] is True
    assert t2.get("category_id") is None
