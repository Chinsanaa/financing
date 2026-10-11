import Link from 'next/link';
import type { ReactNode } from 'react';
import { ArrowRight } from 'lucide-react';
import Button from '@/components/ui/Button';

export interface GuideStep {
  /** The instruction, with the app's English labels in <Ui>. */
  title: ReactNode;
  /** Optional extra sentence in muted text. */
  body?: ReactNode;
  /** "Label may vary" note, e.g. 'Some versions say "Bill".' */
  varies?: string;
  /** The <PhoneFrame> illustration for this step. */
  screen: ReactNode;
}

export interface GuideFact {
  term: string;
  detail: ReactNode;
}

/** An app's English menu label, set so it scans as "the thing to tap". */
export function Ui({ children }: { children: ReactNode }) {
  return <strong className="font-semibold text-ink">{children}</strong>;
}

/**
 * One export walkthrough on /guide: title + intro and a ruled fact list on
 * the left, numbered steps (each with its phone) on the right, then the
 * "upload it here" call to action. Ledger rules: hairlines, no cards.
 */
export default function GuideSection({
  id,
  title,
  intro,
  facts,
  steps,
  aside,
}: {
  id: string;
  title: string;
  intro: ReactNode;
  facts: GuideFact[];
  steps: GuideStep[];
  /** Extra content under the steps (the bank section's column guide). */
  aside?: ReactNode;
}) {
  const headingId = `${id}-title`;
  return (
    <section id={id} aria-labelledby={headingId} className="scroll-mt-32 border-t border-ink/80 pt-8 sm:pt-10">
      <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr),minmax(0,2fr)] lg:gap-14">
        <div>
          <h2 id={headingId} className="font-display text-[1.75rem] font-normal leading-tight tracking-[-0.015em] sm:text-3xl">
            {title}
          </h2>
          <p className="mt-3 max-w-[46ch] text-[15px] leading-relaxed text-muted">{intro}</p>
          <dl className="mt-6 divide-y divide-edge/12 border-y border-edge/12 text-sm">
            {facts.map((f) => (
              <div key={f.term} className="grid grid-cols-[7.5rem,1fr] gap-3 py-3">
                <dt className="text-muted">{f.term}</dt>
                <dd className="text-ink">{f.detail}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div>
          <ol className="grid gap-x-10 gap-y-8 md:grid-cols-2">
            {steps.map((s, i) => (
              <li key={i} className="flex gap-4">
                {s.screen}
                <div className="min-w-0 pt-1">
                  <p className="num text-2xl leading-none text-accent-strong" aria-hidden="true">
                    {i + 1}
                  </p>
                  <p className="mt-2 text-[15px] leading-snug text-ink">
                    <span className="sr-only">Step {i + 1}: </span>
                    {s.title}
                  </p>
                  {s.body && <p className="mt-1.5 text-sm leading-relaxed text-muted">{s.body}</p>}
                  {s.varies && <p className="mt-1.5 text-[13px] italic leading-snug text-muted">{s.varies}</p>}
                </div>
              </li>
            ))}
          </ol>
          {aside}
        </div>
      </div>

      <div className="mt-10 flex flex-col gap-3 border-t border-edge/12 py-6 sm:flex-row sm:items-center sm:justify-between">
        <p className="font-display text-xl font-normal">Got the file? Upload it here.</p>
        <div className="flex flex-wrap items-center gap-4">
          <Link href="/auth?mode=signup">
            <Button variant="outline">
              Start free <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          </Link>
          <Link href="/auth" className="text-sm text-ink underline decoration-edge/30 underline-offset-4 hover:decoration-accent">
            Sign in to upload
          </Link>
        </div>
      </div>
    </section>
  );
}
