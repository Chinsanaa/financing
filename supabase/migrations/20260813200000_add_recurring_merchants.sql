-- Recurring/subscription detection: derived cache table, not a new source of truth.
-- Detection logic (src/recurring.py) recomputes rows from `transactions`; this table
-- just persists user confirm/dismiss state and the last computed summary per merchant.

CREATE TABLE recurring_merchants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES profiles ON DELETE CASCADE,
  merchant text NOT NULL,
  category_id uuid REFERENCES categories ON DELETE SET NULL,
  cadence text NOT NULL,
  typical_amount numeric(12, 2),
  last_seen timestamp with time zone,
  is_confirmed boolean NOT NULL DEFAULT false,
  is_dismissed boolean NOT NULL DEFAULT false,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),

  UNIQUE(user_id, merchant),
  CONSTRAINT recurring_merchants_cadence_check CHECK (cadence IN ('monthly', 'weekly', 'irregular'))
);

COMMENT ON TABLE recurring_merchants IS 'Per-user cache of detected recurring/subscription merchants, with user confirm/dismiss state';

ALTER TABLE recurring_merchants ENABLE ROW LEVEL SECURITY;
CREATE POLICY "select_own_recurring_merchants" ON recurring_merchants FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "insert_own_recurring_merchants" ON recurring_merchants FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "update_own_recurring_merchants" ON recurring_merchants FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "delete_own_recurring_merchants" ON recurring_merchants FOR DELETE USING (user_id = auth.uid());
