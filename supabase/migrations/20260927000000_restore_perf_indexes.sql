-- Performance: restore dropped indexes, cover unindexed FKs, fix RLS initplan.
--
-- 20260707000000_security_performance_indexing_fixes dropped
-- transactions(user_id, timestamp) and (user_id, needs_review) as "never
-- used" — judged on a near-empty database. Every dashboard query filters by
-- user_id + a timestamp range or needs_review, so they're restored here.
-- At today's size (~1.4k rows) queries already run in single-digit ms; these
-- keep it that way as uploads accumulate.

CREATE INDEX IF NOT EXISTS transactions_user_id_timestamp_idx
  ON public.transactions (user_id, timestamp);

-- Partial: only rows still awaiting review (a small, shrinking subset).
CREATE INDEX IF NOT EXISTS transactions_user_id_needs_review_idx
  ON public.transactions (user_id) WHERE needs_review;

CREATE INDEX IF NOT EXISTS transactions_user_id_category_id_idx
  ON public.transactions (user_id, category_id);

-- Unindexed foreign keys flagged by the Supabase performance advisor.
CREATE INDEX IF NOT EXISTS transaction_splits_user_id_idx
  ON public.transaction_splits (user_id);
CREATE INDEX IF NOT EXISTS transaction_splits_category_id_idx
  ON public.transaction_splits (category_id);
CREATE INDEX IF NOT EXISTS budget_alerts_category_id_idx
  ON public.budget_alerts (category_id);
CREATE INDEX IF NOT EXISTS recurring_merchants_category_id_idx
  ON public.recurring_merchants (category_id);

-- RLS "initplan" fix (advisor lint 0003): `auth.uid()` is re-evaluated per
-- row; `(select auth.uid())` is evaluated once per statement. Same semantics.
-- Low impact today (the backend uses the service-role key, which bypasses
-- RLS) but free to fix.
DO $$
DECLARE
  t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['budget_alerts', 'transaction_splits', 'notifications', 'recurring_merchants']
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS "select_own_%1$s" ON public.%1$I', t);
    EXECUTE format('DROP POLICY IF EXISTS "insert_own_%1$s" ON public.%1$I', t);
    EXECUTE format('DROP POLICY IF EXISTS "update_own_%1$s" ON public.%1$I', t);
    EXECUTE format('DROP POLICY IF EXISTS "delete_own_%1$s" ON public.%1$I', t);
    EXECUTE format('CREATE POLICY "select_own_%1$s" ON public.%1$I FOR SELECT USING (user_id = (select auth.uid()))', t);
    EXECUTE format('CREATE POLICY "insert_own_%1$s" ON public.%1$I FOR INSERT WITH CHECK (user_id = (select auth.uid()))', t);
    EXECUTE format('CREATE POLICY "update_own_%1$s" ON public.%1$I FOR UPDATE USING (user_id = (select auth.uid())) WITH CHECK (user_id = (select auth.uid()))', t);
    EXECUTE format('CREATE POLICY "delete_own_%1$s" ON public.%1$I FOR DELETE USING (user_id = (select auth.uid()))', t);
  END LOOP;
END $$;
