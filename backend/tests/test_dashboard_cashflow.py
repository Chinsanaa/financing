"""API v5 transaction kinds: income/transfer rows must never change a spend
number, and GET /dashboard/cashflow (plus the home-currency fields) reports
them per contract §3.3-3.7.

Dates are relative to the real `_now_cn()` clock so nothing ages."""
from datetime import date, timedelta

from routes.dashboard import _now_cn, _month_start

USER_A = "user-a-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def _month(months_back: int) -> str:
    start = _month_start(_now_cn())
    total = start.year * 12 + (start.month - 1) - months_back
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def _ts(months_back: int, day: int = 3, hour: int = 10) -> str:
    return f"{_month(months_back)}-{day:02d}T{hour:02d}:00:00+00:00"


def _txn(tid, months_back, amount, category=None, day=3, **extra):
    row = {
        "id": tid, "user_id": USER_A, "merchant": extra.pop("merchant", f"Shop {tid}"),
        "description": "", "amount": amount, "timestamp": _ts(months_back, day),
        "category_id": f"cat-{category}" if category else None,
        "categories": {"name": category} if category else None,
        "needs_review": False, "is_manually_labeled": False, "is_split": False,
        "label_source": "rule" if category else "none", "confidence": None, "source": "alipay",
    }
    row.update(extra)
    return row


def _seed_expenses(fake_db):
    for name in ("Groceries", "Eating Out", "Investments", "Entertainment"):
        fake_db.seed("categories", [{"id": f"cat-{name}", "user_id": USER_A, "name": name}])
    fake_db.seed("profiles", [{"id": USER_A, "monthly_income": 8000}])
    fake_db.seed("budget_category_config", [
        {"id": "b1", "user_id": USER_A, "category_id": "cat-Groceries", "categories": {"name": "Groceries"},
         "monthly_budget": 500, "type": "Need"},
        {"id": "b2", "user_id": USER_A, "category_id": "cat-Eating Out", "categories": {"name": "Eating Out"},
         "monthly_budget": 100, "type": "Want"},
    ])
    rows = []
    for m in range(0, 4):  # this month + 3 prior months
        rows += [
            _txn(f"g{m}", m, 120 + m, "Groceries"),
            _txn(f"e{m}", m, 60 + 10 * m, "Eating Out", day=5),
            _txn(f"n{m}", m, 39.9, "Entertainment", day=8, merchant="Netflix"),
        ]
    rows += [
        _txn("inv", 0, 500, "Investments", day=9),
        _txn("refund", 0, -20, "Groceries", day=10, flow_subtype="refund"),
        _txn("review", 0, 33, "Eating Out", day=11, needs_review=True, label_source="model", confidence=0.4),
        _txn("uncat", 0, 15, None, day=12, needs_review=True),
        _txn("split", 1, 90, None, day=13, is_split=True, label_source="override", is_manually_labeled=True),
        _txn("manual", 2, 12, "Groceries", day=14, is_manually_labeled=True, label_source="override"),
    ]
    fake_db.seed("transactions", rows)
    fake_db.seed("transaction_splits", [
        {"id": "s1", "user_id": USER_A, "transaction_id": "split", "category_id": "cat-Groceries", "amount": 60,
         "categories": {"name": "Groceries"}, "transactions": {"timestamp": _ts(1, 13)}},
        {"id": "s2", "user_id": USER_A, "transaction_id": "split", "category_id": "cat-Eating Out", "amount": 30,
         "categories": {"name": "Eating Out"}, "transactions": {"timestamp": _ts(1, 13)}},
    ])


def _seed_income_and_transfers(fake_db):
    rows = []
    for m in range(0, 6):  # a monthly salary would look like a "subscription"
        rows.append(_txn(f"sal{m}", m, 10000, None, day=1, merchant="Employer",
                         kind="income", flow_subtype="salary", source="bank"))
    rows += [
        _txn("int", 0, 12.5, None, day=2, kind="income", flow_subtype="interest"),
        _txn("rp_in", 0, -200, None, day=4, kind="transfer", flow_subtype="red_packet", source="wechat"),
        _txn("p2p_out", 0, 300, None, day=4, kind="transfer", flow_subtype="p2p_transfer", source="wechat"),
        _txn("aa_in", 0, -45, None, day=6, kind="transfer", flow_subtype="aa_collection"),
        _txn("null_out", 0, 70, None, day=6, kind="transfer", flow_subtype=None),
        _txn("repay", 0, 500, None, day=7, kind="transfer", flow_subtype="repayment"),
        _txn("topup", 0, -1000, None, day=7, kind="transfer", flow_subtype="top_up"),
        _txn("own", 1, 250, None, day=7, kind="transfer", flow_subtype="own_account"),
        # Deliberately inconsistent rows (a category / review flags on a
        # non-expense row): every expense-only query must still ignore them.
        _txn("bad_inc", 0, 777, "Groceries", day=9, kind="income", flow_subtype="other",
             needs_review=True, is_manually_labeled=True),
        _txn("bad_tr", 0, 888, "Eating Out", day=9, kind="transfer", needs_review=True,
             is_manually_labeled=True, merchant="Netflix"),
    ]
    fake_db.seed("transactions", rows)


