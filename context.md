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

## Key Terms

- **Tokenization**: splitting text into words (`jieba` for Chinese).
- **TF-IDF**: text → numbers; distinctive merchant tokens score high.
- **Classifier**: learns text → category from labeled examples.
- **Bootstrap**: starter merchant rules + `merchants_to_label.csv` before full ML accuracy.

## Open Questions / Not Yet Decided

- [ ] Wire `merchants_to_label` editing into Streamlit dashboard
- [ ] Re-add multi-year trends (`src/trends.py`) to dashboard UI
- [ ] How to handle refunds / internal transfers long-term (currently filtered at parse)

## Next Suggested Step

Run `python src/app.py` and complete the web wizard with your Alipay/WeChat exports.

## Current State (Session 20, 2026-07-01)

| Item | Status |
|---|---|
| Personal transaction data in repo | **Removed** — gitignored; templates only |
| Raw exports | User adds locally (`data/raw/`) |
| Merchant rules | `data/templates/merchant_rules_starter.csv` copied on bootstrap |
| Labeled training data | Created per-user by bootstrap + manual labeling |
| Classifier | Trained per-user via `retrain.py` / bootstrap |
| Budget config | `data/templates/budget_config.example.json` → user `budget_config.json` |

## Session Log

### Session 20 (2026-07-01) — Web onboarding UI
- `src/app.py` Flask server + `web/templates/index.html` wizard
- Steps: upload → define categories → label merchants → iterate to 70%+ → 5-tab HTML dashboard
- `src/session_context.py`, `src/web_pipeline.py`, `src/dashboard_data.py`
- Per-session workspaces under `data/sessions/` (gitignored)
- **English-only UI**: `src/translate.py` + fix in `merchant_display.display_merchant()` — Streamlit and web both route display through translation when no chain mapping exists (was returning raw Chinese)
- **Merchant category rules**: `src/merchant_categories.py` — 295 chain/local patterns mapped to Groceries, Eating Out, Shopping, Transportation, Utilities & Services; synced to `merchant_rules_*.csv`; longest-pattern-first matching in `label.py`

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
