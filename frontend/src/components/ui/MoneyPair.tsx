import { formatCurrency, formatHomeCurrency } from '@/utils/format';

/**
 * A CNY amount with an optional home-currency equivalent underneath (or
 * beside it, `inline`): "¥8,000" / "≈ $1,110". The CNY figure is always the
 * primary, real number; the home line is a muted approximation at the ECB
 * reference rate and is hidden entirely when there is no home currency or
 * no rate (`home` null or `home.amount` null). See docs/contracts/API_V5.md.
 *
 * Solid text colors only (Ledger design rule) — no gradients, no purple.
 */

export interface MoneyPairHome {
  amount: number | null;
  currency: string;
  /** CNY → home rate used (1 CNY = rate home units). Adds a tooltip. */
  rate?: number;
  /** "YYYY-MM-DD" of the ECB rate. */
  rateDate?: string;
}

const SIZES = {
  sm: { cny: 'text-sm', home: 'text-xs' },
  md: { cny: 'text-base', home: 'text-xs' },
  lg: { cny: 'text-[2rem] leading-none tracking-[-0.01em]', home: 'text-sm' },
} as const;

export function rateTooltip(rate?: number, rateDate?: string): string | undefined {
  if (rate === undefined || !Number.isFinite(rate)) return undefined;
  const r = rate >= 1 ? rate.toFixed(2) : rate.toPrecision(4);
  return `Rate ${r}${rateDate ? ` on ${rateDate}` : ''} (ECB)`;
}

export default function MoneyPair({
  cny,
  home,
  size = 'md',
  inline = false,
  decimals = 0,
  className = '',
}: {
  cny: number;
  home?: MoneyPairHome | null;
  size?: 'sm' | 'md' | 'lg';
  inline?: boolean;
  /** Decimals for BOTH figures (default 0 = whole units, like tiles). */
  decimals?: number;
  className?: string;
}) {
  const s = SIZES[size];
  const showHome = !!home && home.amount !== null && Number.isFinite(home.amount) && !!home.currency;
  const homeText = showHome ? formatHomeCurrency(home!.amount as number, home!.currency, decimals) : '';
  const title = showHome ? rateTooltip(home!.rate, home!.rateDate) : undefined;

  return (
    <span
      className={`${inline ? 'inline-flex items-baseline gap-2' : 'inline-flex flex-col'} min-w-0 ${className}`}
      title={title}
    >
      <span className={`num ${s.cny}`}>{formatCurrency(cny, decimals)}</span>
      {showHome && (
        <span className={`num text-muted ${s.home} ${inline ? '' : 'mt-1'}`}>
          <span aria-hidden="true">≈ </span>
          <span className="sr-only">approximately </span>
          {homeText}
        </span>
      )}
    </span>
  );
}
