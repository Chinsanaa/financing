'use client';

import { useEffect, useRef, useState } from 'react';
import NumberFlow from '@number-flow/react';
import { useInView } from 'framer-motion';
import { CURRENCY_SYMBOL } from '@/utils/format';

/**
 * Odometer-style number: digits roll into place the first time the value
 * scrolls into view, and roll again whenever it changes (e.g. switching
 * month). Built on @number-flow/react, which also exposes the final value
 * to screen readers and honors prefers-reduced-motion by itself.
 *
 * `currency` renders whole yuan with the sign before the symbol
 * (-¥1,234), matching utils/format.ts conventions.
 */
export default function RollingNumber({
  value,
  currency = false,
  decimals = 0,
  prefix = '',
  suffix = '',
  className = '',
}: {
  value: number;
  currency?: boolean;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: '-40px' });
  const [shown, setShown] = useState(0);
  const safe = Number.isFinite(value) ? value : 0;

  useEffect(() => {
    if (inView) setShown(safe);
  }, [inView, safe]);

  const sign = currency && safe < 0 ? '-' : '';
  return (
    <span ref={ref} className={`inline-flex tabular-nums ${className}`}>
      <NumberFlow
        value={currency ? Math.abs(shown) : shown}
        locales="en-US"
        format={{ minimumFractionDigits: decimals, maximumFractionDigits: decimals }}
        prefix={`${sign}${prefix}${currency ? CURRENCY_SYMBOL : ''}`}
        suffix={suffix}
        transformTiming={{ duration: 900, easing: 'cubic-bezier(0.22, 1, 0.36, 1)' }}
        spinTiming={{ duration: 900, easing: 'cubic-bezier(0.22, 1, 0.36, 1)' }}
      />
    </span>
  );
}
