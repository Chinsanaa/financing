'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { FileSpreadsheet, UploadCloud, X, Trash2 } from 'lucide-react';
import { api } from '@/utils/api';
import { useApi, invalidate } from '@/utils/useApi';
import { Alert } from '@/components/ui';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import { SkeletonRows } from '@/components/ui/Skeleton';
import EmptyState from '@/components/ui/EmptyState';

interface Upload {
  id: string;
  original_filename: string;
  file_type: string;
  created_at: string;
  row_count: number;
  status: string;
}

export default function UploadTab() {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [deleting, setDeleting] = useState<string | null>(null);

  // Fetch upload history
  const { data: uploadsData, loading: uploadsLoading, setData: setUploadsData } = useApi<{ uploads: Upload[] }>('/uploads/');

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      setFile(droppedFile);
      setError('');
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError('');
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    setUploading(true);
    setError('');
    setMessage('');

    try {
      const response = await api.uploads.upload(file);
      setMessage(`Uploaded ${file.name}: ${response.data.message}`);
      setFile(null);
      // New transactions exist — every dashboard view is now stale.
      invalidate('/dashboard');
      invalidate('/uploads/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (uploadId: string) => {
    if (!confirm('Delete this upload and all its transactions? This cannot be undone.')) {
      return;
    }

    setDeleting(uploadId);
    try {
      await api.uploads.delete(uploadId);
      // Remove from local list
      setUploadsData((prev) =>
        prev
          ? {
              uploads: prev.uploads.filter((u) => u.id !== uploadId),
            }
          : prev
      );
      // Refresh dashboard since transactions were deleted
      invalidate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete upload');
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="max-w-2xl space-y-6">
      <SectionHeader label="Transactions" title="Upload a statement" />
      <p className="-mt-4 text-sm text-muted">
        CSV or Excel exports from Alipay or WeChat. Both formats are detected automatically.
      </p>

      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`rounded-card border-2 border-dashed p-12 text-center transition-all duration-200 ${
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
            <p className="font-medium">Drag and drop your file here</p>
            <p className="mt-1 text-sm text-muted">or choose one from your computer</p>
          </div>
          <input
            type="file"
            accept=".csv,.xlsx"
            onChange={handleFileSelect}
            className="hidden"
            id="file-input"
          />
          <Button
            type="button"
            variant="outline"
            onClick={() => document.getElementById('file-input')?.click()}
          >
            Choose file
          </Button>
        </div>
      </div>

      {file && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent/12 text-accent-strong">
                  <FileSpreadsheet className="h-5 w-5" />
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{file.name}</p>
                  <p className="text-xs text-muted">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
              </div>
              <button
                onClick={() => setFile(null)}
                aria-label="Remove file"
                className="rounded-pill p-1.5 text-muted transition-colors hover:text-danger hover:bg-danger/10"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <Button onClick={handleUpload} loading={uploading} className="mt-4 w-full">
              {uploading ? 'Uploading' : 'Upload'}
            </Button>
          </Card>
        </motion.div>
      )}

      {message && <Alert kind="success">{message}</Alert>}
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
                        {new Date(upload.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          className={`inline-block rounded-full px-2.5 py-1 text-xs font-medium ${
                            upload.status === 'parsed'
                              ? 'bg-success/15 text-success'
                              : upload.status === 'failed'
                                ? 'bg-danger/15 text-danger'
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
