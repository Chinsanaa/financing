'use client';

import { useState } from 'react';
import { api } from '@/utils/api';
import { useApi, invalidate } from '@/utils/useApi';
import { Alert, Loading, ProgressBar } from '@/components/ui';

interface Transaction {
  id: string;
  date: string;
  merchant: string;
  description: string;
  amount: number;
  confidence: number;
  suggested_category: string | null;
}

interface Category {
  id: string;
  name: string;
}

export default function LabelTab() {
  const queueQ = useApi<{ transactions: Transaction[] }>('/dashboard/review-queue');
  const categoriesQ = useApi<{ categories: Category[] }>('/categories/');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [acting, setActing] = useState(false);
  const [actionError, setActionError] = useState('');

  const transactions = queueQ.data?.transactions || [];
  const categories = categoriesQ.data?.categories || [];

  const removeCurrent = () => {
    const tx = transactions[currentIndex];
    queueQ.setData((prev) =>
      prev
        ? { ...prev, transactions: prev.transactions.filter((t) => t.id !== tx.id) }
        : prev
    );
    setCurrentIndex((i) => Math.min(i, Math.max(0, transactions.length - 2)));
    invalidate('/dashboard'); // stats/action counts changed
  };

  const handleAccept = async () => {
    const tx = transactions[currentIndex];
    if (!tx) return;

    try {
      setActing(true);
      setActionError('');
      await api.classifyTx.accept(tx.id);
      removeCurrent();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to accept classification');
    } finally {
      setActing(false);
    }
  };

  const handleOverride = async (categoryId: string) => {
    const tx = transactions[currentIndex];
    if (!tx) return;

    try {
      setActing(true);
      setActionError('');
      await api.classifyTx.label(tx.id, categoryId);
      removeCurrent();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to label transaction');
    } finally {
      setActing(false);
    }
  };

  const handleSkip = () => {
    if (transactions.length === 0) return;
    setCurrentIndex((i) => (i + 1) % transactions.length);
  };

  if (queueQ.loading || categoriesQ.loading) {
    return <Loading label="Loading transactions..." />;
  }

  if (transactions.length === 0) {
    return <Alert kind="success">All transactions labeled! Great job.</Alert>;
  }

  const tx = transactions[Math.min(currentIndex, transactions.length - 1)];
  const progress = Math.round(((currentIndex + 1) / transactions.length) * 100);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Label Transactions</h2>
        <p className="text-gray-600">Review and categorize transactions</p>
      </div>

      {/* Progress */}
      <div className="bg-white rounded-lg p-4 border border-gray-200">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-700">Progress</span>
          <span className="text-sm text-gray-600">
            {currentIndex + 1} of {transactions.length}
          </span>
        </div>
        <ProgressBar percent={progress} />
      </div>

      {(actionError || queueQ.error) && (
        <Alert kind="error">{actionError || queueQ.error}</Alert>
      )}

      {/* Current Transaction */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Merchant</label>
            <p className="text-gray-900 font-medium">{tx.merchant}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Amount</label>
            <p className="text-gray-900 font-medium">¥{tx.amount.toFixed(2)}</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <p className="text-gray-700">{tx.description}</p>
        </div>

        {tx.suggested_category && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="text-sm text-gray-600">
              <strong>Model Suggestion:</strong> {tx.suggested_category}
              {tx.confidence > 0 && ` (${Math.round(tx.confidence * 100)}% confidence)`}
            </p>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="space-y-2">
        {tx.suggested_category && (
          <button
            onClick={handleAccept}
            disabled={acting}
            className="w-full bg-green-600 text-white font-medium py-3 rounded-lg hover:bg-green-700 disabled:opacity-50 transition"
          >
            ✓ Accept Suggestion
          </button>
        )}

        <div className="grid grid-cols-3 gap-2">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => handleOverride(cat.id)}
              disabled={acting}
              className="bg-gray-200 text-gray-900 font-medium py-2 rounded-lg hover:bg-gray-300 disabled:opacity-50 transition text-sm"
            >
              {cat.name}
            </button>
          ))}
        </div>
      </div>

      {transactions.length > 1 && (
        <button
          onClick={handleSkip}
          className="w-full bg-gray-100 text-gray-700 font-medium py-2 rounded-lg hover:bg-gray-200 transition text-sm"
        >
          Skip
        </button>
      )}
    </div>
  );
}
