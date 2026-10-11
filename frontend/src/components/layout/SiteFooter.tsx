import Link from 'next/link';

const WRAP = 'mx-auto max-w-6xl px-4 sm:px-6 lg:px-8';

/**
 * Site footer (moved verbatim from the bottom of landing/Landing.tsx —
 * same markup, same look). Any page that shows the WeChat Pay / Alipay marks
 * must also show the trademark line (docs/DESIGN_SYSTEM.md §5, brand marks).
 */
export default function SiteFooter() {
  return (
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
  );
}
