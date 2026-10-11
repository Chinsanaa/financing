# API v5 contract — cash flow, home currency, bank import

Status: **FROZEN** (2026-10-11). Backend implements exactly this; frontend
codes against `frontend/src/types/v5.ts` and the typed helpers in
`frontend/src/utils/api.ts`. Any change needs a contract edit first.

Base: v4 API as of `origin/main` 106ec73. Everything not mentioned here is
unchanged. All changes are **additive** to response shapes: no v4 field is
removed, renamed or re-typed, so v4 clients keep working.

---

## 0. Global conventions

| Topic | Rule |
|---|---|
| Base currency | Every money field without a suffix is **CNY**. |
| Home fields | `*_home` = same value in the user's home currency, or `null` (no home currency set, or no usable rate). The UI hides the "≈" line on `null`. |
| Rounding | All money in responses is rounded to **2 decimals** (half-even is fine, Python `round`). Aggregates are summed from unrounded values and rounded once at the end. Rates are returned unrounded (as stored, ≤ 6 decimals). |
| Time zone | Transaction timestamps are naive **China time (Asia/Shanghai)**. "Today", month boundaries and the date used for an FX lookup are all China-time calendar dates (use `_now_cn()` in `backend/routes/dashboard.py`). |
| Months | `"YYYY-MM"`. Dates `"YYYY-MM-DD"`. |
| "Spend" | **Always** `kind = 'expense'` only, refunds netted (refunds are negative expense rows). |
| Errors | FastAPI shape `{"detail": "..."}` (422 validation errors keep FastAPI's list shape). |

---

## 1. Data model (migration owned by the backend/DB agent)

### 1.1 `transactions`

```sql
CREATE TYPE transaction_kind AS ENUM ('expense', 'income', 'transfer');
ALTER TABLE transactions
  ADD COLUMN kind transaction_kind NOT NULL DEFAULT 'expense',
  ADD COLUMN flow_subtype text NULL CHECK (flow_subtype IN (
    'refund','red_packet','p2p_transfer','aa_collection','salary','interest',
    'own_account','repayment','top_up','withdrawal','other'));
ALTER TYPE transaction_source ADD VALUE 'bank';
CREATE INDEX ON transactions (user_id, kind, timestamp);
```

Backfill: every existing row is `kind='expense'` (the v1 parser only ever
kept expense and refund rows). Rows with `amount < 0` get
`flow_subtype='refund'`; others stay `NULL`.

#### Kind / subtype semantics

| kind | flow_subtype | Meaning | Amount sign | Counted as |
|---|---|---|---|---|
| expense | `NULL` | A purchase / payment | `+` | spend |
| expense | `refund` | Refund of a purchase (退款) | `−` | spend (nets out) |
| income | `salary` | Payroll / wages | `+` (money in) | income |
| income | `interest` | Interest, Yu'e Bao / 余额宝 earnings | `+` | income |
| income | `other` | Other income (e.g. 收入 rows not matched above) | `+` | income |
| transfer | `p2p_transfer` | Transfer to/from a person (转账) | `+` out / `−` in | transfers_out / transfers_in |
| transfer | `red_packet` | Red packet sent/received (红包) | `+` sent / `−` received | transfers_out / transfers_in |
| transfer | `aa_collection` | Split-bill collection (AA收款), friends paying you back | `−` (money in) | transfers_in |
| transfer | `other` | Unclassified transfer | `+` out / `−` in | transfers_out / transfers_in |
| transfer | `own_account` | Between the user's own accounts/cards | `+` out / `−` in | own_account_moved |
| transfer | `repayment` | Credit card / Huabei (花呗) repayment | `+` | own_account_moved |
| transfer | `top_up` | Bank → wallet top-up (充值) | `−` (into wallet) | own_account_moved |
| transfer | `withdrawal` | Wallet → bank withdrawal (提现) | `+` | own_account_moved |

Sign rule in one line: **for expense and transfer rows `+` = money left the
user, `−` = money came in; income rows are always `+` (money in).** A
negative income row (reversal) is allowed and simply reduces income.

Allowed (kind, subtype) pairs are exactly the table above
(`SUBTYPES_BY_KIND` in `types/v5.ts`); `NULL` subtype is allowed for every
kind. "Own-account subtypes" = `own_account, repayment, top_up, withdrawal`.

Non-expense rows (`income`, `transfer`):
- are inserted with `category_id = NULL`, `needs_review = false`,
  `label_source = 'none'`, `is_split = false`;
- are never classified by the ML pipeline, never appear in the review
  queue, never count toward labeling %, budgets, subscriptions detection,
  insights or alerts.

### 1.2 `profiles`

```sql
ALTER TABLE profiles ADD COLUMN home_currency char(3) NULL;  -- upper-case ISO 4217, never 'CNY'
```

### 1.3 `fx_rates`

```sql
CREATE TABLE fx_rates (
  rate_date date        NOT NULL,          -- ECB reference date
  quote     char(3)     NOT NULL,          -- e.g. 'USD'
  rate      numeric(18,8) NOT NULL,        -- units of `quote` per 1 CNY
  fetched_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (quote, rate_date)
);
-- Global reference data: RLS on, SELECT for authenticated, writes only via service role.
```

Source: Frankfurter (`https://api.frankfurter.dev/v1/{start}..{end}?base=CNY&symbols=XXX`
or the `.app` host), which republishes ECB reference rates (business days only,
~16:00 CET).

### 1.4 `uploads`

```sql
ALTER TABLE uploads ADD COLUMN parser_version smallint NOT NULL DEFAULT 1;
```
Existing rows stay `1`. Every upload created by v5 is written with `2`.

---

## 2. FX rules

**Rate lookup for a transaction** (date `d` = China-time calendar date of
`timestamp`): the row in `fx_rates` for the home currency with the greatest
`rate_date ≤ d` **and** `rate_date ≥ d − 7 days`. None → no rate →
`amount_home = null`.

**Per-row conversion:** `amount_home = round(amount × rate, 2)`.

**Aggregates** (`total_spend_home`, monthly sums, …): sum of
`amount × rate(row date)` over the contributing rows, rounded once. If **any**
contributing row has no rate the aggregate is `null` (never a partial sum).
An aggregate over zero rows is `0` (not null) when a home currency is set.

**Budget amounts** (not dated): converted at the **reference rate** of the
month = lookup with `d = min(last day of month, today)`.

**`rate_asof` / `rate`** (summary): newest `fx_rates` row for the home
currency with `rate_date ≤ today`; `null`/`null` if none.

**Fetching / caching (backend):**
- When `home_currency` is set (PATCH), synchronously backfill rates from
  `min(transaction date) − 7 days` (or today − 400 days if no transactions)
  to today for that quote in one Frankfurter time-series call; if
  Frankfurter fails, the PATCH still succeeds (home fields read `null`
  until a later refresh).
- On every request that needs home fields, if the newest stored rate is
  older than 1 calendar day (China time) refresh at most once per
  6 hours per currency (in-process throttle), best-effort, never blocking
  the response for more than ~3 s; on failure serve what is cached.
- Uploads that add rows older than the earliest cached rate trigger a
  background backfill for the user's home currency.

---

## 3. Endpoints

Unchanged paths are listed only if their response changes.
`currency_home` = the user's `profiles.home_currency` (or `null`).

### 3.1 `GET /fx/currencies` (new; auth required like every route)

```json
{
  "base": "CNY",
  "source": "European Central Bank via Frankfurter",
  "supported": [{ "code": "USD", "name": "US Dollar" }, ...]
}
```

`supported` (this order — most likely home currencies first):

| code | name | code | name | code | name |
|---|---|---|---|---|---|
| USD | US Dollar | EUR | Euro | GBP | British Pound |
| AUD | Australian Dollar | CAD | Canadian Dollar | JPY | Japanese Yen |
| KRW | South Korean Won | SGD | Singapore Dollar | HKD | Hong Kong Dollar |
| CHF | Swiss Franc | NZD | New Zealand Dollar | SEK | Swedish Krona |
| NOK | Norwegian Krone | DKK | Danish Krone | PLN | Polish Zloty |
| CZK | Czech Koruna | HUF | Hungarian Forint | INR | Indian Rupee |
| IDR | Indonesian Rupiah | MYR | Malaysian Ringgit | PHP | Philippine Peso |
| THB | Thai Baht | ZAR | South African Rand | BRL | Brazilian Real |
| MXN | Mexican Peso | ILS | Israeli New Shekel | TRY | Turkish Lira |
| ISK | Icelandic Krona | RON | Romanian Leu | | |

29 codes. **BGN is deliberately excluded**: Bulgaria joined the euro on
2026-01-01 and the ECB no longer publishes a BGN reference rate. CNY is the
base and is not selectable. Static list (a backend constant); no DB read.

### 3.2 `GET /settings/profile` / `PATCH /settings/profile` (changed)

`profile` gains `home_currency: string | null`.

PATCH body gains `home_currency?: string | null`:
- trimmed + upper-cased, then must be in the supported list →
  stored; triggers the FX backfill (§2).
- `null` → cleared (CNY only; all `*_home` become `null`).
- `"CNY"` → **422** `{"detail": "CNY is the base currency; clear home_currency with null instead"}`.
- anything else → **422** `{"detail": "Unsupported home currency 'XYZ'. See GET /fx/currencies."}`.
- Omitting the field leaves it untouched. `{}` is still 400 "No fields to update".

Response: `{"profile": {...}}` (full row, as today).

### 3.3 `GET /dashboard/summary` (changed)

```jsonc
{
  "total_transactions": 1284,      // v4: ALL kinds counted (it's a row count)
  "labeled_transactions": 1093,    // v4 semantics, expense rows only
  "labeling_percentage": 85.1,     // labeled / expense-row count
  "total_spend": 141400.5,         // all-time spend (expense only)
  "monthly_income": 18000,         // unchanged: profiles.monthly_income, 0 if unset
  "month": "2026-09",              // NEW: current China-time month
  "month_spend": 12480.0,          // NEW: spend in `month`
  "month_income": 18012.84,        // NEW: see rule below, may be null
  "month_income_source": "statements", // NEW: 'statements' | 'settings' | null
  "home": {                        // NEW: null when no home currency
    "currency": "USD",
    "total_spend_home": 19694.62,
    "month_spend_home": 1730.98,
    "month_income_home": 2498.38,
    "rate_asof": "2026-09-30",
    "rate": 0.1387
  }
}
```

Change vs v4: `labeling_percentage` denominator becomes expense rows only
(income/transfer rows are never labeled). `total_transactions` stays the
count of all rows (it is shown as "transactions imported").

`month_income` rule: sum of `kind='income'` amounts in `month`; if that sum
is non-zero → `source='statements'`; else if `profiles.monthly_income > 0` →
that value, `source='settings'`; else `null` / `null`.
`month_income_home`: statements → per-row conversion; settings → converted at
the month reference rate; `null` when `month_income` is `null`.

### 3.4 `GET /dashboard/trends` (changed)

Query unchanged (`granularity=day|month`, `days`, `months`). Expense only
(as before). Response:

```json
{ "currency_home": "USD",
  "trends": [{ "date": "2026-09", "total_spend": 12480.0, "total_spend_home": 1730.98 }] }
```
`total_spend_home` is `null` when no home currency or any row in the bucket
lacks a rate.

### 3.5 `GET /dashboard/cashflow?months=12` (new)

`months`: int, default 12, clamped to `1..36`. Window = the `months`
calendar months ending with the current China-time month (same window as
`trends?granularity=month`).

```jsonc
{
  "currency_home": "USD",          // or null
  "months": [                      // oldest → newest, exactly `months` items, zero-filled
    {
      "month": "2026-09",
      "spend": 12480.0,            // Σ amount, kind='expense' (refunds netted)
      "income": 18012.84,          // Σ amount, kind='income'
      "transfers_in": 260.0,       // Σ |amount| of kind='transfer', amount<0, subtype NOT own-account
      "transfers_out": 4588.8,     // Σ amount   of kind='transfer', amount>0, subtype NOT own-account
      "net": 5532.84,              // income − spend   (transfers EXCLUDED)
      "spend_home": 1730.98,       // null if no home currency / missing rate
      "income_home": 2498.38,
      "net_home": 767.4            // income_home − spend_home (computed unrounded), null if either is null
    }
  ],
  "own_account_moved": 26400.0     // Σ |amount| of transfer rows with an own-account subtype in the whole window
}
```

- Months with no rows: all CNY numbers `0`, home numbers `0` (or `null`
  without a home currency).
- `income` comes only from statements (never from `profiles.monthly_income`).
- Transfers with `flow_subtype = NULL` count like `other` (in/out by sign).
- No category/split logic: amounts come from `transactions.amount` directly.

### 3.6 `GET /dashboard/budget?month=YYYY-MM` (changed)

Spend is expense-only (as before). Each `category_budgets[]` row gains
`monthly_budget_home`, `current_spend_home` (number | null). Top level gains:

```json
{ "total_budget": 11600.0, "total_spent": 10822.0,
  "currency_home": "USD", "total_budget_home": 1608.92, "total_spent_home": 1501.01 }
```
`total_budget` = Σ `category_budgets[].monthly_budget`; `total_spent` = Σ
`category_budgets[].current_spend` (budgeted categories only — same numbers
BudgetTab computes today). Both `0` when there are no category budgets.
`*_spent_home`/`current_spend_home`: per-transaction rates (split line-items
use their parent transaction's date). `*_budget_home`: month reference
rate. All home fields `null` without a home currency.

### 3.7 `GET /dashboard/reports` (changed)

New query param `kind`: `expense | income | transfer | all`, default
**`expense`** (so the v4 Reports tab is unchanged). Unrecognized → `expense`.
Category/bucket/uncategorized filters only match expense rows (a
`category_id`/`bucket`/`uncategorized_only=true` filter combined with
`kind=income|transfer` returns an empty page; with `kind=all` it implicitly
restricts to expense rows). `min_amount`/`max_amount` compare the signed
stored amount.

Each row gains:

| field | type | notes |
|---|---|---|
| `kind` | `'expense'\|'income'\|'transfer'` | |
| `flow_subtype` | string \| null | |
| `source` | `'alipay'\|'wechat'\|'manual'\|'bank'` | |
| `amount_home` | number \| null | per-row conversion |

For non-expense rows: `category` = `"Income"` or `"Transfer"`, `category_id`
= `null`, `bucket` = `null`, `is_split` = `false`. Response top level gains
`kind` (the applied filter) and `currency_home`.

### 3.8 `PATCH /transactions/{id}/kind` (new)

Lets the user fix a parser misjudgement, e.g. rent paid by WeChat transfer
(`transfer` → `expense`) or a refund that is really income.

Body: `{"kind": "expense"|"income"|"transfer", "flow_subtype": <subtype>|null}`
(`flow_subtype` optional → `null`).
- Pair must be allowed (§1.1) → else 422.
- Not the caller's row → 404 `Transaction not found`.
- Row `is_split = true` and new kind ≠ expense → 409
  `"Unsplit this transaction before changing its kind"`.
- → `income`/`transfer`: set `category_id=NULL`, `needs_review=false`,
  `label_source='none'`, `confidence=NULL`.
- → `expense` from another kind: `needs_review=true`, `label_source='none'`
  (lands in the review queue and is classified on the next pass).
- Amount is never changed. Rate limit 120/hour.

Response: `{"transaction": {"id", "kind", "flow_subtype", "category_id", "needs_review"}}`.

### 3.9 `POST /uploads/` (changed)

- Accepted sources: `alipay`, `wechat`, **`bank`** (generic bank CSV/XLSX,
  parsed by `src/parse.py::parse_generic_bank_csv` or its successor).
  Detection order: WeChat markers → Alipay markers → bank (has a
  recognisable date column **and** an amount or debit/credit column).
  Undetected → 400 `"Could not detect file source. Expected an Alipay, WeChat or bank statement export."`
- v5 parser (version 2) keeps **all** settled rows and assigns
  `kind`/`flow_subtype` per §1.1. Expense and refund rows must produce
  exactly the same `(timestamp, merchant, description, amount)` as v1 so
  row-level dedup still matches previously imported rows.
- Bank rows whose counterparty is a payment wallet (支付宝 / Alipay,
  财付通 / Tenpay / 微信支付 / WeChat Pay) are imported as
  `kind='transfer', flow_subtype='own_account'` so the same purchase isn't
  counted twice (it is already in the Alipay/WeChat statement).
- Dedup key unchanged (`timestamp, merchant, description, amount, source`).
- **Re-uploading a parser-v1 file** (same file hash as an existing upload
  with `parser_version = 1` and status ≠ failed): no 409. The file is
  re-parsed, dedup skips every row already present (all its expense/refund
  rows), and only the new non-expense rows are inserted **under the existing
  upload's id**. That upload row is then updated to `parser_version = 2`,
  `row_count += inserted`. Response `upload_id` is the existing id and
  `reimported: true`. A hash match on a `parser_version = 2` upload is still
  409 as before.

Response (added fields marked):
```jsonc
{ "upload_id": "…", "file_name": "…", "file_type": "bank", "status": "parsed",
  "message": "Imported 41 transactions (3 income, 9 transfers). Categorization is running.",
  "rows_imported": 41, "rows_skipped": 0,
  "reimported": false,                                       // NEW
  "rows_by_kind": { "expense": 29, "income": 3, "transfer": 9 } }  // NEW (imported rows only)
```

`GET /uploads/` and `GET /uploads/{id}`: unchanged fields; rows now also
carry `parser_version` and `file_type` may be `'bank'`.

### 3.10 `GET /dashboard/export` (changed)

XLSX now contains **all kinds**. Columns:

`Date | Merchant | Description | Category | Kind | Amount | Home amount | Home currency | Label Source`

- `Kind`: `Expense` / `Income` / `Transfer`, plus ` (Refund)`, ` (Salary)` …
  using the English labels in `FLOW_SUBTYPE_LABELS` when a subtype is set,
  e.g. `Transfer (Red packet)`.
- `Category` for non-expense rows: empty string.
- `Home amount`: number (`#,##0.00`) or empty cell when null.
- `Home currency`: the code, or empty when no home currency.

### 3.11 Expense-only endpoints (semantics clarified, shapes unchanged)

Add `kind = 'expense'` to every query/RPC behind:
`/dashboard/by-category`, `/dashboard/rule-503020`, `/dashboard/savings`,
`/dashboard/insights`, `/dashboard/action` (budget crossings), alerts,
`/dashboard/review-queue`, `/subscriptions/*` detection, `/classify/*`,
`/training/*` (training set), `available_months_for_user` (months that have
**any** row — so a salary-only month is selectable). The SQL RPCs
`sum_user_transactions`, `spend_by_category_for_user`,
`spend_trend_for_user`, `spend_by_category_in_range` must filter
`kind = 'expense'`.

`POST /transactions/` (manual entry) stays expense-only; it writes
`kind='expense'` implicitly via the column default.

---

## 4. Edge cases

| Case | Behaviour |
|---|---|
| No home currency | every `*_home` = `null`, `home` = `null`, `currency_home` = `null`. |
| Home currency set, Frankfurter never reachable | `home` object present, `rate_asof`/`rate` `null`, home amounts `null`. |
| Transaction on a weekend/holiday | uses the previous business day's rate (≤ 7 days back). |
| Transaction older than the cache | `null` until backfill fills it (aggregates containing it are `null`). |
| Home currency changed | home fields switch immediately; nothing stored per transaction (always computed). |
| Refund in a month with no purchases | negative `spend` for that month is allowed. |
| Negative `net` | allowed. |
| `months` < 1 or > 36 | clamped. |
| Old (v1) user who never re-uploads | all rows expense: income = 0, `month_income` falls back to settings. |

## 5. Frontend contract helpers

- Types: `frontend/src/types/v5.ts`.
- Requests: `api.dashboard.{summary,trends,cashflow,budget,reports}`,
  `api.fx.currencies`, `api.settings.{getProfile,updateProfile,setHomeCurrency}`,
  `api.transactionKind.update`, `api.uploadsV5.*`; `api.paths.*` builds the
  same URLs for `useApi()`.
- Display: `formatHomeCurrency(value, currency, decimals?)` in
  `utils/format.ts`; `<MoneyPair cny home size inline decimals />` in
  `components/ui/MoneyPair.tsx` (hides the "≈" line when home is null).
- Mocks: `frontend/scripts/ui-snapshots.cjs` serves every endpoint above
  (home currency USD @ 0.1387).
