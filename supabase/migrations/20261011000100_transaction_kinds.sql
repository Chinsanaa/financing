-- Transaction kinds (API v5 §1.1): every row is an expense, income or
-- transfer. Until now the parsers only kept expenses and refunds, so every
-- existing row is an expense and every spend number stays identical.
--
-- Sign rule: for expense and transfer rows `+` = money left the user,
-- `-` = money came in; income rows are `+` (a negative income row is a
-- reversal and simply reduces income).

CREATE TYPE transaction_kind AS ENUM ('expense', 'income', 'transfer');

ALTER TABLE transactions
  ADD COLUMN kind transaction_kind NOT NULL DEFAULT 'expense',
  ADD COLUMN flow_subtype text NULL
    CONSTRAINT transactions_flow_subtype_check CHECK (flow_subtype IN (
      'refund', 'red_packet', 'p2p_transfer', 'aa_collection', 'salary', 'interest',
      'own_account', 'repayment', 'top_up', 'withdrawal', 'other'));

COMMENT ON COLUMN transactions.kind IS 'expense (counts as spend; refunds are negative expense rows) | income | transfer. Only expense rows are categorized, budgeted or classified.';
COMMENT ON COLUMN transactions.flow_subtype IS 'Finer kind: refund (expense); salary/interest/other (income); p2p_transfer/red_packet/aa_collection/other and the own-account moves own_account/repayment/top_up/withdrawal (transfer). NULL is allowed for every kind.';

-- Cash flow and every spend aggregate filter on kind within a user's
-- date range.
CREATE INDEX IF NOT EXISTS transactions_user_id_kind_timestamp_idx
  ON transactions (user_id, kind, "timestamp");

-- Explicit backfill. The column default already set kind = 'expense' (the
-- v1 parser only ever kept expense + refund rows); restated for clarity.
UPDATE transactions SET kind = 'expense' WHERE kind IS DISTINCT FROM 'expense';
UPDATE transactions SET flow_subtype = 'refund' WHERE amount < 0 AND flow_subtype IS NULL;

-- Only expenses can be split across categories: income/transfer rows have
-- no category at all (category_id NULL). PATCH /transactions/{id}/kind
-- returns 409 before this could fire; the constraint is the backstop.
ALTER TABLE transactions
  ADD CONSTRAINT transactions_split_only_expense CHECK (kind = 'expense' OR is_split = false);
