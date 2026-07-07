-- Add file_hash column to uploads table for duplicate file detection
ALTER TABLE uploads
ADD COLUMN file_hash TEXT UNIQUE;

-- Create index for faster lookups
CREATE INDEX idx_uploads_file_hash ON uploads(user_id, file_hash);

-- Comment explaining the column
COMMENT ON COLUMN uploads.file_hash IS 'SHA256 hash of the uploaded file for duplicate detection. Unique to prevent same file being uploaded twice.';
