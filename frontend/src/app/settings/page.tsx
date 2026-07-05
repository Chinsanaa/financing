import SettingsClient from './SettingsClient';

// Auth-gated: depends on per-request session state, so it must never be
// statically prerendered (createClient() would run at build time inside
// a Client Component, which is what SettingsClient.tsx is).
export const dynamic = 'force-dynamic';

export default function SettingsPage() {
  return <SettingsClient />;
}
