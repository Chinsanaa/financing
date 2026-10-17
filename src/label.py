"""Rule-based pre-labeling: match merchants against merchant_rules patterns."""
import pandas as pd


def _match_merchant(merchant: str, rules: dict, sorted_patterns: list) -> str | None:
    """Match a single merchant string against rules.

    Semantics (unchanged): exact match first, then longest-pattern-first
    substring match. Returns the category, or None if nothing matched.

    Note: sorted_patterns is produced by a stable sort on pattern length, so
    two patterns of equal length are tried in their original dict/list
    order, not by any explicit specificity rule — see merchant_categories.py
    module docstring.
    """
    # Try exact match first
    if merchant in rules:
        return rules[merchant]

    # Try substring match — longest pattern first to avoid partial overlaps
    for pattern, category in sorted_patterns:
        if pattern in merchant:
            return category

    return None


def apply_merchant_rules(df: pd.DataFrame, rules: dict) -> pd.DataFrame:
    """
    Apply merchant rules to transactions.

    Returns DataFrame with added columns:
    - 'category': assigned category (or NaN if no rule matched)
    - 'labeled': True if rule matched, False if unlabeled

    Optimized: patterns are sorted once (not per-row), and matching runs only
    on unique merchant strings, then maps back onto the full column. Output is
    identical to the original row-by-row implementation.
    """
    df = df.copy()

    # Sort patterns once — longest first (same tie-breaking as before).
    sorted_patterns = sorted(rules.items(), key=lambda x: len(x[0]), reverse=True)

    # Normalize once, then match only unique merchants (real data repeats them).
    merchant_series = df['merchant'].astype(str).str.strip().str.lower()
    unique_merchants = merchant_series.unique()
    match_cache = {
        m: _match_merchant(m, rules, sorted_patterns) for m in unique_merchants
    }

    matched = merchant_series.map(match_cache)
    df['category'] = matched.where(matched.notna(), pd.NA)
    df['labeled'] = matched.notna().to_numpy()

    return df
