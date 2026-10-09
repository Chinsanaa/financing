'use client';

import { useState } from 'react';
import { useApi } from '@/utils/useApi';
import { useCategoryColors } from '@/utils/useCategoryColors';
import { Bar, BarChart, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ArrowRight, FileSpreadsheet, ListTodo, Upload } from 'lucide-react';
import { Alert, ProgressBar } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import StatTile, { DeltaChip, FactRow } from '@/components/ui/StatTile';
import RollingNumber from '@/components/ui/RollingNumber';
import Skeleton from '@/components/ui/Skeleton';
import EmptyState from '@/components/ui/EmptyState';
import { formatCurrency, formatCurrencyWhole, formatMonthLong, formatMonthShort, formatNumber } from '@/utils/format';

interface Summary {
  total_transactions: number;
  labeled_transactions: number;
  labeling_percentage: number;
  total_spend: number;
  monthly_income: number;
}

interface Category {
  category: string;
  total_amount: number;
  transaction_count: number;
  /** True for the folded tail bucket — painted neutral so it can't collide
   *  with a real category that happens to be named "Other". */
  synthetic?: boolean;
}

interface Trend {
  date: string;
  total_spend: number;
}

/** Neutral paint for the folded tail bucket. */
const FOLDED_FILL = 'rgb(var(--edge) / 0.28)';
/** Categories shown by name before the tail folds into "Everything else". */
const SHOWN = 6;

function MonthTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-edge/15 bg-surface px-3 py-2 text-xs shadow-card">
      <p className="text-muted">{typeof label === 'string' ? formatMonthLong(label) : label}</p>
      <p className="num mt-0.5 text-base text-ink">{formatCurrency(Number(payload[0].value))}</p>
    </div>
  );
}

