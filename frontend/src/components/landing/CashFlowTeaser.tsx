'use client';

import { m } from 'framer-motion';
import { formatCurrency } from '@/utils/format';
import { SAMPLE_CASHFLOW as S } from './sampleStatement';

/**
 * Money in vs money out, flat bars on one shared scale. Mirrors the v5
 * cash-flow rules (docs/contracts/API_V5.md §1.1, §3.5): red packets and AA
 * split-bill paybacks are transfers, not income; transfers between your own
 * accounts are shown but never counted; net = income − spending.
 * Positive (teal-green) = money in, ink = money out, a lighter step of the
 * same color = transfers with people. Every segment is named in text.
 */

const MAX = Math.max(S.income + S.transfersIn, S.spend + S.transfersOut);
const pct = (v: number) => `${(v / MAX) * 100}%`;
const yuan = (v: number) => formatCurrency(v, 0);

function Bar({ children, label }: { children: React.ReactNode; label: string }) {
  return (
    <m.div
      role="img"
      aria-label={label}
      className="flex h-9 w-full gap-[2px] sm:h-11"
      style={{ transformOrigin: 'left center' }}
      initial={{ scaleX: 0 }}
      whileInView={{ scaleX: 1 }}
      viewport={{ once: true, amount: 0.6 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </m.div>
  );
}

function Legend({ items }: { items: [string, number, string][] }) {
  return (
    <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-1.5 text-[13px]">
      {items.map(([name, v, swatch]) => (
        <div key={name} className="flex items-center gap-2">
          <span aria-hidden="true" className={`h-2.5 w-2.5 rounded-[2px] ${swatch}`} />
          <dt className="text-muted">{name}</dt>
          <dd className="num text-ink">{yuan(v)}</dd>
        </div>
      ))}
    </dl>
  );
}

export default function CashFlowTeaser() {
  const net = S.income - S.spend;
  return (
    <figure className="border-t border-ink/80 pt-6">
      <figcaption className="flex flex-wrap items-baseline justify-between gap-2 text-[13px]">
        <span className="text-muted">September cash flow</span>
        <span className="rounded-[3px] border border-edge/20 px-1.5 py-[1px] text-[11px] font-medium text-muted">Sample data</span>
      </figcaption>

      <div className="mt-6">
        <div className="flex items-baseline justify-between">
          <p className="font-medium">Money in</p>
          <p className="num text-2xl text-positive">{yuan(S.income + S.transfersIn)}</p>
        </div>
        <div className="mt-2">
          <Bar label={`Money in: salary ${yuan(S.income)}, red packets and paybacks ${yuan(S.transfersIn)}`}>
            <span className="h-full bg-positive" style={{ width: pct(S.income) }} />
            <span className="h-full bg-positive/40" style={{ width: pct(S.transfersIn) }} />
          </Bar>
        </div>
        <Legend
          items={[
            ['Salary', S.income, 'bg-positive'],
            ['Red packets & AA paybacks', S.transfersIn, 'bg-positive/40'],
          ]}
        />
      </div>

      <div className="mt-8">
        <div className="flex items-baseline justify-between">
          <p className="font-medium">Money out</p>
          <p className="num text-2xl">{yuan(S.spend + S.transfersOut)}</p>
        </div>
        <div className="mt-2">
          <Bar label={`Money out: spending ${yuan(S.spend)}, sent to people ${yuan(S.transfersOut)}`}>
            <span className="h-full bg-ink" style={{ width: pct(S.spend) }} />
            <span className="h-full bg-ink/35" style={{ width: pct(S.transfersOut) }} />
          </Bar>
        </div>
        <Legend
          items={[
            ['Spending', S.spend, 'bg-ink'],
            ['Red packets & transfers sent', S.transfersOut, 'bg-ink/35'],
          ]}
        />
      </div>

      <div className="mt-8 flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
        <div
          className="flex h-7 shrink-0 items-center justify-center rounded-[2px] border-[1.5px] border-dashed border-edge/40 text-[15px] text-muted"
          style={{ width: pct(S.ownAccount) }}
          aria-hidden="true"
        >
          ⇄
        </div>
        <p className="text-[13px] text-muted">
          <span className="num text-ink">{yuan(S.ownAccount)}</span> moved between your own accounts (card repayment,
          wallet top-up) · <span className="text-ink">not counted</span>
        </p>
      </div>

      <div className="mt-8 flex items-baseline justify-between border-t-2 border-ink/80 pt-4">
        <p>
          <span className="font-medium">Net</span>{' '}
          <span className="text-[13px] text-muted">income minus spending</span>
        </p>
        <p className="num text-3xl text-positive">+{yuan(net)}</p>
      </div>
    </figure>
  );
}
