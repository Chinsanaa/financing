# context.md — Project Memory & Explainer

This file is the running record of the project: what it is, what's been
decided, what's open, and what's next. Claude Code should read this at the
start of every session and update it at the end.

---

## The Problem

While living in China, expenses were split across Alipay and WeChat Pay.
Neither app gives a clean combined view of spending, and manually
categorizing transactions (Food, Transport, Shopping, etc.) from exported
CSVs was too time-consuming to keep up with.

## The Goal

A pipeline that:
1. Takes multiple CSV exports (Alipay + WeChat, possibly more sources later)
2. Automatically categorizes each transaction
3. Visualizes spending (by category, over time, by merchant)
4. Improves with use, instead of needing manual re-categorization every time

## Why This Is a Classification Problem, Not Clustering

- K-means is **unsupervised** — no category names like "Food" or "Transport."
- We know target categories in advance → **supervised classification**.
- Clustering is only a bootstrap/discovery tool for unlabeled "Other" rows.

## Key Decisions Made So Far

| Decision | Choice | Why |
|---|---|---|
| Categorization approach | Supervised text classification | Known target categories |
| Category list strategy | Starter rules + ML + manual labels | Control + improves over time |
| Transaction text language | Mixed Chinese and English | Needs `jieba` for Chinese |
| Feature extraction | TF-IDF on segmented text | Simple, interpretable |
| Model | Logistic Regression (`class_weight='balanced'`, `C=10`) | Fast baseline for ~1k samples |
| Training data | ~200–500 manual labels minimum; bootstrap seeds from rules | Supervised learning needs labels |
| New-user onboarding | `src/app.py` web wizard + `src/bootstrap.py` CLI | No personal data in repo |
| Visualization | Web HTML dashboard + Streamlit (`dashboard.py`) | 5-tab layout |
| Refunds | Kept, netted as negative amount in same category/merchant | Purchase + refund should cancel out, not just vanish |
| Internal transfers (credit card repayment, withdrawal) | Excluded entirely at parse (`_TRANSFER_KEYWORDS` in `parse.py`) | Not real spending; would double-count |
| Peer-to-peer transfers (转账/红包) | Left as expense (not auto-excluded) | Ambiguous — could be a real gift/spend; user can extend `_TRANSFER_KEYWORDS` if they want these excluded too |

## Key Terms

- **Tokenization**: splitting text into words (`jieba` for Chinese).
- **TF-IDF**: text → numbers; distinctive merchant tokens score high.
- **Classifier**: learns text → category from labeled examples.
- **Bootstrap**: starter merchant rules + `merchants_to_label.csv` before full ML accuracy.

## Open Questions / Not Yet Decided

- [ ] Wire `merchants_to_label` editing into Streamlit dashboard
- [ ] Re-add multi-year trends (`src/trends.py`) to dashboard UI
- [x] How to handle refunds / internal transfers — resolved Session 22, see Key Decisions

## Next Suggested Step

Run `python src/app.py` and complete the web wizard with your Alipay/WeChat exports.

## Current State (Session 21, 2026-07-02)

| Item | Status |
|---|---|
| Personal transaction data in repo | **Removed** — gitignored; templates only |
| Raw exports | User adds locally (`data/raw/`) |
| Merchant rules | `data/templates/merchant_rules_starter.csv` + in-code rules in `src/merchant_categories.py` (295+ patterns) |
| Labeled training data | Created per-user by bootstrap + manual labeling |
| Classifier | Trained per-user via `retrain.py` / bootstrap |
| Budget config | `data/templates/budget_config.example.json` → user `budget_config.json` |
| Web UI | Flask app (`src/app.py`) with interactive wizard; per-session workspaces (`data/sessions/`, gitignored) |
| English-only display | `src/translate.py` provides consistent translations in both web + Streamlit UIs |

## Session Log

