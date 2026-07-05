# Financing Frontend — Next.js SaaS UI

Multi-tenant financial dashboard for transaction classification and spending analysis.

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Auth**: Supabase Auth (@supabase/ssr)
- **API**: Axios (calls FastAPI backend)
- **Charts**: Recharts (optional, for trends visualization)

## Setup

### 1. Install Dependencies
```bash
npm install
```

### 2. Configure Environment
```bash
cp .env.example .env.local
```

Edit `.env.local` with your Supabase credentials and backend URL:
```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
NEXT_PUBLIC_API_URL=http://localhost:8000  # or your Railway backend URL
```

### 3. Run Locally
```bash
npm run dev
```

Frontend runs on `http://localhost:3000`. Open in browser.

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx          # Root redirect (auth → dashboard)
│   │   ├── auth/
│   │   │   ├── page.tsx      # Signup/Login form
│   │   │   └── verify/
│   │   │       └── page.tsx  # Email verification
│   │   ├── dashboard/
│   │   │   └── page.tsx      # Main dashboard (6-tab layout)
│   │   ├── layout.tsx        # Root layout
│   │   └── globals.css       # Tailwind setup
│   ├── components/
│   │   └── tabs/
│   │       ├── StatsTab.tsx       # Dashboard summary + spending breakdown
│   │       ├── UploadTab.tsx      # CSV drag-drop upload
│   │       ├── LabelTab.tsx       # Transaction labeling interface
│   │       ├── ReviewTab.tsx      # Review queue table
│   │       ├── CategoriesTab.tsx  # Category CRUD
│   │       └── TrainingTab.tsx    # Model training status
│   └── utils/
│       ├── supabase.ts       # Supabase client setup
│       └── api.ts            # FastAPI endpoints wrapper
├── public/                    # Static assets
├── package.json
├── tsconfig.json
├── next.config.js
├── tailwind.config.js
└── postcss.config.js
```

## Features

### Auth Flow
1. Signup with email/password (Supabase Auth)
2. Email verification required
3. Login redirects to dashboard
4. Logout clears session

### 6-Tab Dashboard
1. **Dashboard** — Total transactions, labeling progress, total spend, breakdown by category
2. **Upload** — Drag-drop CSV/Excel, auto-detect Alipay/WeChat format
3. **Label** — Batch review of unlabeled transactions with model suggestions
4. **Review** — Table of transactions pending manual review
5. **Categories** — Add/remove/edit spending categories
6. **Training** — Trigger model retraining, view training history + metrics

### API Integration
All routes call FastAPI backend with JWT auth:
- Auth: signup, login, logout
- Categories: list, create, update, delete
- Uploads: upload file, poll status
- Training: start retrain, check status
- Classify: predict, accept, override
- Dashboard: summary, by-category, trends, review-queue

## RLS & Multi-Tenancy

- Supabase RLS policies enforce user isolation at the database layer
- Anon key used for frontend (can only see own data)
- Service role key on backend (can write/update)
- JWT in every request header

## Deployment

Target: **Vercel** for frontend, **Railway** for backend.

```bash
# Build
npm run build

# Deploy to Vercel
vercel deploy
```

## Development Notes

- **Auth redirect**: Root page checks session, redirects to /auth or /dashboard
- **Token refresh**: Handled by Supabase SDK automatically
- **Error handling**: Try-catch blocks in each tab; messages shown to user
- **Polling**: Training tab polls backend every 5s until complete
- **Responsive**: Mobile-first Tailwind design

## Next Steps

- [ ] Add trending chart (Recharts)
- [ ] Add export to Excel
- [ ] Add dark mode toggle
- [ ] Add settings page (budget limits, email alerts)
- [ ] Mobile app (React Native / Flutter)
