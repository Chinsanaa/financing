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
from segment import tokenize

# Tunable hyperparameter
MERCHANT_WEIGHT = 0.3  # How much merchant features are downweighted vs description


def extract_numeric_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract contextual numeric features from transactions.

    Returns DataFrame with:
    - amount_bucket: Quantized amount (0-9 by percentiles)
    - hour_of_day: 0-23 (from time column)
    - day_of_week: 0-6 (Monday=0, Sunday=6)
    - is_lunch_time: Binary flag for lunch hours (11am-3pm)
    - is_dinner_time: Binary flag for dinner hours (6pm-10pm)
    - merchant_frequency: How often this merchant appears in dataset

    Meal time windows (user preferences):
    - Lunch: 11:00-14:59 (11am to 3pm)
    - Dinner: 18:00-21:59 (6pm to 10pm)

    Skips rows with missing time or amount (as per user decision).
    """
    df = df.copy()

    # Filter out rows with missing critical values
    df = df.dropna(subset=['time', 'amount'])

    # Convert time to datetime unless it already is one.
    # (Robust across pandas versions: pandas 3.0 gives string columns dtype
    # 'str', not 'object', so an == 'object' check silently skips conversion.)
    if not pd.api.types.is_datetime64_any_dtype(df['time']):
        df['time'] = pd.to_datetime(df['time'], errors='coerce')

    # Ensure amount is numeric
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

    # Drop any rows that failed conversion
    df = df.dropna(subset=['time', 'amount'])

    # Hour of day
    df['hour_of_day'] = df['time'].dt.hour

    # Day of week (0=Monday, 6=Sunday)
    df['day_of_week'] = df['time'].dt.dayofweek

    # Meal time flags (user preferences)
    # Lunch: 11am to 3pm (11:00-14:59, so hour 11-14)
    df['is_lunch_time'] = ((df['hour_of_day'] >= 11) & (df['hour_of_day'] < 15)).astype(np.float32)

    # Dinner: 6pm to 10pm (18:00-21:59, so hour 18-21)
    df['is_dinner_time'] = ((df['hour_of_day'] >= 18) & (df['hour_of_day'] < 22)).astype(np.float32)

    # Amount bucket: discretize by percentiles (0-9 buckets)
    # This is normalized within the entire dataset (not per-category, to preserve generalization)
    df['amount_bucket'] = pd.qcut(df['amount'], q=10, labels=False, duplicates='drop')

    # Merchant frequency: how often each merchant appears
    merchant_counts = df['merchant'].value_counts()
    df['merchant_frequency'] = df['merchant'].map(merchant_counts)

    # Normalize merchant frequency to 0-1 scale (log scale to avoid extreme values)
    max_freq = df['merchant_frequency'].max()
    df['merchant_frequency_norm'] = np.log1p(df['merchant_frequency']) / np.log1p(max_freq)

    # Return only the numeric features we care about
    numeric_features = df[[
        'hour_of_day',
        'day_of_week',
        'is_lunch_time',
        'is_dinner_time',
        'amount_bucket',
        'merchant_frequency_norm'
    ]].fillna(0).astype(np.float32)

    return numeric_features, df.index  # Return both features and indices for alignment


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
    numeric_features: pd.DataFrame = None
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
    desc_texts = df.apply(
        lambda row: clean_description_only(row.get('merchant', ''), row.get('description', '')),
        axis=1
    ).tolist()
    X_desc = desc_vectorizer.transform(desc_texts)

    # Clean and vectorize merchant (downweighted)
    merch_texts = df.apply(
        lambda row: clean_merchant_only(row.get('merchant', '')),
        axis=1
    ).tolist()
    X_merch = merch_vectorizer.transform(merch_texts)
    X_merch = X_merch * MERCHANT_WEIGHT  # Apply downweighting

    # Combine text features
    X_combined = sparse.hstack([X_desc, X_merch])

    # Add numeric features if provided
    if numeric_features is not None and len(numeric_features) > 0:
        # Normalize numeric features to 0-1
        numeric_features_norm = (numeric_features - numeric_features.min()) / (
            numeric_features.max() - numeric_features.min() + 1e-8
        )
        # Convert to sparse format and concatenate
        X_numeric = sparse.csr_matrix(numeric_features_norm.values, dtype=np.float32)
        X_combined = sparse.hstack([X_combined, X_numeric])

    return X_combined.astype(np.float32)


if __name__ == '__main__':
    print("Feature Engineering Module")
    print("=" * 70)
    print("\nThis module provides:")
    print("  - extract_numeric_features(): Extract hour, day, amount, merchant frequency")
    print("  - clean_description_only(): Description text without merchant")
    print("  - clean_merchant_only(): Merchant name only")
    print("  - build_hybrid_vectorizers(): Separate TF-IDF for desc (1.0x) + merchant (0.3x)")
    print("  - create_hybrid_feature_matrix(): Combine all into one matrix")
    print("\nUsage:")
    print("  from feature_engineering import create_hybrid_feature_matrix, ...")
    print("  numeric_features, _ = extract_numeric_features(df)")
    print("  desc_vec, merch_vec = build_hybrid_vectorizers(desc_texts, merch_texts)")
    print("  X = create_hybrid_feature_matrix(df, desc_vec, merch_vec, numeric_features)")
