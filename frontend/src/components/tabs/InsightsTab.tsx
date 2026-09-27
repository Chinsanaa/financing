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
      <SectionHeader
        label="Planning"
        title="Insights"
        description="What changed this month compared with your usual, and anything that stands out."
      />

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
              const tone = up ? 'text-warn' : 'text-success';
              const borderTone = up ? 'border-warn/25' : 'border-success/25';
              const max = Math.max(trend.current, trend.avg_3mo, 1);
              return (
                <Card key={trend.category} hover className={`${borderTone} p-4`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2.5">
                      <span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${up ? 'bg-warn/10' : 'bg-success/10'}`}>
                        {up ? (
                          <TrendingUp className={`h-4 w-4 ${tone}`} />
                        ) : (
                          <TrendingDown className={`h-4 w-4 ${tone}`} />
                        )}
                      </span>
                      <div>
                        <p className="text-sm font-semibold">{trend.category}</p>
                        <p className="mt-0.5 text-xs text-muted">
                          {up ? 'Spending more than usual' : 'Spending less than usual'}
                        </p>
                      </div>
                    </div>
                    <p className={`font-display text-xl font-bold tabular-nums ${tone}`}>
                      {up ? '+' : ''}
                      {trend.pct_change}%
                    </p>
                  </div>
                  {/* This month vs 3-month average, on a shared scale */}
                  <div className="mt-4 space-y-2 text-xs">
                    <div className="flex items-center gap-3">
                      <span className="w-20 shrink-0 text-muted">This month</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-edge/8">
                        <div
                          className={`progress-fill h-full rounded-full ${up ? 'bg-warn' : 'bg-success'}`}
                          style={{ width: `${(trend.current / max) * 100}%` }}
                        />
                      </div>
                      <span className="w-16 shrink-0 text-right font-medium tabular-nums">{formatCurrencyWhole(trend.current)}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="w-20 shrink-0 text-muted">3-mo avg</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-edge/8">
                        <div className="progress-fill h-full rounded-full bg-muted/50" style={{ width: `${(trend.avg_3mo / max) * 100}%` }} />
                      </div>
                      <span className="w-16 shrink-0 text-right tabular-nums text-muted">{formatCurrencyWhole(trend.avg_3mo)}</span>
                    </div>
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
          <Card className="stagger-in divide-y divide-edge/8 overflow-hidden">
            {flagged.map((txn) => (
              <div key={txn.id} className="flex items-center justify-between gap-3 p-4 transition-colors hover:bg-edge/[0.03]">
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-danger/10 text-danger">
                    <TriangleAlert className="h-4 w-4" />
                  </span>
                  <div>
                  <p className="text-sm font-medium">{txn.merchant}</p>
                  <p className="mt-0.5 text-xs text-muted">
                    {txn.category} · {formatDate(txn.timestamp)}
                  </p>
                  </div>
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
