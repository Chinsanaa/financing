"""Project paths — single place for local data/artifact locations.

The backend downloads per-user artifacts into a temp dir and passes explicit
paths; these defaults are for local training/evaluation runs.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
LABELED = DATA / 'labeled'
PROCESSED = DATA / 'processed'
REPORTS = DATA / 'reports'

LABELED_TXNS = LABELED / 'labeled_transactions.csv'

CLASSIFIER = PROCESSED / 'classifier.pkl'
VECTORIZER = PROCESSED / 'tfidf_vectorizer.pkl'

# Semantic (embedding) layer artifacts — all rebuilt by retrain.py
SEMANTIC_MODEL = PROCESSED / 'semantic_classifier.pkl'
SEMANTIC_INDEX = PROCESSED / 'semantic_index.pkl'
SEMANTIC_CALIBRATOR = PROCESSED / 'semantic_calibrator.pkl'
TFIDF_CALIBRATOR = PROCESSED / 'tfidf_calibrator.pkl'
ENSEMBLE_CONFIG = PROCESSED / 'ensemble_config.json'
MODEL2VEC_DIR = PROCESSED / 'model2vec' / 'potion-multilingual-128M'
