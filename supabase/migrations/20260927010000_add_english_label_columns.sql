-- Stored English translations of transaction text.
--
-- Reports/Review/Export used to call Google Translate live, once per Chinese
-- string, serially, on every page load. backend/translations.py now fills
-- these once per distinct string in the background (after upload, and
-- lazily for older rows); the request path only reads them.
-- NULL = not translated yet (or the last attempt failed — retried later).

ALTER TABLE public.transactions
  ADD COLUMN IF NOT EXISTS merchant_en text,
  ADD COLUMN IF NOT EXISTS description_en text;
