'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { AnimatePresence, m } from 'framer-motion';
import Stamp from '@/components/ui/Stamp';
import { createClient } from '@/utils/supabase';
import { apiClient } from '@/utils/api';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { Alert } from '@/components/ui-feedback';
import PasswordChecklist, { passwordMeetsRequirements } from '@/components/auth/PasswordChecklist';
import PasswordInput from '@/components/auth/PasswordInput';
import UsernameField from '@/components/auth/UsernameField';

// Soft, client-side throttle on repeated failed sign-ins. This is a UX-layer
// deterrent, not the real security boundary — Supabase Auth applies its own
// project-level rate limits server-side regardless of this. It just avoids
// letting someone hammer the submit button in a tight loop from this tab.
// Generous on purpose (a typo or two shouldn't feel like a threat): the
// remaining-attempts hint only appears from the 3rd failure, in a neutral
// tone, and turns red only on the last attempt.
const MAX_ATTEMPTS_BEFORE_LOCKOUT = 8;
const WARN_AFTER_FAILED_ATTEMPTS = 3;
const BASE_LOCKOUT_SECONDS = 30;
const MAX_LOCKOUT_SECONDS = 300;

const TRUST_POINTS = [
  { text: 'A model that is yours — trained on your own labels.' },
  { text: 'Chinese merchant text, segmented and shown in English.' },
  { text: 'Private per account — nothing shared.' },
];

type Mode = 'signin' | 'signup' | 'forgot';

