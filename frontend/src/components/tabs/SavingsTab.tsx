'use client';

import { useState } from 'react';
import { ArrowDown, ArrowUp, TriangleAlert } from 'lucide-react';
import { api } from '@/utils/api';
import { useApi } from '@/utils/useApi';
import { Alert, ProgressBar } from '@/components/ui';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import { AnimatedNumber } from '@/components/ui/motion';
import { SkeletonCard } from '@/components/ui/Skeleton';
import { formatCurrencyWhole, formatNumber, CURRENCY_SYMBOL } from '@/utils/format';

interface SavingsInfo {
  savings_goal_monthly: number;
  income: number;
  current_spend: number;
  projected_savings: number;
  average_monthly_spend: number;
  is_anomaly: boolean;
}

export default function SavingsTab() {
  const { data: savings, loading, error, reload } = useApi<SavingsInfo>('/dashboard/savings');
  const [editingGoal, setEditingGoal] = useState(false);
  const [goalInput, setGoalInput] = useState('');
  const [savingGoal, setSavingGoal] = useState(false);
  const [goalError, setGoalError] = useState('');

  const handleSaveGoal = async () => {
    const value = parseFloat(goalInput);
    if (!Number.isFinite(value) || value < 0) {
      setGoalError('Please enter a valid amount');
      return;
    }
    setSavingGoal(true);
    setGoalError('');
    try {
      await api.patch('/settings/budget', { saving_goal_monthly: value });
      setEditingGoal(false);
      await reload();
    } catch (err: any) {
      setGoalError(err.response?.data?.detail || 'Failed to save goal');
    } finally {
      setSavingGoal(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
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
    <div className="space-y-6">
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
                  {s.value < 0 ? '-' : ''}{CURRENCY_SYMBOL}
                  <AnimatedNumber
                    value={Math.abs(s.value)}
                    format={(n) => formatNumber(n, 0)}
                  />
                </p>
              </Card>
            ))}
          </div>

          <Card className="p-6">
            <p className="section-label mb-4">Savings goal</p>
            <div className="mb-2 flex items-center justify-between gap-3">
              <p className="text-sm text-muted">Monthly goal</p>
              {editingGoal ? (
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="0"
                    value={goalInput}
                    onChange={(e) => setGoalInput(e.target.value)}
                    placeholder="e.g. 3000"
                    className="w-32 rounded-pill border border-edge/20 bg-surface px-3 py-1.5 text-sm text-ink placeholder-muted focus:border-accent-strong/50 focus:outline-none"
                  />
                  <Button onClick={handleSaveGoal} loading={savingGoal} className="!px-3 !py-1.5 text-sm">
                    Save
                  </Button>
                  <button
                    onClick={() => { setEditingGoal(false); setGoalError(''); }}
                    className="text-sm text-muted hover:text-ink"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => {
                    setGoalInput(savings.savings_goal_monthly > 0 ? String(savings.savings_goal_monthly) : '');
                    setEditingGoal(true);
                  }}
                  className="text-sm font-semibold tabular-nums underline decoration-dotted underline-offset-4 hover:text-accent-strong"
                  title="Edit monthly savings goal"
                >
                  {savings.savings_goal_monthly > 0
                    ? formatCurrencyWhole(savings.savings_goal_monthly)
                    : 'Set a goal'}
                </button>
              )}
            </div>
            {goalError && <Alert kind="error">{goalError}</Alert>}
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
                : `${formatCurrencyWhole(savings.savings_goal_monthly - savings.projected_savings)} short of your goal`}
            </p>
          </Card>

          <Card className="p-6">
            <p className="section-label mb-4">Spending comparison</p>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <p className="mb-1 text-sm text-muted">3-month average</p>
                <p className="font-display text-2xl font-bold tabular-nums">
                  {formatCurrencyWhole(savings.average_monthly_spend)}
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
                      {formatCurrencyWhole(savings.current_spend - savings.average_monthly_spend)}
                    </>
                  ) : (
                    <>
                      <ArrowDown className="h-5 w-5" />
                      {formatCurrencyWhole(savings.average_monthly_spend - savings.current_spend)}
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
