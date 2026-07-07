-- Signup created categories {Food, Transport, Shopping, Entertainment, Health,
-- Work, Other}, but all 554 seeded merchant_rules.category_name values (and
-- the trained classifier's own output classes) target
-- src/categories.py::ML_CATEGORIES: {Groceries, Transportation,
-- Utilities & Services, Eating Out, Shopping, Transfers & Gifts, Other}.
-- Only Shopping/Other overlapped, so classify_all()'s rules-matching stage
-- (src/classify.py:332-337) correctly set label_source='rule', but the very
-- next step, normalize_categories() (src/classify.py:32-48), immediately
-- discarded any category not in the user's actual category names back to
-- 'Other' — silently dropping ~5 of 6 rule categories on every classify run.
--
-- Fix: make the signup trigger create the exact ML_CATEGORIES taxonomy, so
-- rule-matched categories survive normalize_categories() for every new user.

CREATE OR REPLACE FUNCTION public.initialize_default_categories()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.categories (user_id, name, is_catch_all, sort_order)
  VALUES
    (NEW.id, 'Groceries', false, 1),
    (NEW.id, 'Transportation', false, 2),
    (NEW.id, 'Utilities & Services', false, 3),
    (NEW.id, 'Eating Out', false, 4),
    (NEW.id, 'Shopping', false, 5),
    (NEW.id, 'Transfers & Gifts', false, 6),
    (NEW.id, 'Other', true, 7);

  INSERT INTO public.budget_config (user_id, currency)
  VALUES (NEW.id, 'CNY');

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp;
