'use client';

import { useState } from 'react';
import { SectionHeader } from '@/components/ui/Card';
import { SkeletonCard, SkeletonRows } from '@/components/ui/Skeleton';
import { formatMonthLong } from '@/utils/format';
import RuleBreakdown, { useRuleData } from './RuleBreakdown';

export default function RuleTab() {
  const [month, setMonth] = useState('');
  const { data, loading, error } = useRuleData(month);

  const monthOptions = (() => {
    const opts = data?.available_months ? [...data.available_months] : [];
    if (data?.month && !opts.includes(data.month)) opts.unshift(data.month);
    return opts;
  })();
  const selectedMonth = month || data?.month || '';

  if (loading) {
    return (
      <div className="space-y-6">
        <SkeletonCard />
        <SkeletonRows rows={5} />
      </div>
    );
  }

  const header = (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
      <p className="section-label">{selectedMonth ? formatMonthLong(selectedMonth) : 'This month'}</p>
      {monthOptions.length > 1 && (
        <select
          value={selectedMonth}
          onChange={(e) => setMonth(e.target.value)}
          className="rounded-pill border border-edge/20 bg-surface px-3 py-1.5 text-sm text-ink focus:border-accent-strong/50 focus:outline-none focus:ring-2 focus:ring-accent/20"
        >
          {monthOptions.map((m) => (
            <option key={m} value={m}>
              {formatMonthLong(m)}
            </option>
          ))}
        </select>
      )}
    </div>
  );

  return (
    <div className="space-y-6">
      <SectionHeader label="Planning" title="50/30/20 rule" />
      <RuleBreakdown data={data} loading={false} error={error} header={header} />
    </div>
  );
}
