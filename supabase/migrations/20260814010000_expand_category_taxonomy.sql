-- Expand the ML category taxonomy from 7 to 13 categories.
--
-- Adds: Housing, Personal Care & Health, Entertainment, Travel, Education,
-- Investments. See docs/context.md Session 52 for the full decision record
-- (why these six and not the larger lists the user was weighing, why
-- Personal Care and Health were merged into one category, etc.) and
-- src/categories.py::ML_CATEGORIES for the canonical list the classifier
-- now trains on.
--
-- Three things this migration does:
--   1. Updates the signup trigger so new users get all 13 default categories.
--   2. Backfills the 6 new categories onto every EXISTING user (existing 7
--      categories are untouched — ON CONFLICT DO NOTHING on the (user_id,
--      name) unique constraint).
--   3. Syncs the global merchant_rules seed (554 rows from the original
--      20260703000001 migration) with src/merchant_categories.py's new
--      category assignments: remaps patterns that moved category (e.g.
--      airline/airport patterns Transportation -> Travel, video-streaming
--      platforms Utilities & Services -> Entertainment) and inserts the new
--      patterns added for the 6 new categories.

-- ========== 1. SIGNUP TRIGGER: create all 13 default categories ==========

CREATE OR REPLACE FUNCTION public.initialize_default_categories()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.categories (user_id, name, is_catch_all, sort_order, color)
  VALUES
    (NEW.id, 'Groceries', false, 1, 'sky'),
    (NEW.id, 'Transportation', false, 2, 'orange'),
    (NEW.id, 'Utilities & Services', false, 3, 'teal'),
    (NEW.id, 'Eating Out', false, 4, 'amber'),
    (NEW.id, 'Shopping', false, 5, 'emerald'),
    (NEW.id, 'Transfers & Gifts', false, 6, 'violet'),
    (NEW.id, 'Housing', false, 7, 'cyan'),
    (NEW.id, 'Personal Care & Health', false, 8, 'fuchsia'),
    (NEW.id, 'Entertainment', false, 9, 'pink'),
    (NEW.id, 'Travel', false, 10, 'indigo'),
    (NEW.id, 'Education', false, 11, 'lime'),
    (NEW.id, 'Investments', false, 12, NULL),
    (NEW.id, 'Other', true, 13, 'rose');

  INSERT INTO public.budget_config (user_id, currency)
  VALUES (NEW.id, 'CNY');

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp;

