'use client';

import { HTMLAttributes, ReactNode } from 'react';
import { LucideIcon } from 'lucide-react';

/**
 * Base surface — always a solid color (design rule: no gradients/glows).
 * Variants (combine freely):
 * - `glass`  solid surface + border (name kept for existing call sites)
 * - `hover`  lifts slightly on hover
 */
export default function Card({
  glass = false,
  hover = false,
  children,
  className = '',
  ...rest
}: HTMLAttributes<HTMLDivElement> & {
  glass?: boolean;
  hover?: boolean;
  children: ReactNode;
}) {
  return (
    <div
      className={`rounded-card ${
        glass
          ? 'glass'
          : 'bg-surface border border-edge/8 shadow-[inset_0_1px_0_0_rgb(var(--edge)/0.04)]'
      } ${
        hover
          ? 'transition-[transform,box-shadow,border-color] duration-200 ease-out hover:-translate-y-0.5 hover:shadow-card'
          : ''
      } ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}

/**
 * Page/section heading: eyebrow label with a live accent dot, display
 * title, optional one-line description and right-aligned action.
 */
export function SectionHeader({
  label,
  title,
  description,
  icon: Icon,
  action,
}: {
  label?: string;
  title: string;
  description?: ReactNode;
  icon?: LucideIcon;
  action?: ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        {label && (
          <p className="section-label mb-2 flex items-center gap-2">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inset-0 rounded-full bg-accent animate-ping-soft" />
              <span className="relative h-1.5 w-1.5 rounded-full bg-accent" />
            </span>
            {label}
          </p>
        )}
        <h2 className="flex items-center gap-2.5 font-display text-2xl font-semibold tracking-tight sm:text-[1.75rem]">
          {Icon && (
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent/12 text-accent-strong">
              <Icon className="h-[18px] w-[18px]" />
            </span>
          )}
          {title}
        </h2>
        {description && <p className="mt-1.5 max-w-2xl text-sm text-muted">{description}</p>}
      </div>
      {action}
    </div>
  );
}
