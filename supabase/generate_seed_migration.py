#!/usr/bin/env python3
"""Generate SQL migration to seed global merchant rules and default categories."""

import sys
sys.path.insert(0, "src")

from merchant_categories import MERCHANT_CATEGORY_RULES

# Generate INSERT statements for global merchant rules
sql_lines = [
    "-- Seed global merchant rules and initialize category function",
    "-- Generated from src/merchant_categories.py::MERCHANT_CATEGORY_RULES",
    "",
    "-- ========== SEED GLOBAL MERCHANT RULES ==========",
    "INSERT INTO merchant_rules (user_id, merchant_pattern, category_name, source)",
    "VALUES",
]

# Convert rules to SQL VALUES clauses
values = []
for pattern, category in MERCHANT_CATEGORY_RULES:
    # Escape single quotes in pattern and category
    escaped_pattern = pattern.replace("'", "''")
    escaped_category = category.replace("'", "''")
    values.append(f"  (NULL, '{escaped_pattern}', '{escaped_category}', 'global_seed')")

sql_lines.append(",\n".join(values))
sql_lines.append(";")
sql_lines.append("")

# Add function to initialize default categories for new users
sql_lines.extend([
    "-- ========== FUNCTION: Initialize default categories for new user ==========",
    "CREATE OR REPLACE FUNCTION initialize_default_categories()",
    "RETURNS trigger AS $$",
    "BEGIN",
    "  -- Create the 7 default categories for this user",
    "  INSERT INTO categories (user_id, name, is_catch_all, sort_order)",
    "  VALUES",
    "    (NEW.id, 'Food', false, 1),",
    "    (NEW.id, 'Transport', false, 2),",
    "    (NEW.id, 'Shopping', false, 3),",
    "    (NEW.id, 'Entertainment', false, 4),",
    "    (NEW.id, 'Health', false, 5),",
    "    (NEW.id, 'Work', false, 6),",
    "    (NEW.id, 'Other', true, 7);",
    "",
    "  -- Initialize budget config for this user",
    "  INSERT INTO budget_config (user_id, currency)",
    "  VALUES (NEW.id, 'CNY');",
    "",
    "  RETURN NEW;",
    "END;",
    "$$ LANGUAGE plpgsql;",
    "",
    "-- Attach the trigger to profiles",
    "CREATE TRIGGER after_profile_created",
    "  AFTER INSERT ON profiles",
    "  FOR EACH ROW",
    "  EXECUTE FUNCTION initialize_default_categories();",
])

sql_content = "\n".join(sql_lines)
# Write to stdout with UTF-8 encoding
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
print(sql_content)
