'use client';

import Link from 'next/link';
import { ReactNode, useEffect, useState } from 'react';
import { m, type MotionProps } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import SiteFooter from '@/components/layout/SiteFooter';
import LiveDemo from './LiveDemo';
import FormatsStrip from './FormatsStrip';
import HowItWorks from './HowItWorks';
import CurrencyDemo from './CurrencyDemo';
import CashFlowTeaser from './CashFlowTeaser';
import PrivacyPromise from './PrivacyPromise';
import Faq from './Faq';
import SmoothScroll from './SmoothScroll';

/**
 * Landing (design system v5, "Ledger"). One flat page, sections separated
 * by rules and whitespace, every claim a mechanism the product has
 * (PRODUCT.md: no testimonials, counts or savings figures). Sample figures
 * are always labeled. The one stamp on the page lives in LiveDemo.
 */

const WRAP = 'mx-auto max-w-6xl px-4 sm:px-6 lg:px-8';
const EASE_OUT = [0.22, 1, 0.36, 1] as const;
const SIGNUP = '/auth?mode=signup';

function SectionTitle({ children, id }: { children: ReactNode; id?: string }) {
  return (
    <h2 id={id} className="max-w-[20ch] font-display text-4xl font-normal leading-[1.05] tracking-[-0.02em] sm:text-5xl">
      {children}
    </h2>
  );
}

function Lede({ children }: { children: ReactNode }) {
  return <p className="mt-4 max-w-[58ch] text-base leading-relaxed text-muted sm:text-[17px]">{children}</p>;
}

function StartFree({ size = 'lg' }: { size?: 'sm' | 'lg' }) {
  // A link styled as the primary button (no <button> nested in <a>).
  return (
    <Link
      href={SIGNUP}
      className={`inline-flex items-center justify-center gap-2 rounded-md bg-accent font-medium text-accent-ink transition-[transform,background-color] duration-150 ease-out hover:bg-accent-strong active:scale-[0.97] active:duration-75 ${
        size === 'lg' ? 'h-12 px-5 text-[15px]' : 'h-8 px-3 text-[13px]'
      }`}
    >
      Start free {size === 'lg' && <ArrowRight className="h-4 w-4" aria-hidden="true" />}
    </Link>
  );
}

export default function Landing() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // One authored entrance: the headline settles, then the demo arrives.
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
        className={`fixed inset-x-0 top-0 z-50 border-b bg-bg transition-[border-color] duration-200 ${
          scrolled ? 'border-edge/15' : 'border-transparent'
        }`}
      >
        <div className={`${WRAP} flex h-16 items-center justify-between`}>
          <Link href="/" className="font-display text-xl font-medium tracking-[-0.01em]">
            Financing<span className="text-accent">.</span>
          </Link>
          <nav aria-label="Main" className="flex items-center gap-1 sm:gap-5">
            <a href="#how" className="hidden text-sm text-muted transition-colors hover:text-ink md:inline">
              How it works
            </a>
            <a href="#faq" className="hidden text-sm text-muted transition-colors hover:text-ink md:inline">
              FAQ
            </a>
            <Link href="/auth" className="px-2 text-sm text-ink underline-offset-4 hover:underline">
              Sign in
            </Link>
            <StartFree size="sm" />
          </nav>
        </div>
      </header>

      <main>
        {/* ── Hero: the promise, then a statement you can sort ── */}
        <section aria-labelledby="hero-title" className={`${WRAP} pt-24 sm:pt-28 lg:pt-32`}>
          <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr),minmax(0,1.05fr)] lg:items-center lg:gap-14">
            <div>
              <m.h1
                id="hero-title"
                {...rise(0)}
                className="font-display text-[3.25rem] font-normal leading-[0.98] tracking-[-0.025em] sm:text-7xl lg:text-[5.25rem]"
              >
                Every yuan, accounted for.
              </m.h1>
              <m.div {...rise(0.12)}>
                <p className="mt-6 max-w-[40ch] text-[17px] leading-relaxed text-muted">
                  Living in China? Your Alipay and WeChat Pay statements, in plain English, sorted by a model that learns
                  your merchants.
                </p>
                <div className="mt-7 flex flex-wrap items-center gap-x-6 gap-y-4">
                  <StartFree />
                  <Link
                    href="/guide"
                    prefetch={false}
                    className="text-sm text-ink underline decoration-edge/30 underline-offset-4 hover:decoration-accent"
                  >
                    See how to export
                  </Link>
                </div>
              </m.div>
            </div>

            <m.div {...rise(0.25)}>
              <LiveDemo />
            </m.div>
          </div>

          <div className="mt-16 sm:mt-20">
            <FormatsStrip />
          </div>
        </section>

        {/* ── How it works: sticky story ── */}
        <section id="how" aria-labelledby="how-title" className={`${WRAP} scroll-mt-20 pt-24 sm:pt-32`}>
          <SectionTitle id="how-title">Three steps, once a month.</SectionTitle>
          <div className="mt-6 lg:mt-0">
            <HowItWorks />
          </div>
        </section>

        {/* ── Home currency: one big conversion line ── */}
        <section aria-labelledby="ccy-title" className={`${WRAP} pt-24 sm:pt-32`}>
          <SectionTitle id="ccy-title">See it in your home currency.</SectionTitle>
          <Lede>
            Set your home currency once and every total gets an approximate equivalent beside the yuan, at the European
            Central Bank reference rate for that day.
          </Lede>
          <div className="mt-10">
            <CurrencyDemo />
          </div>
        </section>

        {/* ── Cash flow ── */}
        <section aria-labelledby="flow-title" className={`${WRAP} pt-24 sm:pt-32`}>
          <div className="grid gap-10 lg:grid-cols-[minmax(0,0.85fr),minmax(0,1.15fr)] lg:gap-16">
            <div>
              <SectionTitle id="flow-title">Money in, money out, counted once.</SectionTitle>
              <Lede>
                Salary is income. Red packets and AA split-bill paybacks from friends are transfers, so they don’t
                inflate it. Moving money between your own cards and wallets is shown, but never counted as spending.
              </Lede>
            </div>
            <CashFlowTeaser />
          </div>
        </section>

        {/* ── Privacy & how it is paid for ── */}
        <section aria-labelledby="privacy-title" className={`${WRAP} pt-24 sm:pt-32`}>
          <SectionTitle id="privacy-title">Private by design. Here’s the whole deal.</SectionTitle>
          <div className="mt-10">
            <PrivacyPromise />
          </div>
        </section>

        {/* ── FAQ ── */}
        <section id="faq" aria-labelledby="faq-title" className={`${WRAP} scroll-mt-20 pt-24 sm:pt-32`}>
          <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr),minmax(0,2fr)] lg:gap-16">
            <SectionTitle id="faq-title">Questions, answered.</SectionTitle>
            <Faq />
          </div>
        </section>

        {/* ── Close ── */}
        <section aria-labelledby="close-title" className={`${WRAP} pb-24 pt-24 sm:pb-32 sm:pt-32`}>
          <div className="flex flex-col gap-8 border-t border-ink/80 pt-10 sm:flex-row sm:items-end sm:justify-between">
            <h2
              id="close-title"
              className="max-w-[16ch] font-display text-4xl font-normal leading-[1.05] tracking-[-0.02em] sm:text-6xl"
            >
              Start with this month’s statements.
            </h2>
            <div className="flex flex-wrap items-center gap-x-6 gap-y-4 sm:pb-2">
              <StartFree />
              <Link href="/auth" className="text-sm underline decoration-edge/30 underline-offset-4 hover:decoration-accent">
                I already have an account
              </Link>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
