'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import dynamic from 'next/dynamic';
import { AnimatePresence, m } from 'framer-motion';
import { Check, ChevronLeft, ChevronRight } from 'lucide-react';
import Button from '@/components/ui/Button';
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
    description: 'Alipay + WeChat files',
  },
  {
    id: 'categories',
    label: 'Categories',
    description: 'Name and color them',
  },
  {
    id: 'label',
    label: 'Label',
    description: 'Teach your merchants',
  },
  {
    id: 'review',
    label: 'Review',
    description: 'Check the model’s guesses',
  },
  {
    id: 'train',
    label: 'Train',
    description: 'Retrain on your labels',
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

  return (
    <div className="space-y-8">
      {/* Steps as one ruled strip: done = ink rule + check, current =
          vermilion rule, upcoming = hairline. The step's own heading below
          names it, so there is no second title here. */}
      <ol className="grid grid-cols-5 gap-2 sm:gap-4">
        {STEPS.map((step, index) => {
          const done = index < currentStep;
          const current = index === currentStep;
          return (
            <li key={step.id} className="min-w-0">
              <button
                onClick={() => handleStepClick(index)}
                data-tour-id={`wizard-step-${step.id}`}
                aria-label={`Step ${index + 1}: ${step.label}`}
                aria-current={current ? 'step' : undefined}
                className={`group block w-full border-t-2 pt-2.5 text-left transition-colors duration-200 ${
                  current ? 'border-accent' : done ? 'border-ink' : 'border-edge/15 hover:border-edge/40'
                }`}
              >
                <span className="flex items-baseline gap-1.5">
                  <span className={`num text-[15px] ${current ? 'text-accent-strong' : done ? 'text-ink' : 'text-muted'}`}>
                    {done ? <Check className="inline h-3.5 w-3.5 -translate-y-px" aria-hidden="true" /> : index + 1}
                  </span>
                  <span className={`truncate text-sm ${current ? 'font-medium text-ink' : done ? 'text-ink' : 'text-muted group-hover:text-ink'}`}>
                    {step.label}
                  </span>
                </span>
                <span className="mt-0.5 hidden truncate text-[12px] text-muted lg:block">{step.description}</span>
              </button>
            </li>
          );
        })}
      </ol>

      {/* Step Content — slides in the direction of travel */}
      <AnimatePresence mode="wait" custom={direction}>
        <m.div
          key={currentStep}
          custom={direction}
          variants={{
            enter: (d: number) => ({ opacity: 0, x: 16 * d }),
            center: { opacity: 1, x: 0 },
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
      <div className="flex items-center justify-between gap-3 border-t border-edge/15 pt-5">
        {currentStep > 0 ? (
          <Button variant="ghost" onClick={handlePrev}>
            <ChevronLeft className="h-4 w-4" />
            {STEPS[currentStep - 1].label}
          </Button>
        ) : (
          <span />
        )}
        {currentStep < STEPS.length - 1 && (
          <Button variant="outline" onClick={handleNext}>
            Next: {STEPS[currentStep + 1].label}
            <ChevronRight className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
