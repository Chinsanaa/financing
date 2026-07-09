# Backend — FastAPI (Railway)

Multi-tenant API for the transaction classifier. Validates Supabase JWTs,
scopes every query by `user_id`, and drives the ML pipeline in `../src/`.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env    # SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
python -m uvicorn main:app --reload    # http://localhost:8000, docs at /docs
```

## Layout

| File | Purpose |
|---|---|
| `main.py` | App, auth middleware (JWT → `request.state.user_id`), CORS, rate limiting |
| `auth_utils.py` | Verifies Supabase JWTs' ES256 signature against the project's JWKS |
| `config.py` | Env settings + the shared service-role Supabase client |
| `ml.py` | Loads the user's latest trained model from Storage (cached) and bulk-classifies pending transactions |
| `errors.py` | Log-and-mask helper so 500s never leak internals |
| `routes/` | Route groups (below) |
| `tests/` | JWT verification + cross-user isolation tests (`pip install -r requirements-dev.txt && pytest tests/`) |

## Endpoints

All routes except `/health`, `/`, docs, and `/auth/signup|login|refresh`
require `Authorization: Bearer <supabase access token>`.

**Auth** (`/auth`) — rate-limited per IP
- `POST /auth/signup` (5/hour), `POST /auth/login` (10/15min)
- `POST /auth/logout` (stateless ack; the client discards its tokens)
- `POST /auth/refresh` (handled client-side by the Supabase SDK)

**Categories** (`/categories`)
- `GET /` · `POST /` (`{name, sort_order?}`) · `PUT /{id}` · `DELETE /{id}`
  (a DB trigger reassigns the deleted category's transactions to the user's catch-all)

**Uploads** (`/uploads`)
- `POST /` — multipart CSV/XLSX (Alipay or WeChat), validates extension /
  10MB / 50k rows / header sniffing, stores the original in the `uploads`
  bucket under `{user_id}/…`, inserts parsed transactions, then classifies
  them in the background
- `GET /{upload_id}` · `GET /`

**Training** (`/training`)
- `POST /retrain` — trains TF-IDF + semantic models on the user's manually
  labeled transactions in a threadpool background task, uploads artifacts to
  the `model_artifacts` bucket at `{user_id}/models/{run_id}/`, then
  re-classifies unlabeled rows with the new model
- `GET /{model_run_id}` (poll status: queued/running/succeeded/failed) · `GET /`

**Classify** (`/classify`) — single-transaction review actions
- `POST /{transaction_id}/label` — `{category_id, label_source?}`; marks manually labeled
- `POST /{transaction_id}/accept` — accept the model's suggestion

Bulk classification is not an endpoint: it runs automatically after uploads
and training runs (see `ml.py`).

**Dashboard** (`/dashboard`)
- `GET /summary` · `/by-category` · `/trends?days=N` · `/budget` · `/savings`
  · `/action` · `/reports?page=N&per_page=M` · `/review-queue`
- `GET /onboarding-status` · `POST /onboarding-complete`

**Settings** (`/settings`)
- `GET/PATCH /profile` (monthly income)
- `DELETE /account` — recursively deletes the user's Storage folders in both
  buckets, then deletes the auth user (FK `ON DELETE CASCADE` removes all rows)

## Tenant isolation model

The backend uses the **service-role key**, which bypasses RLS — isolation is
enforced by (1) the JWT middleware (verifies signature, `aud`, `sub`, `exp`)
and (2) an explicit `.eq("user_id", user_id)` filter in every query. RLS
policies remain in place as defense-in-depth for any anon-key access path.

## Deployment (Railway)

Config-as-code via `railway.json` (note the `sh -c "uvicorn … --port $PORT"`
wrapper — Railway does not shell-expand `startCommand` itself). `Procfile` and
`Dockerfile` mirror it. See `../docs/guides/DEPLOYMENT.md`.
