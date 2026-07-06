'use client';

import { useApi } from '@/utils/useApi';
import { Alert, Loading, ProgressBar } from '@/components/ui';

interface Summary {
  total_transactions: number;
  labeled_transactions: number;
  labeling_percentage: number;
  total_spend: number;
}

interface Category {
  category: string;
  total_amount: number;
  transaction_count: number;
}

interface Trend {
  date: string;
  total_spend: number;
}

export default function StatsTab() {
  const summaryQ = useApi<Summary>('/dashboard/summary');
  const categoryQ = useApi<{ categories: Category[] }>('/dashboard/by-category');
  const trendsQ = useApi<{ trends: Trend[] }>('/dashboard/trends?days=30');

  if (summaryQ.loading || categoryQ.loading || trendsQ.loading) {
    return <Loading label="Loading dashboard..." />;
  }

  const summary = summaryQ.data;
  const byCategory = categoryQ.data?.categories || [];
  const trends = trendsQ.data?.trends || [];
  const error = summaryQ.error || categoryQ.error || trendsQ.error;

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">Overview</h2>

      {error && <Alert kind="error">{error}</Alert>}

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <p className="text-gray-600 text-sm font-medium mb-1">Total Transactions</p>
            <p className="text-3xl font-bold text-gray-900">{summary.total_transactions}</p>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <p className="text-gray-600 text-sm font-medium mb-1">Labeled</p>
            <p className="text-3xl font-bold text-gray-900">{summary.labeled_transactions}</p>
            <p className="text-xs text-gray-500 mt-1">{summary.labeling_percentage}% complete</p>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <p className="text-gray-600 text-sm font-medium mb-1">Total Spend</p>
            <p className="text-3xl font-bold text-gray-900">¥{summary.total_spend.toFixed(0)}</p>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <p className="text-gray-600 text-sm font-medium mb-1">Status</p>
            <p className="text-lg font-bold text-blue-600">
              {summary.labeling_percentage === 100 ? '✓ Complete' : 'In Progress'}
            </p>
          </div>
        </div>
      )}

      {/* Spending by Category */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="font-bold text-gray-900 mb-4">Spending by Category</h3>

        {byCategory.length === 0 ? (
          <p className="text-gray-600">No categorized transactions yet. Upload and label some data!</p>
        ) : (
          <div className="space-y-3">
            {[...byCategory]
              .sort((a, b) => b.total_amount - a.total_amount)
              .map((cat) => {
                const total = byCategory.reduce((sum, c) => sum + c.total_amount, 0);
                const percentage = total > 0 ? Math.round((cat.total_amount / total) * 100) : 0;

                return (
                  <div key={cat.category}>
                    <div className="flex justify-between items-center mb-1">
                      <p className="font-medium text-gray-900">{cat.category}</p>
                      <p className="text-sm text-gray-600">
                        ¥{cat.total_amount.toFixed(2)} ({cat.transaction_count} txns)
                      </p>
                    </div>
                    <ProgressBar percent={percentage} />
                    <p className="text-xs text-gray-500 mt-1">{percentage}%</p>
                  </div>
                );
              })}
          </div>
        )}
      </div>

      {/* Spending Trend */}
      {trends.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="font-bold text-gray-900 mb-4">Recent Spending (30 days)</h3>
          <div className="space-y-2">
            {trends.slice(-7).map((trend) => {
              const max = Math.max(...trends.map((t) => t.total_spend));
              const percentage = max > 0 ? (trend.total_spend / max) * 100 : 0;
              return (
                <div key={trend.date}>
                  <div className="flex justify-between items-center mb-1">
                    <p className="text-sm text-gray-600">{trend.date}</p>
                    <p className="text-sm font-medium text-gray-900">¥{trend.total_spend.toFixed(0)}</p>
                  </div>
                  <ProgressBar percent={percentage} color="bg-green-500" height="h-1.5" />
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
