"""GET /dashboard/action: over-budget, approaching-budget, and review-queue
action items."""
from datetime import datetime, timezone

USER_A = "user-a-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _seed_budget(fake_db, user_id, category_name, monthly_budget, spend):
    cat_id = f"cat-{category_name}"
    fake_db.seed("categories", [{"id": cat_id, "user_id": user_id, "name": category_name}])
    fake_db.seed("budget_category_config", [
        {
            "id": f"bcc-{category_name}",
            "user_id": user_id,
            "category_id": cat_id,
            "categories": {"name": category_name},
            "monthly_budget": monthly_budget,
        }
    ])
    if spend:
        fake_db.seed("transactions", [
            {
                "id": f"txn-{category_name}",
                "user_id": user_id,
                "category_id": cat_id,
                "categories": {"name": category_name},
                "amount": spend,
                "timestamp": _now_iso(),
                "needs_review": False,
            }
        ])


def test_over_budget_category_flagged(client, patch_jwks, make_token, fake_db):
    _seed_budget(fake_db, USER_A, "Shopping", monthly_budget=100, spend=150)

    response = client.get("/dashboard/action", headers=_headers(make_token))

    assert response.status_code == 200
    actions = response.json()["actions"]
    over = [a for a in actions if a["type"] == "over_budget"]
    assert len(over) == 1
    assert over[0]["category"] == "Shopping"
    assert over[0]["overage"] == 50


def test_approaching_budget_category_flagged_at_80_percent(client, patch_jwks, make_token, fake_db):
    _seed_budget(fake_db, USER_A, "Eating Out", monthly_budget=100, spend=85)

    response = client.get("/dashboard/action", headers=_headers(make_token))

    assert response.status_code == 200
    actions = response.json()["actions"]
    approaching = [a for a in actions if a["type"] == "approaching_budget"]
    assert len(approaching) == 1
    assert approaching[0]["category"] == "Eating Out"
    assert approaching[0]["pct"] == 85.0
    assert not any(a["type"] == "over_budget" for a in actions)


def test_under_threshold_category_not_flagged(client, patch_jwks, make_token, fake_db):
    _seed_budget(fake_db, USER_A, "Groceries", monthly_budget=100, spend=50)

    response = client.get("/dashboard/action", headers=_headers(make_token))

    assert response.status_code == 200
    actions = response.json()["actions"]
    assert not any(a["category"] == "Groceries" for a in actions)


def test_over_budget_takes_priority_over_approaching(client, patch_jwks, make_token, fake_db):
    """A category can't be both over_budget and approaching_budget at once."""
    _seed_budget(fake_db, USER_A, "Transportation", monthly_budget=100, spend=120)

    response = client.get("/dashboard/action", headers=_headers(make_token))

    actions = [a for a in response.json()["actions"] if a["category"] == "Transportation"]
    assert len(actions) == 1
    assert actions[0]["type"] == "over_budget"


def test_budget_inapp_disabled_hides_over_and_approaching_but_not_pending_review(
    client, patch_jwks, make_token, fake_db
):
    fake_db.seed("profiles", [{"id": USER_A, "budget_inapp_enabled": False}])
    _seed_budget(fake_db, USER_A, "Shopping", monthly_budget=100, spend=150)
    fake_db.seed("transactions", [{
        "id": "txn-review", "user_id": USER_A, "category_id": None,
        "needs_review": True, "timestamp": _now_iso(),
    }])

    response = client.get("/dashboard/action", headers=_headers(make_token))

    assert response.status_code == 200
    actions = response.json()["actions"]
    assert not any(a["type"] in ("over_budget", "approaching_budget") for a in actions)
    assert any(a["type"] == "pending_review" for a in actions)


def test_pending_review_inapp_disabled_hides_review_but_not_budget(
    client, patch_jwks, make_token, fake_db
):
    fake_db.seed("profiles", [{"id": USER_A, "pending_review_inapp_enabled": False}])
    _seed_budget(fake_db, USER_A, "Shopping", monthly_budget=100, spend=150)
    fake_db.seed("transactions", [{
        "id": "txn-review", "user_id": USER_A, "category_id": None,
        "needs_review": True, "timestamp": _now_iso(),
    }])

    response = client.get("/dashboard/action", headers=_headers(make_token))

    assert response.status_code == 200
    actions = response.json()["actions"]
    assert not any(a["type"] == "pending_review" for a in actions)
    assert any(a["type"] == "over_budget" for a in actions)


def test_both_notification_types_default_enabled_with_no_profile_row(
    client, patch_jwks, make_token, fake_db
):
    """No seeded profile row at all -> both toggles default to enabled."""
    _seed_budget(fake_db, USER_A, "Shopping", monthly_budget=100, spend=150)
    fake_db.seed("transactions", [{
        "id": "txn-review", "user_id": USER_A, "category_id": None,
        "needs_review": True, "timestamp": _now_iso(),
    }])

    response = client.get("/dashboard/action", headers=_headers(make_token))

    assert response.status_code == 200
    actions = response.json()["actions"]
    assert any(a["type"] == "over_budget" for a in actions)
    assert any(a["type"] == "pending_review" for a in actions)
