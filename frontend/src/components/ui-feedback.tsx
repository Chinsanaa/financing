'use client';

import { ReactNode } from 'react';
import { AlertCircle, CheckCircle2, Info } from 'lucide-react';
import { SkeletonRows } from '@/components/ui/Skeleton';

/** Shared UI atoms used across the dashboard tabs, themed via design tokens. */

const ALERT_STYLES: Record<string, { classes: string; Icon: typeof Info }> = {
  error: { classes: 'border-danger/25 bg-danger/10 text-danger', Icon: AlertCircle },
  success: { classes: 'border-success/25 bg-success/10 text-success', Icon: CheckCircle2 },
  info: { classes: 'border-cyan/25 bg-cyan/10 text-cyan', Icon: Info },
};

export function Alert({
  kind = 'info',
  children,
}: {
  kind?: 'error' | 'success' | 'info';
  children: ReactNode;
}) {
  if (!children) return null;
  const { classes, Icon } = ALERT_STYLES[kind];
  return (
    <div
      role={kind === 'error' ? 'alert' : 'status'}
      aria-live={kind === 'error' ? 'assertive' : 'polite'}
      className={`flex items-start gap-2.5 rounded-lg border px-4 py-3 text-sm animate-fade-up ${classes}`}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <div>{children}</div>
    </div>
  );
}

/** Legacy loading state — now renders a skeleton block instead of text. */
export function Loading({ label }: { label?: string }) {
  return <SkeletonRows rows={4} />;
}

export function ProgressBar({
  percent,
  color = 'bg-accent',
  fillColor,
  height = 'h-2',
  marker,
  label,
}: {
  percent: number;
  /** Tailwind class for the fill. Ignored when `fillColor` is set. */
  color?: string;
  /** Raw CSS color (e.g. `rgb(var(--chart-cat-sky))`) for the fill — takes
   *  priority over `color` when a caller needs a value outside the fixed
   *  Tailwind palette (e.g. a category's own identity color). */
  fillColor?: string;
  height?: string;
  /** Optional target position (0–100) drawn as a thin tick, e.g. the 50%
   *  "Needs" target on the 50/30/20 bars. */
  marker?: number;
  /** Accessible name for the bar (announced with its value). */
  label?: string;
}) {
  const pct = Math.min(Math.max(Number.isFinite(percent) ? percent : 0, 0), 100);
  return (
    <div
      className={`relative w-full rounded-full bg-edge/10 ${height}`}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(pct)}
      aria-label={label}
    >
      <div className={`h-full overflow-hidden rounded-full`}>
        {/* .progress-fill: grows in from 0, glides on change, one light sweep */}
        <div
          className={`progress-fill ${fillColor ? '' : color} h-full rounded-full`}
          style={{
            width: `${pct}%`,
            ...(fillColor
              ? { backgroundColor: fillColor, boxShadow: `0 0 12px -2px ${fillColor}` }
              : {}),
          }}
        />
      </div>
      {marker !== undefined && (
        <span
          aria-hidden="true"
          className="absolute -top-1 -bottom-1 w-0.5 -translate-x-1/2 rounded-full bg-ink/60"
          style={{ left: `${Math.min(Math.max(marker, 0), 100)}%` }}
        />
      )}
    </div>
  );
}
