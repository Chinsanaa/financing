-- Create storage buckets for multi-tenant artifact storage

-- model_artifacts bucket: user/{user_id}/models/{model_run_id}/*.pkl
-- Public: false (RLS enforced via auth)
INSERT INTO storage.buckets (id, name, public)
VALUES ('model_artifacts', 'model_artifacts', false)
ON CONFLICT (id) DO NOTHING;

-- RLS policy: users can only read/write their own model artifacts
CREATE POLICY "Users can read own model artifacts"
  ON storage.objects
  FOR SELECT
  USING (bucket_id = 'model_artifacts' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Users can write own model artifacts"
  ON storage.objects
  FOR INSERT
  WITH CHECK (bucket_id = 'model_artifacts' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Users can delete own model artifacts"
  ON storage.objects
  FOR DELETE
  USING (bucket_id = 'model_artifacts' AND auth.uid()::text = (storage.foldername(name))[1]);

-- uploads bucket: for original CSV/Excel files
-- Similar structure: user/{user_id}/uploads/{upload_id}.*
INSERT INTO storage.buckets (id, name, public)
VALUES ('uploads', 'uploads', false)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "Users can read own uploads"
  ON storage.objects
  FOR SELECT
  USING (bucket_id = 'uploads' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Users can write own uploads"
  ON storage.objects
  FOR INSERT
  WITH CHECK (bucket_id = 'uploads' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Users can delete own uploads"
  ON storage.objects
  FOR DELETE
  USING (bucket_id = 'uploads' AND auth.uid()::text = (storage.foldername(name))[1]);
