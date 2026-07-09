'use client';

import { useApi } from '@/utils/useApi';
import { useCategoryColors } from '@/utils/useCategoryColors';
import {
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Alert } from '@/components/ui';
import Card, { SectionHeader } from '@/components/ui/Card';
import { AnimatedNumber } from '@/components/ui/motion';
import { SkeletonCard, SkeletonChart } from '@/components/ui/Skeleton';
import EmptyState from '@/components/ui/EmptyState';
import { LineChart as LineChartIcon } from 'lucide-react';
import {
  formatCurrency,
  formatNumber,
  formatCurrencyWhole,
  formatMonthShort,
  formatMonthLong,
  CURRENCY_SYMBOL,
} from '@/utils/format';

interface Summary {
  total_transactions: number;
  labeled_transactions: number;
  labeling_percentage: number;
  total_spend: number;
}

interface Category {
  category: string;
  total_amount: number;
  transaction_count: number;
  /** True for the folded ">5 categories" bucket — painted neutral so it can't
   *  collide with a real category that happens to be named "Other". */
  synthetic?: boolean;
}

interface Trend {
  date: string;
  total_spend: number;
}

/** Neutral paint for the synthetic fold bucket. */
const FOLDED_FILL = 'rgb(var(--muted))';

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  // Ticks show month-only ("Jun"); the tooltip carries the full year.
  const labelText = typeof label === 'string' && /^\d{4}-\d{2}$/.test(label) ? formatMonthLong(label) : label;
  return (
    <div className="glass rounded-lg px-3 py-2 text-xs shadow-card">
      {labelText && <p className="mb-1 font-medium">{labelText}</p>}
      {payload.map((p: any) => (
        <p key={p.name} className="tabular-nums text-muted">
          {p.payload?.category ?? p.name}: <span className="font-medium text-ink">{formatCurrency(Number(p.value))}</span>
        </p>
      ))}
    </div>
  );
}

export default function StatsTab() {
  const summaryQ = useApi<Summary>('/dashboard/summary');
  const categoryQ = useApi<{ categories: Category[] }>('/dashboard/by-category');
  const trendsQ = useApi<{ trends: Trend[] }>('/dashboard/trends?granularity=month&months=12');
  // Category identity colors (user-chosen, hash fallback) — shared site-wide.
  const { chartColorFor } = useCategoryColors();

  if (summaryQ.loading || categoryQ.loading || trendsQ.loading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        <div className="grid gap-5 lg:grid-cols-[3fr,2fr]">
          <SkeletonChart />
          <SkeletonChart />
        </div>
      </div>
    );
  }

  const summary = summaryQ.data;
  const sorted = [...(categoryQ.data?.categories || [])].sort(
    (a, b) => b.total_amount - a.total_amount
  );
  // >5 categories fold into a synthetic "Other" bucket to keep the pie legible.
  const byCategory: Category[] =
    sorted.length > 5
      ? [
          ...sorted.slice(0, 4),
          sorted.slice(4).reduce(
            (acc, c) => ({
              category: 'Other',
              total_amount: acc.total_amount + c.total_amount,
              transaction_count: acc.transaction_count + c.transaction_count,
              synthetic: true,
            }),
            { category: 'Other', total_amount: 0, transaction_count: 0, synthetic: true }
          ),
        ]
      : sorted;
  const trends = trendsQ.data?.trends || [];
  const error = summaryQ.error || categoryQ.error || trendsQ.error;
  const categoryTotal = byCategory.reduce((sum, c) => sum + c.total_amount, 0);

  const stats = summary
    ? [
        { label: 'Total spend', value: summary.total_spend, prefix: CURRENCY_SYMBOL, decimals: 0 },
        { label: 'Transactions', value: summary.total_transactions },
        { label: 'Labeled', value: summary.labeled_transactions },
        { label: 'Labeling complete', value: summary.labeling_percentage, suffix: '%' },
      ]
    : [];

  return (
    <div className="space-y-6">
      <SectionHeader label="Overview" title="Your spending at a glance" />

      {error && <Alert kind="error">{error}</Alert>}

      {/* Stat tiles */}
      {summary && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((s) => (
            <Card key={s.label} hover className="p-5">
              <p className="section-label mb-2">{s.label}</p>
              <p className="font-display text-3xl font-bold tabular-nums tracking-tight">
                <AnimatedNumber
                  value={s.value}
                  format={(n) => {
                    if (s.prefix === CURRENCY_SYMBOL) {
                      return formatCurrencyWhole(n).replace(CURRENCY_SYMBOL, '');
                    }
                    return formatNumber(n, s.decimals ?? 0);
                  }}
                />
                {s.prefix}
                {s.suffix}
              </p>
            </Card>
          ))}
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[3fr,2fr]">
        {/* Spending trend */}
        <Card className="p-5">
          <p className="section-label mb-4">Monthly spending — last 12 months</p>
          {trends.length === 0 ? (
            <EmptyState
              icon={LineChartIcon}
              title="No spending data yet"
              description="Upload a statement to see your monthly spending trend."
            />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trends} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="rgb(var(--edge) / 0.08)" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: 'rgb(var(--muted))', fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  minTickGap={16}
                  tickFormatter={formatMonthShort}
                />
                <YAxis
                  tick={{ fill: 'rgb(var(--muted))', fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  width={44}
                  tickFormatter={(v: number) => formatCurrencyWhole(v)}
                />
                <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgb(var(--edge) / 0.2)' }} />
                <Line
                  type="monotone"
                  dataKey="total_spend"
                  name="Spend"
                  stroke="rgb(var(--accent))"
                  strokeWidth={2}
                  dot={{ r: 3, strokeWidth: 0, fill: 'rgb(var(--accent))' }}
                  activeDot={{ r: 4, strokeWidth: 2, stroke: 'rgb(var(--surface))' }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Category split */}
        <Card className="p-5">
          <p className="section-label mb-4">Spending by category</p>
          {byCategory.length === 0 ? (
            <EmptyState
              icon={LineChartIcon}
              title="Nothing categorized yet"
              description="Label a few transactions and the split shows up here."
            />
          ) : (
            <div className="flex flex-col items-center gap-4">
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={byCategory}
                    dataKey="total_amount"
                    nameKey="category"
                    innerRadius={52}
                    outerRadius={80}
                    paddingAngle={2}
                    stroke="rgb(var(--surface))"
                    strokeWidth={2}
                  >
                    {byCategory.map((c) => (
                      <Cell
                        key={c.category}
                        fill={c.synthetic ? FOLDED_FILL : chartColorFor(c.category)}
                      />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              {/* Legend: color follows the entity; text wears text tokens */}
              <ul className="w-full space-y-1.5">
                {byCategory.map((c) => {
                  const pct = categoryTotal > 0 ? Math.round((c.total_amount / categoryTotal) * 100) : 0;
                  return (
                    <li key={c.category} className="flex items-center gap-2 text-sm">
                      <span
                        className="h-2.5 w-2.5 shrink-0 rounded-full"
                        style={{ backgroundColor: c.synthetic ? FOLDED_FILL : chartColorFor(c.category) }}
                      />
                      <span className="min-w-0 flex-1 truncate">{c.category}</span>
                      <span className="tabular-nums text-muted">
                        {formatCurrencyWhole(c.total_amount)} · {pct}%
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
