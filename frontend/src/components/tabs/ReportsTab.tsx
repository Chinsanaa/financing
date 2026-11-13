'use client';

import { Fragment, useEffect, useMemo, useState } from 'react';
import { m } from 'framer-motion';
import RollingNumber from '@/components/ui/RollingNumber';
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Download,
  FileText,
  SlidersHorizontal,
} from 'lucide-react';
import { useApi, invalidate } from '@/utils/useApi';
import { api } from '@/utils/api';
import { Alert } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import Segmented from '@/components/ui/Segmented';
import { useCategoryColors } from '@/utils/useCategoryColors';
import EmptyState from '@/components/ui/EmptyState';
import Skeleton, { SkeletonRows } from '@/components/ui/Skeleton';
import Input, { Select } from '@/components/ui/Input';
import SplitModal from '@/components/tabs/SplitModal';
import type { Category, KindFilter, ReportsResponse } from '@/types/v5';
import { errorDetail } from '@/utils/errors';
import { downloadBlob, downloadTransactionsXlsx } from '@/utils/download';
import ReportsBulkBar from './reports/ReportsBulkBar';
import ReportsRow from './reports/ReportsRow';
import ReportsTypeEditorRow from './reports/ReportsTypeEditorRow';
import { toCsv } from './reports/reportsCsv';
import {
  KIND_OPTIONS,
  PER_PAGE_OPTIONS,
  SORT_OPTIONS,
  TYPE_CHOICES,
  parseTypeValue,
  typeValue,
} from './reports/reportsHelpers';
import type { Transaction } from './reports/reportsHelpers';

