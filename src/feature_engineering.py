"""Hybrid feature engineering: semantic-weighted text + contextual numeric features.

Goal: Reduce merchant overfitting by:
1. Separating merchant (0.3x weight) from description (1.0x weight) features
2. Adding contextual features (hour, day, amount range)
3. Enabling model to learn patterns ("restaurants at lunch") not memorization ("Holy Bagel")
"""
import sys
from pathlib import Path
import re

import pandas as pd
import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, str(Path(__file__).parent))
from segment import column_or_blank, tokenize

# Tunable hyperparameter
MERCHANT_WEIGHT = 0.3  # How much merchant features are downweighted vs description


NUMERIC_COLUMNS = [
    'hour_of_day',
    'day_of_week',
    'is_lunch_time',
    'is_dinner_time',
    'amount_bucket',
    'merchant_frequency_norm',
]
N_AMOUNT_BUCKETS = 10


def _clean_numeric_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Copy of df restricted to rows with a parseable timestamp and amount,
    with both columns converted (datetime / float)."""
    df = df.dropna(subset=['timestamp', 'amount']).copy()
    # Robust across pandas versions: pandas 3.0 gives string columns dtype
    # 'str', not 'object', so an == 'object' check silently skips conversion.
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    return df.dropna(subset=['timestamp', 'amount'])


def fit_numeric_stats(df: pd.DataFrame) -> dict:
    """Learn the dataset-level statistics the numeric features depend on.

    Fit once on TRAINING rows and saved with the model, so a transaction gets
    the same features at prediction time no matter what else is in the batch
    (previously amount buckets, merchant frequency and the 0-1 scaling were
    recomputed from whatever rows were being classified together).

    Returns {} when the columns are missing (features degrade to zeros).
    """
    if 'timestamp' not in df.columns or 'amount' not in df.columns:
        return {}
    clean = _clean_numeric_rows(df)
    if clean.empty:
        return {}

    _, edges = pd.qcut(clean['amount'], q=N_AMOUNT_BUCKETS, retbins=True, duplicates='drop')
    counts = clean['merchant'].astype(str).value_counts()
    stats = {
        'amount_edges': [float(e) for e in edges],
        'merchant_counts': {k: int(v) for k, v in counts.items()},
        'max_merchant_count': int(counts.max()),
    }
    features, _ = extract_numeric_features(df, stats)
    stats['col_min'] = features.min().astype(float).to_dict()
    stats['col_max'] = features.max().astype(float).to_dict()
    return stats


def extract_numeric_features(df: pd.DataFrame, stats: dict | None = None) -> tuple[pd.DataFrame, pd.Index]:
    """
    Extract contextual numeric features from transactions.

    Returns (features, index) where features has columns:
    - amount_bucket: Quantized amount (0-9 by percentiles)
    - hour_of_day: 0-23 (from timestamp column)
    - day_of_week: 0-6 (Monday=0, Sunday=6)
    - is_lunch_time: Binary flag for lunch hours (11am-3pm)
    - is_dinner_time: Binary flag for dinner hours (6pm-10pm)
    - merchant_frequency_norm: log-scaled merchant frequency (0-1)
    and index holds the df index labels of the rows kept.

    `stats` (from fit_numeric_stats on the training data) fixes the amount
    bucket edges and merchant frequencies. Without it (models trained before
    stats were saved) both are computed from `df` itself, the legacy
    per-batch behaviour.

    If timestamp or amount columns are missing, returns zero-valued features
    for all rows (graceful degradation: the classifier still works on text).
    """
    # Graceful degradation: if required columns are missing (e.g., from web UI),
    # return zero features with correct shape instead of crashing.
    if 'timestamp' not in df.columns or 'amount' not in df.columns:
        zeros = pd.DataFrame(0.0, index=df.index, columns=NUMERIC_COLUMNS, dtype=np.float32)
        return zeros.reset_index(drop=True), df.index

    df = _clean_numeric_rows(df)

    hour = df['timestamp'].dt.hour
    df['hour_of_day'] = hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    # Meal windows (user preferences): lunch 11:00-14:59, dinner 18:00-21:59.
    df['is_lunch_time'] = ((hour >= 11) & (hour < 15)).astype(np.float32)
    df['is_dinner_time'] = ((hour >= 18) & (hour < 22)).astype(np.float32)

    merchants = df['merchant'].astype(str)
    if stats:
        # Same bins pd.qcut produced at training time: (e_i, e_i+1], lowest
        # edge inclusive; values outside the training range clip to the ends.
        inner = np.asarray(stats['amount_edges'][1:-1])
        n_bins = max(len(stats['amount_edges']) - 1, 1)
        df['amount_bucket'] = np.clip(
            np.searchsorted(inner, df['amount'].to_numpy(), side='left'), 0, n_bins - 1)
        freq = merchants.map(stats['merchant_counts']).fillna(0)
        max_freq = stats['max_merchant_count']
    else:
        df['amount_bucket'] = pd.qcut(df['amount'], q=N_AMOUNT_BUCKETS, labels=False, duplicates='drop')
        freq = merchants.map(merchants.value_counts())
        max_freq = freq.max()
    # Log scale so a daily merchant doesn't dwarf everything else.
    df['merchant_frequency_norm'] = np.log1p(freq) / np.log1p(max_freq)

    numeric_features = df[NUMERIC_COLUMNS].fillna(0).astype(np.float32)
    return numeric_features, df.index


def clean_description_only(merchant: str, description: str) -> str:
    """
    Clean description text only (merchant excluded).

    This is used for high-weight description features.
    """
    if pd.isna(description) or not description:
        return ""

    d = str(description).strip()
    if d == '/':  # WeChat blank marker
        return ""

    # Remove long order numbers
    d = re.sub(r'\d{10,}', '', d)
    d = re.sub(r'\bOrder\s+No\.\s*\d+', '', d, flags=re.IGNORECASE)

    # Lowercase English, preserve Chinese
    result = []
    for char in d:
        if '一' <= char <= '鿿':  # Chinese character range
            result.append(char)
        elif char.isalpha():
            result.append(char.lower())
        else:
            result.append(char)

    return ''.join(result).strip()


def clean_merchant_only(merchant: str) -> str:
    """
    Clean merchant text only (description excluded).

    This is used for low-weight merchant features (0.3x).
    """
    if pd.isna(merchant) or not merchant:
        return ""

    m = str(merchant).strip()
    # Remove long order numbers
    m = re.sub(r'\d{10,}', '', m)

    # Lowercase English, preserve Chinese
    result = []
    for char in m:
        if '一' <= char <= '鿿':  # Chinese range
            result.append(char)
        elif char.isalpha():
            result.append(char.lower())
        else:
            result.append(char)

    return ''.join(result).strip()


def build_hybrid_vectorizers(
    desc_texts: list,
    merch_texts: list,
    max_features: int = 3000
) -> tuple:
    """
    Build separate TF-IDF vectorizers for description and merchant text.

    Args:
        desc_texts: List of description strings
        merch_texts: List of merchant strings
        max_features: Maximum TF-IDF features for each vectorizer

    Returns:
        (desc_vectorizer, merch_vectorizer) - both fitted TfidfVectorizer instances
    """
    # Description vectorizer (full weight, 1.0x)
    desc_vectorizer = TfidfVectorizer(
        tokenizer=tokenize,
        max_features=max_features,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.8,
        lowercase=False,
        dtype=np.float32
    )
    desc_vectorizer.fit(desc_texts)

    # Merchant vectorizer (downweighted, 0.3x)
    merch_vectorizer = TfidfVectorizer(
        tokenizer=tokenize,
        max_features=max_features // 2,  # Use fewer features for merchant (less important)
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.8,
        lowercase=False,
        dtype=np.float32
    )
    merch_vectorizer.fit(merch_texts)

    return desc_vectorizer, merch_vectorizer


def create_hybrid_feature_matrix(
    df: pd.DataFrame,
    desc_vectorizer: TfidfVectorizer,
    merch_vectorizer: TfidfVectorizer,
    numeric_features: pd.DataFrame = None,
    numeric_stats: dict | None = None,
) -> sparse.csr_matrix:
    """
    Create hybrid feature matrix combining:
    - Description TF-IDF (weight: 1.0)
    - Merchant TF-IDF (weight: 0.3)
    - Numeric contextual features (6 features):
      * hour_of_day (0-23)
      * day_of_week (0-6, Monday=0)
      * is_lunch_time (binary, 11am-3pm)
      * is_dinner_time (binary, 6pm-10pm)
      * amount_bucket (0-9 quantiles)
      * merchant_frequency_norm (0-1, log scale)

    Args:
        df: DataFrame with 'merchant' and 'description' columns
        desc_vectorizer: Fitted description vectorizer
        merch_vectorizer: Fitted merchant vectorizer
        numeric_features: Optional DataFrame with numeric features

    Returns:
        Sparse CSR matrix of combined features
    """
    # Clean and vectorize description (full weight)
    desc_texts = [clean_description_only('', d) for d in column_or_blank(df, 'description')]
    X_desc = desc_vectorizer.transform(desc_texts)

    # Clean and vectorize merchant (downweighted)
    merch_texts = [clean_merchant_only(m) for m in column_or_blank(df, 'merchant')]
    X_merch = merch_vectorizer.transform(merch_texts)
    X_merch = X_merch * MERCHANT_WEIGHT  # Apply downweighting

    # Combine text features
    X_combined = sparse.hstack([X_desc, X_merch])

    # Add numeric features if provided
    if numeric_features is not None and len(numeric_features) > 0:
        # Normalize numeric features to 0-1, with the training-time range when
        # known (stable across batches); else the legacy per-batch range.
        if numeric_stats and 'col_min' in numeric_stats:
            lo = pd.Series(numeric_stats['col_min'])[numeric_features.columns]
            hi = pd.Series(numeric_stats['col_max'])[numeric_features.columns]
            numeric_features_norm = ((numeric_features - lo) / (hi - lo + 1e-8)).clip(0, 1)
        else:
            lo, hi = numeric_features.min(), numeric_features.max()
            numeric_features_norm = (numeric_features - lo) / (hi - lo + 1e-8)
        # Convert to sparse format and concatenate
        X_numeric = sparse.csr_matrix(numeric_features_norm.values, dtype=np.float32)
        X_combined = sparse.hstack([X_combined, X_numeric])

    return X_combined.astype(np.float32)
