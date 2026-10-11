'use client';

import { ReactNode } from 'react';
import { m } from 'framer-motion';
import { LucideIcon } from 'lucide-react';

export type TabItem = { id: string; label: string; icon?: LucideIcon; tourId?: string };

// Critically damped (bounce 0): the indicator arrives and stops — no
// overshoot on something the user didn't fling (apple-design §4).
const SPRING = { type: 'spring', bounce: 0, duration: 0.35 } as const;

/**
 * Top-level section nav: plain words, the active one in ink with a
 * vermilion rule that slides between tabs. No icons, no hover pills.
 */
export function TabBar({
  tabs,
  active,
  onChange,
  layoutId = 'tab-indicator',
}: {
  tabs: TabItem[];
  active: string;
  onChange: (id: string) => void;
  layoutId?: string;
}) {
  return (
    <nav className="scrollbar-hide -mb-px flex gap-6 overflow-x-auto" role="tablist">
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            data-tour-id={tab.tourId}
            className={`relative whitespace-nowrap py-3 text-sm transition-colors duration-150 ${
              isActive ? 'text-ink font-medium' : 'text-muted hover:text-ink'
            }`}
          >
            {tab.label}
            {isActive && (
              <m.span
                layoutId={layoutId}
                className="absolute inset-x-0 bottom-0 h-[2px] bg-accent"
                transition={SPRING}
              />
            )}
          </button>
        );
      })}
    </nav>
  );
}

/** Secondary sub-tabs under a section: smaller words, a thin ink rule. */
export function PillTabs({
  tabs,
  active,
  onChange,
  layoutId = 'pill-indicator',
}: {
  tabs: TabItem[];
  active: string;
  onChange: (id: string) => void;
  layoutId?: string;
}) {
  return (
    <div
      className="scrollbar-hide flex max-w-full gap-5 overflow-x-auto border-b border-edge/12"
      role="tablist"
    >
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            data-tour-id={tab.tourId}
            className={`relative -mb-px whitespace-nowrap pb-2.5 pt-1 text-[13px] transition-colors ${
              isActive ? 'text-ink font-medium' : 'text-muted hover:text-ink'
            }`}
          >
            {tab.label}
            {isActive && (
              <m.span
                layoutId={layoutId}
                className="absolute inset-x-0 bottom-0 h-px bg-ink"
                transition={SPRING}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}

/**
 * Wraps each tab's content: a short fade-rise, then `.stagger-in` cascades
 * the tab's top-level sections. No blur (THE RULE) — and no lingering
 * transform/filter, which would trap position:fixed modals inside tabs.
 */
export function TabPanel({ children }: { children: ReactNode }) {
  return (
    <m.div
      className="tab-panel"
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </m.div>
  );
}
