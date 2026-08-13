'use client';

import { Bell } from 'lucide-react';
import { useApi } from '@/utils/useApi';

interface Action {
  type: string;
}

/** Badge count of over-budget / approaching-budget items from
 * GET /dashboard/action (already polled by ActionTab — this just re-reads
 * the same cached response via useApi's shared cache). Clicking navigates
 * to the Action-plan sub-tab. */
export default function NotificationBell({ onClick }: { onClick: () => void }) {
  const { data } = useApi<{ actions: Action[] }>('/dashboard/action');
  const count = (data?.actions || []).filter(
    (a) => a.type === 'over_budget' || a.type === 'approaching_budget'
  ).length;

  return (
    <button
      onClick={onClick}
      aria-label={count > 0 ? `${count} budget alerts` : 'No budget alerts'}
      className="relative flex h-11 w-11 items-center justify-center rounded-pill border border-edge/10 text-muted transition-colors hover:text-ink hover:border-edge/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
    >
      <Bell className="h-4 w-4" />
      {count > 0 && (
        <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold leading-none text-white">
          {count}
        </span>
      )}
    </button>
  );
}
