'use client';

import { Suspense, useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { createClient } from '@/utils/supabase';
import Button from '@/components/ui/Button';
import { Alert } from '@/components/ui-feedback';
import PasswordChecklist, { passwordMeetsRequirements } from '@/components/auth/PasswordChecklist';
import PasswordInput from '@/components/auth/PasswordInput';

/**
 * Handles every redirect shape Supabase email links actually use:
 * - PKCE flow (default with @supabase/ssr): `?code=...` → exchangeCodeForSession
 * - Token-hash links: `?token_hash=...&type=...` → verifyOtp
 * - Legacy `?token=...&type=email` → verifyOtp
 * - Implicit flow: `#access_token=...` fragment → onAuthStateChange fires
 * - Error redirects: `?error_description=...` → surfaced to the user
 *
 * `type=recovery` (password reset links) is handled specially: instead of
 * redirecting straight to the dashboard once the session is established, we
 * show a "set a new password" form — the whole point of a reset link.
 */
function VerifyContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [supabase] = useState(() => createClient());

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [recoveryReady, setRecoveryReady] = useState(false);

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [settingPassword, setSettingPassword] = useState(false);

  useEffect(() => {
    const isRecovery = searchParams.get('type') === 'recovery';

    const redirectSoon = () => {
      setMessage('Email verified! Redirecting...');
      setTimeout(() => router.push('/dashboard'), 1500);
    };

    // Implicit-flow links put the session in the URL hash; the client
    // consumes it automatically and fires SIGNED_IN (also fires for
    // PASSWORD_RECOVERY on some Supabase versions, hence the extra check).
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'PASSWORD_RECOVERY' || (event === 'SIGNED_IN' && isRecovery)) {
        setRecoveryReady(true);
      } else if (event === 'SIGNED_IN') {
        redirectSoon();
      }
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
          else if (isRecovery) setRecoveryReady(true);
          else redirectSoon();
        } else if (tokenHash) {
          const { error } = await supabase.auth.verifyOtp({
            token_hash: tokenHash,
            type: (type as any) || 'email',
          });
          if (error) setError(error.message);
          else if (isRecovery) setRecoveryReady(true);
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

  const confirmPasswordMismatch = confirmPassword.length > 0 && newPassword !== confirmPassword;

  const handleSetNewPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setSettingPassword(true);
    try {
      const { error: updateError } = await supabase.auth.updateUser({ password: newPassword });
      if (updateError) {
        setError(updateError.message);
      } else {
        setMessage('Password updated! Redirecting...');
        setRecoveryReady(false);
        setTimeout(() => router.push('/dashboard'), 1500);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSettingPassword(false);
    }
  };

  if (recoveryReady) {
    return (
      <div className="glass w-full max-w-md rounded-card p-8 shadow-card animate-fade-up">
        <p className="section-label mb-2">Almost there</p>
        <h1 className="font-display text-2xl font-bold tracking-tight mb-4">Set a new password</h1>

        <form onSubmit={handleSetNewPassword} className="space-y-4">
          <div>
            <PasswordInput
              label="New password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              placeholder="Create a new password"
              autoComplete="new-password"
            />
            <div className="mt-2">
              <PasswordChecklist password={newPassword} />
            </div>
          </div>
          <PasswordInput
            label="Confirm new password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            placeholder="Repeat your new password"
            autoComplete="new-password"
            error={confirmPasswordMismatch ? 'Passwords do not match' : undefined}
          />

          {error && <Alert kind="error">{error}</Alert>}
          {message && <Alert kind="success">{message}</Alert>}

          <Button
            type="submit"
            loading={settingPassword}
            disabled={!passwordMeetsRequirements(newPassword)}
            className="w-full"
          >
            Update password
          </Button>
        </form>
      </div>
    );
  }

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
