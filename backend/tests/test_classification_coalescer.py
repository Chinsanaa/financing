"""Tests for ml.request_classification's per-user thread coalescing.

A multi-file upload batch calls schedule_classification once per file. Before
this coalescer, each call spawned its own daemon thread rescanning the user's
entire needs_review set — N files meant N racing full-table passes. These
tests exercise the threading logic directly (no HTTP, no DB) and assert that
concurrent requests for the same user collapse into at most one rerun.

Every join() has a timeout so a regression that deadlocks fails the test
instead of hanging the suite.
"""
import threading

import pytest

import ml

JOIN_TIMEOUT = 2.0


@pytest.fixture(autouse=True)
def _clean_coalescer_state():
    """Guard against state leaking between tests (or from a prior failure)."""
    ml._running_users.clear()
    ml._rerun_users.clear()
    yield
    ml._running_users.clear()
    ml._rerun_users.clear()


class _BlockingCounter:
    """Stand-in for classify_user_transactions: counts calls and blocks on
    an Event until released, so the test can control exactly when a
    "classification pass" finishes."""

    def __init__(self):
        self.calls = 0
        self.lock = threading.Lock()
        self.gate = threading.Event()
        self.entered = threading.Event()

    def __call__(self, user_id):
        with self.lock:
            self.calls += 1
        self.entered.set()
        self.gate.wait(timeout=JOIN_TIMEOUT)
        self.entered.clear()
        return 0


def test_second_request_reuses_running_worker(monkeypatch):
    fake = _BlockingCounter()
    monkeypatch.setattr(ml, "classify_user_transactions", fake)

    started_first = ml.request_classification("user-a")
    assert fake.entered.wait(timeout=JOIN_TIMEOUT)

    started_second = ml.request_classification("user-a")

    assert started_first is True
    assert started_second is False

    fake.gate.set()  # let the first pass finish; worker should see the rerun flag
    assert fake.entered.wait(timeout=JOIN_TIMEOUT)  # second pass starts
    fake.gate.set()

    _join_all_classify_threads()
    assert fake.calls == 2
    assert ml._running_users == set()
    assert ml._rerun_users == set()


def test_burst_coalesces_to_one_rerun(monkeypatch):
    fake = _BlockingCounter()
    monkeypatch.setattr(ml, "classify_user_transactions", fake)

    assert ml.request_classification("user-a") is True
    assert fake.entered.wait(timeout=JOIN_TIMEOUT)

    # A burst of extra requests while the worker is mid-pass.
    for _ in range(4):
        assert ml.request_classification("user-a") is False

    threads_before = _classify_thread_count()
    assert threads_before == 1

    fake.gate.set()
    assert fake.entered.wait(timeout=JOIN_TIMEOUT)  # the single coalesced rerun
    fake.gate.set()

    _join_all_classify_threads()
    assert fake.calls == 2
    assert ml._running_users == set()
    assert ml._rerun_users == set()


def test_distinct_users_are_independent(monkeypatch):
    fake = _BlockingCounter()
    monkeypatch.setattr(ml, "classify_user_transactions", fake)

    assert ml.request_classification("user-a") is True
    assert ml.request_classification("user-b") is True

    fake.gate.set()
    _join_all_classify_threads()
    assert ml._running_users == set()


def test_state_is_clear_after_worker_exits(monkeypatch):
    fake = _BlockingCounter()
    monkeypatch.setattr(ml, "classify_user_transactions", fake)

    ml.request_classification("user-a")
    fake.gate.set()
    _join_all_classify_threads()

    assert ml._running_users == set()
    assert ml._rerun_users == set()

    # A fresh request afterward must start a new worker, not silently no-op.
    fake.gate.clear()
    assert ml.request_classification("user-a") is True
    fake.gate.set()
    _join_all_classify_threads()


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_worker_cleans_up_when_classifier_raises(monkeypatch):
    def _boom(user_id):
        raise RuntimeError("classification blew up")

    monkeypatch.setattr(ml, "classify_user_transactions", _boom)

    ml.request_classification("user-a")
    _join_all_classify_threads()

    assert ml._running_users == set()
    assert ml._rerun_users == set()

    # The user must not be permanently locked out by the earlier crash.
    monkeypatch.setattr(ml, "classify_user_transactions", lambda user_id: 0)
    assert ml.request_classification("user-a") is True
    _join_all_classify_threads()


def _classify_thread_count() -> int:
    return sum(1 for t in threading.enumerate() if t.name.startswith("classify-"))


def _join_all_classify_threads():
    for t in threading.enumerate():
        if t.name.startswith("classify-") and t is not threading.current_thread():
            t.join(timeout=JOIN_TIMEOUT)
