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

## Phase 1 — Evaluation integrity

**Status: complete, awaiting user confirmation before Phase 2.**
Run 2026-07-02, random_state=42, on the same restored 863-row dataset.

### Headline finding: the 96.5% is almost entirely merchant memorization

The dataset has **863 labeled rows but only 109 unique merchants**. The top 10
merchants account for **73%** of all rows; one merchant (上海纽约大学 / NYU
Shanghai, generic campus QR payments) is **16.5%** of the entire dataset. 63
merchants appear exactly once. So "863 samples" is mostly the same handful of
merchants repeated — and **568 of 863 cleaned texts are exact duplicates** of
another row.

The cleaned text fed to TF-IDF **always begins with the merchant name**
(`clean_text` concatenates merchant + description), e.g.
`滴滴出行 滴滴快车打车...`. So the model can trivially memorize merchant→category.

**The decisive test — cross-validation that never lets a merchant appear in
both train and test:**

| CV scheme | Accuracy | F1-macro | What it measures |
|---|---|---|---|
| Stratified 5-fold, vectorizer fit on ALL (what `eval.py`/`retrain.py` report) | **96.5% ± 1.8%** | 0.857 | inflated |
| Stratified 5-fold, vectorizer fit in-fold | 95.4% ± 2.2% | 0.834 | removes the vectorizer leak (~1pt) |
| **GroupKFold(5) by merchant, vectorizer in-fold** | **36.5% ± 25.6%** | ~0.34 | **generalization to NEW merchants** |
| Majority-class baseline (always "Eating Out") | 38.5% | — | the floor |

**Interpretation (plain language):** on a merchant it has already seen, the
model is ~96% right — because it memorized that merchant's category. On a
merchant it has **never** seen, it scores **36.5%, which is *below* the 38.5%
you'd get by blindly guessing "Eating Out" every time.** Roughly **60
percentage points** of the reported accuracy is merchant memorization, not
generalization. The huge ±25.6% fold variance confirms it: a fold's score
depends almost entirely on whether a big known merchant happened to land in the
test set.

This does not mean the *product* is worthless — for a merchant you've
transacted with before, memorization is genuinely useful and a rule handles it
anyway. But the ML model, as an engine for categorizing **new/unseen**
merchants, currently adds essentially nothing. The 96.5% headline must never be
presented as the model's real-world accuracy on new data.

### The 1.000 scores are artifacts

`<15`-sample classes are **Other (11)** and **Utilities & Services (5)** (no
Travel or Health class exists in this dataset at all).

- **Utilities & Services, F1 = 1.000 → fake.** It is 5 rows but only **2
  unique texts** (mostly 中国移动 / China Mobile phone top-ups; 3 of 5 rows are
  duplicate text). Under stratified CV it gets exactly 1 test row per fold and
  its duplicate/same-merchant twins sit in the training fold → guaranteed
  correct. Under **GroupKFold all 5 rows fall in a single fold `[5,0,0,0,0]`
  and F1 collapses to 0.000** — the model has never seen the merchant, so it
  never gets it right. The 1.000 is a near-empty-fold + duplicate artifact.
- **Other, F1 = 0.240 even under stratified CV** (11 unique-text rows). It is
  genuinely a hard grab-bag class, not inflated — just tiny and incoherent.

### Rule-covered vs model-only

Applying the 177 merchant rules back onto the labeled rows: **91.2% (787 rows)
are already matched by a merchant rule** — unsurprising, since the labels were
*seeded from those rules*. Only **76 rows (8.8%) are "model-only"** (no rule
matches). Under honest GroupKFold out-of-fold prediction:

- Overall: 36.5%
- On rule-covered merchants: 39.0% (moot — a rule already labels these)
- **On model-only merchants: 10.5%** (n=76) ← the real, honest value the ML
  model adds over the rules on unseen merchants: close to zero.

### Label-noise audit (random 40 rows, seed 42)

No outright category errors of the old "McDonald's → Transportation" kind were
found in the 40-row sample → **outright label-error rate ≈ 0–3%; labels are
clean.** But the real label-quality risk is **concentration, not noise**:

- **139 rows (16.5% of the whole dataset) are `上海纽约大学 POS机扫微信二维码消费`
  (NYU Shanghai generic campus QR payment), all blanket-labeled "Eating Out".**
  This is one human assumption applied 139 times, not 139 observations. If the
  campus POS is used for anything besides the canteen (printing, bookstore,
  vending), those are silently mislabeled. It is defensible but unverifiable
  from the text alone, and it dominates the Eating Out class.
