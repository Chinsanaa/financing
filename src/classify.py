"""Apply trained classifier to all transactions."""
import json
import numpy as np
import pandas as pd
import joblib
from dataclasses import dataclass, field
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
    ENSEMBLE_CONFIG,
    MERCHANT_RULES,
    NEEDS_REVIEW,
    PROCESSED,
    SEMANTIC_CALIBRATOR,
    TFIDF_CALIBRATOR,
    TRANSACTIONS,
    TRANSACTIONS_CLASSIFIED,
    VECTORIZER,
)
from feature_engineering import create_hybrid_feature_matrix


def normalize_categories(df: pd.DataFrame, valid_categories: list = None, catch_all: str = 'Other') -> pd.DataFrame:
    """Map legacy/extra rule categories to valid categories.

    Args:
        df: transactions dataframe
        valid_categories: list of allowed category names (defaults to ML_CATEGORIES for backward compat)
        catch_all: category name for unmapped transactions (usually 'Other')
    """
    if valid_categories is None:
        valid_categories = ML_CATEGORIES

    df = df.copy()
    df['category'] = df['category'].replace(CATEGORY_NORMALIZE)
    unknown = ~df['category'].isin(valid_categories)
    if unknown.any():
        df.loc[unknown, 'category'] = catch_all
    return df


def _override_category(merchant: str, desc: str) -> Optional[str]:
    """Resolve the override category for one (merchant, description) pair.

    Precedence (unchanged): special_category() wins; otherwise a
    'catering'/'餐饮' merchant match → Eating Out; otherwise None.
    """
    special = special_category(merchant, desc)
    if special is not None:
        return special
    if 'catering' in merchant.lower() or '餐饮' in merchant:
        return 'Eating Out'
    return None


def apply_description_overrides(df: pd.DataFrame) -> pd.DataFrame:
    """Override categories using merchant/description patterns.

    Optimized: overrides are resolved once per unique (merchant, description)
    pair and applied with vectorized masks instead of row-by-row iteration.
    Output is identical to the original implementation.
    """
    df = df.copy()

    merchants = df['merchant'].astype(str)
    descs = df['description'].astype(str)
    pairs = pd.Series(list(zip(merchants, descs)), index=df.index)

    # Resolve each distinct pair once.
    cache = {pair: _override_category(pair[0], pair[1]) for pair in set(pairs)}
    override_cat = pairs.map(cache)
    mask = override_cat.notna()

    if mask.any():
        df.loc[mask, 'category'] = override_cat[mask]
        df.loc[mask, 'confidence'] = 1.0
        if 'label_source' in df.columns:
            df.loc[mask, 'label_source'] = 'override'
        # Matches original: creates the column if absent (False at override
        # rows, NaN elsewhere); classify_all overwrites it fully afterward.
        df.loc[mask, 'needs_review'] = False

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


@dataclass
class ModelBundle:
    """Everything classify_all needs, loaded once. Any missing artifact is
    None and the corresponding capability degrades gracefully:
    no semantic/calibrators/threshold → today's behavior (all model
    predictions go to review)."""
    vectorizer: Optional[object] = None
    classifier: Optional[object] = None
    config: dict = field(default_factory=lambda: {'use_hybrid': False})
    semantic: Optional[dict] = None      # {'clf','index','encoder','encoder_kind'}
    cal_tfidf: Optional[object] = None
    cal_semantic: Optional[object] = None
    ensemble: Optional[dict] = None      # parsed ensemble_config.json

    @property
    def agreement_ready(self) -> bool:
        """True only when every piece of the graduated-trust gate exists,
        including a data-derived threshold."""
        return (self.classifier is not None
                and self.semantic is not None
                and self.ensemble is not None
                and self.ensemble.get('threshold') is not None)


def load_model_bundle() -> ModelBundle:
    """Load all model artifacts. Never raises; missing pieces are None.

    Note: hybrid vectorizers are saved as tfidf_vectorizer_hybrid.pkl; the
    legacy path is VECTORIZER. We prefer whichever the config points to.
    """
    bundle = ModelBundle()

    vectorizer, classifier, config = load_models()
    # Hybrid artifacts live in a separate file; if config says hybrid but
    # VECTORIZER held a legacy object, prefer the hybrid file when present.
    hybrid_path = PROCESSED / 'tfidf_vectorizer_hybrid.pkl'
    if config and config.get('use_hybrid') and hybrid_path.exists():
        try:
            vectorizer = joblib.load(hybrid_path)
        except Exception:
            pass
    if classifier is None and CLASSIFIER.exists() and hybrid_path.exists():
        # hybrid-only training run: no legacy VECTORIZER file
        try:
            vectorizer = joblib.load(hybrid_path)
            classifier = joblib.load(CLASSIFIER)
            config = {'use_hybrid': True}
        except Exception:
            vectorizer, classifier = None, None

    bundle.vectorizer = vectorizer
    bundle.classifier = classifier
    bundle.config = config or {'use_hybrid': False}

    # Semantic layer (encoder loading never downloads at classification time)
    try:
        from semantic import load_semantic_artifacts
        bundle.semantic = load_semantic_artifacts()
    except Exception:
        bundle.semantic = None

    for attr, path in [('cal_tfidf', TFIDF_CALIBRATOR),
                       ('cal_semantic', SEMANTIC_CALIBRATOR)]:
        if path.exists():
            try:
                setattr(bundle, attr, joblib.load(path))
            except Exception:
                pass

    if ENSEMBLE_CONFIG.exists():
        try:
            bundle.ensemble = json.loads(ENSEMBLE_CONFIG.read_text(encoding='utf-8'))
        except Exception:
            bundle.ensemble = None

    return bundle


