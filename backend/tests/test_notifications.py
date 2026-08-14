"""GET/POST /dashboard/notifications: persisted notification history
backing the header bell -- read/unread + clear."""
from datetime import datetime, timezone

USER_A = "user-a-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _old_iso():
    return datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()


def test_welcome_lazily_inserted_once_for_a_new_account(client, patch_jwks, make_token, fake_db):
    fake_db.seed("profiles", [{"id": USER_A, "created_at": _now_iso()}])

    first = client.get("/dashboard/notifications", headers=_headers(make_token))
    second = client.get("/dashboard/notifications", headers=_headers(make_token))

    assert first.status_code == 200
    welcomes = [n for n in first.json()["notifications"] if n["type"] == "welcome"]
    assert len(welcomes) == 1
    assert first.json()["unread_count"] == 1

    # Second fetch does not insert a duplicate.
    welcomes2 = [n for n in second.json()["notifications"] if n["type"] == "welcome"]
    assert len(welcomes2) == 1


def test_welcome_not_inserted_for_an_old_account(client, patch_jwks, make_token, fake_db):
    fake_db.seed("profiles", [{"id": USER_A, "created_at": _old_iso()}])

    response = client.get("/dashboard/notifications", headers=_headers(make_token))

    assert response.status_code == 200
    assert not any(n["type"] == "welcome" for n in response.json()["notifications"])


def test_budget_crossing_notification_is_deduplicated(client, patch_jwks, make_token, fake_db):
    fake_db.seed("profiles", [{"id": USER_A, "created_at": _old_iso()}])
    cat_id = "cat-shopping"
    fake_db.seed("categories", [{"id": cat_id, "user_id": USER_A, "name": "Shopping"}])
    fake_db.seed("budget_category_config", [{
        "id": "bcc-1", "user_id": USER_A, "category_id": cat_id,
        "categories": {"name": "Shopping"}, "monthly_budget": 100,
    }])
    fake_db.seed("transactions", [{
        "id": "txn-1", "user_id": USER_A, "category_id": cat_id,
        "categories": {"name": "Shopping"}, "amount": 150,
        "timestamp": _now_iso(), "needs_review": False,
    }])

    from alerts import check_budget_alerts
    import asyncio
    asyncio.run(check_budget_alerts(USER_A))
    asyncio.run(check_budget_alerts(USER_A))  # same crossing again -- must not duplicate

    response = client.get("/dashboard/notifications", headers=_headers(make_token))
    assert response.status_code == 200
    over = [n for n in response.json()["notifications"] if n["type"] == "over_budget"]
    assert len(over) == 1
    assert over[0]["payload"]["category"] == "Shopping"


def test_mark_read_clears_unread_count(client, patch_jwks, make_token, fake_db):
    fake_db.seed("profiles", [{"id": USER_A, "created_at": _now_iso()}])
    client.get("/dashboard/notifications", headers=_headers(make_token))  # seeds welcome

    read_resp = client.post("/dashboard/notifications/read", headers=_headers(make_token))
    assert read_resp.status_code == 200

    after = client.get("/dashboard/notifications", headers=_headers(make_token))
    assert after.json()["unread_count"] == 0
    assert len(after.json()["notifications"]) == 1  # still listed, just read


def test_clear_removes_notifications_from_the_list(client, patch_jwks, make_token, fake_db):
    fake_db.seed("profiles", [{"id": USER_A, "created_at": _now_iso()}])
    client.get("/dashboard/notifications", headers=_headers(make_token))  # seeds welcome

    clear_resp = client.post("/dashboard/notifications/clear", headers=_headers(make_token))
    assert clear_resp.status_code == 200

    after = client.get("/dashboard/notifications", headers=_headers(make_token))
    assert after.json()["notifications"] == []
    assert after.json()["unread_count"] == 0


def test_cleared_notification_does_not_reappear_on_refetch(client, patch_jwks, make_token, fake_db):
    fake_db.seed("profiles", [{"id": USER_A, "created_at": _now_iso()}])
    client.get("/dashboard/notifications", headers=_headers(make_token))
    client.post("/dashboard/notifications/clear", headers=_headers(make_token))

    after = client.get("/dashboard/notifications", headers=_headers(make_token))
    assert not any(n["type"] == "welcome" for n in after.json()["notifications"])
