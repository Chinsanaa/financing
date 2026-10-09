'use client';

import { ArrowRight, CheckCircle2 } from 'lucide-react';
import { useApi } from '@/utils/useApi';
import { Alert } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import { SectionHeader } from '@/components/ui/Card';
import { SkeletonRows } from '@/components/ui/Skeleton';
import { formatCurrencyWhole } from '@/utils/format';

interface Action {
  type: string;
  category?: string;
  current?: number;
  limit?: number;
  overage?: number;
  pct?: number;
  count?: number;
  message?: string;
}

const TIPS = [
  'Review categories over 80% of budget and plan to reduce spending.',
  'Check for recurring transactions you can negotiate or cancel.',
  'Clear the review queue to keep categorization accurate.',
  'Set realistic savings goals based on your average spending patterns.',
];

export default function ActionTab({ onNavigate }: { onNavigate?: (tab: string) => void }) {
  const { data, loading, error } = useApi<{ actions: Action[] }>('/dashboard/action');
  const actions = data?.actions || [];

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
        title="Action plan"
        description={actions.length > 0 ? `${actions.length} thing${actions.length === 1 ? '' : 's'} worth a look, most urgent first.` : 'Your to-do list for healthier spending.'}
      />

      {error && <Alert kind="error">{error}</Alert>}

      {actions.length === 0 ? (
        <div className="flex items-center gap-3 border-y border-success/30 py-5">
          <CheckCircle2 className="h-5 w-5 shrink-0 text-success" aria-hidden="true" />
          <div>
            <p className="font-display text-2xl text-success">All clear</p>
            <p className="mt-0.5 text-sm text-muted">No over-budget categories or pending items.</p>
          </div>
        </div>
      ) : (
        // A to-do list, most urgent first. The status word leads each row,
        // so color is never the only signal.
        <ol className="border-t border-ink/80">
          {actions.map((action, idx) => {
            const row = 'grid grid-cols-[6.5rem,1fr,auto] items-baseline gap-x-4 border-b border-edge/12 py-4';
            if (action.type === 'over_budget') {
              return (
                <li key={idx} className={row}>
                  <span className="text-[13px] font-medium text-danger">Over budget</span>
                  <div>
                    <p className="font-medium">{action.category}</p>
                    <p className="mt-0.5 text-[13px] text-muted">
                      Spent {formatCurrencyWhole(action.current || 0)} of a {formatCurrencyWhole(action.limit || 0)} budget
                    </p>
                  </div>
                  <p className="num text-xl text-danger">
                    {formatCurrencyWhole(action.overage || 0)} <span className="text-[13px]">over</span>
                  </p>
                </li>
              );
            } else if (action.type === 'approaching_budget') {
              return (
                <li key={idx} className={row}>
                  <span className="text-[13px] font-medium text-warn">Near limit</span>
                  <div>
                    <p className="font-medium">{action.category}</p>
                    <p className="mt-0.5 text-[13px] text-muted">
                      Spent {formatCurrencyWhole(action.current || 0)} of a {formatCurrencyWhole(action.limit || 0)} budget
                    </p>
                  </div>
                  <p className="num text-xl text-warn">
                    {action.pct}% <span className="text-[13px]">used</span>
                  </p>
                </li>
              );
            } else if (action.type === 'pending_review') {
              return (
                <li key={idx} className={row}>
                  <span className="text-[13px] font-medium">To review</span>
                  <p className="text-sm text-muted">{action.message}</p>
                  <Button variant="outline" size="sm" onClick={() => onNavigate?.('review')}>
                    Review <ArrowRight className="h-3 w-3" />
                  </Button>
                </li>
              );
            }
            return null;
          })}
        </ol>
      )}

      <section className="pt-4">
        <h3 className="mb-3 font-display text-2xl">Habits that help</h3>
        <ul className="max-w-3xl border-t border-edge/15">
          {TIPS.map((tip) => (
            <li key={tip} className="border-b border-edge/10 py-3 text-sm text-muted">
              {tip}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
