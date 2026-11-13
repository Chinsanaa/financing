'use client';

import type { ReactNode } from 'react';
import { m } from 'framer-motion';

const EASE_OUT = [0.22, 1, 0.36, 1] as const;

/**
 * The landing's one authored entrance: content settles upward after `delay`.
 * (Reduced motion is handled globally by MotionConfig — never branch here.)
 */
export default function Rise({
  as = 'div',
  delay,
  id,
  className,
  children,
}: {
  as?: 'div' | 'h1';
  delay: number;
  id?: string;
  className?: string;
  children: ReactNode;
}) {
  const Tag = as === 'h1' ? m.h1 : m.div;
  return (
    <Tag
      id={id}
      className={className}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: EASE_OUT, delay }}
    >
      {children}
    </Tag>
  );
}
