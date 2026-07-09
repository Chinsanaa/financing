'use client';

import { useEffect, useRef, useState } from 'react';
import { Check, ChevronDown, Palette } from 'lucide-react';
import {
  CATEGORY_COLORS,
  chartColorForKey,
  hashCategoryKey,
} from '@/utils/categoryColors';

/**
 * Per-category color chooser: a small trigger pill that opens a popover
 * swatch grid. Purely presentational — the parent owns persistence and
 * passes which colors other categories have already taken.
 */
export default function CategoryColorPicker({
  categoryName,
  color,
  takenBy,
  saving = false,
  onSelect,
}: {
  categoryName: string;
  /** The saved palette key, or null/undefined = auto (hash fallback). */
  color?: string | null;
  /** Palette key -> name of the OTHER category currently using it. */
  takenBy: ReadonlyMap<string, string>;
  saving?: boolean;
  /** Called with a palette key, or null for "Auto". */
  onSelect: (key: string | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  // Effective key drives the trigger dot even when no color is chosen.
  const effectiveKey = color || hashCategoryKey(categoryName);

  // The popover only mounts after a click, so reading the theme off <html>
  // here is safe (no SSR/hydration concern).
  const isDark =
    typeof document !== 'undefined' && document.documentElement.classList.contains('dark');

  useEffect(() => {
    if (!open) return;
    const onMouseDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onMouseDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const choose = (key: string | null) => {
    setOpen(false);
    onSelect(key);
  };

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        disabled={saving}
        aria-label={`Choose color for ${categoryName}`}
        aria-expanded={open}
        className="inline-flex items-center gap-1.5 rounded-pill border border-edge/20 px-2.5 py-1 text-xs text-muted transition-colors hover:border-accent-strong/50 hover:text-ink disabled:opacity-60"
      >
        <span
          className="h-3.5 w-3.5 shrink-0 rounded-full"
          style={{ backgroundColor: chartColorForKey(effectiveKey) }}
        />
        {color ? 'Color' : 'Auto'}
        <ChevronDown className="h-3 w-3" />
      </button>

      {open && (
        <div className="glass absolute left-0 top-full z-50 mt-2 w-72 max-w-[calc(100vw-2rem)] rounded-xl p-3 shadow-card">
          <p className="section-label mb-2">Category color</p>
          <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
            {CATEGORY_COLORS.map((c) => {
              const selected = color === c.key;
              const usedBy = !selected ? takenBy.get(c.key) : undefined;
              return (
                <button
                  key={c.key}
                  type="button"
                  disabled={!!usedBy}
                  onClick={() => choose(c.key)}
                  title={usedBy ? `Used by ${usedBy}` : `${c.label} — pick this color`}
                  className={`flex flex-col items-start gap-0.5 rounded-lg border p-2 text-left transition-colors ${
                    selected
                      ? 'border-accent-strong/60 ring-1 ring-accent/40'
                      : 'border-edge/10 hover:bg-surface-2'
                  } ${usedBy ? 'cursor-not-allowed opacity-40' : ''}`}
                >
                  <span className="flex w-full items-center gap-1.5">
                    <span
                      className="h-4 w-4 shrink-0 rounded-full"
                      style={{ backgroundColor: chartColorForKey(c.key) }}
                    />
                    <span className="min-w-0 flex-1 truncate text-xs font-medium">{c.label}</span>
                    {selected && <Check className="h-3.5 w-3.5 shrink-0 text-accent-strong" />}
                  </span>
                  <span className="pl-[22px] font-mono text-[10px] text-muted">
                    {usedBy ? 'In use' : isDark ? c.dark : c.light}
                  </span>
                </button>
              );
            })}
          </div>
          {color && (
            <button
              type="button"
              onClick={() => choose(null)}
              className="mt-2 inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-edge/10 px-2 py-1.5 text-xs text-muted transition-colors hover:bg-surface-2 hover:text-ink"
            >
              <Palette className="h-3.5 w-3.5" /> Auto (no fixed color)
            </button>
          )}
        </div>
      )}
    </div>
  );
}
