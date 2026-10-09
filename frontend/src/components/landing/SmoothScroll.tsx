'use client';

import { useEffect } from 'react';
import Lenis from 'lenis';

/**
 * Lenis smooth scrolling — on the marketing page only. The dashboard keeps
 * native scrolling: a work tool should never feel like its scroll is being
 * steered. Off entirely under prefers-reduced-motion; anchor links (#how)
 * glide instead of jumping.
 */
export default function SmoothScroll() {
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    // CSS smooth scrolling fights Lenis; it owns scrolling while mounted.
    const html = document.documentElement;
    const prev = html.style.scrollBehavior;
    html.style.scrollBehavior = 'auto';
    const lenis = new Lenis({ autoRaf: true, lerp: 0.12, anchors: { offset: -72 } });
    return () => {
      lenis.destroy();
      html.style.scrollBehavior = prev;
    };
  }, []);
  return null;
}
