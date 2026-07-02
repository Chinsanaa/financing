# Personal Finance Categorizer
## End-to-End Machine Learning Pipeline for Transaction Classification

---

## Executive Summary

**Automated transaction categorization system** for Alipay + WeChat Pay exports: a **rules-first** pipeline (high-precision merchant rules) with a Logistic Regression + TF-IDF + jieba model as a suggester for merchants the rules don't cover, plus a Streamlit dashboard for budgeting.

**How it actually performs** (measured honestly — see [How accuracy is measured](#how-accuracy-is-measured)):
- **Merchant rules are the engine.** On a representative run they matched ~91% of transactions at ~100% precision. This is where the accuracy comes from.
- **On merchants a rule already knows**, the model re-identifies the category at ~95% (stratified CV).
- **On genuinely new merchants** (no rule yet), the model generalizes poorly — ~45% under merchant-grouped CV, only a little above the 38.5% majority-class baseline. So model predictions on unseen merchants are treated as **suggestions routed to manual review**, not trusted labels.
- The system improves by **accumulating rules** (you review new merchants → they become rules), not by the model getting smarter on its own.

**Your own metrics** are generated when you run the pipeline:
- CV accuracy, F1-weighted, F1-macro → `data/reports/TRAINING_REPORT.txt`
- Merchants awaiting review → `data/processed/needs_manual_review.csv`
- Budget variance → Streamlit dashboard

> ⚠️ Earlier versions of this README quoted 99.1% / 97.3% / 95.5% accuracy as if the model were that good in general. Those were single stratified-CV runs on a dataset where the **same merchant appeared in both train and test** — the model was memorizing merchants, not learning to categorize new ones. See `docs/FULL_AUDIT.md` for the full integrity audit.

---

## The Problem

### Situation
When using multiple payment platforms (Alipay + WeChat Pay), there is no unified view of spending patterns. Manually categorizing hundreds of transactions across platforms was:
- **Time-consuming** — requires consistent manual labeling after each export
- **Inconsistent** — prone to subjective classification errors
- **Non-scalable** — impossible to maintain across months/years of data
- **Opaque** — no insights into where money actually goes

### Business Impact
Without automated categorization, personal financial decisions lack data-driven foundation:
- Cannot identify spending patterns or anomalies
- Unable to set and track budget goals
- No actionable insights for spending cuts or investment planning

---

## The Solution

### Architecture Overview

A **supervised machine learning pipeline** that learns spending patterns from labeled examples and classifies new transactions automatically:

```
Raw Data (CSV Exports)
    ↓
[Stage 1] Normalize & Parse
  • Alipay CSV + WeChat Excel → unified schema
  • Handle encoding issues (GBK, UTF-8)
    ↓
[Stage 2] Clean & Tokenize
  • jieba (Chinese word segmentation)
  • Mixed language support
  • Remove noise, lowercase English
    ↓
[Stage 3] Rule-Based Pre-Label
  • Starter merchant rules (~60 national chains) + your custom rules
    ↓
[Stage 4] Vectorize
  • TF-IDF feature extraction (unigrams + bigrams)
  • ~660 most-distinctive tokens (varies with your data)
    ↓
[Stage 5] Train Classifier
  • Logistic Regression with class balancing
  • Regularization C=1.0 (chosen under merchant-grouped CV, not leaky stratified CV)
  • Cross-validation for reporting
    ↓
[Stage 6] Classify & Score (two-stage)
  • Stage 1: merchant rules + description rules (e.g. catering/餐饮) → trusted label
  • Stage 2: model predicts the residual (no-rule merchants) → suggestion
  • Model suggestions on unseen merchants are routed to manual review
    ↓
[Stage 7] Visualize & Decide
  • Interactive Streamlit dashboard
  • Budget tracking, anomaly detection
  • Decision-making tools (savings calculator, investment readiness)
```

### Why This Approach?

| Design Choice | Alternative Considered | Why This Won |
|---|---|---|
| **Supervised Classification** | Unsupervised clustering (K-means) | We know target categories in advance; clustering requires manual re-labeling each run and produces inconsistent clusters |
| **Logistic Regression** | Deep learning (LSTM/BERT) | Simple, interpretable, fast; tokens directly show what the model learned. Given that merchant memorization (not text generalization) drives most of the accuracy, a heavier model would not help here |
| **TF-IDF Vectorization** | Word embeddings (Word2Vec) | Interpretable, distinctive merchant names (Meituan, Taobao, DiDi) score high naturally; no need for heavy compute |
| **jieba Tokenization** | English tokenizer on Chinese | Chinese has no spaces; jieba is the standard library for correct segmentation |
| **Class Weighting** | Balanced train/test split | Data is naturally imbalanced (~38% Eating Out, <1% Utilities); weighting prevents minority categories from being ignored |

---

## Results & Performance

Metrics are **per-user** — generated when you run `python src/bootstrap.py` and `python src/retrain.py`.

| Metric | Where to find it |
|---|---|
| CV accuracy, F1-weighted, F1-macro | `data/reports/TRAINING_REPORT.txt` |
| Per-category precision/recall | Same report, after retrain |
| Manual review queue | `data/processed/needs_manual_review.csv` |
| Rule vs ML coverage | Bootstrap / classify stdout |

### How accuracy is measured

There are two very different ways to cross-validate this system, and they give
very different numbers. Both are honest — they answer different questions.

| Scheme | What it measures | Representative result |
|---|---|---|
| **Stratified 5-fold CV** | Accuracy on merchants the model has *already seen* (they appear in both train and test folds) | ~95% accuracy, ~0.85 F1-macro |
| **GroupKFold by merchant** | Accuracy on **new** merchants (no merchant is in both train and test) | ~45% accuracy, ~0.44 F1-macro |

The gap is the point: because the merchant name is part of the text the model
reads, stratified CV mostly measures **merchant memorization**, not the ability
to categorize a merchant it has never seen. GroupKFold is the honest measure of
generalization — and it sits only a little above the 38.5% majority-class
baseline.

**Which do we report?** Both, labeled for what they are. `retrain.py` prints the
stratified number (useful for known merchants); `run_all.py --honest` prints the
GroupKFold number (the real generalization). We do **not** headline the
stratified number as if it were the model's real-world accuracy — that was the
mistake this project's earlier docs made.

Full methodology, per-category metrics, calibration curves, and the
documented-vs-actual reconciliation are in **`docs/FULL_AUDIT.md`**.

---

## Technical Implementation

### Technology Stack
- **Language**: Python 3.8+
- **ML Framework**: scikit-learn (Logistic Regression)
- **NLP**: jieba (Chinese tokenization), TF-IDF vectorization
- **Data Processing**: pandas, NumPy
- **Web UI**: Flask (interactive onboarding wizard)
- **Dashboard**: Streamlit (5-tab analytics dashboard)
- **File Format**: CSV (normalized), PKL (model serialization)

### Key Algorithms

**1. Chinese + English Tokenization**
```python
# jieba preserves English words, segments Chinese into individual words
# "在Meituan点了外卖" → ["在", "Meituan", "点", "了", "外卖"]
# TF-IDF then weights "Meituan" highly (unique to food category)
```

**2. Class-Balanced Logistic Regression**
- The data is heavily imbalanced (~38% Eating Out, <1% Utilities)
- `class_weight='balanced'` auto-scales loss inversely to class frequency so minority categories aren't ignored
- `C=1.0` regularization: an earlier `C=10` was tuned on the leaky stratified CV; under honest merchant-grouped CV, `C=1.0` generalizes better to unseen merchants

**3. Confidence Calibration (honest)**
- On **known** merchants the model is well calibrated (confidence tracks accuracy; ECE ≈ 0.04)
- On **new** merchants it is **overconfident** — even 0.9+ confidence is only ~89% accurate (ECE ≈ 0.18)
- Because confidence is unreliable exactly where the model is used (unseen merchants), model predictions on no-rule merchants are routed to review rather than auto-accepted on a confidence threshold

**4. Cross-Validation — two schemes, honestly labeled**
- Stratified 5-fold measures accuracy on *known* merchants; GroupKFold-by-merchant measures generalization to *new* merchants (see [How accuracy is measured](#how-accuracy-is-measured))
- The large gap between them revealed that earlier single-number accuracy claims were merchant-memorization artifacts, not real generalization

### Model Complexity & Trade-offs

**Why Logistic Regression (not Deep Learning)?**
| Factor | Logistic Regression | Neural Network |
|---|---|---|
| Training time | ~0.1s | ~30s |
| Interpretability | ✅ Can see which tokens matter | ❌ Black box |
| Data needed | 200-500 samples | 10,000+ samples |
| Production stability | ✅ Deterministic (fixed seed) | ⚠️ Requires careful seeding |
| Fit for this problem | ✅ Merchant memorization dominates; a heavier model wouldn't generalize better on unseen merchants either | ❌ Needs far more data; still bottlenecked by the same memorization issue |
| Maintenance burden | Low | High |

**Decision**: Logistic Regression wins on simplicity, speed, and interpretability. The limiting factor here is the data (few unique merchants, heavy repetition), not model capacity — so a bigger model would not meaningfully improve honest generalization.

---

## Dashboard Features

Six-tab Streamlit dashboard (`streamlit run src/dashboard.py`). Filters (date, category, source, confidence) apply on the **Overview** tab; other tabs use full dataset or their own month selectors.

| Tab | What it answers |
|---|---|
| **📊 Overview** | Where did money go? KPIs (total spend, avg txn, daily avg, top category); monthly total spend trend line (avg reference + endpoint label); monthly stacked bar by category; pie breakdown; top 15 merchants; cumulative spend line; seasonal profile + year-over-year trend (once 2+ calendar years of data exist) |
| **💳 Budget & Forecast** | Am I on track? Per-category budget cards (green/orange/red); variance table (¥ and %); 9-month risk; budget vs actual bar; forecast heatmap (Sep→May); seasonal vs EWMA toggle |
| **💰 Savings & Anomalies** | What's unusual or off-track? Monthly income, YTD savings rate, year-end projection vs savings goal; need/want split; daily burn rate; cumulative savings trend; high-value outliers (IQR-based) |
| **🎯 Action Plan** | What should I cut? Efficiency score (% months met ¥600 goal); ranked discretionary transactions; cuttable merchants chart; interactive savings-gap sliders; investment readiness (3/3 recent months) |
| **🏷️ Label Queue** | Which merchants still need a category? Editable table of unlabeled merchants (English display); pick categories and apply to add rules, retrain, and reclassify — no CLI round-trip required |
| **📋 Reports** | Export utility — month picker, category summary table, CSV download |

**Tab evolution:** Original build had 8 tabs (Overview, Merchants, Budget, Anomalies, Reports, Forecasting, Savings, Action Plan). Session 10 collapsed to 3 priority tabs; Session 17 settled on a 5-tab structure; Session 25 added the Label Queue tab (6 tabs) for in-dashboard merchant labeling.

---

## How to Use

### Web UI (recommended)

Interactive Flask wizard: upload files, define categories, label merchants (each becomes a trusted rule), retrain, then view the dashboard.

```bash
pip install -r requirements.txt
python src/app.py
# Open http://127.0.0.1:5000
```

**Workflow:**
1. **Upload** — drag Alipay `.csv` and/or WeChat `.xlsx` files
2. **Categories** — review and customize the 7 default spending categories
3. **Label** — assign a category per merchant (each becomes a trusted rule); repeat to expand coverage
4. **Dashboard** — explore 5 interactive tabs (Overview, Budget & Forecast, Savings & Anomalies, Action Plan, Reports)

**How it works:**
- Starter merchant rules (~295 patterns) auto-label known chains (Meituan, DiDi, etc.) instantly
- UI iterates: you label ambiguous merchants → ML retrains → confidence updates in real-time
- Session data lives in `data/sessions/` (gitignored for privacy)
- On completion, trained model + categorized data sync to `data/` for offline use or Streamlit dashboard

**Install as a mobile app:** the web UI is an installable PWA. Open `http://<your-server>:5000` on your phone's browser, then "Add to Home Screen" (iOS Safari) or "Install app" (Android Chrome). It launches full-screen without browser chrome — handy for quickly reviewing/labeling merchants (Step 3) between other things.

### CLI setup (alternative)

This repo ships **starter templates**, not someone else's transactions or budget. Your financial data stays local (gitignored).

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Export Alipay + WeChat bills → drop in data/raw/
#    See data/raw/README.md for file names and export tips

# 3. One-command first-run setup (parse → seed rules → train → classify → budget)
python src/bootstrap.py --income 8000   # set your monthly income in CNY

# 4. Label your top merchants (each becomes a trusted rule → more coverage)
#    Open data/exports/merchants_to_label.csv, fill suggested_category, re-run bootstrap

# 5. Dashboard
streamlit run src/dashboard.py
```

**What to expect**

| Stage | What happens | Notes |
|-------|--------------|-------|
| Day 1 (starter rules only) | National chains (Meituan, DiDi, 麦当劳) auto-labeled; everything else → review | Coverage depends on how many of your merchants are national chains |
| After filling `merchants_to_label.csv` | Your local shops become rules | Each rule you add is trusted at 100% precision next run |
| Ongoing | New merchants get model *suggestions* → you confirm → they become rules | Accuracy grows by accumulating rules, not by the model self-improving |

The percentage of transactions that land correctly is driven by **how much of
your spending is at merchants you've already ruled** — not by a single model
accuracy number. Budget numbers in the dashboard come from **your** `data/budget_config.json` (auto-generated from spend history on bootstrap, then editable).

### Quick Start (existing setup)

```bash
pip install -r requirements.txt
python src/bootstrap.py       # or: parse.py → classify.py
streamlit run src/dashboard.py
```

### Classify New Transactions

```python
import pandas as pd
import joblib
from src.classify import classify_all
from src.label import load_merchant_rules

# Load trained models and merchant rules
classifier = joblib.load('data/processed/classifier.pkl')
vectorizer = joblib.load('data/processed/tfidf_vectorizer.pkl')
rules = load_merchant_rules('data/labeled/merchant_rules_expanded.csv')

# Classify new transactions (ML + rule overrides)
df_new = pd.read_csv('new_transactions.csv')
df_classified = classify_all(df_new, vectorizer, classifier, rules=rules)

# View results (includes confidence scores)
print(df_classified[['merchant', 'description', 'category', 'confidence']])
```

### Monthly Retraining (Optional but Recommended)

```bash
# 1. Find ambiguous transactions for labeling
python3 src/find_other_candidates.py
# Output: OTHER_CANDIDATES_TO_LABEL.csv (30 examples)

# 2. Review and label the candidates
# (Add labeled rows to data/labeled/labeled_transactions.csv)

# 3. Retrain the model
python3 src/retrain.py
# Output: data/reports/TRAINING_REPORT.txt (detailed metrics)

# 4. Reclassify all transactions
python3 src/classify.py
```

### Add Bank or Credit Card Exports

Drop a CSV into `data/raw/` as `bank.csv` or `credit_card.csv`, or copy
`data/raw/source_config.example.json` → `source_config.json` and set column names
for your bank's export format. Then re-run parse:

```bash
python3 src/parse.py
python3 src/classify.py
```

The parser auto-detects common Chinese/English headers (交易日期, Amount, etc.)
and filters to expenses only when a 收/支 / Type column is present.

---

## Project Structure

```
financing/
├── README.md                 # This file
├── CLAUDE.md                 # Collaboration guidelines
├── context.md                # Session log and project memory
├── requirements.txt
│
├── data/
│   ├── raw/                  # Original exports (Alipay CSV, WeChat Excel) — do not edit
│   ├── templates/            # Starter files copied on first bootstrap
│   │   ├── merchant_rules_starter.csv    # ~60 portable chain rules
│   │   └── budget_config.example.json
│   ├── labeled/              # Your rules + labels (gitignored)
│   │   ├── merchant_rules_expanded.csv
│   │   └── labeled_transactions.csv
│   ├── processed/            # Pipeline outputs (used by dashboard)
│   │   ├── transactions.csv
│   │   ├── transactions_classified.csv
│   │   ├── needs_manual_review.csv
│   │   ├── classifier.pkl
│   │   └── tfidf_vectorizer.pkl
│   ├── intermediate/         # Stage artifacts (cleaned text, auto-labeled)
│   ├── exports/              # Excel review files for manual checks
│   ├── reports/              # TRAINING_REPORT.txt from retrain.py
│   └── budget_config.json
│
├── output/                   # Generated charts & debug samples (gitignored)
│   ├── charts/
│   └── samples/
│
├── src/                      # Active pipeline scripts
│   ├── bootstrap.py          # First-run setup for new users
│   ├── paths.py              # Central data path constants
│   ├── parse.py              # Stage 1: Parse CSV/Excel
│   ├── segment.py            # Stage 2 & 4: Tokenization + TF-IDF
│   ├── label.py              # Stage 3: Rule-based pre-labeling
│   ├── train.py              # Stage 5: Train classifier
│   ├── classify.py           # Stage 6: Predict + confidence
│   ├── retrain.py            # Automated retraining
│   ├── visualize.py          # Stage 7: Static charts
│   ├── dashboard.py          # Streamlit dashboard
│   ├── dashboard_helpers.py
│   ├── merchant_display.py
│   ├── forecast.py
│   ├── trends.py              # Multi-year trend analysis
│   └── find_other_candidates.py
│
└── _archive/                 # Old experiments, one-off scripts, backups
```

---

## Key Features

### 1. **Dual-Source Normalization**
Seamlessly combines Alipay CSV and WeChat Excel exports into a unified schema, handling different column names, encodings, and date formats automatically.

### 2. **Mixed-Language NLP**
Correctly tokenizes Chinese + English text using jieba segmentation. Prevents the common pitfall of applying English tokenizers to Chinese (which would fail to segment).

### 3. **Rule-Based Pre-Labeling + Post-Classification Overrides**
Starter merchant rules (national chains) auto-label during bootstrap; your custom rules override ML at inference. Description rules handle `餐饮` / `catering` → Eating Out.

### 4. **Two-Stage Routing with Honest Review**
Merchant rules set confidence to 100% on match (trusted). Model predictions on merchants no rule covers are treated as **suggestions** and written to `needs_manual_review.csv` — because the model is unreliable on unseen merchants regardless of its confidence. A `label_source` column records whether each row was labeled by `rule`, `override`, or `model`.

### 5. **Fairness-Aware Model Training**
Class weighting scales the training loss inversely to class frequency so minority spending categories (Transfers, Shopping) aren't drowned out by the majority. It does not overcome the underlying data limitation on unseen merchants — it just keeps small classes represented.

### 6. **Interactive Dashboard**
Five tabs: spending overview, budget & forecast, savings & anomalies, action plan, and monthly reports/export — decision-making tools (savings calculator, investment readiness) plus IQR-based anomaly detection.

### 7. **Automated Retraining Pipeline**
Monthly workflow to identify ambiguous transactions, collect labels, retrain model, and evaluate without manual intervention.

---

## Validation & Robustness

### Cross-Validation Strategy
- Two schemes, reported for what they measure: **stratified 5-fold** (known merchants) and **GroupKFold by merchant** (new merchants). See [How accuracy is measured](#how-accuracy-is-measured).
- **Why this matters:** stratified CV alone let earlier versions of this project report ~95–99% accuracy that was really merchant memorization. GroupKFold exposed ~45% generalization to new merchants.
- A **leakage-guard test** (`tests/test_leakage_guard.py`) fails if a split ever puts the same merchant in both train and test when grouping is expected.

### Confidence Calibration
- Well calibrated on **known** merchants (ECE ≈ 0.04); **overconfident** on **new** merchants (ECE ≈ 0.18, even 0.9+ confidence only ~89% accurate).
- Consequence: predictions on unseen merchants go to review rather than being auto-accepted on a confidence threshold.

### Testing & Reproducibility
- `pytest tests/` covers parsing (encoding, refund netting, transfer filtering, schema, duplicates), the leakage guard, two-stage routing, data validation, and fixed-seed reproducibility.
- `python run_all.py` reproduces raw → parse → label → train → classify → metrics deterministically (all `random_state`s pinned). `--honest` adds the GroupKFold evaluation.
- `src/validate.py` checks schema, amounts, date ranges, and duplicate rows.

### Edge Cases Handled
- ✅ Empty merchant names → fallback to description
- ✅ All-numeric merchant IDs → handled gracefully
- ✅ Duplicate transactions → preserved (intentional for monthly totals)
- ✅ Unseen merchants → model *suggestion* routed to review (not silently trusted)
- ✅ Refunds → netted as a negative amount against the original category/merchant instead of vanishing
- ✅ Internal transfers (credit card repayment, withdrawal) → excluded at parse; not counted as spend

---

## Limitations & Future Work

### Current Limitations
1. **Requires initial labeling** — starter rules cover national chains; local merchants need `merchants_to_label.csv` or manual labels
2. **7 spending categories** — Travel/Health/Entertainment map to Other unless you expand the category list
3. **Batch processing only** — monthly export workflow, not real-time
4. **WeChat export format** — parser assumes current Excel layout (`skiprows=17`); may need update if WeChat changes exports

### Future Enhancements
- [x] Multi-year trend analysis — `src/trends.py` built (Session 16); re-added to the Overview tab (Session 25) as a seasonal profile + year-over-year comparison, gated on 2+ calendar years of data
- [x] Support additional payment sources — generic bank/card CSV parser in `parse.py`; see `data/raw/source_config.example.json`
- [ ] Automated feature engineering with larger datasets (2000+ samples)
- [x] Mobile app for quick transaction review — installable PWA (manifest + service worker); "Add to Home Screen" on the Label step for on-the-go merchant review
- [x] Budget forecasting — EWMA option alongside seasonal+trend in `forecast.py` (Budget & Forecast tab)

---

## Getting Started

### Prerequisites
- Python 3.8 or higher
- pip or conda
- ~50 MB disk space for data + models

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd financing

# Install dependencies
pip install -r requirements.txt

# Run pipeline
python3 src/parse.py
python3 src/classify.py
streamlit run src/dashboard.py
```

### Example: View Dashboard
```bash
streamlit run src/dashboard.py
# Visit http://localhost:8501 in your browser
```

---

## For Recruiters

### What This Project Demonstrates

**Machine Learning Skills:**
- ✅ Supervised classification pipeline (train → evaluate → predict)
- ✅ Data preprocessing and normalization across multiple sources
- ✅ Class imbalance handling (class weighting, stratified CV)
- ✅ NLP: tokenization, TF-IDF vectorization, mixed-language support
- ✅ Model evaluation: precision, recall, F1, cross-validation
- ✅ Hyperparameter tuning and honest metrics reporting
- ✅ Production-ready confidence thresholds and failure modes

**Engineering Skills:**
- ✅ Full-stack data pipeline (parsing → cleaning → feature engineering → modeling → visualization)
- ✅ Automated workflows (retraining, candidate discovery)
- ✅ Code organization and modularity (7-stage pipeline)
- ✅ Interactive dashboards (Streamlit, 5-tab layout)
- ✅ Version control and documentation

**Soft Skills:**
- ✅ Integrity: ran a full evaluation audit that found the reported accuracy was a merchant-memorization artifact, and rewrote the docs to say so (`docs/FULL_AUDIT.md`)
- ✅ Honesty over vanity: report both stratified (~95%, known merchants) and GroupKFold (~45%, new merchants) rather than headlining the flattering number
- ✅ Testing: leakage-guard test, reproducibility test, one deterministic run command
- ✅ Documentation: audit report, context tracking, decision rationale

### Technical Decisions Worth Discussing
1. **Why report two accuracy numbers?** → Stratified CV measures known-merchant recall; GroupKFold measures generalization to new merchants. The gap revealed leakage (see How accuracy is measured).
2. **How does jieba help?** → Chinese segmentation enables TF-IDF to work correctly (see Technical Implementation)
3. **Why a rules-first, two-stage design?** → On this data the model can't generalize to unseen merchants, so high-precision rules do the trusted labeling and the model only suggests for the residual
4. **Why C=1.0 and not C=10?** → C=10 was tuned on the leaky CV; under honest GroupKFold, C=1.0 generalizes better
5. **How do you handle predictions on new merchants?** → Route to manual review, because model confidence is unreliable there regardless of its value

---

## Dependencies

```
pandas>=1.5.0
scikit-learn>=1.0.0
jieba>=0.42.1
openpyxl>=3.0.0
matplotlib>=3.5.0
streamlit>=1.0.0
joblib>=1.1.0
numpy>=1.21.0
```

---

## License

Open source (MIT License)

---

## Contact & Questions

For questions about the implementation or technical decisions, see `context.md` for detailed session logs and decision rationale.

**Last Updated:** 2026-07-02 — ML integrity audit (`docs/FULL_AUDIT.md`): reconciled all accuracy claims to honest stratified + GroupKFold numbers, adopted the rules-first two-stage design, added tests and a deterministic run command.
