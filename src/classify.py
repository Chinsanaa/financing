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
from merchant_categories import special_category
from paths import (
    CLASSIFIER,
    MERCHANT_RULES,
    NEEDS_REVIEW,
    PROCESSED,
    TRANSACTIONS,
    TRANSACTIONS_CLASSIFIED,
    VECTORIZER,
)
from feature_engineering import create_hybrid_feature_matrix


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
        desc = str(row['description'])
        merchant_lower = merchant.lower()

        special = special_category(merchant, desc)
        if special is not None:
            df.loc[idx, 'category'] = special
            df.loc[idx, 'confidence'] = 1.0
            df.loc[idx, 'needs_review'] = False
            if 'label_source' in df.columns:
                df.loc[idx, 'label_source'] = 'override'
            continue

        if 'catering' in merchant_lower or '餐饮' in merchant:
            df.loc[idx, 'category'] = 'Eating Out'
            df.loc[idx, 'confidence'] = 1.0
            df.loc[idx, 'needs_review'] = False
            if 'label_source' in df.columns:
                df.loc[idx, 'label_source'] = 'override'
    return df


def load_models() -> Tuple[Optional[object], Optional[object], Optional[dict]]:
    """
    Load classifier artifacts if they exist; return (vectorizer, classifier, config).
    Config indicates whether to use hybrid or legacy features.
    Returns (None, None, None) for rules-only mode.
    """
    if VECTORIZER.exists() and CLASSIFIER.exists():
        vectorizer = joblib.load(VECTORIZER)
        classifier = joblib.load(CLASSIFIER)

        # Load config to determine feature type (hybrid or legacy)
        config_path = VECTORIZER.parent / 'vectorizer_config.pkl'
        config = {'use_hybrid': False}  # Default to legacy
        if config_path.exists():
            config = joblib.load(config_path)

        return vectorizer, classifier, config
    return None, None, None


def classify_all(
    df,
    vectorizer=None,
    classifier=None,
    config=None,
    confidence_threshold=0.7,
    rules=None,
):
    """Classify transactions via a two-stage design: rules first, model on the residual.

    Stage 1 — high-precision merchant rules (and description overrides) assign a
    trusted category to known merchants. Stage 2 — the model predicts the rest.

    Because the model is badly overconfident on merchants it has never seen
    (see docs/FULL_AUDIT.md Phase 4: even 0.9+ confidence is only ~89% accurate
    on unseen merchants, ECE 0.184), a model prediction on a no-rule merchant is
    treated as a *suggestion routed to review*, not an auto-applied label. The
    `confidence_threshold` no longer gates auto-acceptance; it is kept for
    ranking the review queue. `label_source` records how each row was labeled:
    'rule', 'override', 'model' (needs review), or 'none' (rules-only fallback).

    When vectorizer/classifier are None (no trained model yet), uses rules-only
    mode: matched merchants get their rule category; others → Other, flagged for review.
    """
    df = df.copy()

    if config is None:
        config = {'use_hybrid': False}

    if vectorizer is not None and classifier is not None:
        # Use hybrid feature engineering if config indicates
        if config.get('use_hybrid', False):
            from feature_engineering import extract_numeric_features

            # Extract numeric features
            numeric_features, valid_indices = extract_numeric_features(df)
            df_valid = df.iloc[valid_indices].copy()

            # Create hybrid feature matrix with desc and merch vectorizers
            X = create_hybrid_feature_matrix(df_valid, vectorizer['desc'], vectorizer['merch'], numeric_features)

            # Predict on valid rows only
            predictions = classifier.predict(X)
            probabilities = classifier.predict_proba(X).max(axis=1)

            # Initialize all rows with 'Other' and 0.0 confidence
            df['category'] = 'Other'
            df['confidence'] = 0.0

            # Update only the valid rows with predictions
            df.loc[df_valid.index, 'category'] = predictions
            df.loc[df_valid.index, 'confidence'] = probabilities
            df['label_source'] = 'model'
        else:
            # Legacy vectorizer: single object
            df['text'] = df.apply(
                lambda row: clean_text(row['merchant'], row['description']),
                axis=1,
            )
            X = vectorize(df['text'].tolist(), vectorizer)
            df['category'] = classifier.predict(X)
            df['confidence'] = classifier.predict_proba(X).max(axis=1)
            df['label_source'] = 'model'
    else:
        df['category'] = 'Other'
        df['confidence'] = 0.0
        df['label_source'] = 'none'

    if rules:
        ruled = apply_merchant_rules(df, rules)
        matched = ruled['labeled'] == True
        df.loc[matched, 'category'] = ruled.loc[matched, 'category']
        df.loc[matched, 'confidence'] = 1.0
        df.loc[matched, 'label_source'] = 'rule'

    df = apply_description_overrides(df)
    df = normalize_categories(df)

    # Two-stage routing: only rule/override rows are trusted. Model suggestions
    # on unseen (no-rule) merchants — and rules-only-mode fallbacks — go to review.
    df['needs_review'] = ~df['label_source'].isin(['rule', 'override'])
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
    vectorizer, classifier, config = load_models()
    rules = load_merchant_rules(str(MERCHANT_RULES))

    print(f"\n1. Loaded {len(df)} transactions")
    if classifier is not None:
        feature_type = "HYBRID (semantic-weighted)" if config.get('use_hybrid', False) else "LEGACY (combined text)"
        print(f"2. Loaded trained classifier ({feature_type})")
    else:
        print("2. No classifier found — rules-only mode (run bootstrap.py to train)")
    print(f"3. Loaded {len(rules)} merchant rules")

    print("\n4. Classifying all transactions...")
    df_classified = classify_all(df, vectorizer, classifier, config=config, rules=rules)

    print("\n4. CLASSIFICATION RESULTS:")
    for cat, count in df_classified['category'].value_counts().items():
        avg_conf = df_classified[df_classified['category'] == cat]['confidence'].mean()
        print(f"   {cat:30s}: {count:3d} transactions (avg confidence: {avg_conf:.1%})")

    needs_review = df_classified[df_classified['needs_review']]
    rule_covered = (~df_classified['needs_review']).sum()
    print(f"\n4b. TRUSTED (rule/override): {rule_covered}  |  "
          f"MODEL SUGGESTIONS ROUTED TO REVIEW (unseen merchants): {len(needs_review)}")

    print(f"\n5. Mean confidence: {df_classified['confidence'].mean():.1%}")

    save_classification_outputs(df_classified)
    print(f"\n6. Saved to {TRANSACTIONS_CLASSIFIED}")

    print(f"\n{'=' * 70}")
    print(f"Stage 6 Complete! All {len(df_classified)} transactions classified")
    print("=" * 70)