- Minor borderline calls (not errors): `淘宝闪购` food delivery labeled Eating
  Out (vs Shopping); single-beverage purchases (Pocari/Pepsi) at 大黄鹅 labeled
  Groceries; generic `收钱码收款` payment-code rows.

**Net:** label noise is low, but ~1/6 of the data is a single blanket-labeled
merchant, which both inflates apparent accuracy and makes the Eating Out class
fragile.

### Phase 1 bottom line

The prior "improvements" chased a metric (stratified CV on a merchant-memorized,
duplicate-heavy, 109-merchant dataset) that never measured generalization. The
honest numbers: **~96% at re-recognizing known merchants, ~36% (below baseline)
on new ones, ~0 added value over rules on unseen merchants.** Tiny-class 1.000
scores are duplicate/empty-fold artifacts. This is what Phase 2 must address.

## Phase 2 — Tiny-class handling & two-stage design *(proposal — awaiting user decision, nothing implemented)*

Correction from the brief: **Travel and Health & Wellness do not exist in this
dataset.** The only `<15`-sample classes are:

| Class | Rows | Unique texts | Stratified F1 | GroupKFold F1 | Character |
|---|---|---|---|---|---|
| Other | 11 | 11 | 0.240 | 0.056 | genuine grab-bag, incoherent by design |
| Utilities & Services | 5 | 2 | 1.000 (artifact) | 0.000 | semantically clean (中国移动 phone top-ups) but tiny |

### Options for the tiny classes

