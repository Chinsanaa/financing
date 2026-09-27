'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { m, useMotionValue, useReducedMotion, useScroll, useSpring, useTransform } from 'framer-motion';
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
import Badge, { categoryColor } from '@/components/ui/Badge';
import { trackSpotlight } from '@/utils/spotlight';
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

/** Merchants for the marquee — the kind of rows real statements are full of. */
const MARQUEE = [
  { merchant: 'Luckin Coffee', category: 'Food' },
  { merchant: 'Didi Chuxing', category: 'Transport' },
  { merchant: 'Taobao', category: 'Shopping' },
  { merchant: 'Meituan', category: 'Food' },
  { merchant: 'Shanghai Metro', category: 'Transport' },
  { merchant: 'JD.com', category: 'Shopping' },
  { merchant: 'Hema Fresh', category: 'Groceries' },
  { merchant: 'Ctrip', category: 'Travel' },
  { merchant: 'Bilibili', category: 'Fun' },
  { merchant: 'Watsons', category: 'Health' },
];

/** Headline that reveals word by word: each word rises out of a blur. */
function WordReveal({ text, className = '', delay = 0 }: { text: string; className?: string; delay?: number }) {
  const reduce = useReducedMotion();
  return (
    <>
      {text.split(' ').map((word, i) => (
        <m.span
          key={i}
          className={`inline-block ${className}`}
          initial={reduce ? false : { opacity: 0, y: '0.4em', filter: 'blur(10px)' }}
          animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay: delay + i * 0.08 }}
        >
          {word}&nbsp;
        </m.span>
      ))}
    </>
  );
}

