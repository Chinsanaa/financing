'use client';

import { ArrowRight, CheckCircle2, ClipboardList, TriangleAlert } from 'lucide-react';
import { useApi } from '@/utils/useApi';
import { Alert } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
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
        label="Planning"
        title="Action plan"
        description={actions.length > 0 ? `${actions.length} thing${actions.length === 1 ? '' : 's'} worth a look, most urgent first.` : 'Your to-do list for healthier spending.'}
      />

      {error && <Alert kind="error">{error}</Alert>}

      {actions.length === 0 ? (
        <div className="relative flex items-center gap-4 overflow-hidden rounded-card border border-success/25 bg-success/10 p-6">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -left-10 -top-16 h-48 w-48 rounded-full bg-[radial-gradient(closest-side,rgb(var(--success)/0.25),transparent)]"
          />
          <span className="relative flex h-12 w-12 shrink-0 items-center justify-center">
            <span className="absolute inset-0 rounded-full bg-success/25 animate-ping-soft" />
            <span className="relative flex h-12 w-12 items-center justify-center rounded-full bg-success text-bg">
              <CheckCircle2 className="h-6 w-6" />
            </span>
          </span>
          <div className="relative">
            <p className="font-display text-lg font-semibold text-success">All clear</p>
            <p className="mt-0.5 text-sm text-muted">
              No over-budget categories or pending items. Nice work.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {actions.map((action, idx) => {
            if (action.type === 'over_budget') {
              return (
                <Card key={idx} hover className="relative overflow-hidden border-danger/25 p-4 pl-5">
                  <span aria-hidden="true" className="absolute inset-y-0 left-0 w-1 bg-danger" />
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2.5">
                      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
                      <div>
                        <p className="text-sm font-semibold">Over budget: {action.category}</p>
                        <p className="mt-0.5 text-xs text-muted">
                          Spent {formatCurrencyWhole(action.current || 0)} of {formatCurrencyWhole(action.limit || 0)} budget
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-display text-lg font-bold text-danger tabular-nums">
                        {formatCurrencyWhole(action.overage || 0)}
                      </p>
                      <p className="text-xs text-danger">over</p>
                    </div>
                  </div>
                </Card>
              );
            } else if (action.type === 'approaching_budget') {
              return (
                <Card key={idx} hover className="relative overflow-hidden border-warn/25 p-4 pl-5">
                  <span aria-hidden="true" className="absolute inset-y-0 left-0 w-1 bg-warn" />
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2.5">
                      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-warn" />
                      <div>
                        <p className="text-sm font-semibold">Approaching budget: {action.category}</p>
                        <p className="mt-0.5 text-xs text-muted">
                          Spent {formatCurrencyWhole(action.current || 0)} of {formatCurrencyWhole(action.limit || 0)} budget
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-display text-lg font-bold text-warn tabular-nums">
                        {action.pct}%
                      </p>
                      <p className="text-xs text-warn">used</p>
                    </div>
                  </div>
                </Card>
              );
            } else if (action.type === 'pending_review') {
              return (
                <Card key={idx} hover className="relative overflow-hidden p-4 pl-5">
                  <span aria-hidden="true" className="absolute inset-y-0 left-0 w-1 bg-accent" />
                  <div className="flex items-start gap-2.5">
                    <ClipboardList className="mt-0.5 h-4 w-4 shrink-0 text-accent-strong" />
                    <div>
                      <p className="text-sm font-semibold">Pending review</p>
                      <p className="mt-0.5 text-xs text-muted">{action.message}</p>
                      <Button
                        variant="outline"
                        size="sm"
                        className="mt-3"
                        onClick={() => onNavigate?.('review')}
                      >
                        Review transactions <ArrowRight className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                </Card>
              );
            }
            return null;
          })}
        </div>
      )}

      <div>
        <p className="section-label mb-3">Tips to improve your finances</p>
        <ul className="stagger-in grid gap-3 sm:grid-cols-2">
          {TIPS.map((tip, i) => (
            <li key={i}>
              <Card hover className="flex h-full gap-3 p-4 text-sm">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-accent/12 font-display text-sm font-bold text-accent-strong">
                  {i + 1}
                </span>
                <span className="text-muted">{tip}</span>
              </Card>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
