-- Adds a unique, case-insensitive username to profiles, used as the
-- display identity across the app and as an alternate sign-in identifier.
-- Supabase Auth's signInWithPassword only accepts email, so username-based
-- login needs a database-side username -> email lookup; that lookup (and
-- the live "is this taken" check at signup) must run for anonymous/
-- pre-auth clients, hence the two SECURITY DEFINER RPCs below.

ALTER TABLE profiles ADD COLUMN username text;

ALTER TABLE profiles
  ADD CONSTRAINT username_format CHECK (username IS NULL OR username ~ '^[a-zA-Z0-9_]{3,20}$');

-- Partial (NULLs excluded) so existing accounts without a username don't
-- collide with each other, case-insensitive so "Sanaa" and "sanaa" can't
-- both be taken.
CREATE UNIQUE INDEX profiles_username_lower_idx ON profiles (lower(username)) WHERE username IS NOT NULL;

-- Existing trigger (20260703000000_initial_schema.sql) — now also reads the
-- username the frontend passes via signUp({ options: { data: { username } } }).
-- Original definition had no SET search_path; adding it here as the same
-- hardening already applied to initialize_default_categories() after the
-- Session 36 search-path incident.
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, email_verified_at, username)
  VALUES (
    new.id,
    new.email_confirmed_at,
    new.raw_user_meta_data->>'username'
  );
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp;

CREATE FUNCTION public.is_username_available(check_username text)
RETURNS boolean AS $$
  SELECT NOT EXISTS (
    SELECT 1 FROM public.profiles WHERE lower(username) = lower(check_username)
  );
$$ LANGUAGE sql SECURITY DEFINER SET search_path = public, pg_temp STABLE;

GRANT EXECUTE ON FUNCTION public.is_username_available(text) TO anon, authenticated;

CREATE FUNCTION public.get_email_for_username(check_username text)
RETURNS text AS $$
  SELECT au.email
  FROM auth.users au
  JOIN public.profiles p ON p.id = au.id
  WHERE lower(p.username) = lower(check_username)
  LIMIT 1;
$$ LANGUAGE sql SECURITY DEFINER SET search_path = public, pg_temp STABLE;

GRANT EXECUTE ON FUNCTION public.get_email_for_username(text) TO anon, authenticated;
