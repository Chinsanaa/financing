# Repository Structure

**Last updated**: 2026-07-06 (post-cleanup: legacy Flask/PWA and Streamlit
stacks removed; the Next.js + FastAPI + Supabase product is the only UI).

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
│   ├── src/app/               # auth, dashboard (10 tabs), settings pages
│   ├── src/components/        # ui.tsx atoms + tabs/*.tsx
│   └── src/utils/             # supabase.ts, api.ts (auth interceptor), useApi.ts (cache)
│
├── backend/                   # FastAPI app → Railway (see backend/README.md)
│   ├── main.py                # app, JWT auth middleware, CORS, rate limiting
│   ├── config.py              # env settings + service-role Supabase client
│   ├── ml.py                  # per-user model loading (Storage) + bulk classification
│   ├── errors.py              # log-and-mask error helper
│   ├── routes/                # auth, categories, uploads, training, classify,
│   │                          #   dashboard, settings
│   ├── requirements.txt       # pinned backend deps (installed by Dockerfile)
│   ├── railway.json, Procfile, Dockerfile
│   └── .env.example
│
├── src/                       # ML pipeline (imported by backend/ and tests/)
│   ├── parse.py               # Alipay/WeChat parsers → common schema
│   ├── segment.py             # jieba tokenization + TF-IDF
│   ├── feature_engineering.py # hybrid features (weighted merchant/description + numeric)
│   ├── label.py               # merchant-rule matching (vectorized)
│   ├── merchant_categories.py # ~600 global rule patterns + description keywords
│   ├── categories.py          # category constants + normalization map
│   ├── classify.py            # rules-first + graduated-trust classification
│   ├── semantic.py            # embedding classifier (Model2Vec, LSA fallback)
│   ├── calibration.py         # top-label Platt scaling
│   ├── eval_grouped.py        # GroupKFold eval + auto-apply threshold derivation
│   ├── retrain.py             # training entry point (used by backend/routes/training.py)
│   ├── cv_utils.py            # merchant-leakage guard for CV splits
│   ├── validate.py            # data sanity checks
│   └── paths.py               # CLI-mode artifact paths
│
├── supabase/
│   ├── config.toml
│   ├── generate_seed_migration.py   # regenerates the rules-seed SQL
│   └── migrations/            # 6 migrations:
│       ├── 20260703000000_initial_schema.sql          # 9 tables + RLS + triggers
│       ├── 20260703000001_seed_rules_and_categories.sql
│       ├── 20260704000000_create_storage_buckets.sql  # model_artifacts, uploads
│       ├── 20260705194314_fix_search_path_in_trigger_functions.sql
│       ├── 20260705194600_fix_reassign_category_trigger_missing_column.sql
│       └── 20260706080000_fix_uploads_schema_mismatch.sql
│
├── tests/                     # pytest suite for src/ (71 tests)
│   ├── test_parse.py, test_validate.py, test_semantic.py, test_calibration.py
│   ├── test_classify_routing.py, test_agreement_routing.py
│   ├── test_leakage_guard.py, test_reproducibility.py
│   ├── test_feature_engineering.py, test_matching_optimization.py
│   └── conftest.py
│
├── scripts/
│   └── test_local.sh          # local backend run helper (not a test suite)
│
├── docs/
│   ├── context.md             # project memory: sessions, decisions, open items
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
