-- API v5 (docs/contracts/API_V5.md §1.2, §1.3): home currency + FX rate cache.
--
-- profiles.home_currency: the user's home currency (upper-case ISO 4217).
--   NULL = no home currency (every *_home field in the API is null).
--   Never 'CNY': CNY is the base currency every amount is stored in.
--   The backend additionally restricts it to the supported list
--   (backend/fx.py SUPPORTED); the CHECK only guards the shape.
--
-- fx_rates: ECB reference rates republished by Frankfurter, as units of
--   `quote` per 1 CNY, one row per business day. Filled only by the
--   backend (backend/fx.py background backfills, scripts/backfill_fx.py).
--   RLS on with deliberately NO policies: only the service role, which
--   bypasses RLS, can read or write it. Not user data, so no user_id.
--
-- Idempotent: safe to re-run.

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS home_currency char(3) NULL;

ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_home_currency_check;
ALTER TABLE public.profiles ADD CONSTRAINT profiles_home_currency_check
  CHECK (home_currency ~ '^[A-Z]{3}$' AND home_currency <> 'CNY');

CREATE TABLE IF NOT EXISTS public.fx_rates (
  rate_date  date          NOT NULL,              -- ECB reference date
  quote      char(3)       NOT NULL,              -- e.g. 'USD'
  rate       numeric(18,8) NOT NULL,              -- units of `quote` per 1 CNY
  fetched_at timestamptz   NOT NULL DEFAULT now(),
  PRIMARY KEY (quote, rate_date)
);

ALTER TABLE public.fx_rates ENABLE ROW LEVEL SECURITY;
-- Deliberately NO policies (service role only).
