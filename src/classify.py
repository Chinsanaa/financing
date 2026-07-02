"""Apply trained classifier to all transactions."""
import pandas as pd
import joblib
from pathlib import Path
import sys
from typing import Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from categories import CATEGORY_NORMALIZE, ML_CATEGORIES
from segment import clean_text, vectorize
from label import load_merchant_rules, apply_merchant_rules
from paths import (
    CLASSIFIER,
    MERCHANT_RULES,
    NEEDS_REVIEW,
    PROCESSED,
    TRANSACTIONS,
    TRANSACTIONS_CLASSIFIED,
    VECTORIZER,
)


def normalize_categories(df: pd.DataFrame) -> pd.DataFrame:
    """Map legacy/extra rule categories to ML categories."""
    df = df.copy()
    df['category'] = df['category'].replace(CATEGORY_NORMALIZE)
    unknown = ~df['category'].isin(ML_CATEGORIES)
    if unknown.any():
        df.loc[unknown, 'category'] = 'Other'
    return df


def apply_description_overrides(df: pd.DataFrame) -> pd.DataFrame:
    """Override categories using merchant/description patterns."""
    df = df.copy()
    for idx, row in df.iterrows():
        merchant = str(row['merchant'])
        desc = str(row['description']).lower()
        merchant_lower = merchant.lower()

        if 'catering' in merchant_lower or '餐饮' in merchant:
            df.loc[idx, 'category'] = 'Eating Out'
            df.loc[idx, 'confidence'] = 1.0
            df.loc[idx, 'needs_review'] = False
    return df


def load_models() -> Tuple[Optional[object], Optional[object]]:
    """Load classifier artifacts if they exist; return (None, None) for rules-only mode."""
    if VECTORIZER.exists() and CLASSIFIER.exists():
        return joblib.load(VECTORIZER), joblib.load(CLASSIFIER)
    return None, None


def classify_all(
    df,
    vectorizer=None,
    classifier=None,
    confidence_threshold=0.7,
    rules=None,
):
    """Classify transactions via ML model and/or merchant rules.

    When vectorizer/classifier are None (no trained model yet), uses rules-only
    mode: matched merchants get their rule category; others → Other at 0% confidence.
    """
    df = df.copy()
    df['text'] = df.apply(
        lambda row: clean_text(row['merchant'], row['description']),
        axis=1,
    )

    if vectorizer is not None and classifier is not None:
        X = vectorize(df['text'].tolist(), vectorizer)
        df['category'] = classifier.predict(X)
        df['confidence'] = classifier.predict_proba(X).max(axis=1)
        df['needs_review'] = df['confidence'] < confidence_threshold
    else:
        df['category'] = 'Other'
        df['confidence'] = 0.0
        df['needs_review'] = True

    if rules:
        ruled = apply_merchant_rules(df, rules)
        matched = ruled['labeled'] == True
        df.loc[matched, 'category'] = ruled.loc[matched, 'category']
        df.loc[matched, 'confidence'] = 1.0
        df.loc[matched, 'needs_review'] = False

    df = apply_description_overrides(df)
    df = normalize_categories(df)
    return df


def save_classification_outputs(df_classified: pd.DataFrame) -> None:
    """Write classified transactions and manual-review queue."""
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df_classified.to_csv(TRANSACTIONS_CLASSIFIED, index=False)

    needs_review = df_classified[df_classified['needs_review']]
    if len(needs_review) > 0:
        needs_review.to_csv(NEEDS_REVIEW, index=False)
    elif NEEDS_REVIEW.exists():
        NEEDS_REVIEW.unlink()


if __name__ == '__main__':
    print("=" * 70)
    print("STAGE 6: CLASSIFY ALL TRANSACTIONS")
    print("=" * 70)

    df = pd.read_csv(TRANSACTIONS)
    vectorizer, classifier = load_models()
    rules = load_merchant_rules(str(MERCHANT_RULES))

    print(f"\n1. Loaded {len(df)} transactions")
    if classifier is not None:
        print("2. Loaded trained classifier")
    else:
        print("2. No classifier found — rules-only mode (run bootstrap.py to train)")
    print(f"3. Loaded {len(rules)} merchant rules")

    print("\n4. Classifying all transactions...")
    df_classified = classify_all(df, vectorizer, classifier, rules=rules)

    print("\n4. CLASSIFICATION RESULTS:")
    for cat, count in df_classified['category'].value_counts().items():
        avg_conf = df_classified[df_classified['category'] == cat]['confidence'].mean()
        print(f"   {cat:30s}: {count:3d} transactions (avg confidence: {avg_conf:.1%})")

    needs_review = df_classified[df_classified['needs_review']]
    print(f"\n4b. LOW-CONFIDENCE ITEMS (confidence < 0.70): {len(needs_review)}")

    print(f"\n5. Mean confidence: {df_classified['confidence'].mean():.1%}")

    save_classification_outputs(df_classified)
    print(f"\n6. Saved to {TRANSACTIONS_CLASSIFIED}")

    print(f"\n{'=' * 70}")
    print(f"Stage 6 Complete! All {len(df_classified)} transactions classified")
    print("=" * 70)
