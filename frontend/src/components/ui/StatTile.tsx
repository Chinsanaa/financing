'use client';

import { ReactNode } from 'react';
import { LucideIcon } from 'lucide-react';
import Card from './Card';
import RollingNumber from './RollingNumber';

/**
 * KPI tile: eyebrow label + icon chip, a big rolling number, and an
 * optional footer line (delta chip, "of N", hint). `tone` colors only the
 * number, and callers pair it with a word/icon so color isn't the only cue.
 */
export default function StatTile({
  label,
  value,
  currency = false,
  decimals = 0,
  suffix,
  icon: Icon,
  tone,
  footer,
  className = '',
}: {
  label: string;
  value: number;
  currency?: boolean;
  decimals?: number;
  suffix?: string;
  icon?: LucideIcon;
  tone?: 'success' | 'danger' | 'warn';
  footer?: ReactNode;
  className?: string;
}) {
  const toneClass =
    tone === 'success'
      ? 'text-success'
      : tone === 'danger'
      ? 'text-danger'
      : tone === 'warn'
      ? 'text-warn'
      : '';
  return (
    <Card hover className={`group flex flex-col p-5 ${className}`}>
      <div className="mb-3 flex items-center justify-between gap-2">
        <p className="section-label">{label}</p>
        {Icon && (
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-edge/5 text-muted transition-colors duration-200 group-hover:text-ink">
            <Icon className="h-4 w-4" />
          </span>
        )}
      </div>
      <p className={`font-display text-3xl font-bold tracking-tight ${toneClass}`}>
        <RollingNumber value={value} currency={currency} decimals={decimals} suffix={suffix} />
      </p>
      {footer && <div className="mt-2 text-xs text-muted">{footer}</div>}
    </Card>
  );
}

/** Small ▲/▼ percentage chip. `goodWhenDown` for spend-type metrics. */
export function DeltaChip({ pct, goodWhenDown = true }: { pct: number; goodWhenDown?: boolean }) {
  if (!Number.isFinite(pct)) return null;
  const up = pct > 0;
  const good = pct === 0 ? null : up !== goodWhenDown;
  const cls =
    good === null ? 'bg-edge/8 text-muted' : good ? 'bg-success/12 text-success' : 'bg-danger/12 text-danger';
  return (
    <span className={`inline-flex items-center gap-0.5 rounded-pill px-2 py-0.5 text-[11px] font-semibold tabular-nums ${cls}`}>
      {up ? '▲' : pct < 0 ? '▼' : '•'} {Math.abs(Math.round(pct))}%
    </span>
  );
}
