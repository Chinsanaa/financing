'use client';

import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowRight, Check, X } from 'lucide-react';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { useApi } from '@/utils/useApi';

/**
 * First-run checklist. Completion is derived from real account state:
 *  1. Upload    — any transactions exist
 *  2. Categories — the categories tab was visited (tracked locally)
 *  3. Label     — any transaction has a label
 *  4. Train     — any training run exists
 * Dismissal is stored locally; the card also hides itself once all done.
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

export default function OnboardingChecklist({
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
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, height: 0 }}
        className="mb-8"
      >
        <Card glass className="relative overflow-hidden p-6">
          {/* Progress bar across the top */}
          <div className="absolute inset-x-0 top-0 h-1 bg-edge/10">
            <motion.div
              className="h-full bg-accent"
              initial={false}
              animate={{ width: `${(completed.size / STEPS.length) * 100}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            />
          </div>

          <div className="mb-5 flex items-start justify-between gap-4">
            <div>
              <p className="section-label mb-1">Getting started</p>
              <h2 className="font-display text-lg font-semibold">
                {completed.size} of {STEPS.length} steps done
              </h2>
            </div>
            <button
              onClick={dismiss}
              aria-label="Dismiss onboarding"
              className="rounded-pill p-1.5 text-muted transition-colors hover:text-ink hover:bg-edge/8"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((step, i) => {
              const done = completed.has(step.id);
              const isNext = nextStep?.id === step.id;
              return (
                <div
                  key={step.id}
                  className={`rounded-xl border p-4 transition-colors ${
                    done
                      ? 'border-accent/25 bg-accent/5'
                      : isNext
                      ? 'border-accent/40 bg-surface'
                      : 'border-edge/8 bg-surface/60'
                  }`}
                >
                  <div className="mb-2 flex items-center gap-2">
                    <span
                      className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ${
                        done
                          ? 'bg-accent text-accent-ink'
                          : 'border border-edge/20 text-muted'
                      }`}
                    >
                      {done ? (
                        <motion.span
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          transition={{ type: 'spring', stiffness: 500, damping: 25 }}
                        >
                          <Check className="h-3.5 w-3.5" />
                        </motion.span>
                      ) : (
                        i + 1
                      )}
                    </span>
                    <h3 className={`text-sm font-medium ${done ? 'text-muted line-through' : ''}`}>
                      {step.title}
                    </h3>
                  </div>
                  <p className="mb-3 text-xs leading-relaxed text-muted">{step.text}</p>
                  {!done && (
                    <Button
                      variant={isNext ? 'primary' : 'outline'}
                      size="sm"
                      onClick={() => onNavigate(step.tab)}
                    >
                      Go <ArrowRight className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      </motion.div>
    </AnimatePresence>
  );
}
