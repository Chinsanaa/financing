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
from typing import Dict, Iterable

from config import supabase_client
from db import _call_with_retry, fetch_all
from errors import logger
from src.translate import english_for_storage

# Same per-user coalescing as ml.request_classification: at most one worker
# thread per user; a request arriving mid-run makes that worker loop once
# more instead of spawning a second thread.
_lock = threading.Lock()
_running_users: set = set()
_rerun_users: set = set()

# Strings whose translation just failed are skipped for a while, so a
# Google outage/ratelimit doesn't turn every Reports visit (each of which
# re-requests translation for the still-NULL rows) into a fresh burst of
# doomed calls.
FAILURE_RETRY_SECONDS = 30 * 60
_recent_failures: Dict[str, float] = {}


def request_translation(user_id: str) -> bool:
    """Ask for `user_id`'s untranslated rows to be filled in the background.

    Never raises and never blocks: returns True if a new worker thread was
    started, False if one was already running (it will loop once more).
    """
    with _lock:
        if user_id in _running_users:
            _rerun_users.add(user_id)
            return False
        _running_users.add(user_id)
    try:
        threading.Thread(
            target=_worker, args=(user_id,),
            name=f"translate-{user_id[:8]}", daemon=True,
        ).start()
    except Exception as e:
        with _lock:
            _running_users.discard(user_id)
            _rerun_users.discard(user_id)
        logger.warning("Could not start translation worker for %s: %s", user_id, e)
        return False
    return True


def _worker(user_id: str) -> None:
    try:
        while True:
            try:
                translate_user_transactions(user_id)
            except Exception as e:
                logger.warning("Translation pass failed for %s: %s", user_id, e)
            with _lock:
                if user_id in _rerun_users:
                    _rerun_users.discard(user_id)
                    continue
                _running_users.discard(user_id)
                return
    except BaseException:
        with _lock:
            _running_users.discard(user_id)
            _rerun_users.discard(user_id)
        raise


def _translate(text: str):
    """english_for_storage with the failure backoff applied."""
    failed_at = _recent_failures.get(text)
    if failed_at is not None and time.monotonic() - failed_at < FAILURE_RETRY_SECONDS:
        return None
    value = english_for_storage(text)
    if value is None:
        _recent_failures[text] = time.monotonic()
    else:
        _recent_failures.pop(text, None)
    return value


def _fill_column(user_id: str, source_col: str, target_col: str, texts: Iterable[str]) -> int:
    """Translate each distinct text once and write it to every matching row."""
    written = 0
    for text in texts:
        value = _translate(text)
        if value is None:
            continue

        def _update(match_null_source: bool = False):
            q = (
                supabase_client.table("transactions")
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
    return written


def translate_user_transactions(user_id: str) -> int:
    """Fill NULL merchant_en/description_en for one user. Returns the number
    of distinct strings written. Sync — runs on the worker thread."""
    rows = fetch_all(
        lambda: supabase_client.table("transactions")
        .select("merchant, description, merchant_en, description_en")
        .eq("user_id", user_id)
        .or_("merchant_en.is.null,description_en.is.null")
    )
    # All pages are read before any update, so OFFSET paging can't skip
    # rows that the updates below remove from the NULL filter.
    merchants = {r["merchant"] or "" for r in rows if r.get("merchant_en") is None}
    descriptions = {r["description"] or "" for r in rows if r.get("description_en") is None}
    return (
        _fill_column(user_id, "merchant", "merchant_en", sorted(merchants))
        + _fill_column(user_id, "description", "description_en", sorted(descriptions))
    )


def request_translation_if_missing(user_id: str, rows: Iterable[dict]) -> None:
    """Read-path hook: kick the worker if any returned row lacks a translation."""
    if any(r.get("merchant_en") is None or r.get("description_en") is None for r in rows):
        request_translation(user_id)
