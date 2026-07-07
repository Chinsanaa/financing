'use client';

import { useState, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  ChevronLeft,
  ChevronRight,
  FileSpreadsheet,
  Tags,
  ListTodo,
  CheckCircle,
  Zap,
} from 'lucide-react';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import UploadWithIncomeTab from './UploadWithIncomeTab';
import CategoriesTab from './CategoriesTab';
import LabelTab from './LabelTab';
import ReviewTab from './ReviewTab';
import TrainingTab from './TrainingTab';

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

export default function TransactionsModelTab() {
  const [currentStep, setCurrentStep] = useState(0);

  const handleNext = useCallback(() => {
    setCurrentStep((prev) => Math.min(prev + 1, STEPS.length - 1));
  }, []);

  const handlePrev = useCallback(() => {
    setCurrentStep((prev) => Math.max(prev - 1, 0));
  }, []);

  const handleStepClick = useCallback((index: number) => {
    setCurrentStep(index);
  }, []);

  const currentStepData = STEPS[currentStep];
  const CurrentIcon = currentStepData.icon;

  return (
    <div className="space-y-6">
      {/* Header with Progress and Step Navigation */}
      <Card className="border-0 bg-gradient-to-r from-accent-strong/10 via-transparent to-transparent p-6 space-y-4">
        {/* Title and Description */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <CurrentIcon className="h-5 w-5 text-accent-strong" />
            <h2 className="text-lg font-semibold">{currentStepData.label}</h2>
            <span className="text-xs text-muted ml-auto">
              Step {currentStep + 1} of {STEPS.length} ({Math.round(((currentStep + 1) / STEPS.length) * 100)}%)
            </span>
          </div>
          <p className="text-sm text-muted">{currentStepData.description}</p>
        </div>

        {/* Progress Bar */}
        <div className="flex gap-2">
          {STEPS.map((step, index) => (
            <button
              key={step.id}
              onClick={() => handleStepClick(index)}
              className={`flex-1 h-2 rounded-full transition-all cursor-pointer ${
                index <= currentStep
                  ? 'bg-accent-strong'
                  : 'bg-edge/20 hover:bg-edge/30'
              }`}
              aria-label={`Step ${index + 1}: ${step.label}`}
            />
          ))}
        </div>

        {/* Step Pill Navigation */}
        <div className="flex gap-2 flex-wrap">
          {STEPS.map((step, index) => (
            <button
              key={step.id}
              onClick={() => handleStepClick(index)}
              className={`h-8 px-3 rounded-full text-sm font-medium transition-all ${
                index === currentStep
                  ? 'bg-accent-strong text-white'
                  : index < currentStep
                  ? 'bg-accent-strong/20 text-accent-strong hover:bg-accent-strong/30'
                  : 'bg-edge/10 text-muted hover:bg-edge/20'
              }`}
              aria-label={step.label}
            >
              {step.label}
            </button>
          ))}
        </div>
      </Card>

      {/* Step Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentStep}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.2 }}
        >
          <div className="min-h-[400px]">
            {currentStep === 0 && <UploadWithIncomeTab />}
            {currentStep === 1 && <CategoriesTab />}
            {currentStep === 2 && <LabelTab />}
            {currentStep === 3 && <ReviewTab />}
            {currentStep === 4 && <TrainingTab />}
          </div>
        </motion.div>
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
          Next
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
