import Link from 'next/link';
import Button from '@/components/ui/Button';
import SiteFooter from '@/components/layout/SiteFooter';
import AlipaySteps from './AlipaySteps';
import BankCsvSteps from './BankCsvSteps';
import GuideSwitcher from './GuideSwitcher';
import WeChatSteps from './WeChatSteps';

const WRAP = 'mx-auto max-w-6xl px-4 sm:px-6 lg:px-8';

const AT_A_GLANCE: { label: string; alipay: string; wechat: string; bank: string }[] = [
  { label: 'Arrives as', alipay: '.zip by email (.csv inside)', wechat: '.zip by email (.xlsx inside)', bank: '.csv or .xlsx download' },
  { label: 'Unzip password', alipay: 'Alipay message or SMS', wechat: 'WeChat Pay chat', bank: 'None' },
  { label: 'Per request', alipay: 'Up to 12 months', wechat: 'Up to 3 months', bank: 'Set by your bank' },
  { label: 'Typical wait', alipay: 'Minutes', wechat: 'Up to 24 hours', bank: 'Instant' },
];

/** "/guide" — Painless import: how to export each statement (public page). */
export default function ImportGuide() {
  return (
    <div className="min-h-screen bg-bg">
      <header className="sticky top-0 z-40 border-b border-edge/15 bg-bg">
        <div className={`${WRAP} flex h-14 items-center justify-between`}>
          <Link href="/" className="font-display text-xl font-medium tracking-[-0.01em]">
            Financing<span className="text-accent">.</span>
          </Link>
          <nav className="flex items-center gap-1 sm:gap-4">
            <Link href="/auth" className="px-2 text-sm text-ink underline-offset-4 hover:underline">
              Sign in
            </Link>
            <Link href="/auth?mode=signup">
              <Button size="sm">Start free</Button>
            </Link>
          </nav>
        </div>
      </header>

      <main className={`${WRAP} pb-16`}>
        <div className="pb-8 pt-12 sm:pt-16">
          <h1 className="font-display text-[2.5rem] font-normal leading-[1.02] tracking-[-0.02em] sm:text-6xl">
            Painless import
          </h1>
          <p className="mt-4 max-w-[58ch] text-[17px] leading-relaxed text-muted">
            Getting the statement out of the app is the hard part when the menus aren&apos;t in your language. Here is
            each export step by step, using the apps&apos; English interface. Where labels differ between versions, the step says so.
          </p>

          <div className="mt-8 overflow-x-auto">
            <table className="w-full min-w-[34rem] text-sm">
              <caption className="sr-only">The three exports at a glance</caption>
              <thead className="border-b border-ink/80 text-left">
                <tr>
                  <td />
                  <th scope="col" className="py-2 pr-4 font-medium">Alipay</th>
                  <th scope="col" className="py-2 pr-4 font-medium">WeChat Pay</th>
                  <th scope="col" className="py-2 font-medium">Bank CSV</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-edge/12">
                {AT_A_GLANCE.map((r) => (
                  <tr key={r.label}>
                    <th scope="row" className="py-2.5 pr-4 text-left font-normal text-muted">{r.label}</th>
                    <td className="py-2.5 pr-4">{r.alipay}</td>
                    <td className="py-2.5 pr-4">{r.wechat}</td>
                    <td className="py-2.5">{r.bank}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <GuideSwitcher />

        <div className="mt-10 space-y-16">
          <AlipaySteps />
          <WeChatSteps />
          <BankCsvSteps />
        </div>

        <p className="mt-6 max-w-[64ch] text-[13px] leading-relaxed text-muted">
          Based on published walkthroughs, not official documentation, as of October 2026. Menu labels may vary by
          app version and region. If a button has moved, look for the same words in the menu at the top right of
          your bills or transactions page.
        </p>
      </main>

      <SiteFooter />
    </div>
  );
}
