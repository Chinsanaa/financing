# Financing — Multi-Tenant Transaction Classifier

A full-stack app that categorizes personal spending from Alipay/WeChat exports:
upload a CSV/Excel export → transactions are auto-categorized (trusted merchant
rules first, ML suggestions for the rest) → review the leftovers → dashboards
show where the money went.

## Architecture

```
User Browser (Next.js on Vercel)
    ↓ Supabase Auth (email/password) → JWT in Authorization header
FastAPI Backend (Railway)
    ↓ service-role key + explicit user_id scoping on every query
Supabase PostgreSQL + Auth + Storage
    ↓ RLS policies as defense-in-depth per-user isolation
```

- **Frontend**: Next.js 14 (TypeScript, App Router) + Tailwind CSS — `frontend/`
- **Backend**: FastAPI + supabase-py — `backend/`
- **ML pipeline**: scikit-learn (TF-IDF + Logistic Regression, optional
  semantic-embedding second model with calibrated agreement) — `src/`
- **Database**: PostgreSQL, 9 tables, RLS enabled on all — `supabase/migrations/`

## How classification works

1. **Merchant rules** (554 global seeds + per-user rules in `merchant_rules`)
   are trusted: matching transactions get their category immediately
   (`label_source='rule'`, no review needed).
2. **The user's trained model** suggests categories for everything else
   (`label_source='model'`) — suggestions land in the Review Queue with a
   calibrated confidence.
3. **Graduated trust**: a model prediction auto-applies without review
   (`label_source='model_agreed'`) only when the TF-IDF and semantic models
   agree, their calibrated confidence clears a data-derived threshold, and the
   prediction isn't the catch-all. See `docs/FULL_AUDIT.md` for why raw model
   confidence can't be trusted on unseen merchants.

Classification runs automatically after every upload (rules-only until a model
is trained) and re-runs after every training run (`backend/ml.py`).

### How accuracy is measured (honest numbers)

Two very different questions:
- **Stratified CV** (known merchants): ~95% accuracy — but mostly memorization.
- **GroupKFold by merchant** (unseen merchants): far lower — this is the number
  that matters for new data, and why model output defaults to review instead of
  auto-applying. Details: `docs/FULL_AUDIT.md`.

## Dashboard sections (5)

The ten original tabs are grouped into five compact sections with sub-tabs:
**Overview** (a monthly-spending line chart + category split), **Transactions**
(Upload / Label / Review queue), **Model** (Categories / Training), **Planning**
(Budget / Savings / Action plan), and **Reports**. A dismissible onboarding
checklist (Upload → Categories → Label → Train) guides new accounts. Plus a
separate **Settings** page (income, account deletion). The UI is a dark-first
design with a light theme toggle, skeleton loading states, and a marketing
landing page at `/` for signed-out visitors.

**Correcting categories**: the **Reports → All transactions** table is editable —
click any category (including uncategorized rows) to reassign it; the change is
saved immediately and flows through to the Overview and Budget views. **Per-month
budgets**: the **Budget** tab has a month selector so you can see how each past
month tracked against your budget (budgets are global, so past months compare
against your current budget).

## Quick start (local)

```bash
# 1. Backend
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in your Supabase project's URL/keys/JWT secret
python -m uvicorn main:app --reload   # http://localhost:8000

# 2. Frontend (new terminal)
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_SUPABASE_URL/_ANON_KEY, NEXT_PUBLIC_API_URL
npm run dev                  # http://localhost:3000
```

Guides: `docs/guides/START_LOCAL.md` (setup), `docs/guides/TEST_LOCAL.md`
(manual test flows), `docs/guides/DEPLOYMENT.md` (Railway + Vercel + Supabase).

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/            # ML pipeline: parsing, routing, calibration, leakage guard
```

There is no automated backend/frontend test suite yet (open item); frontend is
verified with `npx tsc --noEmit && npm run build`.

## Repo layout

```
financing/
├── frontend/            # Next.js app (see frontend/README.md)
├── backend/             # FastAPI app (see backend/README.md)
│   ├── routes/          # auth, categories, uploads, training, classify, dashboard, settings
│   └── ml.py            # per-user model loading + bulk classification
├── src/                 # ML pipeline shared by backend + tests
│   ├── parse.py         # Alipay/WeChat parsers → common schema
│   ├── segment.py       # jieba tokenization + TF-IDF
│   ├── classify.py      # rules-first + graduated-trust routing
│   ├── retrain.py       # training entry point (both models + calibration)
│   ├── semantic.py      # embedding classifier (Model2Vec / LSA fallback)
│   ├── calibration.py   # top-label Platt scaling
│   ├── eval_grouped.py  # GroupKFold evaluation + threshold derivation
│   └── merchant_categories.py  # global rule patterns
├── supabase/            # migrations (schema, RLS, storage buckets, fixes)
├── tests/               # pytest suite for src/
├── scripts/test_local.sh
├── docs/                # context.md (project memory), audits, guides
└── data/                # gitignored user data + example templates
```

Full tree with explanations: `REPO_STRUCTURE.md`.

## Documentation

| Document | Purpose |
|---|---|
| `docs/context.md` | Project memory: every session, decision, and open item |
| `docs/PROJECT_SUMMARY.md` | Architecture overview and phase history |
| `docs/SECURITY_AUDIT.md` | Security checklist + test specifications |
| `docs/FULL_AUDIT.md` | ML integrity audit (merchant leakage, honest evaluation) |
| `docs/guides/` | START_LOCAL, TEST_LOCAL, DEPLOYMENT, MIGRATION_GUIDE |
| `CLAUDE.md` | Collaboration guidelines for AI-assisted sessions |

## Known open items

- Old personal data is still recoverable from **git history** (pre-Session-19
  commits); purging requires a `git filter-repo` rewrite + force-push.
- Training runs in the backend threadpool — fine at small scale, should move
  to a real worker queue if user count grows.
- No backend integration test suite (RLS violation / JWT tampering tests are
  specified in `docs/SECURITY_AUDIT.md` but not implemented).

## License

MIT
