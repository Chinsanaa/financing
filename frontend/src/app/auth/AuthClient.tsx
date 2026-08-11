'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { AnimatePresence, motion } from 'framer-motion';
import { BrainCircuit, Languages, ShieldCheck } from 'lucide-react';
import { createClient } from '@/utils/supabase';
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
const MAX_ATTEMPTS_BEFORE_LOCKOUT = 5;
const BASE_LOCKOUT_SECONDS = 30;
const MAX_LOCKOUT_SECONDS = 300;

const TRUST_POINTS = [
  { icon: BrainCircuit, text: 'A model that is yours — trained on your own labels.' },
  { icon: Languages, text: 'Bilingual by design — mixed Chinese and English, understood.' },
  { icon: ShieldCheck, text: 'Private per user — nothing shared across accounts.' },
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
      setLockedUntil(Date.now() + seconds * 1000);
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
          const { data } = await supabase.rpc('get_email_for_username', {
            check_username: trimmedIdentifier,
          });
          resolvedEmail = data || trimmedIdentifier;
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
      <Link
        href="/"
        className="absolute left-4 top-4 z-10 font-display text-lg font-bold tracking-tight sm:left-8 lg:hidden"
      >
        Financing<span className="text-accent-strong">.</span>
      </Link>

      {/* Brand panel */}
      <div className="bg-grid relative hidden flex-col overflow-hidden p-10 lg:flex xl:p-14 2xl:p-20">
        <div className="pointer-events-none absolute -bottom-32 -left-24 h-96 w-96 rounded-full bg-accent/10 blur-3xl animate-glow-pulse" />
        <Link href="/" className="relative font-display text-lg font-bold tracking-tight">
          Financing<span className="text-accent-strong">.</span>
        </Link>
        {/* Centered in the remaining height, not spread edge-to-edge — a
            fixed-height block here (vs. justify-between) is what stopped
            this panel reading as empty on tall/wide desktop viewports. */}
        <div className="relative flex flex-1 flex-col justify-center">
          <h1 className="font-display text-5xl font-bold leading-[1.08] tracking-tight xl:text-6xl 2xl:text-7xl">
            Your money,
            <br />
            <span className="text-accent-strong">decoded</span>.
          </h1>
          <p className="mt-5 max-w-md text-muted xl:max-w-lg xl:text-lg">
            One personal model, trained on your own labels, sorting every Alipay and
            WeChat transaction for you.
          </p>
          <ul className="mt-8 space-y-3">
            {TRUST_POINTS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-start gap-3 text-sm text-muted xl:text-base">
                <Icon className="mt-0.5 h-4 w-4 shrink-0 text-accent-strong" aria-hidden="true" />
                <span className="max-w-md">{text}</span>
              </li>
            ))}
          </ul>
          <svg viewBox="0 0 400 80" className="relative mt-10 w-full max-w-lg opacity-60 xl:max-w-xl" aria-hidden="true">
            <polyline
              points="0,60 50,48 100,54 150,34 200,42 250,22 300,30 350,12 400,20"
              fill="none"
              stroke="rgb(var(--accent))"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
        </div>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center px-4 py-16 sm:px-8 xl:px-12">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
          className="w-full max-w-sm lg:max-w-md"
        >
          {mode !== 'forgot' && (
            <div className="mb-8 inline-flex rounded-pill bg-surface-2 p-1" role="tablist" aria-label="Sign in or create account">
              {[
                { m: 'signin' as Mode, label: 'Sign in' },
                { m: 'signup' as Mode, label: 'Create account' },
              ].map(({ m, label }) => (
                <button
                  key={label}
                  role="tab"
                  aria-selected={mode === m}
                  onClick={() => switchMode(m)}
                  className={`relative rounded-pill px-4 py-1.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 ${
                    mode === m ? 'text-ink font-medium' : 'text-muted hover:text-ink'
                  }`}
                >
                  {mode === m && (
                    <motion.span
                      layoutId="auth-mode"
                      className="absolute inset-0 rounded-pill bg-surface border border-edge/10 shadow-card"
                      transition={{ type: 'spring', stiffness: 500, damping: 40 }}
                    />
                  )}
                  <span className="relative">{label}</span>
                </button>
              ))}
            </div>
          )}

          <h2 className="font-display text-2xl font-bold tracking-tight">
            {mode === 'signup' ? 'Start decoding your spending' : mode === 'forgot' ? 'Reset your password' : 'Welcome back'}
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
                {!isSignup && failedAttempts > 0 && !isLocked && (
                  <p className="mt-1.5 text-xs text-danger">
                    {MAX_ATTEMPTS_BEFORE_LOCKOUT - failedAttempts} attempt
                    {MAX_ATTEMPTS_BEFORE_LOCKOUT - failedAttempts === 1 ? '' : 's'} remaining
                    before a temporary lockout.
                  </p>
                )}
              </div>

              <AnimatePresence initial={false}>
                {isSignup && (
                  <motion.div
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
                  </motion.div>
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
        </motion.div>
      </div>
    </div>
  );
}
