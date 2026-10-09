'use client';

import { useState } from 'react';
import { TriangleAlert } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '@/utils/api';
import { useApi } from '@/utils/useApi';
import { Alert, ProgressBar } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import { SectionHeader } from '@/components/ui/Card';
import { FIELD_CLASSES } from '@/components/ui/Input';
import StatTile, { FactRow } from '@/components/ui/StatTile';
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
      <SectionHeader title="Savings" description="What this month is on pace to leave over, against the goal you set." />

      {error && <Alert kind="error">{error}</Alert>}

      {savings && (
        <>
          <FactRow>
            <StatTile label="Income" value={savings.income} currency footer="Monthly, from your settings" />
            <StatTile label="Spent this month" value={savings.current_spend} currency footer="So far" />
            <StatTile
              label="Projected savings"
              value={savings.projected_savings}
              currency
              tone={savings.projected_savings > 0 ? 'success' : 'danger'}
              footer={savings.projected_savings > 0 ? 'Income minus spend' : 'Spending exceeds income'}
            />
            <StatTile
              label="vs 3-month average"
              value={Math.abs(savings.current_spend - savings.average_monthly_spend)}
              currency
              tone={savings.current_spend > savings.average_monthly_spend ? 'danger' : 'success'}
              footer={`${savings.current_spend > savings.average_monthly_spend ? '▲ more' : '▼ less'} than ${formatCurrencyWhole(savings.average_monthly_spend)}`}
            />
          </FactRow>

          {/* Savings goal: ring gauge + editable goal */}
          {(() => {
            const goal = savings.savings_goal_monthly;
            const pct = goal > 0 ? (savings.projected_savings / goal) * 100 : 0;
            const hit = goal > 0 && savings.projected_savings >= goal;
            return (
              <section className="border-t border-ink/80 pt-4">
                <h3 className="mb-5 font-display text-2xl">Savings goal</h3>
                <div className="space-y-5">
                  {goal > 0 && (
                    // Projected savings against the goal (tick). Past the goal
                    // the bar fills and the overshoot is written, not drawn.
                    <div>
                      <div className="mb-2 flex items-baseline justify-between text-sm">
                        <span className="text-muted">Projected</span>
                        <span className="num text-[15px]">
                          <RollingNumber value={Math.max(0, Math.round(pct))} suffix="%" /> <span className="text-muted">of goal</span>
                        </span>
                      </div>
                      <ProgressBar
                        percent={pct}
                        height="h-2.5"
                        color={hit ? 'bg-success' : 'bg-ink'}
                        marker={100}
                        label="Progress toward monthly savings goal"
                      />
                    </div>
                  )}
                  <div className="w-full space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-sm text-muted">Monthly goal</p>
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
                            className={`${FIELD_CLASSES} w-32 py-1.5`}
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
                          className="num text-2xl underline decoration-edge/30 decoration-dotted underline-offset-8 transition-colors hover:decoration-accent"
                          title="Edit monthly savings goal"
                        >
                          {goal > 0 ? formatCurrencyWhole(goal) : 'Set a goal'}
                        </button>
                      )}
                    </div>
                    {goalError && <Alert kind="error">{goalError}</Alert>}
                    <div
                      className={`text-sm ${goal <= 0 ? 'text-muted' : hit ? 'text-success' : 'text-ink'}`}
                    >
                      {goal <= 0
                        ? 'Set a monthly goal to see your progress here.'
                        : hit
                        ? `On track — projected ${formatCurrencyWhole(savings.projected_savings - goal)} above your goal.`
                        : `${formatCurrencyWhole(goal - savings.projected_savings)} short of your goal at the current pace.`}
                    </div>
                  </div>
                </div>
              </section>
            );
          })()}

            {savings.is_anomaly && (
              <div className="flex items-start gap-2.5 rounded-md border border-danger/25 bg-danger/[0.06] px-4 py-3">
                <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
                <div>
                  <p className="text-sm font-medium text-danger">Spending anomaly detected</p>
                  <p className="mt-0.5 text-xs text-muted">
                    Current spending is 30% higher than your 3-month average.
                  </p>
                </div>
              </div>
            )}
        </>
      )}
    </div>
  );
}
