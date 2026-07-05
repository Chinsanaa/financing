# Repository Structure — Financing SaaS

**Organized**: 2026-07-06  
**Status**: ✅ Clean, professional structure

---

## 📁 Directory Tree

```
financing/
│
├── 📄 README.md                       # Main entry point ⭐
├── 📄 CLAUDE.md                       # Project guidelines
├── 📄 requirements.txt                # Python dependencies
├── 📄 requirements-dev.txt            # Dev dependencies
├── .env.local                         # Secrets (gitignored)
├── .gitignore                         # Git rules
│
├── 📁 docs/                           # Documentation
│   ├── PROJECT_SUMMARY.md             # 6-phase overview & architecture
│   ├── SECURITY_AUDIT.md              # Security audit + test specs
│   ├── context.md                     # Full session memory (6 sessions)
│   ├── CLEANUP_SUMMARY.md             # Documentation cleanup report
│   ├── FULL_AUDIT.md                  # ML integrity audit (legacy)
│   ├── phase1_analysis.py             # ML analysis (legacy)
│   ├── phase4_analysis.py             # ML analysis (legacy)
│   │
│   └── 📁 guides/                     # How-to guides
│       ├── DEPLOYMENT.md              # Production setup (Railway + Vercel)
│       ├── MIGRATION_GUIDE.md         # Personal data migration
│       ├── START_LOCAL.md             # Local development setup
│       └── TEST_LOCAL.md              # Testing guidelines
│
├── 📁 scripts/                        # Utility scripts
│   ├── run_all.py                     # Full pipeline execution
│   └── test_local.sh                  # Test suite runner
│
├── 📁 backend/                        # FastAPI backend (Railway)
│   ├── main.py                        # App entry point
│   ├── config.py                      # Supabase config
│   ├── requirements.txt               # Backend dependencies
│   ├── README.md                      # Backend guide (7 route groups)
│   │
│   ├── 📁 routes/                     # API routes (7 groups)
│   │   ├── auth.py                    # POST signup, login, logout
│   │   ├── categories.py              # GET/POST/PATCH/DELETE categories
│   │   ├── uploads.py                 # POST file uploads
│   │   ├── training.py                # POST retrain, GET status
│   │   ├── classify.py                # POST label, accept
│   │   ├── dashboard.py               # GET 8 analytics endpoints
│   │   ├── settings.py                # GET/PATCH profile, DELETE account
│   │   └── __init__.py
│   │
│   └── migrate_personal_data.py       # One-time migration script
│
├── 📁 frontend/                       # Next.js frontend (Vercel)
│   ├── package.json                   # Node dependencies
│   ├── tsconfig.json                  # TypeScript config (fixed)
│   ├── next.config.js                 # Next.js config
│   ├── tailwind.config.js             # Tailwind CSS config
│   ├── postcss.config.js              # PostCSS config
│   ├── README.md                      # Frontend guide (6 tabs)
│   │
│   └── 📁 src/
│       ├── 📁 app/                    # Next.js App Router
│       │   ├── page.tsx               # Root redirect
│       │   ├── layout.tsx             # Root layout
│       │   ├── globals.css            # Global styles
│       │   │
│       │   ├── 📁 auth/               # Auth pages
│       │   │   ├── page.tsx           # Signup/Login form
│       │   │   └── verify/
│       │   │       └── page.tsx       # Email verification
│       │   │
│       │   ├── 📁 dashboard/          # Dashboard
│       │   │   └── page.tsx           # 6-tab dashboard
│       │   │
│       │   └── 📁 settings/           # Settings
│       │       └── page.tsx           # Account management
│       │
│       ├── 📁 components/
│       │   └── 📁 tabs/               # 6 dashboard tabs
│       │       ├── StatsTab.tsx       # Overview (KPIs, category breakdown)
│       │       ├── BudgetTab.tsx      # Budget & Forecast
│       │       ├── SavingsTab.tsx     # Savings & Anomalies
│       │       ├── ActionTab.tsx      # Action Plan
│       │       ├── ReportsTab.tsx     # Reports & Export
│       │       └── ReviewTab.tsx      # Review Queue
│       │
│       └── 📁 utils/
│           ├── supabase.ts            # Supabase client
│           └── api.ts                 # API client (Bearer token)
│
├── 📁 supabase/                       # Supabase infrastructure
│   ├── config.toml                    # Supabase CLI config
│   │
│   └── 📁 migrations/                 # SQL migrations
│       ├── 20260703000000_initial_schema.sql
│       ├── 20260703000001_seed_rules_and_categories.sql
│       └── 20260704000000_create_storage_buckets.sql
│
├── 📁 src/                            # ML pipeline (from Phase 0)
│   ├── parse.py                       # CSV parsing (Alipay/WeChat)
│   ├── segment.py                     # Tokenization + TF-IDF
│   ├── classify.py                    # Classification + routing
│   ├── semantic.py                    # Embeddings (Model2Vec)
│   ├── retrain.py                     # Training pipeline
│   ├── calibration.py                 # Confidence calibration
│   ├── eval_grouped.py                # Evaluation + threshold
│   ├── merchant_categories.py         # Rules + special logic
│   ├── feature_engineering.py         # Hybrid features
│   └── [+ 10 more utility modules]
│
├── 📁 tests/                          # Test suite
│   ├── test_parse.py                  # Parsing tests
│   ├── test_classify.py               # Classification tests
│   ├── test_semantic.py               # Semantic tests
│   ├── test_calibration.py            # Calibration tests
│   └── [+ 15 more test modules]
│
├── 📁 data/                           # Data directories (gitignored)
│   ├── raw/                           # Original exports
│   ├── processed/                     # Pipeline outputs
│   ├── labeled/                       # Training data
│   ├── intermediate/                  # Stage artifacts
│   ├── exports/                       # Excel review files
│   └── templates/                     # Starter configs
│
├── 📁 _archive/                       # Old experiments (gitignored)
│   └── [archived code & notes]
│
├── 📁 .claude/                        # Claude Code config
│   ├── settings.json                  # CLI settings
│   └── 📁 plans/                      # Implementation plans
│       └── serene-sprouting-muffin.md # 6-phase plan
│
└── 📁 .streamlit/                     # Streamlit config
    └── [legacy config]
```

