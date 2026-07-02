"""Automated retraining workflow: load labeled data, train, evaluate, save."""
import pandas as pd
import joblib
from pathlib import Path
import sys
from datetime import datetime
sys.path.insert(0, str(Path.cwd()))

from segment import clean_text, vectorize, build_vectorizer, LR_HYPERPARAMS
from feature_engineering import (
    extract_numeric_features,
    build_hybrid_vectorizers,
    create_hybrid_feature_matrix,
)
from categories import CATEGORY_NORMALIZE, ML_CATEGORIES
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix

# Enable/disable hybrid semantic-weighted feature engineering
USE_HYBRID_FEATURES = True


def retrain_model():
    """Retrain classifier with latest labeled data."""
    print("="*70)
    print(f"AUTOMATED RETRAINING WORKFLOW — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    # Load labeled data
    labeled_path = 'data/labeled/labeled_transactions.csv'
    df = pd.read_csv(labeled_path)

    # Filter to only explicitly labeled rows (labeled==True) to match train.py
    df_labeled = df[df['labeled'] == True].copy()
    df_labeled['category'] = df_labeled['category'].replace(CATEGORY_NORMALIZE)
    df_labeled = df_labeled[df_labeled['category'].isin(ML_CATEGORIES)]

    # Labeled CSV stores the datetime as 'timestamp'; feature engineering
    # expects 'time'. Normalize once here.
    if 'time' not in df_labeled.columns and 'timestamp' in df_labeled.columns:
        df_labeled['time'] = df_labeled['timestamp']
    print(f"\n1. Loaded {len(df_labeled)} labeled transactions")
    print(f"   Category distribution:")
    for cat, count in df_labeled['category'].value_counts().sort_values(ascending=False).items():
        pct = 100 * count / len(df_labeled)
        print(f"      {cat:30s}: {count:3d} ({pct:5.1f}%)")

    # Filter out categories with fewer than 2 samples (StratifiedKFold requirement)
    min_class_count = df_labeled['category'].value_counts().min()
    if min_class_count < 2:
        print(f"\n   WARNING: Found categories with < 2 samples. Filtering them out.")
        classes_to_keep = df_labeled['category'].value_counts()[df_labeled['category'].value_counts() >= 2].index
        df_labeled = df_labeled[df_labeled['category'].isin(classes_to_keep)].copy()
        print(f"   Kept {len(classes_to_keep)} categories, now training on {len(df_labeled)} samples")

    y = df_labeled['category']

    # Clean and vectorize using either hybrid or legacy approach
    print(f"\n2. Cleaning and vectorizing text...")
    if USE_HYBRID_FEATURES:
        print(f"   Using HYBRID feature engineering (semantic-weighted text + numeric features)")

        # Extract numeric contextual features
        numeric_features, valid_indices = extract_numeric_features(df_labeled)

        # Filter DataFrame to only valid rows (those with time/amount)
        df_valid = df_labeled.iloc[valid_indices].copy()
        y = y.iloc[valid_indices]

        # Build separate vectorizers for description and merchant
        desc_texts = df_valid['description'].tolist()
        merch_texts = df_valid['merchant'].tolist()
        desc_vec, merch_vec = build_hybrid_vectorizers(desc_texts, merch_texts)

        # Create hybrid feature matrix
        X = create_hybrid_feature_matrix(df_valid, desc_vec, merch_vec, numeric_features)

        # Save vectorizers with '_hybrid' suffix to distinguish from legacy
        vectorizer = {'desc': desc_vec, 'merch': merch_vec}
        print(f"   Description vectorizer: {len(desc_vec.get_feature_names_out())} features")
        print(f"   Merchant vectorizer: {len(merch_vec.get_feature_names_out())} features")
        print(f"   Numeric features: 6 (hour, day, lunch, dinner, amount_bucket, merchant_freq)")
        print(f"   Total hybrid features: {X.shape[1]}")

    else:
        print(f"   Using LEGACY feature engineering (combined text only)")

        # Classic approach: combine merchant + description
        df_labeled['text'] = df_labeled.apply(
            lambda row: clean_text(row['merchant'], row['description']),
            axis=1
        )

        vectorizer = build_vectorizer(df_labeled['text'].tolist())
        X = vectorize(df_labeled['text'].tolist(), vectorizer)

        print(f"   Vectorizer: {X.shape[1]} features extracted")

    # Retrain with stratified cross-validation
    print(f"\n3. Training Logistic Regression with stratified CV...")
    clf = LogisticRegression(**LR_HYPERPARAMS)

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = []
    cv_f1_weighted = []
    cv_f1_macro = []

    for fold, (train_idx, test_idx) in enumerate(skf.split(X, y)):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        clf_fold = LogisticRegression(**LR_HYPERPARAMS)
        clf_fold.fit(X_train, y_train)

        acc = accuracy_score(y_test, clf_fold.predict(X_test))
        f1_w = f1_score(y_test, clf_fold.predict(X_test), average='weighted', zero_division=0)
        f1_m = f1_score(y_test, clf_fold.predict(X_test), average='macro', zero_division=0)

        cv_scores.append(acc)
        cv_f1_weighted.append(f1_w)
        cv_f1_macro.append(f1_m)

        print(f"   Fold {fold+1}/5: Accuracy {acc:.1%}, F1-weighted {f1_w:.3f}, F1-macro {f1_m:.3f}")

    # Train final model on all data
    clf.fit(X, y)

    print(f"\n4. CROSS-VALIDATION RESULTS (average):")
    print(f"   Accuracy:    {sum(cv_scores)/len(cv_scores):.1%} (±{max(cv_scores)-min(cv_scores):.1%})")
    print(f"   F1-weighted: {sum(cv_f1_weighted)/len(cv_f1_weighted):.3f}")
    print(f"   F1-macro:    {sum(cv_f1_macro)/len(cv_f1_macro):.3f} (fairness metric)")

    # Save artifacts
    print(f"\n5. Saving updated model artifacts...")
    if USE_HYBRID_FEATURES:
        # Save hybrid vectorizers with metadata
        joblib.dump(vectorizer, 'data/processed/tfidf_vectorizer_hybrid.pkl')
        joblib.dump({'use_hybrid': True}, 'data/processed/vectorizer_config.pkl')
        print(f"   [OK] tfidf_vectorizer_hybrid.pkl (desc + merch vectorizers)")
    else:
        # Save legacy vectorizer
        joblib.dump(vectorizer, 'data/processed/tfidf_vectorizer.pkl')
        joblib.dump({'use_hybrid': False}, 'data/processed/vectorizer_config.pkl')
        print(f"   [OK] tfidf_vectorizer.pkl")

    joblib.dump(clf, 'data/processed/classifier.pkl')
    print(f"   [OK] classifier.pkl")
    print(f"   [OK] vectorizer_config.pkl")

    # 5b. Semantic layer: embedding model + calibrators + agreement threshold.
    # All rebuilt from THIS label snapshot in the same pass, so the two models
    # never drift apart. On any failure, delete semantic artifacts so classify
    # degrades cleanly to review-everything (never pair stale artifacts).
    print(f"\n5b. Training semantic (embedding) layer...")
    from paths import (SEMANTIC_MODEL, SEMANTIC_INDEX, SEMANTIC_CALIBRATOR,
                       TFIDF_CALIBRATOR, ENSEMBLE_CONFIG)
    try:
        import semantic as sem
        encoder = sem.get_encoder()  # retrain is the one moment downloads may happen
        if encoder is None:
            print(f"   Model2Vec unavailable — fitting LsaEncoder fallback "
                  f"(string similarity only, no pretrained knowledge)")
            encoder = sem.fit_lsa_encoder(sem.build_semantic_texts(df_labeled))
        else:
            print(f"   Using Model2Vec encoder (pretrained multilingual)")

        sem_model = sem.train_semantic_model(df_labeled, encoder)
        sem.save_semantic_artifacts(sem_model)
        print(f"   [OK] semantic_classifier.pkl + semantic_index.pkl "
              f"({len(sem_model['index']['labels'])} indexed examples)")

        # Honest grouped evaluation: fits + saves both calibrators, derives
        # + saves the auto-apply threshold (or records that none qualifies).
        import eval_grouped
        eval_results = eval_grouped.run_report(df_labeled=df_labeled, encoder=encoder)
        thr = eval_results.get('threshold')
        if thr:
            print(f"   [OK] Graduated trust ENABLED: threshold {thr['threshold']} "
                  f"(precision {thr['precision']:.1%} on unseen merchants)")
        else:
            print(f"   [OK] No safe threshold found — auto-apply stays OFF "
                  f"(all model predictions go to review)")
    except Exception as e:
        print(f"   [WARN] Semantic layer failed ({type(e).__name__}: {e}) — "
              f"removing semantic artifacts; classifier falls back to review-everything")
        for p in (SEMANTIC_MODEL, SEMANTIC_INDEX, SEMANTIC_CALIBRATOR,
                  TFIDF_CALIBRATOR, ENSEMBLE_CONFIG):
            p.unlink(missing_ok=True)

    # Per-category evaluation on all labeled data
    print(f"\n6. PER-CATEGORY PERFORMANCE (on all {len(df_labeled)} labeled examples):")
    y_pred = clf.predict(X)
    report = classification_report(y, y_pred, output_dict=True, zero_division=0)

    for category in sorted(set(y)):
        if category in report:
            metrics = report[category]
            print(f"   {category:30s}: F1 {metrics['f1-score']:.3f}, Recall {metrics['recall']:.1%}, Precision {metrics['precision']:.1%}")

    # Save detailed report
    report_path = Path('data/reports/TRAINING_REPORT.txt')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"RETRAINING REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*70 + "\n\n")
        f.write(f"Labeled samples: {len(df_labeled)}\n")
        f.write(f"Features: {X.shape[1]}\n")
        f.write(f"Categories: {len(set(y))}\n\n")
        f.write(f"Cross-Validation Results (5-fold stratified):\n")
        f.write(f"  Accuracy:    {sum(cv_scores)/len(cv_scores):.1%}\n")
        f.write(f"  F1-weighted: {sum(cv_f1_weighted)/len(cv_f1_weighted):.3f}\n")
        f.write(f"  F1-macro:    {sum(cv_f1_macro)/len(cv_f1_macro):.3f}\n\n")
        f.write(f"Per-Category Metrics:\n")
        f.write(classification_report(y, y_pred, zero_division=0))

    print(f"   Detailed report: {report_path}")

    print(f"\n{'='*70}")
    print(f"RETRAINING COMPLETE!")
    print(f"Ready to classify new transactions with updated model")
    print(f"{'='*70}")

    return {
        'accuracy': sum(cv_scores) / len(cv_scores),
        'f1_macro': sum(cv_f1_macro) / len(cv_f1_macro),
        'n_samples': len(df_labeled),
        'n_features': X.shape[1]
    }


if __name__ == '__main__':
    try:
        results = retrain_model()
    except Exception as e:
        print(f"\nERROR during retraining: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
