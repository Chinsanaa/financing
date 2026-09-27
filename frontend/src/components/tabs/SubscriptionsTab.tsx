'use client';

import { useState } from 'react';
import { AnimatePresence, m } from 'framer-motion';
import { CalendarClock, Check, Repeat, X } from 'lucide-react';
import { toast } from 'sonner';
import RollingNumber from '@/components/ui/RollingNumber';
import { useCategoryColors } from '@/utils/useCategoryColors';
import { useApi, invalidate } from '@/utils/useApi';
import { api } from '@/utils/api';
import { Alert } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
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
  const { chartColorFor } = useCategoryColors();

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
        label="Planning"
        title="Subscriptions"
        description="Merchants that charge you on a regular schedule, detected automatically."
        action={
          data && subscriptions.length > 0 ? (
            <Card className="px-5 py-3 text-right">
              <p className="font-display text-2xl font-bold">
                <RollingNumber value={data.monthly_total} currency />
              </p>
              <p className="text-xs text-muted">
                est. per month · ≈ {formatCurrencyWhole(data.monthly_total * 12)} a year
              </p>
            </Card>
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
          <AnimatePresence initial={false}>
          {subscriptions.map((sub) => {
            const tint = sub.categories?.name ? chartColorFor(sub.categories.name) : 'rgb(var(--muted))';
            return (
            <m.div
              key={sub.id}
              layout
              exit={{ opacity: 0, scale: 0.96, transition: { duration: 0.15 } }}
            >
            <Card hover className="h-full p-4">
              <div className="flex items-start gap-3">
                {/* Monogram tinted with the category color */}
                <span
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl font-display text-base font-bold"
                  style={{ color: tint, backgroundColor: `color-mix(in srgb, ${tint} 15%, transparent)` }}
                  aria-hidden="true"
                >
                  {sub.merchant.trim().charAt(0).toUpperCase() || '?'}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate text-sm font-semibold">{sub.merchant}</p>
                    {sub.is_confirmed && <Badge tone="success"><Check className="mr-1 h-3 w-3" />Confirmed</Badge>}
                  </div>
                  <p className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-xs text-muted">
                    <Repeat className="h-3 w-3" />
                    {CADENCE_LABEL[sub.cadence] || sub.cadence}
                    {sub.categories?.name ? ` · ${sub.categories.name}` : ''}
                    {sub.last_seen && (
                      <>
                        <span aria-hidden="true">·</span>
                        <CalendarClock className="h-3 w-3" /> last {formatDate(sub.last_seen)}
                      </>
                    )}
                  </p>
                </div>
                <p className="font-display text-lg font-bold tabular-nums">
                  {formatCurrencyWhole(sub.typical_amount)}
                </p>
              </div>

              {!sub.is_confirmed && (
                <div className="mt-3 flex gap-2 pl-[52px]">
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
            </m.div>
            );
          })}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
