"""Honest evaluation: GroupKFold-by-merchant OOF, calibration, threshold derivation.

Why grouped: Stratified CV lets the same merchant appear in train AND test, so
"95% accuracy" mostly measures merchant memorization. GroupKFold puts each
merchant's transactions entirely in train OR test — the test folds simulate
genuinely NEW merchants, which is where the model is actually used (rules
already cover known merchants). The audit's honest number: 36.5% (vs 38.5%
majority baseline).

This module produces, from grouped out-of-fold (OOF) predictions:
1. honest accuracy/F1 for the TF-IDF model, the semantic model, and their
   agreement subset,
2. fitted confidence calibrators for both models (see src/calibration.py),
3. a data-derived auto-apply threshold: the smallest t where predictions that
   BOTH models agree on, with min calibrated confidence >= t, reach the target
   precision. If no threshold qualifies, none is saved and the system keeps
   routing everything to review — we never lower the bar silently.

CLI: python src/eval_grouped.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))

from categories import CATEGORY_NORMALIZE, ML_CATEGORIES
from cv_utils import assert_no_group_leakage
from segment import LR_HYPERPARAMS
from calibration import (
    fit_top_label_calibrator,
    apply_calibrator,
    expected_calibration_error,
    reliability_table,
)
from feature_engineering import (
    extract_numeric_features,
    build_hybrid_vectorizers,
    create_hybrid_feature_matrix,
)
from paths import (
    LABELED_TXNS,
    REPORTS,
    SEMANTIC_CALIBRATOR,
    TFIDF_CALIBRATOR,
    ENSEMBLE_CONFIG,
)

# Auto-apply gate defaults. target_precision is a user-confirmed choice:
# "of the predictions we auto-apply, at least 90% must be correct".
DEFAULT_TARGET_PRECISION = 0.90
DEFAULT_MIN_SUPPORT = 30
THRESHOLD_GRID = np.arange(0.50, 0.96, 0.05)

EVAL_REPORT = REPORTS / 'EVAL_GROUPED.txt'


def load_labeled() -> pd.DataFrame:
    """Load labeled rows, normalize categories, ensure a 'time' column exists.

    The labeled CSV uses 'timestamp'; feature_engineering expects 'time'.
    """
    df = pd.read_csv(LABELED_TXNS)
    df = df[df['labeled'] == True].copy()
    df['category'] = df['category'].replace(CATEGORY_NORMALIZE)
    df = df[df['category'].isin(ML_CATEGORIES)]
    if 'time' not in df.columns and 'timestamp' in df.columns:
        df['time'] = df['timestamp']
    return df.reset_index(drop=True)


def _pick_n_splits(groups: np.ndarray, requested: int = 5) -> int:
    return max(2, min(requested, len(np.unique(groups))))


def grouped_oof(df_labeled: pd.DataFrame, model_kind: str,
                encoder=None, n_splits: int = 5) -> pd.DataFrame:
    """Grouped out-of-fold predictions for one model.

    model_kind: 'tfidf' (hybrid features, mirrors retrain.py) or 'semantic'
    (LogisticRegression on encoder embeddings; encoder required).

    Returns a DataFrame aligned to df_labeled's surviving rows with columns:
    row_id (index into df_labeled), y_true, y_pred, raw_conf, merchant.
    """
    df = df_labeled.reset_index(drop=True)

    # Restrict once to rows with valid time/amount so both models see the SAME
    # rows and the agreement frame aligns 1:1.
    numeric_all, valid_idx = extract_numeric_features(df)
    df = df.loc[valid_idx].reset_index(drop=True)
    numeric_all = numeric_all.reset_index(drop=True)

    y = df['category'].reset_index(drop=True)
    groups = df['merchant'].astype(str).values
    n_splits = _pick_n_splits(groups, n_splits)
    gkf = GroupKFold(n_splits=n_splits)

    if model_kind == 'semantic':
        from semantic import build_semantic_texts, embed_texts
        texts = build_semantic_texts(df)

    rows = []
    for tr, te in gkf.split(df, y, groups):
        assert_no_group_leakage(groups, tr, te)
        df_tr, df_te = df.iloc[tr], df.iloc[te]
        y_tr = y.iloc[tr]

        if model_kind == 'tfidf':
            desc_vec, merch_vec = build_hybrid_vectorizers(
                df_tr['description'].tolist(), df_tr['merchant'].tolist())
            X_tr = create_hybrid_feature_matrix(df_tr, desc_vec, merch_vec,
                                                numeric_all.iloc[tr])
            X_te = create_hybrid_feature_matrix(df_te, desc_vec, merch_vec,
                                                numeric_all.iloc[te])
        elif model_kind == 'semantic':
            # LsaEncoder is unsupervised but fit in-fold anyway (strictest);
            # a pretrained static encoder (model2vec) has nothing to fit.
            fold_encoder = encoder
            if hasattr(fold_encoder, 'fit'):
                import copy
                fold_encoder = copy.deepcopy(encoder)
                fold_encoder.fit([texts[i] for i in tr])
            X_tr = embed_texts([texts[i] for i in tr], fold_encoder)
            X_te = embed_texts([texts[i] for i in te], fold_encoder)
        else:
            raise ValueError(f"unknown model_kind: {model_kind}")

        clf = LogisticRegression(**LR_HYPERPARAMS)
        clf.fit(X_tr, y_tr)
        proba = clf.predict_proba(X_te)
        preds = clf.predict(X_te)

        for i, te_i in enumerate(te):
            rows.append({
                'row_id': int(te_i),
                'y_true': y.iloc[te_i],
                'y_pred': preds[i],
                'raw_conf': float(proba[i].max()),
                'merchant': groups[te_i],
            })

    return pd.DataFrame(rows).sort_values('row_id').reset_index(drop=True)


def summarize_oof(oof: pd.DataFrame, label: str) -> dict:
    acc = accuracy_score(oof['y_true'], oof['y_pred'])
    f1m = f1_score(oof['y_true'], oof['y_pred'], average='macro', zero_division=0)
    correct = (oof['y_true'] == oof['y_pred']).astype(int).values
    ece = expected_calibration_error(oof['raw_conf'].values, correct)
    return {'label': label, 'n': len(oof), 'accuracy': acc, 'f1_macro': f1m,
            'ece_raw': ece}


def agreement_frame(oof_tfidf: pd.DataFrame, oof_semantic: pd.DataFrame,
                    cal_tfidf, cal_semantic) -> pd.DataFrame:
    """Row-aligned frame with agreement flag and ensemble confidence.

    ensemble_conf = min of the two CALIBRATED confidences — conservative:
    both models must be confident, not just one.
    """
    t = oof_tfidf.set_index('row_id')
    s = oof_semantic.set_index('row_id')
    common = t.index.intersection(s.index)
    t, s = t.loc[common], s.loc[common]

    conf_t = apply_calibrator(cal_tfidf, t['raw_conf'].values)
    conf_s = apply_calibrator(cal_semantic, s['raw_conf'].values)

    return pd.DataFrame({
        'row_id': common,
        'y_true': t['y_true'].values,
        'pred_tfidf': t['y_pred'].values,
        'pred_semantic': s['y_pred'].values,
        'agree': (t['y_pred'].values == s['y_pred'].values),
        'ensemble_conf': np.minimum(conf_t, conf_s),
        'is_other': (t['y_pred'].values == 'Other'),
        'correct': (t['y_pred'].values == t['y_true'].values),
    })


def derive_threshold(agree_df: pd.DataFrame,
                     target_precision: float = DEFAULT_TARGET_PRECISION,
                     min_support: int = DEFAULT_MIN_SUPPORT,
                     grid: np.ndarray = THRESHOLD_GRID) -> Optional[dict]:
    """Smallest t where agreed, non-Other predictions with conf >= t hit the
    precision target with enough support. None = no safe threshold exists."""
    eligible = agree_df[agree_df['agree'] & ~agree_df['is_other']]
    for t in grid:
        sub = eligible[eligible['ensemble_conf'] >= t]
        if len(sub) >= min_support:
            precision = sub['correct'].mean()
            if precision >= target_precision:
                return {
                    'threshold': round(float(t), 2),
                    'precision': round(float(precision), 4),
                    'coverage': round(len(sub) / len(agree_df), 4),
                    'n': int(len(sub)),
                }
    return None


def threshold_sweep_table(agree_df: pd.DataFrame,
                          grid: np.ndarray = THRESHOLD_GRID) -> pd.DataFrame:
    """Full sweep for the report: what would each threshold auto-apply?"""
    eligible = agree_df[agree_df['agree'] & ~agree_df['is_other']]
    rows = []
    for t in grid:
        sub = eligible[eligible['ensemble_conf'] >= t]
        rows.append({
            'threshold': round(float(t), 2),
            'n_auto_applied': int(len(sub)),
            'precision': round(float(sub['correct'].mean()), 3) if len(sub) else None,
            'silent_errors': int((~sub['correct']).sum()) if len(sub) else 0,
            'coverage_pct': round(100 * len(sub) / max(len(agree_df), 1), 1),
        })
    return pd.DataFrame(rows)


def run_report(df_labeled: pd.DataFrame = None, encoder=None,
               target_precision: float = DEFAULT_TARGET_PRECISION,
               min_support: int = DEFAULT_MIN_SUPPORT,
               paths: dict = None) -> dict:
    """Full honest evaluation. Fits + saves both calibrators; derives + saves
    the ensemble threshold config. Returns a summary dict.

    paths: when given, calibrators/config/report are written to
    paths['tfidf_calibrator']/paths['semantic_calibrator']/
    paths['ensemble_config']/paths['report'] (per-training-run isolation);
    otherwise the global data/reports/ + data/processed/ files (CLI mode).
    """
    if df_labeled is None:
        df_labeled = load_labeled()

    if encoder is None:
        from semantic import get_encoder, fit_lsa_encoder
        encoder = get_encoder(allow_download=False)
        if encoder is None:
            from semantic import build_semantic_texts
            encoder = fit_lsa_encoder(build_semantic_texts(df_labeled))

    lines = [f"GROUPED (HONEST) EVALUATION — {datetime.now():%Y-%m-%d %H:%M:%S}",
             "=" * 70,
             f"Labeled rows: {len(df_labeled)} | unique merchants: "
             f"{df_labeled['merchant'].nunique()}", ""]

    # 1) grouped OOF for both models
    oof_t = grouped_oof(df_labeled, 'tfidf')
    oof_s = grouped_oof(df_labeled, 'semantic', encoder=encoder)

    sum_t = summarize_oof(oof_t, 'tfidf')
    sum_s = summarize_oof(oof_s, 'semantic')

    # 2) calibrators fit on OOF pairs
    cal_t = fit_top_label_calibrator(
        oof_t['raw_conf'].values, (oof_t['y_true'] == oof_t['y_pred']).values)
    cal_s = fit_top_label_calibrator(
        oof_s['raw_conf'].values, (oof_s['y_true'] == oof_s['y_pred']).values)

    for oof, cal, summ in [(oof_t, cal_t, sum_t), (oof_s, cal_s, sum_s)]:
        correct = (oof['y_true'] == oof['y_pred']).astype(int).values
        calibrated = apply_calibrator(cal, oof['raw_conf'].values)
        summ['ece_calibrated'] = expected_calibration_error(calibrated, correct)

    for summ in (sum_t, sum_s):
        lines.append(
            f"{summ['label']:10s}: grouped acc {summ['accuracy']:.1%} | "
            f"F1-macro {summ['f1_macro']:.3f} | "
            f"ECE raw {summ['ece_raw']:.3f} → calibrated {summ['ece_calibrated']:.3f}")

    # 3) agreement + threshold
    agree_df = agreement_frame(oof_t, oof_s, cal_t, cal_s)
    agree_rate = agree_df['agree'].mean()
    agree_acc = agree_df.loc[agree_df['agree'], 'correct'].mean() if agree_df['agree'].any() else 0.0
    lines += ["", f"Models agree on {agree_rate:.1%} of rows; "
                  f"accuracy when they agree: {agree_acc:.1%}", "",
              "Threshold sweep (agreed, non-Other predictions):"]
    sweep = threshold_sweep_table(agree_df)
    lines.append(sweep.to_string(index=False))

    chosen = derive_threshold(agree_df, target_precision, min_support)
    if chosen:
        lines += ["", f"CHOSEN threshold: {chosen['threshold']} "
                      f"(precision {chosen['precision']:.1%}, "
                      f"auto-applies {chosen['n']} rows = {chosen['coverage']:.1%} coverage)"]
    else:
        lines += ["", f"NO threshold reaches {target_precision:.0%} precision with "
                      f">= {min_support} rows. Auto-apply stays OFF; all model "
                      f"predictions continue to route to review (honest outcome)."]

    # 4) persist artifacts
    report_path = paths['report'] if paths else EVAL_REPORT
    tfidf_cal_path = paths['tfidf_calibrator'] if paths else TFIDF_CALIBRATOR
    semantic_cal_path = paths['semantic_calibrator'] if paths else SEMANTIC_CALIBRATOR
    ensemble_config_path = paths['ensemble_config'] if paths else ENSEMBLE_CONFIG

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding='utf-8')

    joblib.dump(cal_t, tfidf_cal_path)
    joblib.dump(cal_s, semantic_cal_path)

    config = {
        'threshold': chosen['threshold'] if chosen else None,
        'target_precision': target_precision,
        'min_support': min_support,
        'exclude_other': True,
        'stats': {'tfidf': {k: round(float(v), 4) for k, v in sum_t.items() if k != 'label'},
                  'semantic': {k: round(float(v), 4) for k, v in sum_s.items() if k != 'label'},
                  'agreement_rate': round(float(agree_rate), 4)},
        'encoder_kind': type(encoder).__name__,
        'n_labeled': int(len(df_labeled)),
        'created': datetime.now().isoformat(timespec='seconds'),
    }
    ensemble_config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    print("\n".join(lines))
    print(f"\nReport: {report_path}\nConfig: {ensemble_config_path}")
    return {'tfidf': sum_t, 'semantic': sum_s, 'threshold': chosen,
            'agreement_rate': agree_rate}


if __name__ == '__main__':
    run_report()
