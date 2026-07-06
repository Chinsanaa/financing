'use client';

import { useState } from 'react';
import { useApi } from '@/utils/useApi';
import { Alert, Loading } from '@/components/ui';

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

const PER_PAGE = 100;

function toCsv(transactions: Transaction[]): string {
  const esc = (v: unknown) => {
    const s = String(v ?? '');
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const header = ['Date', 'Merchant', 'Description', 'Category', 'Amount', 'Source'];
  const rows = transactions.map((t) =>
    [t.date, t.merchant, t.description, t.category, t.amount, t.label_source].map(esc).join(',')
  );
  return [header.join(','), ...rows].join('\n');
}

export default function ReportsTab() {
  const [page, setPage] = useState(1);
  const { data: reports, loading, error } = useApi<ReportsData>(
    `/dashboard/reports?page=${page}&per_page=${PER_PAGE}`
  );

  const totalPages = reports ? Math.max(1, Math.ceil(reports.total_count / PER_PAGE)) : 1;

  const handleExportCsv = () => {
    if (!reports || reports.transactions.length === 0) return;
    const blob = new Blob(['﻿' + toCsv(reports.transactions)], {
      type: 'text/csv;charset=utf-8;',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transactions_page${reports.page}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return <Loading label="Loading reports..." />;
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

      {error && <Alert kind="error">{error}</Alert>}

      {/* Summary + Export */}
      {reports && (
        <div className="bg-white rounded-lg border border-gray-200 p-4 flex justify-between items-center">
          <p className="text-gray-600 text-sm">
            Showing {reports.transactions.length} of {reports.total_count} transactions
          </p>
          <button
            onClick={handleExportCsv}
            disabled={reports.transactions.length === 0}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium text-sm"
          >
            📥 Export CSV
          </button>
        </div>
      )}

      {/* Transactions Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {!reports || reports.transactions.length === 0 ? (
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
                {reports.transactions.map((txn, idx) => (
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

      {/* Pagination */}
      {reports && totalPages > 1 && (
        <div className="flex justify-between items-center">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-gray-50"
          >
            ← Previous
          </button>
          <p className="text-sm text-gray-600">
            Page {page} of {totalPages}
          </p>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-gray-50"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
