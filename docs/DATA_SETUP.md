# Data Setup & Folder Structure

## Overview

This project processes financial transactions from Alipay and WeChat Pay, cleans them, labels them with categories, and trains a classifier to automatically categorize future transactions.

## Source Files

### Input Data (Raw)

```
/data/raw/
├── alipay.csv              [NOT USED - GBK encoding issues]
├── wechat.csv              [Fallback - GBK encoding issues, corrupts on save]
└── raw-wechat.xlsx         [PREFERRED - Original WeChat Excel with Chinese texts]
```

**Decision:** 
- **Alipay**: Use translated CSV from external folder: `C:\Users\User\Downloads\Finances_1st year\alipay_expenses.csv`
- **WeChat**: Use native Excel file: `/data/raw/raw-wechat.xlsx` (original texts preserved)
- **Policy going forward**: Accept WeChat only as Excel files (.xlsx), not CSV

### Processed Data

```
/data/processed/
├── transactions.csv                    [901 rows | Stage 1 output: raw parsed, normalized]
├── transactions_cleaned.csv            [901 rows | Stage 2 output: with 'text' column]
├── transactions_auto_labeled.csv       [901 rows | Stage 3 output: with 'category' column]
├── tfidf_vectorizer.pkl                [Stage 4 output: fitted TF-IDF vectorizer]
└── classifier.pkl                      [Stage 5 output: trained Logistic Regression model]
```

### Labeled Data (Manual Rules & Labels)

```
/data/labeled/
├── merchant_rules.csv                  [ORIGINAL: 54 merchant → category mappings]
├── merchant_rules_expanded.csv         [CURRENT: 91 rules + ~45 user-categorized]
└── labeled_transactions.csv            [Final output: all 901 transactions with categories]
```

## Column Schemas

### Raw Alipay CSV
- Transaction Time
- Transaction Category
- Transaction Counterparty
- Product Description
- Type (Expense / Not Counted)
- Amount
- Payment Method
- Transaction Status
- ...

### Raw WeChat Excel (原始微信账单)
- 交易时间 (Transaction Time)
- 交易类型 (Transaction Type)
- 交易对方 (Merchant/Counterparty)
- 商品 (Product/Description)
- 收/支 (Income/Expense: 支出 = Expense)
- 金额(元) (Amount in CNY)
- 支付方式 (Payment Method)
- 当前状态 (Status: 支付成功 / 已转账)
- 交易单号 (Transaction ID)
- 商户单号 (Merchant Order No)
- 备注 (Remarks)

### Normalized Schema (Used Throughout Pipeline)

| Column | Type | Notes |
|--------|------|-------|
| timestamp | datetime | Unified time format |
| merchant | string | Merchant/counterparty name (English or Chinese) |
| description | string | Product/service description |
| amount | float | Amount in CNY (positive = expense) |
| source | string | "alipay" or "wechat" |

### With Cleaning (Stage 2)
- All columns above, plus:
- **text** | string | Combined merchant + description, lowercased English, Chinese preserved |

### With Labeling (Stage 3)
- All columns above, plus:
- **category** | string | One of 10 target categories (or NaN if unlabeled) |
- **labeled** | bool | True if auto-labeled, False if still needs manual categorization |

## Processing Pipeline

```
1. Parse (Stage 1)
   Input: Alipay CSV + WeChat Excel
   Output: transactions.csv (normalized)
   
2. Clean (Stage 2)
   Input: transactions.csv
   Output: transactions_cleaned.csv (with 'text' column)
   
3. Label (Stage 3)
   Input: transactions_cleaned.csv + merchant_rules_expanded.csv
   Output: transactions_auto_labeled.csv (with 'category' column)
   
4. Vectorize (Stage 4)
   Input: transactions_auto_labeled.csv (only labeled rows)
   Output: tfidf_vectorizer.pkl (fitted vectorizer)
   
5. Train (Stage 5)
   Input: vectorized data + labels
   Output: classifier.pkl (trained model)
   
6. Classify (Stage 6)
   Input: new CSV/Excel + vectorizer + classifier
   Output: predictions for new transactions
   
7. Visualize (Stage 7)
   Input: categorized transaction data
   Output: charts and dashboards
```

## Data Statistics

**As of Session 2:**
- Total transactions: 901
- Alipay: 243 (¥6,851.28)
- WeChat: 658 (¥17,043.72)
- Date range: 2025-08-23 to 2026-05-16
- Auto-labeled: ~850+ (94%+)
- Categories: 10 standard categories + "Other"

## Notes

- All processing is deterministic and reproducible via `requirements.txt` + scripts
- Sensitive data (transaction IDs, phone numbers) can be anonymized before sharing
- Excel parsing requires `openpyxl` package
- Chinese tokenization requires `jieba` package
