"""
Compare original model vs tuned model on minority category performance.
This shows the REAL impact of class weights and hyperparameter tuning.
"""
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, accuracy_score, confusion_matrix, classification_report
import joblib
import matplotlib.pyplot as plt

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


def build_feature_matrix(df, max_features=500):
    """Build feature matrix from cleaned text."""
    vectorizer = build_vectorizer(df['text'].tolist(), max_features=max_features)
    X = vectorize(df['text'].tolist(), vectorizer)
    y = df['category']

    # Filter categories with < 2 samples
    valid_categories = y.value_counts()[y.value_counts() >= 2].index
    mask = y.isin(valid_categories).values
    X = X[mask]
    y = y[mask]

    return X, y, vectorizer


def evaluate_model(clf_config, X, y, model_name):
    """
    Evaluate a model configuration with stratified CV.
    Returns per-category F1 scores and overall accuracy.
    """
    print(f"\n{'='*80}")
    print(f"Evaluating: {model_name}")
    print(f"{'='*80}")

    n_splits = min(2, min(y.value_counts()))
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    all_y_true = []
    all_y_pred = []
    categories = sorted(y.unique())

    for fold, (train_idx, test_idx) in enumerate(skf.split(X, y), 1):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        # Create and train model
        clf = LogisticRegression(**clf_config)
        clf.fit(X_train, y_train)

        # Predict
        y_pred = clf.predict(X_test)
        all_y_true.extend(y_test)
        all_y_pred.extend(y_pred)

        acc = accuracy_score(y_test, y_pred)
        f1_w = f1_score(y_test, y_pred, average='weighted', zero_division=0)
        print(f"  Fold {fold}: Acc={acc:.3f}, F1-weighted={f1_w:.3f}")

    all_y_true = np.array(all_y_true)
    all_y_pred = np.array(all_y_pred)

    # Overall metrics
    print(f"\nOverall Results:")
    overall_acc = accuracy_score(all_y_true, all_y_pred)
    overall_f1 = f1_score(all_y_true, all_y_pred, average='weighted', zero_division=0)
    print(f"  Accuracy:    {overall_acc:.3f}")
    print(f"  F1-weighted: {overall_f1:.3f}")

    # Per-category F1
    print(f"\nPer-Category F1 Scores:")
    per_cat_f1 = {}
    for cat in categories:
        cat_mask_true = (all_y_true == cat)
        cat_mask_pred = (all_y_pred == cat)

        if cat_mask_true.sum() > 0:
            # F1 for this category
            tp = ((all_y_true == cat) & (all_y_pred == cat)).sum()
            fp = ((all_y_true != cat) & (all_y_pred == cat)).sum()
            fn = ((all_y_true == cat) & (all_y_pred != cat)).sum()

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            per_cat_f1[cat] = f1
            print(f"  {cat:30s}: {f1:.3f} (precision={precision:.3f}, recall={recall:.3f})")

    return {
        'overall_acc': overall_acc,
        'overall_f1': overall_f1,
        'per_cat_f1': per_cat_f1,
        'y_true': all_y_true,
        'y_pred': all_y_pred,
    }


def main():
    print("="*80)
    print("COMPARING MODELS: ORIGINAL VS TUNED")
    print("="*80)

    # Load data
    df = load_data()
    X, y, vectorizer = build_feature_matrix(df, max_features=500)

    print(f"\nEvaluating on {X.shape[0]} transactions")
    print(f"Classes: {len(y.unique())}")

    # Original model config (from current train.py)
    original_config = {
        'max_iter': 1000,
        'solver': 'lbfgs',
        'random_state': 42,
        'class_weight': None,  # NOT balanced
        'C': 1.0,  # default
    }

    # Tuned model config
    tuned_config = {
        'max_iter': 1000,
        'solver': 'lbfgs',
        'random_state': 42,
        'class_weight': 'balanced',  # BALANCED!
        'C': 10,  # Reduced regularization
    }

    # Evaluate both
    original_results = evaluate_model(original_config, X, y, "ORIGINAL MODEL (no class_weight)")
    tuned_results = evaluate_model(tuned_config, X, y, "TUNED MODEL (class_weight='balanced', C=10)")

    # Compare
    print(f"\n{'='*80}")
    print(f"COMPARISON")
    print(f"{'='*80}")

    print(f"\nOverall Accuracy:")
    print(f"  Original: {original_results['overall_acc']:.3f}")
    print(f"  Tuned:    {tuned_results['overall_acc']:.3f}")
    print(f"  Δ:        {(tuned_results['overall_acc'] - original_results['overall_acc']):.3f}")

    print(f"\nOverall F1-weighted:")
    print(f"  Original: {original_results['overall_f1']:.3f}")
    print(f"  Tuned:    {tuned_results['overall_f1']:.3f}")
    print(f"  Δ:        {(tuned_results['overall_f1'] - original_results['overall_f1']):.3f}")

    # Focus on minority categories
    print(f"\n{'='*80}")
    print(f"MINORITY CATEGORY IMPROVEMENTS (F1 Score):")
    print(f"{'='*80}")
    minority_cats = ['Shopping', 'Transfers & Gifts', 'Travel', 'Utilities & Services', 'Other']
    for cat in minority_cats:
        if cat in original_results['per_cat_f1']:
            orig_f1 = original_results['per_cat_f1'].get(cat, 0)
            tuned_f1 = tuned_results['per_cat_f1'].get(cat, 0)
            delta = tuned_f1 - orig_f1
            pct_improvement = (delta / orig_f1 * 100) if orig_f1 > 0 else float('inf')
            print(f"  {cat:30s}: {orig_f1:.3f} → {tuned_f1:.3f} (Δ={delta:+.3f}, {pct_improvement:+.0f}%)")

    # Save comparison report
    with open('_model_comparison_report.txt', 'w', encoding='utf-8') as f:
        f.write("MODEL COMPARISON: ORIGINAL vs TUNED\n")
        f.write("="*80 + "\n\n")
        f.write(f"Overall Accuracy:\n")
        f.write(f"  Original: {original_results['overall_acc']:.3f}\n")
        f.write(f"  Tuned:    {tuned_results['overall_acc']:.3f}\n")
        f.write(f"  Gain:     {(tuned_results['overall_acc'] - original_results['overall_acc']):+.3f}\n\n")
        f.write(f"Overall F1-weighted:\n")
        f.write(f"  Original: {original_results['overall_f1']:.3f}\n")
        f.write(f"  Tuned:    {tuned_results['overall_f1']:.3f}\n")
        f.write(f"  Gain:     {(tuned_results['overall_f1'] - original_results['overall_f1']):+.3f}\n\n")
        f.write("Per-Category F1 Scores:\n")
        f.write("-"*80 + "\n")
        for cat in sorted(original_results['per_cat_f1'].keys()):
            orig = original_results['per_cat_f1'].get(cat, 0)
            tuned = tuned_results['per_cat_f1'].get(cat, 0)
            f.write(f"  {cat:30s}: {orig:.3f} → {tuned:.3f} (Δ={tuned-orig:+.3f})\n")

    print(f"\nComparison report saved to _model_comparison_report.txt")


if __name__ == '__main__':
    main()
