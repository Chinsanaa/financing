'use client';

import { ReactNode } from 'react';

/**
 * Hover label for icon-only buttons — CSS-only (`group-hover`), no JS
 * state, no portal. Wrap a single focusable child (usually an icon
 * button that already carries its own `aria-label`); this only adds the
 * visible-on-hover/focus label, it doesn't replace the accessible name.
 */
export default function Tooltip({
  label,
  children,
  side = 'bottom',
  disabled = false,
}: {
  label: string;
  children: ReactNode;
  side?: 'top' | 'bottom';
  disabled?: boolean;
}) {
  return (
    <span className="group/tooltip relative inline-flex">
      {children}
      {!disabled && (
        <span
          role="tooltip"
          className={`pointer-events-none absolute left-1/2 z-50 -translate-x-1/2 whitespace-nowrap rounded-md bg-ink px-2 py-1 text-xs font-medium text-surface opacity-0 shadow-card transition-opacity delay-300 duration-150 group-hover/tooltip:opacity-100 group-focus-within/tooltip:opacity-100 ${
            side === 'bottom' ? 'top-full mt-2' : 'bottom-full mb-2'
          }`}
        >
          {label}
        </span>
      )}
    </span>
  );
}
