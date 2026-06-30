"""
PHASE 2 & 3: Class imbalance + hyperparameter tuning with stratified CV.
This script identifies the BEST hyperparameters and class weighting strategy.
"""
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from sklearn.model_selection import StratifiedKFold, GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import f1_score, accuracy_score, classification_report
import joblib
import warnings

warnings.filterwarnings('ignore', category=UserWarning)

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
    print(f"Building vectorizer from {len(df)} texts with max_features={max_features}...")
    vectorizer = build_vectorizer(df['text'].tolist(), max_features=max_features)
    X = vectorize(df['text'].tolist(), vectorizer)
    y = df['category']

    # Filter categories with < 2 samples
    valid_categories = y.value_counts()[y.value_counts() >= 2].index
    mask = y.isin(valid_categories).values
    X = X[mask]
    y = y[mask]

    return X, y, vectorizer


def tune_logistic_regression(X, y):
    """
    Grid search for best Logistic Regression hyperparameters.
    Focus on class_weight (most critical for imbalance).
    """
    print("\n" + "="*80)
    print("TUNING LOGISTIC REGRESSION")
    print("="*80)

    # Use stratified CV with fewer splits due to imbalance
    n_splits = min(3, min(y.value_counts()))
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    # Grid search parameters
    param_grid = {
        'C': [0.1, 1, 10],  # Regularization strength
        'solver': ['lbfgs', 'liblinear'],
        'class_weight': [None, 'balanced'],  # THIS IS KEY
        'max_iter': [1000, 2000],
    }

    clf = LogisticRegression(random_state=42)

    print(f"\nGrid searching {len(param_grid['C']) * len(param_grid['solver']) * len(param_grid['class_weight']) * len(param_grid['max_iter'])} parameter combinations...")
    print(f"Using {n_splits}-fold stratified CV")

    # f1_macro (not f1_weighted) is the scoring target: f1_weighted is
    # dominated by majority categories and will happily pick
    # class_weight=None since it barely dents the weighted average while
    # minority categories stay at 0% recall. f1_macro treats every
    # category equally, which is what we actually want to optimize for.
    gs = GridSearchCV(
        clf,
        param_grid,
        cv=skf,
        scoring='f1_macro',
        n_jobs=-1,
        verbose=1
    )

    gs.fit(X, y)

    print(f"\n{'='*80}")
    print(f"BEST PARAMETERS (F1-macro={gs.best_score_:.3f}):")
    print(f"{'='*80}")
    for param, value in gs.best_params_.items():
        print(f"  {param:20s}: {value}")

    return gs


def tune_naive_bayes(X, y):
    """
    Test Naive Bayes as alternative (often better for text, no class_weight but simpler).
    """
    print("\n" + "="*80)
    print("TESTING NAIVE BAYES")
    print("="*80)

    n_splits = min(3, min(y.value_counts()))
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    # Naive Bayes has no class_weight, but is often better for text
    param_grid = {
        'alpha': [0.1, 0.5, 1.0],
        'fit_prior': [True, False],
    }

    clf = MultinomialNB()

    print(f"\nGrid searching {len(param_grid['alpha']) * len(param_grid['fit_prior'])} parameter combinations...")
    print(f"Using {n_splits}-fold stratified CV")

    gs = GridSearchCV(
        clf,
        param_grid,
        cv=skf,
        scoring='f1_macro',
        n_jobs=-1,
        verbose=1
    )

    gs.fit(X, y)

    print(f"\n{'='*80}")
    print(f"BEST PARAMETERS (F1-macro={gs.best_score_:.3f}):")
    print(f"{'='*80}")
    for param, value in gs.best_params_.items():
        print(f"  {param:20s}: {value}")

    return gs


def compare_models(lr_gs, nb_gs, X, y):
    """
    Compare tuned Logistic Regression vs Naive Bayes.
    """
    print("\n" + "="*80)
    print("MODEL COMPARISON")
    print("="*80)

    models = [
        ('Logistic Regression (tuned)', lr_gs.best_estimator_),
        ('Naive Bayes (tuned)', nb_gs.best_estimator_),
    ]

    n_splits = min(3, min(y.value_counts()))
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    for name, model in models:
        f1_scores = []
        accuracy_scores = []

        for fold, (train_idx, test_idx) in enumerate(skf.split(X, y), 1):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
            acc = accuracy_score(y_test, y_pred)

            f1_scores.append(f1)
            accuracy_scores.append(acc)

        print(f"\n{name}:")
        print(f"  Accuracy:    {np.mean(accuracy_scores):.3f} ± {np.std(accuracy_scores):.3f}")
        print(f"  F1-weighted: {np.mean(f1_scores):.3f} ± {np.std(f1_scores):.3f}")

    return models


def main():
    print("="*80)
    print("PHASE 2 & 3: CLASS IMBALANCE + HYPERPARAMETER TUNING")
    print("="*80)

    # Load data
    df = load_data()
    print(f"\nLoaded {len(df)} labeled transactions")

    # Build features (try both 500 and 1000 max_features)
    X, y, vectorizer = build_feature_matrix(df, max_features=500)
    print(f"Feature matrix shape: {X.shape}")

    print(f"\nClass distribution:")
    for cat, count in sorted(y.value_counts().items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat:30s}: {count:3d}")

    # Tune both models
    lr_gs = tune_logistic_regression(X, y)
    nb_gs = tune_naive_bayes(X, y)

    # Compare
    models = compare_models(lr_gs, nb_gs, X, y)

    # Save best model
    best_model = lr_gs.best_estimator_
    print(f"\n" + "="*80)
    print(f"SAVING BEST MODEL: {lr_gs.best_estimator_.__class__.__name__}")
    print(f"="*80)
    joblib.dump(best_model, 'data/processed/classifier_tuned.pkl')
    joblib.dump(vectorizer, 'data/processed/tfidf_vectorizer_tuned.pkl')
    print(f"Saved to data/processed/classifier_tuned.pkl and tfidf_vectorizer_tuned.pkl")

    # Save hyperparameters for reference
    with open('_tuning_report.txt', 'w', encoding='utf-8') as f:
        f.write("HYPERPARAMETER TUNING REPORT\n")
        f.write("="*80 + "\n\n")
        f.write("LOGISTIC REGRESSION (BEST):\n")
        f.write("-"*80 + "\n")
        for param, value in lr_gs.best_params_.items():
            f.write(f"  {param}: {value}\n")
        f.write(f"  F1-macro CV Score: {lr_gs.best_score_:.3f}\n\n")

        f.write("NAIVE BAYES (ALTERNATIVE):\n")
        f.write("-"*80 + "\n")
        for param, value in nb_gs.best_params_.items():
            f.write(f"  {param}: {value}\n")
        f.write(f"  F1-macro CV Score: {nb_gs.best_score_:.3f}\n")

    print(f"\nTuning report saved to _tuning_report.txt")


if __name__ == '__main__':
    main()
