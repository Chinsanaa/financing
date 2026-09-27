"""Performance-motivated changes keep the same responses: SQL-side
aggregates (available months, trends), concurrent queries, cached
subscriptions list, gzip."""
USER_A = "user-a-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def _txn(tid, ts, amount=10, category_id="c1", **extra):
    return {"id": tid, "user_id": USER_A, "merchant": "Shop", "description": "",
            "amount": amount, "timestamp": ts, "category_id": category_id,
            "needs_review": False, "categories": None, "label_source": "none", **extra}


def test_budget_available_months_newest_first(client, patch_jwks, make_token, fake_db):
    fake_db.seed("transactions", [
        _txn("t1", "2026-03-05T00:00:00"), _txn("t2", "2026-05-01T00:00:00"),
        _txn("t3", "2026-03-20T00:00:00"),
    ])

    body = client.get("/dashboard/budget?month=2026-05", headers=_headers(make_token)).json()

    assert body["available_months"] == ["2026-05", "2026-03"]


def test_monthly_trends_bucket_and_filter(client, patch_jwks, make_token, fake_db):
    fake_db.seed("transactions", [
        _txn("t1", "2099-01-05T00:00:00", 10), _txn("t2", "2099-01-20T00:00:00", 5),
        _txn("t3", "2099-02-01T00:00:00", 7),
        _txn("t4", "2099-02-02T00:00:00", 100, category_id=None),  # uncategorized: excluded
    ])
    # Far-future rows are always >= the cutoff, so the test doesn't age.
    body = client.get("/dashboard/trends?granularity=month&months=12", headers=_headers(make_token)).json()

    assert body["trends"] == [
        {"date": "2099-01", "total_spend": 15.0},
        {"date": "2099-02", "total_spend": 7.0},
    ]


def test_summary_counts_are_totals_not_capped(client, patch_jwks, make_token, fake_db):
    fake_db.seed("transactions", [_txn(f"t{i}", "2026-03-05T00:00:00") for i in range(3)]
                 + [_txn("r1", "2026-03-05T00:00:00", needs_review=True)])
    fake_db.rpc_handlers["sum_user_transactions"] = lambda params: 40

    body = client.get("/dashboard/summary", headers=_headers(make_token)).json()

    assert body["total_transactions"] == 4
    assert body["labeled_transactions"] == 3
    assert body["total_spend"] == 40.0


def test_subscriptions_serves_cached_list_with_english_names(client, patch_jwks, make_token, fake_db):
    import routes.subscriptions as subs

    fake_db.seed("recurring_merchants", [
        {"id": "rm-1", "user_id": USER_A, "merchant": "小区健身房", "merchant_en": "Neighborhood gym",
         "cadence": "monthly", "typical_amount": 25, "is_dismissed": False, "categories": None},
    ])
    detections: list = []

    async def _no_detect(user_id):
        detections.append(user_id)

    subs._refreshing_users.clear()
    original = subs._detect_and_upsert
    subs._detect_and_upsert = _no_detect
    try:
        body = client.get("/subscriptions/", headers=_headers(make_token)).json()
    finally:
        subs._detect_and_upsert = original
        subs._refreshing_users.clear()

    assert body["subscriptions"][0]["merchant"] == "Neighborhood gym"
    assert body["monthly_total"] == 25.0


def test_large_responses_are_gzipped(client, patch_jwks, make_token, fake_db):
    fake_db.seed("transactions", [_txn(f"t{i}", "2026-03-05T00:00:00", description="x" * 40) for i in range(60)])

    response = client.get("/dashboard/reports?per_page=100", headers={
        **_headers(make_token), "Accept-Encoding": "gzip"})

    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "gzip"
