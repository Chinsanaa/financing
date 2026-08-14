# Deployment Guide — Financing SaaS

End-to-end deployment for multi-tenant transaction classification system.

## Architecture Overview

```
User Browser
  ↓
Vercel (Next.js Frontend, Port 443)
  ↓ [JWT in Authorization header]
Render (FastAPI Backend, Docker, Port 8000)
  ↓ [Service Role Key]
Supabase (PostgreSQL + Auth + Storage, Singapore)
```

## Prerequisites

- [ ] Supabase project created (Phase 1, already done)
- [ ] Render account (https://render.com) — free tier available
- [ ] Vercel account (https://vercel.com) — free tier available
- [ ] GitHub account with repo linked

## Part 1: Supabase Setup (Already Done)

Schema and RLS policies are in place — the full migration history lives in
`supabase/migrations/`. Don't hand-maintain a list of "applied" migrations
in this doc (it goes stale fast); instead check what's actually pending
before any deploy:

```bash
supabase migration list   # or the Supabase MCP `list_migrations` tool
```

Apply any not-yet-applied migrations with `supabase db push` (or the
Supabase MCP `apply_migration` tool) before deploying backend changes that
rely on them — a migration and the backend code that depends on its schema
should land together, not backend-first.

Verify buckets exist:
```bash
supabase projects list
supabase storage ls
```

Get credentials from Supabase dashboard:
- Project URL: `https://[PROJECT_ID].supabase.co`
- Anon Key: Settings → API → anon/public key (public, safe for frontend)
- Service Role Key: Settings → API → Service role key (secret, backend only)
- JWT Secret: Settings → API → JWT secret (for token verification)

---

## Part 2: Deploy FastAPI Backend to Render

The backend is a Docker web service on Render, building from
`backend/Dockerfile`. The live service for this repo is named **`financing`**
(dashboard: `https://dashboard.render.com/web/srv-d9sn3ov40ujc73di29ag`,
region Singapore, free plan, auto-deploys on every push to `main`).

### Step 2.1: Push Code to GitHub

```bash
git push origin main
```

Render's `financing` service has `autoDeploy: yes` on `main` — a push there
triggers a build automatically. No manual deploy step needed for routine
changes.

### Step 2.2: Connect Render to GitHub Repo (first-time setup only)

1. Go to https://dashboard.render.com
2. Click **New** → **Web Service**
3. Connect and select your repo (`Chinsanaa/financing`)
4. Runtime: **Docker**, Dockerfile path: `backend/Dockerfile`, Docker
   context: `.` (repo root — the Dockerfile needs both `backend/` and
   `src/`)
5. Branch: `main`
6. Region: choose one close to your Supabase project (this deployment uses
   Singapore, matching Supabase's region)
7. Click **Create Web Service**

### Step 2.3: Set Environment Variables on Render

In the service's **Environment** tab, add:

```
SUPABASE_URL=https://[PROJECT_ID].supabase.co
SUPABASE_ANON_KEY=[your_anon_key]
SUPABASE_SERVICE_ROLE_KEY=[your_service_role_key_secret!]
ENVIRONMENT=production
RESEND_API_KEY=[your_resend_key]   # optional — enables budget-alert emails; unset = no-op
GROQ_API_KEY=[your_groq_key]       # optional — enables LLM fallback classification; unset = skipped
```

**IMPORTANT**: These are all secrets except nothing here is public — never
commit any of them to Git. Render env vars live only in Render's dashboard
and the running container; saving them triggers an automatic redeploy.

### Step 2.4: Verify Backend is Running

1. Wait for the build to complete (a Docker build typically takes a few
   minutes)
2. In the Render dashboard: **Logs** tab
3. Should see: `Uvicorn running on 0.0.0.0:8000` (or whatever `$PORT`
   Render assigned — the Dockerfile's `CMD`/`ENTRYPOINT` should read
   `$PORT`, not hardcode 8000)
4. Hit the service URL to test:
   - `https://[render-url]/health` should return `{"status": "ok"}`
   - `https://[render-url]/docs` should show Swagger UI

**Save the Render backend URL** (e.g. `https://financing-lxgt.onrender.com`
for this project): you'll need it for the frontend.

---

## Part 3: Deploy Next.js Frontend to Vercel

### Step 3.1: Create Vercel Project

1. Go to https://vercel.com/dashboard
2. Click **Add New** → **Project**
3. Import repo: select `Chinsanaa/financing`
4. **IMPORTANT**: When prompted for "Root Directory", set it to `frontend/` (this is where `package.json` is located)
5. Framework preset: **Next.js** (auto-detected)
6. Click **Deploy**

Vercel will automatically detect Next.js in the `frontend/` directory and build/deploy.

**If you skip Step 4**: After importing, go to project **Settings** → **General** → **Root Directory** and set to `frontend/`, then redeploy.

### Step 3.2: Set Environment Variables

In Vercel project settings, go to **Environment Variables**:

```
NEXT_PUBLIC_SUPABASE_URL=https://[PROJECT_ID].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[your_anon_key]
NEXT_PUBLIC_API_URL=https://[render-url]  # No trailing slash
```

**IMPORTANT**: `NEXT_PUBLIC_*` variables are exposed to the browser (intended).
Supabase anon key is public (RLS policies enforce access control).

### Step 3.3: Redeploy After Env Changes

In Vercel, go to **Deployments** → **Redeploy** on the latest build.

### Step 3.4: Verify Frontend is Running

1. Visit your Vercel URL: `https://[vercel-url].vercel.app`
2. Should redirect to `/auth`
3. Test signup: create a test account
4. Check Supabase dashboard → Auth → Users (user should appear)

**Save the Vercel frontend URL**: Share with users.

---

## Part 4: Wire Frontend to Backend

### Step 4.1: Test API Connectivity

In frontend **Upload** tab:
1. Login with test account
2. Upload a sample CSV file (Alipay or WeChat format)
3. Should parse and show: "Uploaded X transactions"

If error: check backend logs on Render (service dashboard → **Logs**).

### Step 4.2: Test Training Pipeline

In frontend **Training** tab:
1. Label a few transactions in the **Label** tab first
2. Click **Start Training**
3. Should show "Training in progress"
4. Training status updates every 5 seconds
5. When complete, shows accuracy + F1-macro

If error: check backend logs. Common issues:
- `src/` not in Python path → ensure `sys.path.insert(0)` in routes
- Model artifacts failing to upload → check Supabase Storage bucket exists

---

## Part 5: Post-Deployment Checklist

- [ ] Backend health check passes: `/health` returns `{"status": "ok"}`
- [ ] Frontend loads without 404s
- [ ] Signup → email verification flow works
- [ ] Login stores JWT token (check browser DevTools → Application → Cookies)
- [ ] Upload CSV → transactions inserted in Supabase
- [ ] Label transactions → marked as `labeled=True`
- [ ] Training → calls `retrain_model()`, uploads artifacts to Storage
- [ ] Dashboard stats show correct totals
- [ ] Categories CRUD works
- [ ] Review queue displays pending transactions

---

## Troubleshooting

### "401 Unauthorized" on API calls
- **Cause**: JWT token missing, expired, or fails signature verification
- **Fix**: Check `Authorization` header in API requests (DevTools → Network)
- **Fix**: Confirm `SUPABASE_URL` is correct — the backend verifies tokens against
  that project's JWKS endpoint (`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`)

### "Failed to upload artifacts to Supabase Storage"
- **Cause**: Storage bucket doesn't exist or RLS policy incorrect
- **Fix**: Verify buckets exist: `supabase storage ls`
- **Fix**: Re-run migration: `supabase db push`

### "Cannot import src.retrain"
- **Cause**: Python path not set in FastAPI routes
- **Fix**: Add `sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))` to route files

### "CORS error: No 'Access-Control-Allow-Origin' header"
- **Cause**: Frontend and backend URLs don't match `CORS` config
- **Fix**: Update `CORSMiddleware` in `backend/main.py` with Vercel URL

### "Training still running after 1 hour"
- **Cause**: Background task crashed silently
- **Fix**: Check Render backend logs → look for exceptions in `run_training()`
- **Fix**: Ensure `src/retrain.py` imports work (`sys.path` set)

### Budget-alert emails never arrive / LLM fallback never fires
- **Cause**: `RESEND_API_KEY` / `GROQ_API_KEY` unset on Render — both features
  no-op silently when their key is missing (by design, so a missing optional
  key never breaks the request), so nothing errors, they just don't do
  anything.
- **Fix**: Set the relevant key in the Render service's **Environment** tab
  (see Part 2, Step 2.3) and confirm the automatic redeploy finished.

---

## Monitoring & Logs

### Render Backend Logs
1. Service dashboard → **Logs** tab
2. Search for errors: "Failed", "Error", "Exception"
3. Common patterns: missing env vars, import errors, API failures
4. **Metrics** tab has CPU/memory/request-count graphs if you need them

### Vercel Frontend Logs
1. Dashboard → **Deployments** → latest
2. Click **View Build Logs** or **Logs**
3. Check for build errors (TypeScript, module not found)
4. Runtime errors appear in **Function Logs**

### Supabase Logs
1. Dashboard → **Logs** → **API requests** / **Auth** / **Database**
2. Filter by user_id or endpoint to debug specific flows

---

## Scaling & Future Work

- **Database**: Supabase handles auto-scaling (PostgreSQL 17)
- **Backend**: Render's free plan spins down on inactivity (cold starts on
  the first request after idle) and has limited resources — fine for a
  personal project, worth moving to a paid plan before real user traffic
- **Frontend**: Vercel has built-in CDN and edge caching
- **Storage**: Supabase Storage backed by S3, unlimited capacity

For 10k+ monthly users:
- Monitor Supabase CPU/RAM (Settings → Usage)
- Consider a paid Render plan (no cold starts, more CPU/RAM) if hitting
  free-tier limits
- Add Redis cache for frequently accessed data (optional)

---

## Git Workflow

Main branch: `main` (stable releases)
Dev branches: feature branches merged into `main` via PRs

To deploy a new version:
```bash
git checkout main
git merge <feature-branch>
git push origin main
```

Render and Vercel will auto-redeploy on push to main.

---

## Contacts & Docs

- **Supabase**: https://supabase.io/docs
- **Render**: https://render.com/docs
- **Vercel**: https://vercel.com/docs
- **FastAPI**: https://fastapi.tiangolo.com
- **Next.js**: https://nextjs.org/docs

---

**Deployment Status**: Ready for production
**Last Updated**: 2026-08-14
