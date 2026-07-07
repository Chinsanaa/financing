'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import {
  ArrowRight,
  BrainCircuit,
  FileSpreadsheet,
  Languages,
  LineChart,
  ShieldCheck,
  Tags,
  Upload,
  Wallet,
} from 'lucide-react';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import { Reveal, Stagger, StaggerItem } from '@/components/ui/motion';
import HeroChart from './HeroChart';
import DemoStrip from './DemoStrip';

const FEATURES = [
  {
    icon: FileSpreadsheet,
    title: 'Alipay + WeChat imports',
    text: 'Drop in raw CSV exports. Both formats are parsed and normalized into one clean timeline.',
  },
  {
    icon: BrainCircuit,
    title: 'A model that is yours',
    text: 'Train a personal classifier on your own labels. It learns your merchants, not someone else’s.',
  },
  {
    icon: Languages,
    title: 'Bilingual by design',
    text: 'Mixed Chinese and English descriptions are segmented and understood correctly.',
  },
  {
    icon: Tags,
    title: 'Categories you control',
    text: 'Start from a sensible set, rename and reshape it as your spending evolves.',
  },
  {
    icon: LineChart,
    title: 'Reports that explain',
    text: 'Trends, category splits, budgets and savings goals — clear charts, no spreadsheet digging.',
  },
  {
    icon: ShieldCheck,
    title: 'Private per user',
    text: 'Your transactions, labels and model are isolated to your account. Nothing is shared.',
  },
];

const STEPS = [
  {
    icon: Upload,
    step: '01',
    title: 'Upload',
    text: 'Export statements from Alipay or WeChat and drop the files in.',
  },
  {
    icon: Tags,
    step: '02',
    title: 'Teach',
    text: 'Label a handful of transactions. A few minutes is enough to start.',
  },
  {
    icon: Wallet,
    step: '03',
    title: 'Understand',
    text: 'The model categorizes everything else. Watch your spending come into focus.',
  },
];

export default function Landing() {
  const [scrolled, setScrolled] = useState(false);
  const { scrollYProgress } = useScroll();
  const heroGlow = useTransform(scrollYProgress, [0, 0.2], [1, 0]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div className="relative overflow-x-clip">
      {/* Navbar */}
      <header
        className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
          scrolled ? 'glass py-2.5' : 'bg-transparent py-4'
        }`}
      >
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="font-display text-lg font-bold tracking-tight">
            Financing<span className="text-accent-strong">.</span>
          </Link>
          <nav className="hidden items-center gap-6 text-sm text-muted sm:flex">
            <a href="#how" className="transition-colors hover:text-ink">How it works</a>
            <a href="#features" className="transition-colors hover:text-ink">Features</a>
          </nav>
          <div className="flex items-center gap-2">
            <Link href="/auth">
              <Button variant="ghost" size="sm">Sign in</Button>
            </Link>
            <Link href="/auth?mode=signup">
              <Button size="sm">
                Get started <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="bg-grid relative pt-36 pb-24 sm:pt-44">
        <motion.div
          style={{ opacity: heroGlow }}
          className="pointer-events-none absolute -top-40 left-1/2 h-[480px] w-[720px] -translate-x-1/2 rounded-full bg-accent/10 blur-3xl"
        />
        <div className="pointer-events-none absolute bottom-0 -left-32 h-80 w-80 rounded-full bg-violet/15 blur-3xl" />

        <div className="relative mx-auto max-w-6xl px-4 sm:px-6">
          <div className="grid items-center gap-14 lg:grid-cols-[1.1fr,1fr]">
            <div>
              <Reveal>
                <p className="section-label mb-4">Personal finance, machine-learned</p>
              </Reveal>
              <Reveal delay={0.05}>
                <h1 className="font-display text-5xl font-bold leading-[1.05] tracking-tight sm:text-6xl lg:text-7xl">
                  Know where
                  <br />
                  every yuan{' '}
                  <span className="relative inline-block whitespace-nowrap text-accent-strong">
                    goes.
                    <span className="absolute inset-x-0 -bottom-1 h-1 rounded-full bg-accent shadow-glow" />
                  </span>
                </h1>
              </Reveal>
              <Reveal delay={0.1}>
                <p className="mt-6 max-w-md text-lg text-muted">
                  Upload your Alipay and WeChat statements, teach a model your categories once,
                  and let it sort everything after that.
                </p>
              </Reveal>
              <Reveal delay={0.15}>
                <div className="mt-8 flex flex-wrap items-center gap-3">
                  <Link href="/auth?mode=signup">
                    <Button size="lg">
                      Start free <ArrowRight className="h-4 w-4" />
                    </Button>
                  </Link>
                  <a href="#how">
                    <Button variant="outline" size="lg">See how it works</Button>
                  </a>
                </div>
              </Reveal>
            </div>

            <Reveal delay={0.2}>
              <motion.div
                initial={{ rotate: 2 }}
                whileHover={{ rotate: 0, scale: 1.01 }}
                transition={{ type: 'spring', stiffness: 200, damping: 20 }}
              >
                <HeroChart />
              </motion.div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <Reveal>
            <p className="section-label mb-2">How it works</p>
            <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
              Three steps. No spreadsheets.
            </h2>
          </Reveal>
          <Stagger className="mt-12 grid gap-5 md:grid-cols-3">
            {STEPS.map(({ icon: Icon, step, title, text }) => (
              <StaggerItem key={step}>
                <Card hover className="h-full p-6">
                  <div className="mb-5 flex items-center justify-between">
                    <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent/12 text-accent-strong">
                      <Icon className="h-5 w-5" />
                    </span>
                    <span className="font-display text-sm font-semibold text-muted">{step}</span>
                  </div>
                  <h3 className="font-display text-lg font-semibold">{title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted">{text}</p>
                </Card>
              </StaggerItem>
            ))}
          </Stagger>
        </div>
      </section>

      {/* Live demo strip */}
      <section className="py-10">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <Reveal>
            <DemoStrip />
          </Reveal>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <Reveal>
            <p className="section-label mb-2">Features</p>
            <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
              Built for messy, real statements.
            </h2>
          </Reveal>
          <Stagger className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ icon: Icon, title, text }) => (
              <StaggerItem key={title}>
                <Card glass hover className="h-full p-6">
                  <span className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-accent/12 text-accent-strong">
                    <Icon className="h-5 w-5" />
                  </span>
                  <h3 className="font-display text-base font-semibold">{title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted">{text}</p>
                </Card>
              </StaggerItem>
            ))}
          </Stagger>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <Reveal>
            <Card glass className="relative overflow-hidden px-8 py-16 text-center">
              <div className="pointer-events-none absolute -top-24 left-1/2 h-64 w-96 -translate-x-1/2 rounded-full bg-accent/15 blur-3xl animate-glow-pulse" />
              <h2 className="font-display text-3xl font-bold tracking-tight sm:text-5xl">
                Your money, decoded.
              </h2>
              <p className="mx-auto mt-4 max-w-md text-muted">
                Five minutes from CSV export to your first categorized month.
              </p>
              <div className="mt-8">
                <Link href="/auth?mode=signup">
                  <Button size="lg">
                    Create your account <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
              </div>
            </Card>
          </Reveal>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-edge/8 py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 text-sm text-muted sm:flex-row sm:px-6">
          <span className="font-display font-semibold text-ink">
            Financing<span className="text-accent-strong">.</span>
          </span>
          <span>Personal transaction classification, powered by your own labels.</span>
        </div>
      </footer>
    </div>
  );
}
