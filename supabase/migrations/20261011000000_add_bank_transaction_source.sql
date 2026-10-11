-- Generic bank-statement imports (API v5 §1.1 / §3.9). ALTER TYPE ... ADD
-- VALUE cannot run in the same transaction as statements that use the new
-- value, so it lives alone in this file, before 20261011000100.
ALTER TYPE transaction_source ADD VALUE IF NOT EXISTS 'bank';
