import { Suspense } from 'react';
import AuthClient from './AuthClient';

// Depends on createClient() at render time, which needs runtime env vars;
// must never be statically prerendered (createClient() would run at build
// time inside a Client Component, which is what AuthClient.tsx is).
export const dynamic = 'force-dynamic';

export default function AuthPage() {
  return (
    <Suspense>
      <AuthClient />
    </Suspense>
  );
}