**Option A — Merge into a single "Misc/Other" bucket.**
Fold Utilities & Services into Other so the classifier never faces a 5-sample
class.
- *Pro:* removes the fake 1.000; simplifies the label space.
- *Con:* destroys a **meaningful, clean budget line** — "how much did I spend on
  phone/utilities" is exactly the kind of thing this dashboard exists to show.
  Utilities is coherent (它's a real category with a high-precision rule), so
  merging it into a grab-bag throws away signal to fix a metric artifact. Wrong
  trade for a personal-finance tool.

**Option B — Keep them rule-only (model never predicts them).**
Utilities & Services (and any other genuinely rare, rule-coverable category) is
assigned **only** by explicit high-precision merchant rules (中国移动 → Utilities),
never by the model. The model's label space drops these classes entirely.
- *Pro:* honest — the model stops pretending to predict a class it has 2 unique
  texts for; the fake 1.000 disappears; the category still shows up correctly in
  the dashboard via the rule; deterministic and interpretable.
- *Con:* a **new** utility merchant not yet in the rules won't be auto-caught —
  it falls through to the review queue. But Phase 1 already proved the model
  can't catch new merchants anyway (10.5% on model-only rows), so this loses
  nothing real and makes the behavior explicit instead of pretend.

**Option C — Collect more labels before predicting them.**
Freeze these categories out of the model until each has, say, 20–30 labeled
rows, then revisit.
- *Pro:* the "correct" ML answer in the abstract.
- *Con:* utilities/rare spend may **never** accumulate 30 rows for a single
  user; blocks indefinitely; and even at 30 rows the merchant-memorization
  problem from Phase 1 remains. High effort, uncertain payoff.

### Recommendation

**Option B (rule-only for tiny high-precision classes), and treat "Other" as an
explicit residual/review bucket rather than a predicted class.** Do not merge
Utilities into Other (Option A throws away a real budget line); do not block on
Option C (rare categories may never fill up, and it wouldn't fix the deeper
leakage problem). Option B is the honest one: it stops the model from claiming a
score on classes it cannot learn, keeps the categories visible via deterministic
rules, and matches what Phase 1 showed actually works here (rules, not the model).

### Proposed two-stage design *(proposal only — not built)*

Phase 1 reframes the whole system: **the rules are the engine, the model is a
weak suggester for unseen merchants.** A design that tells the truth:

1. **Stage 1 — high-precision rules (deterministic).** Exact then longest
   substring merchant match. Already covers ~91% of rows at ~100% precision on
   known merchants. Known merchant → its category, done. No model involved.
2. **Stage 2 — model on the residual only.** For merchants with no rule, run the
   model to produce a *suggestion*, not a trusted label.
3. **Confidence gate → review queue.** Any Stage-2 prediction below a calibrated
   threshold (Phase 4 will set it honestly, not the current guessed 0.70) is
   **flagged for manual review** rather than auto-applied. Given the model's
   ~36% on unseen merchants, most residual predictions should route to review.
4. **The system improves by accumulating RULES, not by the model getting
   smarter.** A reviewed merchant becomes a new rule; next time it's Stage 1.
   This is the honest growth loop and it's already how bootstrap/label-queue
   works — the design just makes it explicit and stops overstating the model.

Tiny classes (Option B) live entirely in Stage 1. "Other" is the natural label
for low-confidence Stage-2 residuals awaiting review.

**Decision needed before Phase 3:** (1) which tiny-class option, (2) whether to
adopt this two-stage framing in the docs/pipeline. Nothing changes until you pick.

### Decisions (confirmed by user, 2026-07-02)

- **Tiny classes → Option B (rule-only).** Utilities & Services (and other rare,
  cleanly-ruleable categories) are assigned only by high-precision merchant
  rules, never predicted by the model; "Other" is the explicit residual/review
  bucket. Not merged into Misc; not blocked on collecting more labels.
- **Two-stage framing → adopted.** Docs/pipeline narrative becomes: rules are the
  engine (~91% coverage), the model is a suggester on the no-rule residual,
  low-confidence routes to human review, and the system improves by accumulating
  rules. Implemented in docs/README in Phase 5; the confidence gate is validated
  honestly in Phase 4 before any threshold is asserted.

## Phase 3 — Tests & reproducibility

**Status: complete — 18 tests pass. Awaiting user confirmation before Phase 4.**

### pytest suite (`tests/`, all synthetic data — no personal transactions)

Run: `pytest tests/ -q` → **18 passed**.

- **`test_parse.py`** (7 tests) — schema normalization (exact 5-column unified
  output), **encoding handling** (a UTF-8-sig and a GBK copy of the same Alipay
  export parse to identical frames), **refund netting** (退款 kept as −20.0),
  **internal-transfer exclusion** (信用卡还款 dropped), income-row exclusion,
  generic-bank direction/amount filtering, and **duplicate handling** (validator
  reports the injected duplicate).
- **`test_leakage_guard.py`** (3 tests) — the required guard. A reusable
  `assert_no_group_leakage(groups, train_idx, test_idx)` (in `src/cv_utils.py`)
  raises `GroupLeakageError` if any merchant lands in both train and test.
  Tests prove: GroupKFold passes it on every fold; a naive StratifiedKFold split
  **trips it** (so the guard actually catches the Phase-1 leakage); and it raises
  on an explicit hand-built overlap.
- **`test_reproducibility.py`** (3 tests) — running the CV twice with a fixed
  seed yields **identical** accuracy and F1-macro (stratified and GroupKFold),
  and a check that `LR_HYPERPARAMS` pins `random_state`.
- **`test_validate.py`** (5 tests) — schema/amount/date checks behave (clean
  frame → no violations; missing column → error; zero amount → error; negative
  amount → *warning* not error, because refunds are legitimately negative;
  future/ancient dates → errors).

### Data validation (`src/validate.py`)

Returns a list of typed `Violation`s (error vs warning) rather than raising, so
callers choose whether to fail. Checks: required-column **schema**; **amounts**
non-zero/non-null (negatives allowed = refunds, flagged as warning); **dates**
parseable and within `2000-01-01 .. now`; **duplicate** rows on the natural key
(no transaction-ID column exists in this schema, so identical (time, merchant,
desc, amount) rows are the closest check — a warning, since repeats can be real).
On the real 863-row data: **0 errors, 1 warning** (30 refund rows) — clean.

### One reproducible command (`run_all.py`)

`python run_all.py` runs raw → parse → label → train → classify, then validates,
then emits the stratified-CV metrics report; `--honest` adds the
GroupKFold-by-merchant evaluation. Verified end-to-end on the restored data.
**Determinism confirmed:** two back-to-back `retrain.py` runs gave byte-identical
`Accuracy: 95.4% (±2.2%)`. The one missing seed found in the codebase
(`label.py`'s display `.sample()`) was pinned to `random_state=42`; every
other randomness source was already seeded.

## Phase 4 — Calibration & honest tuning *(pending user confirmation)*

## Phase 5 — Doc reconciliation *(pending)*
