"""
Comprehensive evaluation: stratified CV, per-category metrics, error analysis, calibration.
This is the TRUTH—replace misleading single-split accuracy.
"""
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, brier_score_loss
)
from sklearn.calibration import calibration_curve
from sklearn.dummy import DummyClassifier
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

sys.path.insert(0, str(Path(__file__).parent))
from segment import vectorize, build_vectorizer, clean_text


def load_data():
    """Load labeled transactions and filter to labeled ones."""
    df = pd.read_csv('data/labeled/labeled_transactions.csv')
    df = df[df['labeled'] == True].copy()
    df['text'] = df.apply(
        lambda row: clean_text(row['merchant'], row['description']),
        axis=1
    )
    return df


def build_feature_matrix(df):
    """Build feature matrix from cleaned text."""
    print(f"\n1. Building vectorizer from {len(df)} texts...")
    vectorizer = build_vectorizer(df['text'].tolist(), max_features=500)
    X = vectorize(df['text'].tolist(), vectorizer)
    y = df['category']
    return X, y, vectorizer


def baseline_accuracy(y):
    """Compute baseline: always predict majority class."""
    dummy = DummyClassifier(strategy='most_frequent')
    from sklearn.model_selection import cross_val_score
    scores = cross_val_score(dummy, np.ones((len(y), 1)), y, cv=5, scoring='accuracy')
    return scores.mean()


def stratified_cv_evaluation(X, y):
    """
    Stratified 5-fold cross-validation with per-category metrics.
    """
    print(f"\n2. Class distribution (CRITICAL for understanding imbalance):")
    categories = sorted(y.unique())
    for cat in categories:
        count = (y == cat).sum()
        pct = 100 * count / len(y)
        print(f"   {cat:30s}: {count:3d} ({pct:5.1f}%)")

    print(f"\n3. Stratified K-Fold Cross-Validation starting...")

    # Use fewer splits if necessary due to class imbalance
    # StratifiedKFold requires at least 2 splits
    n_splits = max(2, min(5, min(y.value_counts())))
    if n_splits < 5:
        print(f"   Warning: Using {n_splits}-fold CV due to small class sizes")
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    fold_accuracies = []
    fold_f1s_weighted = []
    fold_f1s_macro = []
    all_y_true = []
    all_y_pred = []
    all_y_proba_list = []

    for fold, (train_idx, test_idx) in enumerate(skf.split(X, y), 1):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        # Train
        clf = LogisticRegression(max_iter=1000, random_state=42, solver='lbfgs')
        clf.fit(X_train, y_train)

        # Predict
        y_pred = clf.predict(X_test)
        y_pred_proba_raw = clf.predict_proba(X_test)

        # Get class order from this fold's model to map probabilities correctly
        fold_classes = list(clf.classes_)

        # Metrics for this fold
        acc = accuracy_score(y_test, y_pred)
        f1_weighted = f1_score(y_test, y_pred, average='weighted', zero_division=0)
        f1_macro = f1_score(y_test, y_pred, average='macro', zero_division=0)

        fold_accuracies.append(acc)
        fold_f1s_weighted.append(f1_weighted)
        fold_f1s_macro.append(f1_macro)

        # Accumulate for overall metrics
        all_y_true.extend(y_test)
        all_y_pred.extend(y_pred)

        # Store probabilities with metadata
        for i, pred_proba in enumerate(y_pred_proba_raw):
            # Create full probability vector aligned to all categories
            full_proba = np.zeros(len(categories))
            for j, cat in enumerate(fold_classes):
                cat_idx = list(categories).index(cat)
                full_proba[cat_idx] = pred_proba[j]
            all_y_proba_list.append(full_proba)

        print(f"   Fold {fold}: Accuracy={acc:.3f}, F1-weighted={f1_weighted:.3f}, F1-macro={f1_macro:.3f}")

    # Convert to numpy for confmat
    all_y_true = np.array(all_y_true)
    all_y_pred = np.array(all_y_pred)
    all_y_proba = np.array(all_y_proba_list)

    print(f"\n4. OVERALL CROSS-VALIDATION RESULTS:")
    print(f"   Accuracy (mean ± std): {np.mean(fold_accuracies):.3f} ± {np.std(fold_accuracies):.3f}")
    print(f"   F1-weighted (mean):    {np.mean(fold_f1s_weighted):.3f}")
    print(f"   F1-macro (mean):       {np.mean(fold_f1s_macro):.3f}")

    # Per-category breakdown
    print(f"\n5. PER-CATEGORY METRICS (over all folds):")
    print("-" * 80)
    report = classification_report(all_y_true, all_y_pred, target_names=categories, digits=3)
    print(report)

    # Confusion matrix
    cm = confusion_matrix(all_y_true, all_y_pred, labels=categories)

    print(f"\n6. CONFUSION MATRIX:")
    print("-" * 80)
    header = "       " + "".join([f"{cat[:6]:>8s}" for cat in categories])
    print(header)
    for i, cat in enumerate(categories):
        row = f"{cat[:6]:6s}"
        for j in range(len(categories)):
            row += f"{cm[i, j]:8d}"
        print(row)

    # Save confusion matrix plot
    plt.figure(figsize=(12, 10))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=categories, yticklabels=categories)
    plt.title('Confusion Matrix (Stratified 5-Fold CV)')
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig('_confusion_matrix.png', dpi=100)
    print(f"\nConfusion matrix plot saved to _confusion_matrix.png")
    plt.close()

    return {
        'accuracy_mean': np.mean(fold_accuracies),
        'accuracy_std': np.std(fold_accuracies),
        'f1_weighted': np.mean(fold_f1s_weighted),
        'f1_macro': np.mean(fold_f1s_macro),
        'y_true': all_y_true,
        'y_pred': all_y_pred,
        'y_proba': all_y_proba,
        'categories': categories,
        'confusion_matrix': cm
    }


