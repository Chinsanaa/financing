import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import SiteFooter from '@/components/layout/SiteFooter';

export default function LegalPageLayout({
  title,
  lastUpdated,
  children,
}: {
  title: string;
  lastUpdated: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-edge/15 bg-bg">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8 xl:px-10">
          <Link href="/" className="font-display text-lg font-medium tracking-[-0.015em]">
            Financing<span className="text-accent">.</span>
          </Link>
          <Link
            href="/"
            className="inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-[13px] text-ink transition-colors duration-150 hover:bg-edge/6"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden /> Home
          </Link>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12 sm:px-6 lg:px-8 xl:px-10">
        <h1 className="font-display text-3xl font-medium tracking-[-0.015em] sm:text-4xl">{title}</h1>
        <p className="mt-2 text-sm text-muted">Last updated: {lastUpdated}</p>

        <div className="mt-10 max-w-[68ch] space-y-8 text-[15px] leading-relaxed text-muted">
          {children}
        </div>
      </main>

      <SiteFooter className="mt-20" />
    </div>
  );
}

export function LegalSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="font-display text-lg font-medium tracking-[-0.015em] text-ink">{title}</h2>
      <div className="mt-3 space-y-3">{children}</div>
    </section>
  );
}
