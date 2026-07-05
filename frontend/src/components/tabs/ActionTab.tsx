'use client';

import { useEffect, useState } from 'react';
import { api } from '@/utils/api';

interface Action {
  type: string;
  category?: string;
  current?: number;
  limit?: number;
  overage?: number;
  count?: number;
  message?: string;
}

export default function ActionTab({ token }: { token: string }) {
  const [actions, setActions] = useState<Action[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadActions = async () => {
      try {
        setLoading(true);
        const res = await api.get('/dashboard/action', { headers: { Authorization: `Bearer ${token}` } });
        setActions(res.data.actions || []);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load action items');
      } finally {
        setLoading(false);
      }
    };

    loadActions();
  }, [token]);

  if (loading) {
    return <div className="text-gray-600">Loading action items...</div>;
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">Action Plan</h2>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {actions.length === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <p className="text-green-900 font-medium">✓ All clear!</p>
          <p className="text-green-700 text-sm mt-1">No over-budget categories or pending items.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {actions.map((action, idx) => {
            if (action.type === 'over_budget') {
              return (
                <div
                  key={idx}
                  className="bg-red-50 border border-red-200 rounded-lg p-4"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-bold text-red-900">Over Budget: {action.category}</p>
                      <p className="text-red-700 text-sm mt-1">
                        Spent ¥{action.current?.toFixed(0)} of ¥{action.limit?.toFixed(0)} budget
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-red-600">
                        ¥{action.overage?.toFixed(0)}
                      </p>
                      <p className="text-xs text-red-600">over</p>
                    </div>
                  </div>
                </div>
              );
            } else if (action.type === 'pending_review') {
              return (
                <div
                  key={idx}
                  className="bg-blue-50 border border-blue-200 rounded-lg p-4"
                >
                  <p className="font-bold text-blue-900">📋 Pending Review</p>
                  <p className="text-blue-700 text-sm mt-1">{action.message}</p>
                  <button className="mt-2 text-blue-600 hover:text-blue-800 text-sm font-medium">
                    Review Transactions →
                  </button>
                </div>
              );
            }
            return null;
          })}
        </div>
      )}

      {/* Tips Section */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="font-bold text-gray-900 mb-4">Tips to Improve Your Finances</h3>
        <ul className="space-y-3">
          <li className="flex gap-3">
            <span className="text-blue-600 font-bold flex-shrink-0">1.</span>
            <span className="text-gray-700 text-sm">Review categories over 80% of budget and plan to reduce spending.</span>
          </li>
          <li className="flex gap-3">
            <span className="text-blue-600 font-bold flex-shrink-0">2.</span>
            <span className="text-gray-700 text-sm">Check for recurring transactions you can negotiate or cancel.</span>
          </li>
          <li className="flex gap-3">
            <span className="text-blue-600 font-bold flex-shrink-0">3.</span>
            <span className="text-gray-700 text-sm">Review the pending transactions in the queue to ensure accurate categorization.</span>
          </li>
          <li className="flex gap-3">
            <span className="text-blue-600 font-bold flex-shrink-0">4.</span>
            <span className="text-gray-700 text-sm">Set realistic savings goals based on your average spending patterns.</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
