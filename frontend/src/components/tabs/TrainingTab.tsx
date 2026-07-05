'use client';

import { useEffect, useState } from 'react';
import { api } from '@/utils/api';

interface TrainingRun {
  id: string;
  status: string;
  metrics?: any;
  created_at: string;
  completed_at?: string;
  error?: string;
}

export default function TrainingTab({ token }: { token: string }) {
  const [runs, setRuns] = useState<TrainingRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadTrainingRuns();
  }, [token]);

  const loadTrainingRuns = async () => {
    try {
      setLoading(true);
      const res = await api.training.list(token);
      setRuns(res.data.training_runs || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load training runs');
    } finally {
      setLoading(false);
    }
  };

  const handleRetrain = async () => {
    try {
      setError('');
      setMessage('');
      setTraining(true);
      const res = await api.training.retrain(token);
      setMessage('Training started! Check back soon for results.');
      setRuns([res.data, ...runs]);

      // Poll for status updates
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await api.training.getStatus(token, res.data.model_run_id);
          setRuns((prev) =>
            prev.map((r) => (r.id === statusRes.data.id ? statusRes.data : r))
          );

          if (statusRes.data.status === 'complete' || statusRes.data.status === 'failed') {
            clearInterval(pollInterval);
            setTraining(false);
          }
        } catch (err) {
          // Polling error, just continue
        }
      }, 5000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start training');
      setTraining(false);
    }
  };

  if (loading) {
    return <div className="text-gray-600">Loading training history...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Model Training</h2>
        <p className="text-gray-600">Train a custom classification model with your labeled data</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {message && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
          {message}
        </div>
      )}

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
                <span
                  className={`px-2 py-1 rounded text-xs font-medium ${
                    run.status === 'complete'
                      ? 'bg-green-100 text-green-800'
                      : run.status === 'failed'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}
                >
                  {run.status}
                </span>
              </div>

              {run.metrics && (
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <p className="text-gray-600">Accuracy</p>
                    <p className="font-medium text-gray-900">
                      {(run.metrics.accuracy * 100).toFixed(1)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-600">F1-Macro</p>
                    <p className="font-medium text-gray-900">
                      {run.metrics.f1_macro.toFixed(3)}
                    </p>
                  </div>
                </div>
              )}

              {run.error && (
                <p className="text-xs text-red-600">{run.error}</p>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
