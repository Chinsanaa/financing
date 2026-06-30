"""Text cleaning, tokenization, and TF-IDF vectorization."""
import re
import jieba
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import joblib
from pathlib import Path

# Production hyperparameters (tuned via grid search in previous audit)
# class_weight='balanced' addresses 40:1 class imbalance (Eating Out vs Utilities)
# C=10 reduces regularization to fit harder on small categories (Shopping, Transfers & Gifts)
LR_HYPERPARAMS = {
    'max_iter': 1000,
    'solver': 'lbfgs',
    'class_weight': 'balanced',
    'C': 10,
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
    if pd.notna(merchant) and merchant.strip():
        m = str(merchant).strip()
        m = re.sub(r'\d{10,}', '', m)  # Remove long order numbers
        if m:
            parts.append(m)

    # Clean description
    if pd.notna(description) and description.strip():
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


def apply_cleaning(df: pd.DataFrame) -> pd.DataFrame:
    """Add cleaned 'text' column to dataframe."""
    df = df.copy()
    df['text'] = df.apply(
        lambda row: clean_text(row['merchant'], row['description']),
        axis=1
    )
    return df


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


def save_vectorizer(vectorizer: TfidfVectorizer, path: str) -> None:
    """Save fitted vectorizer to disk."""
    joblib.dump(vectorizer, path)
    print(f"Saved vectorizer to {path}")


def load_vectorizer(path: str) -> TfidfVectorizer:
    """Load vectorizer from disk."""
    return joblib.load(path)


def vectorize(texts: list, vectorizer: TfidfVectorizer):
    """Transform texts using fitted vectorizer."""
    return vectorizer.transform(texts)


if __name__ == '__main__':
    # Test Stage 2: Text Cleaning
    print("="*70)
    print("STAGE 2: TEXT CLEANING")
    print("="*70)

    df = pd.read_csv('data/processed/transactions.csv')
    df_clean = apply_cleaning(df)

    print("\nBefore/After Examples:")
    print("-" * 70)

    # Write to file to avoid console encoding issues
    with open('_cleaning_sample.txt', 'w', encoding='utf-8') as f:
        for i in range(min(10, len(df))):
            merchant = df.iloc[i]['merchant']
            desc = df.iloc[i]['description']
            cleaned = df_clean.iloc[i]['text']
            f.write(f"\n{i+1}. Merchant: {merchant}\n")
            f.write(f"   Description: {desc[:60]}\n")
            f.write(f"   Cleaned: {cleaned[:70]}\n")

    # Save cleaned data
    df_clean.to_csv('data/processed/transactions_cleaned.csv', index=False)
    print(f"\n\nSaved cleaned data to data/processed/transactions_cleaned.csv")

    # Test Stage 4: Tokenization
    print("\n" + "="*70)
    print("STAGE 4: TOKENIZATION & VECTORIZATION (preview)")
    print("="*70)

    with open('_tokenization_sample.txt', 'w', encoding='utf-8') as f:
        f.write("\nSample tokens from first 5 transactions:\n")
        for i in range(min(5, len(df_clean))):
            text = df_clean.iloc[i]['text']
            tokens = tokenize(text)
            f.write(f"\n{i+1}. Text: {text[:60]}\n")
            f.write(f"   Tokens: {tokens}\n")

    print("Sample output written to _cleaning_sample.txt and _tokenization_sample.txt")
