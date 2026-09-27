-- Design rule (2026-09-27): no purple anywhere in the UI.
-- Category palette keys violet / indigo / fuchsia are replaced by
-- blue / green / olive (frontend: src/utils/categoryColors.ts + globals.css
-- --cat-* tokens; backend: ALLOWED_COLORS in backend/routes/categories.py).
--
-- 1. Allow the new keys (drop + re-add the CHECK; old keys must be gone
--    before the stricter CHECK is added back).
-- 2. Re-color existing categories. The per-user unique index on
--    (user_id, color) can't conflict: the new keys were not allowed before.
-- 3. Signup trigger: default colors for new accounts use the new keys.
--    Body otherwise identical to 20260814010000_expand_category_taxonomy.sql
--    (verified against the live definition before writing this).

ALTER TABLE public.categories DROP CONSTRAINT IF EXISTS categories_color_allowed;

UPDATE public.categories SET color = 'blue'  WHERE color = 'violet';
UPDATE public.categories SET color = 'green' WHERE color = 'indigo';
UPDATE public.categories SET color = 'olive' WHERE color = 'fuchsia';

ALTER TABLE public.categories ADD CONSTRAINT categories_color_allowed
  CHECK (color IS NULL OR color IN (
    'lime','blue','cyan','pink','amber','sky',
    'emerald','rose','green','teal','orange','olive'));

CREATE OR REPLACE FUNCTION public.initialize_default_categories()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.categories (user_id, name, is_catch_all, sort_order, color)
  VALUES
    (NEW.id, 'Groceries', false, 1, 'sky'),
    (NEW.id, 'Transportation', false, 2, 'orange'),
    (NEW.id, 'Utilities & Services', false, 3, 'teal'),
    (NEW.id, 'Eating Out', false, 4, 'amber'),
    (NEW.id, 'Shopping', false, 5, 'emerald'),
    (NEW.id, 'Transfers & Gifts', false, 6, 'blue'),
    (NEW.id, 'Housing', false, 7, 'cyan'),
    (NEW.id, 'Personal Care & Health', false, 8, 'olive'),
    (NEW.id, 'Entertainment', false, 9, 'pink'),
    (NEW.id, 'Travel', false, 10, 'green'),
    (NEW.id, 'Education', false, 11, 'lime'),
    (NEW.id, 'Investments', false, 12, NULL),
    (NEW.id, 'Other', true, 13, 'rose');

  INSERT INTO public.budget_config (user_id, currency)
  VALUES (NEW.id, 'CNY');

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp;
