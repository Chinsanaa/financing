'use client';

import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, m } from 'framer-motion';
import { Bell, Brain, CheckCircle2, Info, Trash2, TriangleAlert } from 'lucide-react';
import { api } from '@/utils/api';
import { useApi, invalidate } from '@/utils/useApi';
import { formatCurrencyWhole, formatNumber } from '@/utils/format';

interface NotificationPayload {
  category?: string;
  current?: number;
  limit?: number;
  overage?: number;
  pct?: number;
  message?: string;
  cv_accuracy?: number;
}

interface Notification {
  id: string;
  type: string;
  payload: NotificationPayload;
  read_at: string | null;
  created_at: string;
}

function NotificationRow({ n }: { n: Notification }) {
  const unread = !n.read_at;
  const dot = unread && <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent-strong" />;

  if (n.type === 'welcome') {
    return (
      <li className="flex items-start gap-2.5 rounded-md p-2 hover:bg-edge/[0.05]">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted" />
        <p className="min-w-0 flex-1 text-sm text-muted">{n.payload.message}</p>
        {dot}
      </li>
    );
  }
  if (n.type === 'training_complete') {
    return (
      <li className="flex items-start gap-2.5 rounded-md p-2 hover:bg-edge/[0.05]">
        <Brain className="mt-0.5 h-4 w-4 shrink-0 text-success" />
        <div className="min-w-0 flex-1">
          <p className="text-sm text-muted">Your model finished training.</p>
          {n.payload.cv_accuracy != null && (
            <p className="text-xs text-success">{formatNumber(n.payload.cv_accuracy * 100, 0)}% accuracy</p>
          )}
        </div>
        {dot}
      </li>
    );
  }
  if (n.type === 'over_budget') {
    return (
      <li className="flex items-start gap-2.5 rounded-md p-2 hover:bg-edge/[0.05]">
        <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">Over budget: {n.payload.category}</p>
          <p className="text-xs text-danger">{formatCurrencyWhole(n.payload.overage || 0)} over</p>
        </div>
        {dot}
      </li>
    );
  }
  if (n.type === 'approaching_budget') {
    return (
      <li className="flex items-start gap-2.5 rounded-md p-2 hover:bg-edge/[0.05]">
        <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-warn" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">Approaching budget: {n.payload.category}</p>
          <p className="text-xs text-warn">{n.payload.pct}% used</p>
        </div>
        {dot}
      </li>
    );
  }
  return null;
}

/** Header bell: real notification history (welcome / training-complete /
 * budget crossings) from GET /dashboard/notifications, with read/unread
 * tracking and a clear-all action. Distinct from Planning -> Action plan
 * (GET /dashboard/action), which stays a live current-state view — this
 * dropdown is purely a notification inbox, no navigation shortcuts. */
export default function NotificationBell({
  onOpenChange,
}: {
  /** Reports open/close so a wrapping Tooltip can hide itself while the
   * dropdown is showing — a hover label would be redundant clutter then. */
  onOpenChange?: (open: boolean) => void;
}) {
  const { data } = useApi<{ notifications: Notification[]; unread_count: number }>(
    '/dashboard/notifications'
  );
  const notifications = data?.notifications || [];
  const unreadCount = data?.unread_count || 0;

  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    onOpenChange?.(open);
  }, [open, onOpenChange]);

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

  const toggleOpen = async () => {
    const next = !open;
    setOpen(next);
    if (next && unreadCount > 0) {
      try {
        await api.post('/dashboard/notifications/read');
        invalidate('/dashboard/notifications');
      } catch {
        // Best-effort — badge will just re-clear next time the dropdown opens.
      }
    }
  };

  const clearAll = async () => {
    try {
      await api.post('/dashboard/notifications/clear');
      invalidate('/dashboard/notifications');
    } catch {
      // No-op on failure — list simply stays as-is until the next successful clear.
    }
  };

  return (
    <div ref={rootRef} className="relative">
      <button
        onClick={toggleOpen}
        aria-label={unreadCount > 0 ? `${unreadCount} unread notifications` : 'No unread notifications'}
        aria-expanded={open}
        className="relative flex h-10 w-10 items-center justify-center rounded-md text-muted transition-colors hover:bg-edge/6 hover:text-ink active:scale-[0.96]"
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[10px] font-semibold leading-none text-accent-ink">
            {unreadCount}
          </span>
        )}
      </button>

      <AnimatePresence>
      {open && (
        // Grows out of the bell (origin top-right) and settles without
        // overshoot; exits faster than it enters.
        <m.div
          initial={{ opacity: 0, scale: 0.97, y: -4 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.98, transition: { duration: 0.12 } }}
          transition={{ type: 'spring', bounce: 0, duration: 0.24 }}
          style={{ transformOrigin: 'top right' }}
          className="glass absolute right-0 top-full z-50 mt-2 w-80 max-w-[calc(100vw-2rem)] rounded-card p-3 shadow-card"
        >
          <p className="mb-2 px-1 font-display text-lg">Notifications</p>

          {notifications.length === 0 ? (
            <div className="flex items-start gap-2.5 rounded-md p-2.5">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" />
              <p className="text-sm text-muted">Nothing to flag right now.</p>
            </div>
          ) : (
            <>
              <ul className="space-y-1.5">
                {notifications.map((n) => (
                  <NotificationRow key={n.id} n={n} />
                ))}
              </ul>
              <button
                onClick={clearAll}
                className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-md border border-edge/15 px-2 py-1.5 text-xs text-muted transition-colors hover:bg-edge/[0.05] hover:text-ink"
              >
                <Trash2 className="h-3 w-3" /> Clear notifications
              </button>
            </>
          )}
        </m.div>
      )}
      </AnimatePresence>
    </div>
  );
}
