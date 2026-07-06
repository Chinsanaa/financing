# Local Testing Guide — Financing SaaS

Test the full stack (backend + frontend + Supabase) locally before deployment.

## Prerequisites

- [x] Supabase project created (you have credentials in `.env.local`)
- [x] Python 3.10+ installed
- [x] Node.js 18+ installed
- [x] Backend code in `backend/`
- [x] Frontend code in `frontend/`

## Architecture

```
Browser (localhost:3000)
    ↓
Next.js Dev Server (localhost:3000)
    ↓ [HTTP calls with JWT]
FastAPI Dev Server (localhost:8000)
    ↓ [Service role key]
Supabase (cloud)
    ↓ [RLS policies]
```

All traffic is LOCAL except to Supabase (which uses your remote project).

---

## Part 1: Start FastAPI Backend

### 1.1: Install Backend Dependencies

```bash
cd financing/backend
pip install -r requirements.txt
```

Should install: fastapi, uvicorn, supabase, pandas, scikit-learn, etc.

### 1.2: Verify Environment Variables

The `.env.local` file already has Supabase credentials. Verify it exists:

```bash
# From project root
cat .env.local
```

You should see:
```
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_JWT_SECRET=...
```

### 1.3: Start the FastAPI Server

```bash
cd backend
python main.py
```

Or with auto-reload:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

You should see:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started server process [12345]
```

### 1.4: Test Backend Health

In a new terminal:

```bash
curl http://localhost:8000/health
```

Should return: `{"status":"ok"}`

View the interactive docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Part 2: Start Next.js Frontend

### 2.1: Install Frontend Dependencies

```bash
cd financing/frontend
npm install
```

### 2.2: Configure Environment

```bash
cp .env.example .env.local
```

Edit `frontend/.env.local`:

```
NEXT_PUBLIC_SUPABASE_URL=https://<your-project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOi...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Important**: Use `http://localhost:8000` (not HTTPS, not a Railway URL).

### 2.3: Start the Next.js Dev Server

```bash
npm run dev
```

You should see:

```
> ready - started server on 0.0.0.0:3000, url: http://localhost:3000
```

---

## Part 3: Test the Full Flow

### 3.1: Signup & Email Verification

1. Open http://localhost:3000 in browser
2. You'll redirect to `/auth` (not logged in)
3. Click **"Don't have an account? Sign up"**
4. Enter test email: `test@example.com`
5. Enter password: `testpass123`
6. Click **Sign Up**
7. Should show: "Check your email to confirm your account"

**Check Supabase for the verification link**:
- Go to https://dashboard.supabase.io
- Project → Auth → Users
- Click the user you just created
- Copy the confirmation token from the "Email confirmations pending" section
- Or: Set the user as **Confirmed** manually in the dashboard

For local testing, manually confirm the user in Supabase:
```sql
-- In Supabase SQL Editor
UPDATE auth.users 
SET email_confirmed_at = NOW()
WHERE email = 'test@example.com';
```

### 3.2: Login

1. Go back to `/auth`
2. Enter email: `test@example.com`
3. Enter password: `testpass123`
4. Click **Sign In**
5. Should redirect to `/dashboard`
6. Should see: email address in top-right, 6 tabs (Dashboard, Upload, Label, Review, Categories, Training)

**Check browser DevTools**:
- Application → Cookies → `sb-*` (Supabase session)
- Console → No errors

### 3.3: Dashboard Tab

Should show:
- Total Transactions: 0
- Labeled: 0
- Total Spend: ¥0
- Status: In Progress

No errors expected (no data yet).

### 3.4: Upload Tab

1. Click **Upload** tab
2. Drag-drop or click to select a CSV file
3. Try with a test Alipay/WeChat CSV (if you have one)
4. Should show: "Uploaded X transactions. Ready to label."

**Check backend logs**: Should see `POST /uploads/ 200 OK`

**Check Supabase**:
- Dashboard → SQL Editor:
  ```sql
  SELECT COUNT(*) FROM transactions WHERE user_id = '[YOUR_USER_ID]';
  ```
  Should show transaction count > 0

If no CSV file: create a minimal one:
```csv
timestamp,merchant,description,amount
2026-01-01 10:30:00,Test Store,Test Item,100.00
2026-01-02 14:15:00,Restaurant,Lunch,50.50
```

Save as `test.csv` and upload.

### 3.5: Label Tab

1. Click **Label** tab
2. Should show a transaction card with:
   - Merchant: "Test Store"
   - Description: "Test Item"
   - Amount: ¥100.00
   - Model Suggestion: "Other" (100% confidence, since no model trained yet)
