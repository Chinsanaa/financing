'use client';

import { useEffect, useState } from 'react';
import { api } from '@/utils/api';

interface Transaction {
  date: string;
  merchant: string;
  description: string;
  amount: number;
  category: string;
  label_source: string;
}

interface ReportsData {
  transactions: Transaction[];
  total_count: number;
  page: number;
  per_page: number;
}

export default function ReportsTab({ token }: { token: string }) {
  const [reports, setReports] = useState<ReportsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadReports = async () => {
      try {
        setLoading(true);
        const res = await api.get('/dashboard/reports', { headers: { Authorization: `Bearer ${token}` } });
        setReports(res.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load reports');
      } finally {
        setLoading(false);
      }
    };

    loadReports();
  }, [token]);

  if (loading) {
    return <div className="text-gray-600">Loading reports...</div>;
  }

  const getLabelSourceLabel = (source: string) => {
    const labels: Record<string, string> = {
      rule: '📋 Rule',
      override: '✏️ Manual',
      model: '🤖 Model',
      model_agreed: '🎯 Auto',
      none: '❓ Unset',
    };
    return labels[source] || source;
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">Reports</h2>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Summary */}
      {reports && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-gray-600 text-sm">
            Showing {reports.transactions.length} of {reports.total_count} transactions
          </p>
        </div>
      )}

      {/* Transactions Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {reports?.transactions.length === 0 ? (
          <div className="p-6 text-gray-600">
            No transactions to display. Upload and categorize some data first.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Date</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Merchant</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Description</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Category</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-700">Amount</th>
                  <th className="px-4 py-3 text-center font-medium text-gray-700">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {reports?.transactions.map((txn, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-900">
                      {new Date(txn.date).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-gray-900 font-medium">{txn.merchant}</td>
                    <td className="px-4 py-3 text-gray-600 text-xs">{txn.description}</td>
                    <td className="px-4 py-3">
                      <span className="inline-block bg-blue-100 text-blue-800 text-xs font-medium px-2 py-1 rounded">
                        {txn.category}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-medium text-gray-900">
                      ¥{txn.amount.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-center text-xs whitespace-nowrap">
                      {getLabelSourceLabel(txn.label_source)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Export Button */}
      <div className="flex gap-3">
        <button className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 font-medium">
          📥 Export to CSV
        </button>
        <button className="flex-1 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 font-medium">
          📊 Export to Excel
        </button>
      </div>
    </div>
  );
}
