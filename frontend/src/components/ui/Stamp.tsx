'use client';

import { m } from 'framer-motion';

/**
 * The Ledger signature: a seal stamped onto a statement row.
 *
 * - `solid` (default): a confirmed category — vermilion ink, paper text.
 * - `outline`: the model's guess, not yet confirmed (state by line form,
 *   not by hue — the same rule the category badges follow).
 *
 * Motion: the seal comes down from 1.12× with a small tilt and settles with
 * a lightly under-damped spring (bounce 0.25) — the one place in the app
 * that bounces, because a stamp is a physical impact. `tilt` is the angle it
 * comes to rest at (real stamps never land square). Plays on mount; remount
 * (change `key`) to stamp again. Reduced motion (MotionConfig): fades in place.
 */
export default function Stamp({
  label,
  variant = 'solid',
  tilt = -3,
  delay = 0,
  className = '',
}: {
  label: string;
  variant?: 'solid' | 'outline';
  tilt?: number;
  delay?: number;
  className?: string;
}) {
  return (
    <m.span
      className={`inline-flex select-none items-center whitespace-nowrap rounded-[3px] px-2 py-[3px] font-display text-[11px] font-semibold uppercase leading-none tracking-[0.08em] ${
        variant === 'solid'
          ? 'bg-accent text-accent-ink'
          : 'border-[1.5px] border-dashed border-accent text-accent-strong'
      } ${className}`}
      initial={{ opacity: 0, scale: 1.12, rotate: tilt - 5 }}
      animate={{ opacity: 1, scale: 1, rotate: tilt }}
      transition={{
        delay,
        opacity: { duration: 0.08, delay },
        default: { type: 'spring', bounce: 0.25, duration: 0.42, delay },
      }}
    >
      {label}
    </m.span>
  );
}
