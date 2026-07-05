'use client';

import { useEffect, useState } from 'react';
import { api } from '@/utils/api';

interface BudgetInfo {
  budget_config: {
    monthly_income: number;
    currency: string;
  } | null;
  category_budgets: Array<{
    category: string;
    monthly_budget: number;
    current_spend: number;
    type: string;
  }>;
}

export default function BudgetTab({ token }: { token: string }) {
  const [budget, setBudget] = useState<BudgetInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadBudget = async () => {
      try {
        setLoading(true);
        const res = await api.get('/dashboard/budget', { headers: { Authorization: `Bearer ${token}` } });
        setBudget(res.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load budget');
      } finally {
        setLoading(false);
      }
    };

    loadBudget();
  }, [token]);

  if (loading) {
    return <div className="text-gray-600">Loading budget...</div>;
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">Budget & Forecast</h2>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Monthly Income */}
      {budget?.budget_config && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <p className="text-gray-600 text-sm font-medium mb-1">Monthly Income</p>
          <p className="text-3xl font-bold text-gray-900">
            ¥{budget.budget_config.monthly_income.toFixed(0)}
          </p>
        </div>
      )}

      {/* Category Budgets */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="font-bold text-gray-900 mb-4">Budget by Category</h3>

        {budget?.category_budgets.length === 0 ? (
          <p className="text-gray-600">No budget set. Create categories and set limits to get started.</p>
        ) : (
          <div className="space-y-4">
            {budget?.category_budgets.map((cat) => {
              const percentage = cat.monthly_budget > 0
                ? Math.round((cat.current_spend / cat.monthly_budget) * 100)
                : 0;
              const isOverBudget = cat.current_spend > cat.monthly_budget;
              const color = isOverBudget ? 'bg-red-600' : percentage > 80 ? 'bg-yellow-600' : 'bg-blue-600';

              return (
                <div key={cat.category}>
                  <div className="flex justify-between items-center mb-2">
                    <p className="font-medium text-gray-900">{cat.category}</p>
                    <p className={`text-sm font-bold ${isOverBudget ? 'text-red-600' : 'text-gray-900'}`}>
                      ¥{cat.current_spend.toFixed(0)} / ¥{cat.monthly_budget.toFixed(0)}
                    </p>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${color}`}
                      style={{ width: `${Math.min(percentage, 100)}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {isOverBudget
                      ? `¥${(cat.current_spend - cat.monthly_budget).toFixed(0)} over`
                      : `${percentage}% of budget`}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
