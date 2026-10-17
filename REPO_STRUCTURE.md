# Repository Structure

**Last updated**: 2026-10-17 (Session 77 cleanup: CLI-only code removed,
shared helpers, CI added). The Next.js + FastAPI + Supabase product is the only UI.

```
financing/
├── README.md                  # Project overview, quick start, honest-accuracy notes
├── REPO_STRUCTURE.md          # This file
├── CLAUDE.md                  # AI-assisted-session collaboration guidelines
├── requirements.txt           # ML pipeline deps (src/ + tests)
├── requirements-dev.txt       # + pytest
│
├── frontend/                  # Next.js 14 app → Vercel (see frontend/README.md)
│   ├── src/middleware.ts      # server-side auth gating
│   ├── src/app/               # auth, dashboard (5 sections, tabs code-split), settings pages
│   ├── src/components/        # ui-feedback.tsx atoms + ui/*.tsx + tabs/*.tsx
│   └── src/utils/             # supabase.ts, api.ts (auth interceptor), useApi.ts (dedupe + SWR), apiCache.ts (sessionStorage mirror), errors.ts (errorDetail), download.ts, useDismiss.ts, format.ts, chunkReload.ts, tour.ts; design rules in docs/DESIGN_SYSTEM.md (NO gradients, solid colors only)
│
├── backend/                   # FastAPI app → Render (see backend/README.md)
│   ├── main.py                # app, JWT auth middleware, CORS, rate limiting
│   ├── config.py              # env settings + service-role Supabase client
│   ├── db.py                  # run_query/fetch_all paging helpers, new_client() for background threads
│   ├── budget.py              # month windows, spend-by-category, budget crossings (dashboard + alerts)
│   ├── ml.py                  # per-user model loading (Storage) + bulk classification
│   ├── translations.py        # background worker: stores English merchant/description once per string
│   ├── fx.py                  # ECB rate cache (Frankfurter, background-only) + RateTable lookups for home currency
│   ├── errors.py              # log-and-mask error helper
│   ├── routes/                # auth (resolve-identifier only), categories, uploads, training, classify,
│   │                          #   dashboard (incl. cashflow), settings, subscriptions,
│   │                          #   transactions (manual + PATCH kind), fx (currencies)
│   ├── requirements.txt       # pinned backend deps (installed by Dockerfile)
│   ├── Dockerfile             # Docker context is the repo root (needs ../src/ too)
│   └── .env.example
│
├── src/                       # ML pipeline (imported by backend/ and tests/)
│   ├── parse.py               # Alipay/WeChat/bank parsers → common schema with kind + flow_subtype
│   ├── segment.py             # jieba tokenization + TF-IDF
│   ├── feature_engineering.py # hybrid features (weighted merchant/description + numeric; stats fitted at training)
│   ├── label.py               # merchant-rule matching (vectorized)
│   ├── merchant_categories.py # ~600 global rule patterns + description keywords (word-boundary matched)
│   ├── categories.py          # category constants, normalization map, prepare_labeled()
│   ├── classify.py            # rules-first + graduated-trust classification
│   ├── semantic.py            # embedding classifier (Model2Vec, LSA fallback)
│   ├── calibration.py         # top-label Platt scaling
│   ├── eval_grouped.py        # GroupKFold eval + auto-apply threshold derivation
│   ├── retrain.py             # training entry point (used by backend/routes/training.py)
│   ├── cv_utils.py            # merchant-leakage guard for CV splits
│   ├── recurring.py           # recurring/subscription merchant detection (pure pandas)
│   ├── llm_classify.py, translate.py, merchant_display.py
│   └── paths.py               # local data paths + ARTIFACT_FILES/artifact_paths() (model file names)
│
├── supabase/
│   ├── config.toml
│   └── migrations/            # 15 migrations:
│       ├── 20260703000000_initial_schema.sql          # 9 tables + RLS + triggers
│       ├── 20260703000001_seed_rules_and_categories.sql
│       ├── 20260704000000_create_storage_buckets.sql  # model_artifacts, uploads
│       ├── 20260705194314_fix_search_path_in_trigger_functions.sql
│       ├── 20260705194600_fix_reassign_category_trigger_missing_column.sql
│       ├── 20260706080000_fix_uploads_schema_mismatch.sql
│       ├── 20260707000000_security_performance_indexing_fixes.sql
│       ├── 20260707000001_fix_numeric_precision_overflow.sql
│       ├── 20260707000002_add_file_hash_for_deduplication.sql
│       ├── 20260707000003_fix_file_hash_constraint.sql
│       ├── 20260707092722_fix_file_hash_constraint.sql
│       ├── 20260708000000_release_readiness_schema_repair.sql
│       ├── 20260709000000_align_default_categories_to_ml_taxonomy.sql
│       ├── 20260709120000_add_category_color.sql
│       ├── 20260811090000_transaction_sum_rpcs.sql     # Postgres-side sum/monthly-spend RPCs
│       ├── … (2026-08-13/14 feature migrations)
│       ├── 20260927000000_restore_perf_indexes.sql     # user_id+timestamp/needs_review/category indexes, FK indexes, RLS initplan fix
│       ├── 20260927010000_add_english_label_columns.sql # transactions.merchant_en/description_en (stored translations)
│       ├── 20260927020000_dashboard_aggregate_rpcs.sql  # available_months/spend_trend RPCs, search_path fix
│       ├── 20260927030000_remove_purple_category_colors.sql # palette violet/indigo/fuchsia → blue/green/olive
│       ├── 20260927040000_onboarding_tour_state.sql     # profiles.tour_step/tour_finished_at (tour once per signup)
│       ├── 20261011000000_add_bank_transaction_source.sql   # transaction_source += 'bank' (own file: ADD VALUE)
│       ├── 20261011000100_transaction_kinds.sql             # transactions.kind (expense/income/transfer) + flow_subtype
│       ├── 20261011000200_expense_only_sql_functions.sql    # spend RPCs filter kind='expense'; daily cash-flow RPCs
│       ├── 20261011000300_uploads_parser_version.sql        # uploads.parser_version (v1 re-import reconciliation)
│       └── 20261011000400_fx_rates_home_currency.sql        # fx_rates cache + profiles.home_currency
│
├── tests/                     # pytest suite for src/ (158 tests)
│   ├── test_parse.py, test_parse_v2.py, test_numeric_stats.py, test_merchant_rules.py, test_semantic.py, test_calibration.py
│   ├── test_classify_routing.py, test_agreement_routing.py
│   ├── test_leakage_guard.py, test_reproducibility.py
│   ├── test_feature_engineering.py, test_matching_optimization.py
│   └── conftest.py
│
├── .github/workflows/
│   ├── ci.yml                 # PRs: src + backend pytest, frontend typecheck + build, design gate
│   └── keepalive.yml          # pings /health/deep every 10 min (free-tier keep-alive)
│
├── scripts/
│   ├── test_local.sh          # local backend run helper (not a test suite)
│   ├── design_gate.sh         # fails on gradients/blur/glass/purple in frontend/src
│   └── backfill_fx.py         # manual FX rate seed (Frankfurter → fx_rates)
│
├── docs/
│   ├── context.md             # project memory: sessions, decisions, open items
│   ├── DESIGN_SYSTEM.md       # frontend tokens, motion, effects, components ("Ledger" v5)
│   ├── contracts/API_V5.md    # frozen API contract: kinds, cash flow, home currency, bank import
│   ├── audits/                # COMPETITOR_AUDIT_2026-10.md, VERIFICATION_2026-10.md
│   ├── design/                # palette-validation-2026-10.txt (contrast + palette validator output)
│   ├── PROJECT_SUMMARY.md     # architecture overview + phase history
│   ├── SECURITY_AUDIT.md      # security checklist + test specs
│   ├── FULL_AUDIT.md          # ML integrity audit (historical, still relevant)
│   └── guides/                # START_LOCAL, TEST_LOCAL, DEPLOYMENT, MIGRATION_GUIDE
│
└── data/                      # user data — gitignored except templates/readmes
    ├── raw/                   # original exports (local CLI use)
    ├── processed/, labeled/, intermediate/, exports/, reports/
    └── templates/             # merchant_rules_starter.csv, budget_config.example.json
```

