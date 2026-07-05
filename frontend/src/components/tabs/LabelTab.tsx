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

interface Category {
  id: string;
  name: string;
}

export default function LabelTab({ token }: { token: string }) {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const [queueRes, catRes] = await Promise.all([
          api.get('/dashboard/review-queue', { headers: { Authorization: `Bearer ${token}` } }),
          api.get('/categories/', { headers: { Authorization: `Bearer ${token}` } }),
        ]);
        setTransactions(queueRes.data.transactions || []);
        setCategories(catRes.data.categories || []);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load transactions');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [token]);

  const removeCurrent = (txs: Transaction[]) => {
    const next = txs.filter((_, i) => i !== currentIndex);
    setTransactions(next);
    if (currentIndex >= next.length) {
      setCurrentIndex(Math.max(0, next.length - 1));
    }
  };

  const handleAccept = async () => {
    if (currentIndex >= transactions.length) return;
    const tx = transactions[currentIndex];

    try {
      setActing(true);
      await api.post(`/classify/${tx.id}/accept`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
      removeCurrent(transactions);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to accept classification');
    } finally {
      setActing(false);
    }
  };

  const handleOverride = async (categoryId: string) => {
    if (currentIndex >= transactions.length) return;
    const tx = transactions[currentIndex];

    try {
      setActing(true);
      await api.post(`/classify/${tx.id}/label`, { category_id: categoryId }, {
        headers: { Authorization: `Bearer ${token}` },
      });
      removeCurrent(transactions);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to label transaction');
    } finally {
      setActing(false);
    }
  };

  const handleSkip = () => {
    setCurrentIndex((i) => (i + 1) % transactions.length);
  };

  if (loading) {
    return <div className="text-gray-600">Loading transactions...</div>;
  }

  if (transactions.length === 0) {
    return (
      <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded text-center">
        All transactions labeled! Great job.
      </div>
    );
  }

  const tx = transactions[currentIndex];
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
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
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
