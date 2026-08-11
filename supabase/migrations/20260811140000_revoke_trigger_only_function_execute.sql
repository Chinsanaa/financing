-- Supabase's security advisor flags handle_new_user() and
-- initialize_default_categories() as callable directly via PostgREST RPC
-- by anon/authenticated (e.g. POST /rest/v1/rpc/handle_new_user). Both are
-- trigger functions only — they reference NEW, which only exists in
-- trigger context, so a direct RPC call would error out harmlessly today,
-- but there's no reason to leave them in the public API surface. Revoking
-- EXECUTE does not affect their triggers: Postgres fires triggers
-- regardless of the caller's EXECUTE grant on the function.
REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.initialize_default_categories() FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.reassign_deleted_category_transactions() FROM PUBLIC, anon, authenticated;
