'use client';

import { useEffect, useRef, useState } from 'react';
import { BrainCircuit, Play } from 'lucide-react';
import { toast } from 'sonner';
import { celebrate } from '@/utils/celebrate';
import RollingNumber from '@/components/ui/RollingNumber';
import { api } from '@/utils/api';
import { useApi, invalidate } from '@/utils/useApi';
import { advanceTour } from '@/utils/tour';
import { formatDateTime } from '@/utils/format';
import { Alert } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import EmptyState from '@/components/ui/EmptyState';
import { SkeletonRows } from '@/components/ui/Skeleton';

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
      invalidate('/training');
      advanceTour('train'); // last tour step — the tour ends here

      stopPolling();
      // Without an id the poll would hit /training/undefined every 5s (seen
      // in production); the run list above still refreshes on reload.
      if (!modelRunId) {
        setTraining(false);
        return;
      }
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
              // A real milestone: celebrate it (no-op under reduced motion).
              celebrate();
              toast.success('Your model is trained', {
                description:
                  run.cv_accuracy != null
                    ? `Cross-validated accuracy ${(run.cv_accuracy * 100).toFixed(1)}%.`
                    : 'Transactions have been re-classified.',
              });
            } else {
              toast.error('Training failed', { description: run.error_message || 'See the run details below.' });
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

  const statusTone = (status: string) =>
    status === 'succeeded' ? 'success' : status === 'failed' ? 'danger' : 'accent';

  return (
    <div className="w-full space-y-6">
      <SectionHeader label="Model" title="Training" />
      <p className="-mt-4 text-sm text-muted">
        Trains a fresh classifier on your labeled transactions, then re-classifies everything else.
      </p>

      {(error || loadError) && <Alert kind="error">{error || loadError}</Alert>}
      {message && <Alert kind="success">{message}</Alert>}

      {/* Launch panel: while a run is live the brain "thinks" (pulsing rings) */}
      <Card className="relative flex flex-col items-center gap-5 overflow-hidden p-8 text-center sm:flex-row sm:text-left">
        <div className="relative flex h-16 w-16 shrink-0 items-center justify-center">
          {training && (
            <>
              <span className="absolute inset-0 rounded-2xl bg-accent/25 animate-ping-soft" />
              <span className="absolute inset-0 rounded-2xl bg-accent/15 animate-ping-soft [animation-delay:1.2s]" />
            </>
          )}
          <span
            className={`relative flex h-16 w-16 items-center justify-center rounded-2xl border border-accent/25 bg-accent/10 text-accent-strong ${
              training ? 'animate-pulse' : ''
            }`}
          >
            <BrainCircuit className="h-8 w-8" />
          </span>
        </div>
        <div className="flex-1">
          <p className="font-display text-lg font-semibold">
            {training ? 'Learning your spending patterns…' : 'Ready when you are'}
          </p>
          <p className="mt-1 text-sm text-muted">
            {training
              ? 'This usually takes under a minute. You can leave this page — it keeps running.'
              : 'The more transactions you label, the smarter it gets.'}
          </p>
        </div>
        <Button onClick={handleRetrain} loading={training} size="lg" data-tour-id="train-start">
          {!training && <Play className="h-4 w-4" />}
          {training ? 'Training' : 'Start training'}
        </Button>
      </Card>

      <div className="space-y-3">
        <p className="section-label">Training history</p>

        {loading ? (
          <SkeletonRows rows={4} />
        ) : runs.length === 0 ? (
          <EmptyState
            icon={BrainCircuit}
            title="No training runs yet"
            description="Label some transactions first, then start your first training run."
          />
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {runs.map((run, i) => (
            <Card key={run.id} hover={i === 0} className="space-y-3 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">Run {run.id.slice(0, 8)}</p>
                  <p className="text-xs text-muted">
                    {formatDateTime(run.created_at)}
                  </p>
                </div>
                <Badge tone={statusTone(run.status)}>
                  {(run.status === 'queued' || run.status === 'running') && (
                    <span className="mr-1.5 inline-block h-1.5 w-1.5 animate-glow-pulse rounded-full bg-current" />
                  )}
                  {run.status}
                </Badge>
              </div>

              {run.cv_accuracy != null && (
                <div className="grid grid-cols-3 gap-2 rounded-lg bg-surface-2 p-3 text-sm">
                  <div>
                    <p className="section-label mb-0.5">CV accuracy</p>
                    <p className="font-display text-lg font-semibold">
                      <RollingNumber value={run.cv_accuracy * 100} decimals={1} suffix="%" />
                    </p>
                  </div>
                  <div>
                    <p className="section-label mb-0.5">F1-macro</p>
                    <p className="font-display text-lg font-semibold">
                      {run.f1_macro != null ? <RollingNumber value={run.f1_macro} decimals={3} /> : '—'}
                    </p>
                  </div>
                  <div>
                    <p className="section-label mb-0.5">Samples</p>
                    <p className="font-display text-lg font-semibold">
                      {run.n_labeled_samples != null ? <RollingNumber value={run.n_labeled_samples} /> : '—'}
                    </p>
                  </div>
                </div>
              )}

              {run.error_message && (
                <p className="text-xs text-danger">{run.error_message}</p>
              )}
            </Card>
          ))}
          </div>
        )}
      </div>
    </div>
  );
}
