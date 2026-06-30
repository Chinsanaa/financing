"""
PHASE 4: Advanced feature engineering beyond TF-IDF.
Simplified version that works with indices properly.
"""
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import f1_score, accuracy_score
from scipy.sparse import hstack, csr_matrix
import warnings

warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent))
from segment import vectorize, build_vectorizer, clean_text


def load_data():
    """Load labeled transactions."""
    df = pd.read_csv('data/labeled/labeled_transactions.csv')
    df = df[df['labeled'] == True].copy()

    # Parse timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=False)
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['month'] = df['timestamp'].dt.month

    # Clean text
    df['text'] = df.apply(
        lambda row: clean_text(row['merchant'], row['description']),
        axis=1
    )

    return df


def engineer_features(df):
    """Engineer features: amount, time, merchant."""
    df = df.copy()

    # Amount bins
    df['amount_bin'] = pd.cut(
        df['amount'],
        bins=[0, 10, 30, 100, 500, 2000, 100000],
        labels=['micro', 'small', 'medium', 'large', 'xlarge', 'xxlarge']
    )

    # Hour bins
    df['hour_bin'] = pd.cut(
        df['hour'],
        bins=[0, 6, 12, 18, 24],
        labels=['night', 'morning', 'afternoon', 'evening'],
        include_lowest=True
    )

    # Day of week
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    df['day_name'] = df['day_of_week'].map({i: day_names[i] for i in range(7)})

    # Merchant length
    df['merchant_len'] = df['merchant'].fillna('').str.len()

    return df


def create_feature_matrices(df, vectorizer):
    """Create text-only and enhanced feature matrices."""
    # Text features
    X_text = vectorize(df['text'].tolist(), vectorizer)

    # Categorical features
    X_cat = pd.get_dummies(
        df[['amount_bin', 'hour_bin', 'day_name']],
        columns=['amount_bin', 'hour_bin', 'day_name'],
        drop_first=False
    )

    # Numerical features (scaled)
    X_num = df[['amount', 'merchant_len']].values
    scaler = StandardScaler()
    X_num_scaled = scaler.fit_transform(X_num)

    # Enhanced = Text + Categorical + Numerical
    X_enhanced = hstack([X_text, X_cat.values, X_num_scaled])

    return X_text, X_enhanced


def evaluate_models(X_text, X_enhanced, y):
    """Compare text-only vs enhanced models."""
    print("\n" + "="*80)
    print("COMPARING TEXT-ONLY vs ENHANCED FEATURES")
    print("="*80)

    # Filter to valid categories
    valid_categories = y.value_counts()[y.value_counts() >= 2].index
    mask_array = np.array([cat in valid_categories for cat in y])
    y_filtered = y[mask_array].reset_index(drop=True)

    # Filter features
    X_text_filtered = X_text.tocsr()[np.where(mask_array)[0]] if hasattr(X_text, 'tocsr') else X_text[mask_array]
    X_enhanced_filtered = X_enhanced.tocsr()[np.where(mask_array)[0]] if hasattr(X_enhanced, 'tocsr') else X_enhanced[mask_array]

    n_splits = min(2, min(y_filtered.value_counts()))
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    results = {}

    for model_name, X in [('Text-only', X_text_filtered), ('Enhanced', X_enhanced_filtered)]:
        print(f"\n{model_name}")
        print("-" * 80)

        f1_list = []
        acc_list = []
        per_cat_f1 = {cat: [] for cat in valid_categories}

        for fold_idx, (train_idx, test_idx) in enumerate(skf.split(X, y_filtered.values), 1):
            X_train = X[train_idx].tocsr() if hasattr(X[train_idx], 'tocsr') else X[train_idx]
            X_test = X[test_idx].tocsr() if hasattr(X[test_idx], 'tocsr') else X[test_idx]
            y_train = y_filtered.iloc[train_idx]
            y_test = y_filtered.iloc[test_idx]

            clf = LogisticRegression(
                C=10, solver='lbfgs', class_weight='balanced',
                max_iter=1000, random_state=42
            )
            clf.fit(X_train, y_train)
            y_pred = clf.predict(X_test)

            f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
            acc = accuracy_score(y_test, y_pred)
            f1_list.append(f1)
            acc_list.append(acc)

            print(f"  Fold {fold_idx}: Accuracy={acc:.3f}, F1={f1:.3f}")

            # Per-category
            for cat in valid_categories:
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
            'f1': np.mean(f1_list),
            'acc': np.mean(acc_list),
            'per_cat_f1': {cat: np.mean(scores) for cat, scores in per_cat_f1.items() if scores}
        }

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    for name, data in results.items():
        print(f"\n{name}:")
        print(f"  Accuracy:    {data['acc']:.3f}")
        print(f"  F1-weighted: {data['f1']:.3f}")

    # Per-category gains
    print(f"\n{'='*80}")
    print("PER-CATEGORY IMPROVEMENTS")
    print(f"{'='*80}")

    text_result = results.get('Text-only', {}).get('per_cat_f1', {})
    enhanced_result = results.get('Enhanced', {}).get('per_cat_f1', {})

    for cat in sorted(valid_categories):
        text_f1 = text_result.get(cat, 0)
        enh_f1 = enhanced_result.get(cat, 0)
        delta = enh_f1 - text_f1
        pct = (delta / max(text_f1, 0.001) * 100)

        sign = "✅" if delta > 0.01 else "❌" if delta < -0.01 else "➖"
        print(f"  {sign} {cat:30s}: {text_f1:.3f} → {enh_f1:.3f} ({delta:+.3f}, {pct:+.0f}%)")

    # Overall gain
    text_f1_overall = results.get('Text-only', {}).get('f1', 0)
    enh_f1_overall = results.get('Enhanced', {}).get('f1', 0)
    print(f"\n  Overall F1-weighted improvement: {text_f1_overall:.3f} → {enh_f1_overall:.3f} ({enh_f1_overall - text_f1_overall:+.3f})")


def main():
    print("="*80)
    print("PHASE 4: ADVANCED FEATURE ENGINEERING")
    print("="*80)

    df = load_data()
    print(f"\nLoaded {len(df)} labeled transactions")

    # Engineer features
    print(f"\n1. Engineering features...")
    df = engineer_features(df)

    # Build vectorizer
    print(f"2. Building TF-IDF vectorizer...")
    vectorizer = build_vectorizer(df['text'].tolist(), max_features=500)
    print(f"   Features: {vectorizer.get_feature_names_out().shape[0]}")

    # Create feature matrices
    print(f"3. Creating feature matrices...")
    X_text, X_enhanced = create_feature_matrices(df, vectorizer)
    print(f"   Text-only: {X_text.shape}")
    print(f"   Enhanced: {X_enhanced.shape}")

    # Evaluate
    y = df['category']
    evaluate_models(X_text, X_enhanced, y)

    print(f"\n{'='*80}")
    print("Feature engineering analysis complete!")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