3. Click a category button (e.g., "Shopping")
4. Transaction should disappear, progress bar moves
5. Click next transaction
6. Repeat until all labeled

**Check Supabase**:
```sql
SELECT COUNT(*) FROM transactions WHERE labeled = TRUE;
```
Should increase with each label.

### 3.6: Training Tab

1. Click **Training** tab
2. Click **Start Training**
3. Should show: "Training started! Check back soon for results."
4. Training history shows status: "running"

**Watch backend logs**: Should see:
```
[Training 1234...] Starting with X samples and Y categories
[Training 1234...] Training complete. Uploading artifacts...
[Training 1234...] Complete (accuracy: 0.XX)
```

If training fails:
- Check if you labeled at least 5 transactions
- Check if categories exist (Categories tab)
- Check backend logs for error details

### 3.7: Review Queue

1. Click **Review** tab
2. If any unlabeled transactions, should show table
3. Should have columns: Merchant, Description, Amount, Suggestion, Confidence
4. Initially empty (or shows transactions that don't fit in the auto-acceptance threshold)

### 3.8: Categories

1. Click **Categories** tab
2. Should show your default categories (Food, Transport, Shopping, etc.)
3. Try adding a new category: type "Hobbies" and click **Add**
4. Should appear in the list
5. Click **Delete** to remove it

**Check Supabase**:
```sql
SELECT name FROM categories WHERE user_id = '[YOUR_USER_ID]';
```

### 3.9: Logout

1. Click **Logout** button (top-right)
2. Should redirect to `/auth`
3. Session should be cleared

---

## Part 4: Debugging

### Backend Logs

Watch the FastAPI terminal for:
```
INFO:     127.0.0.1:12345 - "POST /uploads/ HTTP/1.1" 200 OK
INFO:     127.0.0.1:12346 - "POST /training/retrain HTTP/1.1" 200 OK
ERROR: ... traceback
```

Common errors:
- `ModuleNotFoundError: No module named 'src.retrain'` → Run from project root, not backend/
- `KeyError: 'SUPABASE_SERVICE_ROLE_KEY'` → Missing env var, check `.env.local`
- `RPC failed; curl 6 Could not resolve host` → Network issue, check internet connection

### Frontend Logs

Open browser DevTools (`F12`):

**Console tab**:
- Should be clean (no red errors)
- May see warnings (ok)

**Network tab**:
- Click a button (e.g., Upload)
- Should see HTTP requests to `http://localhost:8000/...`
- Should see response status `200` (ok) or `401` (auth needed)
- Check `Authorization` header is present on requests

**Application tab**:
- Cookies → `sb-*` contains session
- Local Storage → Check if auth state persists

### Supabase Dashboard

Check in real-time:
- **Auth** → Users → verify user exists
- **Database** → transactions table → see your uploads
- **Database** → model_runs table → see training history
- **Logs** → API requests / Auth → filter by request type

---

## Stopping Services

**FastAPI Backend**: Press `Ctrl+C` in the backend terminal

**Next.js Frontend**: Press `Ctrl+C` in the frontend terminal

**Clean up ports** (if stuck):

```bash
# Windows PowerShell
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process
Get-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess | Stop-Process
```

---

## Common Issues & Fixes

### Issue: "Cannot POST /uploads/"

**Cause**: Backend not running or wrong URL

**Fix**:
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check frontend `.env.local` has `NEXT_PUBLIC_API_URL=http://localhost:8000`
3. Restart frontend: `npm run dev`

### Issue: "401 Unauthorized"

**Cause**: JWT token missing or invalid

**Fix**:
1. Check browser DevTools → Network → Headers → `Authorization: Bearer ...`
2. Verify `SUPABASE_JWT_SECRET` in `.env.local` matches Supabase dashboard
3. Try logout/login again

### Issue: "Cannot find module 'src.retrain'"

**Cause**: Python path not set or wrong working directory

**Fix**:
1. Make sure you're in `financing/` root, not `financing/backend/`
2. Restart backend: `cd financing && python backend/main.py`

### Issue: Training never completes

**Cause**: Background task crashed silently

**Fix**:
1. Check backend logs for exceptions
2. Ensure you labeled at least 5 transactions
3. Check `src/retrain.py` imports work: `python -c "import src.retrain"`

---

## Next: Deploy to Production

Once local testing passes:

1. **Push to GitHub**: `git push origin phase-1-supabase-foundation`
2. **Create/merge PR #13**
3. **Deploy to Railway**: Link repo, set env vars, deploy
4. **Deploy to Vercel**: Link frontend, set env vars, deploy
5. **Monitor logs**: Check Railway + Vercel dashboards

See **DEPLOYMENT.md** for detailed steps.

---

**Happy Testing!** 🚀
