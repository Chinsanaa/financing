'use client';

import { ReactNode } from 'react';
import { m, useReducedMotion } from 'framer-motion';

/**
 * Circular gauge. The arc sweeps from 0 to `percent` on mount with a
 * spring and glides on change. Anything passed as children sits in the
 * middle (e.g. a RollingNumber).
 */
export default function ProgressRing({
  percent,
  size = 168,
  stroke = 12,
  color = 'rgb(var(--accent))',
  label,
  children,
}: {
  percent: number;
  size?: number;
  stroke?: number;
  color?: string;
  /** Accessible name, announced with the value. */
  label: string;
  children?: ReactNode;
}) {
  const reduce = useReducedMotion();
  const pct = Math.min(Math.max(Number.isFinite(percent) ? percent : 0, 0), 100);
  const r = (size - stroke) / 2;
  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(pct)}
    >
      <svg width={size} height={size} className="-rotate-90" aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgb(var(--edge) / 0.08)" strokeWidth={stroke} />
        <m.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          initial={{ pathLength: reduce ? pct / 100 : 0 }}
          animate={{ pathLength: pct / 100 }}
          transition={{ type: 'spring', stiffness: 60, damping: 18, delay: 0.15 }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">{children}</div>
    </div>
  );
}
