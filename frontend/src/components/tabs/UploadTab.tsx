'use client';

import { useState } from 'react';
import { api } from '@/utils/api';

export default function UploadTab({ token }: { token: string }) {
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
      const response = await api.uploads.upload(token, file);
      setMessage(`Uploaded ${file.name}: ${response.data.message}`);
      setFile(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Upload Transactions</h2>
        <p className="text-gray-600">Upload CSV or Excel files from Alipay or WeChat</p>
      </div>

      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-12 text-center transition ${
          dragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 bg-gray-50 hover:border-gray-400'
        }`}
      >
        <div className="space-y-4">
          <div className="text-4xl">📄</div>
          <div>
            <p className="font-medium text-gray-900 mb-1">Drag and drop your file here</p>
            <p className="text-sm text-gray-600">or click to browse</p>
          </div>
          <input
            type="file"
            accept=".csv,.xlsx"
            onChange={handleFileSelect}
            className="hidden"
            id="file-input"
          />
          <label htmlFor="file-input" className="cursor-pointer">
            <button
              type="button"
              onClick={() => document.getElementById('file-input')?.click()}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition"
            >
              Choose File
            </button>
          </label>
        </div>
      </div>

      {file && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="font-medium text-gray-900 mb-3">Selected File:</p>
          <div className="flex justify-between items-center">
            <p className="text-gray-700">{file.name}</p>
            <button
              onClick={() => setFile(null)}
              className="text-red-600 hover:text-red-700 text-sm"
            >
              Remove
            </button>
          </div>
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="w-full mt-4 bg-blue-600 text-white font-medium py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      )}

      {message && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
          {message}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}
    </div>
  );
}
