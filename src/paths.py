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

# Model artifact file names. Per-user artifacts in Storage use these exact
# names, so they must never change (existing models would stop loading).
ARTIFACT_FILES = {
    'classifier': 'classifier.pkl',
    'vectorizer': 'tfidf_vectorizer.pkl',
    'vectorizer_hybrid': 'tfidf_vectorizer_hybrid.pkl',
    'vectorizer_config': 'vectorizer_config.pkl',
    'semantic_model': 'semantic_classifier.pkl',
    'semantic_index': 'semantic_index.pkl',
    'semantic_calibrator': 'semantic_calibrator.pkl',
    'tfidf_calibrator': 'tfidf_calibrator.pkl',
    'ensemble_config': 'ensemble_config.json',
}


def artifact_paths(model_dir: Path, report_path: Path | None = None) -> dict:
    """{artifact key: path} for a model directory, plus the training report
    (`report_path`, default <model_dir>/TRAINING_REPORT.txt)."""
    model_dir = Path(model_dir)
    paths = {key: model_dir / name for key, name in ARTIFACT_FILES.items()}
    paths['report'] = Path(report_path) if report_path else model_dir / 'TRAINING_REPORT.txt'
    return paths