EXPENSE_ONLY_ENDPOINTS = [
    "/dashboard/summary",
    "/dashboard/by-category",
    "/dashboard/trends?granularity=month&months=12",
    "/dashboard/trends?granularity=day&days=200",
    "/dashboard/budget",
    "/dashboard/rule-503020",
    "/dashboard/savings",
    "/dashboard/insights",
    "/dashboard/action",
    "/dashboard/review-queue",
    "/dashboard/review-queue?show_labeled=true",
    "/dashboard/reports?per_page=500",
    "/dashboard/reports?category_id=cat-Groceries&kind=all",
    "/subscriptions/",
]


def _snapshot(client, make_token, fake_db) -> dict:
    out = {}
    for path in EXPENSE_ONLY_ENDPOINTS:
        if path.startswith("/subscriptions"):
            # Empty the cache so detection runs inline over transactions.
            fake_db.table("recurring_merchants")  # ensure the table exists
            fake_db._tables["recurring_merchants"].rows = []
        response = client.get(path, headers=_headers(make_token))
        assert response.status_code == 200, (path, response.text)
        out[path] = response.json()
    # The month list legitimately grows (income-only months are selectable,
    # contract §3.11); everything else must be identical.
    for path in ("/dashboard/budget", "/dashboard/rule-503020"):
        out[path].pop("available_months")
    # Not spend: the row count covers every kind and month income now comes
    # from statements (asserted in test_summary_counts_and_month_income).
    for key in ("total_transactions", "month_income", "month_income_source"):
        out["/dashboard/summary"].pop(key)
    # Re-detection inserts fresh cache rows: only the generated id differs.
    # (A leaked "Netflix" transfer would change last_seen/typical_amount.)
    for sub in out["/subscriptions/"]["subscriptions"]:
        sub.pop("id", None)
    return out


def test_income_and_transfers_never_change_spend_numbers(client, patch_jwks, make_token, fake_db):
    _seed_expenses(fake_db)
    before = _snapshot(client, make_token, fake_db)
    cashflow_before = client.get("/dashboard/cashflow", headers=_headers(make_token)).json()
    all_before = client.get("/dashboard/reports?kind=all&per_page=500", headers=_headers(make_token)).json()

    _seed_income_and_transfers(fake_db)
    after = _snapshot(client, make_token, fake_db)

    for path in EXPENSE_ONLY_ENDPOINTS:
        assert after[path] == before[path], (path, before[path], after[path])
    # Sanity: the seed exercised real spend, not empty responses.
    assert before["/dashboard/summary"]["total_spend"] > 0
    assert before["/dashboard/subscriptions/".replace("/dashboard", "")]["subscriptions"]
    assert before["/dashboard/review-queue"]["count"] > 0

    # ...while cash flow and reports?kind=all do see them.
    cashflow_after = client.get("/dashboard/cashflow", headers=_headers(make_token)).json()
    assert cashflow_after != cashflow_before
    assert cashflow_after["months"][-1]["income"] > 0
    all_after = client.get("/dashboard/reports?kind=all&per_page=500", headers=_headers(make_token)).json()
    assert all_after["total_count"] == all_before["total_count"] + 16
    income_rows = client.get("/dashboard/reports?kind=income", headers=_headers(make_token)).json()
    assert income_rows["total_count"] == 8


