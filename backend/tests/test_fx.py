"""backend/fx.py: rate lookups, cache reads, background backfill/refresh,
/fx/currencies and the /health/deep refresh hook (contract API_V5 §2, §3.1).

Every test runs with the network disabled (`no_network`): fx's request-path
functions must never need it, and background fetches are mocked.
"""
import asyncio
import threading
import time
from datetime import date, datetime, timedelta, timezone

import httpx
import pytest

import fx
from fake_supabase import FakeSupabaseClient

TODAY = date(2026, 10, 8)  # a Thursday


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Any real outbound HTTP (httpx's network transports) fails the test.
    TestClient and httpx.MockTransport don't go through these."""
    calls = []

    def _sync(self, request):
        calls.append(str(request.url))
        raise AssertionError(f"outbound HTTP attempted: {request.url}")

    async def _async(self, request):
        calls.append(str(request.url))
        raise AssertionError(f"outbound HTTP attempted: {request.url}")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _sync)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", _async)
    return calls


@pytest.fixture
def fxdb(monkeypatch):
    """fx wired to an in-memory DB, a fixed 'today', clean throttle state,
    and background jobs recorded instead of started."""
    fake = FakeSupabaseClient()
    monkeypatch.setattr(fx, "supabase_client", fake)
    monkeypatch.setattr(fx, "_new_client", lambda: fake)
    monkeypatch.setattr(fx, "_today", lambda: TODAY)
    fx._reset_state()
    yield fake
    fx._reset_state()


@pytest.fixture
def spawned(monkeypatch):
    """Record background jobs instead of starting threads."""
    jobs = []
    monkeypatch.setattr(fx, "_spawn", lambda target, *args, name="fx": jobs.append((target, args)))
    return jobs


@pytest.fixture
def inline(monkeypatch):
    """Run background jobs synchronously on the calling thread."""
    monkeypatch.setattr(fx, "_spawn", lambda target, *args, name="fx": target(*args))


@pytest.fixture
def fetches(monkeypatch):
    """Mock Frankfurter: returns one rate per weekday in the requested range."""
    calls = []

    def _fetch(quote, start, end):
        calls.append((quote, start, end))
        out, d = {}, start
        while d <= end:
            if d.weekday() < 5:
                out[d] = 0.14
            d += timedelta(days=1)
        return out

    monkeypatch.setattr(fx, "_fetch_series", _fetch)
    return calls


def _d(s):
    return date.fromisoformat(s)


def _seed_rates(fake, quote, start, end, rate=0.14, weekdays_only=True):
    rows, d = [], _d(start)
    while d <= _d(end):
        if not weekdays_only or d.weekday() < 5:
            rows.append({"quote": quote, "rate_date": d.isoformat(), "rate": rate,
                         "fetched_at": "2026-01-01T00:00:00+00:00"})
        d += timedelta(days=1)
    fake.seed("fx_rates", rows)


def _wait_idle(timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with fx._lock:
            if not fx._running and not fx._scan_running:
                return True
        time.sleep(0.01)
    return False


# ---------------------------------------------------------------------------
# row_date
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ts, expected", [
    ("2026-09-30T23:30:00+00:00", "2026-09-30"),
    ("2026-09-30T23:30:00Z", "2026-09-30"),
    ("2026-09-30T23:30:00.123456+00:00", "2026-09-30"),
    ("2026-09-30 23:59:59.12345+00", "2026-09-30"),   # Postgres text form
    ("2026-09-30T23:30:00", "2026-09-30"),             # naive = already UTC
    ("2026-10-01T03:00:00+08:00", "2026-09-30"),       # normalised to UTC
    ("2026-09-30", "2026-09-30"),
])
def test_row_date_strings(ts, expected):
    assert fx.row_date(ts) == _d(expected)


def test_row_date_datetimes():
    assert fx.row_date(datetime(2026, 9, 30, 23, 30, tzinfo=timezone.utc)) == _d("2026-09-30")
    assert fx.row_date(datetime(2026, 9, 30, 23, 30)) == _d("2026-09-30")
    tz8 = timezone(timedelta(hours=8))
    assert fx.row_date(datetime(2026, 10, 1, 3, 0, tzinfo=tz8)) == _d("2026-09-30")
    assert fx.row_date(_d("2026-09-30")) == _d("2026-09-30")


# ---------------------------------------------------------------------------
# RateTable
# ---------------------------------------------------------------------------

