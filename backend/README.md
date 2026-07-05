# FastAPI Backend — Financing SaaS

**Framework**: FastAPI with Supabase integration  
**Deployment**: Railway  
**Port**: 8000

Multi-tenant SaaS backend for transaction classification with 7 route groups.

---

## 🏗️ Architecture

7 route groups handling the complete SaaS workflow:

| Route | Purpose | Key Endpoints |
|-------|---------|---|
| **Auth** | User authentication | POST `/auth/signup`, `/auth/login`, `/auth/logout` |
| **Categories** | Spending categories | GET/POST/PATCH/DELETE `/categories/` |
| **Uploads** | File uploads | POST `/uploads/` with CSV/Excel |
| **Training** | Model training | POST `/training/retrain`, GET `/training/{id}` |
| **Classify** | Categorize transactions | POST `/classify/{id}/label`, `/classify/{id}/accept` |
| **Dashboard** | Analytics & stats | GET `/dashboard/{endpoint}` (8 endpoints) |
| **Settings** | User management | GET/PATCH `/settings/profile`, DELETE `/settings/account` |

---

## 📋 Setup

### Local Development

```bash
pip install -r requirements.txt

# Create .env.local
SUPABASE_URL=https://[project-id].supabase.co
SUPABASE_SERVICE_ROLE_KEY=[secret-key]
SUPABASE_JWT_SECRET=[jwt-secret]
ENVIRONMENT=development

# Run
python -m uvicorn main:app --reload
```

Server runs on `http://localhost:8000`. API docs at `/docs`.

## API Routes

### Auth
- `POST /auth/signup` — Create account
- `POST /auth/login` — Authenticate and get token
- `POST /auth/logout` — Sign out
- `POST /auth/refresh` — Refresh access token

### Categories
- `GET /categories` — List user categories
- `POST /categories` — Create category
- `PUT /categories/{id}` — Update category
- `DELETE /categories/{id}` — Delete category

### Uploads
- `POST /uploads` — Upload CSV (Alipay/WeChat)
- `GET /uploads/{id}` — Poll upload status
- `GET /uploads` — List all uploads

### Training
- `POST /training/retrain` — Trigger model retraining (background task)
- `GET /training/{id}` — Poll training status
- `GET /training` — List training runs

### Classification
- `POST /classify` — Classify unlabeled transactions
- `PUT /classify/{id}` — Accept suggestion (mark as labeled)
- `POST /classify/{id}/override` — Override with manual label

### Dashboard
- `GET /dashboard/summary` — Overall stats
- `GET /dashboard/by-category` — Spending by category
- `GET /dashboard/trends` — Spending trends (last N days)
- `GET /dashboard/review-queue` — Transactions needing review
- `GET /dashboard/onboarding-status` — User's onboarding phase
- `POST /dashboard/onboarding-complete` — Mark onboarding done

## Auth Flow

All endpoints except `/health` require an `Authorization: Bearer <token>` header.

1. User signs up → Supabase auth + triggers profile creation + default categories
2. User logs in → Returns access token
3. Requests to API include `Authorization: Bearer <token>`
4. Auth middleware validates JWT and extracts `user_id`
5. RLS policies in database enforce: users see only their own data

## Development

### Endpoints Needing Implementation
- [ ] **CSV Parsing**: `routes/uploads.py` has stubs for Alipay/WeChat parsers
- [ ] **Training Pipeline**: `routes/training.py` calls `src/retrain.py` (needs file paths)
- [ ] **Model Storage**: User-scoped paths in Supabase Storage (not yet implemented)
- [ ] **Semantic Layer**: `routes/classify.py` uses `src/semantic.py` (ready)

### Next Steps
1. Implement CSV parsers (use existing `src/parse_alipay.py`, `src/parse_wechat.py` if available, or build)
2. Wire training background task to actually call `retrain_model()`
3. Set up model versioning + storage (Supabase Storage or local paths)
4. Build Next.js frontend

## Deployment

Target: Railway.app for backend, Vercel for frontend.

**Railway setup** (WIP):
```bash
railway link  # Link to Railway project
railway up    # Deploy
```

## Error Handling

- **400**: Bad request (missing fields, invalid file)
- **401**: Unauthorized (missing/invalid token)
- **404**: Not found (resource doesn't exist)
- **500**: Server error (see logs)

All endpoints return JSON with `detail` field on error.
