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
  height = 'h-2',
}: {
  percent: number;
  color?: string;
  height?: string;
}) {
  return (
    <div className={`w-full overflow-hidden rounded-full bg-edge/10 ${height}`}>
      <div
        className={`${color} ${height} rounded-full transition-all duration-500`}
        style={{ width: `${Math.min(Math.max(percent, 0), 100)}%` }}
      />
    </div>
  );
}
