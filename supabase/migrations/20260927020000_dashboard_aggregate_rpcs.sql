-- Dashboard aggregates computed in Postgres instead of paging every row to
-- the backend (1,000 rows per round trip) and grouping in pandas.
--
-- Buckets use `"timestamp" AT TIME ZONE 'UTC'`: timestamps hold the China
-- wall-clock time from the Alipay/WeChat export stored as UTC, and the old
-- pandas code bucketed the ISO strings PostgREST returns (UTC offset) — this
-- matches it exactly regardless of the session's TimeZone setting.

-- Distinct 'YYYY-MM' months that have transactions, newest first
-- (month selector on Budget / 50-30-20; was a full-history fetch per load).
CREATE OR REPLACE FUNCTION public.available_months_for_user(p_user_id uuid)
RETURNS SETOF text
LANGUAGE sql STABLE
SET search_path = public
AS $$
  SELECT DISTINCT to_char("timestamp" AT TIME ZONE 'UTC', 'YYYY-MM') AS month
  FROM transactions
  WHERE user_id = p_user_id
  ORDER BY 1 DESC;
$$;

-- Spend per day ('YYYY-MM-DD') or month ('YYYY-MM') since p_start, for the
-- Overview trend chart. Same row filter as the old route: categorized rows
-- plus split parents (whose whole amount counts once).
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
    AND (category_id IS NOT NULL OR is_split)
    AND "timestamp" >= p_start
  GROUP BY 1
  ORDER BY 1;
$$;

-- Backend calls these with the service-role key (like every other RPC here);
-- no reason for anon/authenticated to call them directly via PostgREST.
REVOKE EXECUTE ON FUNCTION public.available_months_for_user(uuid) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.spend_trend_for_user(uuid, timestamptz, text) FROM PUBLIC, anon, authenticated;

-- Security-advisor fix (lint 0011) for the existing aggregate RPCs.
ALTER FUNCTION public.sum_user_transactions(uuid, timestamptz, timestamptz) SET search_path = public;
ALTER FUNCTION public.monthly_spend_by_user(uuid, timestamptz, timestamptz) SET search_path = public;
ALTER FUNCTION public.spend_by_category_for_user(uuid, timestamptz, timestamptz) SET search_path = public;

-- English display name for detected subscriptions (raw merchant text can be
-- Chinese; filled from transactions.merchant_en at detection time).
ALTER TABLE public.recurring_merchants ADD COLUMN IF NOT EXISTS merchant_en text;