export default function ReportsTab() {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [sortValue, setSortValue] = useState('date-desc');
  const [kind, setKind] = useState<KindFilter>('expense');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [uncategorizedOnly, setUncategorizedOnly] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState('');
  // Which row's category dropdown is open, and which row is mid-save / errored.
  const [editingId, setEditingId] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);

  // "Change type" inline editor (one row at a time).
  const [typeEditId, setTypeEditId] = useState<string | null>(null);
  const [typeDraft, setTypeDraft] = useState('');
  const [typeSaving, setTypeSaving] = useState(false);
  const [typeError, setTypeError] = useState('');
  const [typeNotice, setTypeNotice] = useState('');

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
  // Category filters (bucket, uncategorized) only match spending rows (API_V5 §3.7).
  const categoryFiltersApply = kind === 'expense';

  const query = api.paths.reports({
    page,
    per_page: perPage,
    sort_by: activeSort.sortBy,
    sort_dir: activeSort.sortDir,
    kind,
    uncategorized_only: categoryFiltersApply && uncategorizedOnly,
    search,
    date_from: dateFrom,
    date_to: dateTo,
    min_amount: minAmount === '' ? undefined : Number(minAmount),
    max_amount: maxAmount === '' ? undefined : Number(maxAmount),
    bucket: categoryFiltersApply && bucketFilter ? (bucketFilter as 'Need' | 'Want' | 'Savings') : undefined,
  });
  const { data: reports, loading, error, setData, reload } = useApi<ReportsResponse>(query);
  const { data: cats } = useApi<{ categories: Category[] }>(api.paths.categories);
  const { toneFor } = useCategoryColors();
  const categories = cats?.categories || [];
  const currencyHome = reports?.currency_home ?? null;
  const expenseRowsOnPage = useMemo(
    () => (reports ? reports.transactions.filter((t) => t.kind === 'expense') : []),
    [reports]
  );

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
    setTypeEditId(null);
    setSelectedIds(new Set());
  };

  const changeKind = (k: KindFilter) => {
    setKind(k);
    setTypeNotice('');
    resetPageAndSelection();
  };

  const toggleSelected = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Only spending rows can be bulk-recategorized (the backend 404s the rest).
  const toggleSelectAllOnPage = () => {
    const pageIds = expenseRowsOnPage.map((t) => t.id);
    const allSelected = pageIds.length > 0 && pageIds.every((id) => selectedIds.has(id));
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
      setBulkError(errorDetail(err, 'Failed to update selected transactions'));
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
      setSplitError(errorDetail(err, 'Failed to save split'));
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
      setSplitError(errorDetail(err, 'Failed to remove split'));
    } finally {
      setSplitSaving(false);
    }
  };

  const openTypeEditor = (txn: Transaction) => {
    if (typeEditId === txn.id) {
      setTypeEditId(null);
      return;
    }
    setEditingId(null);
    setTypeError('');
    setTypeNotice('');
    setTypeDraft(typeValue(txn));
    setTypeEditId(txn.id);
  };

  const handleTypeSave = async (txn: Transaction) => {
    if (!typeDraft || typeDraft === typeValue(txn)) {
      setTypeEditId(null);
      return;
    }
    const next = parseTypeValue(typeDraft);
    setTypeSaving(true);
    setTypeError('');
    try {
      await api.transactionKind.update(txn.id, next);
      const label = TYPE_CHOICES.flatMap((g) => g.options).find((o) => o.value === typeDraft)?.label ?? next.kind;
      setTypeNotice(`${txn.merchant || 'Transaction'} is now "${label}".`);
      setTypeEditId(null);
      setSelectedIds((prev) => {
        const s = new Set(prev);
        s.delete(txn.id);
        return s;
      });
      // Totals, cash flow, budgets and the review queue all depend on kind.
      invalidate('/dashboard');
      reload();
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 409) {
        setTypeError(
          'This transaction is split across categories. Remove the split first (click its "Split" badge, then "Remove split"), then change its type.'
        );
      } else if (status === 404) {
        setTypeError('This transaction no longer exists. Refresh the list and try again.');
      } else {
        setTypeError(errorDetail(err, "Couldn't change the type. Please try again."));
      }
    } finally {
      setTypeSaving(false);
    }
  };

  const changeFilter = (only: boolean) => {
    setUncategorizedOnly(only);
    resetPageAndSelection();
  };

  const handleExportXlsx = async () => {
    setExporting(true);
    setExportError('');
    try {
      await downloadTransactionsXlsx();
    } catch (err) {
      // Used to fail silently (console only) — tell the user.
      setExportError(errorDetail(err, 'Excel export failed. Please try again.'));
    } finally {
      setExporting(false);
    }
  };

  const handleExportCsv = () => {
    if (!reports || reports.transactions.length === 0) return;
    const blob = new Blob(['﻿' + toCsv(reports.transactions)], {
      type: 'text/csv;charset=utf-8;',
    });
    downloadBlob(blob, `transactions_page${reports.page}.csv`);
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

  const emptyDescription =
    kind === 'income'
      ? 'No income found. Salary and interest show up here once you import a statement that contains them (bank statements usually do).'
      : kind === 'transfer'
        ? 'No transfers found. Red packets, transfers to people, top-ups and repayments show up here once imported.'
        : uncategorizedOnly && categoryFiltersApply
          ? 'Nothing uncategorized — every transaction has a category.'
          : 'Upload and categorize some data first — every transaction shows up here.';

  const rowNoun = kind === 'expense' ? 'spending transactions' : kind === 'income' ? 'income transactions' : kind === 'transfer' ? 'transfers' : 'transactions';

  return (
    <div className="space-y-6">
      <SectionHeader
        title="All transactions"
        description="Search, filter, re-categorize, split and export everything you've imported."
        action={
          reports && (
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="outline"
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

      <div className="space-y-2">
        <div className="max-w-full overflow-x-auto">
          <Segmented<KindFilter>
            options={KIND_OPTIONS}
            value={kind}
            onChange={changeKind}
            label="Transaction type"
            layoutId="reports-kind"
            size="sm"
          />
        </div>
        <p className="max-w-2xl text-[13px] text-muted">
          Red packets and shared-bill collections you receive count as transfers, not income — change a
          row&apos;s type if that&apos;s wrong.
        </p>
      </div>

      {error && <Alert kind="error">{error}</Alert>}
      {exportError && <Alert kind="error">{exportError}</Alert>}
      {rowError && (
        <Alert kind="error">Couldn&apos;t save the category for {rowError}. Please try again.</Alert>
      )}
      {typeNotice && <Alert kind="success">{typeNotice}</Alert>}

      <div className="flex flex-wrap items-center justify-between gap-3">
        {reports && (
          <p className="text-sm text-muted">
            Showing {reports.transactions.length} of{' '}
            <span className="font-semibold text-ink">
              <RollingNumber value={reports.total_count} />
            </span>{' '}
            {rowNoun}
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
        <m.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}>
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
                value={categoryFiltersApply ? bucketFilter : ''}
                disabled={!categoryFiltersApply}
                title={categoryFiltersApply ? undefined : 'Buckets only apply to spending'}
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
            <label
              className={`flex items-center gap-2 pb-2.5 text-sm text-muted ${categoryFiltersApply ? 'cursor-pointer' : 'cursor-not-allowed opacity-60'}`}
              title={categoryFiltersApply ? undefined : 'Categories only apply to spending'}
            >
              <input
                type="checkbox"
                checked={categoryFiltersApply && uncategorizedOnly}
                disabled={!categoryFiltersApply}
                onChange={(e) => changeFilter(e.target.checked)}
                className="h-4 w-4 rounded border-edge/30 accent-accent"
              />
              Uncategorized only
            </label>
          </div>
          {!categoryFiltersApply && (
            <p className="text-[13px] text-muted">
              Bucket and category filters only apply to spending, so they&apos;re off for this view.
            </p>
          )}
        </Card>
        </m.div>
      )}

      {selectedIds.size > 0 && (
        <ReportsBulkBar
          selectedCount={selectedIds.size}
          bulkCategoryId={bulkCategoryId}
          onBulkCategoryChange={setBulkCategoryId}
          categories={categories}
          onApply={handleBulkApply}
          applying={bulkApplying}
          onClear={() => setSelectedIds(new Set())}
          error={bulkError}
        />
      )}

      <Card className="flex flex-col overflow-hidden md:max-h-[calc(100vh-22rem)] md:min-h-[16rem]">
        {!reports || reports.transactions.length === 0 ? (
          <div className="p-6">
            <EmptyState icon={FileText} title="No transactions to display" description={emptyDescription} />
          </div>
        ) : (
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 z-10 border-b border-edge/15 bg-surface">
                <tr>
                  <th className="w-10 py-3 pl-3 pr-1 sm:px-4">
                    <input
                      type="checkbox"
                      checked={expenseRowsOnPage.length > 0 && expenseRowsOnPage.every((t) => selectedIds.has(t.id))}
                      disabled={expenseRowsOnPage.length === 0}
                      onChange={toggleSelectAllOnPage}
                      className="h-4 w-4 rounded border-edge/30 accent-accent disabled:opacity-40"
                      aria-label="Select all spending rows on this page"
                    />
                  </th>
                  <th className="hidden px-4 py-3 text-left font-medium text-muted sm:table-cell">Date</th>
                  <th className="px-2 py-3 text-left font-medium text-muted sm:px-4">Merchant</th>
                  <th className="hidden px-4 py-3 text-left font-medium text-muted lg:table-cell">Description</th>
                  <th className="hidden px-4 py-3 text-left font-medium text-muted md:table-cell">Category</th>
                  <th className="hidden px-4 py-3 text-left font-medium text-muted xl:table-cell">Bucket</th>
                  <th className="px-2 py-3 text-right font-medium text-muted sm:px-4">Amount</th>
                  <th className="hidden px-4 py-3 text-center font-medium text-muted md:table-cell">Source</th>
                  <th className="py-3 pl-1 pr-3 sm:px-4">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody className="stagger-in divide-y divide-edge/8">
                {reports.transactions.map((txn) => {
                  const typeOpen = typeEditId === txn.id;
                  return (
                    <Fragment key={txn.id}>
                      <ReportsRow
                        txn={txn}
                        currencyHome={currencyHome}
                        selected={selectedIds.has(txn.id)}
                        typeOpen={typeOpen}
                        isEditing={editingId === txn.id}
                        isSaving={savingId === txn.id}
                        categories={categories}
                        toneFor={toneFor}
                        onToggleSelected={toggleSelected}
                        onOpenTypeEditor={openTypeEditor}
                        onOpenSplit={() => {
                          setSplitError('');
                          setSplitModalTxn(txn);
                        }}
                        onStartEdit={() => {
                          setRowError(null);
                          setTypeEditId(null);
                          setEditingId(txn.id);
                        }}
                        onStopEdit={() => setEditingId(null)}
                        onCategoryChange={handleCategoryChange}
                      />
                      {typeOpen && (
                        <ReportsTypeEditorRow
                          txn={txn}
                          typeDraft={typeDraft}
                          typeSaving={typeSaving}
                          typeError={typeError}
                          onDraftChange={(value) => {
                            setTypeDraft(value);
                            setTypeError('');
                          }}
                          onSave={handleTypeSave}
                          onCancel={() => setTypeEditId(null)}
                        />
                      )}
                    </Fragment>
                  );
                })}
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
              variant={n === page ? 'outline' : 'ghost'}
              size="sm"
              className={`num min-w-8 ${n === page ? 'border-ink' : ''}`}
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

      {splitModalTxn && splitModalTxn.kind === 'expense' && (
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