export default function AuthClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const supabase = createClient();

  const [mode, setMode] = useState<Mode>(searchParams.get('mode') === 'signup' ? 'signup' : 'signin');
  const [identifier, setIdentifier] = useState(''); // sign-in: email or username
  const [email, setEmail] = useState(''); // sign-up / forgot-password: email only
  const [username, setUsername] = useState('');
  const [usernameAvailable, setUsernameAvailable] = useState(false);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const [failedAttempts, setFailedAttempts] = useState(0);
  const [lockoutCount, setLockoutCount] = useState(0);
  const [lockedUntil, setLockedUntil] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());

  const isSignup = mode === 'signup';
  const confirmMismatch = isSignup && confirmPassword.length > 0 && password !== confirmPassword;
  const canSubmitSignup =
    !!email &&
    usernameAvailable &&
    passwordMeetsRequirements(password) &&
    password === confirmPassword &&
    agreedToTerms;

  const lockRemainingSeconds = lockedUntil ? Math.max(0, Math.ceil((lockedUntil - now) / 1000)) : 0;
  const isLocked = lockRemainingSeconds > 0;

  useEffect(() => {
    if (!lockedUntil) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [lockedUntil]);

  useEffect(() => {
    if (lockedUntil && now >= lockedUntil) setLockedUntil(null);
  }, [now, lockedUntil]);

  const recordFailedSignin = () => {
    const attempts = failedAttempts + 1;
    if (attempts >= MAX_ATTEMPTS_BEFORE_LOCKOUT) {
      const seconds = Math.min(BASE_LOCKOUT_SECONDS * 2 ** lockoutCount, MAX_LOCKOUT_SECONDS);
      // `now` only ticks while locked, so refresh it here — otherwise the
      // first second shows 30s + however long since it last ticked.
      const t = Date.now();
      setNow(t);
      setLockedUntil(t + seconds * 1000);
      setLockoutCount((c) => c + 1);
      setFailedAttempts(0);
    } else {
      setFailedAttempts(attempts);
    }
  };

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');

    if (!isSignup && isLocked) return;

    setLoading(true);

    try {
      if (isSignup) {
        const { error: signupError } = await supabase.auth.signUp({
          email: email.trim(),
          password,
          options: {
            data: { username: username.trim() },
            emailRedirectTo: `${window.location.origin}/auth/verify`,
          },
        });

        if (signupError) {
          setError(signupError.message);
        } else {
          setMessage('Check your email to confirm your account');
          setTimeout(() => router.push('/auth/verify'), 2000);
        }
      } else {
        const trimmedIdentifier = identifier.trim();
        let resolvedEmail = trimmedIdentifier;
        if (!trimmedIdentifier.includes('@')) {
          // Routed through the backend (not a direct Supabase RPC): the RPC's
          // anon grant was revoked after it was found to let anyone harvest
          // any username's real email address. This endpoint is rate-limited
          // and public (no session yet at this point in the login flow).
          const { data } = await apiClient.post('/auth/resolve-identifier', {
            identifier: trimmedIdentifier,
          });
          resolvedEmail = data.email || trimmedIdentifier;
        }

        const { data, error: loginError } = await supabase.auth.signInWithPassword({
          email: resolvedEmail,
          password,
        });

        if (loginError) {
          setError(loginError.message);
          recordFailedSignin();
        } else if (data.user) {
          setFailedAttempts(0);
          setLockoutCount(0);
          setLockedUntil(null);
          router.push('/dashboard');
        }
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);

    try {
      const { error: resetError } = await supabase.auth.resetPasswordForEmail(email.trim(), {
        redirectTo: `${window.location.origin}/auth/verify`,
      });
      if (resetError) {
        setError(resetError.message);
      } else {
        setMessage('Check your email for a password reset link');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const switchMode = (next: Mode) => {
    setMode(next);
    setError('');
    setMessage('');
  };

  return (
    <div className="relative grid min-h-screen lg:grid-cols-2">
      {/* Mobile-only logo, pinned to the top so it doesn't drift with the
          centered form's height (sign-up has more inputs than sign-in). The
          desktop logo lives in the brand panel below. */}
      <Link href="/" className="absolute left-4 top-5 z-10 font-display text-xl font-medium sm:left-8 lg:hidden">
        Financing<span className="text-accent">.</span>
      </Link>

      {/* Brand panel — a darker paper well with a short stamped statement */}
      <div className="hidden flex-col bg-surface-2 p-10 lg:flex xl:p-14 2xl:p-20">
        <Link href="/" className="font-display text-xl font-medium">
          Financing<span className="text-accent">.</span>
        </Link>
        <div className="flex flex-1 flex-col justify-center">
          <h1 className="max-w-[12ch] font-display text-5xl font-normal leading-[1.02] tracking-[-0.025em] xl:text-6xl 2xl:text-7xl">
            Every yuan, <span className="italic">accounted for.</span>
          </h1>
          <div className="mt-10 max-w-md border-y border-ink/80">
            {[
              ['Luckin Coffee', '18.50', 'Food', -3],
              ['Didi Chuxing', '32.40', 'Transport', 2],
              ['Hema Fresh', '212.60', 'Groceries', -1.5],
            ].map(([merchant, amount, cat, tilt], i) => (
              <div key={merchant as string} className="flex items-center gap-4 border-t border-edge/12 py-3 text-sm first:border-t-0">
                <span className="flex-1 font-medium">{merchant}</span>
                <span className="num">¥{amount}</span>
                <span className="w-28">
                  <Stamp label={cat as string} tilt={tilt as number} delay={0.5 + i * 0.25} />
                </span>
              </div>
            ))}
          </div>
          <ul className="mt-8 max-w-md space-y-2 text-sm text-muted xl:text-[15px]">
            {TRUST_POINTS.map(({ text }) => (
              <li key={text}>{text}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center px-4 py-20 sm:px-8 xl:px-12">
        <m.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          className="w-full max-w-sm"
        >
          {mode !== 'forgot' && (
            <div className="mb-8 flex gap-6 border-b border-edge/12" role="tablist" aria-label="Sign in or create account">
              {[
                { tabMode: 'signin' as Mode, label: 'Sign in' },
                { tabMode: 'signup' as Mode, label: 'Create account' },
              ].map(({ tabMode, label }) => (
                <button
                  key={label}
                  role="tab"
                  aria-selected={mode === tabMode}
                  onClick={() => switchMode(tabMode)}
                  className={`relative -mb-px pb-2.5 text-sm transition-colors ${
                    mode === tabMode ? 'text-ink font-medium' : 'text-muted hover:text-ink'
                  }`}
                >
                  {mode === tabMode && (
                    <m.span
                      layoutId="auth-mode"
                      className="absolute inset-x-0 bottom-0 h-[2px] bg-accent"
                      transition={{ type: 'spring', bounce: 0, duration: 0.3 }}
                    />
                  )}
                  <span className="relative">{label}</span>
                </button>
              ))}
            </div>
          )}

          <h2 className="font-display text-[2rem] font-normal leading-tight tracking-[-0.015em]">
            {mode === 'signup' ? 'Create your account' : mode === 'forgot' ? 'Reset your password' : 'Welcome back'}
          </h2>
          <p className="mt-1.5 mb-7 text-sm text-muted">
            {mode === 'signup'
              ? 'Free to start. You only need an email and a username.'
              : mode === 'forgot'
              ? "Enter your email and we'll send you a reset link."
              : 'Sign in to pick up where you left off.'}
          </p>

          {mode === 'forgot' ? (
            <form onSubmit={handleForgotPassword} className="space-y-4">
              <Input
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@example.com"
                autoComplete="email"
              />

              {error && <Alert kind="error">{error}</Alert>}
              {message && <Alert kind="success">{message}</Alert>}

              <Button type="submit" loading={loading} className="w-full" size="lg">
                Send reset link
              </Button>
              <button
                type="button"
                onClick={() => switchMode('signin')}
                className="w-full text-center text-sm text-muted transition-colors hover:text-ink"
              >
                Back to sign in
              </button>
            </form>
          ) : (
            <form onSubmit={handleAuth} className="space-y-4">
              {isSignup ? (
                <>
                  <Input
                    label="Email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    placeholder="you@example.com"
                    autoComplete="email"
                  />
                  <UsernameField
                    value={username}
                    onChange={setUsername}
                    onAvailabilityChange={setUsernameAvailable}
                  />
                </>
              ) : (
                <Input
                  label="Email or username"
                  type="text"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  required
                  placeholder="you@example.com or username"
                  autoComplete="username"
                />
              )}

              <div>
                <PasswordInput
                  label="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder={isSignup ? 'Create a password' : 'Your password'}
                  autoComplete={isSignup ? 'new-password' : 'current-password'}
                />
                {!isSignup && (
                  <button
                    type="button"
                    onClick={() => switchMode('forgot')}
                    className="mt-1.5 text-xs text-muted transition-colors hover:text-ink"
                  >
                    Forgot password?
                  </button>
                )}
                {isSignup && (
                  <div className="mt-2">
                    <PasswordChecklist password={password} />
                  </div>
                )}
                {!isSignup && failedAttempts >= WARN_AFTER_FAILED_ATTEMPTS && !isLocked && (() => {
                  const left = MAX_ATTEMPTS_BEFORE_LOCKOUT - failedAttempts;
                  return (
                    <p className={`mt-1.5 text-xs ${left === 1 ? 'text-danger' : 'text-muted'}`}>
                      {left} attempt{left === 1 ? '' : 's'} left before a short pause.
                    </p>
                  );
                })()}
              </div>

              <AnimatePresence initial={false}>
                {isSignup && (
                  <m.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.25, ease: 'easeOut' }}
                    className="overflow-hidden"
                  >
                    <PasswordInput
                      label="Confirm password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required={isSignup}
                      placeholder="Repeat your password"
                      autoComplete="new-password"
                      error={confirmMismatch ? 'Passwords do not match' : undefined}
                    />
                  </m.div>
                )}
              </AnimatePresence>

              {isSignup && (
                <label className="flex items-start gap-2.5 text-sm text-muted">
                  <input
                    type="checkbox"
                    checked={agreedToTerms}
                    onChange={(e) => setAgreedToTerms(e.target.checked)}
                    required
                    className="mt-0.5 h-4 w-4 shrink-0 rounded border-edge/30 accent-accent-strong"
                  />
                  <span>
                    I agree to the{' '}
                    <Link href="/terms" target="_blank" className="text-ink underline hover:no-underline">
                      Terms &amp; Conditions
                    </Link>{' '}
                    and{' '}
                    <Link href="/privacy" target="_blank" className="text-ink underline hover:no-underline">
                      Privacy Policy
                    </Link>
                  </span>
                </label>
              )}

              {!isSignup && isLocked && (
                <Alert kind="error">
                  Too many failed attempts. Try again in {lockRemainingSeconds}s.
                </Alert>
              )}
              {error && <Alert kind="error">{error}</Alert>}
              {message && <Alert kind="success">{message}</Alert>}

              <Button
                type="submit"
                loading={loading}
                disabled={isSignup ? !canSubmitSignup : isLocked}
                className="w-full"
                size="lg"
              >
                {isSignup ? 'Create account' : isLocked ? `Try again in ${lockRemainingSeconds}s` : 'Sign in'}
              </Button>
            </form>
          )}
        </m.div>
      </div>
    </div>
  );
}
