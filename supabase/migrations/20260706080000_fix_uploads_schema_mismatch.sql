-- Fix uploads-table schema mismatches that made EVERY uploads-record insert
-- fail silently (the backend logged a warning and returned upload_id=None):
--
-- 1. file_type was the enum upload_file_type ('alipay_csv','wechat_xlsx'),
--    but the backend writes the detected source ('alipay'/'wechat') — and a
--    WeChat CSV export has no matching enum value at all. Convert to text.
-- 2. storage_path and size_bytes were NOT NULL, but the backend never
--    stored the original file. It now does (best-effort) — keep the columns
--    nullable so a Storage hiccup can't block recording the upload.

ALTER TABLE uploads ALTER COLUMN file_type TYPE text USING file_type::text;
DROP TYPE upload_file_type;

ALTER TABLE uploads ALTER COLUMN storage_path DROP NOT NULL;
ALTER TABLE uploads ALTER COLUMN size_bytes DROP NOT NULL;
ALTER TABLE uploads ALTER COLUMN size_bytes SET DEFAULT 0;
