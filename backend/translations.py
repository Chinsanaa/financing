"""Background English translation of transaction text, stored on the row.

Reports / Review / Export used to call Google Translate live, once per
Chinese merchant/description, serially, on every page load (~200 calls for a
100-row Reports page, each 0.2-1s, with no timeout — deep_translator's
requests.get has none). Translations never change, so they're now computed
once per distinct string here and stored in `transactions.merchant_en` /
`description_en`; the request path only reads them
(`src.translate.merchant_label_stored` / `description_label_stored`).

Triggered after uploads and manual entries, and lazily by the read endpoints
whenever they see a row still missing a translation — which is also how the
one-time backfill of pre-existing rows happens, and how a failed translation
(column left NULL) gets retried.
"""
import threading
import time
from typing import Callable, Dict, Iterable, Optional

from supabase import Client, create_client

from config import settings, supabase_client
from db import _call_with_retry, fetch_all
from errors import logger
from src.translate import english_for_storage

# Same per-user coalescing as ml.request_classification: at most one worker
# thread per user; a request arriving mid-run makes that worker loop once
# more instead of spawning a second thread.
_lock = threading.Lock()
_running_users: set = set()
_rerun_users: set = set()

# Watchdog. A worker that makes no progress for this long is treated as dead
# and replaced (2026-09-29: one hung forever after its first fetch, and
# because it still counted as "running", every later request was a no-op).
# `_generation` lets the replaced worker notice it's stale and exit quietly
# instead of clearing the new worker's state.
STALE_WORKER_SECONDS = 10 * 60
_heartbeat: Dict[str, float] = {}
_generation: Dict[str, int] = {}

# Strings whose translation just failed are skipped for a while, so a
# Google outage/ratelimit doesn't turn every Reports visit (each of which
# re-requests translation for the still-NULL rows) into a fresh burst of
# doomed calls.
FAILURE_RETRY_SECONDS = 30 * 60
_recent_failures: Dict[str, float] = {}

# Circuit breaker: this many failures in a row means Google is unreachable
# (every call is timing out) — stop the pass instead of spending 10s on each
# of hundreds of strings. The rest stay NULL and a later pass retries them.
MAX_CONSECUTIVE_FAILURES = 5

LOG_EVERY = 50


def _new_client() -> Client:
    """A Supabase client owned by one worker thread.

    The process-wide `supabase_client` is shared by the request threadpool
    (several calls at once via asyncio.gather) over one HTTP/2 connection;
    using it from a long-running background thread too is the prime suspect
    for the 2026-09-29 hang. A private client shares nothing.
    """
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def request_translation(user_id: str) -> bool:
    """Ask for `user_id`'s untranslated rows to be filled in the background.

    Never raises and never blocks: returns True if a new worker thread was
    started, False if a live one was already running (it will loop once more).
    """
    now = time.monotonic()
    with _lock:
        if user_id in _running_users:
            if now - _heartbeat.get(user_id, now) < STALE_WORKER_SECONDS:
                _rerun_users.add(user_id)
                return False
            logger.warning(
                "Translation worker for %s made no progress for %ds; starting a new one",
                user_id, int(now - _heartbeat[user_id]),
            )
        _running_users.add(user_id)
        _rerun_users.discard(user_id)
        _heartbeat[user_id] = now
        generation = _generation.get(user_id, 0) + 1
        _generation[user_id] = generation
    try:
        threading.Thread(
            target=_worker, args=(user_id, generation),
            name=f"translate-{user_id[:8]}", daemon=True,
        ).start()
    except Exception as e:
        with _lock:
            if _generation.get(user_id) == generation:
                _running_users.discard(user_id)
                _rerun_users.discard(user_id)
        logger.warning("Could not start translation worker for %s: %s", user_id, e)
        return False
    return True


def _worker(user_id: str, generation: int) -> None:
    def alive() -> bool:
        # Called after every string: records progress for the watchdog and
        # tells a replaced (stale) worker to stop.
        with _lock:
            if _generation.get(user_id) != generation:
                return False
            _heartbeat[user_id] = time.monotonic()
            return True

    try:
        client = _new_client()
        while True:
            try:
                translate_user_transactions(user_id, client=client, alive=alive)
            except Exception as e:
                logger.warning("Translation pass failed for %s: %s", user_id, e)
            with _lock:
                if _generation.get(user_id) != generation:
                    return  # replaced by the watchdog; the new worker owns the state
                if user_id in _rerun_users:
                    _rerun_users.discard(user_id)
                    continue
                _running_users.discard(user_id)
                return
    except BaseException as e:
        with _lock:
            if _generation.get(user_id) == generation:
                _running_users.discard(user_id)
                _rerun_users.discard(user_id)
        if isinstance(e, Exception):
            logger.warning("Translation worker for %s crashed: %s", user_id, e)
            return
        raise


