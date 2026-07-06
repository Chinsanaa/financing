# Security Audit Checklist — Phase 5

Production checklist for financing SaaS before launch.

## 1. Authentication & Authorization

- [x] HTTP-only cookies for session storage (via `@supabase/ssr`)
- [x] JWT validation on every protected route (FastAPI auth middleware)
- [x] Email verification gate (`email_confirmed_at` check)
- [x] Token expiry/tamper detection (Supabase JWT)
- [ ] Password reset flow (scoped token, short TTL)
- [x] Logout clears session cookie

## 2. Rate Limiting

- [x] Signup: 5/hour per IP (`slowapi`)
- [x] Login: 10/15 minutes per IP (`slowapi`)
- [ ] Email verification resend: 3/hour per email (manual impl)
- [ ] Password reset: 3/hour per email (manual impl)
- [x] General authenticated routes: 60/min per user (optional, can add per-endpoint)

**Status**: Basic limits in place. Email-based limits require custom middleware.

## 3. Data Validation & Sanitization

### Uploads

- [x] Extension check (CSV/XLSX only)
- [x] Size limit (10MB max, checked before body read)
- [x] Row count limit (50k rows max post-parse)
- [x] Content sniffing (attempt parse in try/except)
- [x] Failed uploads logged with error_message

### Input

- [x] Pydantic models validate all request bodies (type-safe, bounds-checked)
- [x] EmailStr validates email format
- [x] Numeric fields bounds-checked (monthly_income, amounts)

## 4. XSS Prevention

- [x] React JSX escaping (default, automatic)
- [x] No `dangerouslySetInnerHTML` anywhere (searched: clean)
- [x] User input (merchant, description) never rendered as HTML
- [x] API responses JSON-encoded (never raw HTML)

**Evidence**: Merchant/description in dashboard/tables rendered as text content, never innerHTML.

## 5. SQL Injection Prevention

- [x] All Postgres queries use supabase-py parameterized interface (no string interpolation)
- [x] No raw SQL strings in route handlers
- [x] Category/transaction IDs validated as UUIDs before WHERE clauses

**Evidence**: All routes use `.eq()`, `.select()`, `.insert()` on Supabase client, never string-formatted SQL.

## 6. CORS Configuration

- [x] Allowed origins: `http://localhost:3000` (dev), `https://financing.vercel.app` (prod)
- [x] Credentials: `true` (allow cookies)
- [x] Methods: `["*"]` (explicit allow needed for production audit, but safe for now)
- [x] Headers: `["*"]` (standard)

**Note**: Audit line-by-line before production deploy to restrict to necessary methods/headers.

## 7. Data Isolation (RLS)

### Row-Level Security Policies

- [x] `profiles`: select/update only own (id = auth.uid())
- [x] `categories`: select/insert/update/delete only own (user_id = auth.uid())
- [x] `transactions`: select/insert/update/delete only own (user_id = auth.uid())
- [x] `merchant_rules`: select allows global (user_id IS NULL) + own; insert/update/delete own only
- [x] `model_runs`: select own only (read-only policy, backend-written via service role)
- [x] `budget_config`, `budget_category_config`: select/insert/update/delete own only
- [x] `uploads`: select/insert/update/delete own only
- [x] `special_rules`: select/insert/update/delete own only

### Backend Scoping

- [x] Every route explicitly filters by `user_id = request.state.user_id` (defense-in-depth)
- [x] Service role key used only for backend writes; frontend uses anon key
- [x] Cross-user reads/writes fail at both FastAPI and RLS layers

**Test**: Attempt to read/write another user's data via direct API call with tampered JWT → must fail at RLS.

## 8. Secrets & Environment

- [x] `.env.local` never committed (gitignored)
- [x] `SUPABASE_SERVICE_ROLE_KEY` only in backend (never exposed to frontend)
- [x] `NEXT_PUBLIC_*` variables safe to expose (anon key + RLS boundary)
- [x] JWT secret not hardcoded

