'use client';

import { useEffect, useRef, useState } from 'react';
import { m, useReducedMotion } from 'framer-motion';
import { BrainCircuit, Play } from 'lucide-react';
import { toast } from 'sonner';
import RollingNumber from '@/components/ui/RollingNumber';
import { api } from '@/utils/api';
import { useApi, invalidate } from '@/utils/useApi';
import { advanceTour } from '@/utils/tour';
import { formatDateTime } from '@/utils/format';
import { Alert } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import { SectionHeader } from '@/components/ui/Card';
import Stamp from '@/components/ui/Stamp';
import Badge from '@/components/ui/Badge';
import EmptyState from '@/components/ui/EmptyState';
import { SkeletonRows } from '@/components/ui/Skeleton';
import { errorDetail } from '@/utils/errors';

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

const POLL_INTERVAL_MS = 5000;
const MAX_POLL_MS = 10 * 60 * 1000;

export default function TrainingTab() {
  const { data, setData, loading, error: loadError, reload } = useApi<{ training_runs: TrainingRun[] }>('/training/');
  const [training, setTraining] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  // The run that just finished in this session gets the stamp.
  const [justTrained, setJustTrained] = useState<string | null>(null);
  const reduce = useReducedMotion();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const runs = data?.training_runs || [];

  const mountedRef = useRef(true);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  // Clear any live interval when the tab unmounts — the old implementation
  // leaked the interval on tab switches and could stack several of them.
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      stopPolling();
    };
  }, []);

  const startPolling = (modelRunId: string) => {
    stopPolling();
    // handleRetrain awaits before getting here; if the user left the tab
    // meanwhile, the unmount cleanup already ran and would never clear this.
    if (!mountedRef.current) return;
    const startedAt = Date.now();
    pollRef.current = setInterval(async () => {
      if (Date.now() - startedAt > MAX_POLL_MS) {
        // A run stuck in 'running' must not be polled forever.
        stopPolling();
        setTraining(false);
        setMessage('Training is taking longer than usual. Check back in a few minutes.');
        return;
      }
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
            // A real milestone: the run gets stamped (replaces confetti).
            setJustTrained(run.id);
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
    }, POLL_INTERVAL_MS);
  };

  // Coming back to the tab while a run is still going: pick polling back up.
  const activeRunId = runs.find((r) => r.status === 'queued' || r.status === 'running')?.id;
  useEffect(() => {
    if (activeRunId && !pollRef.current) {
      setTraining(true);
      startPolling(activeRunId);
    }
    // startPolling only touches refs and state setters.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeRunId]);

  const handleRetrain = async () => {
    try {
      setError('');
      setMessage('');
      setTraining(true);
      const res = await api.training.retrain();
      const modelRunId: string = res.data.model_run_id;
      setMessage('Training started. Results appear below when it finishes.');
      // Without an id the poll would hit /training/undefined every 5s (seen
      // in production); the run list still refreshes on reload. Start the
      // poll before reloading so the resume effect doesn't start a second.
      if (modelRunId) startPolling(modelRunId);
      else setTraining(false);
      await reload(true);
      invalidate('/training');
      advanceTour('train'); // last tour step — the tour ends here
    } catch (err: any) {
      setError(errorDetail(err, 'Failed to start training'));
      setTraining(false);
    }
  };

  const statusTone = (status: string) =>
    status === 'succeeded' ? 'success' : status === 'failed' ? 'danger' : 'neutral';

  return (
    <div className="w-full space-y-6">
      <SectionHeader
        title="Training"
        description="Trains a fresh classifier on your labeled transactions, then re-classifies everything else."
      />

      {(error || loadError) && <Alert kind="error">{error || loadError}</Alert>}
      {message && <Alert kind="success">{message}</Alert>}

      {/* Launch: words + one action. While a run is live, a thin rule is
          drawn across — honest "working" without a fake percentage. */}
      <div className="border-y border-edge/15 py-6">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-display text-2xl">
              {training ? 'Learning your spending patterns…' : 'Ready when you are'}
            </p>
            <p className="mt-1 max-w-[56ch] text-sm text-muted">
              {training
                ? 'This usually takes under a minute. You can leave this page — it keeps running.'
                : 'The more transactions you label, the better it gets.'}
            </p>
          </div>
          <Button onClick={handleRetrain} loading={training} size="lg" data-tour-id="train-start">
            {!training && <Play className="h-4 w-4" />}
            {training ? 'Training' : 'Start training'}
          </Button>
        </div>
        {training && (
          <div className="mt-5 h-px overflow-hidden bg-edge/12" role="progressbar" aria-label="Training in progress">
            <m.div
              className="h-full w-full origin-left bg-ink"
              initial={{ scaleX: 0 }}
              animate={reduce ? { scaleX: 0.5 } : { scaleX: [0, 1], opacity: [1, 1, 0] }}
              transition={reduce ? undefined : { duration: 1.6, ease: [0.22, 1, 0.36, 1], repeat: Infinity }}
            />
          </div>
        )}
      </div>

      <div>
        <h3 className="mb-3 font-display text-2xl">History</h3>

        {loading ? (
          <SkeletonRows rows={4} />
        ) : runs.length === 0 ? (
          <EmptyState
            icon={BrainCircuit}
            title="No training runs yet"
            description="Label some transactions first, then start your first training run."
          />
        ) : (
          <div className="overflow-x-auto border-t border-ink/80">
            <table className="w-full text-sm">
              <thead className="border-b border-edge/15 text-left text-[12px] text-muted">
                <tr>
                  <th className="py-2.5 pr-4 font-normal">Run</th>
                  <th className="py-2.5 pr-4 font-normal">Status</th>
                  <th className="py-2.5 pr-4 text-right font-normal">CV accuracy</th>
                  <th className="py-2.5 pr-4 text-right font-normal">F1 (macro)</th>
                  <th className="py-2.5 text-right font-normal">Labels used</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run, i) => (
                  <tr key={run.id} className="border-b border-edge/10 align-middle">
                    <td className="py-3 pr-4">
                      <span className={i === 0 ? 'font-medium' : ''}>{formatDateTime(run.created_at)}</span>
                      {run.error_message && <span className="mt-0.5 block text-xs text-danger">{run.error_message}</span>}
                    </td>
                    <td className="py-3 pr-4">
                      {justTrained === run.id ? (
                        <Stamp label="Trained" tilt={-2} />
                      ) : (
                        <Badge tone={statusTone(run.status)}>
                          {run.status === 'queued' || run.status === 'running' ? `${run.status}…` : run.status}
                        </Badge>
                      )}
                    </td>
                    <td className="num py-3 pr-4 text-right text-[15px]">
                      {run.cv_accuracy != null ? <RollingNumber value={run.cv_accuracy * 100} decimals={1} suffix="%" /> : '—'}
                    </td>
                    <td className="num py-3 pr-4 text-right text-[15px]">
                      {run.f1_macro != null ? <RollingNumber value={run.f1_macro} decimals={3} /> : '—'}
                    </td>
                    <td className="num py-3 text-right text-[15px]">
                      {run.n_labeled_samples != null ? <RollingNumber value={run.n_labeled_samples} /> : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
