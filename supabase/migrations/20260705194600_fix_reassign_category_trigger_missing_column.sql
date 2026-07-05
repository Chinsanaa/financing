-- reassign_deleted_category_transactions() referenced transactions.updated_at,
-- a column that does not exist on the transactions table (unlike other
-- tables, transactions has no updated_at). This broke ANY category
-- deletion (not just account deletion cascade) with:
-- "column \"updated_at\" of relation \"transactions\" does not exist"

CREATE OR REPLACE FUNCTION public.reassign_deleted_category_transactions()
RETURNS trigger AS $$
DECLARE
  catch_all_id uuid;
BEGIN
  SELECT id INTO catch_all_id
  FROM public.categories
  WHERE user_id = OLD.user_id AND is_catch_all = true
  LIMIT 1;

  IF catch_all_id IS NOT NULL THEN
    UPDATE public.transactions
    SET category_id = catch_all_id
    WHERE category_id = OLD.id;
  END IF;

  RETURN OLD;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp;
