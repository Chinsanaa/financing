'use client';

import { useEffect, useRef } from 'react';
import { AnimatePresence, m } from 'framer-motion';
import { ArrowRight, Check, X } from 'lucide-react';
import { skipTour, advanceTour, useTour, TOUR_STEPS, TourStep } from '@/utils/tour';
import TourSpotlight from './TourSpotlight';

/**
 * First-run guide, shown ONCE per account right after sign-up.
 *
 * State lives on the account (utils/tour.ts → GET /dashboard/tour), so it
 * never reappears on another device and is never inferred from data. Each
 * step moves forward only when the user actually does it — the tab that owns
 * the action calls advanceTour() (upload succeeded, first hand label,
 * training started); "Categories" has an explicit "Looks good, next" button
 * because reviewing has no single action. "Skip tour" is the only early exit.
 *
 * Layout: a step box (bottom-right, above the dimmed overlay) that always
 * carries the current instruction, plus a spotlight on the element to use.
 * When a step starts, the tour takes the user to that step's tab once.
 */

const STEP_INFO: Record<TourStep, { tab: string; target: string; title: string; text: string }> = {
  upload: {
    tab: 'upload',
    target: 'upload-choose-files',
    title: 'Upload a statement',
    text: 'Drop in a CSV export from Alipay or WeChat.',
  },
  categories: {
    tab: 'categories',
    target: 'categories-list',
    title: 'Review your categories',
    text: 'Check the starter list and adjust it to fit your life. Press “Looks good” when you’re done.',
  },
  label: {
    tab: 'label',
    target: 'label-area',
    title: 'Label a transaction',
    text: 'Pick the right category for a transaction — each label teaches your model.',
  },
  train: {
    tab: 'train',
    target: 'train-start',
    title: 'Train your model',
    text: 'Start training and let it categorize the rest.',
  },
};

export default function OnboardingTour({
  onNavigate,
  activeTab,
}: {
  onNavigate: (tab: string) => void;
  activeTab: string;
}) {
  const tour = useTour();
  const step = tour && !tour.finished ? tour.step : null;
  const info = step ? STEP_INFO[step] : null;
  const stepIndex = step ? TOUR_STEPS.indexOf(step) : -1;

  // When the user COMPLETES a step, take them to the next step's tab once —
  // so the spotlight always has something to point at. Never on page load
  // (the first step seen this visit is only recorded): a user who opens or
  // reloads another tab mid-tour isn't dragged away; the box offers
  // "Take me there" instead.
  const seenStep = useRef<TourStep | null>(null);
  useEffect(() => {
    if (!step || !info || seenStep.current === step) return;
    const isTransition = seenStep.current !== null;
    seenStep.current = step;
    if (isTransition && activeTab !== info.tab) onNavigate(info.tab);
  }, [step, info, activeTab, onNavigate]);

  // The step box is fixed bottom-right; give the page extra scroll room while
  // it's showing so page-bottom controls (e.g. the wizard's "Next" button)
  // can always be scrolled clear of it.
  const active = !!step;
  useEffect(() => {
    if (!active) return;
    const prev = document.body.style.paddingBottom;
    document.body.style.paddingBottom = '18rem';
    return () => {
      document.body.style.paddingBottom = prev;
    };
  }, [active]);

  if (!step || !info) return null;

  const onStepTab = activeTab === info.tab;

  return (
    <>
      {onStepTab && <TourSpotlight targetId={info.target} />}

      <AnimatePresence>
        <m.div
          key="tour-box"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 12 }}
          // z-[70]: above the spotlight's dim layer (z-[60]) so the guide
          // itself is never darkened.
          className="fixed bottom-6 right-6 z-[70] w-80 rounded-xl border border-edge/10 bg-surface p-4 shadow-card"
          role="dialog"
          aria-label="Getting started"
        >
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <p className="section-label mb-0.5">Getting started</p>
              <p className="text-sm font-semibold">
                Step {stepIndex + 1} of {TOUR_STEPS.length}
              </p>
            </div>
            <button
              onClick={skipTour}
              aria-label="Skip tour"
              className="rounded-pill p-1.5 text-muted transition-colors hover:bg-edge/8 hover:text-ink"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <ol className="mb-3 space-y-1">
            {TOUR_STEPS.map((s, i) => {
              const done = i < stepIndex;
              const current = i === stepIndex;
              return (
                <li key={s} className={`flex items-center gap-2.5 rounded-lg px-2 py-1 ${current ? 'bg-accent/10' : ''}`}>
                  <span
                    className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold ${
                      done
                        ? 'bg-accent text-accent-ink'
                        : current
                        ? 'border border-accent-strong text-accent-strong'
                        : 'border border-edge/20 text-muted'
                    }`}
                  >
                    {done ? <Check className="h-3 w-3" /> : i + 1}
                  </span>
                  <span className={`text-sm ${done ? 'text-muted line-through' : current ? 'font-medium text-ink' : 'text-muted'}`}>
                    {STEP_INFO[s].title}
                  </span>
                </li>
              );
            })}
          </ol>

          {/* The current instruction always lives here, so the guide never
              "vanishes" even when the spotlight target is off-screen. */}
          <p className="text-xs leading-relaxed text-muted">{info.text}</p>

          <div className="mt-3 flex items-center justify-between gap-2">
            <button
              onClick={skipTour}
              className="text-xs text-muted underline decoration-edge/40 underline-offset-2 hover:text-ink"
            >
              Skip tour
            </button>
            {!onStepTab ? (
              <button
                onClick={() => onNavigate(info.tab)}
                className="inline-flex items-center gap-1 rounded-pill bg-accent px-3 py-1.5 text-xs font-semibold text-accent-ink"
              >
                Take me there <ArrowRight className="h-3 w-3" />
              </button>
            ) : step === 'categories' ? (
              <button
                onClick={() => advanceTour('categories')}
                className="inline-flex items-center gap-1 rounded-pill bg-accent px-3 py-1.5 text-xs font-semibold text-accent-ink"
              >
                Looks good, next <ArrowRight className="h-3 w-3" />
              </button>
            ) : null}
          </div>
        </m.div>
      </AnimatePresence>
    </>
  );
}
