'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import dynamic from 'next/dynamic';
import { AnimatePresence, m } from 'framer-motion';
import {
  ChevronLeft,
  ChevronRight,
  FileSpreadsheet,
  Tags,
  ListTodo,
  CheckCircle,
  Check,
  Zap,
} from 'lucide-react';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import { SkeletonRows } from '@/components/ui/Skeleton';

const stepLoading = () => <SkeletonRows rows={5} />;
const UploadWithIncomeTab = dynamic(() => import('./UploadWithIncomeTab'), { loading: stepLoading, ssr: false });
const CategoriesTab = dynamic(() => import('./CategoriesTab'), { loading: stepLoading, ssr: false });
const LabelTab = dynamic(() => import('./LabelTab'), { loading: stepLoading, ssr: false });
const ReviewTab = dynamic(() => import('./ReviewTab'), { loading: stepLoading, ssr: false });
const TrainingTab = dynamic(() => import('./TrainingTab'), { loading: stepLoading, ssr: false });

const STEPS = [
  {
    id: 'upload',
    label: 'Upload',
    icon: FileSpreadsheet,
    description: 'Import your transaction files',
  },
  {
    id: 'categories',
    label: 'Categories',
    icon: Tags,
    description: 'Define your spending categories',
  },
  {
    id: 'label',
    label: 'Label',
    icon: ListTodo,
    description: 'Manually label transactions',
  },
  {
    id: 'review',
    label: 'Review',
    icon: CheckCircle,
    description: 'Review model suggestions',
  },
  {
    id: 'train',
    label: 'Train',
    icon: Zap,
    description: 'Train your ML model',
  },
];

interface TransactionsModelTabProps {
  stepId?: string;
  onStepChange?: (stepId: string) => void;
}