## 9. File Handling & Storage

- [x] Temporary files cleaned up after parse (`.unlink(missing_ok=True)`)
- [x] Storage RLS scopes files by user_id prefix
- [x] Account deletion deletes Storage objects before Auth (no orphans)
- [x] Model artifacts stored under `{user_id}/models/{run_id}/` so the bucket
  RLS (first path segment = user_id) and account-deletion cleanup both apply
  (fixed 2026-07-06 — they were previously written under `models/{user_id}/…`,
  which orphaned them on deletion)

## 10. Error Messages

- [x] Validation errors are specific (help users fix, no info leak)
- [x] Auth errors are generic ("Invalid credentials", not "Email not found")
- [x] 500 errors logged server-side, generic response to client

## 11. Security Testing

### Cross-User RLS Tests

**Test 1: Read another user's transactions**
```
1. Create User A, User B
2. User A uploads transactions
3. User B attempts: GET /transactions?user_id=<A's ID>
4. Result: RLS blocks at Postgres, 401 from FastAPI
```

**Test 2: Update another user's category**
```
1. User A creates category X
2. User B attempts: PATCH /categories/<X's ID> with name="Hacked"
3. Result: RLS blocks (no matching row for B), 404 from FastAPI
```

**Test 3: Delete another user's account**
```
1. User A's account exists
2. User B attempts: DELETE /settings/account with B's JWT
3. Result: Only B's account deletes, A's data untouched
```

### JWT Tampering Tests

**Test 1: Expired token**
```
1. Login, get access token
2. Wait past expiry (or set JWT exp to past)
3. Attempt: GET /dashboard/summary with expired token
4. Result: 401 Unauthorized
```

**Test 2: Tampered token**
```
1. Take valid JWT, flip one character in signature
2. Attempt: GET /dashboard/summary with tampered token
3. Result: 401 Unauthorized (signature invalid)
```

### Rate Limit Tests

**Test 1: Signup rate limit**
```
1. POST /auth/signup 6 times in 1 hour from same IP
2. Result: 6th request returns 429 Too Many Requests
```

**Test 2: Login rate limit**
```
1. POST /auth/login 11 times in 15 minutes from same IP
2. Result: 11th request returns 429 Too Many Requests
```

### Upload Validation Tests

**Test 1: Oversized file**
```
1. Upload 11MB file
2. Result: 400 Bad Request ("exceeds 10MB")
```

**Test 2: Too many rows**
```
1. Create CSV with 50,001 rows
2. Upload
3. Result: 400 Bad Request ("exceeds 50k rows")
```

**Test 3: Invalid format**
```
1. Upload .txt file or random binary
2. Result: 400 Bad Request ("Could not detect file source")
```

## 12. Production Checklist

Before deploying to prod:

- [ ] Allowed CORS origins hardcoded (no `*`)
- [ ] Rate limits tested under load
- [ ] Secrets rotated (JWT secret, service role key)
- [ ] Logs configured (CloudWatch, Datadog, or equivalent)
- [ ] Monitoring alerts set (auth failures, rate limit spike, 500 errors)
- [ ] HTTPS enforced (Railway/Vercel auto-enforce)
- [ ] Database backups enabled (Supabase default)
- [ ] Session TTLs audited (JWT exp, refresh token rotation)

## Notes

- **RLS is the boundary**, not the client. Backend explicitly re-scopes even though RLS holds.
- **XSS**: React's JSX escaping + no innerHTML means safe by default. Keep it that way.
- **SQL injection**: Supabase parameterized API prevents this entirely. No raw SQL ever.
- **Rate limiting**: slowapi in-memory for single-instance Railway. If scaled to multiple replicas, swap for Redis-backed limiter.

---

**Last Updated**: 2026-07-06 (Phase 5)
**Status**: Ready for security testing
