"""Stored English translations: the request path never calls Google
Translate; the background pass translates each distinct string once and
writes it to every matching row (backend/translations.py)."""
import pytest

import translations
from src import translate as translate_mod

# The autouse `translation_requests` fixture replaces request_translation with
# a recorder; keep the real one for the watchdog tests.
_real_request_translation = translations.request_translation

USER_A = "user-a-id"
USER_B = "user-b-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def _seed(fake_db, txn_id, merchant, description, user_id=USER_A, **extra):
    fake_db.seed("transactions", [{
        "id": txn_id, "user_id": user_id, "merchant": merchant, "description": description,
        "amount": 10, "timestamp": "2026-06-01T00:00:00", "category_id": None,
        "categories": None, "label_source": "none", "needs_review": True,
        "confidence": 0.5, **extra,
    }])


def _rows(fake_db, user_id=USER_A):
    return {r["id"]: r for r in fake_db.table("transactions").select("*").eq("user_id", user_id).execute().data}


@pytest.fixture
def fake_google(monkeypatch):
    """Deterministic stand-in for the live translator; counts calls."""
    calls: list = []
    table = {"楼下面馆": "Downstairs noodle shop", "午饭": "lunch", "奶茶": "milk tea"}

    def _fake(text):
        calls.append(text)
        return table.get(text, "")  # unknown text = a failed translation

    monkeypatch.setattr(translate_mod, "translate_to_english", _fake)
    translations._recent_failures.clear()
    yield calls
    translations._recent_failures.clear()


def test_reports_never_calls_translator_and_uses_stored_text(
    client, patch_jwks, make_token, fake_db, fake_google, translation_requests
):
    _seed(fake_db, "t1", "楼下面馆", "午饭", merchant_en="Downstairs noodle shop", description_en="lunch")

    response = client.get("/dashboard/reports", headers=_headers(make_token))

    assert response.status_code == 200
    row = response.json()["transactions"][0]
    assert row["merchant"] == "Downstairs noodle shop"
    assert row["description"] == "lunch"
    assert fake_google == []            # no live translation on the read path
    assert translation_requests == []   # nothing missing -> no background pass


def test_reports_untranslated_row_shows_placeholder_and_requests_pass(
    client, patch_jwks, make_token, fake_db, fake_google, translation_requests
):
    _seed(fake_db, "t1", "楼下面馆", "午饭")  # merchant_en/description_en not yet filled

    response = client.get("/dashboard/reports", headers=_headers(make_token))

    row = response.json()["transactions"][0]
    assert row["merchant"] == "Unknown merchant"  # never leaks Chinese text
    assert row["description"] == ""
    assert fake_google == []
    assert translation_requests == [USER_A]


def test_review_queue_uses_stored_text(
    client, patch_jwks, make_token, fake_db, fake_google, translation_requests
):
    _seed(fake_db, "t1", "楼下面馆", "奶茶", merchant_en="Downstairs noodle shop", description_en="milk tea")

    response = client.get("/dashboard/review-queue", headers=_headers(make_token))

    assert response.status_code == 200
    row = response.json()["transactions"][0]
    assert (row["merchant"], row["description"]) == ("Downstairs noodle shop", "milk tea")
    assert fake_google == []


def test_pass_translates_each_distinct_string_once_for_all_rows(fake_db, fake_google):
    _seed(fake_db, "t1", "楼下面馆", "午饭")
    _seed(fake_db, "t2", "楼下面馆", "午饭")
    _seed(fake_db, "t3", "Starbucks", "/")

    translations.translate_user_transactions(USER_A)

    rows = _rows(fake_db)
    assert rows["t1"]["merchant_en"] == rows["t2"]["merchant_en"] == "Downstairs noodle shop"
    assert rows["t1"]["description_en"] == "lunch"
    assert rows["t3"]["merchant_en"] == "Starbucks"  # non-CJK stored as-is, no call
    assert rows["t3"]["description_en"] == "/"
    assert sorted(fake_google) == ["午饭", "楼下面馆"]  # once each, despite 2 rows


