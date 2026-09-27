"""Onboarding tour: per-account state, advances one step at a time only
when the completed step IS the current one; skip ends it for good."""
import pytest

USER = "user-a-id"


def _h(make_token):
    return {"Authorization": f"Bearer {make_token(sub=USER)}"}


@pytest.fixture
def new_account(fake_db):
    # New signup: the column defaults (step 0, not finished).
    fake_db.seed("profiles", [{"id": USER, "tour_step": 0, "tour_finished_at": None}])
    return fake_db


def _advance(client, make_token, step):
    return client.post("/dashboard/tour/advance", json={"completed": step}, headers=_h(make_token))


def test_new_account_starts_at_upload(client, patch_jwks, make_token, new_account):
    r = client.get("/dashboard/tour", headers=_h(make_token))
    assert r.json() == {"finished": False, "step": "upload"}


def test_existing_account_is_finished(client, patch_jwks, make_token, fake_db):
    fake_db.seed("profiles", [{"id": USER, "tour_step": 0, "tour_finished_at": "2026-09-27T00:00:00Z"}])
    assert client.get("/dashboard/tour", headers=_h(make_token)).json() == {"finished": True, "step": None}


def test_steps_advance_in_order_and_last_one_finishes(client, patch_jwks, make_token, new_account):
    assert _advance(client, make_token, "upload").json()["step"] == "categories"
    assert _advance(client, make_token, "categories").json()["step"] == "label"
    assert _advance(client, make_token, "label").json()["step"] == "train"
    assert _advance(client, make_token, "train").json() == {"finished": True, "step": None}


def test_cannot_skip_ahead(client, patch_jwks, make_token, new_account):
    # e.g. a manual label fired before any upload — must not move the tour.
    assert _advance(client, make_token, "label").json()["step"] == "upload"
    assert _advance(client, make_token, "train").json()["step"] == "upload"


def test_repeat_is_a_noop(client, patch_jwks, make_token, new_account):
    # Uploading a second file must not advance past "categories".
    _advance(client, make_token, "upload")
    assert _advance(client, make_token, "upload").json()["step"] == "categories"


def test_skip_ends_tour_and_it_stays_ended(client, patch_jwks, make_token, new_account):
    assert client.post("/dashboard/tour/skip", headers=_h(make_token)).json()["finished"] is True
    assert client.get("/dashboard/tour", headers=_h(make_token)).json()["finished"] is True
    assert _advance(client, make_token, "upload").json()["finished"] is True


def test_unknown_step_rejected(client, patch_jwks, make_token, new_account):
    assert _advance(client, make_token, "bogus").status_code == 400