## What was removed (2026-07-06, recoverable from git history)

- `web/` — legacy Flask/PWA UI; `.streamlit/` + the Streamlit dashboard
  modules in `src/` (app, dashboard, dashboard_helpers, dashboard_data,
  web_pipeline, session_context, translate, merchant_display, forecast,
  trends, budget_loader)
- Superseded CLI scripts: `bootstrap.py`, `train.py`, `eval.py`,
  `export_en.py`, `find_other_candidates.py`, `visualize.py`
- `_archive/` (old experiments), `scripts/run_all.py` (broken since reorg),
  `docs/phase1_analysis.py`, `docs/phase4_analysis.py`, `docs/CLEANUP_SUMMARY.md`
- `backend/migrate_personal_data.py` (contained personal data; procedure
  documented in `docs/guides/MIGRATION_GUIDE.md`)

## What was removed (2026-10-17, Session 77)

- `src/validate.py`, the CLI sections of parse/classify/label/segment/
  feature_engineering/merchant_categories, `LOCAL_MERCHANT_RULES`
- `supabase/generate_seed_migration.py` (emitted the pre-2026-07 taxonomy)
- Backend `/auth/signup`, `/auth/login`, `/auth/logout` (unused, unsafe)
- Frontend `ui/motion.tsx`, `ui/Stepper.tsx`, `ui/MoneyPair.tsx`, unused exports