def test_failed_translation_stays_null_and_is_backed_off(fake_db, fake_google):
    _seed(fake_db, "t1", "无名小店", "")

    translations.translate_user_transactions(USER_A)
    translations.translate_user_transactions(USER_A)  # immediate retry

    row = _rows(fake_db)["t1"]
    assert row.get("merchant_en") is None     # retried by a later pass
    assert row["description_en"] == ""
    assert fake_google == ["无名小店"]          # backoff: not re-called right away


def test_null_description_gets_filled(fake_db, fake_google):
    # A NULL source column must not leave description_en NULL forever
    # (which would re-trigger the worker on every page load).
    _seed(fake_db, "t1", "Starbucks", None)

    translations.translate_user_transactions(USER_A)

    assert _rows(fake_db)["t1"]["description_en"] == ""


def test_pass_only_touches_its_own_user(fake_db, fake_google):
    _seed(fake_db, "a1", "楼下面馆", "午饭", user_id=USER_A)
    _seed(fake_db, "b1", "楼下面馆", "午饭", user_id=USER_B)

    translations.translate_user_transactions(USER_A)

    assert _rows(fake_db, USER_A)["a1"]["merchant_en"] == "Downstairs noodle shop"
    assert _rows(fake_db, USER_B)["b1"].get("merchant_en") is None


def test_curated_name_beats_stored_translation():
    # Improving the curated map takes effect without re-translating rows.
    assert translate_mod.merchant_label_stored("麦当劳", "Mai Dang Lao") == "McDonald's"


def test_translate_to_english_does_not_cache_failures(monkeypatch):
    import sys
    import types

    results = iter([Exception("429"), "Hello"])

    class _FakeTranslator:
        def __init__(self, **kwargs):
            pass

        def translate(self, text):
            r = next(results)
            if isinstance(r, Exception):
                raise r
            return r

    monkeypatch.setitem(sys.modules, "deep_translator", types.SimpleNamespace(GoogleTranslator=_FakeTranslator))
    translate_mod._translation_cache.pop("你好", None)

    assert translate_mod.translate_to_english("你好") == ""       # failure...
    assert translate_mod.translate_to_english("你好") == "Hello"  # ...is retried, not pinned
    translate_mod._translation_cache.pop("你好", None)


def test_insights_flagged_merchant_is_english(
    client, patch_jwks, make_token, fake_db, fake_google, translation_requests
):
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    fake_db.seed("categories", [{"id": "c1", "user_id": USER_A, "name": "Eating Out"}])
    rows = [("n%d" % i, 10) for i in range(8)] + [("spike", 500)]
    for i, (tid, amount) in enumerate(rows):
        fake_db.seed("transactions", [{
            "id": tid, "user_id": USER_A, "merchant": "楼下面馆", "merchant_en": "Downstairs noodle shop",
            "description": "", "amount": amount, "category_id": "c1",
            "categories": {"name": "Eating Out"}, "is_split": False,
            "timestamp": (now - timedelta(days=i + 1)).isoformat(),
        }])

    response = client.get("/dashboard/insights", headers=_headers(make_token))

    assert response.status_code == 200
    flagged = response.json()["flagged_transactions"]
    assert flagged and all(t["merchant"] == "Downstairs noodle shop" for t in flagged)
    assert fake_google == []


# --- Hang protection (2026-09-29: a worker froze after its first fetch) ---


def test_hung_google_call_times_out(monkeypatch):
    import sys
    import threading
    import types

    release = threading.Event()

    class _HangingTranslator:
        def __init__(self, **kwargs):
            pass

        def translate(self, text):
            release.wait(5)  # "never" answers (within the test)
            return "too late"

    monkeypatch.setitem(sys.modules, "deep_translator", types.SimpleNamespace(GoogleTranslator=_HangingTranslator))
    monkeypatch.setattr(translate_mod, "GOOGLE_TIMEOUT_SECONDS", 0.2)
    translate_mod._translation_cache.pop("你好", None)
    try:
        assert translate_mod.translate_to_english("你好") == ""  # gave up, not stuck
        assert "你好" not in translate_mod._translation_cache  # failure not cached
    finally:
        release.set()


