# Personal Finance Categorizer
## End-to-End Machine Learning Pipeline for Transaction Classification

---

## Executive Summary

**Automated transaction categorization system** for Alipay + WeChat Pay exports: supervised ML (Logistic Regression + TF-IDF + jieba), merchant rules, confidence thresholds, and a five-tab Streamlit dashboard for budgeting.

**Typical performance** (after labeling ~200+ transactions on your own data):
- ~90–96% stratified CV accuracy on held-out labels
- Merchant rules give instant 100% confidence on known chains (Meituan, DiDi, etc.)
- Low-confidence rows flagged for manual review

**Day-one expectation** (starter rules only): ~75–85% category accuracy until you fill `merchants_to_label.csv` and retrain.

**Key Metrics (your run — run `bootstrap.py` to generate):**
- CV accuracy, F1-weighted, F1-macro from `data/reports/TRAINING_REPORT.txt`
- Manual review queue in `data/processed/needs_manual_review.csv`
- Budget variance in Streamlit dashboard

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
  • TF-IDF feature extraction
  • 657 most-distinctive tokens
    ↓
[Stage 5] Train Classifier
  • Logistic Regression with class balancing
  • Hyperparameter optimization (C=10, balanced weights)
  • Stratified 5-fold cross-validation
    ↓
[Stage 6] Classify & Score
  • ML prediction + merchant rule overrides + description rules (e.g. catering/餐饮)
  • Flag low-confidence (<70%) for manual review
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
| **Logistic Regression** | Deep learning (LSTM/BERT) | Simple, interpretable, fast; outperforms complex models for this problem size (~1000 samples); tokens directly show what model learned |
| **TF-IDF Vectorization** | Word embeddings (Word2Vec) | Interpretable, distinctive merchant names (Meituan, Taobao, DiDi) score high naturally; no need for heavy compute |
| **jieba Tokenization** | English tokenizer on Chinese | Chinese has no spaces; jieba is the standard library for correct segmentation |
| **Class Weighting** | Balanced train/test split | Data is naturally imbalanced (47% Eating Out); weighting prevents minority categories from being ignored |

---

## Results & Performance

Metrics are **per-user** — generated when you run `python src/bootstrap.py` and `python src/retrain.py`.

| Metric | Where to find it |
|---|---|
| CV accuracy, F1-weighted, F1-macro | `data/reports/TRAINING_REPORT.txt` |
| Per-category precision/recall | Same report, after retrain |
| Manual review queue | `data/processed/needs_manual_review.csv` |
| Rule vs ML coverage | Bootstrap / classify stdout |

**Reference design targets** (on ~1k labeled mixed CN/EN transactions):
- Stratified 5-fold CV accuracy: often **90–96%** after sufficient labeling
- F1-macro improves materially with `class_weight='balanced'` vs unweighted baseline
- Well-calibrated confidence: wrong predictions tend to score lower than correct ones

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
- Minority categories (Transfers: 27 samples) were invisible to unweighted model
- `class_weight='balanced'` auto-scales loss inversely to class frequency
- Result: all categories get fair representation, F1-macro +39%

**3. Confidence Calibration**
- Well-calibrated: correct predictions average 82.4% confidence, wrong predictions 41.7%
- Threshold strategy: auto-classify ≥80%, manual review 70-79%, reject <70%
- Prevents unreliable predictions from silently failing

**4. Stratified Cross-Validation**
- 5-fold stratified split preserves category distribution in each fold
- Honest metric: prevents accidental overfitting to majority class
- Discovered real accuracy (95.5%) vs. misleading single-split (99.1%)

### Model Complexity & Trade-offs

**Why Logistic Regression (not Deep Learning)?**
| Factor | Logistic Regression | Neural Network |
|---|---|---|
| Training time | ~0.1s | ~30s |
| Interpretability | ✅ Can see which tokens matter | ❌ Black box |
| Data needed | 200-500 samples | 10,000+ samples |
| Production stability | ✅ No randomness | ⚠️ Requires careful seeding |
| Accuracy on this task | 96.2% | ~96.5% (marginal gain) |
| Maintenance burden | Low | High |

**Decision**: Logistic Regression wins on simplicity, speed, and interpretability with acceptable accuracy trade-off.

---

## Dashboard Features

Five-tab Streamlit dashboard (`streamlit run src/dashboard.py`). Filters (date, category, source, confidence) apply on the **Overview** tab; other tabs use full dataset or their own month selectors.

| Tab | What it answers |
|---|---|
| **📊 Overview** | Where did money go? KPIs (total spend, avg txn, daily avg, top category); monthly stacked bar by category; pie breakdown; top 15 merchants; cumulative spend line |
| **💳 Budget & Forecast** | Am I on track? Per-category budget cards (green/orange/red); variance table (¥ and %); 9-month risk; budget vs actual bar; forecast heatmap (Sep→May); seasonal vs EWMA toggle |
| **💰 Savings & Anomalies** | What's unusual or off-track? Monthly income, YTD savings rate, year-end projection vs savings goal; need/want split; daily burn rate; cumulative savings trend; high-value outliers (IQR-based) |
| **🎯 Action Plan** | What should I cut? Efficiency score (% months met ¥600 goal); ranked discretionary transactions; cuttable merchants chart; interactive savings-gap sliders; investment readiness (3/3 recent months) |
| **📋 Reports** | Export utility — month picker, category summary table, CSV download |