def classify_all(
    df,
    vectorizer=None,
    classifier=None,
    config=None,
    confidence_threshold=0.7,
    rules=None,
    bundle: Optional[ModelBundle] = None,
    valid_categories: list = None,
    catch_all: str = 'Other',
):
    """Classify transactions: rules first, then graduated-trust model ensemble.

    Stage 1 — high-precision merchant rules (and description overrides) assign a
    trusted category to known merchants. Stage 2 — the models predict the rest.

    Graduated trust (when semantic artifacts + calibrators + a data-derived
    threshold all exist): a prediction on a no-rule merchant is auto-applied
    ONLY when the TF-IDF model and the semantic (embedding) model AGREE, the
    smaller of their two CALIBRATED confidences clears the threshold, and the
    prediction is not 'Other'. Those rows get label_source='model_agreed'.
    Everything else keeps today's behavior: routed to review as a suggestion
    (raw confidence is badly miscalibrated on unseen merchants — ECE 0.184,
    docs/FULL_AUDIT.md — which is why calibrated agreement is required).

    `label_source` values: 'rule', 'override', 'model_agreed' (trusted),
    'model' (needs review), 'none' (rules-only fallback).

    Backward compatible: with bundle=None (or any semantic artifact missing)
    the routing is identical to the previous version.
    """
    df = df.copy()

    if bundle is not None:
        vectorizer = bundle.vectorizer if vectorizer is None else vectorizer
        classifier = bundle.classifier if classifier is None else classifier
        if config is None:
            config = bundle.config

    if config is None:
        config = {'use_hybrid': False}

    # Defensive: hybrid vectorizers are saved as a dict; honor the artifact
    # shape even if config went stale.
    if isinstance(vectorizer, dict):
        config = dict(config)
        config['use_hybrid'] = True

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

    # --- Graduated trust: calibrated two-model agreement -------------------
    # Requires the full artifact set (semantic model + both calibrators + a
    # data-derived threshold). Missing anything → skip, behavior unchanged.
    if bundle is not None and bundle.agreement_ready and (df['label_source'] == 'model').any():
        try:
            from calibration import apply_calibrator
            from semantic import build_semantic_texts, predict_semantic

            model_mask = (df['label_source'] == 'model') & (df['confidence'] > 0)
            if model_mask.any():
                sub = df.loc[model_mask]
                texts = build_semantic_texts(sub)
                sem_pred, sem_raw = predict_semantic(
                    texts, bundle.semantic['encoder'], bundle.semantic['clf'])

                conf_t = apply_calibrator(bundle.cal_tfidf,
                                          sub['confidence'].to_numpy(dtype=float))
                conf_s = apply_calibrator(bundle.cal_semantic, sem_raw)
                ens_conf = np.minimum(conf_t, conf_s)

                threshold = float(bundle.ensemble['threshold'])
                tfidf_pred = sub['category'].to_numpy()
                agreed = ((tfidf_pred == sem_pred)
                          & (ens_conf >= threshold)
                          & (tfidf_pred != 'Other'))

                idx = sub.index[agreed]
                df.loc[idx, 'label_source'] = 'model_agreed'
                df.loc[idx, 'confidence'] = ens_conf[agreed]
                # Non-agreed model rows: report calibrated (honest) confidence
                # so the review queue ranks by numbers that mean something.
                idx_rest = sub.index[~agreed]
                df.loc[idx_rest, 'confidence'] = conf_t[~agreed]
        except Exception as e:
            # Never let the trust layer break classification; fall back to
            # review-everything behavior for model rows.
            print(f"   [agreement layer skipped: {type(e).__name__}: {e}]")

    if rules:
        ruled = apply_merchant_rules(df, rules)
        matched = ruled['labeled'] == True
        df.loc[matched, 'category'] = ruled.loc[matched, 'category']
        df.loc[matched, 'confidence'] = 1.0
        df.loc[matched, 'label_source'] = 'rule'

    df = apply_description_overrides(df)
    df = normalize_categories(df, valid_categories=valid_categories, catch_all=catch_all)

    # Routing: rules/overrides trusted; model predictions auto-apply only via
    # the calibrated-agreement gate above; everything else goes to review.
    df['needs_review'] = ~df['label_source'].isin(['rule', 'override', 'model_agreed'])
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
    bundle = load_model_bundle()
    rules = load_merchant_rules(str(MERCHANT_RULES))

    print(f"\n1. Loaded {len(df)} transactions")
    if bundle.classifier is not None:
        feature_type = "HYBRID (semantic-weighted)" if bundle.config.get('use_hybrid', False) else "LEGACY (combined text)"
        print(f"2. Loaded trained classifier ({feature_type})")
        if bundle.agreement_ready:
            print(f"   Graduated trust ON — semantic model ({bundle.semantic['encoder_kind']}) "
                  f"+ calibrated agreement, threshold {bundle.ensemble['threshold']}")
        else:
            print("   Graduated trust OFF — all model predictions route to review")
    else:
        print("2. No classifier found — rules-only mode (run bootstrap.py to train)")
    print(f"3. Loaded {len(rules)} merchant rules")

    print("\n4. Classifying all transactions...")
    df_classified = classify_all(df, rules=rules, bundle=bundle)

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
