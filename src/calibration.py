"""Confidence calibration: make "0.9 confident" actually mean ~90% correct.

Why this exists: the audit (docs/FULL_AUDIT.md Phase 4) showed the classifier's
raw predict_proba is badly miscalibrated on merchants it has never seen —
predictions in the 0.8-0.9 confidence bin were only ~44% correct (ECE 0.184).
A confidence number that lies is worse than none, because downstream routing
decisions (auto-apply vs review) depend on it.

Approach: **top-label Platt scaling.** Collect (raw max-confidence, was-correct)
pairs from grouped out-of-fold predictions (so they reflect *unseen-merchant*
behavior), then fit a 1-feature logistic regression mapping raw confidence →
P(correct). This is:
- monotonic by construction (higher raw conf → higher calibrated conf),
- immune to tiny-class sparsity (it never looks at class labels, only
  "was the top prediction right"), unlike per-class CalibratedClassifierCV,
- deliberately simple — sigmoid, not isotonic, because isotonic overfits
  below ~1000 samples and we have a few hundred.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression


def fit_top_label_calibrator(raw_conf: np.ndarray, correct: np.ndarray):
    """Fit P(correct | raw max-confidence) via 1-feature logistic regression.

    Args:
        raw_conf: raw predict_proba().max(axis=1) values from OOF predictions.
        correct:  1/0 (or bool) — whether the top prediction was right.

    Returns a fitted LogisticRegression, or None if the data is degenerate
    (fewer than 10 pairs, or all-correct / all-wrong — nothing to fit).
    """
    raw_conf = np.asarray(raw_conf, dtype=float).reshape(-1, 1)
    correct = np.asarray(correct, dtype=int)

    if len(raw_conf) < 10 or len(np.unique(correct)) < 2:
        return None

    cal = LogisticRegression(random_state=42)
    cal.fit(raw_conf, correct)
    return cal


def apply_calibrator(calibrator, raw_conf: np.ndarray) -> np.ndarray:
    """Map raw confidences → calibrated P(correct).

    Identity passthrough when calibrator is None, so callers never branch.
    """
    raw_conf = np.asarray(raw_conf, dtype=float)
    if calibrator is None:
        return raw_conf
    return calibrator.predict_proba(raw_conf.reshape(-1, 1))[:, 1]


def expected_calibration_error(conf: np.ndarray, correct: np.ndarray,
                               n_bins: int = 10) -> float:
    """ECE: bin predictions by confidence; weighted mean |accuracy - confidence|.

    0 = perfectly calibrated. The audit measured 0.184 on unseen merchants.
    (Same binning as docs/phase4_analysis.py reliability().)
    """
    conf = np.asarray(conf, dtype=float)
    correct = np.asarray(correct, dtype=int)
    ece = 0.0
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        m = (conf >= lo) & (conf <= hi) if i == n_bins - 1 else (conf >= lo) & (conf < hi)
        n = int(m.sum())
        if n == 0:
            continue
        ece += (n / len(conf)) * abs(correct[m].mean() - conf[m].mean())
    return float(ece)


def reliability_table(conf: np.ndarray, correct: np.ndarray,
                      n_bins: int = 10) -> pd.DataFrame:
    """Per-bin reliability breakdown (promoted from docs/phase4_analysis.py,
    returning a DataFrame instead of printing)."""
    conf = np.asarray(conf, dtype=float)
    correct = np.asarray(correct, dtype=int)
    rows = []
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        m = (conf >= lo) & (conf <= hi) if i == n_bins - 1 else (conf >= lo) & (conf < hi)
        n = int(m.sum())
        if n == 0:
            continue
        rows.append({
            'bin_lo': round(lo, 2), 'bin_hi': round(hi, 2), 'n': n,
            'accuracy': round(float(correct[m].mean()), 3),
            'mean_conf': round(float(conf[m].mean()), 3),
            'gap': round(float(abs(correct[m].mean() - conf[m].mean())), 3),
        })
    return pd.DataFrame(rows)
