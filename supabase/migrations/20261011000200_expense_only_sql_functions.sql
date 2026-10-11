-- API v5 §3.11: "spend" is always kind = 'expense' (refunds netted, they are
-- negative expense rows). Income and transfer rows (20261011000100) must
-- never leak into a spend total, so every spend function below gets a
-- `kind = 'expense'` filter. Bodies are copied from the latest migration
-- that defined each one; only the filter is new.
--
-- CREATE OR REPLACE keeps each function's existing EXECUTE grants, but it
-- resets per-function settings, so `SET search_path = public` (added by
-- ALTER FUNCTION in 20260927020000) is restated on every function.
--
-- available_months_for_user is deliberately NOT replaced: it counts rows of
-- every kind, so a month with only a salary row is still selectable.

-- From 20260811090000_transaction_sum_rpcs.sql (summary total, savings).
CREATE OR REPLACE FUNCTION public.sum_user_transactions(
  p_user_id uuid,
  p_start timestamptz DEFAULT NULL,
  p_end timestamptz DEFAULT NULL
) RETURNS numeric
LANGUAGE sql STABLE
SET search_path = public
AS $$
  SELECT COALESCE(SUM(amount), 0)
  FROM transactions
  WHERE user_id = p_user_id
    AND kind = 'expense'
    AND (p_start IS NULL OR "timestamp" >= p_start)
    AND (p_end IS NULL OR "timestamp" < p_end);
$$;

-- From 20260811090000_transaction_sum_rpcs.sql (savings 3-month average).
CREATE OR REPLACE FUNCTION public.monthly_spend_by_user(
  p_user_id uuid,
  p_start timestamptz,
  p_end timestamptz
) RETURNS TABLE(month date, total numeric)
LANGUAGE sql STABLE
SET search_path = public
AS $$
  SELECT date_trunc('month', "timestamp")::date AS month, SUM(amount) AS total
  FROM transactions
  WHERE user_id = p_user_id
    AND kind = 'expense'
    AND "timestamp" >= p_start
    AND "timestamp" < p_end
  GROUP BY 1
  ORDER BY 1;
$$;

-- From 20260814000000_add_transaction_splits.sql (by-category, budget,
-- 50/30/20, action crossings, alerts). Both branches filter: split
-- line-items take their kind from the parent transaction.
CREATE OR REPLACE FUNCTION public.spend_by_category_for_user(
  p_user_id uuid,
  p_start timestamptz DEFAULT NULL,
  p_end timestamptz DEFAULT NULL
) RETURNS TABLE(category_id uuid, category_name text, amount numeric, txn_count bigint)
LANGUAGE sql STABLE
SET search_path = public
AS $$
  WITH contributions AS (
    SELECT t.category_id AS category_id, t.amount AS amount
    FROM transactions t
    WHERE t.user_id = p_user_id
      AND t.kind = 'expense'
      AND t.is_split = false
      AND t.category_id IS NOT NULL
      AND (p_start IS NULL OR t."timestamp" >= p_start)
      AND (p_end IS NULL OR t."timestamp" < p_end)
    UNION ALL
    SELECT s.category_id AS category_id, s.amount AS amount
    FROM transaction_splits s
    JOIN transactions t ON t.id = s.transaction_id
    WHERE s.user_id = p_user_id
      AND t.kind = 'expense'
      AND (p_start IS NULL OR t."timestamp" >= p_start)
      AND (p_end IS NULL OR t."timestamp" < p_end)
  )
  SELECT c.category_id, cat.name AS category_name, SUM(c.amount) AS amount, COUNT(*) AS txn_count
  FROM contributions c
  JOIN categories cat ON cat.id = c.category_id
  GROUP BY c.category_id, cat.name;
$$;

-- From 20260927020000_dashboard_aggregate_rpcs.sql (Overview trend chart).
CREATE OR REPLACE FUNCTION public.spend_trend_for_user(
  p_user_id uuid,
  p_start timestamptz,
  p_granularity text DEFAULT 'day'
) RETURNS TABLE(bucket text, total numeric)
LANGUAGE sql STABLE
SET search_path = public
AS $$
  SELECT to_char("timestamp" AT TIME ZONE 'UTC',
                 CASE WHEN p_granularity = 'month' THEN 'YYYY-MM' ELSE 'YYYY-MM-DD' END) AS bucket,
         SUM(amount) AS total
  FROM transactions
  WHERE user_id = p_user_id
    AND kind = 'expense'
    AND (category_id IS NOT NULL OR is_split)
    AND "timestamp" >= p_start
  GROUP BY 1
  ORDER BY 1;