def test_summary_counts_and_month_income(client, patch_jwks, make_token, fake_db):
    _seed_expenses(fake_db)
    body = client.get("/dashboard/summary", headers=_headers(make_token)).json()
    assert body["month"] == _month(0)
    assert body["month_income"] == 8000 and body["month_income_source"] == "settings"
    assert body["home"] is None
    expense_rows = body["total_transactions"]
    pct_before = body["labeling_percentage"]

    _seed_income_and_transfers(fake_db)
    body = client.get("/dashboard/summary", headers=_headers(make_token)).json()
    assert body["total_transactions"] == expense_rows + 16  # every kind counted
    assert body["labeling_percentage"] == pct_before         # expense rows only
    # 10000 salary + 12.5 interest + 777 (inconsistent income row) this month
    assert body["month_income"] == 10789.5
    assert body["month_income_source"] == "statements"
    month_spend = 120 + 60 + 39.9 + 500 - 20 + 33 + 15
    assert body["month_spend"] == round(month_spend, 2)


def test_summary_month_income_null_without_statements_or_settings(client, patch_jwks, make_token, fake_db):
    fake_db.seed("transactions", [_txn("t1", 0, 10, "Groceries")])
    body = client.get("/dashboard/summary", headers=_headers(make_token)).json()
    assert body["month_income"] is None and body["month_income_source"] is None


def test_cashflow_month_math(client, patch_jwks, make_token, fake_db):
    fake_db.seed("transactions", [
        _txn("exp", 0, 100, "Groceries"),
        _txn("ref", 0, -30, "Groceries", flow_subtype="refund"),
        _txn("sal", 0, 1000, None, kind="income", flow_subtype="salary"),
        _txn("rp_in", 0, -200, None, kind="transfer", flow_subtype="red_packet"),
        _txn("aa_in", 0, -45, None, kind="transfer", flow_subtype="aa_collection"),
        _txn("p2p_out", 0, 300, None, kind="transfer", flow_subtype="p2p_transfer"),
        _txn("null_out", 0, 70, None, kind="transfer", flow_subtype=None),
        _txn("repay", 0, 500, None, kind="transfer", flow_subtype="repayment"),
        _txn("topup", 0, -1000, None, kind="transfer", flow_subtype="top_up"),
        _txn("own_prev", 2, 250, None, kind="transfer", flow_subtype="own_account"),
        _txn("too_old", 5, 99999, None, kind="income"),  # outside a 3-month window
    ])

    body = client.get("/dashboard/cashflow?months=3", headers=_headers(make_token)).json()

    assert body["currency_home"] is None
    assert [m["month"] for m in body["months"]] == [_month(2), _month(1), _month(0)]
    assert body["months"][0] == {
        "month": _month(2), "spend": 0, "income": 0, "transfers_in": 0, "transfers_out": 0,
        "net": 0, "spend_home": None, "income_home": None, "net_home": None,
    }
    current = body["months"][-1]
    assert current["spend"] == 70
    assert current["income"] == 1000
    assert current["transfers_in"] == 245      # |−200| + |−45|
    assert current["transfers_out"] == 370     # 300 + NULL-subtype 70
    assert current["net"] == 930               # income − spend, transfers excluded
    assert body["own_account_moved"] == 1750   # 500 + 1000 + 250


def test_cashflow_months_clamped(client, patch_jwks, make_token, fake_db):
    assert len(client.get("/dashboard/cashflow?months=0", headers=_headers(make_token)).json()["months"]) == 1
    assert len(client.get("/dashboard/cashflow?months=99", headers=_headers(make_token)).json()["months"]) == 36
    assert len(client.get("/dashboard/cashflow", headers=_headers(make_token)).json()["months"]) == 12


# ── Home currency (fake fx module, contract §2) ───────────────────────────

def _daily_rates(start: date, end: date, rate: float) -> dict:
    out, d = {}, start
    while d <= end:
        out[d] = rate
        d += timedelta(days=1)
    return out


def test_home_fields_null_without_home_currency(client, patch_jwks, make_token, fake_db, fake_fx):
    fake_db.seed("transactions", [_txn("t1", 0, 10, "Groceries")])
    summary = client.get("/dashboard/summary", headers=_headers(make_token)).json()
    reports = client.get("/dashboard/reports", headers=_headers(make_token)).json()
    budget = client.get("/dashboard/budget", headers=_headers(make_token)).json()
    assert summary["home"] is None
    assert reports["currency_home"] is None and reports["transactions"][0]["amount_home"] is None
    assert budget["currency_home"] is None and budget["total_budget_home"] is None
    assert fake_fx.load_calls == []  # nothing loaded without a home currency


