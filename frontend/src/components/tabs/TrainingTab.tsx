'use client';

import { useEffect, useRef, useState } from 'react';
import { api } from '@/utils/api';
import { useApi, invalidate } from '@/utils/useApi';
import { Alert, Loading } from '@/components/ui';

// Mirrors the model_runs table columns
interface TrainingRun {
  id: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed' | string;
  cv_accuracy?: number | null;
  f1_macro?: number | null;
  n_labeled_samples?: number | null;
  error_message?: string | null;
  created_at: string;
  finished_at?: string | null;
}

export default function TrainingTab() {
  const { data, setData, loading, error: loadError, reload } = useApi<{ training_runs: TrainingRun[] }>('/training/');
  const [training, setTraining] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const runs = data?.training_runs || [];

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  // Clear any live interval when the tab unmounts — the old implementation
  // leaked the interval on tab switches and could stack several of them.
  useEffect(() => stopPolling, []);

  const handleRetrain = async () => {
    try {
      setError('');
      setMessage('');
      setTraining(true);
      const res = await api.training.retrain();
      const modelRunId: string = res.data.model_run_id;
      setMessage('Training started! Results appear below when it finishes.');
      await reload(true);

      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          const statusRes = await api.training.getStatus(modelRunId);
          const run: TrainingRun = statusRes.data;
          setData((prev) =>
            prev
              ? {
                  ...prev,
                  training_runs: prev.training_runs.map((r) => (r.id === run.id ? run : r)),
                }
              : prev
          );

          if (run.status === 'succeeded' || run.status === 'failed') {
            stopPolling();
            setTraining(false);
            invalidate('/dashboard'); // fresh model reclassified transactions
            if (run.status === 'succeeded') {
              setMessage('Training finished — your transactions have been re-classified.');
            }
          }
        } catch {
          // transient polling error, keep trying
        }
      }, 5000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start training');
      setTraining(false);
    }
  };

  if (loading) {
    return <Loading label="Loading training history..." />;
  }

  const statusStyle = (status: string) =>
    status === 'succeeded'
      ? 'bg-green-100 text-green-800'
      : status === 'failed'
      ? 'bg-red-100 text-red-800'
      : 'bg-yellow-100 text-yellow-800';

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Model Training</h2>
        <p className="text-gray-600">Train a custom classification model with your labeled data</p>
      </div>

      {(error || loadError) && <Alert kind="error">{error || loadError}</Alert>}
      {message && <Alert kind="success">{message}</Alert>}

      <button
        onClick={handleRetrain}
        disabled={training}
        className="bg-blue-600 text-white font-medium py-3 px-6 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
      >
        {training ? 'Training in progress...' : 'Start Training'}
      </button>

      {/* Training History */}
      <div className="space-y-3">
        <h3 className="font-bold text-gray-900">Training History</h3>

        {runs.length === 0 ? (
          <p className="text-gray-600">No training runs yet</p>
        ) : (
          runs.map((run) => (
            <div
              key={run.id}
              className="bg-white rounded-lg border border-gray-200 p-4 space-y-2"
            >
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-medium text-gray-900">
                    Run {run.id.slice(0, 8)}...
                  </p>
                  <p className="text-xs text-gray-500">
                    {new Date(run.created_at).toLocaleString()}
                  </p>
                </div>
                <span className={`px-2 py-1 rounded text-xs font-medium ${statusStyle(run.status)}`}>
                  {run.status}
                </span>
              </div>

              {run.cv_accuracy != null && (
                <div className="grid grid-cols-3 gap-2 text-sm">
                  <div>
                    <p className="text-gray-600">CV Accuracy</p>
                    <p className="font-medium text-gray-900">
                      {(run.cv_accuracy * 100).toFixed(1)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-600">F1-Macro</p>
                    <p className="font-medium text-gray-900">
                      {run.f1_macro != null ? run.f1_macro.toFixed(3) : '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-600">Samples</p>
                    <p className="font-medium text-gray-900">
                      {run.n_labeled_samples ?? '—'}
                    </p>
                  </div>
                </div>
              )}

              {run.error_message && (
                <p className="text-xs text-red-600">{run.error_message}</p>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
