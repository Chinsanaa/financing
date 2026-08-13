/** @type {import('next').NextConfig} */
// Backend origin isn't hardcoded anywhere (it's env-configured per deploy —
// see NEXT_PUBLIC_API_URL in README setup steps), so build connect-src from
// the same env var the API client itself uses, rather than guessing a host.
const backendOrigin = process.env.NEXT_PUBLIC_API_URL || '';

// Next.js App Router's inline hydration script needs 'unsafe-inline' for
// script-src without extra nonce-wiring in middleware — ship a reasonably
// strict policy for now; tightening script-src to nonce-based is a good
// follow-up but out of scope here.
const csp = [
  "default-src 'self'",
  `connect-src 'self' https://*.supabase.co ${backendOrigin}`.trim(),
  "img-src 'self' data:",
  "style-src 'self' 'unsafe-inline'",
  "script-src 'self' 'unsafe-inline'",
  "frame-ancestors 'none'",
].join('; ');

const securityHeaders = [
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains' },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
  { key: 'Content-Security-Policy', value: csp },
];

const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  async headers() {
    return [{ source: '/(.*)', headers: securityHeaders }];
  },
};

module.exports = nextConfig;
