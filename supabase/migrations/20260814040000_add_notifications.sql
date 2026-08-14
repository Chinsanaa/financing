-- Real notification history: read/unread + clear. Reverses Session 54's
-- "no persisted notifications table" decision — that was the right call
-- until the user asked for exactly the concrete behavior (read/unread
-- tracking, a clear-all button) that only persisted state can support.
--
-- Distinct from budget_alerts (20260813210000_add_budget_alerts.sql),
-- which stays untouched as a write-only email-dedup ledger. This table
-- backs the header bell exclusively; GET /dashboard/action (Planning ->
-- Action plan) keeps computing over_budget/approaching_budget/
-- pending_review live and is unaffected by this migration.

CREATE TABLE notifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES profiles ON DELETE CASCADE,
  type text NOT NULL CHECK (type IN ('over_budget', 'approaching_budget', 'welcome', 'training_complete')),
  -- Uniqueness key for the underlying event, e.g. 'budget:over:{category_id}:{month}',
  -- 'welcome', 'training:{model_run_id}' -- the whole de-dup mechanism, same
  -- role budget_alerts' (user_id, category_id, month, kind) unique constraint plays for email.
  dedup_key text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  read_at timestamp with time zone,
  cleared_at timestamp with time zone,
  created_at timestamp with time zone NOT NULL DEFAULT now(),

  UNIQUE(user_id, dedup_key)
);

COMMENT ON TABLE notifications IS 'Persisted in-app notification history backing the header bell: read/unread + clear. Population is reactive (backend/alerts.py, training.py run_training success, lazy welcome insert on first fetch) -- no cron.';

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY "select_own_notifications" ON notifications FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "insert_own_notifications" ON notifications FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "update_own_notifications" ON notifications FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "delete_own_notifications" ON notifications FOR DELETE USING (user_id = auth.uid());

-- Bell reads "WHERE user_id = ? AND cleared_at IS NULL ORDER BY created_at DESC" on every open.
CREATE INDEX notifications_user_active_idx ON notifications(user_id, created_at DESC) WHERE cleared_at IS NULL;
