"""Renaming a category must not silently orphan existing merchant/special
rules that targeted the old name (backend/routes/categories.py).

merchant_rules.category_name / special_rules.category_name are matched back
to a live category by NAME in ml.py::_fetch_categories — a rename that
doesn't also update these rows makes every rule pointing at the old name
stop resolving to any category, permanently.
"""

USER_A = "user-a-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def test_renaming_a_category_updates_matching_merchant_rules(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Eating Out"}])
    fake_db.seed("merchant_rules", [
        {"id": "r1", "user_id": USER_A, "merchant_pattern": "some cafe", "category_name": "Eating Out", "source": "user_created"},
        {"id": "r2", "user_id": USER_A, "merchant_pattern": "some shop", "category_name": "Shopping", "source": "user_created"},
    ])

    response = client.put(
        "/categories/cat-1",
        json={"name": "Food & Dining"},
        headers=_headers(make_token),
    )

    assert response.status_code == 200
    rules = {r["merchant_pattern"]: r["category_name"] for r in fake_db._tables["merchant_rules"].rows}
    assert rules["some cafe"] == "Food & Dining"
    assert rules["some shop"] == "Shopping"  # untouched — different category


def test_renaming_a_category_updates_matching_special_rules(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Eating Out"}])
    fake_db.seed("special_rules", [
        {"id": "s1", "user_id": USER_A, "merchant_pattern": "campus cafeteria", "category_name": "Eating Out"},
    ])

    response = client.put(
        "/categories/cat-1",
        json={"name": "Food & Dining"},
        headers=_headers(make_token),
    )

    assert response.status_code == 200
    special = fake_db._tables["special_rules"].rows[0]
    assert special["category_name"] == "Food & Dining"


def test_rename_sync_only_touches_this_users_rules(client, patch_jwks, make_token, fake_db):
    USER_B = "user-b-id"
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Eating Out"}])
    fake_db.seed("merchant_rules", [
        {"id": "r1", "user_id": USER_A, "merchant_pattern": "cafe a", "category_name": "Eating Out", "source": "user_created"},
        {"id": "r2", "user_id": USER_B, "merchant_pattern": "cafe b", "category_name": "Eating Out", "source": "user_created"},
    ])

    client.put("/categories/cat-1", json={"name": "Food & Dining"}, headers=_headers(make_token, USER_A))

    rules = {r["id"]: r["category_name"] for r in fake_db._tables["merchant_rules"].rows}
    assert rules["r1"] == "Food & Dining"
    assert rules["r2"] == "Eating Out"  # a different user's rule, untouched


def test_updating_non_name_fields_does_not_touch_rules(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Eating Out", "color": None}])
    fake_db.seed("merchant_rules", [
        {"id": "r1", "user_id": USER_A, "merchant_pattern": "cafe a", "category_name": "Eating Out", "source": "user_created"},
    ])

    response = client.put("/categories/cat-1", json={"color": "amber"}, headers=_headers(make_token))

    assert response.status_code == 200
    assert fake_db._tables["merchant_rules"].rows[0]["category_name"] == "Eating Out"
