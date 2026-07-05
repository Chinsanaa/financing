# Quick Start — Local Testing

## Terminal 1: FastAPI Backend

```bash
cd financing/backend
pip install -r requirements.txt
python main.py
```

Wait for:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

Test it works:
```bash
curl http://localhost:8000/health
# Returns: {"status":"ok"}
```

---

## Terminal 2: Next.js Frontend

```bash
cd financing/frontend
npm install
npm run dev
```

Wait for:
```
ready - started server on 0.0.0.0:3000
```

---

## Browser: http://localhost:3000

1. **Sign Up**
   - Email: `test@example.com`
   - Password: `testpass123`
   - Click **Sign Up**

2. **Verify Email** (manually in Supabase)
   - Go to https://dashboard.supabase.io
   - Auth → Users → Click your user
   - Click **Confirm Email** or run in SQL Editor:
     ```sql
     UPDATE auth.users 
     SET email_confirmed_at = NOW()
     WHERE email = 'test@example.com';
     ```

3. **Login**
   - Go back to http://localhost:3000
   - Email: `test@example.com`
   - Password: `testpass123`
   - Click **Sign In**

4. **Test Upload Tab**
   - Create a CSV file (`test.csv`):
     ```csv
     timestamp,merchant,description,amount
     2026-01-01 10:30:00,McDonald's,Lunch,50.00
     2026-01-02 14:15:00,Starbucks,Coffee,20.00
     ```
   - Upload it
   - Should show: "Uploaded 2 transactions"

5. **Test Label Tab**
   - Should see first transaction
   - Click a category (e.g., "Eating Out")
   - Move to next transaction
   - Label all 2

6. **Test Training Tab**
   - Click **Start Training**
   - Watch logs in Terminal 1
   - Should see training progress

7. **Test Dashboard Tab**
   - Should show stats updated

---

## Troubleshooting

**Backend won't start**:
```bash
pip install -r requirements.txt  # Install missing packages
python main.py  # Try again
```

**Frontend won't start**:
```bash
npm install  # Install missing packages
npm run dev  # Try again
```

**"Cannot POST /uploads/"**:
- Check backend is running: `curl http://localhost:8000/health`
- Check frontend `.env.local` has `NEXT_PUBLIC_API_URL=http://localhost:8000`

**"401 Unauthorized"**:
- Login again
- Check Supabase user is confirmed (see step 2 above)

---

## Full Testing Guide

See **TEST_LOCAL.md** for detailed steps + debugging.

---

Done! Ready to deploy to production? See **DEPLOYMENT.md**.
