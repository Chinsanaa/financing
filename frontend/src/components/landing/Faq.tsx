import Link from 'next/link';
import { Plus } from 'lucide-react';

/**
 * FAQ as native <details>/<summary>: keyboard and screen-reader support
 * for free, works without JavaScript. Answers are documented facts only
 * (README, docs/contracts/API_V5.md, app/privacy).
 */
const QA: { q: string; a: React.ReactNode }[] = [
  {
    q: 'Is this made by Alipay or WeChat?',
    a: (
      <>
        No. Financing is independent and not affiliated with Tencent or Ant Group. WeChat Pay and Alipay are trademarks of
        their respective owners. Nothing connects to your Alipay or WeChat account: you export a statement file yourself
        and upload it.
      </>
    ),
  },
  {
    q: 'Which files can I upload?',
    a: (
      <>
        Alipay statement exports, WeChat Pay bill exports, and bank statements, as <span className="text-ink">.csv</span>{' '}
        or <span className="text-ink">.xlsx</span>. The format is detected automatically. A bank file needs a date column
        and an amount (or debit and credit) column. Bank payments to Alipay or WeChat Pay are treated as moves between your
        own accounts, so the same purchase isn’t counted twice.{' '}
        <Link href="/guide" prefetch={false} className="text-ink underline decoration-edge/30 underline-offset-4 hover:decoration-accent">
          How to export each file
        </Link>
        .
      </>
    ),
  },
  {
    q: 'How does the translation work?',
    a: (
      <>
        Well-known merchants come from a curated list of English names. Anything else is sent to Google Translate once,
        in the background, and the result is stored, so pages never wait for it. Separately, your model reads the original
        text, split into words with jieba, a Chinese word segmenter, so the translation doesn’t affect how it sorts.
      </>
    ),
  },
  {
    q: 'Where do the home-currency rates come from?',
    a: (
      <>
        European Central Bank reference rates, published through Frankfurter. Each transaction uses the latest rate on
        or before its date (the ECB publishes on business days). 29 home currencies are supported. Your yuan amounts never
        change; the home figure is shown beside them as an approximation.
      </>
    ),
  },
  {
    q: 'How do I delete my data?',
    a: (
      <>
        In Settings you can export your transactions, then delete your account. That permanently removes your uploaded
        files, trained models, transactions, categories, rules and budgets.
      </>
    ),
  },
];

export default function Faq() {
  return (
    <div className="border-t border-ink/80">
      {QA.map(({ q, a }) => (
        <details key={q} className="group border-b border-edge/15">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-6 py-5 font-display text-xl font-medium marker:hidden [&::-webkit-details-marker]:hidden">
            {q}
            <Plus
              aria-hidden="true"
              className="h-5 w-5 shrink-0 text-muted transition-transform duration-200 ease-out group-open:rotate-45"
            />
          </summary>
          <p className="max-w-[68ch] pb-6 text-[15px] leading-relaxed text-muted">{a}</p>
        </details>
      ))}
    </div>
  );
}
