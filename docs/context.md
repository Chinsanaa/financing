# context.md: Project Memory

Read this at the start of every session. Update it once at the end of a
session or PR. Keep it under about 200 lines: when a session entry is no
longer "recent", move it to `docs/archive/SESSION_LOG.md`.

Full history (Sessions 1 to 77, every decision record): `docs/archive/SESSION_LOG.md`.
Read the archive only when you need the reasoning behind an old decision.

---

## The problem and the goal

Spending in China is split across Alipay and WeChat Pay. Neither gives a
combined view, and hand-categorizing exported statements is too slow.

The product: upload Alipay / WeChat exports, have each transaction
categorized automatically, see spending by category, time and merchant, and
have the categorizer improve as the user labels more.

## Why classification, not clustering

We know the target categories in advance, so this is **supervised text
classification** (merchant/description text to category). Clustering is only a
bootstrap aid for discovering patterns in unlabeled rows.

## Current state (Session 78, 2026-11-13)

| Area | State |
|---|---|
| Stack | Next.js 14 (`frontend/`, Vercel) + FastAPI (`backend/`, Render) + Supabase (Postgres, Auth, Storage). The only UI. |
| Auth | Supabase Auth in the browser; backend verifies the ES256 JWT against Supabase JWKS (`backend/auth_utils.py`). Username or email sign-in, password rules, forgot-password. |
| Parsing | `src/parse.py`: Alipay + WeChat (CSV/XLSX, Chinese and English headers) normalized to one schema. Income rows and internal transfers handled by `kind`. |
| Categories | 13 ML categories in `src/categories.py::ML_CATEGORIES`. Each maps to a Need / Want / Savings bucket (`CATEGORY_BUCKET`). User-selectable colors (12 palette keys, no purple). |
| Classification order | 1) merchant rules (global seeds + per-user rows in `merchant_rules`), 2) description keywords (only when no rule matched), 3) per-user model, 4) LLM fallback suggestion (Groq, `src/llm_classify.py`, needs `GROQ_API_KEY`, no-ops without it). |
| Model | TF-IDF (jieba-segmented) + numeric features, Logistic Regression, plus a semantic classifier (Model2Vec, LSA fallback on the server). Trained per user via `POST /training/retrain`; artifacts in Storage at `{user_id}/models/{run_id}/`. |
| Trust | Auto-apply only on calibrated two-model agreement above a data-derived threshold. Everything else goes to the review queue. |
| Dashboard | Overview, cash flow, budgets (per month), 50/30/20, savings, action plan, notifications (persisted, read/clear), insights, reports (search, filters, bulk label, splits, CSV + XLSX export), subscriptions, multi-currency (FX). |
| Onboarding | `OnboardingTour` + `TourSpotlight`, once per signup. |
| Design | "Ledger" v5. THE RULE: solid colors only (see `docs/DESIGN_SYSTEM.md`). Enforced by `scripts/design_gate.sh` in CI. |
| Tests | `pytest tests` (ML pipeline) and `pytest` in `backend/`. Frontend: typecheck, lint, build, design gate. All run in CI (`.github/workflows/ci.yml`). Counts are recorded in the latest session entry below. |

## Key decisions still in force

| Decision | Choice | Why |
|---|---|---|
| Model family | Logistic Regression on TF-IDF first | Simple, interpretable, enough for about 1k samples |
| Chinese text | `jieba` segmentation before TF-IDF | An English tokenizer cannot split Chinese |
| Refunds | Kept, netted as a negative amount in the same category | Purchase plus refund should cancel, not vanish |
| Internal transfers | Excluded from spend | Not real spending; would double count |
| Peer-to-peer transfers / red packets | Left as expense | Ambiguous; could be a real gift |
| Auto-apply threshold | Derived from grouped CV (target precision 90%, min support 30); none saved if unreachable | Never invent a trust boundary |
| Rules vs keywords | Merchant rules win; keywords only label unmatched rows; English keywords must start a word | "rent" used to fire on "current" (Session 77) |
| Numeric features | Fitted at training and saved with the model | Per-batch stats made one transaction look different depending on its batch (Session 77) |
| Uploads | Sequential, never concurrent | Dedup reads then writes with no unique index behind it |
| Notifications | Persisted table with read / cleared state | Users asked for real unread tracking and clear-all (Session 56) |
| `src.` vs bare imports | Leave as is | Saved model pickles depend on current module paths |
| Storage writes | Service-role backend only (Session 78) | Client write policies allowed planting a pickle the server would load |

