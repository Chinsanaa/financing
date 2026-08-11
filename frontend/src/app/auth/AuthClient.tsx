'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { AnimatePresence, motion } from 'framer-motion';
import { BrainCircuit, Languages, ShieldCheck } from 'lucide-react';
import { createClient } from '@/utils/supabase';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { Alert } from '@/components/ui-feedback';

const TRUST_POINTS = [
  { icon: BrainCircuit, text: 'A model that is yours — trained on your own labels.' },
  { icon: Languages, text: 'Bilingual by design — mixed Chinese and English, understood.' },
  { icon: ShieldCheck, text: 'Private per user — nothing shared across accounts.' },
];

export default function AuthClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const supabase = createClient();

  const [isSignup, setIsSignup] = useState(searchParams.get('mode') === 'signup');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const confirmMismatch =
    isSignup && confirmPassword.length > 0 && password !== confirmPassword;

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);

    try {
      if (isSignup) {
        if (password !== confirmPassword) {
          setError('Passwords do not match');
          setLoading(false);
          return;
        }

        const { error: signupError } = await supabase.auth.signUp({
          email,
          password,
          options: {
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
        const { data, error: loginError } = await supabase.auth.signInWithPassword({
          email,
          password,
        });

        if (loginError) {
          setError(loginError.message);
        } else if (data.user) {
          router.push('/dashboard');
        }
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const switchMode = (signup: boolean) => {
    setIsSignup(signup);
    setError('');
    setMessage('');
  };

  return (
    <div className="relative grid min-h-screen lg:grid-cols-2">
      {/* Mobile-only logo, pinned to the top so it doesn't drift with the
          centered form's height (sign-up has 3 inputs vs sign-in's 2). The
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
          {/* Mode toggle */}
          <div className="mb-8 inline-flex rounded-pill bg-surface-2 p-1" role="tablist" aria-label="Sign in or create account">
            {[
              { signup: false, label: 'Sign in' },
              { signup: true, label: 'Create account' },
            ].map(({ signup, label }) => (
              <button
                key={label}
                role="tab"
                aria-selected={isSignup === signup}
                onClick={() => switchMode(signup)}
                className={`relative rounded-pill px-4 py-1.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 ${
                  isSignup === signup ? 'text-ink font-medium' : 'text-muted hover:text-ink'
                }`}
              >
                {isSignup === signup && (
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

          <h2 className="font-display text-2xl font-bold tracking-tight">
            {isSignup ? 'Start decoding your spending' : 'Welcome back'}
          </h2>
          <p className="mt-1.5 mb-7 text-sm text-muted">
            {isSignup
              ? 'Free to start. You only need an email.'
              : 'Sign in to pick up where you left off.'}
          </p>

          <form onSubmit={handleAuth} className="space-y-4">
            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@example.com"
              autoComplete="email"
            />
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="At least 6 characters"
              autoComplete={isSignup ? 'new-password' : 'current-password'}
            />
            <AnimatePresence initial={false}>
              {isSignup && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.25, ease: 'easeOut' }}
                  className="overflow-hidden"
                >
                  <Input
                    label="Confirm password"
                    type="password"
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

            {error && <Alert kind="error">{error}</Alert>}
            {message && <Alert kind="success">{message}</Alert>}

            <Button type="submit" loading={loading} className="w-full" size="lg">
              {isSignup ? 'Create account' : 'Sign in'}
            </Button>
          </form>
        </motion.div>
      </div>
    </div>
  );
}
