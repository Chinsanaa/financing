'use client';

import { useState } from 'react';
import { api } from '@/utils/api';
import { useApi, invalidate } from '@/utils/useApi';
import { Alert, Loading } from '@/components/ui';

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

export default function ReviewTab() {
  const { data, setData, loading, error: loadError } = useApi<ReviewQueueData>('/dashboard/review-queue');
  const categoriesQ = useApi<{ categories: Array<{ id: string; name: string }> }>('/categories/');
  const [selectedTxn, setSelectedTxn] = useState<string | null>(null);
  const [labeling, setLabeling] = useState<string | null>(null);
  const [actionError, setActionError] = useState('');

  const categories = categoriesQ.data?.categories || [];

  // Optimistically remove the acted-on row instead of refetching the whole
  // queue after every single action.
  const removeRow = (txnId: string) => {
    setData((prev) =>
      prev
        ? {
            ...prev,
            transactions: prev.transactions.filter((t) => t.id !== txnId),
            count: Math.max(0, prev.count - 1),
          }
        : prev
    );
    invalidate('/dashboard'); // stats/action counts changed
  };

  const handleLabel = async (txnId: string, categoryId: string) => {
    try {
      setLabeling(txnId);
      setActionError('');
      await api.classifyTx.label(txnId, categoryId);
      removeRow(txnId);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to label transaction');
    } finally {
      setLabeling(null);
    }
  };

  const handleAccept = async (txnId: string) => {
    try {
      setLabeling(txnId);
      setActionError('');
      await api.classifyTx.accept(txnId);
      removeRow(txnId);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to accept classification');
    } finally {
      setLabeling(null);
    }
  };

  if (loading) {
    return <Loading label="Loading review queue..." />;
  }

  const error = actionError || loadError;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Review Queue</h2>
        <p className="text-gray-600">Transactions pending manual review</p>
        {data && <p className="text-sm text-gray-500 mt-1">{data.count} items</p>}
      </div>

      {error && <Alert kind="error">{error}</Alert>}

      {!data || data.transactions.length === 0 ? (
        <Alert kind="success">✓ No pending reviews! All transactions are categorized.</Alert>
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
                          value=""
                          onChange={(e) => {
                            if (e.target.value) {
                              handleLabel(tx.id, e.target.value);
                            }
                          }}
                          disabled={labeling === tx.id}
                          className="block w-full px-2 py-1 text-xs border border-gray-300 rounded"
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
