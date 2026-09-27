'use client';

import { CalendarDays, ChevronDown } from 'lucide-react';
import { formatMonthLong } from '@/utils/format';

/** Pill-shaped month picker ("YYYY-MM" values), shared by Budget + 50/30/20. */
export default function MonthSelect({
  value,
  months,
  onChange,
}: {
  value: string;
  months: string[];
  onChange: (month: string) => void;
}) {
  return (
    <label className="relative inline-flex items-center">
      <span className="sr-only">Month</span>
      <CalendarDays className="pointer-events-none absolute left-3 h-4 w-4 text-muted" />
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 cursor-pointer appearance-none rounded-pill border border-edge/15 bg-surface pl-9 pr-9 text-sm font-medium text-ink transition-colors hover:border-edge/30 focus:border-accent/60 focus:outline-none focus:ring-2 focus:ring-accent/20"
      >
        {months.map((m) => (
          <option key={m} value={m}>
            {formatMonthLong(m)}
          </option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3 h-4 w-4 text-muted" />
    </label>
  );
}