def test_non_chinese_strings_are_written_without_google(fake_db, fake_google):
    _seed(fake_db, "t1", "Starbucks", "Coffee")
    _seed(fake_db, "t2", "", None)

    written = translations.translate_user_transactions(USER_A)

    rows = _rows(fake_db)
    assert (rows["t1"]["merchant_en"], rows["t1"]["description_en"]) == ("Starbucks", "Coffee")
    assert (rows["t2"]["merchant_en"], rows["t2"]["description_en"]) == ("", "")
    assert written == 4  # merchants {"Starbucks", ""} + descriptions {"Coffee", ""}
    assert fake_google == []


def test_pass_stops_early_when_google_is_unreachable(fake_db, fake_google):
    # 6 unknown strings -> 6 failures; the breaker trips at 5 and stops the pass.
    for i in range(6):
        _seed(fake_db, f"t{i}", f"无名店{i}", "午饭")

    translations.translate_user_transactions(USER_A)

    merchant_calls = [c for c in fake_google if c.startswith("无名店")]
    assert len(merchant_calls) == translations.MAX_CONSECUTIVE_FAILURES
    assert "午饭" not in fake_google  # descriptions not attempted this pass
    assert all(r.get("merchant_en") is None for r in _rows(fake_db).values())


def test_backed_off_strings_do_not_trip_the_breaker(fake_db, fake_google):
    import time

    for i in range(6):
        _seed(fake_db, f"t{i}", f"无名店{i}", None)
        translations._recent_failures[f"无名店{i}"] = time.monotonic()
    _seed(fake_db, "t9", "楼下面馆", None)

    translations.translate_user_transactions(USER_A)

    assert _rows(fake_db)["t9"]["merchant_en"] == "Downstairs noodle shop"


@pytest.fixture
def worker_threads(monkeypatch):
    """Run request_translation for real, but with a controllable worker."""
    started: list = []
    monkeypatch.setattr(translations, "_worker", lambda user_id, gen: started.append(gen))
    for d in (translations._running_users, translations._rerun_users):
        d.clear()
    translations._heartbeat.clear()
    translations._generation.clear()
    yield started
    for d in (translations._running_users, translations._rerun_users):
        d.clear()


def test_running_worker_coalesces_requests(worker_threads):
    assert _real_request_translation(USER_A) is True
    import time; time.sleep(0.05)
    # Our fake worker returned without clearing state = still "running".
    assert _real_request_translation(USER_A) is False
    assert USER_A in translations._rerun_users
    assert worker_threads == [1]


def test_watchdog_replaces_a_stale_worker(worker_threads, monkeypatch):
    import time

    assert _real_request_translation(USER_A) is True
    time.sleep(0.05)
    # Pretend the worker last made progress 11 minutes ago (hung).
    translations._heartbeat[USER_A] -= translations.STALE_WORKER_SECONDS + 60

    assert _real_request_translation(USER_A) is True  # new worker started
    time.sleep(0.05)
    assert worker_threads == [1, 2]
    assert translations._generation[USER_A] == 2


def test_replaced_worker_exits_without_clearing_new_state(fake_db, fake_google, monkeypatch):
    """The old (stale) worker must stop at its next string and leave the
    new worker's 'running' flag alone."""
    monkeypatch.setattr(translations, "_new_client", lambda: fake_db)
    _seed(fake_db, "t1", "楼下面馆", "午饭")
    translations._running_users.add(USER_A)
    translations._generation[USER_A] = 2  # a newer worker (gen 2) now owns it

    translations._worker(USER_A, 1)  # the stale gen-1 worker resumes

    assert _rows(fake_db)["t1"].get("merchant_en") is None  # wrote nothing
    assert USER_A in translations._running_users            # gen 2 still running
    translations._running_users.discard(USER_A)
    translations._generation.clear()


def test_worker_runs_pass_on_its_own_client(fake_db, fake_google, monkeypatch):
    clients: list = []
    monkeypatch.setattr(translations, "_new_client", lambda: clients.append(1) or fake_db)
    _seed(fake_db, "t1", "楼下面馆", "午饭")
    translations._running_users.add(USER_A)
    translations._generation[USER_A] = 1

    translations._worker(USER_A, 1)

    assert clients == [1]
    assert _rows(fake_db)["t1"]["merchant_en"] == "Downstairs noodle shop"
    assert USER_A not in translations._running_users  # finished cleanly
    translations._generation.clear()
