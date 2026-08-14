"""Canonical category lists shared across pipeline and dashboard."""

# 13 categories the ML classifier is trained on (expanded from the original 7
# on 2026-08-14 — see docs/context.md Session 52 for the decision record).
ML_CATEGORIES = [
    'Groceries',
    'Transportation',
    'Utilities & Services',
    'Eating Out',
    'Shopping',
    'Transfers & Gifts',
    'Housing',
    'Personal Care & Health',
    'Entertainment',
    'Travel',
    'Education',
    'Investments',
    'Other',
]

# Legacy/alternate category names that should collapse into an ML category
# when seen in old labeled data or a user's freeform category name.
CATEGORY_NORMALIZE = {
    'Health & Wellness': 'Personal Care & Health',
    '???': 'Other',
}

# 50/30/20 rule: canonical Need/Want/Savings bucket for each ML category, used
# by the Planning tab's 50/30/20 view (backend/routes/dashboard.py). This is
# independent of the per-category `budget_category_config.type` ('Need'/'Want'
# enum, no 'Savings' value) — that table only covers categories the user has
# explicitly set a $ budget for, so it can't be used to bucket ALL of a
# month's spend the way this static mapping can.
CATEGORY_BUCKET = {
    'Groceries': 'Need',
    'Transportation': 'Need',
    'Utilities & Services': 'Need',
    'Housing': 'Need',
    'Personal Care & Health': 'Need',
    'Education': 'Need',
    'Eating Out': 'Want',
    'Shopping': 'Want',
    'Entertainment': 'Want',
    'Travel': 'Want',
    'Transfers & Gifts': 'Want',
    'Other': 'Want',
    'Investments': 'Savings',
}

# All categories shown during interactive labeling
LABEL_CATEGORIES = ML_CATEGORIES

# Dashboard + budget buckets
ACTIVE_CATEGORIES = ML_CATEGORIES

FORECAST_MONTHS = ['Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May']

# Minimum labeled rows before bootstrap will train a classifier
MIN_TRAINING_SAMPLES = 80
MIN_SAMPLES_PER_CLASS = 2
