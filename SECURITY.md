# Security Policy

## Scope

This is a personal-finance transaction categorizer that handles real financial
data (Alipay/WeChat statement exports). It's a single-maintainer project, not
a company with a security team — but because it touches sensitive financial
data, security reports are taken seriously and triaged promptly.

Covers:
- `frontend/` (Next.js, deployed on Vercel)
- `backend/` (FastAPI, deployed on Render)
- `src/` (ML pipeline)
- `supabase/` (database schema, RLS policies, storage rules)

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Instead, report privately by emailing **chinsanaa0202@gmail.com** with:
- A description of the vulnerability and its potential impact
- Steps to reproduce (or a proof-of-concept if possible)
- Which component is affected (frontend / backend / database / ML pipeline)

You should receive an acknowledgment within **5 business days**. This is a
solo-maintained project, so timelines are best-effort:
- **Critical** (auth bypass, cross-user data exposure, RCE): aiming to
  patch within a few days of confirmation
- **High/Medium**: patched in the next reasonable release
- **Low**: addressed as time allows

Please give a reasonable window to fix the issue before any public
disclosure. Credit is happily given in release notes if you'd like it.

## Supported Versions

This project doesn't maintain multiple release branches — only the latest
code on `main` is supported. Security fixes are applied there and deployed
immediately (no backporting to older commits).

## Areas of Particular Concern

Given the app's architecture, these are the highest-value areas for
security review, and where reports are most appreciated:

- **Cross-user data isolation** — every transaction, rule, and model belongs
  to a `user_id`. Any way to read, modify, or infer another user's data
  (via API, RLS bypass, or otherwise) is treated as critical.
- **Row-Level Security (RLS)** — all Supabase tables have RLS enabled as
  defense-in-depth; the backend also explicitly scopes every query by
  `user_id`. A gap between these two layers is a priority finding.
- **Auth** — Supabase Auth (email/password) issuing JWTs consumed by
  FastAPI. Token validation, session handling, and privilege escalation
  paths are in scope.
- **File upload handling** — CSV/Excel statement parsing (Alipay/WeChat
  exports) is a natural injection/parsing-abuse surface (formula injection,
  zip bombs, malformed encodings, etc.).
- **Service-role key usage** — the backend uses a Supabase service-role key
  that bypasses RLS; any endpoint that doesn't correctly re-apply per-user
  scoping on top of it is a serious bug.

## Out of Scope

- Vulnerabilities requiring physical access to a user's device
- Social engineering / phishing
- Denial-of-service via brute-force volume (rate limiting is on the
  roadmap, not yet a hardened control)
- Findings from automated scanners without a demonstrated, working exploit

## Handling of Your Own Data

If your report requires sharing real transaction data or credentials to
demonstrate an issue, please use synthetic/sample data instead. If that's
not possible, say so in your report and it will be deleted immediately
after the issue is confirmed and fixed.
