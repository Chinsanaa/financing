"""Home-currency FX: rate cache reads (request path) and background refresh.

Contract: docs/contracts/API_V5.md §2. Every amount is stored in CNY; a user
may pick a home currency (profiles.home_currency) and the dashboard shows
`*_home` values next to the CNY ones. Rates are ECB reference rates
republished by Frankfurter, cached in the `fx_rates` table as "units of the
quote currency per 1 CNY", one row per business day.

Two halves, kept strictly apart:

* Request path (`load_rates`, `RateTable`, `get_home_currency`): reads
  `fx_rates` / `profiles` only. **Never** touches the network, so a slow or
  unreachable Frankfurter can never slow down or break a page load.
* Background (`request_backfill`, `request_backfill_for_user`,
  `maybe_refresh_all`): daemon threads with their OWN Supabase client (see
  translations._new_client for why the shared HTTP/2 client must not be used
  from a long-running thread), one Frankfurter time-series call per missing
  range, ~5 s timeout, failures logged and swallowed. Per-quote coalescing:
  at most one worker per currency; requests arriving mid-run are merged and
  handled by that worker's next loop.
"""
import asyncio
import bisect
import math
import os
import threading
import time
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import httpx
from supabase import Client, create_client

from config import settings, supabase_client
from db import _call_with_retry, fetch_all, fetch_all_async, run_query
from errors import logger

BASE = "CNY"

# Contract §3.1, in display order. BGN deliberately excluded (Bulgaria
# adopted the euro on 2026-01-01; the ECB no longer publishes it).
SUPPORTED: Dict[str, str] = {
    "USD": "US Dollar",
    "EUR": "Euro",
    "GBP": "British Pound",
    "AUD": "Australian Dollar",
    "CAD": "Canadian Dollar",
    "JPY": "Japanese Yen",
    "KRW": "South Korean Won",
    "SGD": "Singapore Dollar",
    "HKD": "Hong Kong Dollar",
    "CHF": "Swiss Franc",
    "NZD": "New Zealand Dollar",
    "SEK": "Swedish Krona",
    "NOK": "Norwegian Krone",
    "DKK": "Danish Krone",
    "PLN": "Polish Zloty",
    "CZK": "Czech Koruna",
    "HUF": "Hungarian Forint",
    "INR": "Indian Rupee",
    "IDR": "Indonesian Rupiah",
    "MYR": "Malaysian Ringgit",
    "PHP": "Philippine Peso",
    "THB": "Thai Baht",
    "ZAR": "South African Rand",
    "BRL": "Brazilian Real",
    "MXN": "Mexican Peso",
    "ILS": "Israeli New Shekel",
    "TRY": "Turkish Lira",
    "ISK": "Icelandic Krona",
    "RON": "Romanian Leu",
}

SOURCE_NAME = "European Central Bank via Frankfurter"

STRICT_MAX_AGE_DAYS = 7          # strict lookup: rate at most 7 days older than the row
DEFAULT_HISTORY_DAYS = 400       # backfill start when the user has no rows
FRESH_MAX_AGE_DAYS = 1           # newest stored rate this recent = no fetch needed
# A stored range "covers" a requested start when its earliest rate is at most
# this many days after it: the first days of a range are often a weekend or
# an ECB holiday (Easter Fri-Mon is the longest gap), for which no rate will
# ever exist, and refetching them on every trigger would be pointless.
START_COVER_SLACK_DAYS = 4
REFRESH_ALL_SECONDS = 6 * 60 * 60  # /health/deep: per-currency throttle
HTTP_TIMEOUT_SECONDS = 5.0
UPSERT_CHUNK = 500

# FX_API_BASE overrides the primary host (e.g. a self-hosted Frankfurter).
# `.dev/v1` takes base/symbols; the legacy `.app` host takes from/to (and
# currently 301-redirects to .dev). Both return the same JSON shape.
PRIMARY_API_BASE = "https://api.frankfurter.dev/v1"
FALLBACK_API_BASE = "https://api.frankfurter.app"


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

