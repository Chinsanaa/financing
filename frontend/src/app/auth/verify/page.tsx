'use client';

import { Suspense, useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { createClient } from '@/utils/supabase';

/**
 * Handles every redirect shape Supabase email confirmation actually uses:
 * - PKCE flow (default with @supabase/ssr): `?code=...` → exchangeCodeForSession
 * - Token-hash links: `?token_hash=...&type=...` → verifyOtp
 * - Legacy `?token=...&type=email` → verifyOtp
 * - Implicit flow: `#access_token=...` fragment → onAuthStateChange fires
 * - Error redirects: `?error_description=...` → surfaced to the user
 *
 * The old version only handled `?token=&type=email`, so most confirmation
 * links landed on a static "check your email" page and did nothing.
 */
function VerifyContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [supabase] = useState(() => createClient());

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const redirectSoon = () => {
      setMessage('Email verified! Redirecting...');
      setTimeout(() => router.push('/dashboard'), 1500);
    };

    // Implicit-flow links put the session in the URL hash; the client
    // consumes it automatically and fires SIGNED_IN.
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'SIGNED_IN') redirectSoon();
    });

    const handleVerification = async () => {
      const errorDescription = searchParams.get('error_description');
      if (errorDescription) {
        setError(errorDescription);
        return;
      }

      const code = searchParams.get('code');
      const tokenHash = searchParams.get('token_hash') || searchParams.get('token');
      const type = searchParams.get('type');

      if (!code && !tokenHash) return; // plain visit: show the instructions

      setLoading(true);
      try {
        if (code) {
          const { error } = await supabase.auth.exchangeCodeForSession(code);
          if (error) setError(error.message);
          else redirectSoon();
        } else if (tokenHash) {
          const { error } = await supabase.auth.verifyOtp({
            token_hash: tokenHash,
            type: (type as any) || 'email',
          });
          if (error) setError(error.message);
          else redirectSoon();
        }
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    handleVerification();
    return () => subscription.unsubscribe();
  }, [searchParams, supabase, router]);

  return (
    <div className="glass w-full max-w-md rounded-card p-8 shadow-card animate-fade-up">
      <p className="section-label mb-2">Almost there</p>
      <h1 className="font-display text-2xl font-bold tracking-tight mb-4">Email verification</h1>

      {loading && (
        <div className="space-y-2.5" aria-hidden="true">
          <div className="skeleton h-4 w-3/4" />
          <div className="skeleton h-4 w-1/2" />
        </div>
      )}

      {message && (
        <div className="rounded-lg border border-success/25 bg-success/10 px-4 py-3 text-sm text-success">
          {message}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-danger/25 bg-danger/10 px-4 py-3 text-sm text-danger">
          <p>{error}</p>
          <button
            onClick={() => router.push('/auth')}
            className="mt-2 text-sm underline hover:no-underline"
          >
            Back to login
          </button>
        </div>
      )}

      {!loading && !message && !error && (
        <p className="text-sm text-muted">
          Check your email for a verification link. Click it to complete signup.
        </p>
      )}
    </div>
  );
}

export default function VerifyPage() {
  return (
    <div className="bg-grid relative flex min-h-screen items-center justify-center px-4">
      <div className="pointer-events-none absolute -top-24 left-1/2 h-72 w-[560px] -translate-x-1/2 rounded-full bg-accent/10 blur-3xl" />
      <Suspense fallback={<div className="skeleton h-40 w-full max-w-md" aria-hidden="true" />}>
        <VerifyContent />
      </Suspense>
    </div>
  );
}
