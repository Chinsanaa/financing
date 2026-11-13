'use client';

import { formatHomeCurrency, rateTooltip } from '@/utils/format';
import { amountText, isMoneyIn, isOwnAccount } from './reportsHelpers';
import type { Transaction } from './reportsHelpers';

/** CNY amount (money in = "+" in the positive color) with the home-currency
 *  equivalent underneath. Rate tooltip uses the row's own date. */
export default function AmountCell({ txn, currencyHome }: { txn: Transaction; currencyHome: string | null }) {
  const incoming = isMoneyIn(txn);
  const own = isOwnAccount(txn);
  const showHome = !!currencyHome && txn.amount_home !== null && Number.isFinite(txn.amount_home);
  const day = (txn.date || '').slice(0, 10);
  // The row carries no rate, so derive it from the two rounded amounts —
  // only when the home amount is large enough for that to be accurate.
  const rate =
    showHome && Math.abs(txn.amount_home as number) >= 10 && txn.amount !== 0
      ? (txn.amount_home as number) / txn.amount
      : undefined;
  const title = showHome
    ? rateTooltip(rate, day) ?? `Converted at the ECB rate on ${day}`
    : undefined;
  return (
    <span className="inline-flex flex-col items-end" title={title}>
      <span
        className={`num whitespace-nowrap text-[15px] ${incoming ? 'text-positive' : own ? 'text-muted' : ''}`}
        title={own ? 'Moved between your own accounts — not income or spending' : undefined}
      >
        {amountText(txn)}
      </span>
      {showHome && (
        <span className="num whitespace-nowrap text-xs text-muted">
          <span aria-hidden="true">≈ </span>
          <span className="sr-only">approximately </span>
          {own
            ? formatHomeCurrency(Math.abs(txn.amount_home as number), currencyHome as string)
            : incoming
            ? `+${formatHomeCurrency(Math.abs(txn.amount_home as number), currencyHome as string)}`
            : formatHomeCurrency(txn.amount_home as number, currencyHome as string)}
        </span>
      )}
    </span>
  );
}
