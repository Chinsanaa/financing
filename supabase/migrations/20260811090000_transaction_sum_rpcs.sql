-- RPCs to let Postgres aggregate transaction totals instead of the backend
-- pulling every row and summing in Python (see backend/routes/dashboard.py
-- get_summary / get_savings). Backend calls these with the service-role
-- client, same as every other table it queries, so no SECURITY DEFINER /
-- RLS bypass is needed here.

CREATE OR REPLACE FUNCTION public.sum_user_transactions(
  p_user_id uuid,
  p_start timestamptz DEFAULT NULL,
  p_end timestamptz DEFAULT NULL
) RETURNS numeric
LANGUAGE sql STABLE AS $$
  SELECT COALESCE(SUM(amount), 0)
  FROM transactions
  WHERE user_id = p_user_id
    AND (p_start IS NULL OR "timestamp" >= p_start)
    AND (p_end IS NULL OR "timestamp" < p_end);
$$;

CREATE OR REPLACE FUNCTION public.monthly_spend_by_user(
  p_user_id uuid,
  p_start timestamptz,
  p_end timestamptz
) RETURNS TABLE(month date, total numeric)
LANGUAGE sql STABLE AS $$
  SELECT date_trunc('month', "timestamp")::date AS month, SUM(amount) AS total
  FROM transactions
  WHERE user_id = p_user_id
    AND "timestamp" >= p_start
    AND "timestamp" < p_end
  GROUP BY 1
  ORDER BY 1;
$$;
