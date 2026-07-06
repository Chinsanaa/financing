'use client';

import { ReactNode } from 'react';

/** Shared UI atoms — replaces the alert/loading/progress markup that was
 * copy-pasted across every tab. */

const ALERT_STYLES: Record<string, string> = {
  error: 'bg-red-50 border-red-200 text-red-700',
  success: 'bg-green-50 border-green-200 text-green-700',
  info: 'bg-blue-50 border-blue-200 text-blue-700',
};

export function Alert({
  kind = 'info',
  children,
}: {
  kind?: 'error' | 'success' | 'info';
  children: ReactNode;
}) {
  if (!children) return null;
  return (
    <div className={`border px-4 py-3 rounded ${ALERT_STYLES[kind]}`}>{children}</div>
  );
}

export function Loading({ label = 'Loading...' }: { label?: string }) {
  return <div className="text-gray-600">{label}</div>;
}

export function ProgressBar({
  percent,
  color = 'bg-blue-600',
  height = 'h-2',
}: {
  percent: number;
  color?: string;
  height?: string;
}) {
  return (
    <div className={`w-full bg-gray-200 rounded-full ${height}`}>
      <div
        className={`${color} ${height} rounded-full transition-all`}
        style={{ width: `${Math.min(Math.max(percent, 0), 100)}%` }}
      />
    </div>
  );
}
