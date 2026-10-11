'use client';

import { LazyMotion, MotionConfig } from 'framer-motion';

/**
 * App-wide framer-motion setup. Components render the lightweight `m.*`
 * elements; the animation engine (domMax — full set, since the tab
 * indicators use `layoutId`) is fetched as a separate chunk after first
 * paint instead of shipping in every page's initial bundle. Until it
 * arrives, elements render in their final state without animating.
 *
 * `reducedMotion="user"`: under prefers-reduced-motion framer skips every
 * transform/layout animation itself (opacity still fades). Components must
 * NOT branch on useReducedMotion() while rendering server-rendered markup —
 * the server can't know the preference, so the markup would differ and
 * React throws hydration errors (#418).
 */
const loadFeatures = () => import('framer-motion').then((mod) => mod.domMax);

export function MotionProvider({ children }: { children: React.ReactNode }) {
  return (
    <MotionConfig reducedMotion="user">
      <LazyMotion features={loadFeatures}>{children}</LazyMotion>
    </MotionConfig>
  );
}
