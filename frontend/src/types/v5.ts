/**
 * API v5 types — the frozen contract in docs/contracts/API_V5.md.
 *
 * v5 adds three things on top of the existing (CNY-only, spend-only) API:
 *   1. Transaction kinds (expense / income / transfer) and cash flow.
 *   2. An optional home currency with ECB reference rates (via Frankfurter).
 *   3. A generic bank-statement upload source.
 *
 * Conventions (see the contract for the full rules):
 * - Every money field without a suffix is CNY. `*_home` fields are the same
 *   value converted to the user's home currency, or `null` when the user has
 *   no home currency or no rate exists (UI then hides the "≈" line).
 * - Money is rounded to 2 decimals server-side.
 * - Months are "YYYY-MM" and dates are China time (Asia/Shanghai).
 */

// ── Transaction kinds ───────────────────────────────────────────────────────

export type TransactionKind = 'expense' | 'income' | 'transfer';

/** Reports `kind` filter. `all` returns every kind. */
export type KindFilter = TransactionKind | 'all';

export type FlowSubtype =
  | 'refund'
  | 'red_packet'
  | 'p2p_transfer'
  | 'aa_collection'
  | 'salary'
  | 'interest'
  | 'own_account'
  | 'repayment'
  | 'top_up'
  | 'withdrawal'
  | 'other';

/** Which subtypes are valid for which kind (null subtype is always valid). */
export const SUBTYPES_BY_KIND: Record<TransactionKind, readonly FlowSubtype[]> = {
  expense: ['refund'],
  income: ['salary', 'interest', 'other'],
  transfer: [
    'p2p_transfer',
    'red_packet',
    'aa_collection',
    'own_account',
    'repayment',
    'top_up',
    'withdrawal',
    'other',
  ],
};

/** Transfer subtypes that move money between the user's OWN accounts. They
 *  are reported as `own_account_moved`, never as transfers in/out. */
export const OWN_ACCOUNT_SUBTYPES: readonly FlowSubtype[] = ['own_account', 'repayment', 'top_up', 'withdrawal'];

/** English display labels for kinds and subtypes. */
export const KIND_LABELS: Record<TransactionKind, string> = {
  expense: 'Expense',
  income: 'Income',
  transfer: 'Transfer',
};

export const FLOW_SUBTYPE_LABELS: Record<FlowSubtype, string> = {
  refund: 'Refund',
  red_packet: 'Red packet',
  p2p_transfer: 'Transfer to/from a person',
  aa_collection: 'Split-bill collection',
  salary: 'Salary',
  interest: 'Interest',
  own_account: 'Between own accounts',
  repayment: 'Credit repayment',
  top_up: 'Top-up',
  withdrawal: 'Withdrawal',
  other: 'Other',
};

export type TransactionSource = 'alipay' | 'wechat' | 'manual' | 'bank';

// ── FX / home currency ─────────────────────────────────────────────────────

/** ISO 4217 code, upper case, e.g. "USD". */
export type CurrencyCode = string;

export interface FxCurrency {
  code: CurrencyCode;
  name: string;
}

/** GET /fx/currencies */
export interface FxCurrenciesResponse {
  base: 'CNY';
  supported: FxCurrency[];
  source: 'European Central Bank via Frankfurter';
}

// ── Settings ───────────────────────────────────────────────────────────────

export interface Profile {
  id: string;
  username?: string | null;
  email_verified_at?: string | null;
  onboarding_phase?: string | null;
  created_at?: string;
  monthly_income: number | null;
  alert_email_enabled: boolean;
  alert_threshold_pct: number | null;
  budget_inapp_enabled: boolean;
  pending_review_inapp_enabled: boolean;
  monthly_overview_email_enabled: boolean;
  /** v5: ISO code from GET /fx/currencies, or null = CNY only. */
  home_currency: CurrencyCode | null;
  [extra: string]: unknown;
}

/** GET / PATCH /settings/profile response */
export interface ProfileResponse {
  profile: Profile;
}

/** PATCH /settings/profile body — every field optional, at least one required. */
export interface ProfileUpdate {
  monthly_income?: number | null;
  alert_email_enabled?: boolean;
  alert_threshold_pct?: number;
  budget_inapp_enabled?: boolean;
  pending_review_inapp_enabled?: boolean;
  monthly_overview_email_enabled?: boolean;
  /** v5: a supported code (case-insensitive on input, stored upper case) or
   *  null to clear. "CNY" is rejected (422) — clear with null instead. */
  home_currency?: CurrencyCode | null;
}

// ── Dashboard: summary ─────────────────────────────────────────────────────

export interface SummaryHome {
  currency: CurrencyCode;
  total_spend_home: number | null;
  month_spend_home: number | null;
  month_income_home: number | null;
  /** Newest ECB rate date available for this currency ("YYYY-MM-DD"). */
  rate_asof: string | null;
  /** CNY → home rate on `rate_asof` (1 CNY = rate home units). */
  rate: number | null;
}

export type IncomeSource = 'statements' | 'settings';

