"""
PHASE 5: Test ensemble models (LR + NB voting).
Sometimes combining models helps when individual models have different strengths.
"""
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import f1_score, accuracy_score, classification_report
import warnings

warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent))
from segment import vectorize, build_vectorizer, clean_text


def load_data():
    """Load labeled transactions."""
    df = pd.read_csv('data/labeled/labeled_transactions.csv')
    df = df[df['labeled'] == True].copy()
    df['text'] = df.apply(
        lambda row: clean_text(row['merchant'], row['description']),
        axis=1
    )
    return df


def build_feature_matrix(df):
    """Build feature matrix."""
    vectorizer = build_vectorizer(df['text'].tolist(), max_features=500)
    X = vectorize(df['text'].tolist(), vectorizer)
    y = df['category']

    # Filter categories with < 2 samples
    valid_categories = y.value_counts()[y.value_counts() >= 2].index
    mask = y.isin(valid_categories).values
    X = X[mask]
    y = y[mask]

    return X, y, vectorizer


class EnsembleVoter:
    """Soft voting ensemble: LR + NB with confidence averaging."""

    def __init__(self):
        self.lr = None
        self.nb = None

    def fit(self, X, y):
        """Train both models."""
        self.lr = LogisticRegression(
            C=10, solver='lbfgs', class_weight='balanced',
            max_iter=1000, random_state=42
        )
        self.nb = MultinomialNB(alpha=0.1, fit_prior=True)
        self.lr.fit(X, y)
        self.nb.fit(X, y)
        self.classes_ = self.lr.classes_
        return self

    def predict(self, X):
        """Predict using soft voting (average probabilities)."""
        lr_proba = self.lr.predict_proba(X)
        nb_proba = self.nb.predict_proba(X)

        # Average probabilities
        avg_proba = (lr_proba + nb_proba) / 2
        return self.classes_[np.argmax(avg_proba, axis=1)]

    def predict_proba(self, X):
        """Return averaged probabilities."""
        lr_proba = self.lr.predict_proba(X)
        nb_proba = self.nb.predict_proba(X)
        return (lr_proba + nb_proba) / 2


def evaluate_models(X, y):
    """Compare LR vs NB vs Ensemble."""
    print("\n" + "="*80)
    print("COMPARING SINGLE MODELS vs ENSEMBLE")
    print("="*80)

    n_splits = min(2, min(y.value_counts()))
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    models = [
        ('Logistic Regression (tuned)', LogisticRegression(
            C=10, solver='lbfgs', class_weight='balanced',
            max_iter=1000, random_state=42
        )),
        ('Naive Bayes (tuned)', MultinomialNB(alpha=0.1, fit_prior=True)),
        ('Ensemble (LR + NB voting)', EnsembleVoter()),
    ]

    results = {}

    for model_name, model in models:
        print(f"\n{model_name}")
        print("-" * 80)

        f1_scores = []
        acc_scores = []
        per_cat_f1 = {cat: [] for cat in y.unique()}

        for fold_idx, (train_idx, test_idx) in enumerate(skf.split(X, y.values), 1):
            X_train = X[train_idx].tocsr() if hasattr(X[train_idx], 'tocsr') else X[train_idx]
            X_test = X[test_idx].tocsr() if hasattr(X[test_idx], 'tocsr') else X[test_idx]
            y_train = y.iloc[train_idx]
            y_test = y.iloc[test_idx]

            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
            acc = accuracy_score(y_test, y_pred)
            f1_scores.append(f1)
            acc_scores.append(acc)

            print(f"  Fold {fold_idx}: Accuracy={acc:.3f}, F1-weighted={f1:.3f}")

            # Per-category
            for cat in y.unique():
                mask_true = (y_test == cat).values
                mask_pred = (y_pred == cat)
                if mask_true.sum() > 0:
                    tp = (mask_true & mask_pred).sum()
                    fp = (~mask_true & mask_pred).sum()
                    fn = (mask_true & ~mask_pred).sum()
                    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
                    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
                    f1_cat = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                    per_cat_f1[cat].append(f1_cat)

        results[model_name] = {
            'f1': np.mean(f1_scores),
            'acc': np.mean(acc_scores),
            'f1_std': np.std(f1_scores),
            'acc_std': np.std(acc_scores),
            'per_cat_f1': {cat: np.mean(scores) for cat, scores in per_cat_f1.items() if scores}
        }

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    best_model = None
    best_f1 = -1

    for name, data in results.items():
        print(f"\n{name}:")
        print(f"  Accuracy:    {data['acc']:.3f} ± {data['acc_std']:.3f}")
        print(f"  F1-weighted: {data['f1']:.3f} ± {data['f1_std']:.3f}")

        if data['f1'] > best_f1:
            best_f1 = data['f1']
            best_model = name

    print(f"\n{'='*80}")
    print(f"WINNER: {best_model} (F1={best_f1:.3f})")
    print(f"{'='*80}")

    # Per-category comparison
    print(f"\n{'='*80}")
    print("PER-CATEGORY F1 SCORES")
    print(f"{'='*80}")

    categories = sorted(y.unique())
    print(f"\n{'Category':<30} {'LR':>10} {'NB':>10} {'Ensemble':>10}")
    print("-" * 62)

    for cat in categories:
        lr_f1 = results.get('Logistic Regression (tuned)', {}).get('per_cat_f1', {}).get(cat, 0)
        nb_f1 = results.get('Naive Bayes (tuned)', {}).get('per_cat_f1', {}).get(cat, 0)
        ens_f1 = results.get('Ensemble (LR + NB voting)', {}).get('per_cat_f1', {}).get(cat, 0)
        print(f"{cat:<30} {lr_f1:>10.3f} {nb_f1:>10.3f} {ens_f1:>10.3f}")

    # Check if ensemble helps minorities
    print(f"\n{'='*80}")
    print("DOES ENSEMBLE HELP MINORITY CATEGORIES?")
    print(f"{'='*80}")

    minorities = ['Shopping', 'Transfers & Gifts', 'Travel', 'Other']
    ensemble_wins = 0

    for cat in minorities:
        lr_f1 = results.get('Logistic Regression (tuned)', {}).get('per_cat_f1', {}).get(cat, 0)
        ens_f1 = results.get('Ensemble (LR + NB voting)', {}).get('per_cat_f1', {}).get(cat, 0)
        delta = ens_f1 - lr_f1
        sign = "✅" if delta > 0.01 else "❌" if delta < -0.01 else "➖"
        if delta > 0.01:
            ensemble_wins += 1
        print(f"  {sign} {cat:30s}: {lr_f1:.3f} → {ens_f1:.3f} ({delta:+.3f})")

    print(f"\nEnsemble wins on {ensemble_wins}/4 minority categories")

    if ensemble_wins >= 2:
        print("✅ Ensemble shows promise—consider using it for production")
    else:
        print("❌ Ensemble doesn't help—stick with tuned Logistic Regression")


def main():
    print("="*80)
    print("PHASE 5: ENSEMBLE MODEL TESTING")
    print("="*80)

    df = load_data()
    print(f"\nLoaded {len(df)} labeled transactions")

    X, y, vectorizer = build_feature_matrix(df)
    print(f"Feature matrix: {X.shape}")

    evaluate_models(X, y)

    print(f"\n{'='*80}")
    print("Ensemble testing complete!")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
