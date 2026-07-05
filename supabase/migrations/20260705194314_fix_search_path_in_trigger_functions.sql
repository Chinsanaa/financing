-- Fix "relation does not exist" errors during signup.
--
-- initialize_default_categories() referenced `categories` and `budget_config`
-- without schema-qualifying them. As a trigger fired indirectly from an
-- auth.users INSERT (via handle_new_user -> profiles insert -> this trigger),
-- it runs under a search_path that does not include `public`, so the
-- unqualified names failed to resolve ("relation \"categories\" does not
-- exist"), aborting the whole signup transaction.
--
-- Fix: schema-qualify every table reference and pin search_path explicitly
-- on all three trigger functions (defense in depth, and Postgres best
-- practice for SECURITY DEFINER functions).

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, email_verified_at)
  VALUES (
    new.id,
    new.email_confirmed_at
  );
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp;

CREATE OR REPLACE FUNCTION public.initialize_default_categories()
RETURNS trigger AS $$
BEGIN
  -- Create the 7 default categories for this user
  INSERT INTO public.categories (user_id, name, is_catch_all, sort_order)
  VALUES
    (NEW.id, 'Food', false, 1),
    (NEW.id, 'Transport', false, 2),
    (NEW.id, 'Shopping', false, 3),
    (NEW.id, 'Entertainment', false, 4),
    (NEW.id, 'Health', false, 5),
    (NEW.id, 'Work', false, 6),
    (NEW.id, 'Other', true, 7);

  -- Initialize budget config for this user
  INSERT INTO public.budget_config (user_id, currency)
  VALUES (NEW.id, 'CNY');

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp;

CREATE OR REPLACE FUNCTION public.reassign_deleted_category_transactions()
RETURNS trigger AS $$
DECLARE
  catch_all_id uuid;
BEGIN
  -- Find this user's catch-all category
  SELECT id INTO catch_all_id
  FROM public.categories
  WHERE user_id = OLD.user_id AND is_catch_all = true
  LIMIT 1;

  -- Reassign any transactions pointing to this category
  IF catch_all_id IS NOT NULL THEN
    UPDATE public.transactions
    SET category_id = catch_all_id, updated_at = now()
    WHERE category_id = OLD.id;
  END IF;

  RETURN OLD;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp;