-- ========== 2. BACKFILL: add the 6 new categories to existing users ==========
-- Existing users already have Groceries/Transportation/Utilities & Services/
-- Eating Out/Shopping/Transfers & Gifts/Other (and possibly a manually-added
-- "Entertainment" -- ON CONFLICT DO NOTHING skips it if so, matching the
-- live account's existing 'pink' choice below).

INSERT INTO public.categories (user_id, name, is_catch_all, sort_order, color)
SELECT p.id, c.name, false, c.sort_order, c.color
FROM public.profiles p
CROSS JOIN (VALUES
    ('Housing', 7, 'cyan'),
    ('Personal Care & Health', 8, 'fuchsia'),
    ('Entertainment', 9, 'pink'),
    ('Travel', 10, 'indigo'),
    ('Education', 11, 'lime'),
    ('Investments', 12, NULL)
) AS c(name, sort_order, color)
ON CONFLICT (user_id, name) DO NOTHING;

-- ========== 3. SYNC merchant_rules with the updated category assignments ==========

-- Remap global merchant_rules whose pattern moved to a new category
-- (see src/merchant_categories.py diff for the full rationale).
UPDATE merchant_rules SET category_name = 'Travel' WHERE user_id IS NULL AND merchant_pattern = '中国东方航空' AND category_name = 'Transportation';
UPDATE merchant_rules SET category_name = 'Travel' WHERE user_id IS NULL AND merchant_pattern = '东方航空' AND category_name = 'Transportation';
UPDATE merchant_rules SET category_name = 'Travel' WHERE user_id IS NULL AND merchant_pattern = '南方航空' AND category_name = 'Transportation';
UPDATE merchant_rules SET category_name = 'Travel' WHERE user_id IS NULL AND merchant_pattern = '春秋航空' AND category_name = 'Transportation';
UPDATE merchant_rules SET category_name = 'Travel' WHERE user_id IS NULL AND merchant_pattern = '国际航空' AND category_name = 'Transportation';
UPDATE merchant_rules SET category_name = 'Travel' WHERE user_id IS NULL AND merchant_pattern = '浦东机场' AND category_name = 'Transportation';
UPDATE merchant_rules SET category_name = 'Travel' WHERE user_id IS NULL AND merchant_pattern = '国航' AND category_name = 'Transportation';
UPDATE merchant_rules SET category_name = 'Travel' WHERE user_id IS NULL AND merchant_pattern = 'flight' AND category_name = 'Transportation';
UPDATE merchant_rules SET category_name = 'Travel' WHERE user_id IS NULL AND merchant_pattern = 'airport' AND category_name = 'Transportation';
UPDATE merchant_rules SET category_name = 'Travel' WHERE user_id IS NULL AND merchant_pattern = 'airline' AND category_name = 'Transportation';
UPDATE merchant_rules SET category_name = 'Travel' WHERE user_id IS NULL AND merchant_pattern = '火车票' AND category_name = 'Transportation';
UPDATE merchant_rules SET category_name = 'Travel' WHERE user_id IS NULL AND merchant_pattern = '飞机票' AND category_name = 'Transportation';
UPDATE merchant_rules SET category_name = 'Travel' WHERE user_id IS NULL AND merchant_pattern = '机票' AND category_name = 'Transportation';
UPDATE merchant_rules SET category_name = 'Personal Care & Health' WHERE user_id IS NULL AND merchant_pattern = '屈臣氏' AND category_name = 'Shopping';
UPDATE merchant_rules SET category_name = 'Personal Care & Health' WHERE user_id IS NULL AND merchant_pattern = '万宁' AND category_name = 'Shopping';
UPDATE merchant_rules SET category_name = 'Entertainment' WHERE user_id IS NULL AND merchant_pattern = '万达影城' AND category_name = 'Shopping';
UPDATE merchant_rules SET category_name = 'Entertainment' WHERE user_id IS NULL AND merchant_pattern = '万达' AND category_name = 'Shopping';
UPDATE merchant_rules SET category_name = 'Entertainment' WHERE user_id IS NULL AND merchant_pattern = '爱奇艺' AND category_name = 'Utilities & Services';
UPDATE merchant_rules SET category_name = 'Entertainment' WHERE user_id IS NULL AND merchant_pattern = '腾讯视频' AND category_name = 'Utilities & Services';
UPDATE merchant_rules SET category_name = 'Entertainment' WHERE user_id IS NULL AND merchant_pattern = '优酷' AND category_name = 'Utilities & Services';
UPDATE merchant_rules SET category_name = 'Entertainment' WHERE user_id IS NULL AND merchant_pattern = '芒果TV' AND category_name = 'Utilities & Services';
UPDATE merchant_rules SET category_name = 'Entertainment' WHERE user_id IS NULL AND merchant_pattern = '汽水音乐' AND category_name = 'Utilities & Services';
UPDATE merchant_rules SET category_name = 'Entertainment' WHERE user_id IS NULL AND merchant_pattern = '哔哩哔哩' AND category_name = 'Utilities & Services';
UPDATE merchant_rules SET category_name = 'Entertainment' WHERE user_id IS NULL AND merchant_pattern = 'B站' AND category_name = 'Utilities & Services';
UPDATE merchant_rules SET category_name = 'Entertainment' WHERE user_id IS NULL AND merchant_pattern = '网易' AND category_name = 'Utilities & Services';

-- Only MERCHANT_CATEGORY_RULES (chain/generic patterns) below -- deliberately
-- excludes src/merchant_categories.py::LOCAL_MERCHANT_RULES (personal names,
-- one user's reviewed local merchants), matching the original
-- 20260703000001 seed migration, which never synced those to the DB either
-- (global rules apply to every account, and personal-name patterns aren't
-- something that should auto-fire for other users' transactions).
INSERT INTO merchant_rules (user_id, merchant_pattern, category_name, source)
VALUES
  (NULL, '携程', 'Travel', 'global_seed'),
  (NULL, 'Ctrip', 'Travel', 'global_seed'),
  (NULL, '去哪儿', 'Travel', 'global_seed'),
  (NULL, 'Qunar', 'Travel', 'global_seed'),
  (NULL, '飞猪', 'Travel', 'global_seed'),
  (NULL, 'Fliggy', 'Travel', 'global_seed'),
  (NULL, 'Booking.com', 'Travel', 'global_seed'),
  (NULL, 'Airbnb', 'Travel', 'global_seed'),
  (NULL, '如家酒店', 'Travel', 'global_seed'),
  (NULL, '汉庭酒店', 'Travel', 'global_seed'),
  (NULL, '锦江之星', 'Travel', 'global_seed'),
  (NULL, '7天连锁酒店', 'Travel', 'global_seed'),
  (NULL, 'hotel', 'Travel', 'global_seed'),
  (NULL, 'resort', 'Travel', 'global_seed'),
  (NULL, 'itinerary', 'Travel', 'global_seed'),
  (NULL, 'vacation', 'Travel', 'global_seed'),
  (NULL, 'visa', 'Travel', 'global_seed'),
  (NULL, '酒店', 'Travel', 'global_seed'),
  (NULL, '民宿', 'Travel', 'global_seed'),
  (NULL, '度假', 'Travel', 'global_seed'),
  (NULL, '旅游', 'Travel', 'global_seed'),
  (NULL, '签证', 'Travel', 'global_seed'),
  (NULL, 'rent', 'Housing', 'global_seed'),
  (NULL, 'mortgage', 'Housing', 'global_seed'),
  (NULL, 'property management', 'Housing', 'global_seed'),
  (NULL, '房租', 'Housing', 'global_seed'),
  (NULL, '房贷', 'Housing', 'global_seed'),
  (NULL, '物业费', 'Housing', 'global_seed'),
  (NULL, '物业管理', 'Housing', 'global_seed'),
  (NULL, '房屋维修', 'Housing', 'global_seed'),
  (NULL, 'Watsons', 'Personal Care & Health', 'global_seed'),
  (NULL, 'pharmacy', 'Personal Care & Health', 'global_seed'),
  (NULL, 'drugstore', 'Personal Care & Health', 'global_seed'),
  (NULL, 'hospital', 'Personal Care & Health', 'global_seed'),
  (NULL, 'clinic', 'Personal Care & Health', 'global_seed'),
  (NULL, 'dental', 'Personal Care & Health', 'global_seed'),
  (NULL, 'dentist', 'Personal Care & Health', 'global_seed'),
  (NULL, 'fitness', 'Personal Care & Health', 'global_seed'),
  (NULL, 'yoga', 'Personal Care & Health', 'global_seed'),
  (NULL, 'salon', 'Personal Care & Health', 'global_seed'),
  (NULL, 'haircut', 'Personal Care & Health', 'global_seed'),
  (NULL, '药店', 'Personal Care & Health', 'global_seed'),
  (NULL, '药房', 'Personal Care & Health', 'global_seed'),
  (NULL, '医院', 'Personal Care & Health', 'global_seed'),
  (NULL, '诊所', 'Personal Care & Health', 'global_seed'),
  (NULL, '牙科', 'Personal Care & Health', 'global_seed'),
  (NULL, '健身房', 'Personal Care & Health', 'global_seed'),
  (NULL, '美容', 'Personal Care & Health', 'global_seed'),
  (NULL, '美发', 'Personal Care & Health', 'global_seed'),
  (NULL, '理发', 'Personal Care & Health', 'global_seed'),
  (NULL, '网易云音乐', 'Entertainment', 'global_seed'),
  (NULL, 'Netflix', 'Entertainment', 'global_seed'),
  (NULL, 'Spotify', 'Entertainment', 'global_seed'),
  (NULL, 'Steam', 'Entertainment', 'global_seed'),
  (NULL, 'PlayStation', 'Entertainment', 'global_seed'),
  (NULL, 'Xbox', 'Entertainment', 'global_seed'),
  (NULL, 'cinema', 'Entertainment', 'global_seed'),
  (NULL, 'movie ticket', 'Entertainment', 'global_seed'),
  (NULL, 'concert ticket', 'Entertainment', 'global_seed'),
  (NULL, 'streaming', 'Entertainment', 'global_seed'),
  (NULL, '电影院', 'Entertainment', 'global_seed'),
  (NULL, '电影票', 'Entertainment', 'global_seed'),
  (NULL, '演唱会', 'Entertainment', 'global_seed'),
  (NULL, '剧院', 'Entertainment', 'global_seed'),
  (NULL, '游戏', 'Entertainment', 'global_seed'),
  (NULL, 'tuition', 'Education', 'global_seed'),
  (NULL, 'university', 'Education', 'global_seed'),
  (NULL, 'textbook', 'Education', 'global_seed'),
  (NULL, '学费', 'Education', 'global_seed'),
  (NULL, '大学', 'Education', 'global_seed'),
  (NULL, '学校', 'Education', 'global_seed'),
  (NULL, '教材', 'Education', 'global_seed'),
  (NULL, '培训班', 'Education', 'global_seed'),
  (NULL, '课程', 'Education', 'global_seed'),
  (NULL, '余额宝', 'Investments', 'global_seed'),
  (NULL, '天弘基金', 'Investments', 'global_seed'),
  (NULL, '蚂蚁财富', 'Investments', 'global_seed'),
  (NULL, 'brokerage', 'Investments', 'global_seed'),
  (NULL, '基金申购', 'Investments', 'global_seed'),
  (NULL, '基金定投', 'Investments', 'global_seed'),
  (NULL, '理财通', 'Investments', 'global_seed'),
  (NULL, '基金', 'Investments', 'global_seed'),
  (NULL, '理财', 'Investments', 'global_seed'),
  (NULL, '股票', 'Investments', 'global_seed')
ON CONFLICT (user_id, merchant_pattern, category_name) DO NOTHING;

-- Also promote the NYU Shanghai "Tuition and Fees"/"NYUCard Print Fee"
-- special-case rows (special_category() in src/merchant_categories.py,
-- applied at classify-time, not stored as merchant_rules rows) -- no DB
-- change needed there, noting it here since it's part of the same
-- Utilities & Services -> Education move.

-- ========== 4. RE-SEQUENCE sort_order for existing users ==========
-- The step-2 backfill appended new categories at the end of whatever
-- sort_order a user's rows already had (e.g. a manually-added "Entertainment"
-- category keeps its original position); realign every user's categories to
-- the canonical 13-category order so the dashboard displays them
-- consistently, without touching name/color/is_catch_all.
UPDATE categories SET sort_order = CASE name
  WHEN 'Groceries' THEN 1
  WHEN 'Transportation' THEN 2
  WHEN 'Utilities & Services' THEN 3
  WHEN 'Eating Out' THEN 4
  WHEN 'Shopping' THEN 5
  WHEN 'Transfers & Gifts' THEN 6
  WHEN 'Housing' THEN 7
  WHEN 'Personal Care & Health' THEN 8
  WHEN 'Entertainment' THEN 9
  WHEN 'Travel' THEN 10
  WHEN 'Education' THEN 11
  WHEN 'Investments' THEN 12
  WHEN 'Other' THEN 13
  ELSE sort_order
END
WHERE name IN ('Groceries', 'Transportation', 'Utilities & Services', 'Eating Out',
               'Shopping', 'Transfers & Gifts', 'Housing', 'Personal Care & Health',
               'Entertainment', 'Travel', 'Education', 'Investments', 'Other');
