'use client';

import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '@/utils/api';
import { useApi } from '@/utils/useApi';
import { useIsDark } from '@/utils/theme';
import StatTile, { FactRow } from '@/components/ui/StatTile';
import Skeleton from '@/components/ui/Skeleton';
import { formatCurrencyWhole, formatMonthLong, formatMonthShort, formatHomeCurrency } from '@/utils/format';
import type { CashflowMonth, CashflowResponse, SummaryResponse } from '@/types/v5';

/**
 * Cash flow (API v5 §3.3 + §3.5): money in, money out and what's left for the
 * current month, plus twelve months of paired bars.
 *
 * - "Money in" for the month follows `summary.month_income` (statements first,
 *   else the Settings income) and says which. The bars only ever show income
 *   found in statements — the contract never fills them from Settings.
 * - Transfers to/from people and money moved between the user's own accounts
 *   are excluded from in/out/net; the footnote says how much was left out.
 * - Colors: income = solid `positive`, spend = solid ink at 45% opacity
 *   (separation and CVD checked with the dataviz validator; the light-mode
 *   contrast warning is relieved by the legend, tooltip and the hidden table).
 *   Solid fills only, per the Ledger design rule.
 */

const INCOME_FILL = 'rgb(var(--positive))';
const SPEND_FILL = 'rgb(var(--ink))';
// Theme-aware: 0.55 in light reaches ~3.6:1 against the paper, 0.45 in dark
// already clears 3:1; never above 0.55 so spend stays quieter than income.
const spendOpacity = (dark: boolean) => (dark ? 0.45 : 0.55);
// Bars are drawn without an entrance animation: Recharts replays it from zero
// whenever the container resizes, which read as the chart blinking out.

function compactYuan(v: number): string {
  const a = Math.abs(v);
  if (a >= 1000) return `¥${Number((v / 1000).toFixed(1))}k`;
  return formatCurrencyWhole(v);
}

function signed(v: number): string {
  return `${v > 0 ? '+' : ''}${formatCurrencyWhole(v)}`;
}

function FlowTooltip({ active, payload, label, spendAlpha }: any) {
  if (!active || !payload?.length) return null;
  const row: CashflowMonth = payload[0].payload;
  return (
    <div className="rounded-md border border-edge/15 bg-surface px-3 py-2 text-xs shadow-card">
      <p className="text-muted">{typeof label === 'string' ? formatMonthLong(label) : label}</p>
      <dl className="mt-1 grid grid-cols-[auto,auto] gap-x-4 gap-y-0.5">
        <dt className="flex items-center gap-1.5 text-muted">
          <span className="h-2 w-2 rounded-[2px]" style={{ backgroundColor: INCOME_FILL }} aria-hidden="true" />
          In
        </dt>
        <dd className="num text-right text-ink">{formatCurrencyWhole(row.income)}</dd>
        <dt className="flex items-center gap-1.5 text-muted">
          <span className="h-2 w-2 rounded-[2px]" style={{ backgroundColor: SPEND_FILL, opacity: spendAlpha }} aria-hidden="true" />
          Out
        </dt>
        <dd className="num text-right text-ink">{formatCurrencyWhole(row.spend)}</dd>
        <dt className="text-muted">Net</dt>
        <dd className="num text-right text-ink">{signed(row.net)}</dd>
      </dl>
    </div>
  );
}

function Legend({ income, spendAlpha }: { income: boolean; spendAlpha: number }) {
  return (
    <p className="flex items-center gap-4 text-[13px] text-muted">
      {income && (
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-[2px]" style={{ backgroundColor: INCOME_FILL }} aria-hidden="true" />
          Money in
        </span>
      )}
      <span className="flex items-center gap-1.5">
        <span
          className="h-2.5 w-2.5 rounded-[2px]"
          style={{ backgroundColor: SPEND_FILL, opacity: spendAlpha }}
          aria-hidden="true"
        />
        Money out
      </span>
    </p>
  );
}

