# ML PROJECT AUDIT REPORT: Transaction Categorizer

**Date:** 2025-06-30  
**Status:** Critical Issues Identified & Fixed  
**Grade:** D+ → B (after fixes)

---

## EXECUTIVE SUMMARY

Your model claims **99.1% accuracy** but this is **MEANINGLESS**. Real accuracy with proper cross-validation is **95.2%**, but the actual problem is much worse: 3 of 8 categories have **0% recall** (completely broken). The model defaults to "Eating Out" (40.7% of data) for anything ambiguous.

**After applying class weights:** Minority categories improve dramatically, with no tradeoff — both accuracy and F1-weighted improve simultaneously. Two categories (Travel, Other) remain broken because they only have 2-5 training samples; no amount of model tuning fixes that. Data collection is now the bottleneck for those two specifically.

---

## THE TRUTH: STRATIFIED CV EVALUATION

### Overall Metrics (2-fold stratified CV, before any fix)
| Metric | Value | Interpretation |
|--------|-------|-----------------|
| **Accuracy** | 95.2% ± 0.7% | Misleading—accuracy doesn't reflect minority class performance |
| **F1-weighted** | 0.943 | Better metric; still dominated by majority classes |
| **F1-macro** | 0.549 | CRITICAL: Only 54.9%—minority classes are broken |
| **Baseline (majority class)** | 40.7% | You beat this, but barely on minorities |

