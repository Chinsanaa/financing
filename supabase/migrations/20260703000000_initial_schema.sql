-- Supabase Multi-Tenant Finance Categorizer: Initial Schema
-- Session Phase 1, Step 1: Core tables, RLS, triggers, seed data

-- ========== ENUM TYPES ==========
CREATE TYPE onboarding_phase AS ENUM ('upload', 'categories', 'labeling', 'complete');
CREATE TYPE transaction_source AS ENUM ('alipay', 'wechat');
CREATE TYPE label_source_type AS ENUM ('rule', 'override', 'model', 'model_agreed', 'none');
CREATE TYPE model_run_status AS ENUM ('queued', 'running', 'succeeded', 'failed');
CREATE TYPE model_run_trigger AS ENUM ('onboarding', 'label_batch', 'category_edit', 'manual');
CREATE TYPE upload_status AS ENUM ('uploaded', 'parsed', 'failed');
CREATE TYPE upload_file_type AS ENUM ('alipay_csv', 'wechat_xlsx');
CREATE TYPE budget_type AS ENUM ('Need', 'Want');
CREATE TYPE merchant_rule_source AS ENUM ('global_seed', 'user_created', 'migrated_local');

-- ========== PROFILES TABLE (extends auth.users) ==========
CREATE TABLE profiles (
  id uuid PRIMARY KEY REFERENCES auth.users ON DELETE CASCADE,
  email_verified_at timestamp with time zone,
  onboarding_phase onboarding_phase NOT NULL DEFAULT 'upload',
  onboarding_iteration int NOT NULL DEFAULT 0,
  monthly_income numeric(12, 2),
  created_at timestamp with time zone NOT NULL DEFAULT now()
);

COMMENT ON TABLE profiles IS 'Extends auth.users with app-specific profile data';
COMMENT ON COLUMN profiles.onboarding_phase IS 'Tracks user progress: upload → categories → labeling → complete';

-- RLS: users can select and update only their own profile
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "select_own_profile" ON profiles FOR SELECT USING (id = auth.uid());
CREATE POLICY "update_own_profile" ON profiles FOR UPDATE USING (id = auth.uid()) WITH CHECK (id = auth.uid());

-- Trigger: auto-create profile when auth user is created
CREATE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, email_verified_at)
  VALUES (
    new.id,
    new.email_confirmed_at
  );
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ========== CATEGORIES TABLE ==========
CREATE TABLE categories (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES profiles ON DELETE CASCADE,
  name text NOT NULL,
  is_catch_all boolean NOT NULL DEFAULT false,
  sort_order int NOT NULL DEFAULT 0,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),

  UNIQUE(user_id, name)
);

COMMENT ON TABLE categories IS 'User-defined expense categories (seeded with 7 defaults at signup)';
COMMENT ON COLUMN categories.is_catch_all IS 'Exactly one per user, marks the "Other" category for orphaned/unclassified transactions';

-- Partial unique index: enforce only one catch-all per user
CREATE UNIQUE INDEX categories_user_id_catch_all_idx
  ON categories(user_id) WHERE is_catch_all = true;

ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
CREATE POLICY "select_own_categories" ON categories FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "insert_own_categories" ON categories FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "update_own_categories" ON categories FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "delete_own_categories" ON categories FOR DELETE USING (user_id = auth.uid());

-- ========== UPLOADS TABLE ==========
CREATE TABLE uploads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES profiles ON DELETE CASCADE,
  storage_path text NOT NULL,
  original_filename text NOT NULL,
  file_type upload_file_type NOT NULL,
  size_bytes int NOT NULL,
  row_count int,
  status upload_status NOT NULL DEFAULT 'uploaded',
  error_message text,
  created_at timestamp with time zone NOT NULL DEFAULT now()
);

COMMENT ON TABLE uploads IS 'Metadata for uploaded Alipay/WeChat export files';

ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;
CREATE POLICY "select_own_uploads" ON uploads FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "insert_own_uploads" ON uploads FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "update_own_uploads" ON uploads FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "delete_own_uploads" ON uploads FOR DELETE USING (user_id = auth.uid());

-- ========== TRANSACTIONS TABLE ==========
CREATE TABLE transactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES profiles ON DELETE CASCADE,
  upload_id uuid REFERENCES uploads ON DELETE SET NULL,
  timestamp timestamp with time zone NOT NULL,
  merchant text NOT NULL,
  description text,
  amount numeric(12, 2) NOT NULL,
  source transaction_source NOT NULL,
  category_id uuid REFERENCES categories ON DELETE SET NULL,
  confidence numeric(3, 2),
  label_source label_source_type NOT NULL DEFAULT 'none',
  needs_review boolean NOT NULL DEFAULT false,
  is_manually_labeled boolean NOT NULL DEFAULT false,
  created_at timestamp with time zone NOT NULL DEFAULT now()
);

COMMENT ON TABLE transactions IS 'Parsed Alipay/WeChat transactions for each user';
COMMENT ON COLUMN transactions.confidence IS 'Model prediction confidence (0.0-1.0)';
COMMENT ON COLUMN transactions.label_source IS 'How the category was assigned: merchant rule, manual override, model prediction, or agreement between models';
COMMENT ON COLUMN transactions.needs_review IS 'Flag for user to review and correct post-onboarding';

CREATE INDEX transactions_user_id_timestamp_idx ON transactions(user_id, timestamp);
CREATE INDEX transactions_user_id_needs_review_idx ON transactions(user_id, needs_review);
CREATE INDEX transactions_user_id_merchant_idx ON transactions(user_id, merchant);

ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "select_own_transactions" ON transactions FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "insert_own_transactions" ON transactions FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "update_own_transactions" ON transactions FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "delete_own_transactions" ON transactions FOR DELETE USING (user_id = auth.uid());