def _today() -> date:
    """UTC calendar date (ECB rate dates are calendar dates; patched in tests)."""
    return datetime.now(timezone.utc).date()


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def row_date(ts) -> date:
    """FX lookup date of a transaction: ("timestamp" AT TIME ZONE 'UTC')::date.

    Timestamps are China wall-clock stored as UTC (contract §0), so this is
    the UTC calendar date — never converted to Asia/Shanghai again. Accepts
    an ISO string (`+00:00`, `Z`, Postgres `+00`, or naive) or a datetime /
    date. A naive value is taken as already-UTC.
    """
    if isinstance(ts, datetime):
        if ts.tzinfo is not None:
            ts = ts.astimezone(timezone.utc)
        return ts.date()
    if isinstance(ts, date):
        return ts
    s = str(ts).strip()
    try:
        dt = datetime.fromisoformat(s[:-1] + "+00:00" if s.endswith(("Z", "z")) else s)
    except ValueError:
        return date.fromisoformat(s[:10])
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.date()


# ---------------------------------------------------------------------------
# Request path: rate table
# ---------------------------------------------------------------------------

class RateTable:
    """Sorted (rate_date, rate) pairs for ONE quote currency, with the
    contract's lookups. Built by `load_rates`; lookups are exact for dates
    inside the loaded [start, end] window.

    Accepts a mapping {date|"YYYY-MM-DD": rate}, an iterable of
    (date, rate) pairs, or an iterable of fx_rates row dicts.
    """

    def __init__(self, rates=None):
        pairs: Dict[date, float] = {}
        if rates is not None:
            items = rates.items() if isinstance(rates, dict) else rates
            for item in items:
                if isinstance(item, dict):
                    d, r = item.get("rate_date"), item.get("rate")
                else:
                    d, r = item
                if d is None or r is None:
                    continue
                pairs[_as_date(d)] = float(r)
        self._dates: List[date] = sorted(pairs)
        self._rates: List[float] = [pairs[d] for d in self._dates]

    def __len__(self) -> int:
        return len(self._dates)

    def __bool__(self) -> bool:  # an empty table is still a valid table
        return True

    def _idx_on_or_before(self, d: date) -> int:
        return bisect.bisect_right(self._dates, d) - 1

    def strict(self, d: date) -> Optional[float]:
        """Rate with the greatest rate_date <= d and >= d - 7 days, else None."""
        i = self._idx_on_or_before(d)
        if i < 0 or self._dates[i] < d - timedelta(days=STRICT_MAX_AGE_DAYS):
            return None
        return self._rates[i]

    def lenient(self, d: date) -> Tuple[Optional[float], bool]:
        """(rate, approx) for the all-time total: nearest rate_date <= d with
        no age limit; before the earliest stored rate, the earliest one.
        approx=True whenever the strict lookup would have failed.
        (None, False) when nothing is stored."""
        if not self._dates:
            return None, False
        i = self._idx_on_or_before(d)
        if i < 0:
            return self._rates[0], True
        return self._rates[i], self.strict(d) is None

    def latest(self, on_or_before: date) -> Tuple[Optional[date], Optional[float]]:
        """(rate_date, rate) of the newest row <= on_or_before, else (None, None)."""
        i = self._idx_on_or_before(on_or_before)
        if i < 0:
            return None, None
        return self._dates[i], self._rates[i]


async def load_rates(quote: str, start: date, end: date) -> RateTable:
    """Everything the lookups for row dates in [start, end] need, from the DB
    only (never the network): one range read of rate_date in
    [start - 7d, end], plus the single nearest row before that window and
    the earliest stored row (both for `lenient`). The three reads run
    concurrently."""
    quote = (quote or "").strip().upper()
    lo = (start - timedelta(days=STRICT_MAX_AGE_DAYS)).isoformat()
    hi = end.isoformat()

    def _range():
        return (
            supabase_client.table("fx_rates").select("rate_date, rate")
            .eq("quote", quote).gte("rate_date", lo).lte("rate_date", hi)
            .order("rate_date")
        )

    async def _one(build):
        res = await run_query(lambda: build().execute())
        return (res.data or [])[:1]

    window, before, earliest = await asyncio.gather(
        fetch_all_async(_range),
        _one(lambda: supabase_client.table("fx_rates").select("rate_date, rate")
             .eq("quote", quote).lt("rate_date", lo)
             .order("rate_date", desc=True).limit(1)),
        _one(lambda: supabase_client.table("fx_rates").select("rate_date, rate")
             .eq("quote", quote).order("rate_date").limit(1)),
    )
    return RateTable([*before, *earliest, *window])


