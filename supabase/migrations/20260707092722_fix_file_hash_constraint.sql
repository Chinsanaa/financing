-- Repo copy of a migration that was applied directly to the remote project
-- (version 20260707092722) but never committed. Do not re-apply remotely.
--
-- 20260707000002 created file_hash with a column-level UNIQUE, which is
-- GLOBAL: two different users uploading the same file would collide. This
-- replaces it with a partial unique index (still global — made per-user in
-- 20260708000000_release_readiness_schema_repair.sql).

ALTER TABLE uploads DROP CONSTRAINT IF EXISTS uploads_file_hash_key;

CREATE UNIQUE INDEX IF NOT EXISTS idx_uploads_file_hash_not_null
  ON uploads(file_hash)
  WHERE file_hash IS NOT NULL;
