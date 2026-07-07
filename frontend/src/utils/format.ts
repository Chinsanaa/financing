/**
 * Shared money/number formatting.
 *
 * Convention: individual transaction amounts show 2 decimals
 * (`formatCurrency`), aggregates/tiles show whole yuan
 * (`formatCurrencyWhole`). Negatives put the minus before the symbol:
 * -¥1,234.56, never ¥-1234.56.
 */

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
  return `${sign}¥${numberFormatter(decimals).format(Math.abs(n))}`;
}

export function formatCurrencyWhole(value: number): string {
  return formatCurrency(value, 0);
}