-- Trigger: when a category is deleted, reassign its transactions to the user's catch-all
CREATE FUNCTION public.reassign_deleted_category_transactions()
RETURNS trigger AS $$
DECLARE
  catch_all_id uuid;
BEGIN
  -- Find this user's catch-all category
  SELECT id INTO catch_all_id
  FROM categories
  WHERE user_id = OLD.user_id AND is_catch_all = true
  LIMIT 1;

  -- Reassign any transactions pointing to this category
  IF catch_all_id IS NOT NULL THEN
    UPDATE transactions
    SET category_id = catch_all_id, updated_at = now()
    WHERE category_id = OLD.id;
  END IF;

  RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER before_delete_category
  BEFORE DELETE ON categories
  FOR EACH ROW EXECUTE FUNCTION public.reassign_deleted_category_transactions();

-- ========== MERCHANT_RULES TABLE (two-tier: global + user) ==========
CREATE TABLE merchant_rules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES profiles ON DELETE CASCADE,
  merchant_pattern text NOT NULL,
  category_name text NOT NULL,
  source merchant_rule_source NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),

  -- Allow both global (user_id IS NULL) and per-user rules
  UNIQUE(user_id, merchant_pattern, category_name)
);

COMMENT ON TABLE merchant_rules IS 'Two-tier merchant pattern rules: global (user_id=NULL) + per-user (user_id=their_id)';

ALTER TABLE merchant_rules ENABLE ROW LEVEL SECURITY;
-- Users can see and create their own rules; also see global rules (user_id IS NULL)
CREATE POLICY "select_own_and_global_rules" ON merchant_rules
  FOR SELECT USING (user_id IS NULL OR user_id = auth.uid());
CREATE POLICY "insert_own_rules" ON merchant_rules
  FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "update_own_rules" ON merchant_rules
  FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "delete_own_rules" ON merchant_rules
  FOR DELETE USING (user_id = auth.uid());

-- ========== SPECIAL_RULES TABLE (data-driven version of hardcoded logic) ==========
CREATE TABLE special_rules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES profiles ON DELETE CASCADE,
  merchant_pattern text NOT NULL,
  description_markers text[],
  category_name text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now()
);

COMMENT ON TABLE special_rules IS 'Data-driven version of hardcoded merchant+description-based categorization rules';
COMMENT ON COLUMN special_rules.description_markers IS 'Array of description keywords that trigger this rule; NULL means rule applies to merchant alone';

ALTER TABLE special_rules ENABLE ROW LEVEL SECURITY;
CREATE POLICY "select_own_special_rules" ON special_rules FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "insert_own_special_rules" ON special_rules FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "update_own_special_rules" ON special_rules FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "delete_own_special_rules" ON special_rules FOR DELETE USING (user_id = auth.uid());

-- ========== MODEL_RUNS TABLE (audit trail for training/classification jobs) ==========
CREATE TABLE model_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES profiles ON DELETE CASCADE,
  status model_run_status NOT NULL DEFAULT 'queued',
  trigger model_run_trigger NOT NULL,
  cv_accuracy numeric(3, 4),
  f1_macro numeric(3, 4),
  n_labeled_samples int,
  graduated_trust_enabled boolean NOT NULL DEFAULT true,
  agreement_threshold numeric(3, 2),
  artifact_version text,
  error_message text,
  started_at timestamp with time zone,
  finished_at timestamp with time zone,
  created_at timestamp with time zone NOT NULL DEFAULT now()
);

COMMENT ON TABLE model_runs IS 'Audit trail of model training and classification runs; artifacts versioned by model_run_id in Storage';

ALTER TABLE model_runs ENABLE ROW LEVEL SECURITY;
-- Users can select their own runs; only backend (via service role) writes
CREATE POLICY "select_own_runs" ON model_runs FOR SELECT USING (user_id = auth.uid());

-- ========== BUDGET_CONFIG TABLE ==========
CREATE TABLE budget_config (
  user_id uuid PRIMARY KEY REFERENCES profiles ON DELETE CASCADE,
  income numeric(12, 2),
  currency text NOT NULL DEFAULT 'CNY',
  saving_goal_monthly numeric(12, 2),
  saving_goal_annual numeric(12, 2),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now()
);

COMMENT ON TABLE budget_config IS 'Per-user budget settings and goals';

ALTER TABLE budget_config ENABLE ROW LEVEL SECURITY;
CREATE POLICY "select_own_budget_config" ON budget_config FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "insert_own_budget_config" ON budget_config FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "update_own_budget_config" ON budget_config FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "delete_own_budget_config" ON budget_config FOR DELETE USING (user_id = auth.uid());

-- ========== BUDGET_CATEGORY_CONFIG TABLE ==========
CREATE TABLE budget_category_config (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES profiles ON DELETE CASCADE,
  category_id uuid NOT NULL REFERENCES categories ON DELETE CASCADE,
  type budget_type NOT NULL,
  avg_monthly numeric(12, 2),
  monthly_budget numeric(12, 2),
  annual_budget numeric(12, 2),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),

  UNIQUE(user_id, category_id)
);

COMMENT ON TABLE budget_category_config IS 'Per-user, per-category budget settings (Need vs Want classification)';

ALTER TABLE budget_category_config ENABLE ROW LEVEL SECURITY;
CREATE POLICY "select_own_budget_category" ON budget_category_config FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "insert_own_budget_category" ON budget_category_config FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "update_own_budget_category" ON budget_category_config FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "delete_own_budget_category" ON budget_category_config FOR DELETE USING (user_id = auth.uid());