/** Wraps the hero mockup: tilts in 3D toward the pointer, springs back on leave. */
function TiltCard({ children }: { children: React.ReactNode }) {
  const reduce = useReducedMotion();
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotateY = useSpring(useTransform(x, [-0.5, 0.5], [-10, 10]), { stiffness: 200, damping: 20 });
  const rotateX = useSpring(useTransform(y, [-0.5, 0.5], [8, -8]), { stiffness: 200, damping: 20 });
  return (
    <div style={{ perspective: 1200 }}>
      <m.div
        style={reduce ? undefined : { rotateX, rotateY, transformStyle: 'preserve-3d' }}
        onPointerMove={(e) => {
          if (e.pointerType !== 'mouse') return;
          const r = e.currentTarget.getBoundingClientRect();
          x.set((e.clientX - r.left) / r.width - 0.5);
          y.set((e.clientY - r.top) / r.height - 0.5);
        }}
        onPointerLeave={() => {
          x.set(0);
          y.set(0);
        }}
        className="relative"
      >
        {children}
      </m.div>
    </div>
  );
}

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
      <div className="aurora" aria-hidden="true" />
      <div className="grain" aria-hidden="true" />
      {/* Navbar */}
      <header
        className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
          scrolled ? 'glass py-2.5' : 'bg-transparent py-4'
        }`}
      >
        <div className="mx-auto flex max-w-7xl 2xl:max-w-[1440px] items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link href="/" className="group flex items-center gap-2 font-display text-lg font-bold tracking-tight">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent text-sm font-black text-accent-ink shadow-glow transition-transform duration-300 group-hover:rotate-[-8deg]">
              F
            </span>
            <span>
              Financing<span className="text-accent-strong">.</span>
            </span>
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
      <section className="group/hero relative z-[1] pt-36 pb-20 sm:pt-44" onPointerMove={trackSpotlight}>
        {/* Base grid, plus a lime copy of it revealed only around the pointer */}
        <div className="bg-grid pointer-events-none absolute inset-0 [mask-image:linear-gradient(to_bottom,black_60%,transparent)]" aria-hidden="true" />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-500 group-hover/hero:opacity-100"
          style={{
            backgroundImage:
              'linear-gradient(rgb(var(--accent) / 0.35) 1px, transparent 1px), linear-gradient(90deg, rgb(var(--accent) / 0.35) 1px, transparent 1px)',
            backgroundSize: '48px 48px',
            WebkitMaskImage: 'radial-gradient(220px circle at var(--mx, 50%) var(--my, 50%), black, transparent)',
            maskImage: 'radial-gradient(220px circle at var(--mx, 50%) var(--my, 50%), black, transparent)',
          }}
        />
        <m.div
          style={{ opacity: heroGlow }}
          className="pointer-events-none absolute -top-40 left-1/2 h-[480px] w-[720px] -translate-x-1/2 rounded-full bg-[radial-gradient(closest-side,rgb(var(--accent)/0.16),transparent)]"
        />

        <div className="relative mx-auto max-w-7xl 2xl:max-w-[1440px] px-4 sm:px-6 lg:px-8">
          <div className="grid items-center gap-14 lg:grid-cols-[1.1fr,1fr]">
            <div>
              <Reveal>
                <span className="mb-6 inline-flex items-center gap-2 rounded-pill border border-edge/10 bg-surface/60 px-3 py-1.5 text-xs font-medium text-muted backdrop-blur">
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inset-0 rounded-full bg-accent animate-ping-soft" />
                    <span className="relative h-2 w-2 rounded-full bg-accent" />
                  </span>
                  Alipay + WeChat Pay · CSV & Excel
                </span>
              </Reveal>
              <h1 className="font-display text-5xl font-bold leading-[1.05] tracking-tight sm:text-6xl lg:text-7xl">
                <WordReveal text="Know where" />
                <br />
                <WordReveal text="every yuan" delay={0.16} />
                <m.span
                  className="relative inline-block whitespace-nowrap"
                  initial={{ opacity: 0, y: '0.4em', filter: 'blur(10px)' }}
                  animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                  transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay: 0.36 }}
                >
                  <span className="text-shine">goes.</span>
                  <m.span
                    className="absolute inset-x-0 -bottom-1 h-1 origin-left rounded-full bg-accent shadow-glow"
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: 1 }}
                    transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1], delay: 0.9 }}
                  />
                </m.span>
              </h1>
              <Reveal delay={0.35}>
                <p className="mt-6 max-w-md text-lg text-muted">
                  Upload your Alipay and WeChat statements, teach a model your categories once,
                  and let it sort everything after that.
                </p>
              </Reveal>
              <Reveal delay={0.45}>
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
              <TiltCard>
                <HeroChart />
                {/* Floating "just categorized" chips orbit the mockup */}
                <m.div
                  aria-hidden="true"
                  className="glass absolute -left-8 bottom-20 hidden items-center gap-2 rounded-xl px-3 py-2 text-xs shadow-card sm:flex"
                  style={{ transform: 'translateZ(40px)' }}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0, y: [0, -6, 0] }}
                  transition={{ opacity: { delay: 1.4 }, x: { delay: 1.4 }, y: { duration: 5, repeat: Infinity, ease: 'easeInOut' } }}
                >
                  <span className="font-medium">Luckin Coffee</span>
                  <ArrowRight className="h-3 w-3 text-muted" />
                  <Badge tone={categoryColor('Food')}>Food</Badge>
                </m.div>
                <m.div
                  aria-hidden="true"
                  className="glass absolute -right-4 -bottom-5 hidden items-center gap-2 rounded-xl px-3 py-2 text-xs shadow-card sm:flex"
                  style={{ transform: 'translateZ(60px)' }}
                  initial={{ opacity: 0, x: 12 }}
                  animate={{ opacity: 1, x: 0, y: [0, 6, 0] }}
                  transition={{ opacity: { delay: 1.7 }, x: { delay: 1.7 }, y: { duration: 6, repeat: Infinity, ease: 'easeInOut' } }}
                >
                  <BrainCircuit className="h-3.5 w-3.5 text-accent-strong" />
                  <span className="font-medium">Auto-categorized</span>
                  <span className="text-muted">just now</span>
                </m.div>
              </TiltCard>
            </Reveal>
          </div>
        </div>
      </section>

      {/* Merchant marquee — edges fade out via mask */}
      <section className="relative z-[1] border-y border-edge/8 bg-surface/40 py-5 backdrop-blur-sm" aria-label="Example merchants">
        <div className="group/marquee flex overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_12%,black_88%,transparent)]">
          <div className="flex shrink-0 animate-marquee gap-3 pr-3 group-hover/marquee:[animation-play-state:paused]">
            {[...MARQUEE, ...MARQUEE].map((row, i) => (
              <span
                key={i}
                className="flex shrink-0 items-center gap-2 rounded-pill border border-edge/10 bg-surface px-3 py-1.5 text-sm"
                aria-hidden={i >= MARQUEE.length}
              >
                <span className="text-muted">{row.merchant}</span>
                <ArrowRight className="h-3 w-3 text-muted" />
                <Badge tone={categoryColor(row.category)}>{row.category}</Badge>
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="relative z-[1] py-24">
        <div className="mx-auto max-w-7xl 2xl:max-w-[1440px] px-4 sm:px-6 lg:px-8">
          <Reveal>
            <p className="section-label mb-2">How it works</p>
            <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
              Three steps. No spreadsheets.
            </h2>
          </Reveal>
          <Stagger className="mt-12 grid gap-5 md:grid-cols-3">
            {STEPS.map(({ icon: Icon, step, title, text }) => (
              <StaggerItem key={step}>
                <Card hover className="group h-full p-6">
                  <div className="mb-5 flex items-center justify-between">
                    <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent/12 text-accent-strong">
                      <Icon className="h-5 w-5" />
                    </span>
                    <span className="font-display text-4xl font-bold text-edge/10 transition-colors duration-300 group-hover:text-accent/40">{step}</span>
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
      <section className="relative z-[1] py-10">
        <div className="mx-auto max-w-7xl 2xl:max-w-[1440px] px-4 sm:px-6 lg:px-8">
          <Reveal>
            <DemoStrip />
          </Reveal>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="relative z-[1] py-24">
        <div className="mx-auto max-w-7xl 2xl:max-w-[1440px] px-4 sm:px-6 lg:px-8">
          <Reveal>
            <p className="section-label mb-2">Features</p>
            <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
              Built for messy, real statements.
            </h2>
          </Reveal>
          <Stagger className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {/* Bento: 3 double-width tiles + 3 single = 9 cells = three full rows
                (wide/single, single/wide, wide/single) on the 3-col layout. */}
            {FEATURES.map(({ icon: Icon, title, text }, i) => {
              const wide = i === 0 || i === 3 || i === 4;
              return (
                <StaggerItem key={title} className={wide ? 'lg:col-span-2' : ''}>
                  <Card glass hover className="group relative h-full overflow-hidden p-6">
                    {wide && (
                      <div
                        aria-hidden="true"
                        className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-[radial-gradient(closest-side,rgb(var(--accent)/0.14),transparent)] transition-transform duration-500 group-hover:scale-125"
                      />
                    )}
                    <span className="relative mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-accent/12 text-accent-strong transition-transform duration-300 group-hover:-rotate-6 group-hover:scale-110">
                      <Icon className="h-5 w-5" />
                    </span>
                    <h3 className={`relative font-display font-semibold ${wide ? 'text-xl' : 'text-base'}`}>{title}</h3>
                    <p className={`relative mt-1.5 leading-relaxed text-muted ${wide ? 'max-w-md text-base' : 'text-sm'}`}>{text}</p>
                  </Card>
                </StaggerItem>
              );
            })}
          </Stagger>
        </div>
      </section>

      {/* Final CTA */}
      <section className="relative z-[1] py-24">
        <div className="mx-auto max-w-7xl 2xl:max-w-[1440px] px-4 sm:px-6 lg:px-8">
          <Reveal>
            <Card glass glow className="relative overflow-hidden px-8 py-16 text-center">
              <div className="pointer-events-none absolute -top-24 left-1/2 h-64 w-96 -translate-x-1/2 rounded-full bg-accent/15 blur-3xl animate-glow-pulse" />
              <h2 className="font-display text-3xl font-bold tracking-tight sm:text-5xl">
                Your money, <span className="text-shine">decoded.</span>
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
      <footer className="relative z-[1] border-t border-edge/8 py-10">
        <div className="mx-auto flex max-w-7xl 2xl:max-w-[1440px] flex-col items-center justify-between gap-4 px-4 text-sm text-muted sm:flex-row sm:px-6 lg:px-8">
          <span className="font-display font-semibold text-ink">
            Financing<span className="text-accent-strong">.</span>
          </span>
          <span>Personal transaction classification, powered by your own labels.</span>
          <nav className="flex items-center gap-5">
            <Link href="/privacy" className="transition-colors hover:text-ink">
              Privacy Policy
            </Link>
            <Link href="/terms" className="transition-colors hover:text-ink">
              Terms &amp; Conditions
            </Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