def _table():
    # Thu 10-01, Fri 10-02, (weekend), Mon 10-05; then a long gap to 10-20.
    return fx.RateTable({"2026-10-01": 0.10, "2026-10-02": 0.11,
                         _d("2026-10-05"): 0.12, "2026-10-20": 0.13})


def test_strict_exact_and_weekend_gap():
    t = _table()
    assert t.strict(_d("2026-10-02")) == 0.11
    assert t.strict(_d("2026-10-03")) == 0.11  # Saturday → Friday's rate
    assert t.strict(_d("2026-10-04")) == 0.11  # Sunday
    assert t.strict(_d("2026-10-05")) == 0.12


def test_strict_seven_day_limit():
    t = _table()
    assert t.strict(_d("2026-10-12")) == 0.12   # exactly 7 days after 10-05
    assert t.strict(_d("2026-10-13")) is None   # 8 days → no rate
    assert t.strict(_d("2026-10-20")) == 0.13


def test_strict_before_cache_and_empty():
    assert _table().strict(_d("2026-09-30")) is None
    assert fx.RateTable().strict(_d("2026-10-01")) is None
    assert fx.RateTable([]).strict(_d("2026-10-01")) is None


def test_lenient():
    t = _table()
    assert t.lenient(_d("2026-10-03")) == (0.11, False)  # strict works → not approx
    assert t.lenient(_d("2026-10-15")) == (0.12, True)   # 10 days old: no age limit
    assert t.lenient(_d("2026-01-01")) == (0.10, True)   # before cache → earliest
    assert t.lenient(_d("2026-12-31")) == (0.13, True)
    assert fx.RateTable().lenient(_d("2026-10-01")) == (None, False)


def test_latest():
    t = _table()
    assert t.latest(_d("2026-10-08")) == (_d("2026-10-05"), 0.12)
    assert t.latest(_d("2026-10-20")) == (_d("2026-10-20"), 0.13)
    assert t.latest(_d("2026-09-01")) == (None, None)
    assert fx.RateTable().latest(_d("2026-10-01")) == (None, None)


def test_rate_table_accepts_row_dicts_and_numeric_strings():
    t = fx.RateTable([{"rate_date": "2026-10-01", "rate": "0.13870000"},
                      {"rate_date": "2026-10-01", "rate": 0.1387}])
    assert len(t) == 1 and t.strict(_d("2026-10-01")) == pytest.approx(0.1387)


def test_supported_list():
    assert len(fx.SUPPORTED) == 29
    assert list(fx.SUPPORTED)[:3] == ["USD", "EUR", "GBP"]
    assert "BGN" not in fx.SUPPORTED and "CNY" not in fx.SUPPORTED
    assert fx.SUPPORTED["ISK"] == "Icelandic Krona"


# ---------------------------------------------------------------------------
# load_rates / get_home_currency (request path: DB only)
# ---------------------------------------------------------------------------

def _record_queries(fake, monkeypatch):
    builders = []
    real_table = fake.table

    def table(name):
        qb = real_table(name)
        builders.append((name, qb))
        return qb

    monkeypatch.setattr(fake, "table", table)
    return builders


def test_load_rates_one_range_read_plus_two_boundary_reads(fxdb, monkeypatch, no_network):
    _seed_rates(fxdb, "USD", "2026-01-05", "2026-01-09", rate=0.10)   # far before the window
    _seed_rates(fxdb, "USD", "2026-08-03", "2026-08-07", rate=0.12)   # nearest before window
    _seed_rates(fxdb, "USD", "2026-09-24", "2026-10-07", rate=0.14)   # window
    _seed_rates(fxdb, "EUR", "2026-09-01", "2026-10-07", rate=0.5)    # other quote
    builders = _record_queries(fxdb, monkeypatch)

    table = asyncio.run(fx.load_rates("usd", _d("2026-10-01"), _d("2026-10-07")))

    assert [name for name, _ in builders] == ["fx_rates"] * 3
    range_reads = [qb for _, qb in builders
                   if {k for k, _, _ in qb._filters} >= {"gte", "lte"}]
    assert len(range_reads) == 1
    assert ("gte", "rate_date", "2026-09-24") in range_reads[0]._filters
    assert ("lte", "rate_date", "2026-10-07") in range_reads[0]._filters
    assert all(("eq", "quote", "USD") in qb._filters for _, qb in builders)

    # window rows + the nearest earlier row (08-07) + the earliest row (01-05)
    assert table.strict(_d("2026-10-03")) == 0.14
    assert table.lenient(_d("2026-09-10")) == (0.12, True)
    assert table.lenient(_d("2025-12-01")) == (0.10, True)
    assert len(table) == 10 + 2  # 10 window weekdays (09-24..10-07) + 2 boundary rows
    assert no_network == []


