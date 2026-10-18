import { NextRequest, NextResponse } from 'next/server';

/**
 * Server-side auth gating. Before this existed, every protected page
 * shipped its full client bundle, showed a "Loading..." flash, THEN
 * redirected from a useEffect.
 *
 * This is a lightweight cookie-presence check (the @supabase/ssr browser
 * client stores the session in an `sb-<ref>-auth-token` cookie) — real
 * authentication is enforced per-request by the backend's JWT middleware;
 * the client-side session checks remain as a backstop.
 */

function hasSessionCookie(req: NextRequest): boolean {
  return req.cookies
    .getAll()
    .some((c) => /^sb-.+-auth-token/.test(c.name) && c.value.length > 0);
}

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const authed = hasSessionCookie(req);

  if (pathname === '/') {
    // Signed-in users skip the marketing page; signed-out users see the landing.
    return authed
      ? NextResponse.redirect(new URL('/dashboard', req.url))
      : NextResponse.next();
  }
  if (!authed && (pathname.startsWith('/dashboard') || pathname.startsWith('/settings'))) {
    return NextResponse.redirect(new URL('/auth', req.url));
  }
  // ?expired=1 comes from the API client after the backend rejected the
  // session; never bounce it back to the dashboard (that loops).
  if (authed && pathname === '/auth' && req.nextUrl.searchParams.get('expired') !== '1') {
    return NextResponse.redirect(new URL('/dashboard', req.url));
  }
  return NextResponse.next();
}

// NOTE: '/auth' matches exactly — /auth/verify must stay reachable in every
// auth state to complete email confirmation.
export const config = {
  matcher: ['/', '/auth', '/dashboard/:path*', '/settings/:path*'],
};
