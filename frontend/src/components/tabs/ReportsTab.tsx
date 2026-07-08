'use client';

import { useState } from 'react';
import { ChevronLeft, ChevronRight, Download, FileText, Check } from 'lucide-react';
import { useApi, invalidate } from '@/utils/useApi';
import { api } from '@/utils/api';
import { Alert } from '@/components/ui';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import Badge, { categoryColor } from '@/components/ui/Badge';
import EmptyState from '@/components/ui/EmptyState';
import Skeleton, { SkeletonRows } from '@/components/ui/Skeleton';
import { formatCurrencyWhole } from '@/utils/format';

interface Transaction {
  id: string;
  date: string;
  merchant: string;
  description: string;
  amount: number;
  category: string;
  category_id: string | null;
  label_source: string;
}

interface ReportsData {
  transactions: Transaction[];
  total_count: number;
  page: number;
  per_page: number;
}

interface Category {
  id: string;
  name: string;
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
  const [uncategorizedOnly, setUncategorizedOnly] = useState(false);
  const [exporting, setExporting] = useState(false);
  // Which row's category dropdown is open, and which row is mid-save / errored.
  const [editingId, setEditingId] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);

  const query = `/dashboard/reports?page=${page}&per_page=${PER_PAGE}${
    uncategorizedOnly ? '&uncategorized_only=true' : ''
  }`;
  const { data: reports, loading, error, setData, reload } = useApi<ReportsData>(query);
  const { data: cats } = useApi<{ categories: Category[] }>('/categories/');
  const categories = cats?.categories || [];

  const totalPages = reports ? Math.max(1, Math.ceil(reports.total_count / PER_PAGE)) : 1;

  const handleCategoryChange = async (txn: Transaction, newCategoryId: string) => {
    if (!newCategoryId || newCategoryId === txn.category_id) {
      setEditingId(null);
      return;
    }
    const newName = categories.find((c) => c.id === newCategoryId)?.name || txn.category;
    setEditingId(null);
    setSavingId(txn.id);
    setRowError(null);

    // Optimistic: patch the cached row so the badge updates immediately.
    setData((prev) =>
      prev
        ? {
            ...prev,
            transactions: prev.transactions.map((t) =>
              t.id === txn.id
                ? { ...t, category: newName, category_id: newCategoryId, label_source: 'override' }
                : t
            ),
          }
        : prev
    );

    try {
      await api.classifyTx.label(txn.id, newCategoryId);
      invalidate('/dashboard'); // keep Overview/Budget in sync
    } catch (err: any) {
      setRowError(txn.merchant || 'this transaction');
      reload(); // roll back the optimistic write by refetching
    } finally {
      setSavingId(null);
    }
  };

  const changeFilter = (only: boolean) => {
    setUncategorizedOnly(only);
    setPage(1);
    setEditingId(null);
  };

  const handleExportXlsx = async () => {
    setExporting(true);
    try {
      const response = await api.export.xlsx();
      const url = URL.createObjectURL(response.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = response.headers['content-disposition']?.split('filename=')[1]?.replace(/"/g, '') || 'transactions.xlsx';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to export XLSX:', err);
    } finally {
      setExporting(false);
    }
  };

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

  if (loading && !reports) {
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
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                onClick={handleExportXlsx}
                loading={exporting}
                disabled={exporting || reports.transactions.length === 0}
              >
                <Download className="h-3.5 w-3.5" /> Export Excel (all)
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleExportCsv}
                disabled={reports.transactions.length === 0}
              >
                Export CSV
              </Button>
            </div>
          )
        }
      />

      {error && <Alert kind="error">{error}</Alert>}
      {rowError && (
        <Alert kind="error">Couldn&apos;t save the category for {rowError}. Please try again.</Alert>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        {reports && (
          <p className="text-sm text-muted">
            Showing {reports.transactions.length} of {reports.total_count} transactions
          </p>
        )}
        <label className="flex cursor-pointer items-center gap-2 text-sm text-muted">
          <input
            type="checkbox"
            checked={uncategorizedOnly}
            onChange={(e) => changeFilter(e.target.checked)}
            className="h-4 w-4 rounded border-edge/30 accent-accent"
          />
          Uncategorized only
        </label>
      </div>

      <Card className="overflow-hidden">
        {!reports || reports.transactions.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={FileText}
              title="No transactions to display"
              description={
                uncategorizedOnly
                  ? 'Nothing uncategorized — every transaction has a category.'
                  : 'Upload and categorize some data first — every transaction shows up here.'
              }
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
                {reports.transactions.map((txn) => (
                  <tr key={txn.id} className="transition-colors hover:bg-edge/5">
                    <td className="whitespace-nowrap px-4 py-3 text-muted">
                      {new Date(txn.date).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 font-medium">{txn.merchant}</td>
                    <td className="max-w-xs truncate px-4 py-3 text-xs text-muted">
                      {txn.description}
                    </td>
                    <td className="px-4 py-3">
                      {editingId === txn.id ? (
                        <select
                          autoFocus
                          defaultValue={txn.category_id ?? ''}
                          onChange={(e) => handleCategoryChange(txn, e.target.value)}
                          onBlur={() => setEditingId(null)}
                          className="rounded-pill border border-edge/20 bg-surface px-3 py-1 text-sm text-ink focus:border-accent-strong/50 focus:outline-none"
                        >
                          <option value="" disabled>
                            Choose category…
                          </option>
                          {categories.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.name}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <button
                          type="button"
                          onClick={() => {
                            setRowError(null);
                            setEditingId(txn.id);
                          }}
                          disabled={savingId === txn.id}
                          title="Click to change category"
                          className="group inline-flex items-center gap-1 disabled:opacity-60"
                        >
                          {txn.category === 'Uncategorized' ? (
                            <span className="rounded-pill border border-dashed border-edge/40 px-2 py-0.5 text-xs text-muted group-hover:border-accent-strong/50">
                              Uncategorized
                            </span>
                          ) : (
                            <Badge tone={categoryColor(txn.category)}>{txn.category}</Badge>
                          )}
                          {savingId === txn.id && (
                            <Check className="h-3 w-3 animate-pulse text-muted" />
                          )}
                        </button>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-medium tabular-nums">
                      {formatCurrencyWhole(txn.amount)}
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
