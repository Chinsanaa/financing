# Deployment Guide — Financing SaaS

End-to-end deployment for multi-tenant transaction classification system.

## Architecture Overview

```
User Browser
  ↓
Vercel (Next.js Frontend, Port 443)
  ↓ [JWT in Authorization header]
Railway (FastAPI Backend, Port 8000)
  ↓ [Service Role Key]
Supabase (PostgreSQL + Auth + Storage, Singapore)
```

## Prerequisites

- [ ] Supabase project created (Phase 1, already done)
- [ ] Railway account (https://railway.app) — free tier available
- [ ] Vercel account (https://vercel.com) — free tier available
- [ ] GitHub account with repo linked

## Part 1: Supabase Setup (Already Done)

Schema, migrations, and RLS policies are in place:
- `supabase/migrations/20260703000000_initial_schema.sql` ✓
- `supabase/migrations/20260703000001_seed_rules_and_categories.sql` ✓
- `supabase/migrations/20260704000000_create_storage_buckets.sql` ✓

Verify buckets exist:
```bash
supabase projects list
supabase storage ls
```

Get credentials from Supabase dashboard:
- Project URL: `https://[PROJECT_ID].supabase.co`
- Anon Key: Settings → API → Service role key (public, safe for frontend)
- Service Role Key: Settings → API → Service role key (secret, backend only)
- JWT Secret: Settings → API → JWT secret (for token verification)

---

## Part 2: Deploy FastAPI Backend to Railway

### Step 2.1: Push Code to GitHub

```bash
git push origin phase-1-supabase-foundation
```

### Step 2.2: Connect Railway to GitHub Repo

1. Go to https://railway.app/dashboard
2. Click **New Project** → **Deploy from GitHub**
3. Select your repo (`Chinsanaa/financing`)
4. Select branch: `phase-1-supabase-foundation`
5. Click **Deploy**

Railway will automatically detect the `Dockerfile` and build.

### Step 2.3: Set Environment Variables on Railway

In Railway dashboard, go to **Variables**:

```
SUPABASE_URL=https://[PROJECT_ID].supabase.co
SUPABASE_ANON_KEY=[your_anon_key]
SUPABASE_SERVICE_ROLE_KEY=[your_service_role_key_secret!]
SUPABASE_JWT_SECRET=[your_jwt_secret]
ENVIRONMENT=production
```

**IMPORTANT**: Service role key is a secret. Never commit to Git.

### Step 2.4: Verify Backend is Running

1. Wait for build to complete (3-5 minutes)
2. Click **Deployments** → latest → **View Logs**
3. Should see: `Uvicorn running on 0.0.0.0:8000`
4. Click the Railway domain URL to test:
   - `https://[railway-url]/health` should return `{"status": "ok"}`
   - `https://[railway-url]/docs` should show Swagger UI

**Save the Railway backend URL**: You'll need it for the frontend.

---

## Part 3: Deploy Next.js Frontend to Vercel

### Step 3.1: Create Vercel Project

1. Go to https://vercel.com/dashboard
2. Click **Add New** → **Project**
3. Import repo: select `financing` → `frontend` directory
4. Framework preset: **Next.js** (auto-detected)
5. Click **Deploy**

Vercel will automatically build and deploy.

### Step 3.2: Set Environment Variables

In Vercel project settings, go to **Environment Variables**:

```
NEXT_PUBLIC_SUPABASE_URL=https://[PROJECT_ID].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[your_anon_key]
NEXT_PUBLIC_API_URL=https://[railway-url]  # No trailing slash
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

If error: check backend logs on Railway (`Deployments` → `Logs`).

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
- **Cause**: JWT token missing or invalid
- **Fix**: Check `Authorization` header in API requests (DevTools → Network)
- **Fix**: Verify `SUPABASE_JWT_SECRET` matches Supabase dashboard

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
- **Fix**: Check Railway backend logs → look for exceptions in `run_training()`
- **Fix**: Ensure `src/retrain.py` imports work (`sys.path` set)

---

## Monitoring & Logs

### Railway Backend Logs
1. Dashboard → **Deployments** → latest
2. Click **View Logs**
3. Search for errors: "Failed", "Error", "Exception"
4. Common patterns: missing env vars, import errors, API failures

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

- **Database**: Supabase handles auto-scaling (PostgreSQL 15)
- **Backend**: Railway scales containers automatically
- **Frontend**: Vercel has built-in CDN and edge caching
- **Storage**: Supabase Storage backed by S3, unlimited capacity

For 10k+ monthly users:
- Monitor Supabase CPU/RAM (Settings → Usage)
- Consider Railway paid plan if hitting bandwidth limits
- Add Redis cache for frequently accessed data (optional)

---

## Git Workflow

Main branch: `main` (stable releases)
Dev branch: `phase-1-supabase-foundation` (active development)

To deploy a new version:
```bash
git checkout main
git merge phase-1-supabase-foundation
git push origin main
```

Railway and Vercel will auto-redeploy on push to main.

---

## Contacts & Docs

- **Supabase**: https://supabase.io/docs
- **Railway**: https://docs.railway.app
- **Vercel**: https://vercel.com/docs
- **FastAPI**: https://fastapi.tiangolo.com
- **Next.js**: https://nextjs.org/docs

---

**Deployment Status**: Ready for production
**Last Updated**: 2026-07-05
