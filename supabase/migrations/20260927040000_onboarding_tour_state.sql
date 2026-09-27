-- Onboarding tour progress, stored per ACCOUNT (was per-browser localStorage,
-- which made the tour reappear on every new device / cleared browser, and
-- inferred steps from account data, which auto-skipped steps — e.g. rows
-- labeled by merchant rules ticked off "Label" right after the first upload).
--
-- tour_step:        index of the current step (0 upload, 1 categories,
--                   2 label, 3 train). Only moves forward by exactly one,
--                   via POST /dashboard/tour/advance (compare-and-set).
-- tour_finished_at: NULL = tour active; set when the last step completes or
--                   the user taps "Skip tour". Never shown again after that.
--
-- New signups get the column defaults (step 0, active) — the tour shows once,
-- right after sign-up. Accounts that existed before this migration are marked
-- finished (user decision: only new signups see the tour).

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS tour_step smallint NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS tour_finished_at timestamptz;

UPDATE public.profiles SET tour_finished_at = now() WHERE tour_finished_at IS NULL;

ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_tour_step_range;
ALTER TABLE public.profiles ADD CONSTRAINT profiles_tour_step_range CHECK (tour_step BETWEEN 0 AND 4);