async def get_home_currency(user_id: str) -> Optional[str]:
    """profiles.home_currency for the user (upper-case), or None."""
    res = await run_query(
        lambda: supabase_client.table("profiles").select("home_currency")
        .eq("id", user_id).limit(1).execute()
    )
    rows = res.data or []
    value = rows[0].get("home_currency") if rows else None
    value = (value or "").strip().upper()
    return value or None


# ---------------------------------------------------------------------------
# Background: Frankfurter fetch + upsert
# ---------------------------------------------------------------------------

def _new_client() -> Client:
    """A Supabase client owned by one background thread (shares nothing with
    the request path's client — see translations._new_client)."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def _series_url(api_base: str, quote: str, start: date, end: date) -> str:
    api_base = api_base.rstrip("/")
    path = f"{api_base}/{start.isoformat()}..{end.isoformat()}"
    if "frankfurter.app" in api_base:
        return f"{path}?from={BASE}&to={quote}"
    return f"{path}?base={BASE}&symbols={quote}"


def _parse_series(payload, quote: str) -> Dict[date, float]:
    """{date: rate} from a Frankfurter time-series response.

    Shape (both hosts): {"base": "CNY", "rates": {"2026-10-09": {"USD": 0.14943}, ...}}.
    Also accepts a flat list of {"date", "quote", "rate"} entries.
    Non-positive / non-numeric rates are dropped.
    """
    out: Dict[date, float] = {}

    def _put(d, r):
        try:
            value = float(r)
            day = _as_date(d)
        except (TypeError, ValueError):
            return
        if math.isfinite(value) and value > 0:
            out[day] = value

    if isinstance(payload, dict):
        base = payload.get("base")
        if base and str(base).upper() != BASE:
            raise ValueError(f"unexpected base {base!r}")
        rates = payload.get("rates")
        if isinstance(rates, dict):
            for d, by_quote in rates.items():
                if isinstance(by_quote, dict) and quote in by_quote:
                    _put(d, by_quote[quote])
            return out
        payload = rates if isinstance(rates, list) else []
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict) and str(item.get("quote", quote)).upper() == quote:
                _put(item.get("date"), item.get("rate"))
    return out


def _fetch_series(quote: str, start: date, end: date) -> Dict[date, float]:
    """One Frankfurter time-series call (fallback host on failure).

    A 404 means "no published dates in that range" (e.g. a range entirely
    in the future or before ECB history), which is an empty result, not an
    error. Raises when every host fails.
    """
    primary = os.environ.get("FX_API_BASE") or PRIMARY_API_BASE
    hosts = [primary] + ([FALLBACK_API_BASE] if primary != FALLBACK_API_BASE else [])
    last_error: Optional[Exception] = None
    with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=True) as http:
        for api_base in hosts:
            url = _series_url(api_base, quote, start, end)
            try:
                resp = http.get(url)
                if resp.status_code == 404:
                    return {}
                resp.raise_for_status()
                return _parse_series(resp.json(), quote)
            except Exception as e:  # network, HTTP status, bad JSON
                last_error = e
                logger.warning("FX fetch %s %s..%s from %s failed: %s", quote, start, end, api_base, e)
    raise RuntimeError(f"all FX hosts failed: {last_error}")


def _upsert_rates(client, quote: str, rates: Dict[date, float]) -> int:
    if not rates:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {"quote": quote, "rate_date": d.isoformat(), "rate": r, "fetched_at": now}
        for d, r in sorted(rates.items())
    ]
    for i in range(0, len(rows), UPSERT_CHUNK):
        chunk = rows[i:i + UPSERT_CHUNK]
        _call_with_retry(
            lambda: client.table("fx_rates").upsert(chunk, on_conflict="quote,rate_date").execute()
        )
    return len(rows)


def _stored_bounds(client, quote: str) -> Tuple[Optional[date], Optional[date]]:
    """(earliest, newest) stored rate_date for the quote."""
    def _edge(desc: bool):
        res = _call_with_retry(
            lambda: client.table("fx_rates").select("rate_date").eq("quote", quote)
            .order("rate_date", desc=desc).limit(1).execute()
        )
        rows = res.data or []
        return _as_date(rows[0]["rate_date"]) if rows else None
    return _edge(False), _edge(True)


def missing_ranges(
    start: date, end: date, earliest: Optional[date], newest: Optional[date],
    today: date, check_start: bool = True,
) -> List[Tuple[date, date]]:
    """Ranges that still need fetching. Stored rates are contiguous (we only
    ever extend the cached span at its edges), so at most a head and a tail.

    * nothing stored → [start, end]
    * head: earliest > start (+ slack) → [start, earliest - 1]  (skipped when
      check_start is False, i.e. the /health/deep age-only refresh)
    * tail: newest older than FRESH_MAX_AGE_DAYS → [newest + 1, end]
    """
    end = min(end, today)
    if earliest is None or newest is None:
        return [(start, end)] if start <= end else []
    out: List[Tuple[date, date]] = []
    if check_start and earliest > start + timedelta(days=START_COVER_SLACK_DAYS):
        out.append((start, min(earliest - timedelta(days=1), end)))
    if (today - newest).days > FRESH_MAX_AGE_DAYS and newest < end:
        out.append((newest + timedelta(days=1), end))
    return [(a, b) for a, b in out if a <= b]


def backfill(quote: str, start: date, end: Optional[date] = None,
             client=None, check_start: bool = True) -> int:
    """Fetch whatever part of [start, end] isn't cached yet and upsert it.
    Sync; runs on a worker thread (or from scripts/backfill_fx.py).
    Returns the number of rate rows written. Raises on DB/network failure."""
    quote = quote.strip().upper()
    if quote not in SUPPORTED:
        logger.warning("FX backfill skipped: unsupported quote %r", quote)
        return 0
    client = client or _new_client()
    today = _today()
    end = min(end or today, today)
    earliest, newest = _stored_bounds(client, quote)
    written = 0
    for a, b in missing_ranges(start, end, earliest, newest, today, check_start):
        rates = _fetch_series(quote, a, b)
        written += _upsert_rates(client, quote, rates)
        logger.info("FX backfill %s %s..%s: %d rates", quote, a, b, len(rates))
    return written


# ---------------------------------------------------------------------------
# Background: triggers (non-blocking, never raise)
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_running: set = set()
# quote -> pending (start, end, check_start), merged while a worker runs.
_pending: Dict[str, Tuple[date, Optional[date], bool]] = {}
_last_refresh: Dict[str, float] = {}
_scan_running = False


_clock = time.monotonic  # throttle clock (patched in tests)


def _spawn(target, *args, name: str = "fx") -> None:
    """Start a daemon thread (tests replace this to run inline / record)."""
    threading.Thread(target=target, args=args, name=name, daemon=True).start()


def _merge(old, new):
    (s1, e1, c1), (s2, e2, c2) = old, new
    end = None if e1 is None or e2 is None else max(e1, e2)
    return (min(s1, s2), end, c1 or c2)


def _reset_state() -> None:
    """Test helper: forget all in-process coalescing/throttle state."""
    global _scan_running
    with _lock:
        _running.clear()
        _pending.clear()
        _last_refresh.clear()
        _scan_running = False


def _enqueue(quote: str, start: date, end: Optional[date], check_start: bool) -> None:
    quote = (quote or "").strip().upper()
    if quote not in SUPPORTED:
        return
    req = (start, end, check_start)
    with _lock:
        if quote in _running:
            _pending[quote] = _merge(_pending[quote], req) if quote in _pending else req
            return
        _running.add(quote)
        _pending[quote] = req
    try:
        _spawn(_quote_worker, quote, name=f"fx-{quote}")
    except Exception as e:
        with _lock:
            _running.discard(quote)
            _pending.pop(quote, None)
        logger.warning("Could not start FX worker for %s: %s", quote, e)


def _quote_worker(quote: str) -> None:
    client = None
    try:
        while True:
            with _lock:
                req = _pending.pop(quote, None)
                if req is None:
                    _running.discard(quote)
                    return
            start, end, check_start = req
            try:
                client = client or _new_client()
                backfill(quote, start, end, client=client, check_start=check_start)
            except Exception as e:
                logger.warning("FX backfill for %s failed: %s", quote, e)
    except BaseException:
        with _lock:
            _running.discard(quote)
            _pending.pop(quote, None)
        raise


def request_backfill(quote: str, start: date, end: Optional[date] = None) -> None:
    """Fetch + upsert [start, end or today] for `quote` in the background.
    Non-blocking, never raises; coalesced per quote."""
    try:
        _enqueue(quote, start, end, True)
    except Exception as e:
        logger.warning("FX request_backfill(%s) failed: %s", quote, e)


def _user_backfill_job(user_id: str, start: Optional[date]) -> None:
    try:
        client = _new_client()
        res = _call_with_retry(
            lambda: client.table("profiles").select("home_currency")
            .eq("id", user_id).limit(1).execute()
        )
        rows = res.data or []
        quote = ((rows[0].get("home_currency") if rows else None) or "").strip().upper()
        if not quote:
            return
        if start is None:
            first = _call_with_retry(
                lambda: client.table("transactions").select("timestamp")
                .eq("user_id", user_id).order("timestamp").limit(1).execute()
            )
            first_rows = [r for r in (first.data or []) if r.get("timestamp")]
            start = (
                row_date(first_rows[0]["timestamp"]) - timedelta(days=STRICT_MAX_AGE_DAYS)
                if first_rows else _today() - timedelta(days=DEFAULT_HISTORY_DAYS)
            )
        _enqueue(quote, start, None, True)
    except Exception as e:
        logger.warning("FX backfill for user %s failed: %s", user_id, e)


def request_backfill_for_user(user_id: str, start: Optional[date] = None) -> None:
    """Backfill the user's home currency in the background (no-op without
    one). Default start: earliest transaction date - 7 days, or today - 400
    days for a user with no rows. Non-blocking, never raises."""
    try:
        _spawn(_user_backfill_job, user_id, start, name="fx-user")
    except Exception as e:
        logger.warning("FX request_backfill_for_user(%s) failed: %s", user_id, e)


def _refresh_all_job() -> None:
    global _scan_running
    try:
        client = _new_client()
        rows = fetch_all(
            lambda: client.table("profiles").select("home_currency")
            .not_.is_("home_currency", "null")
        )
        quotes = sorted({(r.get("home_currency") or "").strip().upper() for r in rows} - {""})
        today = _today()
        now = _clock()
        for quote in quotes:
            if quote not in SUPPORTED:
                continue
            with _lock:
                last = _last_refresh.get(quote)
                if last is not None and now - last < REFRESH_ALL_SECONDS:
                    continue
                _last_refresh[quote] = now
            # Age-only check (contract §2 trigger 3); a currency with nothing
            # cached yet gets the default history window.
            _enqueue(quote, today - timedelta(days=DEFAULT_HISTORY_DAYS), None, False)
    except Exception as e:
        logger.warning("FX refresh-all failed: %s", e)
    finally:
        with _lock:
            _scan_running = False


def maybe_refresh_all() -> None:
    """/health/deep hook: refresh every in-use home currency, at most once per
    6 h per currency (in-process). Non-blocking, never raises."""
    global _scan_running
    try:
        with _lock:
            if _scan_running:
                return
            _scan_running = True
        try:
            _spawn(_refresh_all_job, name="fx-refresh-all")
        except Exception:
            with _lock:
                _scan_running = False
            raise
    except Exception as e:
        logger.warning("FX maybe_refresh_all failed: %s", e)
