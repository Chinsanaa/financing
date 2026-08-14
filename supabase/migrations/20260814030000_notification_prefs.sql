-- Per-category notification preferences (in-app + email), extending the
-- single flat alert_email_enabled/alert_threshold_pct pair added by
-- 20260813210000_add_budget_alerts.sql into a real Settings "Notifications"
-- section with multiple categories.
--
-- Defaults preserve current behavior for existing users: budget and
-- pending-review in-app items keep showing (they were always on, with no
-- way to turn them off before this). Monthly overview email defaults off
-- since there is no sending logic behind it yet (Settings toggle only,
-- confirmed with the user) — nothing should silently start emailing anyone.

ALTER TABLE profiles ADD COLUMN budget_inapp_enabled boolean NOT NULL DEFAULT true;
ALTER TABLE profiles ADD COLUMN pending_review_inapp_enabled boolean NOT NULL DEFAULT true;
ALTER TABLE profiles ADD COLUMN monthly_overview_email_enabled boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN profiles.budget_inapp_enabled IS 'Show over/approaching-budget items in GET /dashboard/action (bell + Action plan tab)';
COMMENT ON COLUMN profiles.pending_review_inapp_enabled IS 'Show the pending_review item in GET /dashboard/action (bell + Action plan tab)';
COMMENT ON COLUMN profiles.monthly_overview_email_enabled IS 'Preference only — no monthly digest email is sent yet, this just records the opt-in for when that feature ships';