def test_load_rates_empty_cache(fxdb):
    table = asyncio.run(fx.load_rates("JPY", _d("2026-10-01"), _d("2026-10-07")))
    assert len(table) == 0
    assert table.lenient(_d("2026-10-01")) == (None, False)


def test_get_home_currency(fxdb):
    fxdb.seed("profiles", [{"id": "u1", "home_currency": "USD"}, {"id": "u2", "home_currency": None}])
    assert asyncio.run(fx.get_home_currency("u1")) == "USD"
    assert asyncio.run(fx.get_home_currency("u2")) is None
    assert asyncio.run(fx.get_home_currency("nobody")) is None


# ---------------------------------------------------------------------------
# missing ranges / backfill
# ---------------------------------------------------------------------------

def test_missing_ranges():
    mr = fx.missing_ranges
    s, e = _d("2026-01-01"), TODAY
    # nothing stored
    assert mr(s, e, None, None, TODAY) == [(s, e)]
    # fresh (yesterday) and start covered → nothing
    assert mr(s, e, _d("2025-12-31"), TODAY - timedelta(days=1), TODAY) == []
    # start covered within the weekend/holiday slack
    assert mr(_d("2026-01-01"), e, _d("2026-01-05"), TODAY, TODAY) == []
    # head missing
    assert mr(s, e, _d("2026-06-01"), TODAY, TODAY) == [(s, _d("2026-05-31"))]
    # tail stale (2 days)
    assert mr(s, e, s, TODAY - timedelta(days=2), TODAY) == [(TODAY - timedelta(days=1), TODAY)]
    # age-only check ignores the head
    assert mr(s, e, _d("2026-06-01"), TODAY, TODAY, check_start=False) == []
    # end clipped to today; future-only request → nothing
    assert mr(TODAY + timedelta(days=3), TODAY + timedelta(days=9), None, None, TODAY) == []


def test_backfill_fetches_only_missing_head(fxdb, fetches):
    _seed_rates(fxdb, "USD", "2026-06-01", "2026-10-07")
    written = fx.backfill("USD", _d("2026-01-01"))
    assert fetches == [("USD", _d("2026-01-01"), _d("2026-05-31"))]
    assert written > 0
    stored = {r["rate_date"] for r in fxdb._tables["fx_rates"].rows}
    assert "2026-01-02" in stored and "2026-10-07" in stored


def test_backfill_fetches_only_stale_tail(fxdb, fetches):
    _seed_rates(fxdb, "USD", "2026-06-01", "2026-10-02")  # Friday; 6 days old
    fx.backfill("USD", _d("2026-06-01"))
    assert fetches == [("USD", _d("2026-10-03"), TODAY)]


def test_backfill_skips_network_when_fresh_and_covered(fxdb, fetches):
    _seed_rates(fxdb, "USD", "2026-06-01", "2026-10-07")
    assert fx.backfill("USD", _d("2026-06-01")) == 0
    assert fx.backfill("USD", _d("2026-07-01"), _d("2026-08-01")) == 0
    assert fetches == []


def test_backfill_empty_cache_one_call(fxdb, fetches):
    fx.backfill("EUR", _d("2025-09-03"))
    assert fetches == [("EUR", _d("2025-09-03"), TODAY)]


def test_backfill_ignores_unsupported_quote(fxdb, fetches):
    assert fx.backfill("BGN", _d("2026-01-01")) == 0
    assert fetches == []


def test_upsert_in_chunks_and_idempotent(fxdb, monkeypatch):
    monkeypatch.setattr(fx, "UPSERT_CHUNK", 2)
    calls = []
    real_table = fxdb.table

    def table(name):
        qb = real_table(name)
        real_upsert = qb.upsert

        def upsert(data, on_conflict=None, ignore_duplicates=False):
            calls.append((len(data), on_conflict))
            return real_upsert(data, on_conflict=on_conflict, ignore_duplicates=ignore_duplicates)

        qb.upsert = upsert
        return qb

    monkeypatch.setattr(fxdb, "table", table)
    rates = {_d("2026-10-01"): 0.1, _d("2026-10-02"): 0.2, _d("2026-10-05"): 0.3}
    assert fx._upsert_rates(fxdb, "USD", rates) == 3
    assert calls == [(2, "quote,rate_date"), (1, "quote,rate_date")]
    fx._upsert_rates(fxdb, "USD", {_d("2026-10-01"): 0.15})
    rows = fxdb._tables["fx_rates"].rows
    assert len(rows) == 3
    assert next(r for r in rows if r["rate_date"] == "2026-10-01")["rate"] == 0.15


