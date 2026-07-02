"""Canonical category lists shared across pipeline and dashboard."""

# 7 categories the ML classifier is trained on
ML_CATEGORIES = [
    'Groceries',
    'Transportation',
    'Utilities & Services',
    'Eating Out',
    'Shopping',
    'Transfers & Gifts',
    'Other',
]

# Extra labels for interactive labeling (mapped to ML categories at train time)
EXTRA_LABEL_CATEGORIES = [
    'Health & Wellness',
    'Travel',
    'Entertainment',
]

# Map extra / legacy rule categories → ML category for dashboard + training
CATEGORY_NORMALIZE = {
    'Health & Wellness': 'Other',
    'Travel': 'Other',
    'Entertainment': 'Other',
    '???': 'Other',
}

# All categories shown during interactive labeling
LABEL_CATEGORIES = ML_CATEGORIES + EXTRA_LABEL_CATEGORIES

# Dashboard + budget (ML spending + savings buckets)
ACTIVE_CATEGORIES = ML_CATEGORIES + ['Saving', 'Investing']

FORECAST_MONTHS = ['Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May']

# Minimum labeled rows before bootstrap will train a classifier
MIN_TRAINING_SAMPLES = 80
MIN_SAMPLES_PER_CLASS = 2
