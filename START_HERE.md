# START HERE: What Changed, What To Do

**TL;DR:** Your model was lying (99.1% = fake). Real accuracy 95.2%, but 3 of 8 categories had 0% recall. Fixed with class weights — now in `src/train.py` by default. No tradeoff: accuracy AND fairness both improved. Two categories (Travel, Other) still need actual data, not more tuning.

---

## THE BRUTAL TRUTH

| Your Claim | Reality | Evidence |
|-----------|---------|----------|
| "99.1% accurate" | Misleading | Only 95.2% with proper cross-validation |
| "All categories working" | False | 3 categories had 0% recall (Travel, Other, Health & Wellness) |
| "Model is production-ready" | Mostly true, with caveats | 6 of 8 categories are genuinely solid now |
| "Model is well-tuned" | Was wrong, now fixed | Was using default hyperparameters; now uses validated ones |

**What happened:** Single 80/20 train-test split (unreliable), no class weights (ignores minorities), no error analysis (silent failures). Also caught and fixed a bug in the tuning script itself — it was scoring by a metric (`f1_weighted`) that's blind to minority-class failures.

---

## WHAT I FIXED (Already Applied to `src/train.py`)

### 1. Class Weights ✅ APPLIED, NO TRADEOFF
Added `class_weight='balanced'`, `C=10` to Logistic Regression — this is now the default.

**Result:** Shopping F1 +9%, Transfers & Gifts F1 +12%, Utilities F1 0%→100%. Accuracy AND F1-weighted both improved simultaneously (95.0%→95.5%, 0.942→0.961). There was no downside to this fix.

### 2. Tuning Script Bug ✅ FIXED
`src/tune.py` was scoring hyperparameter search by `f1_weighted`, which is dominated by majority categories. It was about to recommend `class_weight=None` — the broken config — as "best." Fixed to score by `f1_macro` instead, which correctly identifies the class-weighted config as best (F1-macro=0.729).

### 3. Feature Engineering ❌ TESTED, SKIP IT
Tested amount, time-of-day, merchant-length features → F1 dropped 1.6%.

**Lesson:** With only 764 samples, extra features cause overfitting. Text-only TF-IDF is already near-optimal here.

### 4. Ensemble Models ❌ TESTED, SKIP IT
Tested LR + Naive Bayes voting → inconsistent results, hurts Transfers & Gifts specifically, doubles inference cost for no reliable gain.

---

## DEPLOY THIS (Already Done — Just Re-train)

The fix is already in `src/train.py`. You just need to re-run training to regenerate the model artifacts:

```bash
cd /path/to/financing
python src/train.py
```

That's it — `classify.py` already loads whatever `train.py` produces, no changes needed there.

### Optional but Recommended: Confidence Thresholds
```python
# In src/classify.py, after predictions:
predictions = clf.predict(X)
confidences = clf.predict_proba(X).max(axis=1)

df['category'] = predictions
df['confidence'] = confidences
df.loc[confidences < 0.7, 'needs_review'] = True  # Flag for human review
```

---

## THE DATA COLLECTION TASK (NEXT ~2 HOURS)

Two categories are still broken — not because the model is bad, but because they have almost no training data:

| Category | Current Samples | Status |
|----------|-----------------|--------|
| Travel | 2 | 0% → 10% F1 even after the fix. Needs ~25-30 more samples. |
| Other | 5 | Still 0% F1. Needs ~20-25 more samples. |
| Health & Wellness | 1 | Too few to even test. Merge into "Other" or label 20+. |

**No model change fixes a 2-sample category.** This is the only remaining lever.

### How to Label

**Option A: Spreadsheet**
1. Export unlabeled transactions from `data/processed/transactions.csv`
2. Label by category, focusing on Travel and Other
3. Save back to `data/labeled/labeled_transactions.csv`

**Option B: Interactive**
```bash
python src/label.py
```

**After labeling:**
```bash
python src/train.py    # Re-train with new data
python src/eval.py     # Check F1-macro improvement
```

---

## CURRENT PERFORMANCE (After the Class-Weight Fix)

