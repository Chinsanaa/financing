'use client';

import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Check, X } from 'lucide-react';
import { useApi } from '@/utils/useApi';
import TourSpotlight from './TourSpotlight';

/**
 * First-run guide: a small step-tracker box in the bottom-right corner
 * (was previously a full-width banner at the top of every page —
 * `OnboardingChecklist`, replaced by this component) plus a spotlight
 * overlay pointing at whatever button the current step needs next.
 *
 * Completion is derived from real account state, unchanged from the
 * previous implementation:
 *  1. Upload     — any transactions exist
 *  2. Categories — the categories tab was visited (tracked locally)
 *  3. Label      — any transaction has a label
 *  4. Train      — any training run exists
 * Dismissal is stored locally; the box also hides itself once all done.
 */

interface Summary {
  total_transactions: number;
  labeled_transactions: number;
}

const STEPS = [
  {
    id: 'upload',
    tab: 'upload',
    title: 'Upload a statement',
    text: 'Drop in a CSV export from Alipay or WeChat.',
  },
  {
    id: 'categories',
    tab: 'categories',
    title: 'Review your categories',
    text: 'Check the starter list and adjust it to fit your life.',
  },
  {
    id: 'label',
    tab: 'label',
    title: 'Label a few transactions',
    text: 'Teach the model by hand-labeling a small batch.',
  },
  {
    id: 'train',
    tab: 'train',
    title: 'Train your model',
    text: 'Kick off training and let it categorize the rest.',
  },
] as const;

const VISITED_KEY = 'onboarding-visited-categories';
const DISMISSED_KEY = 'onboarding-dismissed';

/** Which DOM element the current step's spotlight should point at, aware
 * of where the user currently is — e.g. "upload" points at the top-level
 * nav tab until the user has actually navigated into the upload wizard
 * step, then points at the dropzone itself. */
function resolveTargetId(stepId: string, activeTab: string): string {
  if (stepId === 'upload') {
    return activeTab === 'upload' ? 'upload-choose-files' : 'nav-transactions-model';
  }
  return `wizard-step-${stepId}`;
}

export default function OnboardingTour({
  onNavigate,
  activeTab,
}: {
  onNavigate: (tab: string) => void;
  activeTab: string;
}) {
  const summaryQ = useApi<Summary>('/dashboard/summary');
  const trainingQ = useApi<{ training_runs: unknown[] }>('/training/');

  const [visitedCategories, setVisitedCategories] = useState(false);
  const [dismissed, setDismissed] = useState(true); // hidden until localStorage read

  useEffect(() => {
    setVisitedCategories(localStorage.getItem(VISITED_KEY) === '1');
    setDismissed(localStorage.getItem(DISMISSED_KEY) === '1');
  }, []);

  useEffect(() => {
    if (activeTab === 'categories' && !visitedCategories) {
      localStorage.setItem(VISITED_KEY, '1');
      setVisitedCategories(true);
    }
  }, [activeTab, visitedCategories]);

  const completed = useMemo(() => {
    const done = new Set<string>();
    if ((summaryQ.data?.total_transactions ?? 0) > 0) done.add('upload');
    if (visitedCategories) done.add('categories');
    if ((summaryQ.data?.labeled_transactions ?? 0) > 0) done.add('label');
    if ((trainingQ.data?.training_runs?.length ?? 0) > 0) done.add('train');
    return done;
  }, [summaryQ.data, trainingQ.data, visitedCategories]);

  const allDone = completed.size === STEPS.length;
  const stillLoading = summaryQ.loading || trainingQ.loading;
  const nextStep = STEPS.find((s) => !completed.has(s.id));

  if (dismissed || allDone || stillLoading) return null;

  const dismiss = () => {
    localStorage.setItem(DISMISSED_KEY, '1');
    setDismissed(true);
  };

  return (
    <>
      {nextStep && (
        <TourSpotlight
          targetId={resolveTargetId(nextStep.id, activeTab)}
          title={nextStep.title}
          text={nextStep.text}
          onSkip={dismiss}
        />
      )}

      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 12 }}
          className="glass fixed bottom-6 right-6 z-40 w-72 rounded-xl p-4 shadow-card"
        >
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <p className="section-label mb-0.5">Getting started</p>
              <p className="text-sm font-semibold">{completed.size} of {STEPS.length} done</p>
            </div>
            <button
              onClick={dismiss}
              aria-label="Dismiss onboarding"
              className="rounded-pill p-1.5 text-muted transition-colors hover:text-ink hover:bg-edge/8"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="space-y-1.5">
            {STEPS.map((step, i) => {
              const done = completed.has(step.id);
              const isCurrent = nextStep?.id === step.id;
              return (
                <button
                  key={step.id}
                  onClick={() => onNavigate(step.tab)}
                  className={`flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-left transition-colors ${
                    isCurrent ? 'bg-accent/10' : 'hover:bg-edge/5'
                  }`}
                >
                  <span
                    className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold ${
                      done
                        ? 'bg-accent text-accent-ink'
                        : isCurrent
                        ? 'border border-accent-strong text-accent-strong'
                        : 'border border-edge/20 text-muted'
                    }`}
                  >
                    {done ? <Check className="h-3 w-3" /> : i + 1}
                  </span>
                  <span
                    className={`text-sm ${
                      done ? 'text-muted line-through' : isCurrent ? 'font-medium text-ink' : 'text-muted'
                    }`}
                  >
                    {step.title}
                  </span>
                </button>
              );
            })}
          </div>
        </motion.div>
      </AnimatePresence>
    </>
  );
}
