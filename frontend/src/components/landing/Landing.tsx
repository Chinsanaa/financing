'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { m, type MotionProps } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import Button from '@/components/ui/Button';
import StatementSheet from './StatementSheet';
import HowItWorks from './HowItWorks';
import SmoothScroll from './SmoothScroll';

/** What it does, as ledger rows — no icon tiles, no bento. Every line is a
 *  capability the product actually has (PRODUCT.md: mechanism only). */
const FEATURES = [
  ['Both formats, one timeline', 'Alipay CSV and WeChat Pay Excel exports are parsed separately, then normalized into one schema.'],
  ['Chinese merchant text, understood', 'Descriptions are segmented with jieba before your model reads them, and shown to you in English.'],
  ['A model that is yours', 'It is trained only on your labels, so it learns your merchants — not someone else’s.'],
  ['Honest about doubt', 'Guesses below your model’s measured confidence wait in a review queue instead of being applied silently.'],
  ['Planning, not just charts', 'Category budgets, a 50/30/20 split, a savings goal and detected subscriptions, with alerts as you near a limit.'],
  ['Private per account', 'Your transactions, labels and model are isolated to your account. Nothing is shared.'],
];

const WRAP = 'mx-auto max-w-6xl px-4 sm:px-6 lg:px-8';
const EASE_OUT = [0.22, 1, 0.36, 1] as const;

export default function Landing() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // One authored entrance: the headline settles, then the stamps take over.
  // (Reduced motion is handled globally by MotionConfig — never branch here.)
  const rise = (delay: number): MotionProps => ({
    initial: { opacity: 0, y: 14 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.6, ease: EASE_OUT, delay },
  });

  return (
    <div className="overflow-x-clip">
      <SmoothScroll />

      <header
        className={`fixed inset-x-0 top-0 z-50 bg-bg transition-[border-color] duration-200 border-b ${
          scrolled ? 'border-edge/15' : 'border-transparent'
        }`}
      >
        <div className={`${WRAP} flex h-16 items-center justify-between`}>
          <Link href="/" className="font-display text-xl font-medium tracking-[-0.01em]">
            Financing<span className="text-accent">.</span>
          </Link>
          <nav className="flex items-center gap-1 sm:gap-5">
            <a href="#how" className="hidden text-sm text-muted transition-colors hover:text-ink sm:inline">
              How it works
            </a>
            <Link href="/auth" className="px-2 text-sm text-ink underline-offset-4 hover:underline">
              Sign in
            </Link>
            <Link href="/auth?mode=signup">
              <Button size="sm">Start free</Button>
            </Link>
          </nav>
        </div>
      </header>

      <main>
        {/* ── Hero: the headline, then the statement itself ── */}
        <section className={`${WRAP} pt-28 sm:pt-36`}>
          <div className="grid gap-8 lg:grid-cols-[1.4fr,1fr] lg:items-end">
            <m.h1
              {...rise(0)}
              className="font-display text-[3.25rem] font-normal leading-[0.98] tracking-[-0.025em] sm:text-7xl lg:text-[6rem]"
            >
              Every yuan, accounted for.
            </m.h1>
            <m.div {...rise(0.12)} className="lg:pb-3">
              <p className="max-w-[42ch] text-[17px] leading-relaxed text-muted">
                Upload your Alipay and WeChat Pay statements, label a few merchants once, and a model trained on
                your own labels sorts the rest.
              </p>
              <div className="mt-6 flex flex-wrap items-center gap-5">
                <Link href="/auth?mode=signup">
                  <Button size="lg">
                    Start free <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
                <a href="#how" className="text-sm text-ink underline decoration-edge/30 underline-offset-4 hover:decoration-accent">
                  See how it works
                </a>
              </div>
            </m.div>
          </div>

          <m.div {...rise(0.25)} className="mt-14 sm:mt-20">
            <StatementSheet />
          </m.div>
        </section>

        {/* ── How it works: sticky story ── */}
        <section id="how" className={`${WRAP} scroll-mt-20 pt-28 sm:pt-36`}>
          <h2 className="max-w-[18ch] font-display text-4xl font-normal leading-[1.05] tracking-[-0.02em] sm:text-5xl">
            Three steps, once a month.
          </h2>
          <div className="mt-6 lg:mt-0">
            <HowItWorks />
          </div>
        </section>

        {/* ── What it does: ledger rows ── */}
        <section className={`${WRAP} pt-24 sm:pt-32`}>
          <h2 className="font-display text-4xl font-normal tracking-[-0.02em] sm:text-5xl">Built for real statements.</h2>
          <dl className="mt-10 border-t border-ink/80">
            {FEATURES.map(([term, text]) => (
              <div key={term} className="grid gap-1 border-b border-edge/15 py-5 sm:grid-cols-[minmax(0,1fr),minmax(0,1.4fr)] sm:gap-10">
                <dt className="font-display text-xl">{term}</dt>
                <dd className="max-w-[60ch] text-[15px] leading-relaxed text-muted">{text}</dd>
              </div>
            ))}
          </dl>
        </section>

        {/* ── Close ── */}
        <section className={`${WRAP} pb-24 pt-28 sm:pb-32 sm:pt-36`}>
          <div className="flex flex-col gap-8 border-t border-ink/80 pt-10 sm:flex-row sm:items-end sm:justify-between">
            <p className="max-w-[16ch] font-display text-4xl font-normal leading-[1.05] tracking-[-0.02em] sm:text-6xl">
              Start with this month’s statements.
            </p>
            <div className="flex flex-wrap items-center gap-5 sm:pb-2">
              <Link href="/auth?mode=signup">
                <Button size="lg">
                  Create your account <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/auth" className="text-sm underline decoration-edge/30 underline-offset-4 hover:decoration-accent">
                I already have one
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-edge/15">
        <div className={`${WRAP} flex flex-col gap-3 py-8 text-[13px] text-muted sm:flex-row sm:items-center sm:justify-between`}>
          <span>
            <span className="font-display text-base text-ink">
              Financing<span className="text-accent">.</span>
            </span>{' '}
            · Personal transaction classification, trained on your own labels.
          </span>
          <nav className="flex gap-5">
            <Link href="/privacy" className="hover:text-ink">Privacy</Link>
            <Link href="/terms" className="hover:text-ink">Terms</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
