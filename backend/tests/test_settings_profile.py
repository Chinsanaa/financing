"""GET/PATCH /settings/profile home_currency (contract API_V5 §3.2)."""
import threading
import time
from datetime import date

import httpx
import pytest

import fx


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    calls = []

    def _sync(self, request):
        calls.append(str(request.url))
        raise AssertionError(f"outbound HTTP attempted: {request.url}")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _sync)
    return calls


@pytest.fixture
def db(fake_db, monkeypatch):
    """fake_db plus fx wired to the same fake, clean fx state, a profile."""
    monkeypatch.setattr(fx, "supabase_client", fake_db)
    monkeypatch.setattr(fx, "_new_client", lambda: fake_db)
    monkeypatch.setattr(fx, "_today", lambda: date(2026, 10, 8))
    fx._reset_state()
    fake_db.seed("profiles", [
        {"id": "user-a", "monthly_income": 0, "alert_email_enabled": False},
        {"id": "user-b", "monthly_income": 0, "home_currency": "EUR"},
    ])
    yield fake_db
    fx._reset_state()


@pytest.fixture
def jobs(monkeypatch):
    """Record fx background jobs instead of starting threads."""
    recorded = []
    monkeypatch.setattr(fx, "_spawn", lambda target, *args, name="fx": recorded.append((target.__name__, args)))
    return recorded


def _h(make_token, sub="user-a"):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def _profile(db, user_id):
    return next(r for r in db._tables["profiles"].rows if r["id"] == user_id)


def test_get_profile_includes_home_currency(client, patch_jwks, make_token, db, jobs):
    r = client.get("/settings/profile", headers=_h(make_token))
    assert r.status_code == 200
    assert r.json()["profile"]["home_currency"] is None
    r = client.get("/settings/profile", headers=_h(make_token, "user-b"))
    assert r.json()["profile"]["home_currency"] == "EUR"
    assert jobs == []


@pytest.mark.parametrize("value", ["usd", " USD ", "Usd"])
def test_patch_normalizes_and_requests_backfill(client, patch_jwks, make_token, db, jobs, value):
    r = client.patch("/settings/profile", json={"home_currency": value}, headers=_h(make_token))
    assert r.status_code == 200
    assert r.json()["profile"]["home_currency"] == "USD"
    assert _profile(db, "user-a")["home_currency"] == "USD"
    assert jobs == [("_user_backfill_job", ("user-a", None))]


@pytest.mark.parametrize("value", ["CNY", "cny", " Cny "])
def test_patch_cny_is_422(client, patch_jwks, make_token, db, jobs, value):
    r = client.patch("/settings/profile", json={"home_currency": value}, headers=_h(make_token, "user-b"))
    assert r.status_code == 422
    assert r.json() == {"detail": "CNY is the base currency; clear home_currency with null instead"}
    assert _profile(db, "user-b")["home_currency"] == "EUR"
    assert jobs == []


@pytest.mark.parametrize("value, shown", [("xyz", "XYZ"), ("BGN", "BGN"), ("US", "US"), ("", "")])
def test_patch_unsupported_is_422(client, patch_jwks, make_token, db, jobs, value, shown):
    r = client.patch("/settings/profile", json={"home_currency": value}, headers=_h(make_token))
    assert r.status_code == 422
    assert r.json() == {"detail": f"Unsupported home currency '{shown}'. See GET /fx/currencies."}
    assert "home_currency" not in _profile(db, "user-a")
    assert jobs == []


def test_patch_null_clears(client, patch_jwks, make_token, db, jobs):
    r = client.patch("/settings/profile", json={"home_currency": None}, headers=_h(make_token, "user-b"))
    assert r.status_code == 200
    assert r.json()["profile"]["home_currency"] is None
    assert _profile(db, "user-b")["home_currency"] is None
    assert jobs == []


def test_patch_without_field_leaves_it_untouched(client, patch_jwks, make_token, db, jobs):
    r = client.patch("/settings/profile", json={"monthly_income": 9000}, headers=_h(make_token, "user-b"))
    assert r.status_code == 200
    assert r.json()["profile"]["home_currency"] == "EUR"
    assert r.json()["profile"]["monthly_income"] == 9000
    assert jobs == []


def test_patch_empty_body_still_400(client, patch_jwks, make_token, db, jobs):
    r = client.patch("/settings/profile", json={}, headers=_h(make_token))
    assert r.status_code == 400
    assert r.json() == {"detail": "No fields to update"}


def test_patch_only_touches_callers_row(client, patch_jwks, make_token, db, jobs):
    client.patch("/settings/profile", json={"home_currency": "JPY"}, headers=_h(make_token))
    assert _profile(db, "user-a")["home_currency"] == "JPY"
    assert _profile(db, "user-b")["home_currency"] == "EUR"


def test_patch_returns_without_waiting_for_the_network(client, patch_jwks, make_token, db, monkeypatch):
    """Real background thread, Frankfurter mocked as slow: PATCH must return
    at once, and the rates land afterwards."""
    release = threading.Event()
    fetched = threading.Event()

    def slow_fetch(quote, start, end):
        release.wait(5)
        fetched.set()
        return {date(2026, 10, 7): 0.1387}

    monkeypatch.setattr(fx, "_fetch_series", slow_fetch)
    try:
        t0 = time.monotonic()
        r = client.patch("/settings/profile", json={"home_currency": "usd"}, headers=_h(make_token))
        elapsed = time.monotonic() - t0
        assert r.status_code == 200
        assert r.json()["profile"]["home_currency"] == "USD"
        assert elapsed < 1.0
        assert not fetched.is_set()
    finally:
        release.set()
    assert fetched.wait(5)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and fx._running:  # worker finishes its upsert
        time.sleep(0.01)
    rows = db._tables["fx_rates"].rows
    assert [(r["quote"], r["rate_date"], r["rate"]) for r in rows] == [("USD", "2026-10-07", 0.1387)]
