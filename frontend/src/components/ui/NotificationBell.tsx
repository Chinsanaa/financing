'use client';

import { useEffect, useRef, useState } from 'react';
import { ArrowRight, Bell, Brain, CheckCircle2, ClipboardList, Sparkles, TriangleAlert } from 'lucide-react';
import { useApi } from '@/utils/useApi';
import { formatCurrencyWhole, formatNumber } from '@/utils/format';

interface Action {
  type: string;
  category?: string;
  current?: number;
  limit?: number;
  overage?: number;
  pct?: number;
  count?: number;
  message?: string;
  cv_accuracy?: number;
}

/** Header bell: badge count from GET /dashboard/action (already polled by
 * ActionTab — this re-reads the same cached response via useApi's shared
 * cache), and a dropdown showing that same data directly. "View all" hands
 * off to the fuller Planning -> Action plan view via `onViewAll`. */
export default function NotificationBell({ onViewAll }: { onViewAll: () => void }) {
  const { data } = useApi<{ actions: Action[] }>('/dashboard/action');
  const actions = data?.actions || [];
  const count = actions.filter(
    (a) =>
      a.type === 'over_budget' ||
      a.type === 'approaching_budget' ||
      a.type === 'welcome' ||
      a.type === 'training_complete'
  ).length;

  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

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

  const viewAll = () => {
    setOpen(false);
    onViewAll();
  };

  return (
    <div ref={rootRef} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={count > 0 ? `${count} budget alerts` : 'No budget alerts'}
        aria-expanded={open}
        className="relative flex h-11 w-11 items-center justify-center rounded-pill border border-edge/10 text-muted transition-colors hover:text-ink hover:border-edge/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
      >
        <Bell className="h-4 w-4" />
        {count > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold leading-none text-white">
            {count}
          </span>
        )}
      </button>

      {open && (
        <div className="glass absolute right-0 top-full z-50 mt-2 w-80 max-w-[calc(100vw-2rem)] rounded-xl p-3 shadow-card">
          <p className="section-label mb-2 px-1">Notifications</p>

          {actions.length === 0 ? (
            <div className="flex items-start gap-2.5 rounded-lg p-2.5">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" />
              <p className="text-sm text-muted">Nothing to flag right now.</p>
            </div>
          ) : (
            <ul className="space-y-1.5">
              {actions.map((action, idx) => {
                if (action.type === 'welcome') {
                  return (
                    <li key={idx} className="flex items-start gap-2.5 rounded-lg p-2 hover:bg-surface-2">
                      <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-accent-strong" />
                      <p className="text-sm text-muted">{action.message}</p>
                    </li>
                  );
                }
                if (action.type === 'training_complete') {
                  return (
                    <li key={idx} className="flex items-start gap-2.5 rounded-lg p-2 hover:bg-surface-2">
                      <Brain className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-muted">{action.message}</p>
                        {action.cv_accuracy != null && (
                          <p className="text-xs text-success">
                            {formatNumber(action.cv_accuracy * 100, 0)}% accuracy
                          </p>
                        )}
                      </div>
                    </li>
                  );
                }
                if (action.type === 'over_budget') {
                  return (
                    <li key={idx} className="flex items-start gap-2.5 rounded-lg p-2 hover:bg-surface-2">
                      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">Over budget: {action.category}</p>
                        <p className="text-xs text-danger">
                          {formatCurrencyWhole(action.overage || 0)} over
                        </p>
                      </div>
                    </li>
                  );
                }
                if (action.type === 'approaching_budget') {
                  return (
                    <li key={idx} className="flex items-start gap-2.5 rounded-lg p-2 hover:bg-surface-2">
                      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-[color:var(--chart-5)]" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">Approaching budget: {action.category}</p>
                        <p className="text-xs text-[color:var(--chart-5)]">{action.pct}% used</p>
                      </div>
                    </li>
                  );
                }
                if (action.type === 'pending_review') {
                  return (
                    <li key={idx} className="flex items-start gap-2.5 rounded-lg p-2 hover:bg-surface-2">
                      <ClipboardList className="mt-0.5 h-4 w-4 shrink-0 text-accent-strong" />
                      <p className="text-sm text-muted">{action.message}</p>
                    </li>
                  );
                }
                return null;
              })}
            </ul>
          )}

          <button
            onClick={viewAll}
            className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-lg border border-edge/10 px-2 py-1.5 text-xs text-muted transition-colors hover:bg-surface-2 hover:text-ink"
          >
            View all in Planning <ArrowRight className="h-3 w-3" />
          </button>
        </div>
      )}
    </div>
  );
}
