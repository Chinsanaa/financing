'use client';

import { Check, FileSpreadsheet, Loader2, TriangleAlert, X } from 'lucide-react';
import Badge from '@/components/ui/Badge';
import { ProgressBar } from '@/components/ui-feedback';

export type QueueStatus = 'pending' | 'uploading' | 'processing' | 'done' | 'duplicate' | 'error';

export interface QueuedFile {
  id: string;
  file: File;
  status: QueueStatus;
  detail?: string;
  rowsImported?: number;
  progress?: number;
}

const STATUS_CONFIG: Record<QueueStatus, { tone: 'neutral' | 'accent' | 'success' | 'danger'; label: string }> = {
  pending: { tone: 'neutral', label: 'Queued' },
  uploading: { tone: 'neutral', label: 'Uploading' },
  processing: { tone: 'neutral', label: 'Processing' },
  done: { tone: 'success', label: 'Imported' },
  duplicate: { tone: 'neutral', label: 'Skipped' },
  error: { tone: 'danger', label: 'Failed' },
};

/** One row in the multi-file upload queue: filename, size, live status, and
 * a remove button. Rendered once per queued file — see UploadTab.tsx. */
export default function UploadQueueItem({
  item,
  onRemove,
  disabled,
}: {
  item: QueuedFile;
  onRemove: (id: string) => void;
  disabled: boolean;
}) {
  const { tone, label } = STATUS_CONFIG[item.status];
  const removable = item.status !== 'uploading' && item.status !== 'processing';

  return (
    <div className="flex items-center gap-3 border-b border-edge/12 py-3">
      <FileSpreadsheet className="h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate text-sm font-medium">{item.file.name}</p>
          <Badge tone={tone} className="shrink-0">
            {item.status === 'uploading' || item.status === 'processing' ? (
              <span className="flex items-center gap-1">
                <Loader2 className="h-3 w-3 animate-spin" />
                {item.status === 'uploading' ? `${label} ${item.progress ?? 0}%` : label}
              </span>
            ) : item.status === 'duplicate' ? (
              <span className="flex items-center gap-1">
                <Check className="h-3 w-3" />
                {label}
              </span>
            ) : item.status === 'error' ? (
              <span className="flex items-center gap-1">
                <TriangleAlert className="h-3 w-3" />
                {label}
              </span>
            ) : (
              label
            )}
          </Badge>
        </div>
        <p className="mt-0.5 truncate text-xs text-muted" title={item.detail}>
          {item.detail || `${(item.file.size / 1024).toFixed(1)} KB`}
        </p>
        {item.status === 'uploading' && (
          <div className="mt-1.5">
            <ProgressBar percent={item.progress ?? 0} height="h-1" />
          </div>
        )}
      </div>
      <button
        onClick={() => onRemove(item.id)}
        disabled={disabled || !removable}
        aria-label="Remove file"
        className="shrink-0 rounded-md p-1.5 text-muted transition-colors hover:text-danger hover:bg-danger/10 disabled:opacity-30 disabled:pointer-events-none"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
