# FULL AUDIT — Honest Evaluation & Reproducibility

**Started:** 2026-07-02 · **Status: Phase 0 complete, awaiting user confirmation before Phase 1**

Goal: establish the REAL metrics of the transaction classifier, reconcile the
contradictory numbers in the docs, test for evaluation leakage, and make the
pipeline reproducible. Not a vanity-metrics exercise — if a past "improvement"
was an artifact, this document says so plainly.

---

## Phase 0 — Ground truth (what the scripts actually produce today)

### How this was run (important caveat)

All personal transaction data was purged from the working tree in Session 19,
so the repo as checked out has **no data to train on**. However, the data was
only `git rm`-ed — it still exists in git history. For this audit the last
committed snapshot (commit `ded9330^`, dataset last updated 2026-07-01) was
restored **locally into gitignored paths only** (`data/labeled/`,
`data/processed/`). It is not committed, and `git status` stays clean.

> ⚠️ **Side-finding (privacy):** the Session 19 "purge" removed personal data
> from the working tree but **not from git history**. Anyone who clones the
> GitHub repo can recover `data/labeled/labeled_transactions.csv`, raw
> Alipay/WeChat exports, and budget config with one `git show` command.
> Truly removing them requires a history rewrite (`git filter-repo`) and a
> force-push. **Decision needed from user — out of scope for this audit.**

Environment: Python 3.11, scikit-learn 1.9.0, jieba 0.42.1.
All three scripts already fix `random_state=42` (train/test split, KFold
shuffle, LogisticRegression), so runs are internally deterministic.

### Real numbers (run 2026-07-02, random_state=42)

**Dataset:** `labeled_transactions.csv` = 899 rows, **863 with `labeled == True`**
(the docs' "776" and "850" are both stale). `transactions.csv` = 901 rows.

**TF-IDF features: 663** (docs say 275 and 639; the old committed
TRAINING_REPORT.txt says 657 — small drift is expected because `min_df=2`
feature pruning shifts when jieba's dictionary version changes tokenization).

| Script | CV scheme it actually uses | Accuracy | F1-weighted | F1-macro |
|---|---|---|---|---|
| `train.py` | Single stratified 80/20 holdout (rs=42) | **94.2%** | 0.955 (report wtd avg) | 0.828 |
| `eval.py` | StratifiedKFold, k = min(5, smallest class) = 5, shuffle, rs=42 | **96.5% ± 1.8%** | 0.967 | 0.857 |
| `retrain.py` | StratifiedKFold(5), shuffle, rs=42 | **96.5%** (fold range ±4.6%) | 0.967 | 0.857 |

Two evaluation-hygiene issues already visible from reading the scripts
(evidence gathering is Phase 1, flagged here for the record):

1. **Vectorizer fit on ALL labeled data before splitting/CV** in all three
   scripts — test-fold text influences the vocabulary and IDF weights.
2. **`retrain.py`'s "Per-Category Performance" section is in-sample**: it
   trains the final model on 100% of the data and then scores it on that same
   data. That block (and the per-category table in
   `data/reports/TRAINING_REPORT.txt`) is systematically inflated and should
   never be quoted as accuracy.

### Per-category metrics — honest (out-of-fold, eval.py, pooled over 5 folds)

| Category | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Eating Out | 0.970 | 0.964 | 0.967 | 332 |
| Groceries | 0.996 | 0.981 | 0.989 | 269 |
| Transportation | 1.000 | 1.000 | **1.000** | 169 |
| Shopping | 0.962 | 0.927 | 0.944 | 55 |
| Transfers & Gifts | 0.778 | 0.955 | 0.857 | 22 |
| Other | 0.214 | 0.273 | **0.240** | 11 |
| Utilities & Services | 1.000 | 1.000 | **1.000** | 5 |

Contrast with the same categories scored **in-sample** by `retrain.py`
(the numbers that end up in TRAINING_REPORT.txt): Other jumps 0.240 → 0.786,
Eating Out 0.967 → 0.992. In-sample flattery, not real performance.

Notes:
- There is **no Travel or Health & Wellness class in the final dataset** —
  old docs referencing Travel F1=1.000 describe a category that was merged
  away before the last commit.
- Utilities & Services has **5 samples** → exactly 1 per fold under 5-fold
  CV. Its F1 = 1.000 is statistically meaningless (Phase 1 will quantify).
- **342 of the 863 labeled rows are exact duplicates** of another row's
  (merchant, description) pair. Duplicates straddle train/test folds, so
  every reported number above is still optimistic. Quantifying this — plus
  merchant-level leakage via GroupKFold — is the core of Phase 1.

### Calibration & baseline (eval.py, honest out-of-fold)

- Majority-class baseline: 38.5%
- Mean confidence when correct: **0.932**; when wrong: **0.535** (README's
  "82.4% vs 41.7%" is stale)
- Brier score 0.027

---

## Documented vs Actual

Every figure in README.md / context.md / doc history that disagrees with the
scripts as of 2026-07-02:

| Claim (where) | Documented | Actual (rs=42, 2026-07-02) | Verdict |
|---|---|---|---|
| Single-split test accuracy (old READMEs, "99.1% on 109 test samples") | 99.1% | **94.2%** on 173 test samples | Stale — from a 544-label-era run; also single-split is the metric the project itself already disavowed |
| "Retraining: 97.3% accuracy" (old README/context) | 97.3% | **96.5%** (stratified CV) | Stale intermediate run |
| "Real accuracy 95.5% (stratified CV)" (current README, 3 places) | 95.5% | **96.5% ± 1.8%** | Stale (pre-dates last labeling rounds) |
| "Accuracy on this task: 96.2%" (README model-comparison table) | 96.2% | 96.5% | Closest to true; from committed TRAINING_REPORT.txt (861 samples, 657 features) |
| TF-IDF features (old docs: "275 extracted") | 275 | **663** | Stale — pre-Session-8B, max_features=500, no bigrams |
| TF-IDF features ("639 features with bigrams") | 639 | **663** | Stale — dataset and jieba version drift since that run |
| Labeled training rows ("776 labeled") | 776 | **863** | Stale |
| Labeled training rows ("850 labeled samples") | 850 | **863** | Stale |
| Transfers & Gifts sample count (README: "27 samples") | 27 | **22** | Stale |
| Confidence correct vs wrong (README: 82.4% vs 41.7%) | 82.4 / 41.7 | **93.2 / 53.5** | Stale |
| "F1-macro +39%" from class_weight='balanced' (README) | +39% | not re-verified | Unverified — needs an unweighted baseline run (Phase 4 if wanted) |
| Per-category F1 in TRAINING_REPORT.txt | e.g. Other 0.79 | **Other 0.240** out-of-fold | **Misleading by construction** — that report section is in-sample |

**Summary judgment:** there was never one lie, but the docs quote at least five
different training runs from different dataset sizes as if they were one
number. The only defensible headline today is **96.5% ± 1.8% accuracy /
0.857 F1-macro under stratified 5-fold CV** — and Phase 1 exists because even
that number is suspect (duplicate rows + merchant memorization + vectorizer
fit before splitting all inflate it).

---

## Phase 1 — Evaluation integrity *(pending user confirmation)*

Planned: GroupKFold by merchant vs stratified CV; per-fold support for tiny
classes; rule-covered vs model-only accuracy split; hand-audit of 40 random
labels for label noise.

## Phase 2 — Tiny-class handling *(pending)*

## Phase 3 — Tests & reproducibility *(pending)*

## Phase 4 — Calibration & honest tuning *(pending)*

## Phase 5 — Doc reconciliation *(pending)*