$$;

-- ── New in v5 ──────────────────────────────────────────────────────────────
-- Home-currency amounts are converted in Python with one rate per calendar
-- day, so the backend only needs per-DAY sums (Σ amount × rate(day) is
-- exactly Σ per-row amount × rate). Days use the same
-- ("timestamp" AT TIME ZONE 'UTC')::date the other functions use.
--
-- Each flow column is NULL (not 0) on a day with no rows of that flow, so
-- the backend can tell "no contributing rows" (no rate needed) from rows
-- that net to zero.

-- Per-day cash flow (summary month income/home totals, trends home totals,
-- GET /dashboard/cashflow). Own-account subtypes are kept out of
-- transfers_in/out and summed as absolute amounts into own_account_moved.
CREATE OR REPLACE FUNCTION public.daily_flows_for_user(
  p_user_id uuid,
  p_start timestamptz DEFAULT NULL,
  p_end timestamptz DEFAULT NULL
) RETURNS TABLE(
  day date,
  spend numeric,
  categorized_spend numeric,
  income numeric,
  transfers_in numeric,
  transfers_out numeric,
  own_account_moved numeric
)
LANGUAGE sql STABLE
SET search_path = public
AS $$
  WITH flows AS (
    SELECT ("timestamp" AT TIME ZONE 'UTC')::date AS day,
           kind,
           amount,
           (category_id IS NOT NULL OR is_split) AS categorized,
           COALESCE(flow_subtype IN ('own_account', 'repayment', 'top_up', 'withdrawal'), false) AS own_account
    FROM transactions
    WHERE user_id = p_user_id
      AND (p_start IS NULL OR "timestamp" >= p_start)
      AND (p_end IS NULL OR "timestamp" < p_end)
  )
  SELECT day,
         SUM(amount) FILTER (WHERE kind = 'expense') AS spend,
         -- Same row filter as spend_trend_for_user (categorized or split).
         SUM(amount) FILTER (WHERE kind = 'expense' AND categorized) AS categorized_spend,
         SUM(amount) FILTER (WHERE kind = 'income') AS income,
         SUM(-amount) FILTER (WHERE kind = 'transfer' AND NOT own_account AND amount < 0) AS transfers_in,
         SUM(amount) FILTER (WHERE kind = 'transfer' AND NOT own_account AND amount > 0) AS transfers_out,
         SUM(abs(amount)) FILTER (WHERE kind = 'transfer' AND own_account) AS own_account_moved
  FROM flows
  GROUP BY day
  ORDER BY day;
$$;

-- Per-day spend per category in a window (budget home amounts: every
-- line-item converts at its own day's rate; split line-items use their
-- parent transaction's day). Same contributions as
-- spend_by_category_for_user.
CREATE OR REPLACE FUNCTION public.spend_by_category_daily_for_user(
  p_user_id uuid,
  p_start timestamptz,
  p_end timestamptz
) RETURNS TABLE(category_id uuid, category_name text, day date, amount numeric)
LANGUAGE sql STABLE
SET search_path = public
AS $$
  WITH contributions AS (
    SELECT t.category_id AS category_id, t."timestamp" AS ts, t.amount AS amount
    FROM transactions t
    WHERE t.user_id = p_user_id
      AND t.kind = 'expense'
      AND t.is_split = false
      AND t.category_id IS NOT NULL
      AND t."timestamp" >= p_start
      AND t."timestamp" < p_end
    UNION ALL
    SELECT s.category_id AS category_id, t."timestamp" AS ts, s.amount AS amount
    FROM transaction_splits s
    JOIN transactions t ON t.id = s.transaction_id
    WHERE s.user_id = p_user_id
      AND t.kind = 'expense'
      AND t."timestamp" >= p_start
      AND t."timestamp" < p_end
  )
  SELECT c.category_id, cat.name AS category_name, (c.ts AT TIME ZONE 'UTC')::date AS day,
         SUM(c.amount) AS amount
  FROM contributions c
  JOIN categories cat ON cat.id = c.category_id
  GROUP BY c.category_id, cat.name, 3
  ORDER BY 3, c.category_id;
$$;

-- Backend-only, like the other aggregate RPCs (service-role key).
REVOKE EXECUTE ON FUNCTION public.daily_flows_for_user(uuid, timestamptz, timestamptz) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.spend_by_category_daily_for_user(uuid, timestamptz, timestamptz) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.daily_flows_for_user(uuid, timestamptz, timestamptz) TO service_role;
GRANT EXECUTE ON FUNCTION public.spend_by_category_daily_for_user(uuid, timestamptz, timestamptz) TO service_role;
