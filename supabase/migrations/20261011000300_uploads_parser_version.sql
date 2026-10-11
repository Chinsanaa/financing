-- API v5 §1.4: which parser version produced an upload's rows.
-- 1 = v1 parser (expense + refund rows only); 2 = v5 parser (all settled
-- rows with kind / flow_subtype). Existing uploads stay 1; the backend
-- writes 2 for every new upload and flips a v1 upload to 2 once a re-import
-- has reconciled its whole time range (backend/routes/uploads.py).
ALTER TABLE uploads ADD COLUMN IF NOT EXISTS parser_version smallint NOT NULL DEFAULT 1;
