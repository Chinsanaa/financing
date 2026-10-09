'use client';

import { HTMLAttributes, ReactNode } from 'react';
import { LucideIcon } from 'lucide-react';

/**
 * Ledger surfaces. Cards are the exception, not the page structure: most
 * sections are separated by hairline rules and whitespace (`variant="plain"`).
 * - `sheet` (default): one flat surface color + a hairline border.
 * - `plain`: no box at all — layout wrapper with a top hairline rule.
 * - `raised` (or legacy `glass`): sheet + soft neutral shadow, for things
 *   that genuinely float (popovers, the label card).
 * `hover` only darkens the border — never a transform lift (transforms trap
 * popovers under later siblings; see DESIGN_SYSTEM.md stacking gotchas).
 */
export default function Card({
  variant = 'sheet',
  glass = false,
  hover = false,
  children,
  className = '',
  ...rest
}: HTMLAttributes<HTMLDivElement> & {
  variant?: 'sheet' | 'plain' | 'raised';
  glass?: boolean;
  hover?: boolean;
  children: ReactNode;
}) {
  const v = glass ? 'raised' : variant;
  const base =
    v === 'plain'
      ? 'border-t border-edge/12'
      : `rounded-card bg-surface border border-edge/10 ${v === 'raised' ? 'shadow-card' : ''}`;
  return (
    <div
      className={`${base} ${hover && v !== 'plain' ? 'transition-colors duration-150 hover:border-edge/25' : ''} ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}

/**
 * Section heading: a serif title that carries its own weight, an optional
 * one-line description and a right-aligned action. No eyebrow, no dot, no
 * icon chip (impeccable craft floor). `label` and `icon` are accepted for
 * old call sites and intentionally not rendered.
 */
export function SectionHeader({
  title,
  description,
  action,
}: {
  label?: string;
  title: string;
  description?: ReactNode;
  icon?: LucideIcon;
  action?: ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
      <div className="min-w-0">
        <h2 className="font-display text-[1.75rem] font-medium leading-tight tracking-[-0.01em]">{title}</h2>
        {description && <p className="mt-1.5 max-w-[60ch] text-sm text-muted">{description}</p>}
      </div>
      {action}
    </div>
  );
}