export default function StatsTab({
  onNavigate,
}: {
  onNavigate?: (tab: string) => void;
  displayName?: string;
} = {}) {
  const summaryQ = useApi<Summary>('/dashboard/summary');
  const categoryQ = useApi<{ categories: Category[] }>('/dashboard/by-category');
  const trendsQ = useApi<{ trends: Trend[] }>('/dashboard/trends?granularity=month&months=12');
  // Category identity colors (user-chosen, hash fallback) — shared site-wide.
  const { chartColorFor } = useCategoryColors();
  // Stacked bar ↔ ledger rows hover sync.
  const [hovered, setHovered] = useState<string | null>(null);
  const [hoverMonth, setHoverMonth] = useState<number | null>(null);

  if (summaryQ.loading || categoryQ.loading || trendsQ.loading) {
    return (
      <div className="space-y-10">
        <div>
          <Skeleton className="mb-3 h-4 w-40" />
          <Skeleton className="h-16 w-72" />
        </div>
        <Skeleton className="h-20 w-full" />
        <div className="grid gap-12 lg:grid-cols-[3fr,2fr]">
          <Skeleton className="h-72 w-full" />
          <Skeleton className="h-72 w-full" />
        </div>
      </div>
    );
  }

  const summary = summaryQ.data;
  const sorted = [...(categoryQ.data?.categories || [])].sort((a, b) => b.total_amount - a.total_amount);
  const byCategory: Category[] =
    sorted.length > SHOWN
      ? [
          ...sorted.slice(0, SHOWN - 1),
          sorted.slice(SHOWN - 1).reduce(
            (acc, c) => ({
              ...acc,
              total_amount: acc.total_amount + c.total_amount,
              transaction_count: acc.transaction_count + c.transaction_count,
            }),
            { category: 'Everything else', total_amount: 0, transaction_count: 0, synthetic: true } as Category
          ),
        ]
      : sorted;
  const trends = trendsQ.data?.trends || [];
  const error = summaryQ.error || categoryQ.error || trendsQ.error;
  const categoryTotal = byCategory.reduce((sum, c) => sum + c.total_amount, 0);
  const fillFor = (c: Category) => (c.synthetic ? FOLDED_FILL : chartColorFor(c.category));

  // Headline: the latest month with data, compared with the month before it.
  const latest = trends.length > 0 ? trends[trends.length - 1] : null;
  const previous = trends.length > 1 ? trends[trends.length - 2] : null;
  const deltaPct =
    latest && previous && previous.total_spend > 0
      ? ((latest.total_spend - previous.total_spend) / previous.total_spend) * 100
      : null;
  const average = trends.length > 0 ? trends.reduce((s, t) => s + t.total_spend, 0) / trends.length : 0;
  const leftOver = summary && latest && summary.monthly_income > 0 ? summary.monthly_income - latest.total_spend : null;

  const isNewUser = !!summary && summary.total_transactions === 0;

  if (isNewUser) {
    return (
      <div className="max-w-2xl space-y-6">
        {error && <Alert kind="error">{error}</Alert>}
        <h1 className="font-display text-5xl font-normal leading-[1.02] tracking-[-0.02em] sm:text-6xl">
          Your first statement goes here.
        </h1>
        <p className="max-w-[52ch] text-[15px] text-muted">
          Upload an Alipay or WeChat Pay export. Your first month appears here in seconds, and the model starts
          learning from the merchants you label.
        </p>
        <Button size="lg" onClick={() => onNavigate?.('upload')}>
          <Upload className="h-4 w-4" /> Upload a statement
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-10">
      {error && <Alert kind="error">{error}</Alert>}

      {/* ── Headline: the month's figure ─────────────────────────── */}
      <section className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          {latest ? (
            <>
              <p className="text-[15px] text-muted">Spent in {formatMonthLong(latest.date)}</p>
              <h1 className="num mt-1 text-6xl font-normal leading-none tracking-[-0.02em] sm:text-7xl lg:text-8xl">
                <RollingNumber value={latest.total_spend} currency />
              </h1>
              {deltaPct !== null && previous && (
                <p className="mt-3 flex items-center gap-2 text-[13px] text-muted">
                  <DeltaChip pct={deltaPct} goodWhenDown /> vs {formatMonthLong(previous.date)}
                </p>
              )}
            </>
          ) : (
            <h1 className="font-display text-4xl font-normal">Your spending at a glance</h1>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" onClick={() => onNavigate?.('upload')}>
            <FileSpreadsheet className="h-4 w-4" /> Upload
          </Button>
          <Button variant="outline" onClick={() => onNavigate?.('label')}>
            <ListTodo className="h-4 w-4" /> Label
          </Button>
          <Button variant="ghost" onClick={() => onNavigate?.('reports')}>
            All transactions <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      </section>

      {/* ── Facts: one ruled row, not four boxes ─────────────────── */}
      {summary && (
        <FactRow>
          <StatTile label="Monthly income" value={summary.monthly_income} currency footer="From your settings" />
          {leftOver !== null ? (
            <StatTile
              label={`Left over in ${latest ? formatMonthShort(latest.date) : 'the month'}`}
              value={leftOver}
              currency
              tone={leftOver < 0 ? 'danger' : undefined}
              footer={leftOver < 0 ? 'Spent more than income' : 'Income minus spending'}
            />
          ) : (
            <StatTile label="Transactions" value={summary.total_transactions} footer="Imported so far" />
          )}
          <StatTile
            label="Labeled"
            value={summary.labeling_percentage}
            suffix="%"
            footer={
              <span className="block">
                <span className="mb-1.5 block">
                  {formatNumber(summary.labeled_transactions, 0)} of {formatNumber(summary.total_transactions, 0)}
                </span>
                <ProgressBar percent={summary.labeling_percentage} height="h-1" label="Labeling progress" />
              </span>
            }
          />
          <StatTile label="All imported spending" value={summary.total_spend} currency footer="Every month so far" />
        </FactRow>
      )}

      <div className="grid gap-x-14 gap-y-12 lg:grid-cols-[3fr,2fr]">
        {/* ── Monthly totals: discrete months → bars ─────────────── */}
        <section className="border-t border-ink/80 pt-4">
          <div className="mb-5 flex items-baseline justify-between gap-4">
            <h2 className="font-display text-2xl font-normal">Twelve months</h2>
            {trends.length > 0 && (
              <p className="text-[13px] text-muted">
                <span className="mr-1.5 inline-block w-5 border-t border-dashed border-ink/60 align-middle" aria-hidden="true" />
                average <span className="num text-ink">{formatCurrencyWhole(average)}</span>
              </p>
            )}
          </div>
          {trends.length === 0 ? (
            <EmptyState title="No months yet" description="Upload a statement to see your monthly totals here." />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart
                data={trends}
                margin={{ top: 8, right: 0, bottom: 0, left: 0 }}
                barCategoryGap="22%"
                onMouseMove={(st: any) => setHoverMonth(st?.isTooltipActive ? st.activeTooltipIndex ?? null : null)}
                onMouseLeave={() => setHoverMonth(null)}
              >
                <XAxis
                  dataKey="date"
                  tick={{ fill: 'rgb(var(--muted))', fontSize: 11 }}
                  tickLine={false}
                  axisLine={{ stroke: 'rgb(var(--edge) / 0.25)' }}
                  tickFormatter={formatMonthShort}
                  interval={0}
                  minTickGap={0}
                />
                <YAxis
                  tick={{ fill: 'rgb(var(--muted))', fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  width={52}
                  tickCount={4}
                  tickFormatter={(v: number) => formatCurrencyWhole(v)}
                />
                <Tooltip content={<MonthTooltip />} cursor={false} />
                <ReferenceLine y={average} stroke="rgb(var(--ink) / 0.6)" strokeDasharray="4 4" />
                <Bar dataKey="total_spend" name="Spent" radius={[2, 2, 0, 0]} animationDuration={700} animationEasing="ease-out">
                  {trends.map((t, i) => {
                    const isLatest = i === trends.length - 1;
                    const isHover = hoverMonth === i;
                    return (
                      <Cell
                        key={t.date}
                        fill={isLatest ? 'rgb(var(--accent))' : 'rgb(var(--ink))'}
                        fillOpacity={isLatest ? 1 : isHover ? 0.55 : 0.16}
                        style={{ transition: 'fill-opacity 150ms ease-out' }}
                      />
                    );
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </section>

        {/* ── Where it went: one bold bar + ranked ledger rows ───── */}
        <section className="border-t border-ink/80 pt-4" onMouseLeave={() => setHovered(null)}>
          <div className="mb-5 flex items-baseline justify-between gap-4">
            <h2 className="font-display text-2xl font-normal">Where it went</h2>
            {categoryTotal > 0 && <p className="num text-[15px] text-muted">{formatCurrencyWhole(categoryTotal)}</p>}
          </div>
          {byCategory.length === 0 ? (
            <EmptyState title="Nothing categorized yet" description="Label a few transactions and the split shows up here." />
          ) : (
            <>
              <div className="flex h-11 w-full gap-[2px]" role="img" aria-label="Spending by category">
                {byCategory.map((c) => (
                  <span
                    key={c.category}
                    onMouseEnter={() => setHovered(c.category)}
                    className="progress-fill h-full transition-opacity duration-150"
                    style={{
                      width: `${categoryTotal > 0 ? (c.total_amount / categoryTotal) * 100 : 0}%`,
                      backgroundColor: fillFor(c),
                      opacity: hovered && hovered !== c.category ? 0.3 : 1,
                    }}
                  />
                ))}
              </div>
              <table className="mt-4 w-full text-sm">
                <tbody>
                  {byCategory.map((c, i) => {
                    const pct = categoryTotal > 0 ? (c.total_amount / categoryTotal) * 100 : 0;
                    const dim = hovered && hovered !== c.category;
                    return (
                      <tr
                        key={c.category}
                        onMouseEnter={() => setHovered(c.category)}
                        className={`border-b border-edge/10 transition-opacity duration-150 ${dim ? 'opacity-45' : ''}`}
                      >
                        <td className="num w-6 py-2.5 text-[13px] text-muted">{c.synthetic ? '' : i + 1}</td>
                        <td className="py-2.5">
                          <span className="flex items-center gap-2">
                            <span className="h-2.5 w-2.5 shrink-0 rounded-[2px]" style={{ backgroundColor: fillFor(c) }} aria-hidden="true" />
                            <span className={c.synthetic ? 'text-muted' : ''}>{c.category}</span>
                          </span>
                        </td>
                        <td className="hidden py-2.5 text-right text-[13px] text-muted sm:table-cell">
                          {formatNumber(c.transaction_count, 0)} {c.transaction_count === 1 ? 'payment' : 'payments'}
                        </td>
                        <td className="num py-2.5 pl-4 text-right">{formatCurrencyWhole(c.total_amount)}</td>
                        <td className="num w-12 py-2.5 text-right text-muted">{Math.round(pct)}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
