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

# Semantic (embedding) layer artifacts — all rebuilt by retrain.py
SEMANTIC_MODEL = PROCESSED / 'semantic_classifier.pkl'
SEMANTIC_INDEX = PROCESSED / 'semantic_index.pkl'
SEMANTIC_CALIBRATOR = PROCESSED / 'semantic_calibrator.pkl'
TFIDF_CALIBRATOR = PROCESSED / 'tfidf_calibrator.pkl'
ENSEMBLE_CONFIG = PROCESSED / 'ensemble_config.json'
MODEL2VEC_DIR = PROCESSED / 'model2vec' / 'potion-multilingual-128M'

MERCHANTS_TO_LABEL = EXPORTS / 'merchants_to_label.csv'
TRANSACTIONS_COMBINED_EN_XLSX = EXPORTS / 'transactions_combined_en.xlsx'
