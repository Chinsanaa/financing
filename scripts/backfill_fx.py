"""Manually seed / extend the fx_rates cache from Frankfurter (ECB rates).

Usage (from the repo root; needs SUPABASE_URL, SUPABASE_ANON_KEY and
SUPABASE_SERVICE_ROLE_KEY in the environment or in backend/.env):

    python scripts/backfill_fx.py USD EUR --start 2024-01-01
    python scripts/backfill_fx.py USD --start 2025-06-01 --end 2025-12-31
    python scripts/backfill_fx.py --in-use --start 2024-01-01   # every profiles.home_currency

Uses the same code path as the backend's background backfill
(backend/fx.py `backfill`): only the parts of [start, end] that aren't cached
yet are fetched (one Frankfurter call per missing range), then upserted on
(quote, rate_date). `--force` refetches the whole range anyway. Rates are
stored as units of the quote currency per 1 CNY.
"""
import argparse
import os
import sys
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))
# pydantic-settings reads `.env` relative to the working directory.
os.chdir(BACKEND_DIR)

import fx  # noqa: E402
from db import fetch_all  # noqa: E402


def _in_use_currencies(client) -> list:
    rows = fetch_all(
        lambda: client.table("profiles").select("home_currency")
        .not_.is_("home_currency", "null")
    )
    return sorted({(r.get("home_currency") or "").strip().upper() for r in rows} - {""})


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Seed fx_rates from Frankfurter.")
    parser.add_argument("currencies", nargs="*", help="ISO codes, e.g. USD EUR")
    parser.add_argument("--start", required=True, type=date.fromisoformat, help="YYYY-MM-DD")
    parser.add_argument("--end", type=date.fromisoformat, default=None, help="YYYY-MM-DD (default: today)")
    parser.add_argument("--in-use", action="store_true", help="also every profiles.home_currency")
    parser.add_argument("--force", action="store_true", help="refetch even if already cached")
    args = parser.parse_args(argv)

    client = fx._new_client()
    quotes = {c.strip().upper() for c in args.currencies}
    if args.in_use:
        quotes |= set(_in_use_currencies(client))
    unsupported = sorted(q for q in quotes if q not in fx.SUPPORTED)
    if unsupported:
        parser.error(f"unsupported currencies: {', '.join(unsupported)} "
                     f"(supported: {', '.join(fx.SUPPORTED)})")
    if not quotes:
        parser.error("give at least one currency or --in-use")

    failed = 0
    for quote in sorted(quotes):
        try:
            if args.force:
                rates = fx._fetch_series(quote, args.start, args.end or fx._today())
                written = fx._upsert_rates(client, quote, rates)
            else:
                written = fx.backfill(quote, args.start, args.end, client=client)
            print(f"{quote}: {written} rate rows written")
        except Exception as e:
            failed += 1
            print(f"{quote}: FAILED ({e})", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
