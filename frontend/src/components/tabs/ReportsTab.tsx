'use client';

import { Fragment, useEffect, useState } from 'react';
import { m } from 'framer-motion';
import RollingNumber from '@/components/ui/RollingNumber';
import {
  ArrowLeftRight,
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
import Segmented from '@/components/ui/Segmented';
import { useCategoryColors } from '@/utils/useCategoryColors';
import { toneForKey } from '@/utils/categoryColors';
import EmptyState from '@/components/ui/EmptyState';
import Skeleton, { SkeletonRows } from '@/components/ui/Skeleton';
import Input, { Select } from '@/components/ui/Input';
import { formatCurrency, formatDate, formatHomeCurrency } from '@/utils/format';
import { rateTooltip } from '@/components/ui/MoneyPair';
import SplitModal from '@/components/tabs/SplitModal';
import type { FlowSubtype, KindFilter, ReportRow, ReportsResponse, TransactionKind } from '@/types/v5';

type Transaction = ReportRow;

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

const KIND_OPTIONS: { value: KindFilter; label: string }[] = [
  { value: 'expense', label: 'Spending' },
  { value: 'income', label: 'Income' },
  { value: 'transfer', label: 'Transfers' },
  { value: 'all', label: 'All' },
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

const NON_EXPENSE_HINT =
  "Income and transfers don't have a spending category. Use Change type to make this row spending first.";

/** Money came IN to the user (API_V5 §1.1 sign rule: income rows are + when
 *  money comes in; expense/transfer rows are − when money comes in). */
function isMoneyIn(t: Pick<Transaction, 'kind' | 'amount'>): boolean {
  return t.kind === 'income' ? t.amount > 0 : t.amount < 0;
}

/** Plain-English type label for a row, direction-aware ("Red packet received").
 *  null for ordinary purchases (they need no label). */
function typeLabel(t: Pick<Transaction, 'kind' | 'flow_subtype' | 'amount'>): string | null {
  const incoming = isMoneyIn(t);
  if (t.kind === 'expense') return t.flow_subtype === 'refund' ? 'Refund' : null;
  if (t.kind === 'income') {
    if (t.flow_subtype === 'salary') return 'Salary';
    if (t.flow_subtype === 'interest') return 'Interest';
    return t.flow_subtype === 'other' ? 'Other income' : 'Income';
  }
  switch (t.flow_subtype) {
    case 'red_packet':
      return incoming ? 'Red packet received' : 'Red packet sent';
    case 'aa_collection':
      return 'Shared bill (AA) collected';
    case 'p2p_transfer':
      return incoming ? 'Transfer from a person' : 'Transfer to a person';
    case 'own_account':
      return 'Own-account transfer';
    case 'repayment':
      return 'Credit card repayment';
    case 'top_up':
      return 'Wallet top-up';
    case 'withdrawal':
      return 'Withdrawal to bank';
    default:
      return incoming ? 'Transfer in' : 'Transfer out';
  }
}

// "Change type" choices. Value = "kind:subtype" ("kind:" = no subtype).
// Labels are direction-neutral; the row's sign decides "sent"/"received".
const TYPE_CHOICES: { group: string; options: { value: string; label: string }[] }[] = [
  {
    group: 'Spending',
    options: [
      { value: 'expense:', label: 'Purchase (spending)' },
      { value: 'expense:refund', label: 'Refund of a purchase' },
    ],
  },
  {
    group: 'Income',
    options: [
      { value: 'income:salary', label: 'Salary' },
      { value: 'income:interest', label: 'Interest' },
      { value: 'income:other', label: 'Other income' },
    ],
  },
  {
    group: 'Transfer (not spending or income)',
    options: [
      { value: 'transfer:red_packet', label: 'Red packet' },
      { value: 'transfer:aa_collection', label: 'Shared bill (AA) collection' },
      { value: 'transfer:p2p_transfer', label: 'Transfer to/from a person' },
      { value: 'transfer:own_account', label: 'Own-account transfer' },
      { value: 'transfer:repayment', label: 'Credit card repayment' },
      { value: 'transfer:top_up', label: 'Wallet top-up' },
      { value: 'transfer:withdrawal', label: 'Withdrawal to bank' },
      { value: 'transfer:other', label: 'Other transfer' },
    ],
  },
];

function typeValue(t: Pick<Transaction, 'kind' | 'flow_subtype'>): string {
  return `${t.kind}:${t.flow_subtype ?? ''}`;
}

function parseTypeValue(v: string): { kind: TransactionKind; flow_subtype: FlowSubtype | null } {
  const [kind, sub] = v.split(':');
  return { kind: kind as TransactionKind, flow_subtype: (sub || null) as FlowSubtype | null };
}

function typeChangeNote(kind: TransactionKind): string {
  if (kind === 'expense')
    return 'It will count as spending and go to your review queue to get a category.';
  if (kind === 'income') return 'It will count as income. Its category is removed and it no longer counts as spending.';
  return "It won't count as spending or income. Its category is removed.";
}

/** FastAPI error detail → one readable line (422s carry a list). */
function errorDetail(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d: any) => d?.msg).filter(Boolean).join('; ') || fallback;
  return fallback;
}

