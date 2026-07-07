'use client';

import { ArrowDown, ArrowUp, TriangleAlert } from 'lucide-react';
import { useApi } from '@/utils/useApi';
import { Alert, ProgressBar } from '@/components/ui';
import Card, { SectionHeader } from '@/components/ui/Card';
import { AnimatedNumber } from '@/components/ui/motion';
import { SkeletonCard } from '@/components/ui/Skeleton';

interface SavingsInfo {
  savings_goal_monthly: number;
  income: number;
  current_spend: number;
  projected_savings: number;
  average_monthly_spend: number;
  is_anomaly: boolean;
}

export default function SavingsTab() {
  const { data: savings, loading, error } = useApi<SavingsInfo>('/dashboard/savings');

  if (loading) {
    return (
      <div className="max-w-3xl space-y-6">
        <div className="grid gap-4 md:grid-cols-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <SkeletonCard />
      </div>
    );
  }

  return (
    <div className="max-w-3xl space-y-6">
      <SectionHeader label="Planning" title="Savings and anomalies" />

      {error && <Alert kind="error">{error}</Alert>}

      {savings && (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            {[
              { label: 'Income', value: savings.income, tone: '' },
              { label: 'Spend this month', value: savings.current_spend, tone: '' },
              {
                label: 'Projected savings',
                value: savings.projected_savings,
                tone: savings.projected_savings > 0 ? 'text-success' : 'text-danger',
              },
            ].map((s) => (
              <Card key={s.label} hover className="p-5">
                <p className="section-label mb-2">{s.label}</p>
                <p className={`font-display text-3xl font-bold tabular-nums tracking-tight ${s.tone}`}>
                  ¥
                  <AnimatedNumber
                    value={s.value}
                    format={(n) => n.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  />
                </p>
              </Card>
            ))}
          </div>

          <Card className="p-6">
            <p className="section-label mb-4">Savings goal</p>
            <div className="mb-2 flex items-center justify-between">
              <p className="text-sm text-muted">Monthly goal</p>
              <p className="text-sm font-semibold tabular-nums">
                ¥{savings.savings_goal_monthly.toFixed(0)}
              </p>
            </div>
            <ProgressBar
              percent={
                savings.savings_goal_monthly > 0
                  ? (savings.projected_savings / savings.savings_goal_monthly) * 100
                  : 0
              }
              color={
                savings.projected_savings >= savings.savings_goal_monthly
                  ? 'bg-success'
                  : 'bg-accent'
              }
            />
            <p className="mt-1.5 text-xs text-muted">
              {savings.projected_savings >= savings.savings_goal_monthly
                ? 'On track to hit your goal'
                : `¥${(savings.savings_goal_monthly - savings.projected_savings).toFixed(0)} short of your goal`}
            </p>
          </Card>

          <Card className="p-6">
            <p className="section-label mb-4">Spending comparison</p>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <p className="mb-1 text-sm text-muted">3-month average</p>
                <p className="font-display text-2xl font-bold tabular-nums">
                  ¥{savings.average_monthly_spend.toFixed(0)}
                </p>
              </div>
              <div>
                <p className="mb-1 text-sm text-muted">This month vs average</p>
                <p
                  className={`flex items-center gap-1 font-display text-2xl font-bold tabular-nums ${
                    savings.current_spend > savings.average_monthly_spend
                      ? 'text-danger'
                      : 'text-success'
                  }`}
                >
                  {savings.current_spend > savings.average_monthly_spend ? (
                    <>
                      <ArrowUp className="h-5 w-5" />
                      ¥{(savings.current_spend - savings.average_monthly_spend).toFixed(0)}
                    </>
                  ) : (
                    <>
                      <ArrowDown className="h-5 w-5" />
                      ¥{(savings.average_monthly_spend - savings.current_spend).toFixed(0)}
                    </>
                  )}
                </p>
              </div>
            </div>

            {savings.is_anomaly && (
              <div className="mt-5 flex items-start gap-2.5 rounded-lg border border-danger/25 bg-danger/10 px-4 py-3">
                <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
                <div>
                  <p className="text-sm font-medium text-danger">Spending anomaly detected</p>
                  <p className="mt-0.5 text-xs text-muted">
                    Current spending is 30% higher than your 3-month average.
                  </p>
                </div>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
