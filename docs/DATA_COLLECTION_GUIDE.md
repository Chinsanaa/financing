# DATA COLLECTION GUIDE: What to Label Next

**Current State:** 764 labeled transactions across 8 categories (1 category too small)  
**Goal:** Reach 1,500+ labeled transactions with balanced representation  
**Priority:** Focus on minority categories and fill gaps

---

## CURRENT DATA GAPS

### 🔴 CRITICAL (0% Recall - Must Collect Data)

| Category | Current | Needed | Why |
|----------|---------|--------|-----|
| **Travel** | 2 samples | 30 | Can't train on <10 samples |
| **Other** | 5 samples | 25 | Too small to be reliable |

**Action:** Label ANY transactions in these categories from your raw CSV. If you don't have any, merge these into a catch-all category.

### 🟡 HIGH (Recall < 90% - Collect More)

| Category | Current | Needed | Why |
|----------|---------|--------|-----|
| **Transfers & Gifts** | 20 samples | 50 total (30 more) | Needs 50+ for stable training |
| **Shopping** | 50 samples | 80-100 total (30-50 more) | Frequently confused with Eating Out |

**Action:** Label 30-50 more transactions from each category. Focus on edge cases (transactions that could be mislabeled):
- Shopping: High-end purchases, shopping malls, department stores
- Transfers: P2P transfers, gifts, account transfers

### 🟢 GOOD (Recall ≥ 90% - Maintain Balance)

| Category | Current | Status |
|----------|---------|--------|
| **Eating Out** | 311 | ✅ Healthy (40.7%) |
| **Groceries** | 204 | ✅ Healthy (26.7%) |
| **Transportation** | 166 | ✅ Healthy (21.7%) |
| **Utilities & Services** | 5 | ✅ Recently fixed (class weights) |
| **Health & Wellness** | 1 | ❌ Delete this category |

---

## HOW TO LABEL DATA EFFICIENTLY

### Step 1: Identify Unlabeled Transactions
```bash
# Check which transactions in raw data are unlabeled
python -c "
import pandas as pd
df = pd.read_csv('data/processed/transactions.csv')
print(f'Total transactions: {len(df)}')
df_labeled = pd.read_csv('data/labeled/labeled_transactions.csv')
print(f'Labeled: {len(df_labeled[df_labeled[\"labeled\"] == True])}')
print(f'Unlabeled: {len(df) - len(df_labeled)}')
"
```

### Step 2: Focus on Minority Categories
Priority order for labeling:
1. **Travel** (need 30 samples)
2. **Other** (need 25 samples)
3. **Transfers & Gifts** (need 30-50 samples)
4. **Shopping** (need 30-50 samples)

### Step 3: Run Interactive Labeling
```bash
cd /path/to/project
python src/label.py  # Use interactive_label() to manually label transactions
```

### Step 4: Re-train and Evaluate
After labeling ~50 new transactions:
```bash
python src/tune.py        # Find best hyperparameters
python src/compare_models.py  # See improvements
```

---

## WHAT TO LOOK FOR WHEN LABELING

