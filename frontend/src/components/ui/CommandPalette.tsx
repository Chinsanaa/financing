'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, m } from 'framer-motion';
import { CornerDownLeft, LucideIcon, Search } from 'lucide-react';

export type Command = {
  id: string;
  label: string;
  group: string;
  icon: LucideIcon;
  /** Extra words that should match (e.g. "import csv" for Upload). */
  keywords?: string;
  run: () => void;
};

/**
 * ⌘K / Ctrl+K launcher: jump to any tab or wizard step, flip the theme,
 * sign out. Keyboard-first (↑ ↓ Enter Esc), filterable, focus returns to
 * whatever was focused before it opened.
 */
export default function CommandPalette({
  open,
  onOpenChange,
  commands,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  commands: Command[];
}) {
  const [query, setQuery] = useState('');
  const [index, setIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const restoreRef = useRef<HTMLElement | null>(null);

  // Global shortcut.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onOpenChange]);

  useEffect(() => {
    if (open) {
      restoreRef.current = document.activeElement as HTMLElement | null;
      setQuery('');
      setIndex(0);
      // After the dialog mounts.
      requestAnimationFrame(() => inputRef.current?.focus());
    } else {
      restoreRef.current?.focus?.();
    }
  }, [open]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter((c) =>
      `${c.label} ${c.group} ${c.keywords ?? ''}`.toLowerCase().includes(q)
    );
  }, [commands, query]);

  useEffect(() => setIndex(0), [query]);

  // Keep the highlighted row in view.
  useEffect(() => {
    listRef.current
      ?.querySelector<HTMLElement>(`[data-index="${index}"]`)
      ?.scrollIntoView({ block: 'nearest' });
  }, [index]);

  const runAt = (i: number) => {
    const cmd = filtered[i];
    if (!cmd) return;
    onOpenChange(false);
    cmd.run();
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      runAt(index);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onOpenChange(false);
    } else if (e.key === 'Tab') {
      e.preventDefault(); // focus stays in the input; arrows move the selection
    }
  };

  // Group headings in first-seen order.
  let lastGroup = '';

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[100] flex items-start justify-center px-4 pt-[12vh]">
          <m.div
            className="absolute inset-0 bg-ink/25 dark:bg-black/50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.1 }}
            onClick={() => onOpenChange(false)}
          />
          <m.div
            role="dialog"
            aria-modal="true"
            aria-label="Command menu"
            className="relative w-full max-w-lg overflow-hidden rounded-card border border-edge/15 bg-surface shadow-card"
            // Keyboard-summoned, used many times a day: appear immediately.
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, transition: { duration: 0.08 } }}
            transition={{ duration: 0.1 }}
            onKeyDown={onKeyDown}
          >
            <div className="flex items-center gap-3 border-b border-edge/12 px-4">
              <Search className="h-4 w-4 shrink-0 text-muted" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Jump to a tab or run a command…"
                className="h-14 w-full bg-transparent text-[15px] text-ink placeholder:text-muted outline-none"
                role="combobox"
                aria-expanded="true"
                aria-controls="command-list"
                aria-activedescendant={filtered[index] ? `cmd-${filtered[index].id}` : undefined}
              />
              <span className="kbd">Esc</span>
            </div>

            <div ref={listRef} id="command-list" role="listbox" className="max-h-[50vh] overflow-y-auto p-2">
              {filtered.length === 0 && (
                <p className="px-3 py-10 text-center text-sm text-muted">No matches for “{query}”</p>
              )}
              {filtered.map((cmd, i) => {
                const header = cmd.group !== lastGroup ? cmd.group : null;
                lastGroup = cmd.group;
                const Icon = cmd.icon;
                const active = i === index;
                return (
                  <div key={cmd.id}>
                    {header && <p className="section-label px-3 pb-1.5 pt-3 first:pt-1">{header}</p>}
                    <button
                      id={`cmd-${cmd.id}`}
                      data-index={i}
                      role="option"
                      aria-selected={active}
                      onMouseMove={() => setIndex(i)}
                      onClick={() => runAt(i)}
                      className={`relative flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm transition-colors ${
                        active ? 'text-ink' : 'text-muted'
                      }`}
                    >
                      {/* Arrow keys move this — no glide, it must keep up with the key. */}
                      {active && <span className="absolute inset-0 rounded-md bg-edge/[0.07]" />}
                      <Icon className={`relative h-4 w-4 ${active ? 'text-ink' : ''}`} />
                      <span className="relative flex-1">{cmd.label}</span>
                      {active && <CornerDownLeft className="relative h-3.5 w-3.5 text-muted" />}
                    </button>
                  </div>
                );
              })}
            </div>

            <div className="flex items-center gap-4 border-t border-edge/12 px-4 py-2.5 text-[11px] text-muted">
              <span className="flex items-center gap-1.5"><span className="kbd">↑</span><span className="kbd">↓</span> navigate</span>
              <span className="flex items-center gap-1.5"><span className="kbd">Enter</span> open</span>
              <span className="ml-auto flex items-center gap-1.5"><span className="kbd">⌘</span><span className="kbd">K</span> toggle</span>
            </div>
          </m.div>
        </div>
      )}
    </AnimatePresence>
  );
}
