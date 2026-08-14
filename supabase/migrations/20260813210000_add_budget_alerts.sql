-- Budget alert email de-dup: records that a category has already been emailed
-- for a given month + kind ("approaching" or "over" budget), so the reactive
-- background check (backend/alerts.py) never sends the same alert twice.
-- The in-app "approaching_budget"/"over_budget" action items themselves
-- (GET /dashboard/action) stay computed fresh on every call — this table only
-- exists to gate the email side effect.

CREATE TABLE budget_alerts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES profiles ON DELETE CASCADE,
  category_id uuid NOT NULL REFERENCES categories ON DELETE CASCADE,
  month date NOT NULL,
  kind text NOT NULL,
  triggered_at timestamp with time zone NOT NULL DEFAULT now(),

  UNIQUE(user_id, category_id, month, kind),
  CONSTRAINT budget_alerts_kind_check CHECK (kind IN ('approaching', 'over'))
);

COMMENT ON TABLE budget_alerts IS 'Per-user record of budget-crossing emails already sent this month, keyed by category + kind, to prevent duplicate sends';

ALTER TABLE budget_alerts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "select_own_budget_alerts" ON budget_alerts FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "insert_own_budget_alerts" ON budget_alerts FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "update_own_budget_alerts" ON budget_alerts FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "delete_own_budget_alerts" ON budget_alerts FOR DELETE USING (user_id = auth.uid());

-- Alert preferences: a single configurable "approaching" threshold per user
-- (not per-category, not an array of thresholds) — "over" (100%) is not
-- configurable. profiles was last altered by 20260811130000_add_username.sql.
ALTER TABLE profiles ADD COLUMN alert_email_enabled boolean NOT NULL DEFAULT false;
ALTER TABLE profiles ADD COLUMN alert_threshold_pct numeric NOT NULL DEFAULT 80;
