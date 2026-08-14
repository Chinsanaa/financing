'use client';

import { useState } from 'react';
import { Lightbulb, PiggyBank, Sparkles } from 'lucide-react';
import { useApi } from '@/utils/useApi';
import { Alert, ProgressBar } from '@/components/ui-feedback';
import Card, { SectionHeader } from '@/components/ui/Card';
import EmptyState from '@/components/ui/EmptyState';
import { SkeletonCard, SkeletonRows } from '@/components/ui/Skeleton';
import { chartFillColorForKey } from '@/utils/categoryColors';
import { formatCurrencyWhole, formatMonthLong } from '@/utils/format';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

interface BucketCategory {
  category: string;
  amount: number;
}

interface Bucket {
  target_pct: number;
  target_amount: number | null;
  spent: number;
  categories: BucketCategory[];
}

interface RuleData {
  month: string;
  available_months: string[];
  income: number;
  buckets: {
    needs: Bucket;
    wants: Bucket;
    savings: Bucket;
  };
}

// Fixed bucket colors — these are aggregate buckets, not per-category
// identities, so they stay constant rather than going through
// useCategoryColors(). Picked from the same design-system palette.
const BUCKET_COLOR: Record<'needs' | 'wants' | 'savings', string> = {
  needs: chartFillColorForKey('sky'),
  wants: chartFillColorForKey('amber'),
  savings: chartFillColorForKey('emerald'),
};

const BUCKET_LABEL: Record<'needs' | 'wants' | 'savings', string> = {
  needs: 'Needs',
  wants: 'Wants',
  savings: 'Savings & Investing',
};

const ADVICE_TOLERANCE_PCT = 3;

function ChartTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const p = payload[0];
  return (
    <div className="glass rounded-lg px-3 py-2 text-xs shadow-card">
      <p className="font-medium">{p.name}</p>
      <p className="tabular-nums text-muted">{formatCurrencyWhole(Number(p.value))}</p>
    </div>
  );
}