def confidence_calibration(y_true, y_proba, categories):
    """
    Analyze: is predicted confidence actually predictive of correctness?
    """
    print(f"\n7. CONFIDENCE CALIBRATION:")
    print("-" * 80)

    # Get max probability (confidence) for each prediction
    confidences = y_proba.max(axis=1)
    predicted_labels = np.array([categories[np.argmax(p)] for p in y_proba])
    correctness = (predicted_labels == y_true).astype(int)

    print(f"   Mean confidence: {confidences.mean():.3f}")
    print(f"   Std confidence:  {confidences.std():.3f}")
    print(f"   Min confidence:  {confidences.min():.3f}")
    print(f"   Max confidence:  {confidences.max():.3f}")

    # Plot calibration curve
    prob_true, prob_pred = calibration_curve(correctness, confidences, n_bins=10)

    plt.figure(figsize=(10, 6))
    plt.plot([0, 1], [0, 1], 'k--', label='Perfectly calibrated')
    plt.plot(prob_pred, prob_true, 'o-', label='Model')
    plt.xlabel('Mean Predicted Confidence')
    plt.ylabel('Fraction of Positives (Accuracy at Confidence)')
    plt.title('Calibration Curve: Is Confidence Predictive of Correctness?')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig('_calibration_curve.png', dpi=100)
    print(f"\nCalibration curve saved to _calibration_curve.png")
    plt.close()

    # Brier score (lower is better)
    brier = brier_score_loss(correctness, confidences)
    print(f"   Brier score:     {brier:.3f} (lower is better; 0 = perfect calibration)")

    # Confidence by correctness
    correct_conf = confidences[correctness == 1]
    incorrect_conf = confidences[correctness == 0]
    print(f"\n   Confidence when CORRECT:   mean={correct_conf.mean():.3f}, std={correct_conf.std():.3f}")
    print(f"   Confidence when WRONG:     mean={incorrect_conf.mean():.3f}, std={incorrect_conf.std():.3f}")

    if len(incorrect_conf) > 0:
        separation = correct_conf.mean() - incorrect_conf.mean()
        print(f"   Separation (higher=better): {separation:.3f}")
        if separation < 0.1:
            print(f"   ⚠️  WARNING: Low separation—model confidence is NOT well-calibrated!")