# ---------------------------------------------------------------------------
# Frankfurter HTTP (mocked transport)
# ---------------------------------------------------------------------------

SAMPLE_DEV = {"amount": 1.0, "base": "CNY", "start_date": "2026-09-28", "end_date": "2026-10-02",
              "rates": {"2026-09-28": {"USD": 0.14902}, "2026-09-29": {"USD": 0.14918},
                        "2026-09-30": {"USD": 0.14915}, "2026-10-01": {"USD": 0.14915},
                        "2026-10-02": {"USD": 0.14915}}}


_REAL_HTTPX_CLIENT = httpx.Client


def _mock_http(monkeypatch, handler):
    real_client = _REAL_HTTPX_CLIENT
    seen = {}

    def factory(**kwargs):
        seen.update(kwargs)
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(fx.httpx, "Client", factory)
    return seen


def test_fetch_series_dev_host(monkeypatch):
    urls = []

    def handler(request):
        urls.append(str(request.url))
        return httpx.Response(200, json=SAMPLE_DEV)

    monkeypatch.delenv("FX_API_BASE", raising=False)
    seen = _mock_http(monkeypatch, handler)
    rates = fx._fetch_series("USD", _d("2026-09-28"), _d("2026-10-02"))
    assert urls == ["https://api.frankfurter.dev/v1/2026-09-28..2026-10-02?base=CNY&symbols=USD"]
    assert rates[_d("2026-09-29")] == 0.14918 and len(rates) == 5
    assert seen["timeout"] == fx.HTTP_TIMEOUT_SECONDS


def test_fetch_series_falls_back_to_app_host(monkeypatch):
    urls = []

    def handler(request):
        urls.append(str(request.url))
        if "frankfurter.dev" in request.url.host:
            return httpx.Response(503)
        return httpx.Response(200, json=SAMPLE_DEV)

    monkeypatch.delenv("FX_API_BASE", raising=False)
    _mock_http(monkeypatch, handler)
    rates = fx._fetch_series("USD", _d("2026-09-28"), _d("2026-10-02"))
    assert urls[1] == "https://api.frankfurter.app/2026-09-28..2026-10-02?from=CNY&to=USD"
    assert len(rates) == 5


def test_fetch_series_env_host_404_and_failure(monkeypatch):
    monkeypatch.setenv("FX_API_BASE", "https://fx.example.test/v1/")
    urls = []
    _mock_http(monkeypatch, lambda r: urls.append(str(r.url)) or httpx.Response(404, json={"message": "not found"}))
    assert fx._fetch_series("USD", _d("2026-10-12"), _d("2026-10-20")) == {}
    assert urls == ["https://fx.example.test/v1/2026-10-12..2026-10-20?base=CNY&symbols=USD"]

    def boom(request):
        raise httpx.ConnectTimeout("timed out")

    _mock_http(monkeypatch, boom)
    with pytest.raises(RuntimeError):
        fx._fetch_series("USD", _d("2026-10-01"), _d("2026-10-02"))


def test_parse_series_shapes():
    assert fx._parse_series(SAMPLE_DEV, "USD")[_d("2026-10-02")] == 0.14915
    flat = [{"date": "2026-10-01", "base": "CNY", "quote": "USD", "rate": 0.1},
            {"date": "2026-10-01", "base": "CNY", "quote": "EUR", "rate": 0.2},
            {"date": "2026-10-02", "base": "CNY", "quote": "USD", "rate": -1}]
    assert fx._parse_series(flat, "USD") == {_d("2026-10-01"): 0.1}
    with pytest.raises(ValueError):
        fx._parse_series({"base": "EUR", "rates": {}}, "USD")


# ---------------------------------------------------------------------------
# triggers: coalescing, never raising, per-user start, health throttle
# ---------------------------------------------------------------------------

