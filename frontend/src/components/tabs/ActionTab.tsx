'use client';

import { ArrowRight, CheckCircle2, ClipboardList, TriangleAlert } from 'lucide-react';
import { useApi } from '@/utils/useApi';
import { Alert } from '@/components/ui';
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
      <SectionHeader label="Planning" title="Action plan" />

      {error && <Alert kind="error">{error}</Alert>}

      {actions.length === 0 ? (
        <div className="flex items-start gap-3 rounded-card border border-success/25 bg-success/10 p-5">
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-success" />
          <div>
            <p className="font-medium text-success">All clear</p>
            <p className="mt-0.5 text-sm text-muted">
              No over-budget categories or pending items.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {actions.map((action, idx) => {
            if (action.type === 'over_budget') {
              return (
                <Card key={idx} className="border-danger/25 p-4">
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
            } else if (action.type === 'pending_review') {
              return (
                <Card key={idx} className="p-4">
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

      <Card className="p-6">
        <p className="section-label mb-4">Tips to improve your finances</p>
        <ul className="space-y-3">
          {TIPS.map((tip, i) => (
            <li key={i} className="flex gap-3 text-sm">
              <span className="font-display font-semibold text-accent-strong">{i + 1}.</span>
              <span className="text-muted">{tip}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
