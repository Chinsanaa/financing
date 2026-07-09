-- Add user-selectable category colors.
--
-- Stores a design-system palette KEY (e.g. 'violet'), not a raw hex: the
-- frontend maps each key to theme-aware light/dark values, so a choice looks
-- right in both themes and stays inside the design system.
-- NULL = no color chosen; the UI falls back to a deterministic hash.

ALTER TABLE categories ADD COLUMN IF NOT EXISTS color text;

-- Only known palette keys (or NULL) are storable.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'categories_color_allowed'
  ) THEN
    ALTER TABLE categories ADD CONSTRAINT categories_color_allowed
      CHECK (color IS NULL OR color IN (
        'lime','violet','cyan','pink','amber','sky',
        'emerald','rose','indigo','teal','orange','fuchsia'));
  END IF;
END $$;

-- No two of a user's categories may share a chosen color (NULL/auto exempt).
CREATE UNIQUE INDEX IF NOT EXISTS categories_user_color_unique
  ON categories(user_id, color) WHERE color IS NOT NULL;

COMMENT ON COLUMN categories.color IS
  'Design-system palette key; NULL = auto (deterministic hash fallback in the frontend)';
