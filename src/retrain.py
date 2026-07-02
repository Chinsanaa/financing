"""Automated retraining workflow: load labeled data, train, evaluate, save."""
import pandas as pd
import joblib
from pathlib import Path
import sys
from datetime import datetime
sys.path.insert(0, str(Path.cwd()))

from segment import clean_text, vectorize, build_vectorizer, LR_HYPERPARAMS
from categories import CATEGORY_NORMALIZE, ML_CATEGORIES
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix


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
    print(f"\n1. Loaded {len(df_labeled)} labeled transactions")
    print(f"   Category distribution:")
    for cat, count in df_labeled['category'].value_counts().sort_values(ascending=False).items():
        pct = 100 * count / len(df_labeled)
        print(f"      {cat:30s}: {count:3d} ({pct:5.1f}%)")

    # Clean and vectorize
    print(f"\n2. Cleaning and vectorizing text...")
    df_labeled['text'] = df_labeled.apply(
        lambda row: clean_text(row['merchant'], row['description']),
        axis=1
    )

    # Filter out categories with fewer than 2 samples (StratifiedKFold requirement)
    min_class_count = df_labeled['category'].value_counts().min()
    if min_class_count < 2:
        print(f"\n   WARNING: Found categories with < 2 samples. Filtering them out.")
        classes_to_keep = df_labeled['category'].value_counts()[df_labeled['category'].value_counts() >= 2].index
        df_labeled = df_labeled[df_labeled['category'].isin(classes_to_keep)].copy()
        print(f"   Kept {len(classes_to_keep)} categories, now training on {len(df_labeled)} samples")

    vectorizer = build_vectorizer(df_labeled['text'].tolist())
    X = vectorize(df_labeled['text'].tolist(), vectorizer)
    y = df_labeled['category']

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
    joblib.dump(vectorizer, 'data/processed/tfidf_vectorizer.pkl')
    joblib.dump(clf, 'data/processed/classifier.pkl')
    print(f"   [OK] tfidf_vectorizer.pkl")
    print(f"   [OK] classifier.pkl")

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
