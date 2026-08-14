'use client';

import { useEffect, useState } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Download,
  FileText,
  Check,
  SlidersHorizontal,
} from 'lucide-react';
import { useApi, invalidate } from '@/utils/useApi';
import { api } from '@/utils/api';
import { Alert } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import { useCategoryColors } from '@/utils/useCategoryColors';
import { toneForKey } from '@/utils/categoryColors';
import EmptyState from '@/components/ui/EmptyState';
import Skeleton, { SkeletonRows } from '@/components/ui/Skeleton';
import Input, { Select } from '@/components/ui/Input';
import { formatCurrencyWhole, formatDate } from '@/utils/format';
import SplitModal from '@/components/tabs/SplitModal';

interface Transaction {
  id: string;
  date: string;
  merchant: string;
  description: string;
  amount: number;
  category: string;
  category_id: string | null;
  is_split: boolean;
  splits?: { category_id: string; category_name: string; amount: number }[] | null;
  label_source: string;
  bucket: 'Need' | 'Want' | 'Savings' | null;
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

const PER_PAGE_OPTIONS = [10, 20, 50, 100];

const SORT_OPTIONS: { value: string; sortBy: 'date' | 'category'; sortDir: 'asc' | 'desc'; label: string }[] = [
  { value: 'date-desc', sortBy: 'date', sortDir: 'desc', label: 'Date (Newest)' },
  { value: 'date-asc', sortBy: 'date', sortDir: 'asc', label: 'Date (Oldest)' },
  { value: 'category-asc', sortBy: 'category', sortDir: 'asc', label: 'Category (A–Z)' },
  { value: 'category-desc', sortBy: 'category', sortDir: 'desc', label: 'Category (Z–A)' },
];

// Same fixed sky/amber/emerald palette as the 50/30/20 breakdown
// (RuleBreakdown.tsx) — these are aggregate buckets, not per-category
// identities, so they stay constant rather than going through useCategoryColors().
const BUCKET_TONE: Record<'Need' | 'Want' | 'Savings', string> = {
  Need: toneForKey('sky'),
  Want: toneForKey('amber'),
  Savings: toneForKey('emerald'),
};

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
    [formatDate(t.date), t.merchant, t.description, t.category, t.amount, t.label_source].map(esc).join(',')
  );
  return [header.join(','), ...rows].join('\n');
}

