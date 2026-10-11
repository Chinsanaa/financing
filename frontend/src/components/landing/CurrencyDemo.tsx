'use client';

import { useState } from 'react';
import Segmented from '@/components/ui/Segmented';
import RollingNumber from '@/components/ui/RollingNumber';
import { formatCurrency } from '@/utils/format';
import { ILLUSTRATIVE_RATES } from './sampleStatement';

type Code = keyof typeof ILLUSTRATIVE_RATES;

const SYMBOL: Record<Code, string> = { USD: '$', EUR: '€', GBP: '£' };
const OPTIONS: { value: Code; label: string }[] = [
  { value: 'USD', label: 'USD' },
  { value: 'EUR', label: 'EUR' },
  { value: 'GBP', label: 'GBP' },
];

const CNY = 8000;

/**
 * "See it in your home currency": one big conversion line. The yuan figure
 * stays the real, primary number; the home figure is an approximation in
 * muted ink. The rates here are fixed and illustrative — the app uses ECB
 * reference rates via Frankfurter (docs/contracts/API_V5.md §2).
 */
export default function CurrencyDemo() {
  const [code, setCode] = useState<Code>('USD');
  const rate = ILLUSTRATIVE_RATES[code];
  const home = Math.round(CNY * rate);

  return (
    <div className="border-t border-ink/80 pt-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <p className="text-[13px] text-muted">Rent share · September</p>
        <Segmented options={OPTIONS} value={code} onChange={setCode} label="Home currency" layoutId="landing-home-ccy" size="sm" />
      </div>

      <p className="mt-6 flex flex-wrap items-baseline gap-x-5 gap-y-1 sm:mt-8">
        <span className="num text-[3.5rem] leading-none tracking-[-0.02em] sm:text-[6.5rem]">{formatCurrency(CNY, 0)}</span>
        <span className="num whitespace-nowrap text-[2.5rem] leading-none tracking-[-0.02em] text-muted sm:text-[4.5rem]">
          <span aria-hidden="true">≈ </span>
          <span className="sr-only">approximately </span>
          <RollingNumber value={home} prefix={SYMBOL[code]} />
        </span>
      </p>

      <p className="mt-6 border-t border-edge/12 pt-3 text-[13px] text-muted">
        Illustrative rate: 1 CNY = {rate} {code}. Not a live quote.
      </p>
    </div>
  );
}
