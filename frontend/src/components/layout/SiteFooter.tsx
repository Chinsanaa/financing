import Link from 'next/link';
import FormatBadges from '@/components/brand/FormatBadges';

const WRAP = 'mx-auto max-w-6xl px-4 sm:px-6 lg:px-8';

const COLUMNS: { title: string; links: [label: string, href: string][] }[] = [
  {
    title: 'Product',
    links: [
      ['Start free', '/auth'],
      ['How it works', '/#how'],
      ['Import guide', '/guide'],
    ],
  },
  {
    title: 'Help',
    links: [
      ['Export from Alipay', '/guide#alipay'],
      ['Export from WeChat', '/guide#wechat'],
      ['Bank CSV', '/guide#bank'],
      ['FAQ', '/#faq'],
    ],
  },
  {
    title: 'Legal',
    links: [
      ['Privacy', '/privacy'],
      ['Terms', '/terms'],
    ],
  },
];

/**
 * Shared site footer (landing, privacy, terms, 404).
 *
 * Ledger detail: it opens with a thin double rule, the line a bookkeeper
 * draws under a closed account. Solid ink, no boxes.
 *
 * Every sentence here is grounded in documented facts (privacy page,
 * README, backend/fx.py) — no claims, counts or proof we can't back up.
 * Any page that shows the WeChat Pay / Alipay marks must also show the
 * trademark line (docs/DESIGN_SYSTEM.md §5, brand marks) — it lives here.
 */
export default function SiteFooter({ className = '' }: { className?: string } = {}) {
  const year = new Date().getFullYear();

  return (
    <footer className={`text-[13px] text-muted ${className}`}>
      <div className={WRAP}>
        {/* Closing double rule */}
        <div aria-hidden className="border-t border-ink/80 pt-[3px]">
          <div className="border-t border-ink/80" />
        </div>

        <div className="grid gap-12 py-12 lg:grid-cols-12 lg:gap-8 lg:py-14">
          <div className="lg:col-span-5">
            <Link href="/" className="font-display text-[1.75rem] font-medium leading-none lg:text-[2rem] tracking-[-0.02em] text-ink">
              Financing<span className="text-accent">.</span>
            </Link>
            <p className="mt-3 max-w-[38ch] text-[15px] leading-relaxed text-ink">
              Your Alipay and WeChat Pay spending, sorted and shown in English. Built for
              foreigners living in China.
            </p>

            <p className="mt-7 text-muted">Works with exports from</p>
            <FormatBadges size={15} compact className="mt-2" />

            <p className="mt-7 max-w-[46ch] leading-relaxed">
              <span className="text-ink">Private per account.</span> Row-level security on
              every record, a model trained only on your labels, no ad or analytics trackers,
              and you can delete everything from Settings.
            </p>
          </div>

          <nav aria-label="Footer" className="grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-3 lg:col-span-6 lg:col-start-7">
            {COLUMNS.map(({ title, links }) => (
              <div key={title}>
                <h2 className="font-display text-[15px] font-medium text-ink">{title}</h2>
                <ul className="mt-3 space-y-1">
                  {links.map(([label, href]) => (
                    <li key={href}>
                      <Link
                        href={href}
                        className="inline-block py-1 text-[14px] text-muted underline decoration-transparent underline-offset-4 transition-colors duration-150 hover:text-ink hover:decoration-edge/30"
                      >
                        {label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
        </div>

        <div className="space-y-1.5 border-t border-edge/15 py-6 text-xs leading-relaxed">
          <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="text-ink">
              &copy; <span className="num">{year}</span> Financing
            </span>
            <span>Home-currency amounts use European Central Bank reference rates via Frankfurter.</span>
          </p>
          <p>
            Not affiliated with Tencent or Ant Group. WeChat Pay and Alipay are trademarks of their
            respective owners.
          </p>
        </div>
      </div>
    </footer>
  );
}
