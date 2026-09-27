'use client';

import { useState } from 'react';
import { ArrowDown, ArrowUp, Banknote, PiggyBank, Receipt, Target, TriangleAlert } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '@/utils/api';
import { useApi } from '@/utils/useApi';
import { Alert } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import StatTile from '@/components/ui/StatTile';
import ProgressRing from '@/components/ui/ProgressRing';
import RollingNumber from '@/components/ui/RollingNumber';
import { SkeletonCard } from '@/components/ui/Skeleton';
import { formatCurrencyWhole } from '@/utils/format';

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
      toast.success('Savings goal updated', { description: `${formatCurrencyWhole(value)} per month.` });
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
            <StatTile label="Income" value={savings.income} currency icon={Banknote} footer="Monthly, from your settings" />
            <StatTile label="Spend this month" value={savings.current_spend} currency icon={Receipt} footer="So far" />
            <StatTile
              label="Projected savings"
              value={savings.projected_savings}
              currency
              icon={PiggyBank}
              tone={savings.projected_savings > 0 ? 'success' : 'danger'}
              footer={savings.projected_savings > 0 ? 'Income minus spend' : 'Spending exceeds income'}
            />
          </div>

          {/* Savings goal: ring gauge + editable goal */}
          {(() => {
            const goal = savings.savings_goal_monthly;
            const pct = goal > 0 ? (savings.projected_savings / goal) * 100 : 0;
            const hit = goal > 0 && savings.projected_savings >= goal;
            return (
              <Card className="p-6">
                <p className="section-label mb-5">Savings goal</p>
                <div className="flex flex-col items-center gap-8 sm:flex-row">
                  <ProgressRing
                    percent={pct}
                    label="Progress toward monthly savings goal"
                    color={hit ? 'rgb(var(--success))' : 'rgb(var(--accent))'}
                  >
                    <p className="font-display text-3xl font-bold">
                      <RollingNumber value={Math.max(0, Math.round(pct))} suffix="%" />
                    </p>
                    <p className="text-xs text-muted">of goal</p>
                  </ProgressRing>

                  <div className="w-full flex-1 space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="flex items-center gap-2 text-sm text-muted">
                        <Target className="h-4 w-4" /> Monthly goal
                      </p>
                      {editingGoal ? (
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            min="0"
                            value={goalInput}
                            onChange={(e) => setGoalInput(e.target.value)}
                            placeholder="e.g. 3000"
                            autoFocus
                            aria-label="Monthly savings goal"
                            className="w-32 rounded-pill border border-edge/20 bg-surface px-3 py-1.5 text-sm text-ink placeholder-muted focus:border-accent-strong/50 focus:outline-none focus:ring-2 focus:ring-accent/20"
                          />
                          <Button onClick={handleSaveGoal} loading={savingGoal} size="sm">
                            Save
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => { setEditingGoal(false); setGoalError(''); }}
                          >
                            Cancel
                          </Button>
                        </div>
                      ) : (
                        <button
                          onClick={() => {
                            setGoalInput(goal > 0 ? String(goal) : '');
                            setEditingGoal(true);
                          }}
                          className="font-display text-2xl font-bold tabular-nums underline decoration-edge/30 decoration-dotted underline-offset-8 transition-colors hover:text-accent-strong hover:decoration-accent"
                          title="Edit monthly savings goal"
                        >
                          {goal > 0 ? formatCurrencyWhole(goal) : 'Set a goal'}
                        </button>
                      )}
                    </div>
                    {goalError && <Alert kind="error">{goalError}</Alert>}
                    <div
                      className={`rounded-lg border px-4 py-3 text-sm ${
                        goal <= 0
                          ? 'border-edge/10 bg-edge/5 text-muted'
                          : hit
                          ? 'border-success/25 bg-success/10 text-success'
                          : 'border-accent/25 bg-accent/5 text-ink'
                      }`}
                    >
                      {goal <= 0
                        ? 'Set a monthly goal to see your progress here.'
                        : hit
                        ? `On track — projected ${formatCurrencyWhole(savings.projected_savings - goal)} above your goal.`
                        : `${formatCurrencyWhole(goal - savings.projected_savings)} short of your goal at the current pace.`}
                    </div>
                  </div>
                </div>
              </Card>
            );
          })()}

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
