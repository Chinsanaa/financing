'use client';

import { useEffect, useState } from 'react';

const PADDING = 6;
const BUBBLE_WIDTH = 260;
const GAP = 14;

/**
 * Visual-only guide overlay: dims the page and punches a "spotlight" hole
 * around the DOM element matching `[data-tour-id="${targetId}"]`, with a
 * small instruction bubble + arrow pointing at it. Deliberately NOT a
 * blocking modal — every layer here has `pointer-events: none` except the
 * bubble's own dismiss link, so the real button underneath stays fully
 * clickable and a user can never get stuck. Renders nothing if the target
 * isn't currently in the DOM (e.g. it's inside a section the user hasn't
 * navigated to yet) — the tour simply resumes once they get there.
 */
export default function TourSpotlight({
  targetId,
  title,
  text,
  onSkip,
}: {
  targetId: string | null;
  title: string;
  text: string;
  onSkip: () => void;
}) {
  const [rect, setRect] = useState<DOMRect | null>(null);

  useEffect(() => {
    if (!targetId) {
      setRect(null);
      return;
    }

    const update = () => {
      const el = document.querySelector(`[data-tour-id="${targetId}"]`);
      setRect(el ? el.getBoundingClientRect() : null);
    };

    update();
    window.addEventListener('resize', update);
    window.addEventListener('scroll', update, true);
    // Short poll: the target may mount asynchronously (e.g. a lazy-loaded
    // tab the user just navigated into) — cheaper than a MutationObserver
    // for a handful of possible targets.
    const interval = setInterval(update, 400);

    return () => {
      window.removeEventListener('resize', update);
      window.removeEventListener('scroll', update, true);
      clearInterval(interval);
    };
  }, [targetId]);

  if (!rect) return null;

  const highlightTop = rect.top - PADDING;
  const highlightLeft = rect.left - PADDING;
  const highlightWidth = rect.width + PADDING * 2;
  const highlightHeight = rect.height + PADDING * 2;

  const spaceBelow = window.innerHeight - (highlightTop + highlightHeight);
  const placeAbove = spaceBelow < 140;
  const bubbleTop = placeAbove ? highlightTop - GAP : highlightTop + highlightHeight + GAP;

  const targetCenterX = rect.left + rect.width / 2;
  const bubbleLeft = Math.min(
    Math.max(targetCenterX - BUBBLE_WIDTH / 2, 16),
    window.innerWidth - BUBBLE_WIDTH - 16
  );
  const caretLeft = Math.min(Math.max(targetCenterX - bubbleLeft - 6, 12), BUBBLE_WIDTH - 24);

  return (
    <div className="pointer-events-none fixed inset-0 z-[60]">
      <div
        className="absolute rounded-xl transition-all duration-200 ease-out"
        style={{
          top: highlightTop,
          left: highlightLeft,
          width: highlightWidth,
          height: highlightHeight,
          boxShadow: '0 0 0 9999px rgba(0,0,0,0.65)',
        }}
      />
      <div
        className="glass pointer-events-auto absolute rounded-xl p-3 shadow-card transition-all duration-200 ease-out"
        style={{ top: bubbleTop, left: bubbleLeft, width: BUBBLE_WIDTH, transform: placeAbove ? 'translateY(-100%)' : undefined }}
      >
        <div
          className="glass absolute h-3 w-3 rotate-45"
          style={
            placeAbove
              ? { bottom: -6, left: caretLeft }
              : { top: -6, left: caretLeft }
          }
        />
        <p className="text-sm font-semibold">{title}</p>
        <p className="mt-0.5 text-xs leading-relaxed text-muted">{text}</p>
        <button
          onClick={onSkip}
          className="mt-2 text-xs text-muted underline decoration-edge/40 underline-offset-2 hover:text-ink"
        >
          Skip tour
        </button>
      </div>
    </div>
  );
}
