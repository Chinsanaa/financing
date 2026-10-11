/**
 * Fictional sample data for the landing page. Every figure here is made up
 * and every place it renders is labeled "Sample" / "Illustrative" — the
 * landing claims the mechanism only, never results (PRODUCT.md).
 *
 * Merchants are shown as the romanized original (pinyin, how the name reads
 * in the export) next to the English name the app shows. No Chinese
 * characters are rendered anywhere on the landing page.
 */

export type SampleSource = 'Alipay' | 'WeChat Pay';

export interface SampleRow {
  id: string;
  date: string;
  /** Romanized original merchant text, as it reads in the export. */
  original: string;
  /** English name shown in the app. */
  english: string;
  source: SampleSource;
  amount: number;
  /** The model's confident suggestion (drawn as a dashed chip). */
  suggestion?: string;
  /** Not sure: the visitor labels this row. The two leading guesses. */
  unsure?: [string, string];
}

/** Fixed sample colors (palette keys) so neighbours never collide. */
export const SAMPLE_COLOR: Record<string, string> = {
  Food: 'cat-amber',
  Groceries: 'cat-emerald',
  Transport: 'cat-blue',
  Shopping: 'cat-rose',
  Entertainment: 'cat-cyan',
  Health: 'cat-green',
  Housing: 'cat-sky',
  Travel: 'cat-olive',
};

/** Picker options, in key order (1–6). */
export const DEMO_CATEGORIES = ['Food', 'Groceries', 'Transport', 'Shopping', 'Entertainment', 'Health'] as const;

export const SAMPLE_ROWS: SampleRow[] = [
  { id: 'luckin', date: '09-01', original: 'Ruixing Kafei', english: 'Luckin Coffee', source: 'WeChat Pay', amount: 18.5, suggestion: 'Food' },
  { id: 'didi', date: '09-01', original: 'Didi Chuxing', english: 'DiDi Rides', source: 'Alipay', amount: 32.4, suggestion: 'Transport' },
  { id: 'familymart', date: '09-02', original: 'Quanjia', english: 'FamilyMart', source: 'WeChat Pay', amount: 27.9, unsure: ['Groceries', 'Food'] },
  { id: 'meituan', date: '09-03', original: 'Meituan Waimai', english: 'Meituan Delivery', source: 'WeChat Pay', amount: 46.8, suggestion: 'Food' },
  { id: 'metro', date: '09-03', original: 'Shanghai Ditie', english: 'Shanghai Metro', source: 'Alipay', amount: 4, suggestion: 'Transport' },
  { id: 'wanda', date: '09-04', original: 'Wanda Yingcheng', english: 'Wanda Cinema', source: 'Alipay', amount: 79, unsure: ['Entertainment', 'Shopping'] },
  { id: 'hema', date: '09-05', original: 'Hema Xiansheng', english: 'Hema Fresh', source: 'Alipay', amount: 212.6, suggestion: 'Groceries' },
];

/** Illustrative CNY → home rates for the currency demo (not live). */
export const ILLUSTRATIVE_RATES = {
  USD: 0.1388,
  EUR: 0.119,
  GBP: 0.1035,
} as const;

/** Sample month for the cash-flow teaser (CNY). */
export const SAMPLE_CASHFLOW = {
  income: 18000, // salary
  transfersIn: 1260, // red packets received + AA split-bill paybacks
  spend: 12480,
  transfersOut: 1600, // red packets sent + transfers to friends
  ownAccount: 3000, // card repayment / wallet top-ups between your own accounts
} as const;
