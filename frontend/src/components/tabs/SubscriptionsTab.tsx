'use client';

import { useState } from 'react';
import { Check, Repeat, X } from 'lucide-react';
import { useApi, invalidate } from '@/utils/useApi';
import { api } from '@/utils/api';
import { Alert } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import EmptyState from '@/components/ui/EmptyState';
import { SkeletonRows } from '@/components/ui/Skeleton';
import { formatCurrencyWhole } from '@/utils/format';

interface Subscription {
  id: string;
  merchant: string;
  cadence: 'monthly' | 'weekly' | 'irregular';
  typical_amount: number;
  last_seen: string | null;
  is_confirmed: boolean;
  categories: { name: string } | null;
}

interface SubscriptionsData {
  subscriptions: Subscription[];
  monthly_total: number;
}

const CADENCE_LABEL: Record<string, string> = {
  monthly: 'Monthly',
  weekly: 'Weekly',
};

export default function SubscriptionsTab() {
  const { data, loading, error } = useApi<SubscriptionsData>('/subscriptions/');
  const [actioningId, setActioningId] = useState<string | null>(null);
  const [actionError, setActionError] = useState('');

  const subscriptions = data?.subscriptions || [];

  const handleConfirm = async (id: string) => {
    setActioningId(id);
    setActionError('');
    try {
      await api.subscriptions.confirm(id);
      invalidate('/subscriptions');
    } catch (err: any) {
      setActionError(err?.response?.data?.detail || 'Could not confirm subscription');
    } finally {
      setActioningId(null);
    }
  };

  const handleDismiss = async (id: string) => {
    setActioningId(id);
    setActionError('');
    try {
      await api.subscriptions.dismiss(id);
      invalidate('/subscriptions');
    } catch (err: any) {
      setActionError(err?.response?.data?.detail || 'Could not dismiss subscription');
    } finally {
      setActioningId(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <SkeletonRows rows={4} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        label="Planning"
        title="Subscriptions"
        action={
          data && subscriptions.length > 0 ? (
            <div className="text-right">
              <p className="font-display text-xl font-bold tabular-nums">
                {formatCurrencyWhole(data.monthly_total)}
              </p>
              <p className="text-xs text-muted">est. per month</p>
            </div>
          ) : undefined
        }
      />

      {error && <Alert kind="error">{error}</Alert>}
      {actionError && <Alert kind="error">{actionError}</Alert>}

      {subscriptions.length === 0 ? (
        <EmptyState
          icon={Repeat}
          title="No recurring charges detected yet"
          description="Once you have a few months of transactions, merchants that charge you on a regular schedule (subscriptions, memberships) will show up here automatically."
        />
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {subscriptions.map((sub) => (
            <Card key={sub.id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold">{sub.merchant}</p>
                    {sub.is_confirmed && <Badge tone="success">Confirmed</Badge>}
                  </div>
                  <p className="mt-0.5 text-xs text-muted">
                    {CADENCE_LABEL[sub.cadence] || sub.cadence}
                    {sub.categories?.name ? ` · ${sub.categories.name}` : ''}
                  </p>
                </div>
                <p className="font-display text-lg font-bold tabular-nums">
                  {formatCurrencyWhole(sub.typical_amount)}
                </p>
              </div>

              {!sub.is_confirmed && (
                <div className="mt-3 flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={actioningId === sub.id}
                    onClick={() => handleConfirm(sub.id)}
                  >
                    <Check className="h-3 w-3" /> Looks right
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={actioningId === sub.id}
                    onClick={() => handleDismiss(sub.id)}
                  >
                    <X className="h-3 w-3" /> Not recurring
                  </Button>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
