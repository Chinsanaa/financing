'use client';

import { useState } from 'react';
import { useApi } from '@/utils/useApi';
import { useCategoryColors } from '@/utils/useCategoryColors';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  ArrowRight,
  Banknote,
  FileSpreadsheet,
  FileText,
  LineChart as LineChartIcon,
  ListTodo,
  Tags,
  Target,
  Upload,
  Wallet,
} from 'lucide-react';
import { Alert, ProgressBar } from '@/components/ui-feedback';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import StatTile, { DeltaChip } from '@/components/ui/StatTile';
import RollingNumber from '@/components/ui/RollingNumber';
import Skeleton, { SkeletonCard, SkeletonChart } from '@/components/ui/Skeleton';
import EmptyState from '@/components/ui/EmptyState';
import {
  formatCurrency,
  formatNumber,
  formatCurrencyWhole,
  formatMonthShort,
  formatMonthLong,
} from '@/utils/format';

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

function greeting(): string {
  const h = new Date().getHours();
  if (h < 5) return 'Up late';
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  // Ticks show month-only ("Jun"); the tooltip carries the full year.
  const labelText = typeof label === 'string' && /^\d{4}-\d{2}$/.test(label) ? formatMonthLong(label) : label;
  return (
    <div className="rounded-lg border border-edge/10 bg-surface px-3 py-2 text-xs shadow-card">
      {labelText && <p className="mb-1 font-medium">{labelText}</p>}
      {payload.map((p: any) => (
        <p key={p.name} className="tabular-nums text-muted">
          {p.payload?.category ?? p.name}: <span className="font-medium text-ink">{formatCurrency(Number(p.value))}</span>
        </p>
      ))}
    </div>
  );
}

