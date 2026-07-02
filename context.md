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

- [x] Wire `merchants_to_label` editing into Streamlit dashboard — resolved Session 25
- [x] Re-add multi-year trends (`src/trends.py`) to dashboard UI — resolved Session 25
- [x] How to handle refunds / internal transfers — resolved Session 22, see Key Decisions

Open items are tracked in the Session 27 audit entry below (privacy/git-history
scrub is the main one needing a user decision).

## Next Suggested Step

Decide on the git-history privacy scrub (Session 27 open item #1). Otherwise run
`python run_all.py` (deterministic full pipeline) or `python src/app.py` for the
web wizard with your Alipay/WeChat exports.

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

### Session 27 (2026-07-02) — ML integrity audit (honest evaluation & reproducibility)
Full audit written to `docs/FULL_AUDIT.md`. Worked phase by phase with user sign-off.

- **The big finding — merchant leakage.** The dataset is 863 labeled rows but only
  **109 unique merchants** (top 10 = 73%, one merchant = 16.5%; 568/863 texts are
  duplicates). The merchant name is part of the vectorized text, so the model
  memorizes merchant→category. Honest numbers:
  - Stratified 5-fold CV (known merchants): **~95% acc, F1-macro ~0.85**
  - **GroupKFold by merchant (NEW merchants): ~45% acc, F1-macro ~0.44** — barely above the 38.5% majority baseline.
  - So ~50 points of the old headline was memorization, not generalization.
- **Old docs were wrong.** 99.1% / 97.3% / 95.5% were single stratified runs on
  different dataset sizes, quoted as if one true number. Feature counts (275/639/657)
  and label counts (776/850) were all stale — real: **~660 features, 863 labeled rows**.
- **`retrain.py`'s per-category table is in-sample** (model scored on its own training
  data) → inflated by construction. Don't quote it as accuracy.
- **Tiny classes → rule-only (user decision).** Utilities & Services (5 rows, 2 unique
  texts; its 1.000 F1 was a duplicate/empty-fold artifact → 0.000 under GroupKFold) and
  other rare cleanly-ruleable categories are assigned by rules only; "Other" is the
  explicit review/residual bucket. Not merged, not blocked on more labels.
- **Two-stage design adopted (user decision) + implemented.** `classify.py`: rules/
  overrides are trusted; model predictions on no-rule (unseen) merchants are *suggestions
  routed to review* regardless of confidence (Phase 4 showed even 0.9+ confidence is only
  ~89% accurate on unseen merchants). Added `label_source` column. The 0.70 gate no longer
  auto-accepts.
- **Tuning (honest).** `C=10 → C=1.0` in `segment.py` (C=10 had been tuned on the leaky CV);
  under GroupKFold C=1.0 gives +8.9pts acc / +0.106 F1-macro with stratified unchanged.
- **Tests + reproducibility.** New `tests/` suite (18→20 passing): parse (encoding, refund
  netting, transfer filtering, schema, duplicates), **leakage guard** (`src/cv_utils.py` —
  fails if a merchant is in both train & test), two-stage routing, data validation
  (`src/validate.py`), fixed-seed reproducibility. One command: **`python run_all.py`**
  (raw→parse→label→train→classify→metrics, deterministic; `--honest` adds GroupKFold). Pinned
  the one missing seed (`label.py` display sample).
- **README reconciled** to one source of truth: added a "How accuracy is measured" section
  (stratified vs GroupKFold), removed every stale figure, reframed around rules-first.
- **Open items:**
  1. ⚠️ **Privacy:** Session 19's data purge removed personal data from the working tree
     but **not from git history** — raw exports + labels are still recoverable from the
     public repo. Proper fix = history rewrite (`git filter-repo`) + force-push. **User decision needed.**
  2. Even at C=1.0, unseen-merchant accuracy (~45%) is only just above baseline. Real
     improvement would come from more *distinct* merchants/labels, not model tuning.
  3. Consider enforcing rule-only for Utilities in code (currently a data/labeling
     convention, not enforced in the training label set).

