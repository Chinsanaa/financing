"""Project paths — single place for data file locations."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
TEMPLATES = DATA / 'templates'
RAW = DATA / 'raw'
LABELED = DATA / 'labeled'
PROCESSED = DATA / 'processed'
EXPORTS = DATA / 'exports'
REPORTS = DATA / 'reports'

STARTER_RULES = TEMPLATES / 'merchant_rules_starter.csv'
BUDGET_EXAMPLE = TEMPLATES / 'budget_config.example.json'

MERCHANT_RULES = LABELED / 'merchant_rules_expanded.csv'
LABELED_TXNS = LABELED / 'labeled_transactions.csv'
BUDGET_CONFIG = DATA / 'budget_config.json'

TRANSACTIONS = PROCESSED / 'transactions.csv'
TRANSACTIONS_CLASSIFIED = PROCESSED / 'transactions_classified.csv'
NEEDS_REVIEW = PROCESSED / 'needs_manual_review.csv'
CLASSIFIER = PROCESSED / 'classifier.pkl'
VECTORIZER = PROCESSED / 'tfidf_vectorizer.pkl'

MERCHANTS_TO_LABEL = EXPORTS / 'merchants_to_label.csv'
TRANSACTIONS_COMBINED_EN_XLSX = EXPORTS / 'transactions_combined_en.xlsx'
