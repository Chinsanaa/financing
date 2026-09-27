'use client';

import { useEffect, useState } from 'react';

const PADDING = 6;

/**
 * Visual-only highlight: dims the page and leaves a hole around the element
 * matching `[data-tour-id="${targetId}"]`. Not a blocking modal — the whole
 * layer is `pointer-events: none`, so the real UI underneath stays clickable
 * and nobody can get stuck. The instruction text lives in the tour's step
 * box (OnboardingTour), so nothing disappears if the target is missing.
 *
 * The target is scrolled into view once when it first appears (tabs are
 * lazy-loaded, so it may mount a moment after navigation — hence the short
 * poll, which only re-renders when the rect actually changes).
 */
export default function TourSpotlight({ targetId }: { targetId: string }) {
  const [rect, setRect] = useState<DOMRect | null>(null);

  useEffect(() => {
    let scrolled = false;

    const update = () => {
      const el = document.querySelector(`[data-tour-id="${targetId}"]`);
      if (el && !scrolled) {
        scrolled = true;
        el.scrollIntoView({ block: 'center', behavior: 'smooth' });
      }
      const next = el ? el.getBoundingClientRect() : null;
      setRect((prev) =>
        prev && next &&
        prev.top === next.top && prev.left === next.left &&
        prev.width === next.width && prev.height === next.height
          ? prev
          : next
      );
    };

    update();
    window.addEventListener('resize', update);
    window.addEventListener('scroll', update, true);
    const interval = setInterval(update, 300);
    return () => {
      window.removeEventListener('resize', update);
      window.removeEventListener('scroll', update, true);
      clearInterval(interval);
    };
  }, [targetId]);

  if (!rect) return null;

  return (
    <div className="pointer-events-none fixed inset-0 z-[60]" aria-hidden="true">
      <div
        className="absolute rounded-xl border-2 border-accent transition-all duration-200 ease-out"
        style={{
          top: rect.top - PADDING,
          left: rect.left - PADDING,
          width: rect.width + PADDING * 2,
          height: rect.height + PADDING * 2,
          boxShadow: '0 0 0 9999px rgba(0,0,0,0.55)',
        }}
      />
    </div>
  );
}
