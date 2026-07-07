'use client';

import { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { LucideIcon } from 'lucide-react';

export type TabItem = { id: string; label: string; icon?: LucideIcon };

/** Compact top-level tab bar with a sliding active indicator. */
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
    <nav className="flex gap-1 overflow-x-auto" role="tablist">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = tab.id === active;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={`relative flex items-center gap-1.5 px-3.5 py-2.5 text-sm whitespace-nowrap transition-colors ${
              isActive ? 'text-ink font-medium' : 'text-muted hover:text-ink'
            }`}
          >
            {Icon && <Icon className="h-4 w-4" />}
            {tab.label}
            {isActive && (
              <motion.span
                layoutId={layoutId}
                className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-accent"
                transition={{ type: 'spring', stiffness: 500, damping: 40 }}
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
    <div className="inline-flex gap-1 rounded-pill bg-surface-2 p-1" role="tablist">
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={`relative rounded-pill px-3.5 py-1.5 text-sm whitespace-nowrap transition-colors ${
              isActive ? 'text-ink font-medium' : 'text-muted hover:text-ink'
            }`}
          >
            {isActive && (
              <motion.span
                layoutId={layoutId}
                className="absolute inset-0 rounded-pill bg-surface border border-edge/10 shadow-card"
                transition={{ type: 'spring', stiffness: 500, damping: 40 }}
              />
            )}
            <span className="relative">{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}

export function TabPanel({ children }: { children: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  );
}
