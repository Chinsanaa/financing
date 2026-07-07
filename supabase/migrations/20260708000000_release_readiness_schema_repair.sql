-- Release-readiness schema repair.
--
-- The live database and the repo's migration history diverged: the live
-- project never received 20260706080000_fix_uploads_schema_mismatch, so
-- every uploads-row insert failed silently (file_type enum mismatch +
-- NOT NULL storage columns) — upload history stayed empty and file-hash
-- duplicate detection never engaged. This migration is written to be
-- idempotent against BOTH states:
--   * the live project (original uploads schema, global partial unique on
--     file_hash, transactions.upload_id ON DELETE SET NULL), and
--   * a fresh database that ran every repo migration in order.

-- 1. uploads.file_type: enum -> text (no-op where 20260706080000 already ran)
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'uploads'
      AND column_name = 'file_type' AND udt_name = 'upload_file_type'
  ) THEN
    ALTER TABLE uploads ALTER COLUMN file_type TYPE text USING file_type::text;
  END IF;
END $$;
DROP TYPE IF EXISTS upload_file_type;

-- 2. The upload row is now created BEFORE format detection/parsing (so
--    failed uploads appear in history) — these columns are filled in later.
ALTER TABLE uploads ALTER COLUMN file_type DROP NOT NULL;
ALTER TABLE uploads ALTER COLUMN storage_path DROP NOT NULL;
ALTER TABLE uploads ALTER COLUMN size_bytes DROP NOT NULL;
ALTER TABLE uploads ALTER COLUMN size_bytes SET DEFAULT 0;

-- 3. File-hash duplicate detection is per-user, not global: two users may
--    legitimately upload the same statement file.
ALTER TABLE uploads DROP CONSTRAINT IF EXISTS uploads_file_hash_key;
DROP INDEX IF EXISTS idx_uploads_file_hash_not_null;
DROP INDEX IF EXISTS idx_uploads_file_hash;  -- superseded by the unique index below
CREATE UNIQUE INDEX IF NOT EXISTS uploads_user_id_file_hash_key
  ON uploads(user_id, file_hash)
  WHERE file_hash IS NOT NULL;

-- 4. Deleting an upload must delete its transactions ("delete file clears
--    the data"). The original FK was ON DELETE SET NULL, which orphaned rows.
ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_upload_id_fkey;
ALTER TABLE transactions ADD CONSTRAINT transactions_upload_id_fkey
  FOREIGN KEY (upload_id) REFERENCES uploads(id) ON DELETE CASCADE;