## Key terms

- **Tokenization:** splitting text into words (`jieba` for Chinese).
- **TF-IDF:** turns text into numbers; distinctive merchant tokens score high.
- **Classifier:** learns text to category from labeled examples.
- **Calibration:** adjusting model confidence so "90% sure" is right about 90% of the time.

## Open items (need a user decision)

- **Personal data in git history.** Removed from the working tree in Session 19 but recoverable from history. Needs a history rewrite and force-push.
- **Apply migration `20261113000000_lock_storage_writes.sql`** to the live database (Session 78).
- **Rate limiting behind Render's proxy:** limits may be shared across users. Needs a check of Render settings.
- **CORS regex** accepts any Vercel project named `financing-*`; username lookup discloses emails by design.
- **Dead schema:** `profiles.onboarding_phase`, `onboarding_iteration`, `email_verified_at`, `budget_config.income`, `saving_goal_annual`, table `special_rules`. Not dropped.
- **Upgrades:** `@supabase/ssr` 0.0.10, scikit-learn.
- **NYU Shanghai / Shanghai Ruisheng special cases** in the rules: removing them changes classifications.
- **`ponytail` plugin** in `.claude/settings.json`: confirm it is still wanted.
- **Leaked Password Protection** is off in the Supabase dashboard (dashboard-only setting).

## Recent sessions

### Session 78 (2026-11-13): Full audit and optimization (PR #68)

Manager-style audit with cheaper subagents doing scoped tasks. Checks at the
end: 158 pipeline tests, 276 backend tests, frontend typecheck + lint + build,
design gate, all passing.

**Security and bugs**
- New migration `20261113000000_lock_storage_writes.sql` drops client
  INSERT/DELETE storage policies. Why: the backend loads model files with
  joblib (pickle), so a user who could write to their own folder could plant a
  file the server would run. **Not yet applied to the live database.**
- Training: generic error text to clients, own DB client in the worker thread,
  409 if a run is already in progress (runs stale for 30+ minutes do not block).
- CSV export neutralizes cells starting with `= + - @` (spreadsheet formulas).
- `/docs` and `/openapi.json` are hidden when `ENVIRONMENT=production`.
- Reports: stricter search sanitizing; invalid date filters return 422.
- Blocking calls moved off the event loop (auth lookup, account deletion).

**Performance**
- Classification writes are grouped by identical payload: a few UPDATEs per
  pass instead of one per transaction (`backend/ml.py`).
- Bulk label: 6 queries for 50 ids instead of about 200.
- Landing page is a server component; first-load JS 143 kB to 137 kB.

**Structure and cleanup**
- `backend/routes/dashboard.py` (1,600 lines) is now the package
  `backend/routes/dashboard/` (pure move).
- `ReportsTab.tsx` 1,074 to 710 lines; pieces live in `components/tabs/reports/`.
- One shared `Category` type; dead exports removed; ESLint works and runs in CI.
- Backend dependencies pinned; `model2vec` no longer installed on the server.
- Docs: this file slimmed (history in the archive), CLAUDE.md shortened,
  duplicated tree and rule text removed, two conflicting design skills removed,
  `.claude/agents/cleanup-worker.md` added.

**Decided not to do (and why)**
- Parser dedup in `src/parse.py`: the merged version was longer and needed a
  flag parameter. Reverted.
- Global exception handler: FastAPI returns catch-all 500s outside the CORS
  layer, so browsers would see a network error. Per-route wrappers stay.
- Removing the dashboard session gate: saves milliseconds, risks tabs firing
  requests without a session.
- Deleting `GET /uploads/{id}`: unused by the frontend but listed in the frozen
  API contract.
- Upload size guard caveat: FastAPI parses the body before the handler, so the
  10 MB cap limits handler memory, not network intake.

### Session 77 (2026-10-17): Codebase cleanup (PR #67, merged)

Backend hardening (removed shared-client auth routes, FastAPI upgrade, paged
rule and training fetches), rules beat keywords, numeric features fitted at
training, dead code and CLI code removed, helpers deduplicated, frontend 401
loop fixed, CI workflow added. Details in the archive.

## Next suggested step

Review and merge PR #68, apply the storage migration, then press **Train**
once so the model saves the Session 77 fitted numeric stats (if not done yet).
