'use client';

import { KeyboardEvent, useEffect, useRef, useState } from 'react';
import { RotateCcw } from 'lucide-react';
import Stamp from '@/components/ui/Stamp';
import { formatCurrency } from '@/utils/format';
import { DEMO_CATEGORIES, SAMPLE_COLOR, SAMPLE_ROWS, type SampleRow } from './sampleStatement';

/**
 * Hero artifact: a sample statement the visitor can sort.
 *
 * Most rows already carry the model's suggestion — a DASHED chip (a guess,
 * by line form). Two rows the model isn't sure about wait for the visitor:
 * pick a category (click, or keys 1–6) and that row gets the "Sorted" stamp.
 * Only the latest sorted row wears the stamp — earlier picks settle into a
 * solid chip — so at most one stamp is ever on screen (DESIGN_SYSTEM §5,
 * approved stamp site #3). Fictional data, labeled "Sample".
 */

const UNSURE = SAMPLE_ROWS.filter((r) => r.unsure);

function Swatch({ category, outline = false }: { category: string; outline?: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={`${SAMPLE_COLOR[category] ?? ''} inline-block h-2.5 w-2.5 shrink-0 rounded-[2px]`}
      style={outline ? { border: '1.5px solid rgb(var(--cat))' } : { backgroundColor: 'rgb(var(--cat))' }}
    />
  );
}

/** Model suggestion: dashed outline chip. */
function GuessChip({ category }: { category: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-[4px] border border-dashed border-edge/35 px-2 py-[3px] text-[12px] text-ink">
      <Swatch category={category} outline />
      {category}
      <span className="sr-only"> (suggested by the model)</span>
    </span>
  );
}

/** Confirmed by the visitor: solid swatch, solid hairline. */
function LabelChip({ category }: { category: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-[4px] border border-edge/25 bg-bg px-2 py-[3px] text-[12px] font-medium text-ink">
      <Swatch category={category} />
      {category}
      <span className="sr-only"> (labeled by you)</span>
    </span>
  );
}

function Merchant({ row }: { row: SampleRow }) {
  return (
    <span className="block min-w-0">
      <span className="text-[14px] leading-snug">
        <span className="text-muted">{row.original}</span>
        <span aria-hidden="true" className="px-1.5 text-muted">
          →
        </span>
        <span className="sr-only"> translated as </span>
        <span className="font-medium text-ink">{row.english}</span>
      </span>
      <span className="mt-0.5 block text-[12px] text-muted">
        <span className="num">{row.date}</span> · {row.source}
      </span>
    </span>
  );
}