| Category | Samples | F1 | Status | Next Step |
|----------|---------|-----|--------|-----------|
| Transportation | 166 | 0.988 | ✅ Done | Maintain |
| Eating Out | 311 | 0.964 | ✅ Done | Maintain |
| Groceries | 204 | 0.978 | ✅ Done | Maintain |
| Shopping | 50 | 0.938 | ✅ Good | More data helps but not urgent |
| Utilities & Services | 5 | 1.000 | ⚠️ Small sample | Monitor for drift |
| Transfers & Gifts | 20 | 0.909 | ✅ Good | A bit more data would reduce variance |
| Travel | 2 | 0.100 | ❌ Broken | Label 25-30 samples |
| Other | 5 | 0.000 | ❌ Broken | Label 20-25 samples |

---

## KEY FILES IN THIS PR

| File | Purpose |
|------|---------|
| `AUDIT_REPORT.md` | Full audit findings (read if skeptical) |
| `OPTIMIZATION_SUMMARY.md` | All tests & results (technical deep-dive) |
| `DATA_COLLECTION_GUIDE.md` | How to label more data |
| `src/train.py` | **Updated** — now defaults to the validated hyperparameters |
| `src/eval.py` | Stratified CV evaluation — use this, not a single train/test split |
| `src/tune.py` | Hyperparameter search — fixed to score by f1_macro |
| `src/compare_models.py` | Before/after comparison tooling |
| `src/ensemble_test.py` | Ensemble experiment (kept for reference; result was negative) |
| `src/feature_engineering.py` | Feature engineering experiment (kept for reference; result was negative) |

---

## QUICK REFERENCE: HYPERPARAMETERS

**Before (in production, was wrong):**
```python
LogisticRegression(
    max_iter=1000,
    solver='lbfgs',
    # class_weight not set → defaults to None, ignores minorities
)
```

**After (now in `src/train.py`):**
```python
LogisticRegression(
    max_iter=1000,
    solver='lbfgs',
    class_weight='balanced',  # ✅ Penalizes minority errors
    C=10                       # ✅ Reduced regularization, fits harder
)
```

---

## CHECKLIST: BEFORE YOU CALL IT "DONE"

- [x] Class weights applied to `src/train.py`
- [x] Tuning script scoring bug fixed
- [x] Feature engineering and ensembling tested (both rejected, documented why)
- [ ] Re-run `python src/train.py` to regenerate model artifacts with the fix
- [ ] **[Recommended] Add confidence thresholds** to `classify.py`
- [ ] **[Highest ROI] Label 45-55 transactions** for Travel and Other specifically
- [ ] Re-train monthly as new data arrives

---

## ANSWERING YOUR ORIGINAL QUESTIONS

### "Exactly what is my painpoint?"
- **Class imbalance ignored** (40% Eating Out vs 0.3% Travel) — now fixed
- **No stratified cross-validation** (single split was unreliable) — now have `eval.py`
- **No hyperparameter tuning** — now have `tune.py`, with a scoring bug caught and fixed
- **Insufficient data for 3 categories** (1-5 samples each) — this is the one thing left

### "How can I improve accuracy?"
1. Class weights — done, zero tradeoff
2. Hyperparameter tuning — done, bug caught and fixed
3. Collect data for Travel/Other — your turn, ~2 hours

### "What strategies should I use?"
- Class weighting for imbalance (done)
- Stratified CV for reliable measurement (done)
- Score tuning by the metric you care about, not just accuracy (done — caught a real bug here)
- Confidence thresholds for safety (recommended, not yet implemented)

### "What can I do to max out accuracy?"
- Label 25-30 Travel samples, 20-25 Other samples (highest ROI left)
- Don't add feature engineering or ensembling at this dataset size — both tested negative
- Re-test those once you have 2,000+ labeled samples

---

## HONEST GRADE

**Before audit:** F (99.1% claim was fake, 3 categories silently broken)  
**After fix:** B (production model fixed, honest about its limits, 6/8 categories solid)  
**After data collection (projected):** A- (Travel/Other fixed, all 8 categories working)

---

## NEXT ACTION

1. **Right now (5 min):** `python src/train.py` to pick up the fix
2. **This week (~1 hr):** Add confidence thresholds to `classify.py`
3. **This week (~2 hrs):** Label 25-30 Travel + 20-25 Other transactions
4. **Next week:** Re-train and measure F1-macro improvement

---

*For questions, refer to AUDIT_REPORT.md (what's wrong), OPTIMIZATION_SUMMARY.md (why it was fixed), or DATA_COLLECTION_GUIDE.md (how to improve further).*
