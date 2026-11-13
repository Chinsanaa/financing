import { toneForKey } from '@/utils/categoryColors';
import { formatCurrency } from '@/utils/format';
import { OWN_ACCOUNT_SUBTYPES } from '@/types/v5';
import type { FlowSubtype, KindFilter, ReportRow, TransactionKind } from '@/types/v5';

export type Transaction = ReportRow;

export const PER_PAGE_OPTIONS = [10, 20, 50, 100];

export const SORT_OPTIONS: { value: string; sortBy: 'date' | 'category'; sortDir: 'asc' | 'desc'; label: string }[] = [
  { value: 'date-desc', sortBy: 'date', sortDir: 'desc', label: 'Date (Newest)' },
  { value: 'date-asc', sortBy: 'date', sortDir: 'asc', label: 'Date (Oldest)' },
  { value: 'category-asc', sortBy: 'category', sortDir: 'asc', label: 'Category (A–Z)' },
  { value: 'category-desc', sortBy: 'category', sortDir: 'desc', label: 'Category (Z–A)' },
];

export const KIND_OPTIONS: { value: KindFilter; label: string }[] = [
  { value: 'expense', label: 'Spending' },
  { value: 'income', label: 'Income' },
  { value: 'transfer', label: 'Transfers' },
  { value: 'all', label: 'All' },
];

// Same fixed sky/amber/emerald palette as the 50/30/20 breakdown
// (RuleBreakdown.tsx) — these are aggregate buckets, not per-category
// identities, so they stay constant rather than going through useCategoryColors().
export const BUCKET_TONE: Record<'Need' | 'Want' | 'Savings', string> = {
  Need: toneForKey('sky'),
  Want: toneForKey('amber'),
  Savings: toneForKey('emerald'),
};

export const LABEL_SOURCES: Record<string, string> = {
  rule: 'Rule',
  override: 'Manual',
  model: 'Model',
  model_agreed: 'Auto',
  none: 'Unset',
};

export const NON_EXPENSE_HINT =
  "Income and transfers don't have a spending category. Use Change type to make this row spending first.";

/** Money came IN to the user (API_V5 §1.1 sign rule: income rows are + when
 *  money comes in; expense/transfer rows are − when money comes in). */
export function isMoneyIn(t: Pick<Transaction, 'kind' | 'amount' | 'flow_subtype'>): boolean {
  if (isOwnAccount(t)) return false; // moving your own money is neither in nor out
  return t.kind === 'income' ? t.amount > 0 : t.amount < 0;
}

/** Transfers between the user's own accounts (top-up, repayment, …). They are
 *  shown NEUTRAL — muted, unsigned, "⇄" — never as income or spending. */
export function isOwnAccount(t: Pick<Transaction, 'kind' | 'flow_subtype'>): boolean {
  return t.kind === 'transfer' && !!t.flow_subtype && OWN_ACCOUNT_SUBTYPES.includes(t.flow_subtype);
}

/** CNY amount as shown in the table/editor: "+¥260.00" (in), "⇄ ¥2,000.00"
 *  (own-account), "¥18.50" (out / spending). */
export function amountText(t: Pick<Transaction, 'kind' | 'amount' | 'flow_subtype'>): string {
  if (isOwnAccount(t)) return `⇄ ${formatCurrency(Math.abs(t.amount))}`;
  return isMoneyIn(t) ? `+${formatCurrency(Math.abs(t.amount))}` : formatCurrency(t.amount);
}

/** Plain-English type label for a row, direction-aware ("Red packet received").
 *  null for ordinary purchases (they need no label). */
export function typeLabel(t: Pick<Transaction, 'kind' | 'flow_subtype' | 'amount'>): string | null {
  const incoming = isMoneyIn(t);
  if (t.kind === 'expense') return t.flow_subtype === 'refund' ? 'Refund' : null;
  if (t.kind === 'income') {
    if (t.flow_subtype === 'salary') return 'Salary';
    if (t.flow_subtype === 'interest') return 'Interest';
    return t.flow_subtype === 'other' ? 'Other income' : 'Income';
  }
  switch (t.flow_subtype) {
    case 'red_packet':
      return incoming ? 'Red packet received' : 'Red packet sent';
    case 'aa_collection':
      return 'AA collected';
    case 'p2p_transfer':
      return incoming ? 'Transfer from a person' : 'Transfer to a person';
    case 'own_account':
      return 'Own-account transfer';
    case 'repayment':
      return 'Credit card repayment';
    case 'top_up':
      return 'Wallet top-up';
    case 'withdrawal':
      return 'Withdrawal to bank';
    default:
      return incoming ? 'Transfer in' : 'Transfer out';
  }
}

// "Change type" choices. Value = "kind:subtype" ("kind:" = no subtype).
// Labels are direction-neutral; the row's sign decides "sent"/"received".
export const TYPE_CHOICES: { group: string; options: { value: string; label: string }[] }[] = [
  {
    group: 'Spending',
    options: [
      { value: 'expense:', label: 'Purchase (spending)' },
      { value: 'expense:refund', label: 'Refund of a purchase' },
    ],
  },
  {
    group: 'Income',
    options: [
      { value: 'income:salary', label: 'Salary' },
      { value: 'income:interest', label: 'Interest' },
      { value: 'income:other', label: 'Other income' },
    ],
  },
  {
    group: 'Transfer (not spending or income)',
    options: [
      { value: 'transfer:red_packet', label: 'Red packet' },
      { value: 'transfer:aa_collection', label: 'Shared bill (AA) collection' },
      { value: 'transfer:p2p_transfer', label: 'Transfer to/from a person' },
      { value: 'transfer:own_account', label: 'Own-account transfer' },
      { value: 'transfer:repayment', label: 'Credit card repayment' },
      { value: 'transfer:top_up', label: 'Wallet top-up' },
      { value: 'transfer:withdrawal', label: 'Withdrawal to bank' },
      { value: 'transfer:other', label: 'Other transfer' },
    ],
  },
];

export function typeValue(t: Pick<Transaction, 'kind' | 'flow_subtype'>): string {
  return `${t.kind}:${t.flow_subtype ?? ''}`;
}

export function parseTypeValue(v: string): { kind: TransactionKind; flow_subtype: FlowSubtype | null } {
  const [kind, sub] = v.split(':');
  return { kind: kind as TransactionKind, flow_subtype: (sub || null) as FlowSubtype | null };
}

export function typeChangeNote(kind: TransactionKind): string {
  if (kind === 'expense')
    return 'It will count as spending and go to your review queue to get a category.';
  if (kind === 'income') return 'It will count as income. Its category is removed and it no longer counts as spending.';
  return "It won't count as spending or income. Its category is removed.";
}
