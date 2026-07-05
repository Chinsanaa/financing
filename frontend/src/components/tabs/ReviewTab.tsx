'use client';

import { useEffect, useState } from 'react';
import { api } from '@/utils/api';

interface Transaction {
  id: string;
  date: string;
  merchant: string;
  description: string;
  amount: number;
  confidence: number;
  suggested_category: string | null;
}

interface ReviewQueueData {
  transactions: Transaction[];
  count: number;
}

export default function ReviewTab({ token }: { token: string }) {
  const [data, setData] = useState<ReviewQueueData | null>(null);
  const [selectedTxn, setSelectedTxn] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [categories, setCategories] = useState<Array<{ id: string; name: string }>>([]);
  const [labeling, setLabeling] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const [queueRes, catRes] = await Promise.all([
          api.get('/dashboard/review-queue', { headers: { Authorization: `Bearer ${token}` } }),
          api.get('/categories/', { headers: { Authorization: `Bearer ${token}` } }),
        ]);
        setData(queueRes.data);
        setCategories(catRes.data.categories || []);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load data');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [token]);

  const handleLabel = async (txnId: string, categoryId: string) => {
    try {
      setLabeling(txnId);
      await api.post(`/classify/${txnId}/label`, { category_id: categoryId }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      // Reload queue after labeling
      const res = await api.get('/dashboard/review-queue', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setData(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to label transaction');
    } finally {
      setLabeling(null);
    }
  };

  const handleAccept = async (txnId: string) => {
    try {
      setLabeling(txnId);
      await api.post(`/classify/${txnId}/accept`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      // Reload queue after accepting
      const res = await api.get('/dashboard/review-queue', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setData(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to accept classification');
    } finally {
      setLabeling(null);
    }
  };

  if (loading) {
    return <div className="text-gray-600">Loading review queue...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Review Queue</h2>
        <p className="text-gray-600">Transactions pending manual review</p>
        {data && <p className="text-sm text-gray-500 mt-1">{data.count} items</p>}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {!data || data.transactions.length === 0 ? (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded text-center">
          ✓ No pending reviews! All transactions are categorized.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left px-4 py-3 font-medium text-gray-700">Date</th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Merchant</th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Description</th>
                <th className="text-right px-4 py-3 font-medium text-gray-700">Amount</th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Suggestion</th>
                <th className="text-center px-4 py-3 font-medium text-gray-700">Confidence</th>
                <th className="text-center px-4 py-3 font-medium text-gray-700">Action</th>
              </tr>
            </thead>
            <tbody>
              {data.transactions.map((tx) => (
                <tr
                  key={tx.id}
                  className={`border-b border-gray-200 hover:bg-gray-50 ${
                    selectedTxn === tx.id ? 'bg-blue-50' : ''
                  }`}
                >
                  <td className="px-4 py-3 text-gray-600 text-xs">
                    {new Date(tx.date).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-900">{tx.merchant}</td>
                  <td className="px-4 py-3 text-gray-700 max-w-xs truncate">{tx.description}</td>
                  <td className="px-4 py-3 text-right text-gray-900 font-medium">
                    ¥{tx.amount.toFixed(2)}
                  </td>
                  <td className="px-4 py-3">
                    {tx.suggested_category ? (
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium">
                        {tx.suggested_category}
                      </span>
                    ) : (
                      <span className="text-gray-500 text-xs">No suggestion</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center text-gray-600 text-xs">
                    {tx.confidence > 0 ? `${Math.round(tx.confidence * 100)}%` : '—'}
                  </td>
                  <td className="px-4 py-3 text-center space-y-1">
                    {selectedTxn === tx.id ? (
                      <div className="space-y-2">
                        {tx.suggested_category && (
                          <button
                            onClick={() => handleAccept(tx.id)}
                            disabled={labeling === tx.id}
                            className="block w-full px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded hover:bg-green-200 disabled:opacity-50"
                          >
                            {labeling === tx.id ? 'Labeling...' : 'Accept'}
                          </button>
                        )}
                        <select
                          onChange={(e) => {
                            if (e.target.value) {
                              handleLabel(tx.id, e.target.value);
                            }
                          }}
                          disabled={labeling === tx.id}
                          className="block w-full px-2 py-1 text-xs border border-gray-300 rounded"
                          defaultValue=""
                        >
                          <option value="">Change category...</option>
                          {categories.map((cat) => (
                            <option key={cat.id} value={cat.id}>
                              {cat.name}
                            </option>
                          ))}
                        </select>
                      </div>
                    ) : (
                      <button
                        onClick={() => setSelectedTxn(tx.id)}
                        className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                      >
                        Review
                      </button>
                    )}
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
