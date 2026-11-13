# Personal Data Migration Guide — Phase 6

One-time migration of personal merchant rules and data from the shared codebase to your private account.

> **Note (2026-07-06)**: the script this guide describes,
> `backend/migrate_personal_data.py`, has been REMOVED from the repo because
> it embedded personal names in a public codebase. If you still need to run
> the migration, recover it from git history
> (`git show c611ef4^:backend/migrate_personal_data.py > migrate_personal_data.py`)
> and run it locally without committing it.

## Why This Matters

Your original analysis included personal data:
- **63 merchant rules** (personal names for P2P transfers, local shops, restaurants)
- **Special categorization logic** (NYU Shanghai split by description)
- **Classified transaction history** (optional import)
- **Budget configuration** (optional import)

Before production launch, this data moves from the shared codebase to your private database rows, so:
1. You don't re-onboard from scratch
2. Your personal merchant names aren't in the public repo
3. You own and control this data (via RLS)

---

## Prerequisites

- Your account created in the new app (sign up, verify email)
- Your user UUID (from Supabase → Authentication → Users, or from the dashboard)
- (Optional) Exported files:
  - `data/processed/transactions_classified.csv` (past classified transactions)
  - `data/templates/budget_config.json` (budget limits and income)

---

## Step 1: Prepare Your Data Files (Optional)

If you want to import your historical transaction data, export it from the old pipeline:

### Transactions Export
From your old local data directory, copy:
```
data/processed/transactions_classified.csv
```

This CSV should have columns:
- `timestamp` (ISO format: 2025-06-15T14:30:00)
- `merchant` (string)
- `description` (string)
- `amount` (float)
- `category` (string, matching your 7 default categories)
- `source` (optional: 'alipay' or 'wechat')

### Budget Config Export
Copy your existing budget configuration:
```
data/templates/budget_config.json
```

This JSON should have:
```json
{
  "monthly_income": 10000,
  "currency": "CNY",
  "saving_goal_monthly": 2000,
  "saving_goal_annual": 24000,
  "categories": {
    "Food": {
      "type": "Need",
      "monthly_budget": 1500,
      "annual_budget": 18000
    },
    ...
  }
}
```

---

## Step 2: Run the Migration Script

### Set Up Environment

```bash
cd backend

# Install dependencies (if not already done)
pip install -r requirements.txt

# Load Supabase credentials from .env.local
# (already set up in Phase 1)
```

### Run Migration

```bash
python migrate_personal_data.py <YOUR_USER_UUID>
```

**Replace `<YOUR_USER_UUID>` with your actual user ID** (find it in Supabase dashboard → Authentication).

### With Optional Imports

```bash
python migrate_personal_data.py <YOUR_USER_UUID> \
  --import-transactions ../data/processed/transactions_classified.csv \
  --import-budget ../data/templates/budget_config.json
```

### Example Output

```
🚀 Starting personal data migration for user 550e8400-e29b-41d4-a716-446655440000...

📋 Migrating 63 personal merchant rules...
✅ Inserted 63 merchant rules

🔍 Migrating special category rules...
✅ Inserted 2 special rules

📥 Importing transactions from ../data/processed/transactions_classified.csv...
  Loaded 1247 transactions from CSV
✅ Imported 1247 transactions

💰 Importing budget config from ../data/templates/budget_config.json...
✅ Updated budget config
✅ Updated category budgets

✅ Migration complete!
  • 63 merchant rules migrated
  • 2 special rules migrated
  • 1247 transactions imported
  • Budget config updated

User 550e8400-e29b-41d4-a716-446655440000 is ready to use the app without re-onboarding.
```

---

## Step 3: Verify Migration

After running the script:

1. **Log in** to the app (http://localhost:3000 or vercel.app)
2. **Check Dashboard → Overview**: Should see your imported transactions in the stats
3. **Check Dashboard → Budget**: Your monthly income and category limits should be loaded
4. **Check Dashboard → Review Queue**: Your personal merchants should not appear (they're now classified by rules)

---

## What Gets Migrated

| Item | Source | Destination | Scoped To |
|------|--------|-------------|-----------|
| 63 merchant patterns | `src/merchant_categories.py::LOCAL_MERCHANT_RULES` | `merchant_rules` table | Your user_id |
| 2 special rules | `src/merchant_categories.py::special_category()` | `special_rules` table | Your user_id |
| Transaction history | `data/processed/transactions_classified.csv` | `transactions` table | Your user_id |
| Budget config | `data/templates/budget_config.json` | `budget_config` + `budget_category_config` | Your user_id |

**Nothing is shared or visible to other users** (RLS policies enforce user_id scoping).

---

## After Migration

Once the script completes successfully:

1. **Remove the personal data from the shared codebase** (optional, but recommended for privacy):
   ```bash
   git rm data/processed/transactions_classified.csv
   git rm data/templates/budget_config.json
   # Optionally also strip LOCAL_MERCHANT_RULES from src/merchant_categories.py
   # (keep global MERCHANT_CATEGORY_RULES only)
   ```

2. **Test the app** with your imported data:
   - Upload a new file via the web UI → should parse correctly
   - Your personal merchants should auto-categorize by rules
   - Historical data should appear in dashboard stats

3. **Deploy to production** once verified.

---

## Troubleshooting

### "User not found"
```
❌ User not found: 550e8400-e29b-41d4-a716-446655440000
```
**Fix**: Double-check your user UUID in Supabase dashboard → Authentication → Users. Copy the full UUID.

### "Failed to insert merchant rules: ..."
```
❌ Failed to insert merchant rules: duplicate key value violates unique constraint
```
**Cause**: You ran the script twice. Each merchant rule is unique per user.
**Fix**: Safe to re-run; the script will fail gracefully on duplicates.

### "CSV missing 'category' column"
```
⚠️  CSV missing 'category' column, skipping import
```
**Fix**: Ensure your CSV has a `category` column with values matching your 7 default categories (Food, Transport, Shopping, Entertainment, Health, Work, Other).

### Missing categories in budget import
If some categories in `budget_config.json` don't exist in your account, they're silently skipped.
**Fix**: Create any missing categories in the app first (Settings/Categories tab), then re-run migration.

---

## Questions?

- **User UUID location**: Supabase dashboard → Authentication → Users → Copy User ID
- **Category names**: Should match exactly (Food, Transport, Shopping, Entertainment, Health, Work, Other)
- **Timezone handling**: Timestamps are stored as-is; adjust in your CSV if needed to match your timezone

---

**Created**: 2026-07-06 (Phase 6)
**Status**: Ready for one-time use