### Per-Category Performance (BEFORE any fix)
| Category | Samples | Recall | Precision | F1 | Status |
|----------|---------|--------|-----------|----|----|
| Transportation | 166 (21.7%) | 98.2% | 100% | 0.991 | ✅ Excellent |
| Groceries | 204 (26.7%) | 98.0% | 99.0% | 0.985 | ✅ Excellent |
| Eating Out | 311 (40.7%) | 99.4% | 90.4% | 0.946 | ✅ Excellent |
| Shopping | 50 (6.5%) | 76.0% | 100% | 0.864 | ⚠️ Poor |
| Transfers & Gifts | 20 (2.6%) | 85.0% | 89.5% | 0.872 | ⚠️ OK |
| Other | 5 (0.7%) | 0.0% | 0% | 0.000 | ❌ Broken |
| Travel | 2 (0.3%) | 0.0% | 0% | 0.000 | ❌ Broken |
| Utilities & Services | 5 (0.7%) | 0.0% | 0% | 0.000 | ❌ Broken |
| Health & Wellness | 1 (0.1%) | 0.0% | 0% | 0.000 | ❌ Broken (1 sample — can't even be cross-validated) |

### Most Common Misclassifications
Everything gets predicted as "Eating Out" when uncertain:
- Shopping → Eating Out: **11 times**
- Other → Eating Out: **5 times**
- Utilities & Services → Eating Out: **5 times**
- Groceries → Eating Out: **3 times**
- Transfers & Gifts → Eating Out: **3 times**
- Transportation → Eating Out: **3 times**

---

## TOP 3 ROOT CAUSES

### 1. **Massive Class Imbalance**
- Top 3 categories = 89% of data (Eating Out 40.7%, Groceries 26.7%, Transportation 21.7%)
- Bottom 5 categories = only 5% of data (Shopping 6.5%, everything else < 3%)
- **Result:** Model defaults to majority class for uncertain predictions

### 2. **Insufficient Training Data for Minorities**
- Need **minimum 10-30 samples per category**, 50-100 for reliable performance
- Current state:
  - Shopping: 50 samples (borderline)
  - Transfers & Gifts: 20 samples (workable but thin)
  - Travel, Other, Utilities, Health: 1-5 samples each (useless — can't train on this)
- **Result:** Categories with <10 samples have 0% recall regardless of model choice

### 3. **No Class Weight Balancing**
- Original model: `class_weight=None` (treats all classes equally in the loss function)
- Penalizes minority class errors less than majority class errors during optimization
- **Result:** Optimizer ignores minority classes; nothing in training pushes it to learn them

---

## IMPROVEMENTS APPLIED

### Fix 1: Class Weight Balancing
**Applied:** `class_weight='balanced'` + `C=10` to Logistic Regression (now the default in `src/train.py`)

**Results (per-category F1, before → after):**
| Category | Before | After | Δ |
|----------|--------|-------|---|
| Transfers & Gifts | F1=0.811 | F1=0.909 | +**12%** |
| Shopping | F1=0.864 | F1=0.938 | +**9%** |
| Travel | F1=0.000 | F1=0.100 | +10pts (still broken) |
| Utilities & Services | F1=0.000 | F1=1.000 | +100pts |
| Groceries | F1=0.988 | F1=0.978 | -1.0% |
| Eating Out | F1=0.944 | F1=0.964 | +2.0% |
| Transportation | F1=0.991 | F1=0.988 | -0.3% |
| Other | F1=0.000 | F1=0.000 | unchanged (only 5 samples) |

**No tradeoff:** Accuracy improves 95.0% → 95.5% AND F1-weighted improves 0.942 → 0.961. This fix is a pure win — there was no reason not to have done it from the start.

### Fix 2: Hyperparameter Tuning (with corrected scoring metric)
**Applied:** Grid search over C, solver, max_iter, class_weight

**Important catch:** The first version of the tuning script scored candidates by `f1_weighted`, which is dominated by majority categories — it picked `class_weight=None` as "best" because the weighted average barely notices 3 categories sitting at 0% recall. Re-scored by `f1_macro` (treats every category equally), the grid search correctly identifies the fix above as best.

**Best Parameters Found (by F1-macro=0.729):**
- `C=10` (regularization strength—higher = fit harder)
- `solver='lbfgs'`
- `class_weight='balanced'` ← Critical
- `max_iter=1000`

**Lesson for future tuning:** Always score hyperparameter search by the metric you actually care about. If you care about fairness across categories, score by `f1_macro`, not `f1_weighted` or `accuracy`.

### Tested & Rejected: Feature Engineering
**Tested:** Added amount bins, hour-of-day bins, day-of-week, merchant-name-length as extra features alongside TF-IDF.

**Result:** F1-weighted dropped 0.961 → 0.946 (-1.6%). Shopping F1 dropped -12%, Travel F1 dropped back to 0%.

**Why:** With only 764 labeled samples, adding 19 extra dimensions causes overfitting — the model has more parameters to fit but no more signal. TF-IDF text already captures the available signal well; don't add features without more data to support them.

### Tested & Rejected: Ensemble (LR + Naive Bayes voting)
**Tested:** Soft-voting ensemble averaging Logistic Regression and Naive Bayes probabilities.

**Result:** Mixed — overall F1-weighted ticked up slightly (0.961→0.965) but Transfers & Gifts F1 dropped notably (0.909→0.855), and only 1 of 4 minority categories improved. Not worth the doubled inference cost and complexity for an inconsistent gain.

---

## REMAINING PROBLEMS

### Problem 1: Insufficient Data for Tiny Categories
**Categories with 0% Recall (even after the fix):**
- Other (5 samples)
- Health & Wellness (1 sample — too few to even appear in a test fold)

**Categories barely working:**
- Travel (2 samples, 10% F1 — basically still broken)

**Fix:** Collect 20-30 more labeled samples for each. This is a data problem, not a model problem — no amount of tuning fixes a category with 2 training examples.

### Problem 2: Minority Classes Still Thin
**Categories with room to improve:**
- Shopping: 90% recall after fix (was 76%)
- Transfers & Gifts: variable across folds (small sample = high variance)

**Causes:**
- Sample size (50 and 20 respectively — still thin for 8-way classification)
- Genuinely ambiguous transactions (e.g., a mall food court could be Shopping or Eating Out)

**Fix:** Collect 30-50 more samples each. Do NOT add more features (tested, made things worse) — more labeled examples is the correct lever here.

### Problem 3: Why "Shopping" → "Eating Out" Specifically
- Both categories can share similar merchant vocabulary (malls have food courts, e.g. "美食城")
- TF-IDF from merchant + description text alone can't disambiguate these without more examples to learn the distinction from
- We tried adding amount/time features to help with exactly this — it made things worse (see Feature Engineering above), because the dataset is too small to support the extra parameters

---

## WHAT TO DO NEXT (PRIORITIZED)

### 🔴 URGENT (Already Done)
1. ~~Add `class_weight='balanced'`, `C=10` to production model~~ ✅ Done — this PR
2. ~~Fix tuning script to score by `f1_macro` not `f1_weighted`~~ ✅ Done — this PR

### 🟡 HIGH PRIORITY (Do This Month)
1. **Collect 20-30 samples for Travel** (currently 2 — completely broken)
2. **Collect 20-30 samples for Other** (currently 5 — completely broken)
3. **Collect 30-50 more samples for Shopping and Transfers & Gifts** (currently 50/20 — workable but thin)
4. **Decide on Health & Wellness:** 1 sample is unusable. Either commit to collecting 20+ samples or merge it into "Other" until you do.

### 🟢 MEDIUM PRIORITY (Next Quarter)
1. **Implement confidence threshold** (only auto-classify if confidence > 0.7-0.8; else route to manual review)
2. Re-run `src/tune.py` and `src/eval.py` after each batch of new labels to track F1-macro improvement
3. ~~Try ensemble model~~ — tested, not worth it (see above)
4. ~~Add feature engineering~~ — tested, made things worse with current data size (see above)

### 🔵 LOW PRIORITY (Future)
1. Revisit feature engineering once you have 2,000+ labeled samples (more data may justify more features)
2. Automated retraining pipeline
3. Active-learning style review queue (human corrects low-confidence predictions, feeds back into training)

---

## DEPLOYMENT DECISION

**SAFE TO DEPLOY?** ✅ **YES, with the class-weight fix (already applied to `src/train.py`)**

**✅ Do:**
- Use the updated `src/train.py` (now defaults to `class_weight='balanced'`, `C=10`)
- Use confidence thresholds (mark predictions < 0.7 confidence for manual review)
- Monitor minority category accuracy (Shopping, Transfers & Gifts)

**❌ Don't:**
- Trust the 99.1% accuracy claim from the old single-split evaluation — it's wrong
- Auto-classify Travel, Other, or Health & Wellness without a manual review step (not enough data)
- Add feature engineering or ensembling at this data size — both tested negative

**Current Status:**
- **Majority categories (Eating Out, Groceries, Transportation):** 96%+ F1 ✅ Safe to automate
- **Medium categories (Shopping, Transfers & Gifts):** 91-94% F1 ⚠️ Safe but monitor, more data helps
- **Tiny categories (Travel, Other, Health & Wellness):** 0-10% F1 ❌ Route to manual review until more data exists

---

## KEY METRICS TO MONITOR

After deploying the fix, track these monthly:

| Metric | Target | Current (after class-weight fix) |
|--------|--------|---------|
| F1-weighted (overall) | ≥0.95 | 0.961 ✅ |
| F1-macro (fairness) | ≥0.70 | 0.729 ✅ (was 0.549 before fix) |
| Shopping F1 | ≥0.90 | 0.938 ✅ |
| Transfers & Gifts F1 | ≥0.90 | 0.909 ✅ |
| Travel F1 | ≥0.50 | 0.100 ❌ (needs more data) |
| Confidence calibration (Brier score) | ≤0.08 | 0.059 ✅ |

---

## CONFIDENCE CALIBRATION

**Is predicted confidence actually predictive of correctness?** YES ✅

- Mean confidence when **correct:** 0.824
- Mean confidence when **wrong:** 0.417
- **Separation:** 0.407 (good—high confidence is a real signal, not noise)
- **Brier score:** 0.059 (well calibrated)

**What this means:** You can safely use confidence thresholds. If the model reports >0.8 confidence, it's usually right; route anything below 0.7 to manual review.

---

## RECOMMENDATIONS FOR THE USER

### Short-term (This Sprint)
1. ~~Apply class_weight='balanced' + C=10 to production model~~ ✅ Done in this PR
2. **Add a manual review queue** for predictions with confidence < 0.7
3. **Track per-category F1 scores** weekly (`python src/eval.py`)
4. **Start collecting data** for Travel and Other specifically (the two genuinely broken categories)

### Medium-term (Next Month)
1. **Collect 30-50 more samples** for Shopping and Transfers & Gifts to push them from "workable" to "solid"
2. **Re-train monthly** as new data arrives: `python src/tune.py` then `python src/eval.py`
3. **Decide on Health & Wellness:** merge into Other, or commit to labeling 20+ samples

### Long-term (Next Quarter)
1. **Target F1-macro ≥0.85** once Travel/Other have real sample sizes
2. **Implement automated confidence-based review queue** (humans review low-confidence predictions, corrections feed back into training)
3. Revisit feature engineering only once labeled data is in the thousands, not hundreds

---

## CONCLUSION

**Your original claim of 99.1% accuracy is a red herring.** The real story:
- Majority categories (Eating Out, Groceries, Transportation): **96%+ F1** ✅
- Minority categories (Shopping, Transfers & Gifts): **91-94% F1** ✅ (after the fix)
- Tiny categories (Travel, Other, Health & Wellness): **0-10% F1** ❌ (need data, not tuning)

**The class-weight fix is a pure win** — accuracy and F1-weighted both improve, no tradeoff. It's now the default in `src/train.py`. Feature engineering and ensembling were tested and explicitly rejected because they made things worse at this dataset size — don't add them back without re-testing on a larger dataset.

**Your model is usable today for 6 of 8 categories.** The other 2 (Travel, Other) need labeled data before they can work — no model change will fix a 2-sample category.

---

## FILES & ARTIFACTS

Generated during audit:
- `_eval_report.txt` — Full evaluation metrics
- `_confusion_matrix.png` — Heatmap of prediction errors
- `_calibration_curve.png` — Confidence calibration analysis
- `_tuning_report.txt` — Hyperparameter tuning results
- `_model_comparison_report.txt` — Before/after comparison
- `classifier_tuned.pkl` / `tfidf_vectorizer_tuned.pkl` — Tuned model artifacts from `src/tune.py`
- `src/train.py` — Production training script, now defaults to the validated hyperparameters

---

**Audit completed by:** ML Senior Review  
**Confidence in findings:** High — re-verified with the project's actual `jieba` tokenizer (not a fallback) before finalizing  
**Recommended action:** Ship the class-weight fix now; collect data for Travel/Other next.
