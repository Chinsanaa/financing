'use client';

import { useEffect, useState } from 'react';
import { api } from '@/utils/api';

interface Transaction {
  transaction_id: string;
  merchant: string;
  description: string;
  amount: number;
  category: string;
  confidence: number;
  label_source: string;
  needs_review: boolean;
}

export default function LabelTab({ token }: { token: string }) {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [classifying, setClassifying] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);

        // Fetch categories
        const categoriesRes = await api.categories.list(token);
        const categoryNames = categoriesRes.data.categories.map((c: any) => c.name);
        setCategories(categoryNames);

        // Fetch transactions to label
        const txRes = await api.classify.predict(token, 50);
        setTransactions(txRes.data.transactions);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load transactions');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [token]);

  const handleAccept = async () => {
    if (currentIndex >= transactions.length) return;

    const tx = transactions[currentIndex];
    try {
      await api.classify.accept(token, tx.transaction_id);
      setTransactions(transactions.filter((_, i) => i !== currentIndex));
      if (currentIndex >= transactions.length - 1) {
        setCurrentIndex(Math.max(0, transactions.length - 2));
      }
    } catch (err: any) {
      setError('Failed to accept classification');
    }
  };

  const handleOverride = async (category: string) => {
    if (currentIndex >= transactions.length) return;

    const tx = transactions[currentIndex];
    try {
      await api.classify.override(token, tx.transaction_id, category);
      setTransactions(transactions.filter((_, i) => i !== currentIndex));
      if (currentIndex >= transactions.length - 1) {
        setCurrentIndex(Math.max(0, transactions.length - 2));
      }
    } catch (err: any) {
      setError('Failed to override classification');
    }
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

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <p className="text-sm text-gray-600 mb-1">
            <strong>Model Suggestion:</strong> {tx.category} ({Math.round(tx.confidence * 100)}% confidence)
          </p>
          {tx.needs_review && (
            <p className="text-xs text-gray-500">This transaction needs manual review</p>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="space-y-2">
        <button
          onClick={handleAccept}
          disabled={classifying}
          className="w-full bg-green-600 text-white font-medium py-3 rounded-lg hover:bg-green-700 disabled:opacity-50 transition"
        >
          ✓ Accept Suggestion
        </button>

        <div className="grid grid-cols-3 gap-2">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => handleOverride(cat)}
              disabled={classifying}
              className="bg-gray-200 text-gray-900 font-medium py-2 rounded-lg hover:bg-gray-300 disabled:opacity-50 transition text-sm"
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      <button
        onClick={() => setCurrentIndex(Math.min(currentIndex + 1, transactions.length - 1))}
        className="w-full bg-gray-100 text-gray-700 font-medium py-2 rounded-lg hover:bg-gray-200 transition text-sm"
      >
        Skip
      </button>
    </div>
  );
}
