'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Bell, Download, FileText, ScrollText } from 'lucide-react';
import { invalidate } from '@/utils/useApi';
import type { FxCurrency } from '@/types/v5';
import { createClient } from '@/utils/supabase';
import { api } from '@/utils/api';
import { formatDate } from '@/utils/format';
import { Alert } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import Input, { Select } from '@/components/ui/Input';
import Switch from '@/components/ui/Switch';
import { SkeletonCard } from '@/components/ui/Skeleton';
import PasswordChecklist, { passwordMeetsRequirements } from '@/components/auth/PasswordChecklist';
import PasswordInput from '@/components/auth/PasswordInput';
import { errorDetail } from '@/utils/errors';
import { downloadTransactionsXlsx } from '@/utils/download';

interface Profile {
  id: string;
  username: string | null;
  email_verified_at: string;
  onboarding_phase: string;
  created_at: string;
  alert_email_enabled: boolean;
  alert_threshold_pct: number;
  budget_inapp_enabled: boolean;
  pending_review_inapp_enabled: boolean;
  monthly_overview_email_enabled: boolean;
  home_currency?: string | null;
}

/** FastAPI error detail → one readable line (422s may carry a list). */

export default function SettingsClient() {
  const router = useRouter();
  const supabase = createClient();

  const [user, setUser] = useState<any>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const deleteConfirmRef = useRef<HTMLDivElement>(null);

  const [exporting, setExporting] = useState(false);

  const [alertEmailEnabled, setAlertEmailEnabled] = useState(false);
  const [alertThresholdPct, setAlertThresholdPct] = useState(80);
  const [budgetInappEnabled, setBudgetInappEnabled] = useState(true);
  const [pendingReviewInappEnabled, setPendingReviewInappEnabled] = useState(true);
  const [monthlyOverviewEmailEnabled, setMonthlyOverviewEmailEnabled] = useState(false);
  const [alertSaving, setAlertSaving] = useState(false);
  const [alertError, setAlertError] = useState('');
  const [alertSuccess, setAlertSuccess] = useState('');

  // Home currency (v5): '' = none, CNY only.
  const [currencies, setCurrencies] = useState<FxCurrency[]>([]);
  const [currenciesError, setCurrenciesError] = useState('');
  const [homeCurrency, setHomeCurrency] = useState('');
  const [savedHomeCurrency, setSavedHomeCurrency] = useState('');
  const [homeSaving, setHomeSaving] = useState(false);
  const [homeError, setHomeError] = useState('');
  const [homeSuccess, setHomeSuccess] = useState('');

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const confirmPasswordMismatch = confirmPassword.length > 0 && newPassword !== confirmPassword;

  useEffect(() => {
    if (deleteConfirm) deleteConfirmRef.current?.focus();
  }, [deleteConfirm]);

  useEffect(() => {
    const checkAuth = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        router.push('/auth');
        return;
      }

      setUser(session.user);

      // Load profile (the api client attaches the auth token itself)
      try {
        const res = await api.get('/settings/profile');
        setProfile(res.data.profile);
        setAlertEmailEnabled(!!res.data.profile.alert_email_enabled);
        setAlertThresholdPct(res.data.profile.alert_threshold_pct ?? 80);
        setBudgetInappEnabled(res.data.profile.budget_inapp_enabled ?? true);
        setPendingReviewInappEnabled(res.data.profile.pending_review_inapp_enabled ?? true);
        setMonthlyOverviewEmailEnabled(!!res.data.profile.monthly_overview_email_enabled);
        setHomeCurrency(res.data.profile.home_currency || '');
        setSavedHomeCurrency(res.data.profile.home_currency || '');
      } catch (err: any) {
        setError(errorDetail(err, 'Failed to load profile'));
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
    api.fx
      .currencies()
      .then((res) => setCurrencies(res.data.supported || []))
      .catch((err) => setCurrenciesError(errorDetail(err, "Couldn't load the currency list")));
  }, [supabase, router]);

  const handleSaveHomeCurrency = async () => {
    setHomeSaving(true);
    setHomeError('');
    setHomeSuccess('');
    try {
      const res = await api.settings.setHomeCurrency(homeCurrency || null);
      const saved = res.data.profile?.home_currency || '';
      setHomeCurrency(saved);
      setSavedHomeCurrency(saved);
      // Every dashboard response carries *_home fields — refetch them.
      invalidate('/dashboard');
      invalidate('/settings/profile');
      setHomeSuccess(
        saved
          ? `Saved. Amounts will also show in ${saved} once rates have loaded.`
          : 'Saved. Amounts now show in CNY only.'
      );
    } catch (err: any) {
      setHomeError(errorDetail(err, "Couldn't save your home currency"));
    } finally {
      setHomeSaving(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await downloadTransactionsXlsx();
    } catch (err) {
      setError(errorDetail(err, 'Failed to export data'));
    } finally {
      setExporting(false);
    }
  };

  const handleSaveNotificationPreferences = async () => {
    setAlertSaving(true);
    setAlertError('');
    setAlertSuccess('');
    try {
      await api.patch('/settings/profile', {
        alert_email_enabled: alertEmailEnabled,
        alert_threshold_pct: alertThresholdPct,
        budget_inapp_enabled: budgetInappEnabled,
        pending_review_inapp_enabled: pendingReviewInappEnabled,
        monthly_overview_email_enabled: monthlyOverviewEmailEnabled,
      });
      setAlertSuccess('Notification preferences saved');
    } catch (err: any) {
      setAlertError(errorDetail(err, 'Failed to save notification preferences'));
    } finally {
      setAlertSaving(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError('');
    setPasswordSuccess('');

    if (!currentPassword) {
      setPasswordError('Enter your current password');
      return;
    }
    if (!passwordMeetsRequirements(newPassword)) {
      setPasswordError('Password does not meet the requirements below');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match');
      return;
    }

    setPasswordSaving(true);
    try {
      // Re-verify the current password before changing it — a bare access
      // token alone used to be enough to change a password with no re-auth
      // check. signInWithPassword re-establishes a fresh session on success
      // and fails without one, so this doubles as the re-auth step.
      if (!user?.email) throw new Error('Missing account email; try reloading the page');
      const { error: reauthError } = await supabase.auth.signInWithPassword({
        email: user.email,
        password: currentPassword,
      });
      if (reauthError) {
        setPasswordError('Current password is incorrect');
        return;
      }

      const { error: updateError } = await supabase.auth.updateUser({ password: newPassword });
      if (updateError) throw updateError;
      setPasswordSuccess('Password updated successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setPasswordError(err.message || 'Failed to update password');
    } finally {
      setPasswordSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!deleteConfirm) {
      setDeleteConfirm(true);
      return;
    }

    setDeleting(true);
    setError('');

    try {
      await api.delete('/settings/account');

      // Sign out and redirect
      await supabase.auth.signOut();
      router.push('/');
    } catch (err: any) {
      setError(errorDetail(err, 'Failed to delete account'));
      setDeleting(false);
      setDeleteConfirm(false);
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl space-y-6 px-4 py-12 sm:px-6 lg:px-8 xl:px-10">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  return (
    <div className="relative min-h-screen">
      <header className="sticky top-0 z-40 border-b border-edge/8 bg-bg">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8 xl:px-10">
          <h1 className="font-display text-lg font-medium tracking-[-0.015em]">Settings</h1>
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" /> Back
          </Button>
        </div>
      </header>

      {/* stagger-in: section cards cascade in on load */}
      <div className="stagger-in relative z-[1] mx-auto max-w-3xl space-y-6 px-4 py-8 sm:px-6 lg:px-8 xl:px-10">
        <Card className="p-6">
          <SectionHeader title="Account" />
          <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
          <span
            aria-hidden="true"
            className="flex h-14 w-14 shrink-0 items-center justify-center rounded-md bg-ink font-display text-2xl text-bg"
          >
            {(profile?.username || user?.email || '?').charAt(0).toUpperCase()}
          </span>
          <div className="grid flex-1 gap-4 sm:grid-cols-3">
            <div>
              <p className="section-label mb-0.5">Username</p>
              <p className="text-sm font-medium">{profile?.username || '—'}</p>
            </div>
            <div className="min-w-0">
              <p className="section-label mb-0.5">Email</p>
              <p className="truncate text-sm font-medium" title={user?.email}>{user?.email}</p>
            </div>
            <div>
              <p className="section-label mb-0.5">Account created</p>
              <p className="text-sm font-medium">
                {profile?.created_at ? formatDate(profile.created_at) : '—'}
              </p>
            </div>
          </div>
          </div>
        </Card>

        <Card className="p-6">
          <SectionHeader title="Home currency" />
          <div className="space-y-4">
            <p className="text-sm text-muted">
              Everything stays in CNY. Pick the currency you think in and an approximate amount is
              shown underneath, e.g. &ldquo;&yen;100 &asymp; $13.87&rdquo;.
            </p>
            <div className="max-w-[320px]">
              <Select
                label="Also show amounts in"
                value={homeCurrency}
                onChange={(e) => {
                  setHomeCurrency(e.target.value);
                  setHomeError('');
                  setHomeSuccess('');
                }}
              >
                <option value="">None (CNY only)</option>
                {/* Keep a saved code selectable even if the list failed to load. */}
                {homeCurrency && !currencies.some((c) => c.code === homeCurrency) && (
                  <option value={homeCurrency}>{homeCurrency}</option>
                )}
                {currencies.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.code} — {c.name}
                  </option>
                ))}
              </Select>
            </div>
            <p className="text-[13px] text-muted">
              Amounts are converted with European Central Bank reference rates on each
              transaction&apos;s date (via Frankfurter). Rates update in the background — the first
              conversion can take a minute.
            </p>
            {currenciesError && <Alert kind="error">{currenciesError}</Alert>}
            {homeError && <Alert kind="error">{homeError}</Alert>}
            {homeSuccess && <Alert kind="success">{homeSuccess}</Alert>}
            <Button
              variant="outline"
              onClick={handleSaveHomeCurrency}
              loading={homeSaving}
              disabled={homeSaving || homeCurrency === savedHomeCurrency}
            >
              {homeSaving ? 'Saving' : 'Save home currency'}
            </Button>
          </div>
        </Card>

        <Card className="p-6">
          <SectionHeader title="Notification preferences" />
          <div className="space-y-6">
            <div className="space-y-3">
              <p className="text-sm font-semibold text-ink">Budget alerts</p>
              <p className="text-sm text-muted">
                When a category goes over budget, or crosses your chosen
                "approaching budget" threshold. Checked when you use the app
                (upload, review, label) — not a continuous background check.
              </p>
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-ink">Show in the notification bell</span>
                <Switch
                  checked={budgetInappEnabled}
                  onChange={setBudgetInappEnabled}
                  label="Show budget alerts in the notification bell"
                />
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-ink">Email me budget alerts</span>
                <Switch
                  checked={alertEmailEnabled}
                  onChange={setAlertEmailEnabled}
                  label="Email me budget alerts"
                />
              </div>
              <div className="max-w-[180px]">
                <Input
                  type="number"
                  label="Approaching-budget threshold (%)"
                  min={0}
                  max={100}
                  value={alertThresholdPct}
                  onChange={(e) => setAlertThresholdPct(Number(e.target.value))}
                  disabled={!alertEmailEnabled && !budgetInappEnabled}
                />
              </div>
            </div>

            <div className="space-y-3 border-t border-edge/8 pt-6">
              <p className="text-sm font-semibold text-ink">Pending review reminders</p>
              <p className="text-sm text-muted">
                A reminder when transactions are waiting in your review queue.
              </p>
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-ink">Show in the notification bell</span>
                <Switch
                  checked={pendingReviewInappEnabled}
                  onChange={setPendingReviewInappEnabled}
                  label="Show pending review reminders in the notification bell"
                />
              </div>
            </div>

            <div className="space-y-3 border-t border-edge/8 pt-6">
              <p className="text-sm font-semibold text-ink">Monthly spending overview</p>
              <p className="text-sm text-muted">
                A monthly email summarizing your spending. This feature hasn't
                shipped yet — your preference is saved now so we can start
                sending these as soon as it does.
              </p>
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-ink">Email me a monthly overview</span>
                <Switch
                  checked={monthlyOverviewEmailEnabled}
                  onChange={setMonthlyOverviewEmailEnabled}
                  label="Email me a monthly spending overview"
                />
              </div>
            </div>

            {alertError && <Alert kind="error">{alertError}</Alert>}
            {alertSuccess && <Alert kind="success">{alertSuccess}</Alert>}

            <Button variant="outline" onClick={handleSaveNotificationPreferences} loading={alertSaving}>
              <Bell className="h-4 w-4" />
              {alertSaving ? 'Saving' : 'Save notification preferences'}
            </Button>
          </div>
        </Card>

        <Card className="p-6">
          <SectionHeader title="Export your data" />
          <div className="space-y-4">
            <p className="text-sm text-muted">
              Download your categorized transaction history as an Excel spreadsheet.
            </p>
            {error && <Alert kind="error">{error}</Alert>}
            <Button variant="outline" onClick={handleExport} loading={exporting}>
              <Download className="h-4 w-4" />
              {exporting ? 'Exporting' : 'Export transactions (.xlsx)'}
            </Button>
          </div>
        </Card>

        <Card className="p-6">
          <SectionHeader title="Change password" />
          <form onSubmit={handleChangePassword} className="space-y-4">
            <PasswordInput
              label="Current password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder="Enter your current password"
              autoComplete="current-password"
            />
            <div>
              <PasswordInput
                label="New password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
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
              placeholder="Re-enter new password"
              autoComplete="new-password"
              error={confirmPasswordMismatch ? 'Passwords do not match' : undefined}
            />

            {passwordError && <Alert kind="error">{passwordError}</Alert>}
            {passwordSuccess && <Alert kind="success">{passwordSuccess}</Alert>}

            <Button
              type="submit"
              loading={passwordSaving}
              disabled={
                !currentPassword ||
                !passwordMeetsRequirements(newPassword) ||
                newPassword !== confirmPassword
              }
            >
              {passwordSaving ? 'Saving' : 'Update password'}
            </Button>
          </form>
        </Card>

        <Card className="p-6">
          <SectionHeader title="Policies" />
          <div className="space-y-3">
            <Link
              href="/privacy"
              className="flex items-center gap-2.5 text-sm font-medium text-ink underline decoration-edge/30 underline-offset-4 transition-colors hover:decoration-accent"
            >
              <FileText className="h-4 w-4 text-muted" /> Privacy Policy
            </Link>
            <Link
              href="/terms"
              className="flex items-center gap-2.5 text-sm font-medium text-ink underline decoration-edge/30 underline-offset-4 transition-colors hover:decoration-accent"
            >
              <ScrollText className="h-4 w-4 text-muted" /> Terms &amp; Conditions
            </Link>
          </div>
        </Card>

        <Card className="border-danger/25 p-6">
          <SectionHeader title="Danger zone" />
          <div className="space-y-4">
            <p className="text-sm text-muted">
              Deleting your account will permanently remove all your data, transactions, and
              models. This action cannot be undone.
            </p>

            {deleteConfirm ? (
              <div
                ref={deleteConfirmRef}
                role="alert"
                tabIndex={-1}
                className="space-y-3 rounded-lg border border-danger/30 bg-danger/5 p-4 focus:outline-none"
              >
                <p className="text-sm font-semibold text-danger">Are you absolutely sure?</p>
                <p className="text-sm text-muted">
                  All transactions, categories, and trained models will be permanently deleted.
                </p>
                <div className="flex gap-3">
                  <Button
                    variant="danger"
                    onClick={handleDeleteAccount}
                    loading={deleting}
                  >
                    {deleting ? 'Deleting' : 'Yes, delete everything'}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => setDeleteConfirm(false)}
                    disabled={deleting}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <Button variant="danger" onClick={handleDeleteAccount}>
                Delete account
              </Button>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
