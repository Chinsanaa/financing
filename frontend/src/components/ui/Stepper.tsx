'use client';

import { Check } from 'lucide-react';
import { m } from 'framer-motion';

export type Step = { id: string; title: string };

/** Horizontal progress stepper: ink check for done, vermilion outline for current. */
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
                className={`num flex h-7 w-7 items-center justify-center rounded-full border text-[13px] transition-colors ${
                  done
                    ? 'bg-ink border-ink text-bg'
                    : current
                    ? 'border-accent border-[1.5px] text-accent-strong'
                    : 'border-edge/25 text-muted'
                }`}
              >
                {done ? (
                  <m.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', bounce: 0, duration: 0.3 }}
                  >
                    <Check className="h-3.5 w-3.5" />
                  </m.span>
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
              <div className="mx-2 mb-5 h-px flex-1 overflow-hidden bg-edge/15">
                <div
                  className={`h-full bg-ink transition-[width] duration-500 ease-out ${
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
