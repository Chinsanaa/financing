-- Security, Performance, and Indexing Fixes
-- Fixes 30+ Supabase linter warnings:
-- 1. Security: Revoke public access to SECURITY DEFINER functions
-- 2. Performance: Optimize RLS policies with single auth.uid() call per query
-- 3. Indexing: Add missing indexes, drop unused ones

-- ========== DROP UNUSED INDEXES ==========
-- These indexes on transactions have never been used since creation
DROP INDEX IF EXISTS public.transactions_user_id_timestamp_idx;
DROP INDEX IF EXISTS public.transactions_user_id_needs_review_idx;

-- ========== ADD MISSING INDEXES ON FOREIGN KEYS ==========
-- Improves query performance when joining on these columns
CREATE INDEX budget_category_config_category_id_idx ON public.budget_category_config(category_id);
CREATE INDEX model_runs_user_id_idx ON public.model_runs(user_id);
CREATE INDEX special_rules_user_id_idx ON public.special_rules(user_id);
CREATE INDEX transactions_category_id_idx ON public.transactions(category_id);
CREATE INDEX transactions_upload_id_idx ON public.transactions(upload_id);
CREATE INDEX uploads_user_id_idx ON public.uploads(user_id);

-- ========== UPDATE RLS POLICIES: OPTIMIZE auth.uid() CALLS ==========
-- Use (select auth.uid()) instead of direct auth.uid() to initialize function once per query
-- instead of once per row. Fixes 30+ "auth_rls_initplan" warnings.

-- profiles table
DROP POLICY "select_own_profile" ON profiles;
CREATE POLICY "select_own_profile" ON profiles FOR SELECT USING (id = (SELECT auth.uid()));

DROP POLICY "update_own_profile" ON profiles;
CREATE POLICY "update_own_profile" ON profiles FOR UPDATE USING (id = (SELECT auth.uid())) WITH CHECK (id = (SELECT auth.uid()));

-- categories table
DROP POLICY "select_own_categories" ON categories;
CREATE POLICY "select_own_categories" ON categories FOR SELECT USING (user_id = (SELECT auth.uid()));

DROP POLICY "insert_own_categories" ON categories;
CREATE POLICY "insert_own_categories" ON categories FOR INSERT WITH CHECK (user_id = (SELECT auth.uid()));

DROP POLICY "update_own_categories" ON categories;
CREATE POLICY "update_own_categories" ON categories FOR UPDATE USING (user_id = (SELECT auth.uid())) WITH CHECK (user_id = (SELECT auth.uid()));

DROP POLICY "delete_own_categories" ON categories;
CREATE POLICY "delete_own_categories" ON categories FOR DELETE USING (user_id = (SELECT auth.uid()));

-- uploads table
DROP POLICY "select_own_uploads" ON uploads;
CREATE POLICY "select_own_uploads" ON uploads FOR SELECT USING (user_id = (SELECT auth.uid()));

DROP POLICY "insert_own_uploads" ON uploads;
CREATE POLICY "insert_own_uploads" ON uploads FOR INSERT WITH CHECK (user_id = (SELECT auth.uid()));

DROP POLICY "update_own_uploads" ON uploads;
CREATE POLICY "update_own_uploads" ON uploads FOR UPDATE USING (user_id = (SELECT auth.uid())) WITH CHECK (user_id = (SELECT auth.uid()));

DROP POLICY "delete_own_uploads" ON uploads;
CREATE POLICY "delete_own_uploads" ON uploads FOR DELETE USING (user_id = (SELECT auth.uid()));

-- transactions table
DROP POLICY "select_own_transactions" ON transactions;
CREATE POLICY "select_own_transactions" ON transactions FOR SELECT USING (user_id = (SELECT auth.uid()));

DROP POLICY "insert_own_transactions" ON transactions;
CREATE POLICY "insert_own_transactions" ON transactions FOR INSERT WITH CHECK (user_id = (SELECT auth.uid()));

DROP POLICY "update_own_transactions" ON transactions;
CREATE POLICY "update_own_transactions" ON transactions FOR UPDATE USING (user_id = (SELECT auth.uid())) WITH CHECK (user_id = (SELECT auth.uid()));

DROP POLICY "delete_own_transactions" ON transactions;
CREATE POLICY "delete_own_transactions" ON transactions FOR DELETE USING (user_id = (SELECT auth.uid()));