export default function LiveDemo() {
  const [picks, setPicks] = useState<Record<string, string>>({});
  const [last, setLast] = useState<string | null>(null);
  const [announce, setAnnounce] = useState('');
  const pickerRef = useRef<HTMLDivElement>(null);
  const resetRef = useRef<HTMLButtonElement>(null);
  const refocus = useRef(false);

  const current = UNSURE.find((r) => !picks[r.id]) ?? null;
  const done = !current;
  const touched = Object.keys(picks).length > 0;

  // Keyboard users keep their place: when the picker they were in moves to
  // the next row, focus follows it (never steal focus on load).
  useEffect(() => {
    if (!refocus.current) return;
    refocus.current = false;
    const first = pickerRef.current?.querySelector<HTMLButtonElement>('button');
    (first ?? resetRef.current)?.focus();
  }, [current?.id]);

  function pick(category: string) {
    if (!current) return;
    if (pickerRef.current?.contains(document.activeElement)) refocus.current = true;
    const next = UNSURE.find((r) => r.id !== current.id && !picks[r.id]);
    setPicks((p) => ({ ...p, [current.id]: category }));
    setLast(current.id);
    setAnnounce(
      `${current.english} sorted as ${category}.${next ? ` Next: ${next.english}.` : ' All rows sorted.'}`,
    );
  }

  function reset() {
    setPicks({});
    setLast(null);
    setAnnounce('Sample reset.');
  }

  function onKeyDown(e: KeyboardEvent<HTMLElement>) {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const n = Number(e.key);
    if (!current || !Number.isInteger(n) || n < 1 || n > DEMO_CATEGORIES.length) return;
    e.preventDefault();
    pick(DEMO_CATEGORIES[n - 1]);
  }

  return (
    <figure
      onKeyDown={onKeyDown}
      aria-labelledby="demo-title"
      className="rounded-card border border-edge/15 bg-surface"
    >
      <figcaption className="flex items-start justify-between gap-4 border-b border-edge/12 px-4 py-3 sm:items-center sm:px-5">
        <span className="flex flex-col text-[13px] sm:flex-row sm:items-baseline sm:gap-x-2">
          <span id="demo-title" className="font-medium">
            Sample statement
          </span>
          <span className="text-muted">September · Alipay + WeChat Pay</span>
        </span>
        <span className="shrink-0 rounded-[3px] border border-edge/20 px-1.5 py-[1px] text-[11px] font-medium text-muted">
          Sample data
        </span>
      </figcaption>

      <ol className="divide-y divide-edge/10">
        {SAMPLE_ROWS.map((row) => {
          const picked = picks[row.id];
          const isCurrent = current?.id === row.id;
          return (
            <li key={row.id} className={`relative px-4 py-3 sm:px-5 ${isCurrent ? 'bg-bg' : ''}`}>
              {isCurrent && <span aria-hidden="true" className="absolute inset-y-0 left-0 w-[3px] bg-accent" />}
              <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1.5 sm:grid-cols-[minmax(0,1fr)_auto_5rem] sm:gap-x-4">
                <span className="row-span-2 sm:row-span-1">
                  <Merchant row={row} />
                </span>
                <span className="num col-start-2 row-start-1 text-right text-[15px] leading-snug sm:col-start-3">
                  {formatCurrency(row.amount)}
                </span>
                <span className="col-start-2 row-start-2 flex items-center justify-end gap-2 sm:row-start-1">
                  {picked ? (
                    <>
                      {last === row.id && <Stamp key={`${row.id}-${picked}`} label="Sorted" tilt={-5} />}
                      <LabelChip category={picked} />
                    </>
                  ) : row.suggestion ? (
                    <GuessChip category={row.suggestion} />
                  ) : (
                    <span
                      className={`rounded-[4px] border border-dashed px-2 py-[3px] text-[12px] ${
                        isCurrent ? 'border-accent text-accent-strong' : 'border-edge/30 text-muted'
                      }`}
                    >
                      {isCurrent ? 'Your call' : 'Not sure'}
                    </span>
                  )}
                </span>
              </div>

              {isCurrent && row.unsure && (
                <div className="mt-3">
                  <p id={`ask-${row.id}`} className="text-[13px] text-muted">
                    Your model isn’t sure: <span className="text-ink">{row.unsure[0]}</span> or{' '}
                    <span className="text-ink">{row.unsure[1]}</span>? Pick one.
                  </p>
                  <div
                    ref={pickerRef}
                    role="group"
                    aria-label={`Category for ${row.english}`}
                    aria-describedby={`ask-${row.id}`}
                    className="mt-2 grid grid-cols-2 gap-1.5 sm:grid-cols-3"
                  >
                    {DEMO_CATEGORIES.map((c, i) => {
                      const leading = row.unsure!.includes(c);
                      return (
                        <button
                          key={c}
                          type="button"
                          onClick={() => pick(c)}
                          aria-keyshortcuts={String(i + 1)}
                          className={`flex min-h-[40px] items-center justify-between gap-2 rounded-md border bg-surface px-2.5 py-2 text-left text-[13px] transition-[border-color,transform] duration-150 active:scale-[0.97] active:duration-75 hover:border-edge/45 ${
                            leading ? 'border-dashed border-accent text-ink' : 'border-edge/15 text-ink'
                          }`}
                        >
                          <span className="flex min-w-0 items-center gap-2">
                            <Swatch category={c} outline={leading} />
                            <span className="truncate">{c}</span>
                          </span>
                          <span className="kbd" aria-hidden="true">
                            {i + 1}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </li>
          );
        })}
      </ol>

      <div className="flex flex-wrap items-center justify-between gap-x-5 gap-y-2 border-t border-edge/12 px-4 py-3 text-[12px] text-muted sm:px-5">
        {done ? (
          <span className="text-ink">Sorted. In the app, every label you give trains your own model.</span>
        ) : (
          <span className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-3 w-5 rounded-[3px] border border-dashed border-edge/45" aria-hidden="true" />
              Suggested by your model
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-3 w-5 rounded-[3px] border border-edge/25 bg-bg" aria-hidden="true" />
              Labeled by you
            </span>
          </span>
        )}
        {touched && (
          <button
            ref={resetRef}
            type="button"
            onClick={reset}
            className="inline-flex items-center gap-1.5 rounded-sm text-muted transition-colors hover:text-ink"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" /> Start over
          </button>
        )}
      </div>

      <p className="sr-only" role="status" aria-live="polite">
        {announce}
      </p>
    </figure>
  );
}