def test_home_conversion_strict_and_lenient(client, patch_jwks, make_token, fake_db, fake_fx):
    today = _now_cn().date()
    fake_fx.home[USER_A] = "USD"
    # Rates cover only the current month (plus a week before it).
    month_start = _month_start(_now_cn()).date()
    fake_fx.rates.update(_daily_rates(month_start - timedelta(days=7), today, 0.5))
    fake_db.seed("transactions", [
        _txn("now1", 0, 100, "Groceries", day=1),
        _txn("now2", 0, 50.01, "Groceries", day=1),
        _txn("sal", 0, 1000, None, day=1, kind="income", flow_subtype="salary"),
        _txn("old", 3, 40, "Groceries", day=1),   # older than every stored rate
    ])

    summary = client.get("/dashboard/summary", headers=_headers(make_token)).json()
    home = summary["home"]
    assert home["currency"] == "USD"
    assert home["month_spend_home"] == 75.0         # round(150.01 × 0.5) = 75.0
    assert home["month_income_home"] == 500.0
    assert home["total_spend_home"] == 95.0         # old row uses the earliest rate
    assert home["approx"] is True
    assert home["rate"] == 0.5 and home["rate_asof"] == today.isoformat()
    assert len(fake_fx.load_calls) == 1             # one rate read per request

    cashflow = client.get("/dashboard/cashflow?months=4", headers=_headers(make_token)).json()
    assert cashflow["currency_home"] == "USD"
    assert cashflow["months"][-1]["spend_home"] == 75.0
    assert cashflow["months"][-1]["net_home"] == 425.0
    assert cashflow["months"][0]["spend_home"] is None   # no strict rate 3 months ago
    assert cashflow["months"][0]["net_home"] is None
    assert cashflow["months"][1]["spend_home"] == 0      # zero rows → 0, not null

    trends = client.get("/dashboard/trends?granularity=month&months=6", headers=_headers(make_token)).json()
    by_month = {t["date"]: t["total_spend_home"] for t in trends["trends"]}
    assert by_month[_month(0)] == 75.0 and by_month[_month(3)] is None

    reports = client.get("/dashboard/reports?kind=all", headers=_headers(make_token)).json()
    by_id = {r["id"]: r for r in reports["transactions"]}
    assert by_id["now2"]["amount_home"] == 25.0 and by_id["old"]["amount_home"] is None
    assert by_id["sal"]["category"] == "Income" and by_id["sal"]["kind"] == "income"


def test_total_spend_home_null_when_no_rate_stored(client, patch_jwks, make_token, fake_db, fake_fx):
    fake_fx.home[USER_A] = "EUR"
    fake_db.seed("transactions", [_txn("t1", 0, 10, "Groceries")])
    home = client.get("/dashboard/summary", headers=_headers(make_token)).json()["home"]
    assert home == {"currency": "EUR", "total_spend_home": None, "month_spend_home": None,
                    "month_income_home": None, "rate_asof": None, "rate": None, "approx": False}


def test_budget_home_amounts(client, patch_jwks, make_token, fake_db, fake_fx):
    today = _now_cn().date()
    fake_fx.home[USER_A] = "USD"
    fake_fx.rates.update(_daily_rates(today - timedelta(days=60), today, 0.25))
    _seed_expenses(fake_db)

    body = client.get("/dashboard/budget", headers=_headers(make_token)).json()
    assert body["currency_home"] == "USD"
    assert body["total_budget"] == 600
    groceries = next(c for c in body["category_budgets"] if c["category"] == "Groceries")
    assert groceries["current_spend"] == 100            # 120 − 20 refund
    assert groceries["current_spend_home"] == 25.0
    assert groceries["monthly_budget_home"] == 125.0
    assert body["total_budget_home"] == 150.0
    assert body["total_spent"] == round(100 + 60 + 33, 2)
    assert body["total_spent_home"] == round((100 + 60 + 33) * 0.25, 2)


def test_budget_early_return_has_totals(client, patch_jwks, make_token, fake_db, fake_fx):
    body = client.get("/dashboard/budget", headers=_headers(make_token)).json()
    assert (body["total_budget"], body["total_spent"], body["currency_home"]) == (0, 0, None)
    assert body["total_budget_home"] is None and body["total_spent_home"] is None

    fake_fx.home[USER_A] = "USD"
    body = client.get("/dashboard/budget", headers=_headers(make_token)).json()
    assert body["currency_home"] == "USD"
    assert body["total_budget_home"] == 0 and body["total_spent_home"] == 0
