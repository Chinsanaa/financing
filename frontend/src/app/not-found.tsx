'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import Stamp from '@/components/ui/Stamp';
import SiteFooter from '@/components/layout/SiteFooter';

/**
 * 404 — "this page isn't in the ledger": a one-entry statement for the
 * requested address, struck through and stamped "Void" (approved stamp site
 * #4, docs/DESIGN_SYSTEM.md §5 — the only stamp on this page).
 */
export default function NotFound() {
  // The requested path is read after hydration (never during render), so the
  // prerendered markup and the first client render match (no #418).
  const [path, setPath] = useState<string | null>(null);
  useEffect(() => {
    setPath(window.location.pathname);
  }, []);

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-edge/15">
        <div className="mx-auto flex max-w-6xl items-center px-4 py-3 sm:px-6 lg:px-8">
          <Link href="/" className="font-display text-lg font-medium tracking-[-0.015em]">
            Financing<span className="text-accent">.</span>
          </Link>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-xl flex-1 flex-col justify-center px-4 py-20 sm:px-6">
        <h1 className="font-display text-[2rem] font-normal leading-[1.08] tracking-[-0.02em] sm:text-5xl">
          This page isn&rsquo;t in the ledger.
        </h1>
        <p className="mt-4 max-w-[46ch] text-[15px] leading-relaxed text-muted">
          Error 404. The address may be mistyped, or the page has moved. Nothing was recorded against it.
        </p>

        {/* The entry, voided */}
        <div className="mt-10 border-y border-ink/80 text-sm">
          <div className="flex items-center justify-between border-b border-edge/12 py-2 text-[13px] text-muted">
            <span>Entry</span>
            <span>Amount</span>
          </div>
          <div className="relative flex items-center gap-4 py-7">
            <span className="min-w-0 flex-1 truncate text-muted line-through decoration-edge/40">
              {path ?? ' '}
            </span>
            <span className="num text-muted line-through decoration-edge/40">¥0.00</span>
            <span className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 scale-[1.6] sm:scale-[1.9]">
              <Stamp label="Void" tilt={-6} delay={0.25} />
            </span>
          </div>
        </div>

        <div className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-4">
          <Link
            href="/"
            className="inline-flex h-10 items-center gap-2 rounded-md bg-accent px-4 text-sm font-medium text-accent-ink transition-colors duration-150 hover:bg-accent-strong active:scale-[0.97] active:duration-75"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden /> Back to home
          </Link>
          <Link
            href="/guide"
            className="text-sm text-ink underline decoration-edge/30 underline-offset-4 hover:decoration-accent"
          >
            Read the import guide
          </Link>
        </div>
      </main>

      <SiteFooter />
    </div>
  );
}