export default function TransactionsModelTab({ stepId, onStepChange }: TransactionsModelTabProps = {}) {
  const stepIndex = stepId ? STEPS.findIndex((s) => s.id === stepId) : 0;
  const [currentStep, setCurrentStep] = useState(stepIndex >= 0 ? stepIndex : 0);

  useEffect(() => {
    if (stepId) {
      const index = STEPS.findIndex((s) => s.id === stepId);
      if (index >= 0) {
        setCurrentStep(index);
      }
    }
  }, [stepId]);

  const handleNext = useCallback(() => {
    const newStep = Math.min(currentStep + 1, STEPS.length - 1);
    setCurrentStep(newStep);
    onStepChange?.(STEPS[newStep].id);
  }, [currentStep, onStepChange]);

  const handlePrev = useCallback(() => {
    const newStep = Math.max(currentStep - 1, 0);
    setCurrentStep(newStep);
    onStepChange?.(STEPS[newStep].id);
  }, [currentStep, onStepChange]);

  const handleStepClick = useCallback((index: number) => {
    setCurrentStep(index);
    onStepChange?.(STEPS[index].id);
  }, [onStepChange]);

  // Remember the previous step so content slides in the direction of travel.
  const prevStepRef = useRef(currentStep);
  const direction = currentStep >= prevStepRef.current ? 1 : -1;
  useEffect(() => {
    prevStepRef.current = currentStep;
  }, [currentStep]);

  const currentStepData = STEPS[currentStep];
  const CurrentIcon = currentStepData.icon;
  const progress = currentStep / (STEPS.length - 1);

  return (
    <div className="space-y-6">
      {/* Header: current step + connected stepper */}
      <Card className="relative overflow-hidden p-5 sm:p-6">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -left-20 -top-24 h-64 w-64 rounded-full bg-[radial-gradient(closest-side,rgb(var(--accent)/0.14),transparent)]"
        />
        <div className="relative mb-6 flex items-center gap-3">
          <AnimatePresence mode="wait" initial={false}>
            <m.span
              key={currentStepData.id}
              initial={{ scale: 0.6, rotate: -20, opacity: 0 }}
              animate={{ scale: 1, rotate: 0, opacity: 1 }}
              exit={{ scale: 0.6, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 420, damping: 24 }}
              className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent text-accent-ink shadow-glow"
            >
              <CurrentIcon className="h-5 w-5" />
            </m.span>
          </AnimatePresence>
          <div className="min-w-0">
            <h2 className="font-display text-xl font-semibold tracking-tight">{currentStepData.label}</h2>
            <p className="text-sm text-muted">{currentStepData.description}</p>
          </div>
          <span className="ml-auto shrink-0 rounded-pill bg-edge/5 px-3 py-1 text-xs font-medium tabular-nums text-muted">
            Step {currentStep + 1} / {STEPS.length}
          </span>
        </div>

        {/* Stepper: nodes on a rail; the lit part of the rail grows with progress */}
        <ol className="relative flex items-start justify-between">
          <span aria-hidden="true" className="absolute left-4 right-4 top-4 h-0.5 rounded-full bg-edge/10" />
          <m.span
            aria-hidden="true"
            className="absolute left-4 top-4 h-0.5 origin-left rounded-full bg-accent shadow-[0_0_10px_rgb(var(--accent)/0.6)]"
            style={{ right: '1rem' }}
            initial={false}
            animate={{ scaleX: progress }}
            transition={{ type: 'spring', stiffness: 120, damping: 22 }}
          />
          {STEPS.map((step, index) => {
            const done = index < currentStep;
            const current = index === currentStep;
            const Icon = step.icon;
            return (
              <li key={step.id} className="relative z-[1] flex flex-col items-center gap-2">
                <button
                  onClick={() => handleStepClick(index)}
                  data-tour-id={`wizard-step-${step.id}`}
                  aria-label={`Step ${index + 1}: ${step.label}`}
                  aria-current={current ? 'step' : undefined}
                  className={`flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 ${
                    done
                      ? 'border-accent bg-accent text-accent-ink'
                      : current
                      ? 'scale-110 border-accent bg-surface text-accent-strong ring-4 ring-accent/15'
                      : 'border-edge/15 bg-surface text-muted hover:border-edge/30 hover:text-ink'
                  }`}
                >
                  {done ? <Check className="h-4 w-4" /> : <Icon className="h-3.5 w-3.5" />}
                </button>
                <span
                  className={`hidden text-xs sm:block ${
                    current ? 'font-semibold text-ink' : done ? 'text-ink' : 'text-muted'
                  }`}
                >
                  {step.label}
                </span>
              </li>
            );
          })}
        </ol>
      </Card>

      {/* Step Content — slides in the direction of travel */}
      <AnimatePresence mode="wait" custom={direction}>
        <m.div
          key={currentStep}
          custom={direction}
          variants={{
            enter: (d: number) => ({ opacity: 0, x: 24 * d, filter: 'blur(4px)' }),
            center: { opacity: 1, x: 0, filter: 'blur(0px)', transitionEnd: { filter: 'none' } },
            exit: (d: number) => ({ opacity: 0, x: -16 * d, transition: { duration: 0.14 } }),
          }}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="min-h-[400px]">
            {currentStep === 0 && <UploadWithIncomeTab />}
            {currentStep === 1 && <CategoriesTab />}
            {currentStep === 2 && <LabelTab />}
            {currentStep === 3 && <ReviewTab />}
            {currentStep === 4 && <TrainingTab />}
          </div>
        </m.div>
      </AnimatePresence>

      {/* Navigation Buttons */}
      <div className="flex gap-3 justify-between">
        <Button
          variant="outline"
          onClick={handlePrev}
          disabled={currentStep === 0}
          className="gap-2"
        >
          <ChevronLeft className="h-4 w-4" />
          Previous
        </Button>

        <Button
          variant="primary"
          onClick={handleNext}
          disabled={currentStep === STEPS.length - 1}
          className="gap-2"
        >
          Next: {STEPS[Math.min(currentStep + 1, STEPS.length - 1)].label}
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