export default function ReportsTab() {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [sortValue, setSortValue] = useState('date-desc');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [uncategorizedOnly, setUncategorizedOnly] = useState(false);
  const [exporting, setExporting] = useState(false);
  // Which row's category dropdown is open, and which row is mid-save / errored.
  const [editingId, setEditingId] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);

  // Search is debounced so typing doesn't refetch on every keystroke.
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [minAmount, setMinAmount] = useState('');
  const [maxAmount, setMaxAmount] = useState('');
  const [bucketFilter, setBucketFilter] = useState('');

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkCategoryId, setBulkCategoryId] = useState('');
  const [bulkApplying, setBulkApplying] = useState(false);
  const [bulkError, setBulkError] = useState('');

  const [splitModalTxn, setSplitModalTxn] = useState<Transaction | null>(null);
  const [splitSaving, setSplitSaving] = useState(false);
  const [splitError, setSplitError] = useState('');

  const activeSort = SORT_OPTIONS.find((s) => s.value === sortValue) || SORT_OPTIONS[0];

  const query = `/dashboard/reports?page=${page}&per_page=${perPage}&sort_by=${activeSort.sortBy}&sort_dir=${activeSort.sortDir}${
    uncategorizedOnly ? '&uncategorized_only=true' : ''
  }${search ? `&search=${encodeURIComponent(search)}` : ''}${
    dateFrom ? `&date_from=${dateFrom}` : ''
  }${dateTo ? `&date_to=${dateTo}` : ''}${minAmount ? `&min_amount=${minAmount}` : ''}${
    maxAmount ? `&max_amount=${maxAmount}` : ''
  }${bucketFilter ? `&bucket=${bucketFilter}` : ''}`;
  const { data: reports, loading, error, setData, reload } = useApi<ReportsData>(query);
  const { data: cats } = useApi<{ categories: Category[] }>('/categories/');
  const { toneFor } = useCategoryColors();
  const categories = cats?.categories || [];

  const totalPages = reports ? Math.max(1, Math.ceil(reports.total_count / perPage)) : 1;
  const pageNumbers = (() => {
    const nums: number[] = [];
    let start = Math.max(1, page - 1);
    const end = Math.min(totalPages, start + 2);
    start = Math.max(1, end - 2);
    for (let n = start; n <= end; n++) nums.push(n);
    return nums;
  })();

  const resetPageAndSelection = () => {
    setPage(1);
    setEditingId(null);
    setSelectedIds(new Set());
  };

  const toggleSelected = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAllOnPage = () => {
    if (!reports) return;
    const pageIds = reports.transactions.map((t) => t.id);
    const allSelected = pageIds.every((id) => selectedIds.has(id));
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (allSelected) pageIds.forEach((id) => next.delete(id));
      else pageIds.forEach((id) => next.add(id));
      return next;
    });
  };

  const handleBulkApply = async () => {
    if (!bulkCategoryId || selectedIds.size === 0) return;
    setBulkApplying(true);
    setBulkError('');
    try {
      await api.classifyTx.bulkLabel(Array.from(selectedIds), bulkCategoryId);
      invalidate('/dashboard');
      setSelectedIds(new Set());
      setBulkCategoryId('');
      reload();
    } catch (err: any) {
      setBulkError(err.response?.data?.detail || 'Failed to update selected transactions');
    } finally {
      setBulkApplying(false);
    }
  };

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

  const handleSplitSubmit = async (txn: Transaction, splits: { category_id: string; amount: number }[]) => {
    setSplitSaving(true);
    setSplitError('');
    try {
      await api.classifyTx.split(txn.id, splits);
      invalidate('/dashboard');
      setSplitModalTxn(null);
      reload();
    } catch (err: any) {
      setSplitError(err.response?.data?.detail || 'Failed to save split');
    } finally {
      setSplitSaving(false);
    }
  };

  const handleUnsplit = async (txn: Transaction) => {
    setSplitSaving(true);
    setSplitError('');
    try {
      await api.classifyTx.unsplit(txn.id);
      invalidate('/dashboard');
      setSplitModalTxn(null);
      reload();
    } catch (err: any) {
      setSplitError(err.response?.data?.detail || 'Failed to remove split');
    } finally {
      setSplitSaving(false);
    }
  };

  const changeFilter = (only: boolean) => {
    setUncategorizedOnly(only);
    resetPageAndSelection();
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
        <Button
          variant="outline"
          size="sm"
          onClick={() => setFiltersOpen((v) => !v)}
          aria-expanded={filtersOpen}
        >
          <SlidersHorizontal className="h-3.5 w-3.5" /> Filters
        </Button>
      </div>

      {filtersOpen && (
        <Card className="space-y-4 p-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[200px] flex-1">
              <Input
                label="Search"
                placeholder="Merchant or description…"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
              />
            </div>
            <div className="w-[150px]">
              <Input
                type="date"
                label="From"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                  resetPageAndSelection();
                }}
              />
            </div>
            <div className="w-[150px]">
              <Input
                type="date"
                label="To"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value);
                  resetPageAndSelection();
                }}
              />
            </div>
            <div className="w-[120px]">
              <Input
                type="number"
                label="Min amount"
                value={minAmount}
                onChange={(e) => {
                  setMinAmount(e.target.value);
                  resetPageAndSelection();
                }}
              />
            </div>
            <div className="w-[120px]">
              <Input
                type="number"
                label="Max amount"
                value={maxAmount}
                onChange={(e) => {
                  setMaxAmount(e.target.value);
                  resetPageAndSelection();
                }}
              />
            </div>
          </div>

          <div className="flex flex-wrap items-end gap-3">
            <div className="w-[170px]">
              <Select
                label="Sort by"
                value={sortValue}
                onChange={(e) => {
                  setSortValue(e.target.value);
                  resetPageAndSelection();
                }}
              >
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </Select>
            </div>
            <div className="w-[130px]">
              <Select
                label="Rows per page"
                value={perPage}
                onChange={(e) => {
                  setPerPage(Number(e.target.value));
                  resetPageAndSelection();
                }}
              >
                {PER_PAGE_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </Select>
            </div>
            <div className="w-[140px]">
              <Select
                label="Bucket"
                value={bucketFilter}
                onChange={(e) => {
                  setBucketFilter(e.target.value);
                  resetPageAndSelection();
                }}
              >
                <option value="">All</option>
                <option value="Need">Need</option>
                <option value="Want">Want</option>
                <option value="Savings">Savings</option>
              </Select>
            </div>
            <label className="flex cursor-pointer items-center gap-2 pb-2.5 text-sm text-muted">
              <input
                type="checkbox"
                checked={uncategorizedOnly}
                onChange={(e) => changeFilter(e.target.checked)}
                className="h-4 w-4 rounded border-edge/30 accent-accent"
              />
              Uncategorized only
            </label>
          </div>
        </Card>
      )}

      {selectedIds.size > 0 && (
        <Card className="flex flex-wrap items-center gap-3 border-accent/25 p-4">
          <p className="text-sm font-medium">{selectedIds.size} selected</p>
          <div className="w-[200px]">
            <Select value={bulkCategoryId} onChange={(e) => setBulkCategoryId(e.target.value)}>
              <option value="" disabled>
                Move to category…
              </option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </div>
          <Button size="sm" onClick={handleBulkApply} loading={bulkApplying} disabled={!bulkCategoryId}>
            Apply
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setSelectedIds(new Set())}>
            Clear selection
          </Button>
          {bulkError && <Alert kind="error">{bulkError}</Alert>}
        </Card>
      )}

      <Card className="flex max-h-[calc(100vh-22rem)] flex-col overflow-hidden">
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
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 z-10 border-b border-edge/8 bg-surface-2/95 backdrop-blur">
                <tr>
                  <th className="w-10 px-4 py-3">
                    <input
                      type="checkbox"
                      checked={reports.transactions.every((t) => selectedIds.has(t.id))}
                      onChange={toggleSelectAllOnPage}
                      className="h-4 w-4 rounded border-edge/30 accent-accent"
                      aria-label="Select all on this page"
                    />
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-muted">Date</th>
                  <th className="px-4 py-3 text-left font-medium text-muted">Merchant</th>
                  <th className="px-4 py-3 text-left font-medium text-muted">Description</th>
                  <th className="px-4 py-3 text-left font-medium text-muted">Category</th>
                  <th className="px-4 py-3 text-left font-medium text-muted">Bucket</th>
                  <th className="px-4 py-3 text-right font-medium text-muted">Amount</th>
                  <th className="px-4 py-3 text-center font-medium text-muted">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-edge/8">
                {reports.transactions.map((txn) => (
                  <tr key={txn.id} className="transition-colors hover:bg-edge/5">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(txn.id)}
                        onChange={() => toggleSelected(txn.id)}
                        className="h-4 w-4 rounded border-edge/30 accent-accent"
                        aria-label={`Select ${txn.merchant}`}
                      />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-muted">
                      {formatDate(txn.date)}
                    </td>
                    <td className="px-4 py-3 font-medium">{txn.merchant}</td>
                    <td className="max-w-xs truncate px-4 py-3 text-xs text-muted">
                      {txn.description}
                    </td>
                    <td className="px-4 py-3">
                      {txn.is_split ? (
                        <button
                          type="button"
                          onClick={() => {
                            setSplitError('');
                            setSplitModalTxn(txn);
                          }}
                          title="Click to edit split"
                          className="group inline-flex items-center gap-1"
                        >
                          <Badge tone="neutral">Split ({txn.splits?.length ?? 0})</Badge>
                        </button>
                      ) : editingId === txn.id ? (
                        <select
                          autoFocus
                          defaultValue={txn.category_id ?? ''}
                          onChange={(e) => handleCategoryChange(txn, e.target.value)}
                          onBlur={() => setEditingId(null)}
                          className="rounded-pill border border-edge/20 bg-surface px-3 py-1 text-sm text-ink focus:border-accent-strong/50 focus:outline-none focus:ring-2 focus:ring-accent/20"
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
                        <div className="flex items-center gap-1">
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
                              <Badge tone={toneFor(txn.category)}>{txn.category}</Badge>
                            )}
                            {savingId === txn.id && (
                              <Check className="h-3 w-3 animate-pulse text-muted" />
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setSplitError('');
                              setSplitModalTxn(txn);
                            }}
                            title="Split across categories"
                            className="text-xs text-muted underline decoration-dotted hover:text-ink"
                          >
                            Split
                          </button>
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {txn.bucket && <Badge tone={BUCKET_TONE[txn.bucket]}>{txn.bucket}</Badge>}
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
        <div className="flex items-center justify-center gap-1">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(1)}
            disabled={page <= 1}
            aria-label="First page"
          >
            <ChevronsLeft className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            aria-label="Previous page"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </Button>
          {pageNumbers.map((n) => (
            <Button
              key={n}
              variant={n === page ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setPage(n)}
              aria-current={n === page ? 'page' : undefined}
            >
              {n}
            </Button>
          ))}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            aria-label="Next page"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(totalPages)}
            disabled={page >= totalPages}
            aria-label="Last page"
          >
            <ChevronsRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}

      {splitModalTxn && (
        <SplitModal
          transaction={splitModalTxn}
          categories={categories}
          saving={splitSaving}
          error={splitError}
          onSubmit={(splits) => handleSplitSubmit(splitModalTxn, splits)}
          onUnsplit={() => handleUnsplit(splitModalTxn)}
          onClose={() => {
            setSplitModalTxn(null);
            setSplitError('');
          }}
        />
      )}
    </div>
  );
}
