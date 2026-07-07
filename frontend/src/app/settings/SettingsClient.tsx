'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { createClient } from '@/utils/supabase';
import { api } from '@/utils/api';
import { Alert } from '@/components/ui';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import Input from '@/components/ui/Input';
import { SkeletonCard } from '@/components/ui/Skeleton';

interface Profile {
  id: string;
  email_verified_at: string;
  onboarding_phase: string;
  monthly_income: number;
  created_at: string;
}

export default function SettingsClient() {
  const router = useRouter();
  const supabase = createClient();

  const [user, setUser] = useState<any>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [income, setIncome] = useState<string>('0');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

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
        setIncome(res.data.profile.monthly_income?.toString() || '0');
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load profile');
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, [supabase, router]);

  const handleUpdateIncome = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      await api.patch('/settings/profile', { monthly_income: parseFloat(income) });
      setSuccess('Income updated successfully');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update income');
    } finally {
      setSaving(false);
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
      <div className="mx-auto max-w-2xl space-y-6 px-4 py-12 sm:px-6">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="glass sticky top-0 z-40 border-b border-edge/8">
        <div className="mx-auto flex max-w-2xl items-center justify-between px-4 py-3 sm:px-6">
          <h1 className="font-display text-lg font-bold tracking-tight">Settings</h1>
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" /> Back
          </Button>
        </div>
      </header>

      <div className="mx-auto max-w-2xl space-y-6 px-4 py-8 sm:px-6">
        <Card className="p-6">
          <SectionHeader label="Profile" title="Account" />
          <div className="space-y-4">
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
            <div>
              <p className="section-label mb-0.5">Onboarding status</p>
              <p className="text-sm font-medium capitalize">{profile?.onboarding_phase || '—'}</p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <SectionHeader label="Budget" title="Monthly income" />
          <form onSubmit={handleUpdateIncome} className="space-y-4">
            <div>
              <Input
                label="Monthly income (¥)"
                type="number"
                value={income}
                onChange={(e) => setIncome(e.target.value)}
                placeholder="0"
              />
              <p className="mt-1.5 text-xs text-muted">
                Used for budget and savings calculations
              </p>
            </div>

            {error && <Alert kind="error">{error}</Alert>}
            {success && <Alert kind="success">{success}</Alert>}

            <Button type="submit" loading={saving}>
              {saving ? 'Saving' : 'Save income'}
            </Button>
          </form>
        </Card>

        <Card className="border-danger/25 p-6">
          <SectionHeader label="Irreversible" title="Danger zone" />
          <div className="space-y-4">
            <p className="text-sm text-muted">
              Deleting your account will permanently remove all your data, transactions, and
              models. This action cannot be undone.
            </p>

            {deleteConfirm ? (
              <div className="space-y-3 rounded-lg border border-danger/30 bg-danger/5 p-4">
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