function toCsv(transactions: Transaction[]): string {
  const esc = (v: unknown) => {
    const s = String(v ?? '');
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const header = ['Date', 'Merchant', 'Description', 'Category', 'Type', 'Amount', 'Home amount', 'Source'];
  const rows = transactions.map((t) =>
    [
      formatDate(t.date),
      t.merchant,
      t.description,
      t.kind === 'expense' ? t.category : '',
      typeLabel(t) ?? 'Purchase',
      t.amount,
      t.amount_home ?? '',
      t.label_source,
    ]
      .map(esc)
      .join(',')
  );
  return [header.join(','), ...rows].join('\n');
}

/** CNY amount (money in = "+" in the positive color) with the home-currency
 *  equivalent underneath. Rate tooltip uses the row's own date. */
function AmountCell({ txn, currencyHome }: { txn: Transaction; currencyHome: string | null }) {
  const incoming = isMoneyIn(txn);
  const showHome = !!currencyHome && txn.amount_home !== null && Number.isFinite(txn.amount_home);
  const day = (txn.date || '').slice(0, 10);
  // The row carries no rate, so derive it from the two rounded amounts —
  // only when the home amount is large enough for that to be accurate.
  const rate =
    showHome && Math.abs(txn.amount_home as number) >= 10 && txn.amount !== 0
      ? (txn.amount_home as number) / txn.amount
      : undefined;
  const title = showHome
    ? rateTooltip(rate, day) ?? `Converted at the ECB rate on ${day}`
    : undefined;
  return (
    <span className="inline-flex flex-col items-end" title={title}>
      <span className={`num whitespace-nowrap text-[15px] ${incoming ? 'text-positive' : ''}`}>
        {incoming ? `+${formatCurrency(Math.abs(txn.amount))}` : formatCurrency(txn.amount)}
      </span>
      {showHome && (
        <span className="num whitespace-nowrap text-xs text-muted">
          <span aria-hidden="true">≈ </span>
          <span className="sr-only">approximately </span>
          {incoming
            ? `+${formatHomeCurrency(Math.abs(txn.amount_home as number), currencyHome as string)}`
            : formatHomeCurrency(txn.amount_home as number, currencyHome as string)}
        </span>
      )}
    </span>
  );
}

export default function ReportsTab() {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [sortValue, setSortValue] = useState('date-desc');
  const [kind, setKind] = useState<KindFilter>('expense');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [uncategorizedOnly, setUncategorizedOnly] = useState(false);
  const [exporting, setExporting] = useState(false);
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
  const { data: cats } = useApi<{ categories: Category[] }>('/categories/');
  const { toneFor } = useCategoryColors();
  const categories = cats?.categories || [];
  const currencyHome = reports?.currency_home ?? null;
  const expenseRowsOnPage = reports ? reports.transactions.filter((t) => t.kind === 'expense') : [];

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

  const emptyDescription =
    kind === 'income'
      ? 'No income found. Salary and interest show up here once you import a statement that contains them (bank statements usually do).'
      : kind === 'transfer'
        ? 'No transfers found. Red packets, transfers to people, top-ups and repayments show up here once imported.'
        : uncategorizedOnly && categoryFiltersApply
          ? 'Nothing uncategorized — every transaction has a category.'
          : 'Upload and categorize some data first — every transaction shows up here.';

  const rowNoun = kind === 'expense' ? 'spending transactions' : kind === 'income' ? 'income transactions' : kind === 'transfer' ? 'transfers' : 'transactions';
  // 8 visible columns on desktop + the action column.
  const COLS = 9;

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
                  const isExpense = txn.kind === 'expense';
                  const label = typeLabel(txn);
                  const typeOpen = typeEditId === txn.id;
                  const categoryCell = !isExpense ? (
                    <span className="inline-flex items-center gap-2" title={NON_EXPENSE_HINT}>
                      <span className="text-xs text-muted">No category</span>
                      <button
                        type="button"
                        disabled
                        aria-label="Split (only for spending)"
                        className="cursor-not-allowed text-xs text-muted/60 underline decoration-dotted"
                      >
                        Split
                      </button>
                    </span>
                  ) : txn.is_split ? (
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
                      className="rounded-md border border-edge/20 bg-surface px-2.5 py-1 text-sm text-ink focus:border-accent focus:outline-none"
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
                          setTypeEditId(null);
                          setEditingId(txn.id);
                        }}
                        disabled={savingId === txn.id}
                        title="Click to change category"
                        className="group inline-flex items-center gap-1 disabled:opacity-60"
                      >
                        {txn.category === 'Uncategorized' ? (
                          <span className="rounded-[4px] border border-dashed border-edge/40 px-1.5 py-0.5 text-xs text-muted group-hover:border-ink/50">
                            Uncategorized
                          </span>
                        ) : (
                          <Badge tone={toneFor(txn.category)}>{txn.category}</Badge>
                        )}
                        {savingId === txn.id && <Check className="h-3 w-3 animate-pulse text-muted" />}
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
                  );

                  return (
                    <Fragment key={txn.id}>
                      <tr
                        className={`transition-colors hover:bg-edge/5 ${selectedIds.has(txn.id) ? 'bg-edge/[0.06]' : ''} ${typeOpen ? 'bg-edge/[0.04]' : ''}`}
                      >
                        <td className="py-3 pl-3 pr-1 align-top sm:px-4 sm:align-middle">
                          <span title={isExpense ? undefined : NON_EXPENSE_HINT} className="inline-flex">
                            <input
                              type="checkbox"
                              checked={selectedIds.has(txn.id)}
                              disabled={!isExpense}
                              onChange={() => toggleSelected(txn.id)}
                              className="h-4 w-4 rounded border-edge/30 accent-accent disabled:opacity-30"
                              aria-label={`Select ${txn.merchant}`}
                            />
                          </span>
                        </td>
                        <td className="hidden whitespace-nowrap px-4 py-3 text-muted sm:table-cell">
                          {formatDate(txn.date)}
                        </td>
                        <td className="min-w-0 px-2 py-3 sm:px-4">
                          <div className="font-medium leading-snug">{txn.merchant}</div>
                          <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted">
                            <span className="sm:hidden">{formatDate(txn.date)}</span>
                            {label && (
                              <span
                                className={`rounded-[4px] border px-1.5 py-px leading-4 ${
                                  isMoneyIn(txn) ? 'border-positive/35 text-positive' : 'border-edge/20 text-muted'
                                }`}
                              >
                                {label}
                              </span>
                            )}
                          </div>
                          {/* Phone: category lives under the merchant (column hidden). */}
                          {isExpense && <div className="mt-1.5 md:hidden">{categoryCell}</div>}
                        </td>
                        <td className="hidden max-w-xs truncate px-4 py-3 text-xs text-muted lg:table-cell">
                          {txn.description}
                        </td>
                        <td className="hidden px-4 py-3 md:table-cell">{categoryCell}</td>
                        <td className="hidden px-4 py-3 xl:table-cell">
                          {txn.bucket && <Badge tone={BUCKET_TONE[txn.bucket]}>{txn.bucket}</Badge>}
                        </td>
                        <td className="px-2 py-3 text-right align-top sm:px-4 sm:align-middle">
                          <AmountCell txn={txn} currencyHome={currencyHome} />
                        </td>
                        <td className="hidden px-4 py-3 text-center md:table-cell">
                          {isExpense ? (
                            <Badge tone="neutral">{LABEL_SOURCES[txn.label_source] || txn.label_source}</Badge>
                          ) : (
                            <span className="text-xs text-muted">—</span>
                          )}
                        </td>
                        <td className="py-3 pl-1 pr-3 text-right align-top sm:px-4 sm:align-middle">
                          <button
                            type="button"
                            onClick={() => openTypeEditor(txn)}
                            aria-expanded={typeOpen}
                            aria-label={`Change type of ${txn.merchant}`}
                            title="Change type (spending, income or transfer)"
                            className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-md border px-2 py-1 text-xs transition-colors ${
                              typeOpen
                                ? 'border-ink/60 text-ink'
                                : 'border-edge/15 text-muted hover:border-edge/35 hover:text-ink'
                            }`}
                          >
                            <ArrowLeftRight className="h-3.5 w-3.5" aria-hidden="true" />
                            <span className="hidden sm:inline">Change type</span>
                          </button>
                        </td>
                      </tr>
                      {typeOpen && (
                        <tr className="bg-edge/[0.04]">
                          <td colSpan={COLS} className="px-3 pb-4 pt-1 sm:px-4">
                            <div className="ml-0 max-w-xl space-y-3 border-l-2 border-ink/70 pl-3 sm:ml-10 sm:pl-4">
                              <p className="text-sm text-ink">
                                What is <span className="font-medium">{txn.merchant}</span>{' '}
                                <span className="num">
                                  ({isMoneyIn(txn) ? '+' : ''}
                                  {formatCurrency(isMoneyIn(txn) ? Math.abs(txn.amount) : txn.amount)})
                                </span>
                                ?
                              </p>
                              <div className="flex flex-wrap items-end gap-2">
                                <div className="w-full sm:w-[280px]">
                                  <Select
                                    aria-label="New type"
                                    value={typeDraft}
                                    onChange={(e) => {
                                      setTypeDraft(e.target.value);
                                      setTypeError('');
                                    }}
                                    className="py-2"
                                  >
                                    {TYPE_CHOICES.map((g) => (
                                      <optgroup key={g.group} label={g.group}>
                                        {g.options.map((o) => (
                                          <option key={o.value} value={o.value}>
                                            {o.label}
                                          </option>
                                        ))}
                                      </optgroup>
                                    ))}
                                  </Select>
                                </div>
                                <Button
                                  size="sm"
                                  onClick={() => handleTypeSave(txn)}
                                  loading={typeSaving}
                                  disabled={typeSaving || typeDraft === typeValue(txn)}
                                >
                                  Save type
                                </Button>
                                <Button variant="ghost" size="sm" onClick={() => setTypeEditId(null)} disabled={typeSaving}>
                                  Cancel
                                </Button>
                              </div>
                              <p className="text-[13px] text-muted">
                                {typeDraft === typeValue(txn)
                                  ? 'Pick a different type. The amount never changes.'
                                  : `${typeChangeNote(parseTypeValue(typeDraft).kind)} The amount never changes.`}
                              </p>
                              {typeError && <Alert kind="error">{typeError}</Alert>}
                            </div>
                          </td>
                        </tr>
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
