'use client';

import { useEffect, useState } from 'react';
import { api } from '@/utils/api';

interface SavingsInfo {
  savings_goal_monthly: number;
  income: number;
  current_spend: number;
  projected_savings: number;
  average_monthly_spend: number;
  is_anomaly: boolean;
}

export default function SavingsTab({ token }: { token: string }) {
  const [savings, setSavings] = useState<SavingsInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadSavings = async () => {
      try {
        setLoading(true);
        const res = await api.get('/dashboard/savings', { headers: { Authorization: `Bearer ${token}` } });
        setSavings(res.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load savings info');
      } finally {
        setLoading(false);
      }
    };

    loadSavings();
  }, [token]);

  if (loading) {
    return <div className="text-gray-600">Loading savings info...</div>;
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">Savings & Anomalies</h2>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {savings && (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <p className="text-gray-600 text-sm font-medium mb-1">Income</p>
              <p className="text-3xl font-bold text-gray-900">¥{savings.income.toFixed(0)}</p>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <p className="text-gray-600 text-sm font-medium mb-1">Current Spend (This Month)</p>
              <p className="text-3xl font-bold text-gray-900">¥{savings.current_spend.toFixed(0)}</p>
            </div>

            <div className={`bg-white rounded-lg border p-6 ${
              savings.projected_savings > 0 ? 'border-green-200' : 'border-red-200'
            }`}>
              <p className="text-gray-600 text-sm font-medium mb-1">Projected Savings</p>
              <p className={`text-3xl font-bold ${
                savings.projected_savings > 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                ¥{savings.projected_savings.toFixed(0)}
              </p>
            </div>
          </div>

          {/* Savings Goal vs Projected */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="font-bold text-gray-900 mb-4">Savings Goal</h3>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between items-center mb-2">
                  <p className="text-sm text-gray-600">Monthly Goal</p>
                  <p className="font-medium text-gray-900">¥{savings.savings_goal_monthly.toFixed(0)}</p>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      savings.projected_savings >= savings.savings_goal_monthly ? 'bg-green-600' : 'bg-yellow-600'
                    }`}
                    style={{
                      width: `${Math.min(
                        (savings.projected_savings / savings.savings_goal_monthly) * 100,
                        100
                      )}%`,
                    }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {savings.projected_savings >= savings.savings_goal_monthly
                    ? `✓ On track`
                    : `¥${(savings.savings_goal_monthly - savings.projected_savings).toFixed(0)} short`}
                </p>
              </div>
            </div>
          </div>

          {/* Historical Comparison */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="font-bold text-gray-900 mb-4">Spending Comparison</h3>
            <div className="space-y-2">
              <div>
                <p className="text-sm text-gray-600 mb-1">Average Monthly Spend (Last 3 Months)</p>
                <p className="text-2xl font-bold text-gray-900">¥{savings.average_monthly_spend.toFixed(0)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">This Month vs Average</p>
                <p className={`text-lg font-bold ${
                  savings.current_spend > savings.average_monthly_spend ? 'text-red-600' : 'text-green-600'
                }`}>
                  {savings.current_spend > savings.average_monthly_spend
                    ? `↑ ¥${(savings.current_spend - savings.average_monthly_spend).toFixed(0)} higher`
                    : `↓ ¥${(savings.average_monthly_spend - savings.current_spend).toFixed(0)} lower`}
                </p>
              </div>
            </div>

            {/* Anomaly Alert */}
            {savings.is_anomaly && (
              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                <p className="text-yellow-800 text-sm font-medium">⚠️ Spending Anomaly Detected</p>
                <p className="text-yellow-700 text-xs mt-1">
                  Current spending is 30% higher than your 3-month average.
                </p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