export default function StatsTab({
  onNavigate,
  displayName,
}: {
  onNavigate?: (tab: string) => void;
  displayName?: string;
} = {}) {
  const summaryQ = useApi<Summary>('/dashboard/summary');
  const categoryQ = useApi<{ categories: Category[] }>('/dashboard/by-category');
  const trendsQ = useApi<{ trends: Trend[] }>('/dashboard/trends?granularity=month&months=12');
  // Category identity colors (user-chosen, hash fallback) — shared site-wide.
  const { chartColorFor } = useCategoryColors();
  // Donut ↔ legend hover sync.
  const [hovered, setHovered] = useState<string | null>(null);

  if (summaryQ.loading || categoryQ.loading || trendsQ.loading) {
    return (
      <div className="space-y-6">
        <div className="rounded-card border border-edge/8 bg-surface p-6 sm:p-8">
          <Skeleton className="mb-4 h-4 w-40" />
          <Skeleton className="mb-3 h-12 w-64" />
          <Skeleton className="h-4 w-56" />
        </div>
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
  const fillFor = (c: Category) => (c.synthetic ? FOLDED_FILL : chartColorFor(c.category));
  const hoveredCat = byCategory.find((c) => c.category === hovered) || null;

  // Hero: the latest month with data, compared with the month before it.
  const latest = trends.length > 0 ? trends[trends.length - 1] : null;
  const previous = trends.length > 1 ? trends[trends.length - 2] : null;
  const deltaPct =
    latest && previous && previous.total_spend > 0
      ? ((latest.total_spend - previous.total_spend) / previous.total_spend) * 100
      : null;

  const isNewUser = !!summary && summary.total_transactions === 0;
  const firstName = (displayName || '').split(/[@\s]/)[0];

  return (
    <div className="space-y-6">
      {error && <Alert kind="error">{error}</Alert>}

      {/* ── Hero ─────────────────────────────────────────────────── */}
      <Card className="relative overflow-hidden p-6 sm:p-8">
        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="section-label mb-3">
              {greeting()}
              {firstName ? `, ${firstName}` : ''}
            </p>
            {isNewUser ? (
              <>
                <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
                  Let&apos;s decode your <span className="text-accent-strong">spending.</span>
                </h2>
                <p className="mt-2 max-w-md text-sm text-muted">
                  Upload an Alipay or WeChat statement to get started. Your first month appears here in
                  seconds.
                </p>
              </>
            ) : latest ? (
              <>
                <p className="text-sm text-muted">Spent in {formatMonthLong(latest.date)}</p>
                <div className="mt-1 flex flex-wrap items-center gap-3">
                  <p className="font-display text-5xl font-bold tracking-tight sm:text-6xl">
                    <RollingNumber value={latest.total_spend} currency />
                  </p>
                  {deltaPct !== null && (
                    <span className="flex items-center gap-2 text-xs text-muted">
                      <DeltaChip pct={deltaPct} goodWhenDown />
                      vs {previous ? formatMonthShort(previous.date) : 'last month'}
                    </span>
                  )}
                </div>
              </>
            ) : (
              <h2 className="font-display text-3xl font-bold tracking-tight">Your spending at a glance</h2>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            {isNewUser ? (
              <Button size="lg" onClick={() => onNavigate?.('upload')}>
                <Upload className="h-4 w-4" /> Upload a statement
              </Button>
            ) : (
              <>
                <Button variant="outline" onClick={() => onNavigate?.('upload')}>
                  <FileSpreadsheet className="h-4 w-4" /> Upload
                </Button>
                <Button variant="outline" onClick={() => onNavigate?.('label')}>
                  <ListTodo className="h-4 w-4" /> Label
                </Button>
                <Button onClick={() => onNavigate?.('reports')}>
                  <FileText className="h-4 w-4" /> Reports <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </>
            )}
          </div>
        </div>
      </Card>

      {/* ── KPI tiles ────────────────────────────────────────────── */}
      {summary && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile label="Total spend" value={summary.total_spend} currency icon={Wallet} footer="All imported transactions" />
          <StatTile label="Monthly income" value={summary.monthly_income} currency icon={Banknote} footer="From your settings" />
          <StatTile
            label="Labeled"
            value={summary.labeled_transactions}
            icon={Tags}
            footer={`of ${formatNumber(summary.total_transactions, 0)} transactions`}
          />
          <StatTile
            label="Labeling complete"
            value={summary.labeling_percentage}
            decimals={0}
            suffix="%"
            icon={Target}
            footer={<ProgressBar percent={summary.labeling_percentage} height="h-1.5" label="Labeling progress" />}
          />
        </div>
      )}

      {/* ── Charts ───────────────────────────────────────────────── */}
      <div className="grid gap-5 lg:grid-cols-[3fr,2fr]">
        {/* Spending trend */}
        <Card className="p-5">
          <div className="mb-4 flex items-center justify-between">
            <p className="section-label">Monthly spending — last 12 months</p>
            {trends.length > 0 && (
              <p className="text-xs text-muted tabular-nums">
                avg {formatCurrencyWhole(trends.reduce((s, t) => s + t.total_spend, 0) / trends.length)}
              </p>
            )}
          </div>
          {trends.length === 0 ? (
            <EmptyState
              icon={LineChartIcon}
              title="No spending data yet"
              description="Upload a statement to see your monthly spending trend."
            />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={trends} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="rgb(var(--edge) / 0.06)" vertical={false} />
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
                  width={52}
                  tickFormatter={(v: number) => formatCurrencyWhole(v)}
                />
                <Tooltip
                  content={<ChartTooltip />}
                  cursor={{ stroke: 'rgb(var(--accent) / 0.4)', strokeDasharray: '4 4' }}
                />
                <Area
                  type="monotone"
                  dataKey="total_spend"
                  name="Spend"
                  stroke="rgb(var(--accent-strong))"
                  strokeWidth={2.5}
                  fill="rgb(var(--accent))"
                  fillOpacity={0.15}
                  dot={false}
                  activeDot={{ r: 5, strokeWidth: 3, stroke: 'rgb(var(--surface))', fill: 'rgb(var(--accent-strong))' }}
                  animationDuration={1200}
                  animationEasing="ease-out"
                />
              </AreaChart>
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
            <div className="flex flex-col items-center gap-5">
              <div className="relative w-full" onMouseLeave={() => setHovered(null)}>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={byCategory}
                      dataKey="total_amount"
                      nameKey="category"
                      innerRadius={64}
                      outerRadius={92}
                      paddingAngle={2.5}
                      cornerRadius={4}
                      stroke="rgb(var(--surface))"
                      strokeWidth={2}
                      animationDuration={900}
                      onMouseEnter={(_: unknown, i: number) => setHovered(byCategory[i]?.category ?? null)}
                    >
                      {byCategory.map((c) => (
                        <Cell
                          key={c.category}
                          fill={fillFor(c)}
                          fillOpacity={hovered && hovered !== c.category ? 0.3 : 1}
                          style={{ transition: 'fill-opacity 200ms ease-out', cursor: 'pointer' }}
                        />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                {/* Center label: total, or the hovered slice */}
                <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
                  <p className="max-w-[110px] truncate text-[11px] font-medium uppercase tracking-wider text-muted">
                    {hoveredCat ? hoveredCat.category : 'Total'}
                  </p>
                  <p className="font-display text-xl font-bold tabular-nums">
                    {formatCurrencyWhole(hoveredCat ? hoveredCat.total_amount : categoryTotal)}
                  </p>
                </div>
              </div>
              {/* Legend: color follows the entity; text wears text tokens */}
              <ul className="w-full space-y-1">
                {byCategory.map((c) => {
                  const pct = categoryTotal > 0 ? Math.round((c.total_amount / categoryTotal) * 100) : 0;
                  const dim = hovered && hovered !== c.category;
                  return (
                    <li
                      key={c.category}
                      onMouseEnter={() => setHovered(c.category)}
                      onMouseLeave={() => setHovered(null)}
                      className={`rounded-lg px-2 py-1.5 text-sm transition-[opacity,background-color] duration-200 hover:bg-edge/5 ${
                        dim ? 'opacity-50' : ''
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: fillFor(c) }} />
                        <span className="min-w-0 flex-1 truncate">{c.category}</span>
                        <span className="tabular-nums text-muted">
                          {formatCurrencyWhole(c.total_amount)} · {pct}%
                        </span>
                      </div>
                      <div className="ml-[18px] mt-1.5">
                        <ProgressBar percent={pct} fillColor={fillFor(c)} height="h-1" />
                      </div>
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
