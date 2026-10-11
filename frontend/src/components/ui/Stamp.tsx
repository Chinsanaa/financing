'use client';

import { m } from 'framer-motion';
import { useEffect, useLayoutEffect, useRef, useState } from 'react';

// useLayoutEffect warns during SSR; on the server nothing runs anyway.
const useIsomorphicLayoutEffect = typeof window === 'undefined' ? useEffect : useLayoutEffect;

const SIZE = {
  sm: 'px-1.5 py-[2px] text-[10px] tracking-[0.07em]',
  md: 'px-2 py-[3px] text-[11px] tracking-[0.08em]',
} as const;

/**
 * The Ledger signature: a seal stamped onto a statement row.
 *
 * - `solid` (default): a confirmed category — vermilion ink, paper text.
 * - `outline`: the model's guess, not yet confirmed (state by line form,
 *   not by hue — the same rule the category badges follow).
 * - `size`: `md` (default) or `sm` for dense rows.
 * - `once`: a session key. The stamp animates only the first time per
 *   browser session for that key (sessionStorage); afterwards, and whenever
 *   storage is unavailable after a first play, it renders statically.
 *
 * Motion: the seal comes down from 1.12× with a small tilt and settles with
 * a lightly under-damped spring (bounce 0.25) — the one place in the app
 * that bounces, because a stamp is a physical impact. `tilt` is the angle it
 * comes to rest at (real stamps never land square). Plays on mount; remount
 * (change `key`) to stamp again.
 *
 * Reduced motion / "already seen": decided in a layout effect (before paint,
 * after hydration) — never during render, so server and client markup match
 * (no hydration error #418, see MotionProvider). The first client render is
 * the animated element; the effect swaps it for the static seal before the
 * browser paints. Approved stamp sites: docs/DESIGN_SYSTEM.md §5.
 */
export default function Stamp({
  label,
  variant = 'solid',
  size = 'md',
  tilt = -3,
  delay = 0,
  once,
  className = '',
}: {
  label: string;
  variant?: 'solid' | 'outline';
  size?: 'sm' | 'md';
  tilt?: number;
  delay?: number;
  once?: string;
  className?: string;
}) {
  const [still, setStill] = useState(false);
  const decided = useRef(false);

  useIsomorphicLayoutEffect(() => {
    // Decide once per mount (StrictMode re-runs effects; refs survive).
    if (decided.current) return;
    decided.current = true;
    let reduce = false;
    try {
      reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch {
      /* no matchMedia: animate */
    }
    let seen = false;
    if (once) {
      const key = `stamp:${once}`;
      try {
        seen = window.sessionStorage.getItem(key) === '1';
        if (!seen) window.sessionStorage.setItem(key, '1');
      } catch {
        /* storage blocked: animate this time */
      }
    }
    if (reduce || seen) setStill(true);
  }, [once]);

  const classes = `inline-flex select-none items-center whitespace-nowrap rounded-[3px] font-display font-semibold uppercase leading-none ${
    SIZE[size]
  } ${
    variant === 'solid'
      ? 'bg-accent text-accent-ink'
      : 'border-[1.5px] border-dashed border-accent text-accent-strong'
  } ${className}`;

  if (still) {
    return (
      <span className={classes} style={{ transform: `rotate(${tilt}deg)` }}>
        {label}
      </span>
    );
  }

  return (
    <m.span
      className={classes}
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