### Session 23 (2026-07-02) — NYU Shanghai admin fees recategorized
- `special_category()` in `src/merchant_categories.py`: the 3 NYU Shanghai admin-fee markers (Campus Card Top Up, Tuition and Fees, NYUCard Print Fee) now map to `Utilities & Services` instead of `Other` — they're campus services, not uncategorized spend
- Renamed `NYU_OTHER_DESCRIPTION_MARKERS` → `NYU_SERVICE_DESCRIPTION_MARKERS` to match
- No blanket merchant rule involved (NYU Shanghai is description-split, not in `MERCHANT_CATEGORY_RULES`), so no CSV re-sync needed

### Session 22 (2026-07-02) — Refund netting & internal transfer exclusion
- Resolved the open question on refunds/transfers in `src/parse.py`:
  - **Refunds** (交易状态/Transaction Status contains 退款/Refund): kept as a negative-amount row instead of dropped, so they net against the original purchase in category/merchant totals
  - **Internal transfers** (交易分类/交易类型 contains 信用卡还款, 花呗还款, 提现): excluded entirely — moving your own money isn't spend
  - **P2P transfers** (转账/红包): deliberately left as-is (still counted as expense) — ambiguous whether a transfer to another person is "spending"; `_TRANSFER_KEYWORDS` in `parse.py` documents how to add them if wanted
  - Native Chinese Alipay/WeChat exports get the full split (both column types available); English-translated fallback formats (`parse_alipay_english`, `parse_wechat_csv`) only get refund netting since they lack a transaction-type column — documented as a limitation in their docstrings
- Verified with synthetic CSV/XLSX fixtures (no real user data available): confirmed refund nets correctly, credit card repayment excluded, unrelated expense/closed transactions unaffected
- Downstream code (dashboard, forecast, visualize) all aggregate `amount` via `.sum()`/`.groupby()` — confirmed negative refund amounts net correctly with no other code changes needed

### Session 21 (2026-07-02) — Documentation Review
- Read through codebase: web UI fully functional, merchant rules comprehensive, pipeline modular
- Verified current file state: no uncommitted changes on `claude/update-readme-context-j82rsk`
- Updated context.md and README.md for accuracy and completeness
- All prior commits (Sessions 0–20) verified; repo is adoptable by new users

### Session 20 (2026-07-01) — Web onboarding UI & merchant rules
- `src/app.py` Flask server + `web/templates/index.html` wizard
- Steps: upload → define categories → label merchants → iterate to 70%+ → 5-tab HTML dashboard
- `src/session_context.py`, `src/web_pipeline.py`, `src/dashboard_data.py`
- Per-session workspaces under `data/sessions/` (gitignored)
- **English-only UI**: `src/translate.py` + fix in `merchant_display.display_merchant()` — Streamlit and web both route display through translation when no chain mapping exists (was returning raw Chinese)
- **Merchant category rules**: `src/merchant_categories.py` — 295+ chain/local patterns mapped to 7 categories; synced to `merchant_rules_*.csv`; longest-pattern-first matching in `label.py`

### Session 19 (2026-07-01) — Personal data purge
- Deleted all raw exports, labeled data, models, processed CSVs, budget config, exports, reports
- `git rm --cached` on previously tracked personal files + `_archive` debug artifacts
- Scrubbed `merchant_display.py`, `forecast.py` defaults, README metrics
- Historical session logs (1–17) removed — contained private transaction details
- Repo is adoptable: templates + code only

### Session 18 (2026-07-01) — Adoption / new-user bootstrap
- `src/bootstrap.py`, `src/paths.py`, `data/templates/`, `data/raw/README.md`
- Rules-only classify fallback; `.gitignore` for user data paths

### Session 0 (planning)
- Problem definition, supervised vs clustering, CLAUDE.md + context.md

### Sessions 1–17 (redacted)
- Built full pipeline (parse → classify → dashboard) on private data.
- Detailed logs removed in Session 19 for privacy.
