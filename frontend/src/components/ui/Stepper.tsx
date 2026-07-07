'use client';

import { Check } from 'lucide-react';
import { motion } from 'framer-motion';

export type Step = { id: string; title: string };

/** Horizontal progress stepper: filled check for done, accent ring for current. */
export default function Stepper({
  steps,
  completed,
  currentId,
}: {
  steps: Step[];
  completed: Set<string>;
  currentId?: string;
}) {
  return (
    <ol className="flex items-center gap-0 w-full">
      {steps.map((step, i) => {
        const done = completed.has(step.id);
        const current = step.id === currentId;
        return (
          <li key={step.id} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center gap-1.5">
              <span
                className={`flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold transition-colors ${
                  done
                    ? 'bg-accent border-accent text-accent-ink'
                    : current
                    ? 'border-accent text-accent-strong ring-4 ring-accent/15'
                    : 'border-edge/20 text-muted'
                }`}
              >
                {done ? (
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 500, damping: 25 }}
                  >
                    <Check className="h-4 w-4" />
                  </motion.span>
                ) : (
                  i + 1
                )}
              </span>
              <span
                className={`text-xs whitespace-nowrap ${
                  done || current ? 'text-ink font-medium' : 'text-muted'
                }`}
              >
                {step.title}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className="mx-2 mb-5 h-px flex-1 overflow-hidden rounded bg-edge/15">
                <div
                  className={`h-full bg-accent transition-all duration-500 ${
                    done ? 'w-full' : 'w-0'
                  }`}
                />
              </div>
            )}
          </li>
        );
      })}
    </ol>
  );
}
