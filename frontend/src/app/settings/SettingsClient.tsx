'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Bell, Download, FileText, ScrollText } from 'lucide-react';
import { createClient } from '@/utils/supabase';
import { api } from '@/utils/api';
import { Alert } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import Input from '@/components/ui/Input';
import { SkeletonCard } from '@/components/ui/Skeleton';
import PasswordChecklist, { passwordMeetsRequirements } from '@/components/auth/PasswordChecklist';
import PasswordInput from '@/components/auth/PasswordInput';

interface Profile {
  id: string;
  username: string | null;
  email_verified_at: string;
  onboarding_phase: string;
  created_at: string;
  alert_email_enabled: boolean;
  alert_threshold_pct: number;
}

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
  const [alertSaving, setAlertSaving] = useState(false);
  const [alertError, setAlertError] = useState('');
  const [alertSuccess, setAlertSuccess] = useState('');

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
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load profile');
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, [supabase, router]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const response = await api.export.xlsx();
      const url = URL.createObjectURL(response.data);
      const a = document.createElement('a');
      a.href = url;
      a.download =
        response.headers['content-disposition']?.split('filename=')[1]?.replace(/"/g, '') ||
        'transactions.xlsx';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to export data');
    } finally {
      setExporting(false);
    }
  };

  const handleSaveAlertPreferences = async () => {
    setAlertSaving(true);
    setAlertError('');
    setAlertSuccess('');
    try {
      await api.patch('/settings/profile', {
        alert_email_enabled: alertEmailEnabled,
        alert_threshold_pct: alertThresholdPct,
      });
      setAlertSuccess('Alert preferences saved');
    } catch (err: any) {
      setAlertError(err.response?.data?.detail || 'Failed to save alert preferences');
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
      setError(err.response?.data?.detail || 'Failed to delete account');
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
    <div className="min-h-screen">
      <header className="glass sticky top-0 z-40 border-b border-edge/8">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8 xl:px-10">
          <h1 className="font-display text-lg font-bold tracking-tight">Settings</h1>
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" /> Back
          </Button>
        </div>
      </header>

      <div className="mx-auto max-w-3xl space-y-6 px-4 py-8 sm:px-6 lg:px-8 xl:px-10">
        <Card className="p-6">
          <SectionHeader label="Profile" title="Account" />
          <div className="space-y-4">
            <div>
              <p className="section-label mb-0.5">Username</p>
              <p className="text-sm font-medium">{profile?.username || '—'}</p>
            </div>
            <div>
              <p className="section-label mb-0.5">Email</p>
              <p className="text-sm font-medium">{user?.email}</p>
            </div>
            <div>
              <p className="section-label mb-0.5">Account created</p>
              <p className="text-sm font-medium">
                {profile?.created_at ? new Date(profile.created_at).toLocaleDateString() : '—'}
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <SectionHeader label="Notifications" title="Budget alerts" />
          <div className="space-y-4">
            <p className="text-sm text-muted">
              Get an email when a category goes over budget, or crosses your
              chosen "approaching budget" threshold. Checked when you use the
              app (upload, review, label) — not a continuous background
              check.
            </p>

            <label className="flex items-center gap-2.5 text-sm font-medium text-ink">
              <input
                type="checkbox"
                checked={alertEmailEnabled}
                onChange={(e) => setAlertEmailEnabled(e.target.checked)}
                className="h-4 w-4 rounded border-edge/30 accent-accent"
              />
              Email me budget alerts
            </label>

            <div className="max-w-[180px]">
              <Input
                type="number"
                label="Approaching-budget threshold (%)"
                min={0}
                max={100}
                value={alertThresholdPct}
                onChange={(e) => setAlertThresholdPct(Number(e.target.value))}
                disabled={!alertEmailEnabled}
              />
            </div>

            {alertError && <Alert kind="error">{alertError}</Alert>}
            {alertSuccess && <Alert kind="success">{alertSuccess}</Alert>}

            <Button variant="outline" onClick={handleSaveAlertPreferences} loading={alertSaving}>
              <Bell className="h-4 w-4" />
              {alertSaving ? 'Saving' : 'Save alert preferences'}
            </Button>
          </div>
        </Card>

        <Card className="p-6">
          <SectionHeader label="Data & Security" title="Export your data" />
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
          <SectionHeader label="Data & Security" title="Change password" />
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
          <SectionHeader label="Legal" title="Policies" />
          <div className="space-y-3">
            <Link
              href="/privacy"
              className="flex items-center gap-2.5 text-sm font-medium text-ink transition-colors hover:text-accent-strong"
            >
              <FileText className="h-4 w-4 text-muted" /> Privacy Policy
            </Link>
            <Link
              href="/terms"
              className="flex items-center gap-2.5 text-sm font-medium text-ink transition-colors hover:text-accent-strong"
            >
              <ScrollText className="h-4 w-4 text-muted" /> Terms &amp; Conditions
            </Link>
          </div>
        </Card>

        <Card className="border-danger/25 p-6">
          <SectionHeader label="Irreversible" title="Danger zone" />
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
