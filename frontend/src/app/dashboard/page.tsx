import DashboardClient from './DashboardClient';

// Auth-gated: depends on per-request session state, so it must never be
// statically prerendered (createClient() would run at build time inside
// a Client Component, which is what DashboardClient.tsx is).
export const dynamic = 'force-dynamic';

export default function DashboardPage() {
  return <DashboardClient />;
}