**Tab evolution:** Original build had 8 tabs (Overview, Merchants, Budget, Anomalies, Reports, Forecasting, Savings, Action Plan). Session 10 collapsed to 3 priority tabs; Session 17 settled on the 5-tab structure above without losing functionality.

---

## How to Use

### Web UI (recommended)

Interactive Flask wizard: upload files, define categories, label merchants, auto-train until **70%+** accuracy, then view the 5-tab dashboard.

```bash
pip install -r requirements.txt
python src/app.py
# Open http://127.0.0.1:5000
```

**Workflow:**
1. **Upload** — drag Alipay `.csv` and/or WeChat `.xlsx` files
2. **Categories** — review and customize the 7 default spending categories
3. **Label** — assign a category per merchant; repeat until accuracy ≥ 70%
4. **Dashboard** — explore 5 interactive tabs (Overview, Budget & Forecast, Savings & Anomalies, Action Plan, Reports)

**How it works:**
- Starter merchant rules (~295 patterns) auto-label known chains (Meituan, DiDi, etc.) instantly
- UI iterates: you label ambiguous merchants → ML retrains → confidence updates in real-time
- Session data lives in `data/sessions/` (gitignored for privacy)
- On completion, trained model + categorized data sync to `data/` for offline use or Streamlit dashboard

### CLI setup (alternative)

This repo ships **starter templates**, not someone else's transactions or budget. Your financial data stays local (gitignored).

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Export Alipay + WeChat bills → drop in data/raw/
#    See data/raw/README.md for file names and export tips

# 3. One-command first-run setup (parse → seed rules → train → classify → budget)
python src/bootstrap.py --income 8000   # set your monthly income in CNY

# 4. Label your top merchants (improves accuracy from ~75% → 90%+)
#    Open data/exports/merchants_to_label.csv, fill suggested_category, re-run bootstrap

# 5. Dashboard
streamlit run src/dashboard.py
```

**What to expect**

| Stage | Category accuracy | Notes |
|-------|-------------------|-------|
| Day 1 (starter rules only) | ~75–85% | National chains (Meituan, DiDi, 麦当劳) auto-labeled |
| After filling `merchants_to_label.csv` | ~85–92% | Your local shops get rules |
| After 200+ labels + retrain | ~90–96% | Full ML pipeline kicks in |

Budget numbers in the dashboard come from **your** `data/budget_config.json` (auto-generated from spend history on bootstrap, then editable).

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

### 4. **Production-Ready Confidence Thresholds**
Merchant rules set confidence to 100% on match; ML predictions below 70% go to `needs_manual_review.csv`.

### 5. **Fairness-Aware Model Training**
Class weighting ensures minority spending categories (Transfers, Shopping) are learned equally well, not ignored in favor of majority categories.

### 6. **Interactive Dashboard**
Five tabs: spending overview, budget & forecast, savings & anomalies, action plan, and monthly reports/export — decision-making tools (savings calculator, investment readiness) plus IQR-based anomaly detection.

### 7. **Automated Retraining Pipeline**
Monthly workflow to identify ambiguous transactions, collect labels, retrain model, and evaluate without manual intervention.

---

## Validation & Robustness

### Cross-Validation Strategy
- **5-fold stratified cross-validation** ensures category distribution is preserved in each fold
- **Why stratified?** Dataset is imbalanced (47% Eating Out). Regular k-fold might accidentally put all minority samples in one fold, making metrics unreliable.
- **Result**: Honest accuracy (95.5%) instead of overfitted claims (99.1%)

### Confidence Calibration
- **Correct predictions**: 82.4% average confidence
- **Incorrect predictions**: 41.7% average confidence
- **Calibration ratio**: 2:1, indicating model is well-calibrated (knows when to be uncertain)

### Edge Cases Handled
- ✅ Empty merchant names → fallback to description
- ✅ All-numeric merchant IDs → handled gracefully
- ✅ Duplicate transactions → preserved (intentional for monthly totals)
- ✅ Low-confidence predictions → flagged for manual review
- ✅ Entirely new merchants → predicted based on description text alone
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
- [x] Multi-year trend analysis — `src/trends.py` built (Session 16); dashboard UI removed in Session 17 restructure — re-add when desired
- [x] Support additional payment sources — generic bank/card CSV parser in `parse.py`; see `data/raw/source_config.example.json`
- [ ] Automated feature engineering with larger datasets (2000+ samples)
- [ ] Mobile app for quick transaction review
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
- ✅ Problem-solving: identified and fixed misleading accuracy claims
- ✅ Honesty: reported real 95.5% instead of inflated 99.1%
- ✅ Iteration: improved fairness (F1-macro +39%) without sacrificing accuracy
- ✅ Documentation: detailed audit report, context tracking, decision rationale

### Technical Decisions Worth Discussing
1. **Why Logistic Regression over neural networks?** → Interpretability, speed, data efficiency (see table above)
2. **How does jieba help?** → Chinese segmentation enables TF-IDF to work correctly (see Technical Implementation)
3. **Why class weighting?** → Prevents majority category from dominating; ensures all categories learned fairly
4. **Why stratified CV?** → Honest metric that accounts for class imbalance; discovered real accuracy
5. **How do you handle low-confidence predictions?** → Thresholding strategy; confidence well-calibrated for safe auto-classification

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

**Last Updated:** Session 21 (2026-07-02) — Web UI complete; merchant category rules comprehensive (295+ patterns); documentation verified
