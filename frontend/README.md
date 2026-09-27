# Frontend — Next.js (Vercel)

Multi-tenant dashboard for the transaction classifier. Auth via Supabase
(email/password), data via the FastAPI backend.

## Setup

```bash
npm install
cp .env.example .env.local
# NEXT_PUBLIC_SUPABASE_URL=…      your Supabase project URL
# NEXT_PUBLIC_SUPABASE_ANON_KEY=… anon key (public by design; RLS + backend enforce isolation)
# NEXT_PUBLIC_API_URL=…           FastAPI base URL (http://localhost:8000 locally)
npm run dev        # http://localhost:3000
npm run build      # production build (also the CI check)
npx tsc --noEmit   # typecheck
```

## Structure

```
src/
├── middleware.ts              # server-side auth gating (no client redirect flash)
├── app/
│   ├── layout.tsx, page.tsx    # page.tsx renders the Landing marketing page
│   ├── auth/                  # AuthClient (login/signup), verify/ (email confirmation)
│   ├── dashboard/             # DashboardClient — 5 sections, tabs code-split via next/dynamic
│   └── settings/              # SettingsClient — income, account deletion
├── components/
│   ├── ui-feedback.tsx        # shared Alert / Loading / ProgressBar
│   ├── ui/                    # design-system components (Card, StatTile,
│   │                          #   RollingNumber, Tabs, CommandPalette, …)
│   └── tabs/                  # one component per dashboard tab
└── utils/
    ├── supabase.ts            # browser client factory
    ├── api.ts                 # axios client; interceptor attaches the current
    │                          #   Supabase token per request, 401 → /auth
    └── useApi.ts              # cached stale-while-revalidate data hook +
                               #   invalidate(prefix) for mutations
```

## Dashboard sections (5)

The ten original tabs are grouped into five compact sections with sub-tabs:
**Overview**, **Transactions & Model** (Upload / Categories / Label / Review /
Training), **Planning** (Budget / 50/30/20 / Savings / Subscriptions /
Insights / Action plan, reached via the pill sub-tabs), and **Reports**
(CSV export + pagination). ⌘K / Ctrl+K opens a command menu for every tab. Each tab's component is code-split via
`next/dynamic` so only the active tab's JS loads.

## Design system

Read **`../docs/DESIGN_SYSTEM.md`** before adding UI: tokens (never raw hex),
motion rules, effect classes (`.spotlight`, `.glow-border`, `.stagger-in`, …),
components, and how to screenshot-verify the logged-in dashboard with mocked
data. Success feedback uses `toast.success()` (sonner); errors stay inline.

## Data-fetching conventions

- Components call `useApi<T>('/path')` — never hand-roll fetch/useEffect
  boilerplate or Authorization headers.
- After a mutation, call `invalidate('/dashboard')` (or the relevant prefix)
  so cached tabs refresh; update local state optimistically where possible.
- Auth tokens are attached by the axios interceptor in `utils/api.ts`;
  `getSession()` transparently refreshes expired tokens.

## Deployment (Vercel)

Set the three `NEXT_PUBLIC_*` env vars in the Vercel project. The build fails
loudly if `NEXT_PUBLIC_API_URL` is missing in production (no silent localhost
fallback). Security headers are set in `next.config.js`.
