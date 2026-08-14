-- Transaction splits: let one transaction's amount be divided across multiple
-- categories (e.g. a Costco run: groceries + household). When a transaction
-- is split, its own transactions.category_id is cleared (NULL) and
-- transactions.is_split flags it so every aggregation call site can branch
-- cheaply instead of re-deriving "is this split" from a join every time.
-- See backend/routes/dashboard.py and backend/routes/classify.py.

ALTER TABLE transactions ADD COLUMN is_split boolean NOT NULL DEFAULT false;

CREATE TABLE transaction_splits (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES profiles ON DELETE CASCADE,
  transaction_id uuid NOT NULL REFERENCES transactions ON DELETE CASCADE,
  category_id uuid NOT NULL REFERENCES categories ON DELETE CASCADE,
  amount numeric(12, 2) NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),

  UNIQUE(transaction_id, category_id)
);

COMMENT ON TABLE transaction_splits IS 'Per-transaction category line-items when a transaction is split across multiple categories; amounts sum to the parent transactions.amount (same sign convention).';

ALTER TABLE transaction_splits ENABLE ROW LEVEL SECURITY;
CREATE POLICY "select_own_transaction_splits" ON transaction_splits FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "insert_own_transaction_splits" ON transaction_splits FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "update_own_transaction_splits" ON transaction_splits FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "delete_own_transaction_splits" ON transaction_splits FOR DELETE USING (user_id = auth.uid());

-- Shared aggregation RPC: unions non-split transactions' own category
-- contribution with split line-items' contributions, then re-aggregates in
-- an outer SELECT so a category doesn't get two separate rows depending on
-- which branch it came from. Replaces the pandas groupby in
-- backend/routes/dashboard.py::_spend_by_category / get_by_category.
-- txn_count counts contributing line items, not distinct transactions (a
-- split transaction contributes one line item per category it's split into).
CREATE OR REPLACE FUNCTION public.spend_by_category_for_user(
  p_user_id uuid,
  p_start timestamptz DEFAULT NULL,
  p_end timestamptz DEFAULT NULL
) RETURNS TABLE(category_id uuid, category_name text, amount numeric, txn_count bigint)
LANGUAGE sql STABLE AS $$
  WITH contributions AS (
    SELECT t.category_id AS category_id, t.amount AS amount
    FROM transactions t
    WHERE t.user_id = p_user_id
      AND t.is_split = false
      AND t.category_id IS NOT NULL
      AND (p_start IS NULL OR t."timestamp" >= p_start)
      AND (p_end IS NULL OR t."timestamp" < p_end)
    UNION ALL
    SELECT s.category_id AS category_id, s.amount AS amount
    FROM transaction_splits s
    JOIN transactions t ON t.id = s.transaction_id
    WHERE s.user_id = p_user_id
      AND (p_start IS NULL OR t."timestamp" >= p_start)
      AND (p_end IS NULL OR t."timestamp" < p_end)
  )
  SELECT c.category_id, cat.name AS category_name, SUM(c.amount) AS amount, COUNT(*) AS txn_count
  FROM contributions c
  JOIN categories cat ON cat.id = c.category_id
  GROUP BY c.category_id, cat.name;
$$;
