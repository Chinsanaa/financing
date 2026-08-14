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

# All categories shown during interactive labeling
LABEL_CATEGORIES = ML_CATEGORIES

# Dashboard + budget buckets
ACTIVE_CATEGORIES = ML_CATEGORIES

FORECAST_MONTHS = ['Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May']

# Minimum labeled rows before bootstrap will train a classifier
MIN_TRAINING_SAMPLES = 80
MIN_SAMPLES_PER_CLASS = 2
