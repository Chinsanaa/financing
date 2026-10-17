"""Regression tests for the 2026-10 hardening pass (Session 77)."""
USER_A = "user-a-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def test_removed_auth_endpoints_are_gone(client):
    # /auth/login and /auth/signup signed in on the shared service-role
    # client, swapping its token to the user's JWT for every later query.
    # They are not public paths any more, so the middleware answers 401
    # before routing; either way they can't reach Supabase Auth.
    for path in ("/auth/login", "/auth/signup", "/auth/logout"):
        response = client.post(path, json={"email": "a@b.co", "password": "x"})
        assert response.status_code in (401, 404), path


def test_removed_auth_endpoints_404_for_signed_in_user(client, patch_jwks, make_token):
    response = client.post("/auth/login", json={}, headers=_headers(make_token))
    assert response.status_code == 404


def test_label_source_cannot_be_spoofed(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [{"id": "cat-1", "user_id": USER_A, "name": "Groceries"}])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_A, "merchant": "Shop", "kind": "expense", "category_id": None},
    ])
    response = client.post(
        "/classify/t1/label",
        json={"category_id": "cat-1", "label_source": "rule"},
        headers=_headers(make_token),
    )
    assert response.status_code == 422


def test_trends_clamps_huge_ranges(client, patch_jwks, make_token, fake_db):
    for query in ("granularity=day&days=99999999", "granularity=month&months=99999999"):
        response = client.get(f"/dashboard/trends?{query}", headers=_headers(make_token))
        assert response.status_code == 200, query


def test_fetch_rules_user_rules_override_global(monkeypatch, fake_db):
    import ml

    monkeypatch.setattr(ml, "supabase_client", fake_db)
    fake_db.seed("merchant_rules", [
        {"id": "r1", "user_id": None, "merchant_pattern": " Starbucks ", "category_name": "Food & Dining"},
        {"id": "r2", "user_id": USER_A, "merchant_pattern": "starbucks", "category_name": "Work"},
        {"id": "r3", "user_id": "someone-else", "merchant_pattern": "didi", "category_name": "Shopping"},
    ])
    rules = ml._fetch_rules(USER_A)
    assert rules["starbucks"] == "Work"
    assert "didi" not in rules


def test_alert_threshold_zero_is_respected_everywhere():
    # alerts.py used `or 80`, turning an explicit 0 into 80 for emails while
    # the in-app path kept 0. Both now share budget.alert_threshold_pct.
    from budget import alert_threshold_pct

    assert alert_threshold_pct({"alert_threshold_pct": 0}) == 0
    assert alert_threshold_pct({"alert_threshold_pct": None}) == 80
    assert alert_threshold_pct(None) == 80
