'use client';

import { Sparkles, TrendingDown, TrendingUp, TriangleAlert } from 'lucide-react';
import { useApi } from '@/utils/useApi';
import { Alert } from '@/components/ui-feedback';
import Card, { SectionHeader } from '@/components/ui/Card';
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

  if (loading) {
    return (
      <div className="space-y-6">
        <SkeletonRows rows={4} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SectionHeader label="Planning" title="Insights" />

      {error && <Alert kind="error">{error}</Alert>}

      <div>
        <p className="section-label mb-3">Spending trends vs. 3-month average</p>
        {trends.length === 0 ? (
          <EmptyState
            icon={Sparkles}
            title="Not enough history yet"
            description="Once you have a few months of categorized transactions, we'll show you which categories are trending up or down."
          />
        ) : (
          <div className="grid gap-3 xl:grid-cols-2">
            {trends.map((trend) => {
              const up = trend.pct_change > 0;
              const tone = up ? 'text-[color:var(--chart-5)]' : 'text-success';
              const borderTone = up ? 'border-[color:var(--chart-5)]/25' : 'border-success/25';
              return (
                <Card key={trend.category} className={`${borderTone} p-4`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2.5">
                      {up ? (
                        <TrendingUp className={`mt-0.5 h-4 w-4 shrink-0 ${tone}`} />
                      ) : (
                        <TrendingDown className={`mt-0.5 h-4 w-4 shrink-0 ${tone}`} />
                      )}
                      <div>
                        <p className="text-sm font-semibold">{trend.category}</p>
                        <p className="mt-0.5 text-xs text-muted">
                          {formatCurrencyWhole(trend.current)} this month vs.{' '}
                          {formatCurrencyWhole(trend.avg_3mo)} avg
                        </p>
                      </div>
                    </div>
                    <p className={`font-display text-lg font-bold tabular-nums ${tone}`}>
                      {up ? '+' : ''}
                      {trend.pct_change}%
                    </p>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      <div>
        <p className="section-label mb-3">Unusually large transactions</p>
        {flagged.length === 0 ? (
          <EmptyState
            icon={TriangleAlert}
            title="Nothing flagged"
            description="No transactions in the last 3 months stand out as unusually large for their category."
          />
        ) : (
          <Card className="divide-y divide-edge/8">
            {flagged.map((txn) => (
              <div key={txn.id} className="flex items-center justify-between gap-3 p-4">
                <div>
                  <p className="text-sm font-medium">{txn.merchant}</p>
                  <p className="mt-0.5 text-xs text-muted">
                    {txn.category} · {formatDate(txn.timestamp)}
                  </p>
                </div>
                <p className="font-display text-sm font-bold tabular-nums">
                  {formatCurrencyWhole(txn.amount)}
                </p>
              </div>
            ))}
          </Card>
        )}
      </div>
    </div>
  );
}
