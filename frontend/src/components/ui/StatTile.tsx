'use client';

import { ReactNode } from 'react';
import RollingNumber from './RollingNumber';

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
  footer,
  className = '',
}: {
  label: string;
  value: number;
  currency?: boolean;
  decimals?: number;
  suffix?: string;
  tone?: 'success' | 'danger' | 'warn';
  footer?: ReactNode;
  className?: string;
}) {
  const toneClass =
    tone === 'success' ? 'text-success' : tone === 'danger' ? 'text-danger' : tone === 'warn' ? 'text-warn' : '';
  return (
    <div className={`flex min-w-0 flex-col py-1 ${className}`}>
      <p className="text-[13px] text-muted">{label}</p>
      <p className={`num mt-1 text-[2rem] font-normal leading-none tracking-[-0.01em] ${toneClass}`}>
        <RollingNumber value={value} currency={currency} decimals={decimals} suffix={suffix} />
      </p>
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
