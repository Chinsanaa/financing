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
  return d ? d.toLocaleDateString('en-US', { month: 'short' }) : ym;
}

/** "2026-06" -> "June 2026" — for tooltips and month selectors, where the
 *  full year disambiguates month-only axis ticks. */
export function formatMonthLong(ym: string): string {
  const d = parseYearMonth(ym);
  return d ? d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }) : ym;
}

/** Any timestamp -> "yyyy/mm/dd", fixed regardless of browser locale. */
export function formatDate(value: string | Date | null | undefined): string {
  if (value == null) return '—';
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}/${m}/${day}`;
}

/** Any timestamp -> "yyyy/mm/dd HH:MM" (local time), fixed regardless of browser locale. */
export function formatDateTime(value: string | Date | null | undefined): string {
  if (value == null) return '—';
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${formatDate(d)} ${hh}:${mm}`;
}

// ── Home currency (v5) ──────────────────────────────────────────────────────
// CNY helpers above are untouched. Home-currency amounts use Intl's currency
// formatting so every ISO code gets its own symbol and minor units (JPY, KRW,
// ISK have none). en-US symbols disambiguate dollars ($, A$, CA$, HK$).

const homeFormatters = new Map<string, Intl.NumberFormat | null>();

function homeFormatter(currency: string, decimals?: number): Intl.NumberFormat | null {
  const key = `${currency}|${decimals ?? ''}`;
  if (!homeFormatters.has(key)) {
    let fmt: Intl.NumberFormat | null = null;
    try {
      fmt = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency,
        ...(decimals === undefined ? {} : { minimumFractionDigits: decimals, maximumFractionDigits: decimals }),
      });
    } catch {
      fmt = null; // not a valid ISO 4217 code
    }
    homeFormatters.set(key, fmt);
  }
  return homeFormatters.get(key) ?? null;
}

/**
 * Format an amount in the user's home currency, symbol-forward, minus before
 * the symbol: formatHomeCurrency(-1110.5, 'USD') → "-$1,110.50".
 * `decimals` defaults to the currency's own minor units. JPY renders as
 * "JP¥" so it can't be mistaken for the app's CNY "¥". An invalid code
 * falls back to "1,110.50 XYZ" instead of throwing.
 */
export function formatHomeCurrency(value: number, currency: string, decimals?: number): string {
  const n = Number.isFinite(value) ? value : 0;
  const code = (currency || '').toUpperCase();
  const fmt = homeFormatter(code, decimals);
  if (!fmt) return `${formatNumber(n, decimals ?? 2)} ${code}`.trim();
  return fmt
    .formatToParts(n)
    .map((p) => (p.type === 'currency' && p.value === CURRENCY_SYMBOL && code !== 'CNY' ? `${code.slice(0, 2)}${p.value}` : p.value))
    .join('');
}
