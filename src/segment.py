"""Text cleaning, tokenization, and TF-IDF vectorization."""
import re
import jieba
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

# Production hyperparameters.
# class_weight='balanced' addresses the ~40:1 class imbalance (Eating Out vs Utilities).
# C=1.0: the earlier C=10 was tuned on stratified CV, which leaks merchants across
# folds (see docs/FULL_AUDIT.md Phase 4). Under honest GroupKFold-by-merchant CV,
# C=1.0 strictly dominates C=10 (accuracy +8.9pts, F1-macro +0.106) while leaving
# stratified accuracy essentially unchanged — less overfitting generalizes better
# to unseen merchants.
LR_HYPERPARAMS = {
    'max_iter': 1000,
    'solver': 'lbfgs',
    'class_weight': 'balanced',
    'C': 1.0,
    'random_state': 42
}

# ============================================================================
# STAGE 2: TEXT CLEANING
# ============================================================================

def clean_text(merchant: str, description: str) -> str:
    r"""
    Clean and combine merchant + description for tokenization.

    Rules:
    - Strip long numeric strings (order numbers: \d{10,})
    - Strip "/" (WeChat blank descriptions)
    - Combine merchant + description
    - Leave Chinese as-is for jieba, lowercase English portions
    """
    parts = []

    # Clean merchant
    if pd.notna(merchant) and str(merchant).strip():
        m = str(merchant).strip()
        m = re.sub(r'\d{10,}', '', m)  # Remove long order numbers
        if m:
            parts.append(m)

    # Clean description
    if pd.notna(description) and str(description).strip():
        d = str(description).strip()
        if d != '/':  # Skip WeChat "/" placeholder
            d = re.sub(r'\d{10,}', '', d)  # Remove long order numbers
            d = re.sub(r'\bOrder\s+No\.\s*\d+', '', d, flags=re.IGNORECASE)
            if d.strip():
                parts.append(d.strip())

    combined = ' '.join(parts)

    # Lowercase English, leave Chinese
    result = []
    for char in combined:
        if '一' <= char <= '鿿':  # Chinese character range
            result.append(char)
        elif char.isalpha():
            result.append(char.lower())
        else:
            result.append(char)

    return ''.join(result).strip()


# ============================================================================
# STAGE 4: TOKENIZATION + TF-IDF VECTORIZATION
# ============================================================================

def tokenize(text: str) -> list:
    """
    Tokenize mixed Chinese/English text.

    - Runs jieba on Chinese portions
    - Splits English on spaces/punctuation
    - Returns list of tokens
    """
    if not text or pd.isna(text):
        return []

    text = str(text).strip()
    if not text:
        return []

    # Use jieba to segment (handles both Chinese and passes through English)
    tokens = jieba.cut(text, cut_all=False)

    # Filter out single characters and very short tokens (noise)
    tokens = [t.strip() for t in tokens if len(t.strip()) > 1]

    return tokens


def build_vectorizer(texts: list, max_features: int = 3000) -> TfidfVectorizer:
    """
    Fit TF-IDF vectorizer on training texts.

    Args:
        texts: list of strings to fit on
        max_features: max number of features to extract (default 3000 for better coverage)

    Returns:
        Fitted TfidfVectorizer instance
    """
    vectorizer = TfidfVectorizer(
        tokenizer=tokenize,
        max_features=max_features,
        ngram_range=(1, 2),  # Add bigrams: capture compound merchant names (便利店, 外卖平台)
        min_df=2,  # Ignore tokens that appear in < 2 documents
        max_df=0.8,  # Ignore tokens that appear in > 80% of documents
        lowercase=False  # We handle case in tokenize()
    )
    vectorizer.fit(texts)
    return vectorizer


def vectorize(texts: list, vectorizer: TfidfVectorizer):
    """Transform texts using fitted vectorizer."""
    return vectorizer.transform(texts)
