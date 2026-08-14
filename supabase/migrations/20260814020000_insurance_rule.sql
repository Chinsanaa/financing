-- Add the "insurance"/"保险" merchant rule → Utilities & Services.
--
-- Follow-up correction after Session 52's category-taxonomy expansion: the
-- user reviewed Alipay/WeChat's native category screenshots (which include
-- an "Insurance" type) and confirmed insurance spend should classify as
-- Utilities & Services, not a new category and not Personal Care & Health
-- (an earlier guess). src/merchant_categories.py had no rule for insurance
-- at all until now.

INSERT INTO merchant_rules (user_id, merchant_pattern, category_name, source)
VALUES
  (NULL, 'insurance', 'Utilities & Services', 'global_seed'),
  (NULL, '保险', 'Utilities & Services', 'global_seed')
ON CONFLICT (user_id, merchant_pattern, category_name) DO NOTHING;