---

## 🗂️ File Organization Logic

### **Root Level** (Critical files only)
- `README.md` — Entry point for users/developers
- `CLAUDE.md` — Collaboration guidelines
- `requirements.txt` — Standard Python convention
- Secrets (`.env.local`) — Gitignored

### **docs/** (All documentation)
- `PROJECT_SUMMARY.md` — 6-phase overview
- `SECURITY_AUDIT.md` — Security checklist
- `context.md` — Full project memory
- `CLEANUP_SUMMARY.md` — Documentation report
- Legacy audit files (Phase 0 ML work)

### **docs/guides/** (How-to guides)
- `DEPLOYMENT.md` — Production setup
- `MIGRATION_GUIDE.md` — Data migration
- `START_LOCAL.md` — Local development
- `TEST_LOCAL.md` — Testing procedures

### **scripts/** (Utility scripts)
- `run_all.py` — Full pipeline (legacy ML)
- `test_local.sh` — Test runner (legacy ML)

### **backend/** (FastAPI SaaS backend)
- 7 route groups (auth, categories, uploads, training, classify, dashboard, settings)
- Supabase integration
- Model training & inference
- One-time migration script

### **frontend/** (Next.js SaaS frontend)
- 6 dashboard tabs (Overview, Budget, Savings, Action, Reports, Review)
- Auth pages (signup, login, email verification)
- Settings page (profile, account deletion)
- Supabase SSR integration

### **supabase/** (Database infrastructure)
- 3 migrations (schema, seed, storage)
- RLS policies
- Triggers & functions

### **src/** (ML pipeline - Phase 0)
- Parsing, vectorization, classification
- Semantic embeddings
- Training & evaluation
- Merchant rules & special logic

### **tests/** (ML test suite - Phase 0)
- Parse, classify, semantic tests
- Calibration, evaluation tests
- 45+ test cases

### **data/** (User data - gitignored)
- Raw exports
- Processed outputs
- Training labels
- Intermediate artifacts

---

## 📊 Statistics

| Component | Files | Purpose |
|-----------|-------|---------|
| **Frontend** | 15+ | Next.js SaaS UI (6 tabs) |
| **Backend** | 10+ | FastAPI routes (7 groups) |
| **Database** | 3 | Supabase migrations + RLS |
| **ML Pipeline** | 20+ | Classification, training, evaluation |
| **Tests** | 45+ | Test suite |
| **Documentation** | 12 | Guides + reports |
| **Scripts** | 2 | Utility runners |

---

## 🎯 How to Navigate

**First time here?**
1. Start with `README.md`
2. See `docs/PROJECT_SUMMARY.md` for architecture
3. Follow `docs/guides/START_LOCAL.md` for setup

**Need to deploy?**
1. Read `docs/guides/DEPLOYMENT.md`
2. Check `docs/SECURITY_AUDIT.md`
3. Follow step-by-step instructions

**Need to migrate data?**
1. See `docs/guides/MIGRATION_GUIDE.md`
2. Run `backend/migrate_personal_data.py`

**Building/testing locally?**
1. See `docs/guides/START_LOCAL.md`
2. Run `python scripts/run_all.py`
3. Check `docs/guides/TEST_LOCAL.md`

---

## 🔍 Key Directories

| Path | Contains |
|------|----------|
| `/` | Entry points (README, CLAUDE, requirements) |
| `backend/` | FastAPI SaaS backend |
| `frontend/` | Next.js SaaS frontend |
| `docs/` | All documentation |
| `docs/guides/` | Setup & deployment guides |
| `scripts/` | Utility scripts |
| `src/` | ML pipeline (Phase 0) |
| `supabase/` | Database migrations |
| `data/` | User data (gitignored) |

---

**Last Updated**: 2026-07-06 (Post-Phase 6 reorganization)  
**Commit**: `0888f08` — Reorganize repository structure
