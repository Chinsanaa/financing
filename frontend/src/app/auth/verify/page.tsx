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
    <div className="w-full max-w-md bg-white rounded-lg shadow-lg p-8">
      <h1 className="text-2xl font-bold mb-4">Email Verification</h1>

      {loading && <p className="text-gray-600">Verifying your email...</p>}

      {message && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
          {message}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
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
        <p className="text-gray-600">
          Check your email for a verification link. Click it to complete signup.
        </p>
      )}
    </div>
  );
}

export default function VerifyPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <Suspense fallback={<p className="text-gray-600">Loading...</p>}>
        <VerifyContent />
      </Suspense>
    </div>
  );
}
