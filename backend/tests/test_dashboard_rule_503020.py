"""GET /dashboard/rule-503020: Needs/Wants/Savings breakdown vs income-derived
50/30/20 targets."""
from datetime import datetime, timezone

USER_A = "user-a-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _seed_category(fake_db, user_id, name):
    cat_id = f"cat-{name}"
    fake_db.seed("categories", [{"id": cat_id, "user_id": user_id, "name": name}])
    return cat_id


def _seed_spend(fake_db, user_id, category_name, amount):
    cat_id = f"cat-{category_name}"
    fake_db.seed("transactions", [{
        "id": f"txn-{category_name}",
        "user_id": user_id,
        "category_id": cat_id,
        "amount": amount,
        "timestamp": _now_iso(),
        "needs_review": False,
    }])


def test_buckets_categorized_spend_into_needs_wants_savings(client, patch_jwks, make_token, fake_db):
    fake_db.seed("profiles", [{"id": USER_A, "monthly_income": 10000}])
    _seed_category(fake_db, USER_A, "Groceries")
    _seed_category(fake_db, USER_A, "Eating Out")
    _seed_category(fake_db, USER_A, "Investments")
    _seed_spend(fake_db, USER_A, "Groceries", 2000)
    _seed_spend(fake_db, USER_A, "Eating Out", 1000)
    _seed_spend(fake_db, USER_A, "Investments", 500)

    response = client.get("/dashboard/rule-503020", headers=_headers(make_token))

    assert response.status_code == 200
    data = response.json()
    assert data["income"] == 10000
    assert data["buckets"]["needs"]["spent"] == 2000
    assert data["buckets"]["needs"]["target_amount"] == 5000
    assert data["buckets"]["wants"]["spent"] == 1000
    assert data["buckets"]["wants"]["target_amount"] == 3000
    # Savings = 500 (Investments) + unspent income (10000 - 3500 = 6500)
    assert data["buckets"]["savings"]["spent"] == 7000
    assert data["buckets"]["savings"]["target_amount"] == 2000
    savings_cats = {c["category"]: c["amount"] for c in data["buckets"]["savings"]["categories"]}
    assert savings_cats["Investments"] == 500
    assert savings_cats["Unspent income"] == 6500


def test_no_income_returns_null_targets_not_error(client, patch_jwks, make_token, fake_db):
    fake_db.seed("profiles", [{"id": USER_A, "monthly_income": 0}])
    _seed_category(fake_db, USER_A, "Groceries")
    _seed_spend(fake_db, USER_A, "Groceries", 500)

    response = client.get("/dashboard/rule-503020", headers=_headers(make_token))

    assert response.status_code == 200
    data = response.json()
    assert data["income"] == 0
    assert data["buckets"]["needs"]["target_amount"] is None
    assert data["buckets"]["needs"]["spent"] == 500
    # No income means no "unspent income" contribution to savings.
    assert data["buckets"]["savings"]["spent"] == 0


def test_overspending_beyond_income_floors_unspent_at_zero(client, patch_jwks, make_token, fake_db):
    fake_db.seed("profiles", [{"id": USER_A, "monthly_income": 1000}])
    _seed_category(fake_db, USER_A, "Shopping")
    _seed_spend(fake_db, USER_A, "Shopping", 5000)

    response = client.get("/dashboard/rule-503020", headers=_headers(make_token))

    assert response.status_code == 200
    data = response.json()
    assert data["buckets"]["savings"]["spent"] == 0
    assert data["buckets"]["savings"]["categories"] == []