export default function CashFlowCard({
  summary,
  onNavigate,
}: {
  summary: SummaryResponse | null;
  onNavigate?: (tab: string) => void;
}) {
  const q = useApi<CashflowResponse>(api.paths.cashflow(12));
  const spendAlpha = spendOpacity(useIsDark());
  const months = q.data?.months || [];
  const current = months.length > 0 ? months[months.length - 1] : null;
  const homeCurrency = summary?.home?.currency ?? q.data?.currency_home ?? null;
  const rate = summary?.home?.rate ?? null;
  const rateDate = summary?.home?.rate_asof ?? null;

  const monthKey = summary?.month ?? current?.month ?? null;
  const monthName = monthKey ? formatMonthLong(monthKey) : 'this month';

  // Current month: summary first (it knows the Settings fallback), cash flow second.
  const moneyOut = summary?.month_spend ?? current?.spend ?? 0;
  const moneyOutHome = summary?.home ? summary.home.month_spend_home : current?.spend_home ?? null;
  const moneyIn: number | null =
    summary && summary.month !== undefined ? summary.month_income : current && current.income !== 0 ? current.income : null;
  const source = summary?.month_income_source ?? (moneyIn !== null ? 'statements' : null);
  const moneyInHome = summary?.home ? summary.home.month_income_home : current?.income_home ?? null;
  const net = moneyIn !== null ? moneyIn - moneyOut : null;
  const netHome = moneyInHome !== null && moneyOutHome !== null && moneyInHome !== undefined ? moneyInHome - moneyOutHome : null;

  const anyStatementIncome = months.some((m) => m.income !== 0);
  const anyActivity = months.some((m) => m.income !== 0 || m.spend !== 0);
  const moved = q.data?.own_account_moved ?? 0;
  const home = (amount: number | null | undefined) =>
    homeCurrency ? { amount: amount ?? null, currency: homeCurrency, rate, rateDate } : null;

  return (
    <section className="border-t border-ink/80 pt-4" aria-labelledby="cashflow-title">
      <div className="mb-5 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
        <h2 id="cashflow-title" className="font-display text-2xl font-normal">
          Cash flow <span className="text-muted">· {monthName}</span>
        </h2>
        {anyActivity && <Legend income={anyStatementIncome} spendAlpha={spendAlpha} />}
      </div>

      <div className="space-y-6">
        {/* ── This month: in, out, net ─────────────────────────────── */}
        <FactRow>
          <StatTile
            label="Money in"
            value={moneyIn}
            currency
            tone={moneyIn !== null && moneyIn > 0 ? 'positive' : undefined}
            home={moneyIn !== null ? home(moneyInHome) : null}
            footer={
              source === 'statements' ? (
                'From your statements'
              ) : source === 'settings' ? (
                'From your settings — no income found in your statements'
              ) : (
                <span>
                  No income recorded.{' '}
                  <button
                    type="button"
                    onClick={() => onNavigate?.('upload')}
                    className="text-ink underline decoration-edge/40 underline-offset-2 hover:decoration-ink"
                  >
                    Import a bank statement
                  </button>{' '}
                  or set a monthly income in Settings.
                </span>
              )
            }
          />
          <StatTile
            label="Money out"
            value={moneyOut}
            currency
            home={home(moneyOutHome)}
            footer="Spending, refunds netted"
          />
          {net !== null ? (
            <StatTile
              label="Net"
              value={net}
              currency
              tone={net < 0 ? 'danger' : net > 0 ? 'positive' : undefined}
              home={home(netHome)}
              footer={
                source === 'settings'
                  ? 'Settings income minus spending'
                  : net < 0
                  ? 'Spent more than came in'
                  : net > 0
                  ? 'Kept this month'
                  : 'Broke even'
              }
            />
          ) : (
            <div className="flex min-w-0 flex-col py-1">
              <p className="text-[13px] text-muted">Net</p>
              <p className="mt-1 text-sm text-muted">Shows once there is income for {monthName}.</p>
            </div>
          )}
        </FactRow>

        {/* ── Twelve months, paired bars ─────────────────────────── */}
        <div className="min-w-0">
          {q.loading && !q.data ? (
            <Skeleton className="h-[220px] w-full" />
          ) : q.error && !q.data ? (
            <div className="rounded-card border border-dashed border-edge/20 px-6 py-10 text-sm text-muted">
              Cash flow didn&apos;t load.{' '}
              <button type="button" onClick={() => q.reload()} className="text-ink underline underline-offset-2">
                Try again
              </button>
            </div>
          ) : !anyActivity ? (
            <div className="rounded-card border border-dashed border-edge/20 px-6 py-10">
              <h3 className="font-display text-xl font-medium">No money in or out yet</h3>
              <p className="mt-1.5 max-w-[52ch] text-sm text-muted">
                Twelve months of income and spending appear here after your first statement.
              </p>
            </div>
          ) : (
            <>
              <p className="mb-2 text-[13px] text-muted">Per month, in ¥ (CNY)</p>
              <div aria-hidden="true">
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={months} margin={{ top: 4, right: 0, bottom: 0, left: 0 }} barCategoryGap="22%" barGap={2} maxBarSize={28}>
                    <XAxis
                      dataKey="month"
                      tick={{ fill: 'rgb(var(--muted))', fontSize: 11 }}
                      tickLine={false}
                      axisLine={{ stroke: 'rgb(var(--edge) / 0.25)' }}
                      tickFormatter={formatMonthShort}
                      minTickGap={2}
                    />
                    <YAxis
                      tick={{ fill: 'rgb(var(--muted))', fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                      width={44}
                      tickCount={4}
                      tickFormatter={compactYuan}
                    />
                    <Tooltip content={<FlowTooltip spendAlpha={spendAlpha} />} cursor={{ fill: 'rgb(var(--edge) / 0.06)' }} />
                    {anyStatementIncome && (
                      <Bar dataKey="income" name="Money in" fill={INCOME_FILL} radius={[2, 2, 0, 0]} isAnimationActive={false} />
                    )}
                    <Bar
                      dataKey="spend"
                      name="Money out"
                      fill={SPEND_FILL}
                      fillOpacity={spendAlpha}
                      radius={[2, 2, 0, 0]}
                      isAnimationActive={false}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <table className="sr-only">
                <caption>Money in and money out per month, in yuan</caption>
                <thead>
                  <tr>
                    <th scope="col">Month</th>
                    <th scope="col">Money in</th>
                    <th scope="col">Money out</th>
                    <th scope="col">Net</th>
                    {homeCurrency && <th scope="col">Net in {homeCurrency}</th>}
                  </tr>
                </thead>
                <tbody>
                  {months.map((m) => (
                    <tr key={m.month}>
                      <th scope="row">{formatMonthLong(m.month)}</th>
                      <td>{formatCurrencyWhole(m.income)}</td>
                      <td>{formatCurrencyWhole(m.spend)}</td>
                      <td>{signed(m.net)}</td>
                      {homeCurrency && (
                        <td>{m.net_home !== null ? formatHomeCurrency(m.net_home, homeCurrency, 0) : 'no rate'}</td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
              {!anyStatementIncome && (
                <p className="mt-3 text-[13px] text-muted">
                  No income in your statements yet, so only money out is drawn. Import a bank statement with your
                  salary to add money in.
                </p>
              )}
            </>
          )}
        </div>
      </div>

      {q.data && (
        <div className="mt-4 space-y-1 text-[13px] text-muted">
          {current && (current.transfers_in > 0 || current.transfers_out > 0) && (
            <p>
              Transfers with people in {formatMonthShort(current.month)}:{' '}
              <span className="num text-ink">{formatCurrencyWhole(current.transfers_out)}</span> sent,{' '}
              <span className="num text-ink">{formatCurrencyWhole(current.transfers_in)}</span> received — kept out of
              money in and out.
            </p>
          )}
          {moved > 0 && (
            <p>
              <span className="num text-ink">{formatCurrencyWhole(moved)}</span> moved between your own accounts — not
              counted.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
