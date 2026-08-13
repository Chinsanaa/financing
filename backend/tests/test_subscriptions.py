"""Subscription detection route: /subscriptions runs detection over the
user's transactions, upserts recurring_merchants, and confirm/dismiss update
that user's own rows only."""

USER_A = "user-a-id"
USER_B = "user-b-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def _monthly_rows(merchant, amount, months=6, category_id=None, user_id=USER_A):
    return [
        {
            "merchant": merchant,
            "amount": amount,
            "timestamp": f"2026-{(2 + i):02d}-15T00:00:00",
            "category_id": category_id,
            "user_id": user_id,
        }
        for i in range(months)
    ]


def test_list_subscriptions_detects_and_returns_recurring_merchant(client, patch_jwks, make_token, fake_db):
    fake_db.seed("transactions", _monthly_rows("Netflix", 39.9))

    response = client.get("/subscriptions/", headers=_headers(make_token))

    assert response.status_code == 200
    body = response.json()
    assert len(body["subscriptions"]) == 1
    assert body["subscriptions"][0]["merchant"] == "Netflix"
    assert body["subscriptions"][0]["cadence"] == "monthly"
    assert body["monthly_total"] == 39.9


def test_list_subscriptions_only_sees_own_transactions(client, patch_jwks, make_token, fake_db):
    fake_db.seed("transactions", _monthly_rows("Netflix", 39.9, user_id=USER_B))

    response = client.get("/subscriptions/", headers=_headers(make_token, sub=USER_A))

    assert response.status_code == 200
    assert response.json()["subscriptions"] == []


def test_confirm_subscription_sets_flag_for_owner_only(client, patch_jwks, make_token, fake_db):
    fake_db.seed("recurring_merchants", [
        {"id": "rm-1", "user_id": USER_A, "merchant": "Netflix", "cadence": "monthly",
         "typical_amount": 39.9, "is_confirmed": False, "is_dismissed": False},
    ])

    response = client.post("/subscriptions/rm-1/confirm", headers=_headers(make_token, sub=USER_A))
    assert response.status_code == 200
    assert response.json()["subscription"]["is_confirmed"] is True

    other_response = client.post("/subscriptions/rm-1/confirm", headers=_headers(make_token, sub=USER_B))
    assert other_response.status_code == 404


def test_dismiss_subscription_excludes_it_from_next_list_call(client, patch_jwks, make_token, fake_db):
    fake_db.seed("transactions", _monthly_rows("Netflix", 39.9))
    fake_db.seed("recurring_merchants", [
        {"id": "rm-1", "user_id": USER_A, "merchant": "Netflix", "cadence": "monthly",
         "typical_amount": 39.9, "is_confirmed": False, "is_dismissed": False},
    ])

    dismiss = client.post("/subscriptions/rm-1/dismiss", headers=_headers(make_token))
    assert dismiss.status_code == 200

    listing = client.get("/subscriptions/", headers=_headers(make_token))
    assert listing.json()["subscriptions"] == []
