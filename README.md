# Financing — Multi-Tenant Transaction Classifier

A full-stack app that categorizes personal spending from Alipay/WeChat exports:
drop up to 10 CSV/Excel statements at once (they upload one at a time, each
reporting its own result — a re-upload of a file you already imported is
skipped, not failed) → transactions are auto-categorized (trusted merchant
rules first, ML suggestions for the rest) → review the leftovers → dashboards
show where the money went.

## Architecture

```
User Browser (Next.js on Vercel)
    ↓ Supabase Auth (email/password, sign-in via email or username) → JWT in Authorization header
FastAPI Backend (Render)
    ↓ service-role key + explicit user_id scoping on every query
Supabase PostgreSQL + Auth + Storage
    ↓ RLS policies as defense-in-depth per-user isolation
```

- **Frontend**: Next.js 14 (TypeScript, App Router) + Tailwind CSS — `frontend/`
- **Backend**: FastAPI + supabase-py — `backend/`
- **ML pipeline**: scikit-learn (TF-IDF + Logistic Regression, optional
  semantic-embedding second model with calibrated agreement) — `src/`
- **Database**: PostgreSQL, 12 tables, RLS enabled on all — `supabase/migrations/`

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
4. **LLM fallback** (`label_source='llm'`, `src/llm_classify.py`): rows still
   unclassified after rules + model (no rule hit, no trained model yet — the
   common case for a new account or merchant vocabulary the hardcoded rules
   were never written for) get one more, batched call to Groq's free-tier
   inference API (an open model, no cost) using the user's *current*
   category names, so it's immune to category renames. Always a
   review-queue suggestion, never auto-applied. Requires `GROQ_API_KEY`
   (free at [console.groq.com](https://console.groq.com)); skipped entirely
   if unset. Renaming a category (`PUT /categories/{id}`) also updates any
   of that user's existing `merchant_rules`/`special_rules` pointing at the
   old name, so pre-existing rules survive the rename too.

**Rule generalization ("unique merchants only")**: labeling or accepting
*any* transaction in the review queue — LLM suggestion or not — writes back
a new per-user `merchant_rules` row, so the next transaction from that
merchant hits the fast rule path instead of needing review again. It also
immediately resolves every other pending transaction from that same
merchant right then, so a merchant with several un-labeled rows clears
from the queue in one action instead of resurfacing per-row.
`DESCRIPTION_KEYWORD_RULES` (`src/merchant_categories.py`) also classifies
by description keywords for unseen merchants, e.g. Shanghai Metro station
names (Houtan, Jing'an Temple, Lujiazui, Hongqiao, Pudong, and others) →
Transportation.

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
(Budget / 50/30/20 / Savings / Subscriptions / Insights / Action plan), and **Reports**. A dismissible
bottom-right onboarding guide (Upload → Categories → Label → Train) walks new
accounts through each step, spotlighting the specific button to press next
with a dimmed backdrop and an arrow. Plus a
separate **Settings** page (data export, password change, legal links,
account deletion). The UI is a dark-first design with a light theme toggle,
skeleton loading states, and a marketing landing page at `/` for signed-out
visitors, with `/privacy` and `/terms` legal pages linked from its footer.

**Sign-up/sign-in**: signup requires a unique username (checked live against
the database as you type) alongside email, a password meeting a live
checklist (9+ chars, upper/lower/digit/special), and agreeing to the Terms &
Conditions / Privacy Policy. Sign-in accepts either email or username. A
"Forgot password?" link sends a reset email; the link lands on `/auth/verify`
with a "set a new password" form instead of the usual auto-redirect. Every
password field has a show/hide toggle and confirm-password fields show a
live "passwords do not match" message. Sign-in has a client-side soft
lockout (escalating cooldown) after 5 failed attempts in a row, on top of
Supabase Auth's own project-level rate limits.

**Correcting categories**: the **Reports → All transactions** table is editable —
click any category (including uncategorized rows) to reassign it; the change is
saved immediately and flows through to the Overview and Budget views. A
"Filters" button toggles a panel with search (merchant/description), date
range, amount range, sort (by date or category), rows-per-page (10/20/50/100),
and a Need/Want/Savings bucket filter, all combinable; pagination has
first/previous/page-number/next/last controls. Each row also shows a
Need/Want/Savings badge (blank for split or uncategorized rows) using the
same static category-bucket mapping as the 50/30/20 rule. Select multiple
rows with the checkbox column to
re-categorize them all at once via the bulk action bar. **Split
transactions**: any transaction can be split across multiple categories
(e.g. a Costco run: groceries + household) via the "Split" action next to
its category — amounts must sum to the transaction's total. A split
transaction shows a "Split (n)" badge instead of a single category and its
per-category amounts are counted separately everywhere spend is
aggregated (Budget, Action items, Insights, by-category totals); a split
can be removed at any time, which sends the transaction back to the
review queue uncategorized. **Per-month
budgets**: the **Budget** tab has a month selector so you can see how each past
month tracked against your budget (budgets are global, so past months compare
against your current budget). Below the category list, the same month's
50/30/20 breakdown (donut chart, actual-vs-target per bucket, guidance card —
see below) is shown for context, hidden while the budget edit form is open.
**Category colors**: pick a color per category in
**Model → Categories** (12 design-system choices, hex shown, no duplicates) — the
same color follows that category everywhere: the Overview pie chart, badges in
Budget/Review/Label, and Reports. Categories without a chosen color get a stable
automatic color. The dashboard layout is fluid — it fills large desktop screens
(capped for ultrawides) and adapts down to tablet and phone.

**50/30/20 rule**: the **Planning → 50/30/20** tab buckets each of the 13
categories into Needs / Wants / Savings & Investing and compares the
month's actual split (donut chart) against the 50/30/20 targets derived
from your monthly income, plus a short rule-based guidance card (e.g.
trim the largest "want" if savings are short). Savings counts both money
spent in the Investments category and unspent income for the month.

**Subscriptions**: the **Planning → Subscriptions** tab auto-detects recurring
merchants (≥3 charges in the trailing 6 months at a monthly or weekly cadence,
with a stable amount) and shows an estimated monthly total. Each detected
merchant can be confirmed or dismissed; dismissals persist across future
re-detection runs. Detection logic lives in `src/recurring.py` (pure pandas,
no DB access); `backend/routes/subscriptions.py` fetches transactions, runs
detection, and upserts into the `recurring_merchants` cache table.

**Notifications**: the header's notification bell is a real notification
inbox — over-budget/approaching-budget crossings, a one-time welcome
message for new accounts, and a note when a model finishes training, all
persisted in a `notifications` table with real read/unread tracking. The
badge shows the unread count (hidden at 0); opening the dropdown marks
everything read; a "Clear notifications" button removes them from the list
for good — a cleared notification only reappears if a genuinely new event
happens. This is separate from **Planning → Action plan**, which stays a
live current-state view (over-budget/approaching-budget/pending-review,
recomputed on every load, no history) — the two don't share data.
**Settings → Notification preferences** has three categories: Budget
alerts (in-app + email, with a configurable "approaching budget" threshold,
default 80%), Pending review reminders (in-app only, Action-plan-only —
not part of the bell), and Monthly spending overview (email only — a
settings toggle today, sending isn't built yet).
Budget alert emails are de-duplicated per category/month so the same
crossing is never sent twice, and are checked reactively (when you upload,
review, or label a transaction), not on a schedule, since no background
scheduler exists yet.

**Insights**: **Planning → Insights** compares each category's current-month
spend to its trailing 3-month average (flagging notable swings either way)
and lists individual transactions whose amount is unusually large for their
category (more than 2 standard deviations above that category's mean,
skipped for categories with too little history to judge). Both are computed
fresh on every load — nothing is persisted.

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
(manual test flows), `docs/guides/DEPLOYMENT.md` (Render + Vercel + Supabase).

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/            # ML pipeline: parsing, routing, calibration, leakage guard

cd backend && pip install -r requirements-dev.txt
pytest tests/             # backend: JWT verification, cross-user isolation
```

There is no automated frontend test suite yet (open item); frontend is
verified with `npx tsc --noEmit && npm run build`.

## Repo layout

```
financing/
├── frontend/            # Next.js app (see frontend/README.md)
├── backend/             # FastAPI app (see backend/README.md)
│   ├── routes/          # auth, categories, uploads, training, classify, dashboard, settings, subscriptions
│   ├── auth_utils.py    # JWT verification against Supabase's JWKS
│   ├── tests/           # JWT verification + cross-user isolation tests
│   └── ml.py            # per-user model loading + bulk classification
├── src/                 # ML pipeline shared by backend + tests
│   ├── parse.py         # Alipay/WeChat parsers → common schema
│   ├── segment.py       # jieba tokenization + TF-IDF
│   ├── classify.py      # rules-first + graduated-trust routing
│   ├── retrain.py       # training entry point (both models + calibration)
│   ├── semantic.py      # embedding classifier (Model2Vec / LSA fallback)
│   ├── calibration.py   # top-label Platt scaling
│   ├── eval_grouped.py  # GroupKFold evaluation + threshold derivation
│   ├── merchant_categories.py  # global rule patterns
│   ├── llm_classify.py  # LLM fallback classifier (batched, DB-free)
│   └── recurring.py     # recurring/subscription merchant detection (pure pandas, DB-free)
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
- Real Postgres RLS policies are never exercised through the API (the backend
  always uses the service-role key, which bypasses RLS) — only route-level
  `user_id` scoping is tested today (`backend/tests/`). Testing RLS directly
  would need a local/CLI Supabase stack hit with an anon key + real user JWT.

## License

MIT