def test_request_backfill_coalesces_per_quote(fxdb, spawned, monkeypatch):
    runs = []
    monkeypatch.setattr(fx, "backfill", lambda q, s, e=None, client=None, check_start=True: runs.append((q, s, e)))
    fx.request_backfill("USD", _d("2026-05-01"))
    fx.request_backfill("usd", _d("2026-03-01"))
    fx.request_backfill("USD", _d("2026-04-01"), _d("2026-09-01"))
    fx.request_backfill("EUR", _d("2026-05-01"))
    assert len(spawned) == 2  # one worker per quote

    target, args = spawned[0]
    target(*args)
    # the three USD requests merged into one run: earliest start, open end
    assert runs == [("USD", _d("2026-03-01"), None)]
    assert "USD" not in fx._running and "USD" not in fx._pending


def test_request_arriving_mid_run_makes_worker_loop(fxdb, spawned, monkeypatch):
    runs = []

    def fake_backfill(q, s, e=None, client=None, check_start=True):
        runs.append(s)
        if len(runs) == 1:
            fx.request_backfill("USD", _d("2025-01-01"))  # arrives while running

    monkeypatch.setattr(fx, "backfill", fake_backfill)
    fx.request_backfill("USD", _d("2026-05-01"))
    target, args = spawned[0]
    target(*args)
    assert runs == [_d("2026-05-01"), _d("2025-01-01")]
    assert len(spawned) == 1


def test_concurrent_requests_fetch_once_with_real_threads(fxdb, monkeypatch):
    release = threading.Event()
    calls = []

    def slow_fetch(quote, start, end):
        calls.append((quote, start, end))
        release.wait(5)
        return {start + timedelta(days=i): 0.14 for i in range((end - start).days + 1)}

    monkeypatch.setattr(fx, "_fetch_series", slow_fetch)
    for _ in range(5):
        fx.request_backfill("USD", _d("2026-09-01"))
    time.sleep(0.05)
    release.set()
    assert _wait_idle()
    # one fetch; the merged follow-up run finds the range already covered
    assert len(calls) == 1


