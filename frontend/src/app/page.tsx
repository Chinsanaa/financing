import HomeClient from './HomeClient';

// Auth-gated redirect: depends on per-request session state, so it must
// never be statically prerendered (createClient() would run at build time
// inside a Client Component, which is what HomeClient.tsx is).
export const dynamic = 'force-dynamic';

export default function HomePage() {
  return <HomeClient />;
}
