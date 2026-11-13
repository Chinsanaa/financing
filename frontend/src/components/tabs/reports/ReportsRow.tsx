'use client';

import { ArrowLeftRight, Check } from 'lucide-react';
import Badge from '@/components/ui/Badge';
import { formatDate } from '@/utils/format';
import AmountCell from './AmountCell';
import { BUCKET_TONE, LABEL_SOURCES, NON_EXPENSE_HINT, isMoneyIn, typeLabel } from './reportsHelpers';
import type { Transaction } from './reportsHelpers';
import type { Category } from '@/types/v5';

export default function ReportsRow({
  txn,
  currencyHome,
  selected,
  typeOpen,
  isEditing,
  isSaving,
  categories,
  toneFor,
  onToggleSelected,
  onOpenTypeEditor,
  onOpenSplit,
  onStartEdit,
  onStopEdit,
  onCategoryChange,
}: {
  txn: Transaction;
  currencyHome: string | null;
  selected: boolean;
  typeOpen: boolean;
  isEditing: boolean;
  isSaving: boolean;
  categories: Category[];
  toneFor: (name: string) => string;
  onToggleSelected: (id: string) => void;
  onOpenTypeEditor: (txn: Transaction) => void;
  onOpenSplit: () => void;
  onStartEdit: () => void;
  onStopEdit: () => void;
  onCategoryChange: (txn: Transaction, newCategoryId: string) => void;
}) {
    const isExpense = txn.kind === 'expense';
    const label = typeLabel(txn);
      const categoryCell = !isExpense ? (
      <span className="text-muted" title={NON_EXPENSE_HINT}>
        <span aria-hidden="true">—</span>
        <span className="sr-only">No category (only spending has categories)</span>
      </span>
    ) : txn.is_split ? (
      <button
        type="button"
        onClick={onOpenSplit}
        title="Click to edit split"
        className="group inline-flex items-center gap-1"
      >
        <Badge tone="neutral">Split ({txn.splits?.length ?? 0})</Badge>
      </button>
    ) : isEditing ? (
      <select
        autoFocus
        defaultValue={txn.category_id ?? ''}
        onChange={(e) => onCategoryChange(txn, e.target.value)}
        onBlur={onStopEdit}
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
          onClick={onStartEdit}
          disabled={isSaving}
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
          {isSaving && <Check className="h-3 w-3 animate-pulse text-muted" />}
        </button>
        <button
          type="button"
          onClick={onOpenSplit}
          title="Split across categories"
          className="text-xs text-muted underline decoration-dotted hover:text-ink"
        >
          Split
        </button>
      </div>
    );

  return (
    <tr
      className={`transition-colors hover:bg-edge/5 ${selected ? 'bg-edge/[0.06]' : ''} ${typeOpen ? 'bg-edge/[0.04]' : ''}`}
    >
      <td className="py-3 pl-3 pr-1 align-top sm:px-4 sm:align-middle">
        <span title={isExpense ? undefined : NON_EXPENSE_HINT} className="inline-flex">
          <input
            type="checkbox"
            checked={selected}
            disabled={!isExpense}
            onChange={() => onToggleSelected(txn.id)}
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
              className={`max-w-full truncate whitespace-nowrap rounded-[4px] border px-1.5 py-px leading-4 ${
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
          onClick={() => onOpenTypeEditor(txn)}
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
  );
}
