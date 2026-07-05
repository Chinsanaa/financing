'use client';

import { useEffect, useState } from 'react';
import { api } from '@/utils/api';

interface Transaction {
  id: string;
  merchant: string;
  description: string;
  amount: number;
  category: string;
  confidence: number;
  label_source: string;
}

export default function ReviewTab({ token }: { token: string }) {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadReviewQueue = async () => {
      try {
        const res = await api.dashboard.reviewQueue(token);
        setTransactions(res.data.transactions || []);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load review queue');
      } finally {
        setLoading(false);
      }
    };

    loadReviewQueue();
  }, [token]);

  if (loading) {
    return <div className="text-gray-600">Loading review queue...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Review Queue</h2>
        <p className="text-gray-600">Transactions pending manual review</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {transactions.length === 0 ? (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded text-center">
          No pending reviews!
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left px-4 py-3 font-medium text-gray-700">Merchant</th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Description</th>
                <th className="text-right px-4 py-3 font-medium text-gray-700">Amount</th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Suggestion</th>
                <th className="text-center px-4 py-3 font-medium text-gray-700">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx) => (
                <tr key={tx.id} className="border-b border-gray-200 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{tx.merchant}</td>
                  <td className="px-4 py-3 text-gray-700">{tx.description}</td>
                  <td className="px-4 py-3 text-right text-gray-900 font-medium">
                    ¥{tx.amount.toFixed(2)}
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium">
                      {tx.category}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center text-gray-600">
                    {Math.round(tx.confidence * 100)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
