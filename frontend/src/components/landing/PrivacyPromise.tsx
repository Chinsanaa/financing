import Link from 'next/link';

/**
 * "Private by design, and how it is paid for." Every line is taken from a
 * documented fact — app/privacy/page.tsx, README.md, PRODUCT.md — and
 * nothing else (audit W-11). Deliberately NOT claimed because it is not
 * documented: hosting region, encryption specifics, certifications, a
 * future pricing promise.
 */
const TERMS: { term: string; body: React.ReactNode }[] = [
  {
    term: 'What we keep',
    body: 'The statement files you upload, the transactions in them, your categories and labels, any budgets or goals you enter, and the model trained on your labels.',
  },
  {
    term: 'Who can see it',
    body: 'Your account only. The database enforces per-account row-level security, and uploaded files and models sit in per-user storage. Your model is trained on your labels alone and is never used for anyone else. We don’t sell your data.',
  },
  {
    term: 'What leaves the app',
    body: 'Merchant names we don’t already have an English name for are sent to Google Translate, once per name, and the translation is stored. There are no ads, and no third-party analytics or advertising trackers.',
  },
  {
    term: 'How to delete it',
    body: (
      <>
        Export your transactions any time, then delete your account in Settings. That removes your files, models,
        transactions, categories, rules and budgets. It can’t be undone.
      </>
    ),
  },
  {
    term: 'How it’s paid for',
    body: 'It’s free, and there is no paid plan today. It runs on free hosting tiers, which is why the first page after a quiet spell can take about 30 seconds to wake up. It started as its maker’s own monthly tool.',
  },
];

export default function PrivacyPromise() {
  return (
    <div>
      <dl className="border-t border-ink/80">
        {TERMS.map(({ term, body }) => (
          <div
            key={term}
            className="grid gap-1.5 border-b border-edge/15 py-5 sm:grid-cols-[minmax(0,15rem),minmax(0,1fr)] sm:gap-10"
          >
            <dt className="font-display text-xl font-medium">{term}</dt>
            <dd className="max-w-[62ch] text-[15px] leading-relaxed text-muted">{body}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-4 text-[13px] text-muted">
        The details are in the{' '}
        <Link href="/privacy" className="text-ink underline decoration-edge/30 underline-offset-4 hover:decoration-accent">
          privacy policy
        </Link>
        .
      </p>
    </div>
  );
}