### Session 26 (2026-07-02) — Monthly spending trend line (Overview tab)
- Added a plain "Monthly Spending Trend" line chart (total ¥ per month, not stacked by category, not cumulative) right under the KPI cards on Overview — the stacked bar and cumulative line already there don't make month-to-month direction easy to read at a glance.
- Followed the dataviz skill: single series (no legend needed), 2px purple line + ≥8px markers with a surface-color ring, ~10% opacity area wash, dashed muted-gray average reference line, direct endpoint label (latest month's ¥ value), hairline recessive gridlines (reused existing `apply_chart_theme`), hover tooltip via `hovertemplate`.
- Verified live with Playwright against synthetic 2-year data with deliberate month-to-month variance — renders cleanly, no exceptions.

### Session 25 (2026-07-02) — Streamlit: Label Queue tab + multi-year trends
Closed out the two remaining open questions from earlier sessions.

- **Multi-year trends** (`src/dashboard.py`, Overview tab): new "Yearly & Seasonal Trends" section using `src/trends.py` (built Session 16, never wired up). Seasonal profile (avg spend per calendar month, pools all years) always shows; year-over-year bar chart + growth caption only render once `trends.multi_year_ready()` is true (2+ calendar years), otherwise shows an explanatory `st.info`.
- **Label Queue tab** (`src/dashboard.py`, new 5th tab before Reports): editable `st.data_editor` table backed by `data/exports/merchants_to_label.csv`. Merchant/description shown via `translate.enrich_label_row()` (English-only, consistent with the web UI); raw Chinese merchant id kept in the underlying dataframe for saving but hidden from display via `column_order`. "Apply & retrain" button calls a new `bootstrap.apply_label_queue_and_retrain()`.
- **New backend function** `bootstrap.apply_label_queue_and_retrain()`: applies filled-in categories to merchant rules, seeds `labeled_transactions.csv` from the updated rules, retrains only if `can_train()` passes (otherwise reports why not), reclassifies all transactions, and refreshes the queue with whatever's still unlabeled. Reuses the same building blocks `run_bootstrap()` already had imported — no new dependencies.
- **Bug found and fixed while verifying**: `export_merchants_to_label()` skipped writing the CSV entirely when nothing was left to label, so a fully-labeled queue kept showing stale already-applied rows forever (in both the CLI flow and, more visibly, this new tab's "apply until empty" loop). Fixed to always overwrite, writing an empty (headers-only) CSV when there's nothing left.
- **Verified live**: ran `streamlit run src/dashboard.py` against synthetic 2-year, multi-category data with one deliberately unlabeled merchant; drove it with headless Chromium (Playwright) — confirmed the trends section renders (seasonal bars + YoY bars + caption), the Label Queue tab renders with no exceptions, and clicking "Apply" actually adds the rule, retrains (83% CV accuracy in the synthetic run), reclassifies, and empties the queue.

### Session 24 (2026-07-02) — PWA: mobile app for quick transaction review
- Turned the existing Flask web UI into an installable PWA rather than building a separate native/React Native app — ticked the README future-enhancement box
- Added `web/static/manifest.json` (name, theme colors, icons), `web/static/sw.js` (caches app shell only; `/api/*` always hits network so transaction/label data is never stale), and two hand-generated solid-color PNG icons (`web/static/icons/icon-192.png`, `icon-512.png` — no Pillow dependency, built with stdlib `zlib`/`struct`)
- `src/app.py`: new `/sw.js` route serving from root (not `/static/`) so the service worker's default scope covers the whole app, not just `/static/`
- `web/templates/index.html`: manifest link, apple-touch-icon, theme-color and `apple-mobile-web-app-*` meta tags for iOS/Android install prompts
- `web/static/js/app.js`: registers the service worker on load
- `web/static/css/app.css`: bumped touch-target size for `.btn`/`.merchant-card select` under 480px — the Label step (Step 3) is the "quick transaction review" screen
- Verified with a real headless Chromium session (Playwright, iPhone viewport/UA): manifest resolves, service worker reaches `activated` state, existing responsive layout already stacks correctly on a phone screen
- Did not add a persistent "resume session" feature — the app has no session-resume concept at all today (every page load creates a fresh session), so that's a separate, bigger decision if wanted later

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
