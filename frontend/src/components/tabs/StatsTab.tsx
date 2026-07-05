'use client';

import { useEffect, useState } from 'react';
import { api } from '@/utils/api';

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

export default function StatsTab({ token }: { token: string }) {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [byCategory, setByCategory] = useState<Category[]>([]);
  const [trends, setTrends] = useState<Trend[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadStats = async () => {
      try {
        setLoading(true);

        const [summaryRes, categoryRes, trendsRes] = await Promise.all([
          api.get('/dashboard/summary', { headers: { Authorization: `Bearer ${token}` } }),
          api.get('/dashboard/by-category', { headers: { Authorization: `Bearer ${token}` } }),
          api.get('/dashboard/trends?days=30', { headers: { Authorization: `Bearer ${token}` } }),
        ]);

        setSummary(summaryRes.data);
        setByCategory(categoryRes.data.categories || []);
        setTrends(trendsRes.data.trends || []);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load stats');
      } finally {
        setLoading(false);
      }
    };

    loadStats();
  }, [token]);

  if (loading) {
    return <div className="text-gray-600">Loading dashboard...</div>;
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">Overview</h2>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

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
            {byCategory
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
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
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
              const max = Math.max(...trends.map(t => t.total_spend));
              const percentage = max > 0 ? (trend.total_spend / max) * 100 : 0;
              return (
                <div key={trend.date}>
                  <div className="flex justify-between items-center mb-1">
                    <p className="text-sm text-gray-600">{trend.date}</p>
                    <p className="text-sm font-medium text-gray-900">¥{trend.total_spend.toFixed(0)}</p>
                  </div>
                  <div className="w-full bg-gray-200 rounded h-1.5">
                    <div
                      className="bg-green-500 h-1.5 rounded"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
