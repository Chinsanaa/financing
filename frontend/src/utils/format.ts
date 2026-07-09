/**
 * Shared money/number formatting.
 *
 * Convention: individual transaction amounts show 2 decimals
 * (`formatCurrency`), aggregates/tiles show whole yuan
 * (`formatCurrencyWhole`). Negatives put the minus before the symbol:
 * -¥1,234.56, never ¥-1234.56.
 */

// Single source of truth for the currency glyph. The app is CNY-only today;
// centralizing it here means the handful of places that render a bare symbol
// (income tiles, input placeholders) stay consistent, and switching to true
// multi-currency later is one edit instead of a grep-and-replace.
export const CURRENCY_SYMBOL = '¥';

const formatters = new Map<number, Intl.NumberFormat>();

function numberFormatter(decimals: number): Intl.NumberFormat {
  let fmt = formatters.get(decimals);
  if (!fmt) {
    fmt = new Intl.NumberFormat('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
    formatters.set(decimals, fmt);
  }
  return fmt;
}

export function formatNumber(value: number, decimals = 0): string {
  return numberFormatter(decimals).format(value);
}

export function formatCurrency(value: number, decimals = 2): string {
  const n = Number.isFinite(value) ? value : 0;
  const sign = n < 0 ? '-' : '';
  return `${sign}${CURRENCY_SYMBOL}${numberFormatter(decimals).format(Math.abs(n))}`;
}

export function formatCurrencyWhole(value: number): string {
  return formatCurrency(value, 0);
}

/**
 * Parse a "YYYY-MM" month string as a LOCAL date. Never feed these to
 * `new Date("YYYY-MM-01")`: date-only ISO strings parse as UTC midnight, so
 * any viewer west of UTC sees the previous day — shifting every month label
 * back by one month.
 */
export function parseYearMonth(ym: string): Date | null {
  const m = /^(\d{4})-(\d{2})$/.exec(ym);
  if (!m) return null;
  return new Date(Number(m[1]), Number(m[2]) - 1, 1);
}

/** "2026-06" -> "Jun" — for chart axis ticks. Month only: a 2-digit year
 *  next to a month reads as a day-of-month ("Jun 26"). */
export function formatMonthShort(ym: string): string {
  const d = parseYearMonth(ym);
  return d ? d.toLocaleDateString(undefined, { month: 'short' }) : ym;
}

/** "2026-06" -> "June 2026" — for tooltips and month selectors, where the
 *  full year disambiguates month-only axis ticks. */
export function formatMonthLong(ym: string): string {
  const d = parseYearMonth(ym);
  return d ? d.toLocaleDateString(undefined, { month: 'long', year: 'numeric' }) : ym;
}