def test_worker_failure_is_swallowed_and_state_cleared(fxdb, inline, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("frankfurter down")

    monkeypatch.setattr(fx, "_fetch_series", boom)
    fx.request_backfill("USD", _d("2026-09-01"))  # must not raise
    assert not fx._running and not fx._pending
    assert "fx_rates" not in fxdb._tables or fxdb._tables["fx_rates"].rows == []


def test_triggers_never_raise_when_spawn_fails(fxdb, monkeypatch):
    def broken(*a, **k):
        raise RuntimeError("can't start new thread")

    monkeypatch.setattr(fx, "_spawn", broken)
    fx.request_backfill("USD", _d("2026-09-01"))
    fx.request_backfill_for_user("u1")
    fx.maybe_refresh_all()
    assert not fx._running and not fx._scan_running


def test_backfill_for_user_starts_7_days_before_first_row(fxdb, inline, monkeypatch):
    runs = []
    monkeypatch.setattr(fx, "backfill", lambda q, s, e=None, client=None, check_start=True: runs.append((q, s)))
    fxdb.seed("profiles", [{"id": "u1", "home_currency": "EUR"}])
    fxdb.seed("transactions", [
        {"id": "t2", "user_id": "u1", "timestamp": "2026-03-10T09:00:00+00:00"},
        {"id": "t1", "user_id": "u1", "timestamp": "2026-02-20T23:30:00+00:00"},
        {"id": "tx", "user_id": "other", "timestamp": "2020-01-01T00:00:00+00:00"},
    ])
    fx.request_backfill_for_user("u1")
    assert runs == [("EUR", _d("2026-02-13"))]


def test_backfill_for_user_without_rows_uses_400_days(fxdb, inline, monkeypatch):
    runs = []
    monkeypatch.setattr(fx, "backfill", lambda q, s, e=None, client=None, check_start=True: runs.append((q, s)))
    fxdb.seed("profiles", [{"id": "u1", "home_currency": "GBP"}])
    fx.request_backfill_for_user("u1")
    assert runs == [("GBP", TODAY - timedelta(days=400))]
    runs.clear()
    fx.request_backfill_for_user("u1", start=_d("2026-07-01"))
    assert runs == [("GBP", _d("2026-07-01"))]


def test_backfill_for_user_without_home_currency_is_noop(fxdb, inline, monkeypatch):
    runs = []
    monkeypatch.setattr(fx, "backfill", lambda *a, **k: runs.append(a))
    fxdb.seed("profiles", [{"id": "u1", "home_currency": None}])
    fx.request_backfill_for_user("u1")
    fx.request_backfill_for_user("missing-user")
    assert runs == []


def test_maybe_refresh_all_throttles_per_currency(fxdb, inline, monkeypatch):
    runs = []
    monkeypatch.setattr(fx, "backfill", lambda q, s, e=None, client=None, check_start=True: runs.append((q, check_start)))
    clock = [1000.0]
    monkeypatch.setattr(fx, "_clock", lambda: clock[0])
    fxdb.seed("profiles", [
        {"id": "a", "home_currency": "USD"}, {"id": "b", "home_currency": "EUR"},
        {"id": "c", "home_currency": "USD"}, {"id": "d", "home_currency": None},
    ])
    fx.maybe_refresh_all()
    assert sorted(runs) == [("EUR", False), ("USD", False)]  # age-only checks

    runs.clear()
    clock[0] += 5 * 3600
    fx.maybe_refresh_all()
    assert runs == []                     # within 6 h

    fxdb.seed("profiles", [{"id": "e", "home_currency": "JPY"}])
    fx.maybe_refresh_all()
    assert runs == [("JPY", False)]       # a new currency isn't throttled by others

    runs.clear()
    clock[0] += 3600 + 1
    fx.maybe_refresh_all()
    assert sorted(runs) == [("EUR", False), ("USD", False)]


def test_refresh_all_age_check_only(fxdb, inline, fetches):
    fxdb.seed("profiles", [{"id": "a", "home_currency": "USD"}])
    _seed_rates(fxdb, "USD", "2026-09-01", "2026-10-07")  # fresh; head "missing" but ignored
    fx.maybe_refresh_all()
    assert fetches == []
    fx._reset_state()
    fxdb._tables["fx_rates"].rows = [r for r in fxdb._tables["fx_rates"].rows if r["rate_date"] <= "2026-10-01"]
    fx.maybe_refresh_all()
    assert fetches == [("USD", _d("2026-10-02"), TODAY)]


def test_refresh_all_scan_is_single_flight(fxdb, spawned):
    fx.maybe_refresh_all()
    fx.maybe_refresh_all()
    assert len(spawned) == 1


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------

def _auth(make_token, sub="user-a"):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def test_fx_currencies_shape(client, patch_jwks, make_token, no_network):
    r = client.get("/fx/currencies", headers=_auth(make_token))
    assert r.status_code == 200
    body = r.json()
    assert body["base"] == "CNY"
    assert body["source"] == "European Central Bank via Frankfurter"
    assert body["supported"][0] == {"code": "USD", "name": "US Dollar"}
    assert [c["code"] for c in body["supported"]] == list(fx.SUPPORTED)
    assert len(body["supported"]) == 29
    assert no_network == []


def test_fx_currencies_requires_auth(client):
    assert client.get("/fx/currencies").status_code == 401


def test_get_paths_make_no_outbound_http_and_start_no_jobs(
        client, patch_jwks, make_token, fake_db, fxdb, spawned, no_network, monkeypatch):
    import routes.settings as settings_module
    monkeypatch.setattr(settings_module, "supabase_client", fxdb)
    fxdb.seed("profiles", [{"id": "user-a", "home_currency": "USD", "monthly_income": 0}])
    _seed_rates(fxdb, "USD", "2025-01-01", "2025-02-01")  # stale cache: still no fetch on GET

    for path in ("/settings/profile", "/fx/currencies"):
        r = client.get(path, headers=_auth(make_token))
        assert r.status_code == 200, path
    assert no_network == []
    assert spawned == []


def test_deep_health_unchanged_when_refresh_raises(client, fake_db, monkeypatch):
    def boom():
        raise RuntimeError("refresh exploded")

    monkeypatch.setattr(fx, "maybe_refresh_all", boom)
    r = client.get("/health/deep")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": True}


def test_deep_health_returns_quickly_while_refresh_is_slow(client, fake_db, fxdb, monkeypatch):
    release = threading.Event()
    started = threading.Event()

    def slow_fetch(quote, start, end):
        started.set()
        release.wait(5)
        raise httpx.ConnectTimeout("frankfurter unreachable")

    monkeypatch.setattr(fx, "_fetch_series", slow_fetch)
    fxdb.seed("profiles", [{"id": "a", "home_currency": "USD"}])
    try:
        t0 = time.monotonic()
        r = client.get("/health/deep")
        elapsed = time.monotonic() - t0
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "db": True}
        assert elapsed < 1.0
        assert started.wait(2)  # the refresh really ran, in the background
    finally:
        release.set()
        assert _wait_idle()
