'use client';

import { LineChart, TriangleAlert } from 'lucide-react';
import { useApi } from '@/utils/useApi';
import { Alert } from '@/components/ui-feedback';
import { SectionHeader } from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import { useCategoryColors } from '@/utils/useCategoryColors';
import EmptyState from '@/components/ui/EmptyState';
import { SkeletonRows } from '@/components/ui/Skeleton';
import { formatCurrencyWhole, formatDate } from '@/utils/format';

interface CategoryTrend {
  category: string;
  current: number;
  avg_3mo: number;
  pct_change: number;
}

interface FlaggedTransaction {
  id: string;
  merchant: string;
  category: string;
  amount: number;
  timestamp: string;
}

interface InsightsData {
  category_trends: CategoryTrend[];
  flagged_transactions: FlaggedTransaction[];
}

export default function InsightsTab() {
  const { data, loading, error } = useApi<InsightsData>('/dashboard/insights');
  const trends = data?.category_trends || [];
  const flagged = data?.flagged_transactions || [];
  const { toneFor } = useCategoryColors();

  if (loading) {
    return (
      <div className="space-y-6">
        <SkeletonRows rows={4} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Insights"
        description="What changed this month compared with your usual, and anything that stands out."
      />

      {error && <Alert kind="error">{error}</Alert>}

      <section className="border-t border-ink/80 pt-4">
        <h3 className="mb-4 font-display text-2xl">This month vs your 3-month average</h3>
        {trends.length === 0 ? (
          <EmptyState
            icon={LineChart}
            title="Not enough history yet"
            description="Once you have a few months of categorized transactions, categories trending up or down show up here."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-edge/15 text-left text-[12px] text-muted">
                <tr>
                  <th className="py-2 pr-4 font-normal">Category</th>
                  <th className="hidden py-2 pr-4 font-normal sm:table-cell">
                    <span className="mr-3 inline-flex items-center gap-1.5"><span className="h-2 w-3 bg-ink" aria-hidden="true" />this month</span>
                    <span className="inline-flex items-center gap-1.5"><span className="h-2 w-3 bg-ink/25" aria-hidden="true" />3-month avg</span>
                  </th>
                  <th className="py-2 pr-4 text-right font-normal">This month</th>
                  <th className="py-2 pr-4 text-right font-normal">Average</th>
                  <th className="py-2 text-right font-normal">Change</th>
                </tr>
              </thead>
              <tbody>
                {trends.map((trend) => {
                  const up = trend.pct_change > 0;
                  const max = Math.max(...trends.map((t) => Math.max(t.current, t.avg_3mo)), 1);
                  return (
                    <tr key={trend.category} className="border-b border-edge/10">
                      <td className="py-3 pr-4">
                        <Badge tone={toneFor(trend.category)}>{trend.category}</Badge>
                      </td>
                      <td className="hidden w-[40%] py-3 pr-4 sm:table-cell">
                        <div className="space-y-1">
                          <div className="progress-fill h-2 bg-ink" style={{ width: `${(trend.current / max) * 100}%` }} />
                          <div className="progress-fill h-2 bg-ink/25" style={{ width: `${(trend.avg_3mo / max) * 100}%` }} />
                        </div>
                      </td>
                      <td className="num py-3 pr-4 text-right text-[15px]">{formatCurrencyWhole(trend.current)}</td>
                      <td className="num py-3 pr-4 text-right text-[15px] text-muted">{formatCurrencyWhole(trend.avg_3mo)}</td>
                      <td className={`num py-3 text-right text-[15px] ${up ? 'text-warn' : 'text-success'}`}>
                        {up ? '▲' : '▼'} {Math.abs(trend.pct_change)}%
                        <span className="sr-only">{up ? ' more than usual' : ' less than usual'}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="border-t border-ink/80 pt-4">
        <h3 className="mb-4 font-display text-2xl">Unusually large for their category</h3>
        {flagged.length === 0 ? (
          <EmptyState
            icon={TriangleAlert}
            title="Nothing flagged"
            description="No transactions in the last 3 months stand out as unusually large for their category."
          />
        ) : (
          <ul>
            {flagged.map((txn) => (
              <li key={txn.id} className="flex items-baseline justify-between gap-4 border-b border-edge/10 py-3">
                <div className="min-w-0">
                  <p className="truncate font-medium">{txn.merchant}</p>
                  <p className="mt-0.5 text-[13px] text-muted">
                    {txn.category} · {formatDate(txn.timestamp)}
                  </p>
                </div>
                <p className="num text-xl">{formatCurrencyWhole(txn.amount)}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
