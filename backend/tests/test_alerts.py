"""backend/alerts.py::check_budget_alerts — email de-dup and gating.

No pytest-asyncio/anyio plugin is configured in this project, so async
`check_budget_alerts` is driven directly via `asyncio.run()` from ordinary
sync test functions rather than via an async-test marker.
"""
import asyncio
import pytest
from datetime import datetime, timezone

import alerts

USER_A = "user-a-id"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _seed_over_budget_category(fake_db, user_id, category_name="Shopping", budget=100, spend=150):
    cat_id = f"cat-{category_name}"
    fake_db.seed("categories", [{"id": cat_id, "user_id": user_id, "name": category_name}])
    fake_db.seed("budget_category_config", [
        {
            "id": f"bcc-{category_name}",
            "user_id": user_id,
            "category_id": cat_id,
            "categories": {"name": category_name},
            "monthly_budget": budget,
        }
    ])
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
    return cat_id


@pytest.fixture
def spy_email(monkeypatch):
    calls = []

    async def fake_send(to_email, subject, body):
        calls.append((to_email, subject, body))

    monkeypatch.setattr(alerts, "send_alert_email", fake_send)
    return calls


def _run(user_id):
    asyncio.run(alerts.check_budget_alerts(user_id))


def test_skips_when_alert_email_disabled(fake_db, spy_email):
    fake_db.seed("profiles", [{"id": USER_A, "alert_email_enabled": False, "alert_threshold_pct": 80}])
    _seed_over_budget_category(fake_db, USER_A)

    _run(USER_A)

    assert spy_email == []
    assert fake_db._tables.get("budget_alerts", None) is None or fake_db._tables["budget_alerts"].rows == []


def test_sends_email_and_records_alert_when_enabled(fake_db, spy_email):
    fake_db.seed("profiles", [{"id": USER_A, "alert_email_enabled": True, "alert_threshold_pct": 80}])
    fake_db.seed_user_email(USER_A, "user-a@example.com")
    _seed_over_budget_category(fake_db, USER_A)

    _run(USER_A)

    assert len(spy_email) == 1
    to_email, subject, body = spy_email[0]
    assert to_email == "user-a@example.com"
    assert "Shopping" in body

    alert_rows = fake_db._tables["budget_alerts"].rows
    assert len(alert_rows) == 1
    assert alert_rows[0]["kind"] == "over"


def test_does_not_resend_for_the_same_crossing(fake_db, spy_email):
    fake_db.seed("profiles", [{"id": USER_A, "alert_email_enabled": True, "alert_threshold_pct": 80}])
    fake_db.seed_user_email(USER_A, "user-a@example.com")
    _seed_over_budget_category(fake_db, USER_A)

    _run(USER_A)
    _run(USER_A)

    assert len(spy_email) == 1
    assert len(fake_db._tables["budget_alerts"].rows) == 1


def test_no_email_when_no_categories_are_crossed(fake_db, spy_email):
    fake_db.seed("profiles", [{"id": USER_A, "alert_email_enabled": True, "alert_threshold_pct": 80}])
    fake_db.seed_user_email(USER_A, "user-a@example.com")
    _seed_over_budget_category(fake_db, USER_A, budget=1000, spend=50)  # well under threshold

    _run(USER_A)

    assert spy_email == []


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def test_labeling_a_transaction_triggers_the_alert_check_end_to_end(
    client, patch_jwks, make_token, fake_db, spy_email
):
    """POST /classify/{id}/label wires up BackgroundTasks -> check_budget_alerts
    -> mailer for real, not just via a direct unit-test call."""
    fake_db.seed("profiles", [{"id": USER_A, "alert_email_enabled": True, "alert_threshold_pct": 80}])
    fake_db.seed_user_email(USER_A, "user-a@example.com")
    cat_id = _seed_over_budget_category(fake_db, USER_A, spend=0)  # budget row exists, no spend yet
    # `categories` is pre-set to match the category this test labels the
    # transaction into: the fake DB doesn't recompute embedded-relation
    # fields after an .update() changes category_id (no live joins), so
    # every row `_spend_by_category` reads needs a consistent `categories`
    # value up front, same as every other test seeding this fake.
    fake_db.seed("transactions", [{
        "id": "txn-new", "user_id": USER_A, "merchant": "Big Store",
        "category_id": None, "categories": {"name": "Shopping"},
        "needs_review": True, "amount": 200, "timestamp": _now_iso(),
    }])

    response = client.post(
        "/classify/txn-new/label",
        json={"category_id": cat_id, "label_source": "override"},
        headers=_headers(make_token),
    )

    assert response.status_code == 200
    assert len(spy_email) == 1
    assert "Shopping" in spy_email[0][2]
