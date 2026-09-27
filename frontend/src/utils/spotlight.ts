import type { PointerEvent } from 'react';

/**
 * Pointer handler for the `.spotlight` effect (globals.css): writes the
 * pointer position into --mx/--my on the hovered element. Direct style
 * writes, no React state, so it never re-renders.
 */
export function trackSpotlight(e: PointerEvent<HTMLElement>) {
  if (e.pointerType !== 'mouse') return; // no hover glow on touch
  const el = e.currentTarget;
  const r = el.getBoundingClientRect();
  el.style.setProperty('--mx', `${e.clientX - r.left}px`);
  el.style.setProperty('--my', `${e.clientY - r.top}px`);
}
