"""Detect recurring/subscription merchants from a user's transaction history.

Pure function over a DataFrame — no DB access here (that lives in
backend/routes/subscriptions.py, matching the rest of the pipeline: src/
holds transformation logic, backend/routes/ holds the Supabase queries).
"""
import pandas as pd

MIN_OCCURRENCES = 3
LOOKBACK_DAYS = 183  # ~6 months
MONTHLY_INTERVAL_DAYS = 30
WEEKLY_INTERVAL_DAYS = 7
INTERVAL_TOLERANCE_DAYS = 5
AMOUNT_VARIANCE_TOLERANCE = 0.15  # median absolute deviation as a fraction of the median


def _cadence_for_intervals(median_interval_days: float) -> str:
    """Classify a merchant's median day-gap between transactions as a cadence."""
    if abs(median_interval_days - MONTHLY_INTERVAL_DAYS) <= INTERVAL_TOLERANCE_DAYS:
        return "monthly"
    if abs(median_interval_days - WEEKLY_INTERVAL_DAYS) <= INTERVAL_TOLERANCE_DAYS:
        return "weekly"
    return "irregular"


def detect_recurring_merchants(df: pd.DataFrame, now: pd.Timestamp = None) -> pd.DataFrame:
    """Find merchants with a regular monthly/weekly cadence and stable amount.

    Args:
        df: transactions with columns 'merchant', 'amount', 'timestamp',
            and optionally 'category_id'. Not required to be pre-filtered
            to the lookback window; that's applied here.
        now: reference "today" for the lookback window (defaults to
            the max timestamp in df, so this works on historical fixtures too).

    Returns:
        DataFrame with columns: merchant, category_id, cadence,
        typical_amount, last_seen, occurrences — one row per detected
        recurring merchant, sorted by typical_amount descending.
    """
    if df.empty:
        return pd.DataFrame(
            columns=["merchant", "category_id", "cadence", "typical_amount", "last_seen", "occurrences"]
        )

    work = df.copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"])
    reference = now or work["timestamp"].max()
    cutoff = reference - pd.Timedelta(days=LOOKBACK_DAYS)
    work = work[work["timestamp"] >= cutoff]

    results = []
    for merchant, group in work.groupby("merchant"):
        if len(group) < MIN_OCCURRENCES:
            continue

        group = group.sort_values("timestamp")
        intervals = group["timestamp"].diff().dt.days.dropna()
        if intervals.empty:
            continue
        median_interval = intervals.median()

        cadence = _cadence_for_intervals(median_interval)
        if cadence == "irregular":
            continue

        median_amount = group["amount"].median()
        if median_amount == 0:
            continue
        amount_deviation = (group["amount"] - median_amount).abs().median()
        if amount_deviation / abs(median_amount) > AMOUNT_VARIANCE_TOLERANCE:
            continue

        category_id = None
        if "category_id" in group.columns:
            mode = group["category_id"].dropna().mode()
            category_id = mode.iloc[0] if not mode.empty else None

        results.append(
            {
                "merchant": merchant,
                "category_id": category_id,
                "cadence": cadence,
                "typical_amount": round(float(median_amount), 2),
                "last_seen": group["timestamp"].max(),
                "occurrences": len(group),
            }
        )

    if not results:
        return pd.DataFrame(
            columns=["merchant", "category_id", "cadence", "typical_amount", "last_seen", "occurrences"]
        )

    return pd.DataFrame(results).sort_values("typical_amount", ascending=False).reset_index(drop=True)
