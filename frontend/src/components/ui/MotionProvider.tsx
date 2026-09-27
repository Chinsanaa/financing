'use client';

import { LazyMotion } from 'framer-motion';

/**
 * App-wide framer-motion setup. Components render the lightweight `m.*`
 * elements; the animation engine (domMax — full set, since the tab
 * indicators use `layoutId`) is fetched as a separate chunk after first
 * paint instead of shipping in every page's initial bundle. Until it
 * arrives, elements render in their final state without animating.
 */
const loadFeatures = () => import('framer-motion').then((mod) => mod.domMax);

export function MotionProvider({ children }: { children: React.ReactNode }) {
  return <LazyMotion features={loadFeatures}>{children}</LazyMotion>;
}
