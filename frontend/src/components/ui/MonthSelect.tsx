'use client';

import { ChevronDown } from 'lucide-react';
import { formatMonthLong } from '@/utils/format';

/** Month picker ("YYYY-MM" values), shared by Budget + 50/30/20. */
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
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 cursor-pointer appearance-none rounded-md border border-edge/20 bg-surface pl-3 pr-9 text-sm font-medium text-ink transition-colors hover:border-edge/40 focus:border-accent focus:outline-none"
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
