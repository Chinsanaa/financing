-- Fix file_hash constraint to allow NULL values and be more lenient
-- Drop existing constraint if it exists
ALTER TABLE uploads DROP CONSTRAINT IF EXISTS uploads_file_hash_key;

-- Make file_hash nullable and add proper constraint
ALTER TABLE uploads
  ALTER COLUMN file_hash DROP NOT NULL;

-- Add back constraint but allow multiple NULLs
CREATE UNIQUE INDEX idx_uploads_file_hash_not_null
ON uploads(file_hash)
WHERE file_hash IS NOT NULL;

-- Drop old index if it exists and recreate properly
DROP INDEX IF EXISTS idx_uploads_file_hash;

CREATE INDEX idx_uploads_user_file_hash ON uploads(user_id, file_hash);
