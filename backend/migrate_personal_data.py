#!/usr/bin/env python3
"""
One-time personal data migration script.

Moves the original user's private merchant rules and special categorization logic
from the shared codebase (src/merchant_categories.py) into their database account rows.

Usage:
    python migrate_personal_data.py <user_id> [--import-transactions <csv_file>] [--import-budget <json_file>]

Example:
    python migrate_personal_data.py "550e8400-e29b-41d4-a716-446655440000" \
        --import-transactions data/processed/transactions_classified.csv \
        --import-budget data/templates/budget_config.json
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from config import supabase_client
import pandas as pd


# Personal merchant rules (from src/merchant_categories.py::LOCAL_MERCHANT_RULES)
PERSONAL_MERCHANT_RULES = [
    ("上海蕤盛工贸", "Transportation"),
    ("上海都畅数字技术有限公司", "Transportation"),
    ("济明路蘭州牛肉面", "Eating Out"),
    ("美淑家", "Eating Out"),
    ("饿梨酱", "Eating Out"),
    ("YogurtDay", "Eating Out"),
    ("马永胜牛肉面", "Eating Out"),
    ("豹喵酒吧", "Eating Out"),
    ("橘柚梧桐", "Eating Out"),
    ("Holy Bagel", "Eating Out"),
    ("Habibi", "Eating Out"),
    ("13DE MARZO", "Eating Out"),
    ("AMINO AMIGO", "Eating Out"),
    ("LA BARAKA UV", "Eating Out"),
    ("鹈鹕镇大王", "Eating Out"),
    ("上海英和企业管理有限公司", "Eating Out"),
    ("floating kitchen", "Eating Out"),
    ("高青西门市", "Groceries"),
    ("K-MART", "Groceries"),
    ("上海香雪海国际贸易有限公司", "Groceries"),
    ("上海优悠生活商业管理有限公司", "Groceries"),
    ("JUNGLEplus", "Shopping"),
    ("上海谱墨品牌管理有限公司", "Shopping"),
    ("ws**1", "Shopping"),
    ("**店", "Shopping"),
    ("Sydney Yuen", "Transfers & Gifts"),
    ("Evie", "Transfers & Gifts"),
    ("Tara", "Transfers & Gifts"),
    ("sydney", "Transfers & Gifts"),
    ("Steve", "Transfers & Gifts"),
    ("dudu", "Transfers & Gifts"),
    ("enni", "Transfers & Gifts"),
    ("urnma", "Transfers & Gifts"),
    ("UYANGA", "Transfers & Gifts"),
    ("Margad", "Transfers & Gifts"),
    ("O. A. OCHIR", "Transfers & Gifts"),
    ("Yesui Battogtokh", "Transfers & Gifts"),
    ("Munkh-Erdene", "Transfers & Gifts"),
    ("ERDENE", "Transfers & Gifts"),
    ("Tselmeg Bayarjargal", "Transfers & Gifts"),
    ("Tsolmon Khurelbaatar", "Transfers & Gifts"),
    ("Ujin", "Transfers & Gifts"),
    ("ujin", "Transfers & Gifts"),
    ("Uranmaa", "Transfers & Gifts"),
    ("Udval Lkhagvadorj", "Transfers & Gifts"),
    ("Ari", "Transfers & Gifts"),
    ("Anar", "Transfers & Gifts"),
    ("E. DULGUUN", "Transfers & Gifts"),
    ("B. E. DULGUUN", "Transfers & Gifts"),
    ("P2P Transfer", "Transfers & Gifts"),
    ("River", "Transfers & Gifts"),
    ("S. MISHEEL", "Transfers & Gifts"),
    ("Laine", "Transfers & Gifts"),
    ("M.i", "Transfers & Gifts"),
    ("Misheel.S", "Transfers & Gifts"),
    ("Erkhkhongor", "Transfers & Gifts"),
    ("G. A. ERDENE", "Transfers & Gifts"),
    ("Hi", "Transfers & Gifts"),
    ("ODAY", "Transfers & Gifts"),
    ("Naransuvd", "Transfers & Gifts"),
    ("Yugi", "Transfers & Gifts"),
    ("alex", "Transfers & Gifts"),
    ("murun", "Transfers & Gifts"),
]

# Special rules (description-based disambiguation)
SPECIAL_RULES = [
    {
        "merchant_pattern": "上海纽约大学",
        "description_markers": ["Campus Card Top Up", "Tuition and Fees", "NYUCard Print Fee"],
        "category_name": "Utilities & Services",
    },
    {
        "merchant_pattern": "上海纽约大学",
        "description_markers": None,  # Fallback: no markers match → Eating Out
        "category_name": "Eating Out",
    },
]


def migrate_merchant_rules(user_id: str) -> int:
    """Insert personal merchant rules into merchant_rules table."""
    print(f"\n📋 Migrating {len(PERSONAL_MERCHANT_RULES)} personal merchant rules...")

    rules_to_insert = [
        {
            "user_id": user_id,
            "merchant_pattern": merchant,
            "category_name": category,
            "source": "migrated_local",
            "created_at": datetime.utcnow().isoformat(),
        }
        for merchant, category in PERSONAL_MERCHANT_RULES
    ]

    try:
        response = supabase_client.table("merchant_rules").insert(rules_to_insert).execute()
        count = len(response.data) if response.data else 0
        print(f"✅ Inserted {count} merchant rules")
        return count
    except Exception as e:
        print(f"❌ Failed to insert merchant rules: {e}")
        raise


def migrate_special_rules(user_id: str) -> int:
    """Insert special category rules (description-based) into special_rules table."""
    print(f"\n🔍 Migrating special category rules...")

    rules_to_insert = [
        {
            "user_id": user_id,
            "merchant_pattern": rule["merchant_pattern"],
            "description_markers": rule["description_markers"],
            "category_name": rule["category_name"],
            "created_at": datetime.utcnow().isoformat(),
        }
        for rule in SPECIAL_RULES
    ]

    try:
        response = supabase_client.table("special_rules").insert(rules_to_insert).execute()
        count = len(response.data) if response.data else 0
        print(f"✅ Inserted {count} special rules")
        return count
    except Exception as e:
        print(f"❌ Failed to insert special rules: {e}")
        raise


def import_transactions(user_id: str, csv_file: str) -> int:
    """Optionally import existing classified transactions from CSV."""
    print(f"\n📥 Importing transactions from {csv_file}...")

    if not Path(csv_file).exists():
        print(f"⚠️  File not found: {csv_file}")
        return 0

    try:
        df = pd.read_csv(csv_file)
        print(f"  Loaded {len(df)} transactions from CSV")

        # Normalize schema: expect timestamp, merchant, description, amount, category, source
        # Map to: timestamp, merchant, description, amount, category_id (lookup), label_source
        if "category" in df.columns:
            # Fetch user's categories to map category names to IDs
            cat_response = supabase_client.table("categories").select("id,name").eq("user_id", user_id).execute()
            cat_lookup = {cat["name"]: cat["id"] for cat in cat_response.data}

            df["category_id"] = df["category"].map(cat_lookup)
            df["user_id"] = user_id
            df["label_source"] = df.get("source", "migrated_local")
            df["is_manually_labeled"] = True
            df["needs_review"] = False

            # Keep only required columns
            required = ["timestamp", "merchant", "description", "amount", "category_id", "user_id", "label_source", "is_manually_labeled", "needs_review"]
            df = df[[col for col in required if col in df.columns]]

            rows = df.to_dict("records")
            response = supabase_client.table("transactions").insert(rows).execute()
            count = len(response.data) if response.data else 0
            print(f"✅ Imported {count} transactions")
            return count
        else:
            print("⚠️  CSV missing 'category' column, skipping import")
            return 0

    except Exception as e:
        print(f"❌ Failed to import transactions: {e}")
        raise


def import_budget_config(user_id: str, json_file: str) -> bool:
    """Optionally import budget configuration from JSON."""
    print(f"\n💰 Importing budget config from {json_file}...")

    if not Path(json_file).exists():
        print(f"⚠️  File not found: {json_file}")
        return False

    try:
        with open(json_file, "r") as f:
            config = json.load(f)

        # Update budget_config: extract income, currency, goals
        budget_update = {
            "income": config.get("monthly_income", 0),
            "currency": config.get("currency", "CNY"),
            "saving_goal_monthly": config.get("saving_goal_monthly", 0),
            "saving_goal_annual": config.get("saving_goal_annual", 0),
        }

        supabase_client.table("budget_config").update(budget_update).eq("user_id", user_id).execute()
        print(f"✅ Updated budget config")

        # Update budget_category_config: per-category limits
        if "categories" in config:
            for cat_name, cat_config in config["categories"].items():
                # Find category ID
                cat_response = supabase_client.table("categories").select("id").eq("user_id", user_id).eq("name", cat_name).execute()
                if cat_response.data:
                    cat_id = cat_response.data[0]["id"]
                    supabase_client.table("budget_category_config").update({
                        "type": cat_config.get("type", "Want"),
                        "monthly_budget": cat_config.get("monthly_budget", 0),
                        "annual_budget": cat_config.get("annual_budget", 0),
                    }).eq("user_id", user_id).eq("category_id", cat_id).execute()

        print(f"✅ Updated category budgets")
        return True

    except Exception as e:
        print(f"❌ Failed to import budget config: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Migrate personal data from shared codebase to user account.",
        epilog="Example: python migrate_personal_data.py <user_id> --import-transactions data/processed/transactions_classified.csv"
    )
    parser.add_argument("user_id", help="UUID of the target user account")
    parser.add_argument("--import-transactions", help="Path to CSV file with classified transactions")
    parser.add_argument("--import-budget", help="Path to JSON file with budget config")

    args = parser.parse_args()
    user_id = args.user_id

    print(f"🚀 Starting personal data migration for user {user_id}...\n")

    try:
        # Verify user exists
        user_response = supabase_client.table("profiles").select("id").eq("id", user_id).execute()
        if not user_response.data:
            print(f"❌ User not found: {user_id}")
            sys.exit(1)

        # Migrate merchant rules
        rules_count = migrate_merchant_rules(user_id)

        # Migrate special rules
        special_count = migrate_special_rules(user_id)

        # Optionally import transactions
        txn_count = 0
        if args.import_transactions:
            txn_count = import_transactions(user_id, args.import_transactions)

        # Optionally import budget
        budget_ok = False
        if args.import_budget:
            budget_ok = import_budget_config(user_id, args.import_budget)

        print(f"\n✅ Migration complete!")
        print(f"  • {rules_count} merchant rules migrated")
        print(f"  • {special_count} special rules migrated")
        print(f"  • {txn_count} transactions imported" if txn_count else "  • 0 transactions imported")
        print(f"  • Budget config {'updated' if budget_ok else 'not imported'}")
        print(f"\nUser {user_id} is ready to use the app without re-onboarding.")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
