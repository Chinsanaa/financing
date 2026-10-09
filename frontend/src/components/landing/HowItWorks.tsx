'use client';

import { ReactNode, useEffect, useRef, useState } from 'react';
import { AnimatePresence, m, useInView, useReducedMotion } from 'framer-motion';
import { categoryColor } from '@/components/ui/Badge';

/**
 * Sticky scroll story (layout idea from Aceternity's sticky-scroll-reveal,
 * rebuilt on Ledger material): the steps scroll on the left while one sheet
 * on the right turns to the matching page. Phones get each sheet inline.
 * The 1-2-3 numbers carry real sequence, so they stay.
 */

function UploadSheet() {
  return (
    <div className="text-sm">
      {[
        ['alipay_record_202609.csv', 'Alipay', 214],
        ['wechat_bill_202609.xlsx', 'WeChat Pay', 97],
      ].map(([file, src, rows]) => (
        <div key={file as string} className="flex items-baseline justify-between gap-4 border-b border-edge/10 py-3">
          <span className="min-w-0 truncate">
            {file} <span className="text-muted">· {src}</span>
          </span>
          <span className="num shrink-0 text-muted">{rows} rows</span>
        </div>
      ))}
      <div className="flex items-baseline justify-between border-b-2 border-ink/80 py-4">
        <span className="font-medium">One timeline</span>
        <span className="num text-3xl">311</span>
      </div>
      <p className="pt-3 text-[13px] text-muted">
        Credit-card repayments and transfers between your own accounts are left out, so nothing is counted twice.
      </p>
    </div>
  );
}

const KEYS = ['Food', 'Transport', 'Shopping', 'Groceries', 'Health', 'Travel'];

function TeachSheet() {
  return (
    <div className="text-sm">
      <div className="flex items-baseline justify-between border-b border-edge/10 pb-3">
        <span className="font-display text-2xl">Keep Fitness</span>
        <span className="num text-2xl">¥82.00</span>
      </div>
      <p className="py-3 text-[13px] text-muted">
        Your model suggests <span className="text-ink">Health</span> · 61% sure
      </p>
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-edge/12 bg-edge/12 sm:grid-cols-3">
        {KEYS.map((k, i) => (
          <span key={k} className={`flex items-center justify-between bg-bg px-3 py-2.5 ${k === 'Health' ? 'text-ink outline-dashed outline-[1.5px] -outline-offset-[3px] outline-accent' : 'text-muted'}`}>
            {k}
            <span className="kbd">{i + 1}</span>
          </span>
        ))}
      </div>
      <p className="pt-3 text-[13px] text-muted">
        <span className="kbd">Enter</span> accepts the suggestion · <span className="kbd">S</span> skips
      </p>
    </div>
  );
}

const SPLIT = [
  ['Food', 4210],
  ['Housing', 2600],
  ['Transport', 1980],
  ['Shopping', 1620],
  ['Other', 2070],
] as const;

function UnderstandSheet() {
  const total = SPLIT.reduce((s, [, v]) => s + v, 0);
  return (
    <div className="text-sm">
      <p className="text-[13px] text-muted">Spent in September</p>
      <p className="num text-5xl leading-tight">¥{total.toLocaleString('en-US')}</p>
      {/* The chart is the headline: one bold bar, every slice named. */}
      <div className="mt-5 flex h-10 w-full gap-[2px]" role="img" aria-label="September spending by category">
        {SPLIT.map(([c, v]) => (
          <span
            key={c}
            className={`${c === 'Other' ? '' : categoryColor(c)} h-full`}
            style={{ width: `${(v / total) * 100}%`, backgroundColor: c === 'Other' ? 'rgb(var(--edge) / 0.25)' : 'rgb(var(--cat))' }}
          />
        ))}
      </div>
      <dl className="mt-4">
        {SPLIT.map(([c, v]) => (
          <div key={c} className="flex items-baseline justify-between border-b border-edge/10 py-2">
            <dt className="flex items-center gap-2">
              <span
                aria-hidden="true"
                className={`${c === 'Other' ? '' : categoryColor(c)} h-2.5 w-2.5 rounded-[2px]`}
                style={{ backgroundColor: c === 'Other' ? 'rgb(var(--edge) / 0.25)' : 'rgb(var(--cat))' }}
              />
              {c}
            </dt>
            <dd className="num">
              ¥{v.toLocaleString('en-US')} <span className="text-muted">· {Math.round((v / total) * 100)}%</span>
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

const STEPS: { title: string; text: string; sheet: ReactNode }[] = [
  {
    title: 'Upload both statements',
    text: 'Export the month from Alipay and WeChat Pay and drop both files in. Each format is parsed and normalized into one timeline.',
    sheet: <UploadSheet />,
  },
  {
    title: 'Teach it your merchants',
    text: 'Label the merchants your model isn’t sure about. Number keys pick a category; Enter accepts the suggestion. Every label becomes training data.',
    sheet: <TeachSheet />,
  },
  {
    title: 'Read the month',
    text: 'Your model sorts everything else. The month reads as one statement — totals, categories, budgets — with doubtful guesses held back for review.',
    sheet: <UnderstandSheet />,
  },
];

function Step({ i, active, onActive }: { i: number; active: boolean; onActive: (i: number) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.6 });
  useEffect(() => {
    if (inView) onActive(i);
  }, [inView, i, onActive]);
  const s = STEPS[i];
  return (
    <div ref={ref} className="flex min-h-0 flex-col justify-center py-10 lg:min-h-[60vh] lg:py-0">
      <p className={`num text-xl transition-colors duration-300 ${active ? 'text-accent-strong' : 'text-muted'}`}>{i + 1}</p>
      <h3 className="mt-2 font-display text-3xl font-medium tracking-[-0.01em] sm:text-4xl">{s.title}</h3>
      <p className="mt-3 max-w-[46ch] text-base leading-relaxed text-muted">{s.text}</p>
      <div className="mt-8 border-t border-ink/80 pt-5 lg:hidden">{s.sheet}</div>
    </div>
  );
}

export default function HowItWorks() {
  const [active, setActive] = useState(0);
  const reduce = useReducedMotion();
  return (
    <div className="grid gap-x-16 lg:grid-cols-2">
      <div>
        {STEPS.map((_, i) => (
          <Step key={i} i={i} active={active === i} onActive={setActive} />
        ))}
      </div>
      <div className="hidden lg:block">
        <div className="sticky top-[calc(50vh-210px)] min-h-[420px] border-t border-ink/80 pt-6">
          <AnimatePresence mode="wait" initial={false}>
            <m.div
              key={active}
              initial={reduce ? false : { opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduce ? undefined : { opacity: 0, y: -6, transition: { duration: 0.14, ease: [0.55, 0, 1, 0.45] } }}
              transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
            >
              {STEPS[active].sheet}
            </m.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
