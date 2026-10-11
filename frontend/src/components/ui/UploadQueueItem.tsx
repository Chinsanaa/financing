'use client';

import { Check, FileSpreadsheet, Loader2, TriangleAlert, X } from 'lucide-react';
import Badge from '@/components/ui/Badge';
import Stamp from '@/components/ui/Stamp';
import { ProgressBar } from '@/components/ui-feedback';
import type { TransactionKind, UploadResult } from '@/types/v5';

export type QueueStatus = 'pending' | 'uploading' | 'processing' | 'done' | 'duplicate' | 'error';

export interface QueuedFile {
  id: string;
  file: File;
  status: QueueStatus;
  detail?: string;
  rowsImported?: number;
  progress?: number;
  /** v5 upload result (API_V5.md §3.9) once the file has imported. */
  result?: UploadResult;
}

const STATUS_CONFIG: Record<QueueStatus, { tone: 'neutral' | 'accent' | 'success' | 'danger'; label: string }> = {
  pending: { tone: 'neutral', label: 'Queued' },
  uploading: { tone: 'neutral', label: 'Uploading' },
  processing: { tone: 'neutral', label: 'Processing' },
  done: { tone: 'success', label: 'Imported' },
  duplicate: { tone: 'neutral', label: 'Skipped' },
  error: { tone: 'danger', label: 'Failed' },
};

const KIND_WORDS: Record<TransactionKind, string> = {
  expense: 'spending',
  income: 'income',
  transfer: 'transfers',
};
const KIND_ORDER: TransactionKind[] = ['expense', 'income', 'transfer'];

const plural = (n: number, one: string, many = `${one}s`) => `${n.toLocaleString()} ${n === 1 ? one : many}`;

/** "41 transactions: 29 spending, 3 income, 9 transfers" (zero kinds omitted). */
export function describeRowsByKind(total: number, byKind?: Partial<Record<TransactionKind, number>> | null): string {
  const head = plural(total, 'transaction');
  if (!byKind) return head;
  const parts = KIND_ORDER.filter((k) => (byKind[k] ?? 0) > 0).map((k) => {
    const n = byKind[k] ?? 0;
    return `${n.toLocaleString()} ${k === 'transfer' && n === 1 ? 'transfer' : KIND_WORDS[k]}`;
  });
  return parts.length ? `${head}: ${parts.join(', ')}` : head;
}

/** The re-import sentence from the contract: "Updated 12 and removed 2 earlier transactions from this statement." */
export function describeReimport(r: Pick<UploadResult, 'rows_updated' | 'rows_removed'>): string {
  const updated = r.rows_updated ?? 0;
  const removed = r.rows_removed ?? 0;
  if (!updated && !removed) return 'Matched the transactions you had already imported from this statement; nothing needed changing.';
  const bits: string[] = [];
  if (updated) bits.push(`updated ${updated.toLocaleString()}`);
  if (removed) bits.push(`removed ${removed.toLocaleString()}`);
  const sentence = bits.join(' and ');
  const noun = updated + removed === 1 ? 'earlier transaction' : 'earlier transactions';
  return `${sentence.charAt(0).toUpperCase()}${sentence.slice(1)} ${noun} from this statement.`;
}

/** One row in the multi-file upload queue: filename, size, live status, and
 * a remove button. Rendered once per queued file — see UploadTab.tsx.
 *
 * `stamped`: this is the most recently finished import, so the "Imported"
 * seal replaces the badge (approved stamp site #1). UploadTab passes it to
 * exactly one row, so two stamps are never visible at once. */
export default function UploadQueueItem({
  item,
  onRemove,
  disabled,
  stamped = false,
}: {
  item: QueuedFile;
  onRemove: (id: string) => void;
  disabled: boolean;
  stamped?: boolean;
}) {
  const { tone, label } = STATUS_CONFIG[item.status];
  const removable = item.status !== 'uploading' && item.status !== 'processing';
  const r = item.status === 'done' ? item.result : undefined;
  const showStamp = stamped && item.status === 'done';

  return (
    <div className="flex items-start gap-3 border-b border-edge/12 py-3">
      <FileSpreadsheet className="mt-0.5 h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <div className="flex min-h-[20px] items-center gap-2">
          <p className="truncate text-sm font-medium">{item.file.name}</p>
          {showStamp ? (
            <span className="shrink-0">
              <Stamp label="Imported" size="sm" once={`upload-${item.id}`} />
            </span>
          ) : (
            <Badge tone={tone} className="shrink-0">
              {item.status === 'uploading' || item.status === 'processing' ? (
                <span className="flex items-center gap-1">
                  <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
                  {item.status === 'uploading' ? `${label} ${item.progress ?? 0}%` : label}
                </span>
              ) : item.status === 'duplicate' ? (
                <span className="flex items-center gap-1">
                  <Check className="h-3 w-3" aria-hidden="true" />
                  {label}
                </span>
              ) : item.status === 'error' ? (
                <span className="flex items-center gap-1">
                  <TriangleAlert className="h-3 w-3" aria-hidden="true" />
                  {label}
                </span>
              ) : (
                label
              )}
            </Badge>
          )}
        </div>

        {r ? (
          <div className="mt-1 space-y-0.5 text-xs leading-relaxed" title={r.message}>
            <p className="text-ink">{describeRowsByKind(r.rows_imported, r.rows_by_kind)}</p>
            {r.reimported && <p className="text-muted">{describeReimport(r)}</p>}
            {r.rows_skipped > 0 && (
              <p className="text-muted">{plural(r.rows_skipped, 'row')} already imported, skipped.</p>
            )}
          </div>
        ) : (
          <p className="mt-0.5 truncate text-xs text-muted" title={item.detail}>
            {item.detail || `${(item.file.size / 1024).toFixed(1)} KB`}
          </p>
        )}
        {item.status === 'uploading' && (
          <div className="mt-1.5">
            <ProgressBar percent={item.progress ?? 0} height="h-1" />
          </div>
        )}
      </div>
      <button
        type="button"
        onClick={() => onRemove(item.id)}
        disabled={disabled || !removable}
        aria-label={`Remove ${item.file.name}`}
        className="shrink-0 rounded-md p-1.5 text-muted transition-colors hover:bg-danger/10 hover:text-danger disabled:pointer-events-none disabled:opacity-30"
      >
        <X className="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  );
}