export default function RuleTab() {
  const [month, setMonth] = useState('');
  const { data, loading, error } = useApi<RuleData>(
    month ? `/dashboard/rule-503020?month=${month}` : '/dashboard/rule-503020'
  );

  const monthOptions = (() => {
    const opts = data?.available_months ? [...data.available_months] : [];
    if (data?.month && !opts.includes(data.month)) opts.unshift(data.month);
    return opts;
  })();
  const selectedMonth = month || data?.month || '';

  if (loading) {
    return (
      <div className="space-y-6">
        <SkeletonCard />
        <SkeletonRows rows={5} />
      </div>
    );
  }

  const buckets = data?.buckets;
  const hasIncome = !!data && data.income > 0;
  const hasAnySpend =
    !!buckets && (buckets.needs.spent > 0 || buckets.wants.spent > 0 || buckets.savings.spent > 0);

  const pieData = buckets
    ? (['needs', 'wants', 'savings'] as const)
        .map((key) => ({ key, name: BUCKET_LABEL[key], value: buckets[key].spent }))
        .filter((d) => d.value > 0)
    : [];

  const pctOfIncome = (spent: number) => (hasIncome ? Math.round((spent / data!.income) * 100) : 0);

  const advice = (() => {
    if (!buckets || !hasIncome) return null;
    const needsPct = pctOfIncome(buckets.needs.spent);
    const wantsPct = pctOfIncome(buckets.wants.spent);
    const savingsPct = pctOfIncome(buckets.savings.spent);

    const onTrack =
      Math.abs(needsPct - 50) <= ADVICE_TOLERANCE_PCT &&
      Math.abs(wantsPct - 30) <= ADVICE_TOLERANCE_PCT &&
      Math.abs(savingsPct - 20) <= ADVICE_TOLERANCE_PCT;
    if (onTrack) {
      return { onTrack: true as const, text: "You're right on track with the 50/30/20 rule this month." };
    }

    // Prioritize a savings shortfall — that's the rule's aspirational goal —
    // then whichever spend bucket runs hottest over its target.
    if (savingsPct < 20 - ADVICE_TOLERANCE_PCT) {
      const topWant = buckets.wants.categories[0];
      const suggestion = topWant
        ? ` Trimming your largest "want" — ${topWant.category} — would free up more room to save.`
        : '';
      return {
        onTrack: false as const,
        text: `You're saving ${savingsPct}% of income (target 20%).${suggestion}`,
      };
    }
    if (needsPct > 50 + ADVICE_TOLERANCE_PCT) {
      const topNeed = buckets.needs.categories[0];
      const suggestion = topNeed ? ` Your biggest needs category is ${topNeed.category} — see if there's room to reduce it.` : '';
      return {
        onTrack: false as const,
        text: `You're spending ${needsPct}% of income on needs (target 50%).${suggestion}`,
      };
    }
    if (wantsPct > 30 + ADVICE_TOLERANCE_PCT) {
      const topWant = buckets.wants.categories[0];
      const suggestion = topWant ? ` Your biggest "want" is ${topWant.category} — consider cutting back there first.` : '';
      return {
        onTrack: false as const,
        text: `You're spending ${wantsPct}% of income on wants (target 30%).${suggestion}`,
      };
    }
    return { onTrack: true as const, text: "You're right on track with the 50/30/20 rule this month." };
  })();

  return (
    <div className="space-y-6">
      <SectionHeader label="Planning" title="50/30/20 rule" />

      {error && <Alert kind="error">{error}</Alert>}

      {data && !hasIncome && (
        <Alert kind="info">
          Set your monthly income in Settings to see targets and personalized guidance — spend is still
          shown below.
        </Alert>
      )}

      <Card className="p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <p className="section-label">
            {selectedMonth ? formatMonthLong(selectedMonth) : 'This month'}
          </p>
          {monthOptions.length > 1 && (
            <select
              value={selectedMonth}
              onChange={(e) => setMonth(e.target.value)}
              className="rounded-pill border border-edge/20 bg-surface px-3 py-1.5 text-sm text-ink focus:border-accent-strong/50 focus:outline-none focus:ring-2 focus:ring-accent/20"
            >
              {monthOptions.map((m) => (
                <option key={m} value={m}>
                  {formatMonthLong(m)}
                </option>
              ))}
            </select>
          )}
        </div>

        {!hasAnySpend ? (
          <EmptyState
            icon={PiggyBank}
            title="No spend yet this month"
            description="Categorize some transactions to see your Needs/Wants/Savings split."
          />
        ) : (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,220px),1fr]">
            <div className="flex items-center justify-center">
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={52}
                    outerRadius={80}
                    paddingAngle={2}
                    stroke="rgb(var(--surface))"
                    strokeWidth={2}
                  >
                    {pieData.map((d) => (
                      <Cell key={d.key} fill={BUCKET_COLOR[d.key]} />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="space-y-5">
              {(['needs', 'wants', 'savings'] as const).map((key) => {
                const b = buckets![key];
                const actualPct = pctOfIncome(b.spent);
                return (
                  <div key={key}>
                    <div className="mb-1 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <span
                          className="h-2.5 w-2.5 shrink-0 rounded-full"
                          style={{ backgroundColor: BUCKET_COLOR[key] }}
                        />
                        <span className="text-sm font-semibold">{BUCKET_LABEL[key]}</span>
                      </div>
                      <p className="text-sm tabular-nums text-muted">
                        {formatCurrencyWhole(b.spent)}
                        {hasIncome && ` · ${actualPct}%`}
                        {b.target_amount !== null && ` of ${formatCurrencyWhole(b.target_amount)} (${b.target_pct}%) target`}
                      </p>
                    </div>
                    <ProgressBar percent={hasIncome ? actualPct : 0} fillColor={BUCKET_COLOR[key]} />
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </Card>

      {advice && (
        <div
          className={`flex items-start gap-3 rounded-card border p-5 ${
            advice.onTrack ? 'border-success/25 bg-success/10' : 'border-[color:var(--chart-5)]/25 bg-[color:var(--chart-5)]/10'
          }`}
        >
          {advice.onTrack ? (
            <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-success" />
          ) : (
            <Lightbulb className="mt-0.5 h-5 w-5 shrink-0 text-[color:var(--chart-5)]" />
          )}
          <div>
            <p className={`font-medium ${advice.onTrack ? 'text-success' : 'text-[color:var(--chart-5)]'}`}>
              {advice.onTrack ? 'On track' : 'Guidance'}
            </p>
            <p className="mt-0.5 text-sm text-muted">{advice.text}</p>
          </div>
        </div>
      )}
    </div>
  );
}
