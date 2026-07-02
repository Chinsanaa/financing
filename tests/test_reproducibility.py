"""Reproducibility: same seed → identical metrics; and validation sanity."""
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, GroupKFold
from sklearn.metrics import accuracy_score, f1_score

from segment import build_vectorizer, vectorize, clean_text, LR_HYPERPARAMS


def _run_cv(df, seed=42, group_by_merchant=False):
    """Deterministic CV over the synthetic frame; returns (accuracy, f1_macro)."""
    texts = df.apply(lambda r: clean_text(r["merchant"], r["description"]), axis=1).tolist()
    y = df["category"].reset_index(drop=True)
    y_true, y_pred = [], []
    if group_by_merchant:
        splitter = GroupKFold(n_splits=4)
        splits = splitter.split(texts, y, df["merchant"].values)
    else:
        splitter = StratifiedKFold(n_splits=4, shuffle=True, random_state=seed)
        splits = splitter.split(texts, y)
    for tr, te in splits:
        vec = build_vectorizer([texts[i] for i in tr])
        Xtr = vectorize([texts[i] for i in tr], vec)
        Xte = vectorize([texts[i] for i in te], vec)
        clf = LogisticRegression(**LR_HYPERPARAMS)
        clf.fit(Xtr, y.iloc[tr])
        y_true.extend(y.iloc[te]); y_pred.extend(clf.predict(Xte))
    return accuracy_score(y_true, y_pred), f1_score(y_true, y_pred, average="macro", zero_division=0)


def test_identical_metrics_across_runs(synthetic_labeled):
    a1 = _run_cv(synthetic_labeled, seed=42)
    a2 = _run_cv(synthetic_labeled, seed=42)
    assert a1 == a2, f"Non-deterministic metrics with fixed seed: {a1} vs {a2}"


def test_lr_hyperparams_pin_random_state():
    # A missing random_state is the classic silent source of run-to-run drift.
    assert LR_HYPERPARAMS.get("random_state") == 42


def test_groupkfold_metrics_also_deterministic(synthetic_labeled):
    g1 = _run_cv(synthetic_labeled, group_by_merchant=True)
    g2 = _run_cv(synthetic_labeled, group_by_merchant=True)
    assert g1 == g2