-- merchant_rules table
-- Note: select_own_and_global_rules uses OR logic, so optimize differently
DROP POLICY "select_own_and_global_rules" ON merchant_rules;
CREATE POLICY "select_own_and_global_rules" ON merchant_rules FOR SELECT USING (user_id IS NULL OR user_id = (SELECT auth.uid()));

DROP POLICY "insert_own_rules" ON merchant_rules;
CREATE POLICY "insert_own_rules" ON merchant_rules FOR INSERT WITH CHECK (user_id = (SELECT auth.uid()));

DROP POLICY "update_own_rules" ON merchant_rules;
CREATE POLICY "update_own_rules" ON merchant_rules FOR UPDATE USING (user_id = (SELECT auth.uid())) WITH CHECK (user_id = (SELECT auth.uid()));

DROP POLICY "delete_own_rules" ON merchant_rules;
CREATE POLICY "delete_own_rules" ON merchant_rules FOR DELETE USING (user_id = (SELECT auth.uid()));

-- special_rules table
DROP POLICY "select_own_special_rules" ON special_rules;
CREATE POLICY "select_own_special_rules" ON special_rules FOR SELECT USING (user_id = (SELECT auth.uid()));

DROP POLICY "insert_own_special_rules" ON special_rules;
CREATE POLICY "insert_own_special_rules" ON special_rules FOR INSERT WITH CHECK (user_id = (SELECT auth.uid()));

DROP POLICY "update_own_special_rules" ON special_rules;
CREATE POLICY "update_own_special_rules" ON special_rules FOR UPDATE USING (user_id = (SELECT auth.uid())) WITH CHECK (user_id = (SELECT auth.uid()));

DROP POLICY "delete_own_special_rules" ON special_rules;
CREATE POLICY "delete_own_special_rules" ON special_rules FOR DELETE USING (user_id = (SELECT auth.uid()));

-- model_runs table
DROP POLICY "select_own_runs" ON model_runs;
CREATE POLICY "select_own_runs" ON model_runs FOR SELECT USING (user_id = (SELECT auth.uid()));

-- budget_config table
DROP POLICY "select_own_budget_config" ON budget_config;
CREATE POLICY "select_own_budget_config" ON budget_config FOR SELECT USING (user_id = (SELECT auth.uid()));

DROP POLICY "insert_own_budget_config" ON budget_config;
CREATE POLICY "insert_own_budget_config" ON budget_config FOR INSERT WITH CHECK (user_id = (SELECT auth.uid()));

DROP POLICY "update_own_budget_config" ON budget_config;
CREATE POLICY "update_own_budget_config" ON budget_config FOR UPDATE USING (user_id = (SELECT auth.uid())) WITH CHECK (user_id = (SELECT auth.uid()));

DROP POLICY "delete_own_budget_config" ON budget_config;
CREATE POLICY "delete_own_budget_config" ON budget_config FOR DELETE USING (user_id = (SELECT auth.uid()));

-- budget_category_config table
DROP POLICY "select_own_budget_category" ON budget_category_config;
CREATE POLICY "select_own_budget_category" ON budget_category_config FOR SELECT USING (user_id = (SELECT auth.uid()));

DROP POLICY "insert_own_budget_category" ON budget_category_config;
CREATE POLICY "insert_own_budget_category" ON budget_category_config FOR INSERT WITH CHECK (user_id = (SELECT auth.uid()));

DROP POLICY "update_own_budget_category" ON budget_category_config;
CREATE POLICY "update_own_budget_category" ON budget_category_config FOR UPDATE USING (user_id = (SELECT auth.uid())) WITH CHECK (user_id = (SELECT auth.uid()));

DROP POLICY "delete_own_budget_category" ON budget_category_config;
CREATE POLICY "delete_own_budget_category" ON budget_category_config FOR DELETE USING (user_id = (SELECT auth.uid()));

-- ========== SECURITY: REVOKE PUBLIC ACCESS TO SECURITY DEFINER FUNCTIONS ==========
-- Keep SECURITY DEFINER but revoke access from anon/authenticated roles
-- postgres role retains access for trigger execution

REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.initialize_default_categories() FROM anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.reassign_deleted_category_transactions() FROM anon, authenticated;