def _in_backoff(text: str) -> bool:
    failed_at = _recent_failures.get(text)
    return failed_at is not None and time.monotonic() - failed_at < FAILURE_RETRY_SECONDS


def _translate(text: str) -> Optional[str]:
    """english_for_storage with the failure backoff applied."""
    if _in_backoff(text):
        return None
    value = english_for_storage(text)
    if value is None:
        _recent_failures[text] = time.monotonic()
    else:
        _recent_failures.pop(text, None)
    return value


class _GoogleUnreachable(Exception):
    pass


def _fill_column(
    client, user_id: str, source_col: str, target_col: str,
    texts: Iterable[str], alive: Callable[[], bool], progress: Dict[str, int],
) -> int:
    """Translate each distinct text once and write it to every matching row."""
    written = 0
    failures_in_a_row = 0
    for text in texts:
        if not alive():
            return written
        if _in_backoff(text):
            continue  # failed recently; not a new failure
        value = _translate(text)
        if value is None:
            failures_in_a_row += 1
            if failures_in_a_row >= MAX_CONSECUTIVE_FAILURES:
                raise _GoogleUnreachable(
                    f"{failures_in_a_row} translations failed in a row"
                )
            continue
        failures_in_a_row = 0

        def _update(match_null_source: bool = False):
            q = (
                client.table("transactions")
                .update({target_col: value})
                .eq("user_id", user_id)
                .is_(target_col, "null")
            )
            q = q.is_(source_col, "null") if match_null_source else q.eq(source_col, text)
            return q.execute()

        _call_with_retry(_update)
        if text == "":
            # A NULL source column reads as "" above but doesn't match
            # .eq(col, ""); without this those rows would stay NULL and
            # re-trigger the worker on every page load.
            _call_with_retry(lambda: _update(match_null_source=True))
        written += 1
        progress["written"] += 1
        if progress["written"] % LOG_EVERY == 0:
            logger.info(
                "Translation pass for %s: %d/%d strings written",
                user_id, progress["written"], progress["total"],
            )
    return written


def translate_user_transactions(
    user_id: str, client=None, alive: Optional[Callable[[], bool]] = None,
) -> int:
    """Fill NULL merchant_en/description_en for one user. Returns the number
    of distinct strings written. Sync — runs on the worker thread."""
    client = client or supabase_client
    alive = alive or (lambda: True)
    rows = fetch_all(
        lambda: client.table("transactions")
        .select("merchant, description, merchant_en, description_en")
        .eq("user_id", user_id)
        .or_("merchant_en.is.null,description_en.is.null")
    )
    # All pages are read before any update, so OFFSET paging can't skip
    # rows that the updates below remove from the NULL filter.
    merchants = {r["merchant"] or "" for r in rows if r.get("merchant_en") is None}
    descriptions = {r["description"] or "" for r in rows if r.get("description_en") is None}
    progress = {"written": 0, "total": len(merchants) + len(descriptions)}
    if not progress["total"]:
        return 0
    logger.info(
        "Translation pass start for %s: %d rows, %d distinct strings",
        user_id, len(rows), progress["total"],
    )
    try:
        _fill_column(client, user_id, "merchant", "merchant_en", sorted(merchants), alive, progress)
        _fill_column(client, user_id, "description", "description_en", sorted(descriptions), alive, progress)
    except _GoogleUnreachable as e:
        logger.warning(
            "Translation pass for %s stopped early (%s); %d/%d written, the rest retry later",
            user_id, e, progress["written"], progress["total"],
        )
        return progress["written"]
    logger.info(
        "Translation pass done for %s: %d/%d strings written",
        user_id, progress["written"], progress["total"],
    )
    return progress["written"]


def request_translation_if_missing(user_id: str, rows: Iterable[dict]) -> None:
    """Read-path hook: kick the worker if any returned row lacks a translation."""
    if any(r.get("merchant_en") is None or r.get("description_en") is None for r in rows):
        request_translation(user_id)
