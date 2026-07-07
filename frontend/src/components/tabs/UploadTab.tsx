'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { FileSpreadsheet, UploadCloud, X } from 'lucide-react';
import { api } from '@/utils/api';
import { invalidate } from '@/utils/useApi';
import { Alert } from '@/components/ui';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';

export default function UploadTab() {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

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
      invalidate('/uploads');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
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
    </div>
  );
}
