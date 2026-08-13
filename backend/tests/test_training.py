"""Tests for POST /training/retrain's pre-check on labeled sample count.

retrain_model() (src/retrain.py) has always required >= 5 labeled samples,
but the old trigger_retrain() spawned the background task and returned 200
"Training started" regardless, so a first-time user with too few labels only
found out via polling model_runs.error_message. This suite pins the new
behavior: reject before creating a model_runs row or touching the background
task at all.
"""
USER_A = "user-a-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def _seed_labeled(fake_db, user_id: str, n: int):
    cat_id = "cat-1"
    fake_db.seed("categories", [{"id": cat_id, "user_id": user_id, "name": "Eating Out"}])
    fake_db.seed("transactions", [
        {
            "id": f"txn-{i}",
            "user_id": user_id,
            "category_id": cat_id,
            "categories": {"name": "Eating Out"},
            "is_manually_labeled": True,
        }
        for i in range(n)
    ])


def test_too_few_labeled_samples_returns_400_before_any_run_created(
    client, patch_jwks, make_token, fake_db
):
    _seed_labeled(fake_db, USER_A, 3)

    resp = client.post("/training/retrain", headers=_headers(make_token))

    assert resp.status_code == 400
    assert "5" in resp.json()["detail"]
    assert fake_db._tables.get("model_runs") is None or fake_db._tables["model_runs"].rows == []


def test_zero_labeled_samples_returns_400(client, patch_jwks, make_token, fake_db):
    resp = client.post("/training/retrain", headers=_headers(make_token))

    assert resp.status_code == 400
    assert fake_db._tables.get("model_runs") is None or fake_db._tables["model_runs"].rows == []
