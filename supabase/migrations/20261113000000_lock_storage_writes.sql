-- Lock client writes to Storage.
--
-- The backend loads model artifacts with joblib (pickle), and only the
-- service-role backend ever writes to the `model_artifacts` and `uploads`
-- buckets (service role bypasses RLS). The frontend never calls Storage.
-- The original client INSERT/DELETE policies therefore only served an
-- attacker: a user could plant a malicious pickle under their own
-- {user_id}/ prefix. Drop them. The SELECT policies are kept.
-- Idempotent: safe to re-run.

DROP POLICY IF EXISTS "Users can write own model artifacts" ON storage.objects;
DROP POLICY IF EXISTS "Users can delete own model artifacts" ON storage.objects;
DROP POLICY IF EXISTS "Users can write own uploads" ON storage.objects;
DROP POLICY IF EXISTS "Users can delete own uploads" ON storage.objects;
