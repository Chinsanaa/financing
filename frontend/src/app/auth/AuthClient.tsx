'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { AnimatePresence, motion } from 'framer-motion';
import { createClient } from '@/utils/supabase';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { Alert } from '@/components/ui';

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
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Brand panel */}
      <div className="bg-grid relative hidden flex-col justify-between overflow-hidden p-10 lg:flex">
        <div className="pointer-events-none absolute -bottom-32 -left-24 h-96 w-96 rounded-full bg-accent/10 blur-3xl animate-glow-pulse" />
        <Link href="/" className="relative font-display text-lg font-bold tracking-tight">
          Financing<span className="text-accent-strong">.</span>
        </Link>
        <div className="relative">
          <h1 className="font-display text-5xl font-bold leading-[1.08] tracking-tight">
            Your money,
            <br />
            <span className="text-accent-strong">decoded</span>.
          </h1>
          <p className="mt-5 max-w-sm text-muted">
            One personal model, trained on your own labels, sorting every Alipay and
            WeChat transaction for you.
          </p>
        </div>
        <svg viewBox="0 0 400 80" className="relative w-full max-w-md opacity-60" aria-hidden="true">
          <polyline
            points="0,60 50,48 100,54 150,34 200,42 250,22 300,30 350,12 400,20"
            fill="none"
            stroke="rgb(var(--accent))"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center px-4 py-16 sm:px-8">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
          className="w-full max-w-sm"
        >
          <Link href="/" className="mb-8 block font-display text-lg font-bold tracking-tight lg:hidden">
            Financing<span className="text-accent-strong">.</span>
          </Link>

          {/* Mode toggle */}
          <div className="mb-8 inline-flex rounded-pill bg-surface-2 p-1">
            {[
              { signup: false, label: 'Sign in' },
              { signup: true, label: 'Create account' },
            ].map(({ signup, label }) => (
              <button
                key={label}
                onClick={() => switchMode(signup)}
                className={`relative rounded-pill px-4 py-1.5 text-sm transition-colors ${
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
