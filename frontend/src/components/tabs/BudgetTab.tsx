'use client';

import { Wallet } from 'lucide-react';
import { useApi } from '@/utils/useApi';
import { Alert, ProgressBar } from '@/components/ui';
import Card, { SectionHeader } from '@/components/ui/Card';
import Badge, { categoryColor } from '@/components/ui/Badge';
import EmptyState from '@/components/ui/EmptyState';
import { AnimatedNumber } from '@/components/ui/motion';
import { SkeletonCard, SkeletonRows } from '@/components/ui/Skeleton';

interface BudgetInfo {
  budget_config: {
    monthly_income: number;
    currency: string;
  } | null;
  category_budgets: Array<{
    category: string;
    monthly_budget: number;
    current_spend: number;
    type: string;
  }>;
}

export default function BudgetTab() {
  const { data: budget, loading, error } = useApi<BudgetInfo>('/dashboard/budget');

  if (loading) {
    return (
      <div className="max-w-3xl space-y-6">
        <SkeletonCard />
        <SkeletonRows rows={5} />
      </div>
    );
  }

  return (
    <div className="max-w-3xl space-y-6">
      <SectionHeader label="Planning" title="Budget and forecast" />

      {error && <Alert kind="error">{error}</Alert>}

      {budget?.budget_config && (
        <Card className="p-5">
          <p className="section-label mb-2">Monthly income</p>
          <p className="font-display text-3xl font-bold tabular-nums tracking-tight">
            ¥
            <AnimatedNumber
              value={budget.budget_config.monthly_income}
              format={(n) => n.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            />
          </p>
        </Card>
      )}

      <Card className="p-6">
        <p className="section-label mb-4">Budget by category — this month</p>

        {!budget || budget.category_budgets.length === 0 ? (
          <EmptyState
            icon={Wallet}
            title="No budget set"
            description="Create categories and set monthly limits to see how you're tracking."
          />
        ) : (
          <div className="space-y-5">
            {budget.category_budgets.map((cat) => {
              const percentage = cat.monthly_budget > 0
                ? Math.round((cat.current_spend / cat.monthly_budget) * 100)
                : 0;
              const isOverBudget = cat.current_spend > cat.monthly_budget;
              const color = isOverBudget
                ? 'bg-danger'
                : percentage > 80
                ? 'bg-[color:var(--chart-5)]'
                : 'bg-accent';

              return (
                <div key={cat.category}>
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <Badge tone={categoryColor(cat.category)}>{cat.category}</Badge>
                    <p className={`text-sm font-semibold tabular-nums ${isOverBudget ? 'text-danger' : ''}`}>
                      ¥{cat.current_spend.toFixed(0)} / ¥{cat.monthly_budget.toFixed(0)}
                    </p>
                  </div>
                  <ProgressBar percent={percentage} color={color} />
                  <p className="mt-1 text-xs text-muted">
                    {isOverBudget
                      ? `¥${(cat.current_spend - cat.monthly_budget).toFixed(0)} over budget`
                      : `${percentage}% of budget used`}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
