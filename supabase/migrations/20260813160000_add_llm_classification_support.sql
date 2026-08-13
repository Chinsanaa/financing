-- Adds the LLM fallback tier to classification: a new label_source value for
-- transactions classified by the LLM (always a suggestion, needs_review=true
-- until confirmed), and a new merchant_rules source value for rules created
-- when a user confirms an LLM suggestion ("rule generalization" — the next
-- transaction from that merchant hits the fast rule path instead of calling
-- the LLM again).
--
-- Both additive/backward-compatible: existing rows and code paths using the
-- prior enum values are unaffected.

ALTER TYPE label_source_type ADD VALUE IF NOT EXISTS 'llm';
ALTER TYPE merchant_rule_source ADD VALUE IF NOT EXISTS 'llm_confirmed';
