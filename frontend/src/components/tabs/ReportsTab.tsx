'use client';

import { useState } from 'react';
import { ChevronLeft, ChevronRight, Download, FileText } from 'lucide-react';
import { useApi } from '@/utils/useApi';
import { Alert } from '@/components/ui';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import Badge, { categoryColor } from '@/components/ui/Badge';
import EmptyState from '@/components/ui/EmptyState';
import Skeleton, { SkeletonRows } from '@/components/ui/Skeleton';

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

const LABEL_SOURCES: Record<string, string> = {
  rule: 'Rule',
  override: 'Manual',
  model: 'Model',
  model_agreed: 'Auto',
  none: 'Unset',
};

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
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-14 w-full" />
        <SkeletonRows rows={8} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        label="Reports"
        title="All transactions"
        action={
          reports && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportCsv}
              disabled={reports.transactions.length === 0}
            >
              <Download className="h-3.5 w-3.5" /> Export CSV
            </Button>
          )
        }
      />

      {error && <Alert kind="error">{error}</Alert>}

      {reports && (
        <p className="-mt-2 text-sm text-muted">
          Showing {reports.transactions.length} of {reports.total_count} transactions
        </p>
      )}

      <Card className="overflow-hidden">
        {!reports || reports.transactions.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={FileText}
              title="No transactions to display"
              description="Upload and categorize some data first — every labeled transaction shows up here."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-edge/8 bg-surface-2/60">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-muted">Date</th>
                  <th className="px-4 py-3 text-left font-medium text-muted">Merchant</th>
                  <th className="px-4 py-3 text-left font-medium text-muted">Description</th>
                  <th className="px-4 py-3 text-left font-medium text-muted">Category</th>
                  <th className="px-4 py-3 text-right font-medium text-muted">Amount</th>
                  <th className="px-4 py-3 text-center font-medium text-muted">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-edge/8">
                {reports.transactions.map((txn, idx) => (
                  <tr key={idx} className="transition-colors hover:bg-edge/5">
                    <td className="whitespace-nowrap px-4 py-3 text-muted">
                      {new Date(txn.date).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 font-medium">{txn.merchant}</td>
                    <td className="max-w-xs truncate px-4 py-3 text-xs text-muted">
                      {txn.description}
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={categoryColor(txn.category)}>{txn.category}</Badge>
                    </td>
                    <td className="px-4 py-3 text-right font-medium tabular-nums">
                      ¥{txn.amount.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <Badge tone="neutral">{LABEL_SOURCES[txn.label_source] || txn.label_source}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {reports && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
          >
            <ChevronLeft className="h-3.5 w-3.5" /> Previous
          </Button>
          <p className="text-sm text-muted tabular-nums">
            Page {page} of {totalPages}
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
          >
            Next <ChevronRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}
    </div>
  );
}
