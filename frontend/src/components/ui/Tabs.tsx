'use client';

import { ReactNode, useState } from 'react';
import { AnimatePresence, m } from 'framer-motion';
import { LucideIcon } from 'lucide-react';

export type TabItem = { id: string; label: string; icon?: LucideIcon; tourId?: string };

const SPRING = { type: 'spring', stiffness: 500, damping: 40 } as const;

/**
 * Top-level tab bar. Two shared-layout layers: a soft pill that glides to
 * whichever tab is hovered (the "spotlight nav" pattern), and a glowing
 * lime underline that springs to the active tab.
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
  const [hovered, setHovered] = useState<string | null>(null);
  return (
    <nav
      className="scrollbar-hide flex gap-1 overflow-x-auto py-1"
      role="tablist"
      onMouseLeave={() => setHovered(null)}
    >
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = tab.id === active;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            onMouseEnter={() => setHovered(tab.id)}
            onFocus={() => setHovered(tab.id)}
            data-tour-id={tab.tourId}
            className={`relative flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-sm whitespace-nowrap transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 ${
              isActive ? 'text-ink font-medium' : 'text-muted hover:text-ink'
            }`}
          >
            <AnimatePresence>
              {hovered === tab.id && (
                <m.span
                  layoutId={`${layoutId}-hover`}
                  className="absolute inset-0 rounded-lg bg-edge/[0.06]"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={SPRING}
                />
              )}
            </AnimatePresence>
            {Icon && (
              <Icon
                className={`relative h-4 w-4 transition-colors ${isActive ? 'text-accent-strong' : ''}`}
              />
            )}
            <span className="relative">{tab.label}</span>
            {isActive && (
              <m.span
                layoutId={layoutId}
                className="absolute inset-x-3 -bottom-[5px] h-0.5 rounded-full bg-accent shadow-[0_0_12px_1px_rgb(var(--accent)/0.6)]"
                transition={SPRING}
              />
            )}
          </button>
        );
      })}
    </nav>
  );
}

/** Small pill sub-tabs shown under a section. */
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
      className="scrollbar-hide inline-flex max-w-full gap-1 overflow-x-auto rounded-pill border border-edge/8 bg-surface-2/70 p-1 backdrop-blur"
      role="tablist"
    >
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        const Icon = tab.icon;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            data-tour-id={tab.tourId}
            className={`relative flex items-center gap-1.5 rounded-pill px-3.5 py-1.5 text-sm whitespace-nowrap transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 ${
              isActive ? 'text-ink font-medium' : 'text-muted hover:text-ink'
            }`}
          >
            {isActive && (
              <m.span
                layoutId={layoutId}
                className="absolute inset-0 rounded-pill border border-edge/10 bg-surface shadow-card"
                transition={SPRING}
              />
            )}
            {Icon && (
              <Icon className={`relative h-3.5 w-3.5 ${isActive ? 'text-accent-strong' : ''}`} />
            )}
            <span className="relative">{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}

/**
 * Wraps each tab's content: the panel blurs/rises in, then `.stagger-in`
 * cascades the tab's top-level sections (tab root's children) 55ms apart.
 */
export function TabPanel({ children }: { children: ReactNode }) {
  return (
    <m.div
      className="tab-panel"
      initial={{ opacity: 0, y: 10, filter: 'blur(6px)' }}
      // filter must end as `none`: any other value turns this wrapper into
      // the containing block for position:fixed modals inside tabs.
      animate={{ opacity: 1, y: 0, filter: 'blur(0px)', transitionEnd: { filter: 'none' } }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </m.div>
  );
}