/** GET /dashboard/summary */
export interface SummaryResponse {
  total_transactions: number;
  labeled_transactions: number;
  labeling_percentage: number;
  /** All-time spend (kind='expense', refunds netted). */
  total_spend: number;
  /** profiles.monthly_income (0 when unset) — unchanged from v4. */
  monthly_income: number;
  /** v5: current China-time month, "YYYY-MM". */
  month: string;
  /** v5: spend in `month` (kind='expense', refunds netted). */
  month_spend: number;
  /** v5: income in `month` from statements if any, else the Settings value, else null. */
  month_income: number | null;
  month_income_source: IncomeSource | null;
  /** v5: null when the user has no home currency. */
  home: SummaryHome | null;
}

// ── Dashboard: trends ──────────────────────────────────────────────────────

export interface TrendPoint {
  /** "YYYY-MM-DD" (granularity=day) or "YYYY-MM" (granularity=month). */
  date: string;
  total_spend: number;
  /** v5: null without a home currency or when any row in the bucket has no rate. */
  total_spend_home: number | null;
}

/** GET /dashboard/trends */
export interface TrendsResponse {
  trends: TrendPoint[];
  /** v5 */
  currency_home: CurrencyCode | null;
}

// ── Dashboard: cash flow ───────────────────────────────────────────────────

export interface CashflowMonth {
  month: string;
  spend: number;
  income: number;
  transfers_in: number;
  transfers_out: number;
  /** income − spend (transfers excluded). */
  net: number;
  spend_home: number | null;
  income_home: number | null;
  net_home: number | null;
}

/** GET /dashboard/cashflow?months=12 */
export interface CashflowResponse {
  currency_home: CurrencyCode | null;
  /** Oldest first, exactly `months` entries (zero-filled), current month last. */
  months: CashflowMonth[];
  /** Sum of |amount| of own-account transfer rows in the window (CNY). */
  own_account_moved: number;
}

// ── Dashboard: budget ──────────────────────────────────────────────────────

export interface CategoryBudget {
  category: string;
  monthly_budget: number;
  current_spend: number;
  type: 'Need' | 'Want' | 'Savings' | string;
  /** v5 */
  monthly_budget_home: number | null;
  /** v5 */
  current_spend_home: number | null;
}

/** GET /dashboard/budget?month=YYYY-MM */
export interface BudgetResponse {
  budget_config: { monthly_income: number; currency: string };
  category_budgets: CategoryBudget[];
  month: string;
  available_months: string[];
  /** v5: sum of category_budgets[].monthly_budget. */
  total_budget: number;
  /** v5: sum of category_budgets[].current_spend. */
  total_spent: number;
  /** v5 */
  currency_home: CurrencyCode | null;
  total_budget_home: number | null;
  total_spent_home: number | null;
}

// ── Dashboard: reports ─────────────────────────────────────────────────────

export interface ReportSplit {
  category_id: string;
  category_name: string;
  amount: number;
}

export interface ReportRow {
  id: string;
  date: string;
  merchant: string;
  description: string;
  amount: number;
  category: string;
  category_id: string | null;
  is_split: boolean;
  splits: ReportSplit[] | null;
  label_source: string;
  bucket: 'Need' | 'Want' | 'Savings' | null;
  /** v5 */
  kind: TransactionKind;
  flow_subtype: FlowSubtype | null;
  source: TransactionSource;
  amount_home: number | null;
}

/** GET /dashboard/reports */
export interface ReportsResponse {
  transactions: ReportRow[];
  total_count: number;
  page: number;
  per_page: number;
  /** v5: echo of the applied kind filter. */
  kind: KindFilter;
  currency_home: CurrencyCode | null;
}

export interface ReportsQuery {
  page?: number;
  per_page?: number;
  uncategorized_only?: boolean;
  category_id?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  min_amount?: number;
  max_amount?: number;
  sort_by?: 'date' | 'category';
  sort_dir?: 'asc' | 'desc';
  bucket?: 'Need' | 'Want' | 'Savings';
  /** v5, default 'expense'. */
  kind?: KindFilter;
}

// ── Transactions ───────────────────────────────────────────────────────────

/** PATCH /transactions/{id}/kind body */
export interface TransactionKindUpdate {
  kind: TransactionKind;
  flow_subtype?: FlowSubtype | null;
}

export interface TransactionKindResponse {
  transaction: {
    id: string;
    kind: TransactionKind;
    flow_subtype: FlowSubtype | null;
    category_id: string | null;
    needs_review: boolean;
  };
}

// ── Uploads ────────────────────────────────────────────────────────────────

export type UploadFileType = 'alipay' | 'wechat' | 'bank';

/** POST /uploads/ (201-style success, returned with HTTP 200) */
export interface UploadResult {
  upload_id: string;
  file_name: string;
  file_type: UploadFileType;
  status: 'parsed';
  message: string;
  rows_imported: number;
  rows_skipped: number;
  /** v5: true when the file had been imported by parser v1 and this upload
   *  only added its non-expense rows to the existing upload. */
  reimported: boolean;
  /** v5: imported rows per kind. */
  rows_by_kind: Record<TransactionKind, number>;
}

/** Row of GET /uploads/ and GET /uploads/{id} (the uploads table). */
export interface UploadRecord {
  id: string;
  original_filename: string;
  file_type: UploadFileType | null;
  created_at: string;
  row_count: number;
  status: 'uploaded' | 'parsed' | 'failed' | string;
  error_message?: string | null;
  /** v5: 1 = expense/refund rows only; 2 = all kinds. */
  parser_version?: number;
  [extra: string]: unknown;
}

export interface UploadsListResponse {
  uploads: UploadRecord[];
}
