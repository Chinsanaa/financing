'use client';

import { ReactNode } from 'react';
import RollingNumber from './RollingNumber';
import { rateTooltip } from './MoneyPair';
import { formatHomeCurrency } from '@/utils/format';

/** Home-currency equivalent of a CNY figure (docs/contracts/API_V5.md §0). */
export interface HomeAmount {
  /** `null` = no usable rate: the line is hidden. */
  amount: number | null | undefined;
  currency: string;
  rate?: number | null;
  rateDate?: string | null;
  /** Some rows needed a fallback (older) rate: adds an "approx." note. */
  approx?: boolean;
}

/**
 * The muted "≈ $1,110" line under a CNY figure. Renders nothing without a
 * home currency or a rate, so callers can pass `summary.home` fields blindly.
 * Same reading as MoneyPair's home line, without re-rendering the CNY figure
 * (tiles roll theirs with RollingNumber).
 */
export function HomeLine({
  home,
  decimals = 0,
  className = '',
}: {
  home?: HomeAmount | null;
  decimals?: number;
  className?: string;
}) {
  if (!home || !home.currency || home.amount === null || home.amount === undefined || !Number.isFinite(home.amount)) {
    return null;
  }
  const rateTitle = rateTooltip(home.rate ?? undefined, home.rateDate ?? undefined);
  const approxTitle = 'Some older transactions use the nearest available ECB rate, so this total is approximate.';
  return (
    <span className={`num block text-muted ${className}`} title={home.approx ? approxTitle : rateTitle}>
      <span aria-hidden="true">≈ </span>
      <span className="sr-only">approximately </span>
      {formatHomeCurrency(home.amount, home.currency, decimals)}
      {home.approx && (
        <span className="ml-1.5 font-sans text-[11px] text-muted underline decoration-dotted underline-offset-2">
          approx.
          <span className="sr-only"> {approxTitle}</span>
        </span>
      )}
    </span>
  );
}

/**
 * A ledger "fact": caption, a serif rolling figure and an optional footer
 * line. Deliberately not a card — put facts in a row separated by hairlines
 * (`FactRow`). `tone` colors only the figure, and callers pair it with a
 * word/icon so color isn't the only cue. No icon chips.
 */
export default function StatTile({
  label,
  value,
  currency = false,
  decimals = 0,
  suffix,
  tone,
  home,
  footer,
  className = '',
}: {
  label: string;
  value: number;
  currency?: boolean;
  decimals?: number;
  suffix?: string;
  tone?: 'success' | 'danger' | 'warn' | 'positive';
  /** Optional home-currency line under the figure (hidden when null). */
  home?: HomeAmount | null;
  footer?: ReactNode;
  className?: string;
}) {
  const toneClass =
    tone === 'success' ? 'text-success' : tone === 'danger' ? 'text-danger' : tone === 'warn' ? 'text-warn' : tone === 'positive' ? 'text-positive' : '';
  return (
    <div className={`flex min-w-0 flex-col py-1 ${className}`}>
      <p className="text-[13px] text-muted">{label}</p>
      <p className={`num mt-1 text-[2rem] font-normal leading-none tracking-[-0.01em] ${toneClass}`}>
        <RollingNumber value={value} currency={currency} decimals={decimals} suffix={suffix} />
      </p>
      <HomeLine home={home} className="mt-1.5 text-sm" />
      {footer && <div className="mt-2 text-xs text-muted">{footer}</div>}
    </div>
  );
}

/** A row of facts divided by vertical hairlines (stacks on phones). */
export function FactRow({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`grid grid-cols-2 gap-y-6 border-y border-edge/12 py-5 sm:flex sm:divide-x sm:divide-edge/12 [&>*]:sm:flex-1 [&>*]:sm:px-6 [&>*:first-child]:sm:pl-0 ${className}`}
    >
      {children}
    </div>
  );
}

/** Small ▲/▼ percentage chip. `goodWhenDown` for spend-type metrics. */
export function DeltaChip({ pct, goodWhenDown = true }: { pct: number; goodWhenDown?: boolean }) {
  if (!Number.isFinite(pct)) return null;
  const up = pct > 0;
  const good = pct === 0 ? null : up !== goodWhenDown;
  const cls = good === null ? 'text-muted' : good ? 'text-success' : 'text-danger';
  return (
    <span className={`inline-flex items-center gap-1 text-[13px] font-medium tabular-nums ${cls}`}>
      <span aria-hidden="true">{up ? '▲' : pct < 0 ? '▼' : '•'}</span>
      {Math.abs(Math.round(pct))}%<span className="sr-only">{up ? ' up' : pct < 0 ? ' down' : ''}</span>
    </span>
  );
}
