'use client';

import { m } from 'framer-motion';

/**
 * Two-to-four way choice: a hairline frame with an ink block that slides to
 * the chosen option (critically damped — it arrives and stops).
 */
export default function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
  layoutId,
  size = 'md',
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  /** Accessible name for the group. */
  label: string;
  /** Unique per mounted instance (shared-layout animation key). */
  layoutId: string;
  size?: 'sm' | 'md';
}) {
  return (
    <div className="inline-flex rounded-md border border-edge/15 p-0.5" role="radiogroup" aria-label={label}>
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => onChange(o.value)}
            className={`relative rounded-[4px] transition-colors ${size === 'sm' ? 'px-2.5 py-1 text-[13px]' : 'px-3 py-1.5 text-sm'} ${
              on ? 'text-bg' : 'text-muted hover:text-ink'
            }`}
          >
            {on && (
              <m.span
                layoutId={layoutId}
                className="absolute inset-0 rounded-[4px] bg-ink"
                transition={{ type: 'spring', bounce: 0, duration: 0.25 }}
              />
            )}
            <span className="relative whitespace-nowrap">{o.label}</span>
          </button>
        );
      })}
    </div>
  );
}
