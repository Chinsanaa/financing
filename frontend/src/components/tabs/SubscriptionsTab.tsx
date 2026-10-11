'use client';

import { useState } from 'react';
import { AnimatePresence, m } from 'framer-motion';
import { Check, Repeat, X } from 'lucide-react';
import { toast } from 'sonner';
import RollingNumber from '@/components/ui/RollingNumber';
import { useCategoryColors } from '@/utils/useCategoryColors';
import { useApi, invalidate } from '@/utils/useApi';
import { api } from '@/utils/api';
import { Alert } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import { SectionHeader } from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import EmptyState from '@/components/ui/EmptyState';
import { SkeletonRows } from '@/components/ui/Skeleton';
import { formatCurrencyWhole, formatDate } from '@/utils/format';

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
  const { toneFor } = useCategoryColors();

  const handleConfirm = async (id: string) => {
    setActioningId(id);
    setActionError('');
    try {
      await api.subscriptions.confirm(id);
      invalidate('/subscriptions');
      toast.success('Marked as a subscription');
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
      toast('Dismissed — it won\'t be suggested again');
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
        title="Subscriptions"
        description="Merchants that charge you on a regular schedule, detected automatically."
        action={
          data && subscriptions.length > 0 ? (
            <div className="text-right">
              <p className="num text-4xl leading-none">
                <RollingNumber value={data.monthly_total} currency />
              </p>
              <p className="mt-1.5 text-xs text-muted">
                est. per month · ≈ {formatCurrencyWhole(data.monthly_total * 12)} a year
              </p>
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
        <ul className="border-t border-ink/80">
          <AnimatePresence initial={false}>
            {subscriptions.map((sub) => (
              <m.li
                key={sub.id}
                layout
                exit={{ opacity: 0, transition: { duration: 0.15 } }}
                className="flex flex-wrap items-center gap-x-6 gap-y-3 border-b border-edge/12 py-4"
              >
                <div className="min-w-0 flex-1 basis-60">
                  <p className="truncate font-display text-xl">{sub.merchant}</p>
                  <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-[13px] text-muted">
                    <span>{CADENCE_LABEL[sub.cadence] || sub.cadence}</span>
                    {sub.categories?.name && (
                      <>
                        <span aria-hidden="true">·</span>
                        <Badge tone={toneFor(sub.categories.name)}>{sub.categories.name}</Badge>
                      </>
                    )}
                    {sub.last_seen && (
                      <>
                        <span aria-hidden="true">·</span>
                        <span>last charged {formatDate(sub.last_seen)}</span>
                      </>
                    )}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {sub.is_confirmed ? (
                    <span className="inline-flex items-center gap-1 text-[13px] text-success">
                      <Check className="h-3.5 w-3.5" aria-hidden="true" /> Confirmed
                    </span>
                  ) : (
                    <>
                      <Button variant="outline" size="sm" disabled={actioningId === sub.id} onClick={() => handleConfirm(sub.id)}>
                        <Check className="h-3 w-3" /> Looks right
                      </Button>
                      <Button variant="ghost" size="sm" disabled={actioningId === sub.id} onClick={() => handleDismiss(sub.id)}>
                        <X className="h-3 w-3" /> Not recurring
                      </Button>
                    </>
                  )}
                </div>
                <p className="num w-24 text-right text-xl">{formatCurrencyWhole(sub.typical_amount)}</p>
              </m.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </div>
  );
}