def error_analysis(y_true, y_pred, categories):
    """
    Deep dive: which categories fail most, why, common misclassifications.
    """
    print(f"\n8. ERROR ANALYSIS:")
    print("-" * 80)

    incorrect_mask = y_true != y_pred
    incorrect_count = incorrect_mask.sum()
    print(f"   Total errors: {incorrect_count}/{len(y_true)} ({100*incorrect_count/len(y_true):.1f}%)")

    print(f"\n   Errors by TRUE category (recall = 1 - % of category that's wrong):")
    for cat in categories:
        cat_mask = (y_true == cat)
        cat_errors = (incorrect_mask & cat_mask).sum()
        cat_total = cat_mask.sum()
        if cat_total > 0:
            recall = 1 - (cat_errors / cat_total)
            print(f"      {cat:30s}: {cat_errors:3d}/{cat_total:3d} errors ({100*(1-recall):5.1f}% error rate, {100*recall:.1f}% recall)")

    print(f"\n   Most common misclassifications:")
    confusion_pairs = []
    for i, true_cat in enumerate(categories):
        for j, pred_cat in enumerate(categories):
            if i != j:
                count = ((y_true == true_cat) & (y_pred == pred_cat)).sum()
                if count > 0:
                    confusion_pairs.append((true_cat, pred_cat, count))

    confusion_pairs.sort(key=lambda x: x[2], reverse=True)
    for true_cat, pred_cat, count in confusion_pairs[:10]:
        print(f"      {true_cat:25s} → {pred_cat:25s}: {count:3d} times")


def main():
    print("="*80)
    print("COMPREHENSIVE EVALUATION: STRATIFIED CV + PER-CATEGORY ANALYSIS")
    print("="*80)

    # Load data
    df = load_data()
    print(f"\nLoaded {len(df)} labeled transactions")

    # Build features
    X, y, vectorizer = build_feature_matrix(df)
    print(f"Feature matrix shape: {X.shape}")

    # Baseline
    baseline = baseline_accuracy(y)
    print(f"\nBASELINE (always predict majority class): {baseline:.3f} ({100*baseline:.1f}%)")
    print("(This is what we need to beat)")

    # Stratified CV evaluation
    results = stratified_cv_evaluation(X, y)

    # Calibration
    confidence_calibration(results['y_true'], results['y_proba'], results['categories'])

    # Error analysis
    error_analysis(results['y_true'], results['y_pred'], results['categories'])

    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY:")
    print(f"{'='*80}")
    print(f"REAL Accuracy (stratified CV): {100*results['accuracy_mean']:.1f}% ± {100*results['accuracy_std']:.1f}%")
    print(f"Baseline:                       {100*baseline:.1f}%")
    print(f"Improvement over baseline:      {100*(results['accuracy_mean']-baseline):.1f}%")
    print(f"F1-weighted:                    {results['f1_weighted']:.3f}")
    print(f"F1-macro (unweighted):          {results['f1_macro']:.3f} ← Shows performance on minority classes")
    print(f"\n⚠️  Note: F1-macro < F1-weighted means minority classes are dragging down accuracy!")
    print(f"{'='*80}\n")

    # Save report
    with open('_eval_report.txt', 'w', encoding='utf-8') as f:
        f.write("COMPREHENSIVE EVALUATION REPORT\n")
        f.write("="*80 + "\n\n")
        f.write(f"REAL Accuracy (stratified CV): {100*results['accuracy_mean']:.1f}% ± {100*results['accuracy_std']:.1f}%\n")
        f.write(f"Baseline (majority class):     {100*baseline:.1f}%\n")
        f.write(f"F1-weighted:                   {results['f1_weighted']:.3f}\n")
        f.write(f"F1-macro:                      {results['f1_macro']:.3f}\n\n")
        f.write("CLASSIFICATION REPORT:\n")
        f.write(classification_report(results['y_true'], results['y_pred'],
                                      target_names=results['categories'], digits=3))

    print("Report saved to _eval_report.txt")


if __name__ == '__main__':
    main()
