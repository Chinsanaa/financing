'use client';

import { useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { FileSpreadsheet, UploadCloud, Trash2, PenLine } from 'lucide-react';
import { api } from '@/utils/api';
import { useApi, invalidate } from '@/utils/useApi';
import { formatDate } from '@/utils/format';
import { Alert } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import { SkeletonRows } from '@/components/ui/Skeleton';
import EmptyState from '@/components/ui/EmptyState';
import UploadQueueItem, { QueuedFile, QueueStatus } from '@/components/ui/UploadQueueItem';
import Input, { Select } from '@/components/ui/Input';

interface Upload {
  id: string;
  original_filename: string;
  file_type: string;
  created_at: string;
  row_count: number;
  status: string;
  error_message?: string | null;
}

const MAX_QUEUE = 10;
const MAX_SIZE = 10 * 1024 * 1024; // mirrors backend/routes/uploads.py MAX_SIZE

function makeId(): string {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function fileKey(f: File): string {
  return `${f.name}|${f.size}|${f.lastModified}`;
}

function isSupportedFile(f: File): boolean {
  const name = f.name.toLowerCase();
  return name.endsWith('.csv') || name.endsWith('.xlsx');
}

function buildSummary(queue: QueuedFile[]): { kind: 'success' | 'info' | 'error'; text: string } | null {
  const attempted = queue.filter((i) => i.status !== 'pending');
  if (!attempted.length) return null;

  const done = attempted.filter((i) => i.status === 'done');
  const duplicates = attempted.filter((i) => i.status === 'duplicate');
  const failed = attempted.filter((i) => i.status === 'error');
  const rowsImported = done.reduce((sum, i) => sum + (i.rowsImported ?? 0), 0);

  const parts: string[] = [];
  if (done.length) {
    parts.push(
      `${done.length} of ${attempted.length} file${attempted.length !== 1 ? 's' : ''} imported` +
        (rowsImported ? ` (${rowsImported} transactions)` : '')
    );
  }
  if (duplicates.length) parts.push(`${duplicates.length} skipped as already uploaded`);
  if (failed.length) parts.push(`${failed.length} failed`);

  const kind = failed.length && !done.length ? 'error' : done.length ? 'success' : 'info';
  return { kind, text: parts.join('. ') + '.' };
}

export default function UploadTab() {
  const [dragActive, setDragActive] = useState(false);
  const [queue, setQueue] = useState<QueuedFile[]>([]);
  const [running, setRunning] = useState(false);
  const [batchProgress, setBatchProgress] = useState<{ current: number; total: number } | null>(null);
  const [summary, setSummary] = useState<{ kind: 'success' | 'info' | 'error'; text: string } | null>(null);
  const [queueError, setQueueError] = useState('');
  const [error, setError] = useState(''); // delete-path errors only
  const [deleting, setDeleting] = useState<string | null>(null);

  const [showManualForm, setShowManualForm] = useState(false);
  const [manualDate, setManualDate] = useState('');
  const [manualMerchant, setManualMerchant] = useState('');
  const [manualDescription, setManualDescription] = useState('');
  const [manualAmount, setManualAmount] = useState('');
  const [manualCategoryId, setManualCategoryId] = useState('');
  const [manualError, setManualError] = useState('');
  const [manualSuccess, setManualSuccess] = useState('');
  const [manualSubmitting, setManualSubmitting] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const stopRef = useRef(false);

  // Fetch upload history
  const { data: uploadsData, loading: uploadsLoading, setData: setUploadsData, reload } = useApi<{ uploads: Upload[] }>('/uploads/');
  const { data: categoriesData } = useApi<{ categories: { id: string; name: string }[] }>('/categories/');
  const categories = categoriesData?.categories || [];

  const resetManualForm = () => {
    setManualDate('');
    setManualMerchant('');
    setManualDescription('');
    setManualAmount('');
    setManualCategoryId('');
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setManualSuccess('');

    const merchant = manualMerchant.trim();
    const description = manualDescription.trim();
    const amount = Number(manualAmount);

    if (!manualDate || !merchant || !description || !manualAmount || !manualCategoryId) {
      setManualError('All fields are required.');
      return;
    }
    if (!Number.isFinite(amount) || amount <= 0) {
      setManualError('Amount must be a number greater than 0.');
      return;
    }

    setManualError('');
    setManualSubmitting(true);
    try {
      await api.transactions.create({
        timestamp: new Date(`${manualDate}T00:00:00`).toISOString(),
        merchant,
        description,
        amount,
        category_id: manualCategoryId,
      });
      setManualSuccess('Expense added.');
      resetManualForm();
      setShowManualForm(false);
      invalidate('/dashboard');
    } catch (err: any) {
      setManualError(err.response?.data?.detail || 'Failed to add expense');
    } finally {
      setManualSubmitting(false);
    }
  };

  const patch = (id: string, partial: Partial<QueuedFile>) => {
    setQueue((prev) => prev.map((i) => (i.id === id ? { ...i, ...partial } : i)));
  };

  const addFiles = (incoming: File[]) => {
    if (!incoming.length) return;
    setQueue((prevQueue) => {
      const existingKeys = new Set(prevQueue.map((i) => fileKey(i.file)));
      const rejections: string[] = [];
      const accepted: QueuedFile[] = [];
      let slotsLeft = MAX_QUEUE - prevQueue.length;

      for (const f of incoming) {
        if (!isSupportedFile(f)) {
          rejections.push(`${f.name} (only CSV or Excel)`);
          continue;
        }
        if (f.size > MAX_SIZE) {
          rejections.push(`${f.name} (over 10MB)`);
          continue;
        }
        const key = fileKey(f);
        if (existingKeys.has(key)) {
          rejections.push(`${f.name} (already in the list)`);
          continue;
        }
        if (slotsLeft <= 0) {
          rejections.push(`${f.name} (queue is full — max ${MAX_QUEUE})`);
          continue;
        }
        existingKeys.add(key);
        slotsLeft -= 1;
        accepted.push({ id: makeId(), file: f, status: 'pending' as QueueStatus });
      }

      if (rejections.length) {
        setQueueError(`${rejections.length} file${rejections.length !== 1 ? 's' : ''} not added: ${rejections.join(', ')}`);
      } else {
        setQueueError('');
      }
      return [...prevQueue, ...accepted];
    });
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    if (running) return;
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (running) return;
    addFiles(Array.from(e.dataTransfer.files ?? []));
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    addFiles(Array.from(e.target.files ?? []));
    e.target.value = ''; // allow re-picking the same file later
  };

  const removeFromQueue = (id: string) => {
    setQueue((prev) => prev.filter((i) => i.id !== id));
  };

  const clearFinished = () => {
    setQueue((prev) => prev.filter((i) => i.status === 'pending' || i.status === 'uploading' || i.status === 'processing'));
    setSummary(null);
  };

  const runQueue = async () => {
    const batch = queue.filter((i) => i.status === 'pending' || i.status === 'error');
    if (!batch.length) return;

    setRunning(true);
    setSummary(null);
    setQueueError('');
    stopRef.current = false;

    // React state updates from `patch` are async, so the summary at the end
    // can't be read back from the `queue` closure (it would still show
    // everything as 'pending'). Track outcomes locally as the loop runs.
    const outcomes: QueuedFile[] = batch.map((i) => ({ ...i }));

    for (let idx = 0; idx < batch.length; idx++) {
      const item = batch[idx];
      if (stopRef.current) break;
      setBatchProgress({ current: idx + 1, total: batch.length });
      patch(item.id, { status: 'uploading', progress: 0, detail: undefined });

      try {
        const res = await api.uploads.upload(item.file, {
          onUploadProgress: (evt: any) => {
            const pct = evt.total ? Math.round((evt.loaded / evt.total) * 100) : 0;
            if (pct >= 100) {
              patch(item.id, { status: 'processing', progress: 100 });
            } else {
              patch(item.id, { status: 'uploading', progress: pct });
            }
          },
        });
        const done: Partial<QueuedFile> = {
          status: 'done',
          progress: 100,
          rowsImported: res.data.rows_imported,
          detail: res.data.message,
        };
        patch(item.id, done);
        outcomes[idx] = { ...outcomes[idx], ...done };
      } catch (err: any) {
        const status = err?.response?.status;
        const failure: Partial<QueuedFile> =
          status === 409
            ? { status: 'duplicate', detail: err.response?.data?.detail || 'Already uploaded' }
            : !err?.response
              ? { status: 'error', detail: 'Network error — check your connection' }
              : { status: 'error', detail: err.response?.data?.detail || 'Upload failed' };
        patch(item.id, failure);
        outcomes[idx] = { ...outcomes[idx], ...failure };
      }

      // Refresh history after each file so rows appear as the queue drains;
      // background=true keeps the table from flashing its loading skeleton.
      invalidate('/uploads/');
      await reload(true);
    }

    setRunning(false);
    setBatchProgress(null);
    invalidate('/dashboard');
    setSummary(buildSummary(outcomes));
  };

  const handleDelete = async (uploadId: string) => {
    if (!confirm('Delete this upload and all its transactions? Any manually labeled transactions will also be removed. This cannot be undone.')) {
      return;
    }

    setDeleting(uploadId);
    try {
      await api.uploads.delete(uploadId);
      setUploadsData((prev) =>
        prev
          ? {
              uploads: prev.uploads.filter((u) => u.id !== uploadId),
            }
          : prev
      );
      invalidate('/dashboard');
      await reload();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete upload');
    } finally {
      setDeleting(null);
    }
  };

  const pendingCount = queue.filter((i) => i.status === 'pending' || i.status === 'error').length;
  const hasFinished = queue.some((i) => i.status === 'done' || i.status === 'duplicate' || i.status === 'error');

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6">
      <SectionHeader label="Transactions" title="Upload statements" />
      <p className="-mt-4 text-sm text-muted">
        CSV or Excel exports from Alipay or WeChat — up to {MAX_QUEUE} files at a time. Both formats are
        detected automatically, and each file uploads one after another.
      </p>

      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        data-tour-id="upload-choose-files"
        className={`rounded-card border-2 border-dashed p-12 text-center transition-all duration-200 ${
          running ? 'pointer-events-none opacity-60' : ''
        } ${
          dragActive
            ? 'border-accent bg-accent/5 shadow-glow'
            : 'border-edge/15 bg-surface hover:border-edge/30'
        }`}
      >
        <div className="space-y-4">
          <motion.div
            animate={dragActive ? { scale: 1.1, y: -4 } : { scale: 1, y: 0 }}
            className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-accent/12 text-accent-strong"
          >
            <UploadCloud className="h-7 w-7" />
          </motion.div>
          <div>
            <p className="font-medium">Drag and drop your files here</p>
            <p className="mt-1 text-sm text-muted">or choose them from your computer</p>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,.xlsx"
            multiple
            onChange={handleFileSelect}
            className="hidden"
          />
          <Button type="button" variant="outline" disabled={running} onClick={() => inputRef.current?.click()}>
            Choose files
          </Button>
        </div>
      </div>

      <div className="text-center">
        <Button
          type="button"
          variant="ghost"
          onClick={() => {
            setShowManualForm((prev) => !prev);
            setManualError('');
            setManualSuccess('');
          }}
        >
          <PenLine className="h-4 w-4" />
          Add expense manually
        </Button>
      </div>

      {showManualForm && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="space-y-4 p-6">
            <SectionHeader label="Manual entry" title="Add an expense" />
            <form onSubmit={handleManualSubmit} className="space-y-4">
              <Input
                label="Date"
                type="date"
                required
                value={manualDate}
                onChange={(e) => setManualDate(e.target.value)}
              />
              <Input
                label="Merchant"
                type="text"
                required
                placeholder="e.g. Starbucks"
                value={manualMerchant}
                onChange={(e) => setManualMerchant(e.target.value)}
              />
              <Input
                label="Description"
                type="text"
                required
                placeholder="e.g. Coffee with a friend"
                value={manualDescription}
                onChange={(e) => setManualDescription(e.target.value)}
              />
              <Input
                label="Amount"
                type="number"
                step="0.01"
                min="0.01"
                required
                placeholder="0.00"
                value={manualAmount}
                onChange={(e) => setManualAmount(e.target.value)}
              />
              <Select
                label="Category"
                required
                value={manualCategoryId}
                onChange={(e) => setManualCategoryId(e.target.value)}
              >
                <option value="" disabled>
                  Select a category
                </option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </Select>

              {manualError && <Alert kind="error">{manualError}</Alert>}
              {manualSuccess && <Alert kind="success">{manualSuccess}</Alert>}

              <div className="flex items-center gap-2">
                <Button type="submit" loading={manualSubmitting} className="flex-1">
                  Add expense
                </Button>
                <Button type="button" variant="ghost" onClick={() => setShowManualForm(false)}>
                  Cancel
                </Button>
              </div>
            </form>
          </Card>
        </motion.div>
      )}

      {queue.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
          <div className="space-y-2">
            {queue.map((item) => (
              <UploadQueueItem key={item.id} item={item} onRemove={removeFromQueue} disabled={running} />
            ))}
          </div>

          <div className="flex items-center gap-2">
            {running ? (
              <>
                <Button variant="outline" onClick={() => (stopRef.current = true)} className="flex-1">
                  Stop after this file
                </Button>
                {batchProgress && (
                  <span className="text-xs text-muted">
                    Uploading {batchProgress.current} of {batchProgress.total}
                  </span>
                )}
              </>
            ) : (
              <>
                {pendingCount > 0 && (
                  <Button onClick={runQueue} className="flex-1">
                    Upload {pendingCount} file{pendingCount !== 1 ? 's' : ''}
                  </Button>
                )}
                {hasFinished && (
                  <Button variant="ghost" onClick={clearFinished}>
                    Clear finished
                  </Button>
                )}
              </>
            )}
          </div>
        </motion.div>
      )}

      {queueError && <Alert kind="error">{queueError}</Alert>}
      {summary && <Alert kind={summary.kind}>{summary.text}</Alert>}
      {error && <Alert kind="error">{error}</Alert>}

      {/* Upload History */}
      <div className="mt-10 border-t pt-8">
        <SectionHeader label="History" title="Recent uploads" />
        <p className="-mt-4 mb-4 text-sm text-muted">
          Manage your uploaded files and their transactions.
        </p>

        {uploadsLoading ? (
          <SkeletonRows rows={3} />
        ) : uploadsData?.uploads && uploadsData.uploads.length > 0 ? (
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-edge/8 bg-surface-2/60">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-muted">File</th>
                    <th className="px-4 py-3 text-left font-medium text-muted">Type</th>
                    <th className="px-4 py-3 text-right font-medium text-muted">Transactions</th>
                    <th className="px-4 py-3 text-left font-medium text-muted">Date</th>
                    <th className="px-4 py-3 text-center font-medium text-muted">Status</th>
                    <th className="px-4 py-3 text-center font-medium text-muted">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-edge/8">
                  {uploadsData.uploads.map((upload) => (
                    <tr key={upload.id} className="transition-colors hover:bg-edge/5">
                      <td className="px-4 py-3 font-medium">{upload.original_filename}</td>
                      <td className="px-4 py-3 text-xs text-muted capitalize">{upload.file_type}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{upload.row_count}</td>
                      <td className="px-4 py-3 text-xs text-muted">
                        {formatDate(upload.created_at)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          title={upload.status === 'failed' ? upload.error_message || undefined : undefined}
                          className={`inline-block rounded-full px-2.5 py-1 text-xs font-medium ${
                            upload.status === 'parsed'
                              ? 'bg-success/15 text-success'
                              : upload.status === 'failed'
                                ? 'bg-danger/15 text-danger cursor-help'
                                : 'bg-accent/15 text-accent-strong'
                          }`}
                        >
                          {upload.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={() => handleDelete(upload.id)}
                          disabled={deleting === upload.id}
                          aria-label="Delete upload"
                          className="rounded-lg p-2 text-muted transition-colors hover:text-danger hover:bg-danger/10 disabled:opacity-50"
                          title="Delete upload and all its transactions"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        ) : (
          <EmptyState
            icon={FileSpreadsheet}
            title="No uploads yet"
            description="Upload a statement to get started."
          />
        )}
      </div>
    </div>
  );
}