### Travel Transactions
- ✅ Flight tickets, hotels, rental cars, tours
- ✅ Airplane food, airport lounges
- ✅ International transfers (wire fees for vacation)
- ❌ NOT: Uber to airport (that's Transportation)
- ❌ NOT: Hotel restaurant (that's Eating Out)

**Current issue:** Only 2 samples. These are too few to establish patterns.

### Transfers & Gifts
- ✅ Money to friends/family
- ✅ Split bills, group payments
- ✅ Refunds from merchants
- ✅ Account-to-account transfers
- ❌ NOT: Paid through a payment app as Eating Out (use merchant, not transfer)

**Current issue:** Only 20 samples. Often confused with Eating Out (restaurants get misclassified).

### Shopping (Hard Cases)
- ✅ Clothing, electronics, books, furniture
- ✅ Amazon, Taobao, mall purchases
- ⚠️ **HARD:** Online shopping platforms with food sections (Pinduoduo)
- ⚠️ **HARD:** Malls that have both shopping + food courts
- ❌ NOT: Grocery store (that's Groceries)
- ❌ NOT: Cosmetics/beauty (should be Shopping, not Eating Out)

**Current issue:** 50 samples but 30% error rate. Many are mislabeled as Eating Out.

### Utilities & Services
- ✅ Internet, water, electricity, gas bills
- ✅ Subscriptions (Netflix, Spotify)
- ✅ Phone plans
- ✅ Insurance payments
- ✅ Gym memberships
- ❌ NOT: Online shopping (Shopping)

**Current issue:** Recently improved to 100% F1 with only 5 samples (luck!). Fragile—collect more data to stabilize.

---

## ESTIMATED EFFORT

| Task | Time | Samples |
|------|------|---------|
| Label 30 Travel transactions | 30-45 min | 30 |
| Label 25 Other transactions | 30-45 min | 25 |
| Label 50 Shopping transactions | 45-60 min | 50 |
| Label 30 Transfers transactions | 30-45 min | 30 |
| Re-train and evaluate | 10 min | - |
| **TOTAL** | **2.5-3.5 hours** | **135 new** |

**After labeling:** Model should reach F1 ≥ 0.95 on all major categories.

---

## QUALITY CHECKS

### Before Committing Labels
1. **Check for duplicates:** Same transaction labeled differently? Fix it.
2. **Check for ambiguous transactions:** If YOU can't decide, mark as "Other"
3. **Check merchant consistency:** All transactions from same merchant should usually be same category (use merchant rules)

### Command to Check Label Quality
```bash
python -c "
import pandas as pd
df = pd.read_csv('data/labeled/labeled_transactions.csv')
# Check for merchants with conflicting labels
merchant_categories = df.groupby('merchant')['category'].nunique()
conflicts = merchant_categories[merchant_categories > 1]
if len(conflicts) > 0:
    print(f'WARNING: {len(conflicts)} merchants have conflicting labels!')
    print(conflicts.head())
else:
    print('✅ No conflicting merchant labels found')
"
```

---

## AFTER LABELING: NEXT STEPS

### 1. Immediate (after labeling)
```bash
# Re-train with new data
python src/tune.py

# Evaluate
python src/compare_models.py

# Check per-category performance
python src/eval.py
```

### 2. Expected Results
- **F1-macro should improve** from 0.73 (after the class-weight fix, before new data) → target 0.85+
- **Travel & Other F1** should jump from 0-10% → 70%+ (these two are still the real gap)
- **Shopping & Transfers F1** should improve from ~91-94% → 95%+

### 3. If Still Not Good Enough
- Collect another 100 samples for minority categories
- Implement confidence threshold (only auto-classify if confidence > 0.8)
- Use Naive Bayes ensemble (vote between LR and NB)

---

## LONG-TERM STRATEGY

**6 months:**
- 2,000+ labeled transactions
- F1-macro ≥ 0.85 on all categories
- Automated monthly retraining

**1 year:**
- 3,000+ labeled transactions
- Add 2-3 new categories (Entertainment, Insurance, Salary)
- Multi-month trend analysis
- Budget forecasting

---

## QUICK START

**Want to label data now?**

1. Copy unlabeled transactions to a spreadsheet
2. For each transaction, label by category
3. Save to `data/labeled/labeled_transactions.csv`
4. Run `python src/eval.py` to see improvement

**Example workflow:**
```bash
cd /path/to/project

# Check current status
python src/eval.py

# Label new data (manual step)
# ... edit spreadsheet ...

# Re-train
python src/tune.py

# Check improvement
python src/compare_models.py
```

---

**Key Insight:** The class-weight fix already pushed F1-macro from 0.55 → 0.73 for free. What's left is almost entirely Travel (2 samples) and Other (5 samples) sitting at 0% recall — no amount of tuning fixes that, only labeling more examples will. Collecting ~55 samples across those two categories is the highest-ROI next step, well above any further model tuning.
