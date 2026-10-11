'use client';

import { useState } from 'react';
import { RotateCcw } from 'lucide-react';
import Stamp from '@/components/ui/Stamp';

/**
 * Hero artifact: a sample statement whose rows get their category stamped,
 * one after another. The first rows carry solid seals (labeled by you), the
 * rest outlined seals (your model's guesses, waiting for a one-key confirm) —
 * the product's actual mechanism, shown on its own material.
 * Synthetic data, labeled as such.
 */
const ROWS = [
  { date: '09-01', merchant: 'Luckin Coffee', source: 'WeChat Pay', amount: '18.50', category: 'Food', by: 'you' },
  { date: '09-01', merchant: 'Didi Chuxing', source: 'Alipay', amount: '32.40', category: 'Transport', by: 'you' },
  { date: '09-02', merchant: 'Hema Fresh', source: 'Alipay', amount: '212.60', category: 'Groceries', by: 'you' },
  { date: '09-03', merchant: 'Shanghai Metro', source: 'Alipay', amount: '4.00', category: 'Transport', by: 'model' },
  { date: '09-03', merchant: 'Meituan Delivery', source: 'WeChat Pay', amount: '46.80', category: 'Food', by: 'model' },
  { date: '09-04', merchant: 'Taobao', source: 'Alipay', amount: '129.00', category: 'Shopping', by: 'model' },
  { date: '09-05', merchant: 'Watsons', source: 'WeChat Pay', amount: '88.90', category: 'Health', by: 'model' },
] as const;

const TILTS = [-3, 2, -1.5, 2.5, -2.5, 1.5, -2];

export default function StatementSheet() {
  const [run, setRun] = useState(0);
  const mine = ROWS.filter((r) => r.by === 'you').length;

  return (
    <figure className="border-y border-ink/80 bg-bg">
      <figcaption className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 border-b border-edge/15 py-3 text-[13px]">
        <span>
          <span className="font-medium">Sample statement</span>
          <span className="text-muted"> · September 2026 · Alipay + WeChat Pay</span>
        </span>
        <button
          onClick={() => setRun((n) => n + 1)}
          className="inline-flex items-center gap-1.5 text-muted transition-colors hover:text-ink motion-reduce:hidden"
        >
          <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" /> Stamp again
        </button>
      </figcaption>

      <table className="w-full text-sm">
        <thead className="sr-only sm:not-sr-only">
          <tr className="text-left text-[12px] text-muted">
            <th className="w-20 py-2 font-normal">Date</th>
            <th className="py-2 font-normal">Merchant</th>
            <th className="py-2 pr-8 text-right font-normal">Amount</th>
            <th className="w-40 py-2 font-normal">Category</th>
          </tr>
        </thead>
        <tbody key={run}>
          {ROWS.map((r, i) => (
            <tr key={r.merchant} className="border-t border-edge/10 align-middle">
              <td className="num hidden py-3 text-muted sm:table-cell">{r.date}</td>
              <td className="py-3 pr-3">
                <span className="block font-medium">{r.merchant}</span>
                <span className="block text-[12px] text-muted">
                  <span className="num sm:hidden">{r.date} · </span>
                  {r.source}
                </span>
              </td>
              <td className="num py-3 pr-4 text-right text-[15px] sm:pr-8">¥{r.amount}</td>
              <td className="py-3">
                <Stamp
                  label={r.category}
                  variant={r.by === 'you' ? 'solid' : 'outline'}
                  tilt={TILTS[i]}
                  delay={0.55 + i * 0.24}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-edge/15 py-3 text-[12px] text-muted">
        <span className="inline-flex items-center gap-2">
          <span className="h-3 w-5 rounded-[2px] bg-accent" aria-hidden="true" /> {mine} labeled by you
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="h-3 w-5 rounded-[2px] border-[1.5px] border-dashed border-accent" aria-hidden="true" />{' '}
          {ROWS.length - mine} suggested by your model, one key to confirm
        </span>
      </div>
    </figure>
  );
}
