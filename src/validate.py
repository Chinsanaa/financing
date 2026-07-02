"""Lightweight data validation for the unified transaction schema.

Checks structural and value-level invariants and RETURNS a list of violations
rather than raising — callers (run_all.py, tests) decide whether to warn or
fail. Refunds are legitimately negative (see parse.py refund netting), so the
amount check flags only zero/NaN amounts, not negatives.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import pandas as pd

REQUIRED_COLUMNS = ["timestamp", "merchant", "description", "amount", "source"]

# Transactions before this project could plausibly exist are almost certainly a
# parse error (e.g. a 1970 epoch default or a misread column).
MIN_REASONABLE_DATE = datetime(2000, 1, 1)


@dataclass
class Violation:
    check: str
    severity: str  # "error" | "warning"
    count: int
    detail: str

    def __str__(self) -> str:
        return f"[{self.severity.upper():7s}] {self.check}: {self.detail} (n={self.count})"


def validate_transactions(
    df: pd.DataFrame,
    max_date: Optional[datetime] = None,
) -> List[Violation]:
    """Validate a parsed/combined transactions frame. Returns violations (may be empty)."""
    violations: List[Violation] = []
    max_date = max_date or datetime.now()

    # 1. Schema: required columns present
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        violations.append(Violation("schema", "error", len(missing),
                                    f"missing required columns: {missing}"))
        # Without the core columns the remaining checks are meaningless.
        return violations

    # 2. Amounts: must be non-zero, non-null numeric (negatives allowed = refunds)
    amt = pd.to_numeric(df["amount"], errors="coerce")
    n_nan = int(amt.isna().sum())
    if n_nan:
        violations.append(Violation("amount_nan", "error", n_nan,
                                    "non-numeric / missing amounts"))
    n_zero = int((amt == 0).sum())
    if n_zero:
        violations.append(Violation("amount_zero", "error", n_zero,
                                    "zero-amount rows (not real transactions)"))
    n_refund = int((amt < 0).sum())
    if n_refund:
        violations.append(Violation("amount_negative", "warning", n_refund,
                                    "negative amounts (expected if refund netting is on)"))

    # 3. Dates: parseable and within a sane range
    ts = pd.to_datetime(df["timestamp"], errors="coerce")
    n_bad_ts = int(ts.isna().sum())
    if n_bad_ts:
        violations.append(Violation("date_unparseable", "error", n_bad_ts,
                                    "unparseable timestamps"))
    valid_ts = ts.dropna()
    n_old = int((valid_ts < MIN_REASONABLE_DATE).sum())
    if n_old:
        violations.append(Violation("date_too_old", "error", n_old,
                                    f"timestamps before {MIN_REASONABLE_DATE.date()}"))
    n_future = int((valid_ts > max_date).sum())
    if n_future:
        violations.append(Violation("date_future", "error", n_future,
                                    f"timestamps after {max_date.date()}"))

    # 4. Duplicate transactions. There is no transaction-ID column in this
    #    schema, so the closest check is fully-identical rows on the natural
    #    key. These may be legitimate repeat purchases, so this is a warning.
    key = ["timestamp", "merchant", "description", "amount"]
    n_dup = int(df.duplicated(subset=key).sum())
    if n_dup:
        violations.append(Violation("duplicate_rows", "warning", n_dup,
                                    "fully-identical (time, merchant, desc, amount) rows"))

    return violations


def format_report(violations: List[Violation]) -> str:
    if not violations:
        return "Data validation: OK — no violations."
    errors = [v for v in violations if v.severity == "error"]
    lines = [f"Data validation: {len(violations)} finding(s) "
             f"({len(errors)} error, {len(violations) - len(errors)} warning):"]
    lines += [f"  {v}" for v in violations]
    return "\n".join(lines)


def has_errors(violations: List[Violation]) -> bool:
    return any(v.severity == "error" for v in violations)


if __name__ == "__main__":
    import sys
    from paths import TRANSACTIONS
    path = sys.argv[1] if len(sys.argv) > 1 else str(TRANSACTIONS)
    df = pd.read_csv(path)
    vs = validate_transactions(df)
    print(format_report(vs))
    sys.exit(1 if has_errors(vs) else 0)
