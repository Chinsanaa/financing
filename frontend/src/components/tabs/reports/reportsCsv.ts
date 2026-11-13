import { formatDate } from '@/utils/format';
import { typeLabel } from './reportsHelpers';
import type { Transaction } from './reportsHelpers';

export function toCsv(transactions: Transaction[]): string {
  // `text` cells come from statement text: a leading = + - @ tab or CR would make
  // spreadsheets run them as formulas, so prefix a single quote. Numbers and dates skip this.
  const esc = (v: unknown, text = false) => {
    let s = String(v ?? '');
    if (text && /^[=+\-@\t\r]/.test(s)) s = `'${s}`;
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const header = ['Date', 'Merchant', 'Description', 'Category', 'Type', 'Amount', 'Home amount', 'Source'];
  const rows = transactions.map((t) =>
    [
      esc(formatDate(t.date)),
      esc(t.merchant, true),
      esc(t.description, true),
      esc(t.kind === 'expense' ? t.category : '', true),
      esc(typeLabel(t) ?? 'Purchase', true),
      esc(t.amount),
      esc(t.amount_home ?? ''),
      esc(t.label_source, true),
    ].join(',')
  );
  return [header.join(','), ...rows].join('\n');
}
