'use client';

import { useState } from 'react';
import { Pencil, Wallet } from 'lucide-react';
import { api } from '@/utils/api';
import { useApi, invalidate } from '@/utils/useApi';
import { Alert, ProgressBar } from '@/components/ui';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import Badge, { categoryColor } from '@/components/ui/Badge';
import EmptyState from '@/components/ui/EmptyState';
import { AnimatedNumber } from '@/components/ui/motion';
import { SkeletonCard, SkeletonRows } from '@/components/ui/Skeleton';
import { formatCurrencyWhole, formatNumber, CURRENCY_SYMBOL } from '@/utils/format';

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
  month: string; // resolved "YYYY-MM"
  available_months: string[]; // months with transactions, newest first
}

/* "YYYY-MM" -> e.g. "June 2026". */
function monthLabel(ym: string): string {
  const d = new Date(ym + '-01');
  if (isNaN(d.getTime())) return ym;
  return d.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
}

interface Category {
  id: string;
  name: string;
  is_catch_all?: boolean;
}

interface BudgetDraft {
  amount: string;
  type: 'Need' | 'Want';
}

export default function BudgetTab() {
  // Empty string = current month. useApi caches per path, so each selected month
  // is fetched once and re-displayed instantly on revisit.
  const [month, setMonth] = useState('');
  const { data: budget, loading, error, reload } = useApi<BudgetInfo>(
    month ? `/dashboard/budget?month=${month}` : '/dashboard/budget'
  );
  const { data: categoriesData } = useApi<{ categories: Category[] }>('/categories/');

  // Options for the selector: the resolved current month is always first, then
  // any other months that have transactions.
  const monthOptions = (() => {
    const opts = budget?.available_months ? [...budget.available_months] : [];
    if (budget?.month && !opts.includes(budget.month)) opts.unshift(budget.month);
    return opts;
  })();
  const selectedMonth = month || budget?.month || '';

  const [editing, setEditing] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, BudgetDraft>>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');

  const categories = categoriesData?.categories || [];

  const startEditing = () => {
    const initial: Record<string, BudgetDraft> = {};
    for (const cat of categories) {
      const existing = budget?.category_budgets.find((b) => b.category === cat.name);
      initial[cat.id] = {
        amount: existing && existing.monthly_budget > 0 ? String(existing.monthly_budget) : '',
        type: existing?.type === 'Want' ? 'Want' : 'Need',
      };
    }
    setDrafts(initial);
    setSaveError('');
    setEditing(true);
  };

  const handleSave = async () => {
    const budgets = Object.entries(drafts)
      .filter(([, d]) => d.amount !== '' && Number.isFinite(parseFloat(d.amount)))
      .map(([categoryId, d]) => ({
        category_id: categoryId,
        monthly_budget: parseFloat(d.amount),
        type: d.type,
      }));

    if (budgets.length === 0) {
      setSaveError('Enter at least one budget amount');
      return;
    }

    setSaving(true);
    setSaveError('');
    try {
      await api.put('/dashboard/budget/categories', { budgets });
      setEditing(false);
      invalidate('/dashboard');
      await reload();
    } catch (err: any) {
      setSaveError(err.response?.data?.detail || 'Failed to save budgets');
    } finally {
      setSaving(false);
    }
  };

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

      {budget?.budget_config && budget.budget_config.monthly_income > 0 && (
        <Card className="p-5">
          <p className="section-label mb-2">Monthly income</p>
          <p className="font-display text-3xl font-bold tabular-nums tracking-tight">
            {CURRENCY_SYMBOL}
            <AnimatedNumber
              value={budget.budget_config.monthly_income}
              format={(n) => formatNumber(n, 0)}
            />
          </p>
        </Card>
      )}

      <Card className="p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <p className="section-label">
            Budget by category — {selectedMonth ? monthLabel(selectedMonth) : 'this month'}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {!editing && monthOptions.length > 1 && (
              <select
                value={selectedMonth}
                onChange={(e) => setMonth(e.target.value)}
                className="rounded-pill border border-edge/20 bg-surface px-3 py-1.5 text-sm text-ink focus:border-accent-strong/50 focus:outline-none"
              >
                {monthOptions.map((m) => (
                  <option key={m} value={m}>
                    {monthLabel(m)}
                  </option>
                ))}
              </select>
            )}
            {!editing && categories.length > 0 && (
              <Button variant="outline" onClick={startEditing} className="!px-3 !py-1.5 text-sm">
                <Pencil className="mr-1.5 h-3.5 w-3.5" />
                {budget && budget.category_budgets.length > 0 ? 'Edit budgets' : 'Set budgets'}
              </Button>
            )}
          </div>
        </div>

        {!editing && budget && budget.category_budgets.length > 0 && (
          <p className="-mt-2 mb-4 text-xs text-muted">
            Budgets are global. Past months show that month&apos;s actual spend compared against your
            current budget.
          </p>
        )}

        {editing ? (
          <div className="space-y-4">
            <p className="text-sm text-muted">
              Set a monthly limit per category. Leave a field empty to skip that category. Budgets
              apply to every month.
            </p>
            {categories.map((cat) => (
              <div key={cat.id} className="flex items-center gap-3">
                <div className="w-36 shrink-0">
                  <Badge tone={categoryColor(cat.name)}>{cat.name}</Badge>
                </div>
                <input
                  type="number"
                  min="0"
                  value={drafts[cat.id]?.amount ?? ''}
                  onChange={(e) =>
                    setDrafts((prev) => ({
                      ...prev,
                      [cat.id]: { ...prev[cat.id], amount: e.target.value },
                    }))
                  }
                  placeholder={`${CURRENCY_SYMBOL} per month`}
                  className="w-36 rounded-pill border border-edge/20 bg-surface px-3 py-1.5 text-sm text-ink placeholder-muted focus:border-accent-strong/50 focus:outline-none"
                />
                <select
                  value={drafts[cat.id]?.type ?? 'Need'}
                  onChange={(e) =>
                    setDrafts((prev) => ({
                      ...prev,
                      [cat.id]: { ...prev[cat.id], type: e.target.value as 'Need' | 'Want' },
                    }))
                  }
                  className="rounded-pill border border-edge/20 bg-surface px-3 py-1.5 text-sm text-ink focus:border-accent-strong/50 focus:outline-none"
                >
                  <option value="Need">Need</option>
                  <option value="Want">Want</option>
                </select>
              </div>
            ))}
            {saveError && <Alert kind="error">{saveError}</Alert>}
            <div className="flex items-center gap-3 pt-2">
              <Button onClick={handleSave} loading={saving}>
                Save budgets
              </Button>
              <button onClick={() => setEditing(false)} className="text-sm text-muted hover:text-ink">
                Cancel
              </button>
            </div>
          </div>
        ) : !budget || budget.category_budgets.length === 0 ? (
          <EmptyState
            icon={Wallet}
            title="No budget set"
            description="Set monthly limits per category to see how you're tracking."
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
                      {formatCurrencyWhole(cat.current_spend)} / {formatCurrencyWhole(cat.monthly_budget)}
                    </p>
                  </div>
                  <ProgressBar percent={percentage} color={color} />
                  <p className="mt-1 text-xs text-muted">
                    {isOverBudget
                      ? `${formatCurrencyWhole(cat.current_spend - cat.monthly_budget)} over budget`
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
