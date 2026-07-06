"""Semantic (embedding-based) transaction classification.

Why: TF-IDF treats "麦当劳" and "KFC" as unrelated strings, so the model can't
generalize to merchants it never saw (36.5% grouped accuracy — the audit).
Embeddings map text into a vector space where MEANING determines position:
fast-food names land near each other because the encoder was pretrained on
billions of sentences. A simple LogisticRegression on those vectors inherits
that world knowledge.

Encoder backends (pluggable, best available wins):
1. Model2Vec `potion-multilingual-128M` — distilled from BGE-M3, 101 languages
   incl. Chinese, numpy-only inference (no torch). Preferred; weights download
   once and are cached under data/processed/model2vec/. NOTE: some environments
   block huggingface.co — get_encoder() then returns None and callers fall back.
2. LsaEncoder — char n-gram TF-IDF + TruncatedSVD fit on the labeled corpus.
   Captures string similarity (面馆 ≈ 面店), NOT world knowledge (bagel ≈/= bakery).
   Trainable fully offline; keeps the whole pipeline testable anywhere.
3. None — semantic layer disabled; classify falls back to today's behavior
   (every model prediction routed to review).

The classifier here is deliberately the same family as the TF-IDF path
(LogisticRegression, LR_HYPERPARAMS): interpretable, calibratable, and it
retrains in a fraction of a second — every reviewed label immediately
sharpens both the classifier and the nearest-example index.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).parent))

from categories import CATEGORY_NORMALIZE, ML_CATEGORIES
from segment import clean_text, LR_HYPERPARAMS
from paths import MODEL2VEC_DIR, SEMANTIC_MODEL, SEMANTIC_INDEX

MODEL2VEC_NAME = 'minishlab/potion-multilingual-128M'


# --------------------------------------------------------------------------
# Encoders
# --------------------------------------------------------------------------

class LsaEncoder:
    """Offline fallback encoder: char n-gram TF-IDF -> TruncatedSVD.

    Unsupervised (fits on text only, never labels). joblib-serializable.
    """

    def __init__(self, n_components: int = 200):
        self.n_components = n_components
        self._vectorizer = None
        self._svd = None

    def fit(self, texts: list[str]) -> 'LsaEncoder':
        self._vectorizer = TfidfVectorizer(
            analyzer='char_wb', ngram_range=(2, 4), min_df=1, max_features=20000)
        X = self._vectorizer.fit_transform(texts)
        # SVD components must be < min(n_samples, n_features)
        k = max(2, min(self.n_components, X.shape[0] - 1, X.shape[1] - 1))
        self._svd = TruncatedSVD(n_components=k, random_state=42)
        self._svd.fit(X)
        return self

    def encode(self, texts: list[str]) -> np.ndarray:
        if self._vectorizer is None or self._svd is None:
            raise RuntimeError("LsaEncoder must be fit before encoding")
        return self._svd.transform(self._vectorizer.transform(texts)).astype(np.float32)


def get_encoder(local_dir: Path = MODEL2VEC_DIR, allow_download: bool = True):
    """Best-effort Model2Vec encoder. Never raises — returns None on any failure.

    Order: (1) cached weights in local_dir, (2) download + cache if allowed.
    Classification-time callers use allow_download=False so scoring never
    performs network I/O; retrain is the one moment downloads may happen.
    """
    try:
        from model2vec import StaticModel  # lazy: package optional
    except ImportError:
        return None

    if local_dir.exists() and any(local_dir.iterdir()):
        try:
            return StaticModel.from_pretrained(str(local_dir))
        except Exception as e:
            print(f"   [semantic] cached model unreadable ({type(e).__name__}); ignoring cache")

    if not allow_download:
        return None

    try:
        model = StaticModel.from_pretrained(MODEL2VEC_NAME)
        local_dir.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(local_dir))
        return model
    except Exception as e:
        print(f"   [semantic] model download unavailable ({type(e).__name__}); "
              f"will fall back to LsaEncoder")
        return None


def fit_lsa_encoder(texts: list[str], n_components: int = 200) -> LsaEncoder:
    return LsaEncoder(n_components=n_components).fit(texts)


# --------------------------------------------------------------------------
# Text prep + embedding
# --------------------------------------------------------------------------

def build_semantic_texts(df: pd.DataFrame) -> list[str]:
    """Same cleaning as the TF-IDF path (segment.clean_text) so both models
    see identical input text."""
    return df.apply(
        lambda row: clean_text(row.get('merchant', ''), row.get('description', '')),
        axis=1,
    ).tolist()


def embed_texts(texts: list[str], encoder) -> np.ndarray:
    """Encoder-agnostic embedding: both StaticModel and LsaEncoder expose
    .encode(list[str]) -> ndarray."""
    vectors = encoder.encode(texts)
    return np.asarray(vectors, dtype=np.float32)


# --------------------------------------------------------------------------
# Training / prediction / explanation
# --------------------------------------------------------------------------

def train_semantic_model(df_labeled: pd.DataFrame, encoder, valid_categories: list = None) -> dict:
    """Fit LogisticRegression on embeddings of the labeled data.

    Mirrors retrain.py's filtering: labeled==True, category normalization,
    drop classes with < 2 samples. Returns {'clf', 'index', 'encoder_kind'}
    where index holds the embeddings/labels/merchants for nearest_examples().

    Args:
        df_labeled: dataframe with 'labeled' column and 'category' column
        encoder: StaticModel or LsaEncoder instance
        valid_categories: list of allowed category names (defaults to ML_CATEGORIES for backward compat)
    """
    if valid_categories is None:
        valid_categories = ML_CATEGORIES

    df = df_labeled[df_labeled['labeled'] == True].copy()
    df['category'] = df['category'].replace(CATEGORY_NORMALIZE)
    df = df[df['category'].isin(valid_categories)]

    counts = df['category'].value_counts()
    df = df[df['category'].isin(counts[counts >= 2].index)]
    if len(df) == 0:
        raise ValueError("no trainable labeled rows after filtering")

    texts = build_semantic_texts(df)
    X = embed_texts(texts, encoder)
    y = df['category'].values

    clf = LogisticRegression(**LR_HYPERPARAMS)
    clf.fit(X, y)

    return {
        'clf': clf,
        'index': {
            'embeddings': X,
            'labels': y,
            'merchants': df['merchant'].astype(str).values,
        },
        'encoder_kind': type(encoder).__name__,
        # LsaEncoder must travel with its model (it's corpus-fit);
        # StaticModel reloads from MODEL2VEC_DIR instead (large, cached on disk).
        'lsa_encoder': encoder if isinstance(encoder, LsaEncoder) else None,
    }


def predict_semantic(texts: list[str], encoder, clf) -> tuple[np.ndarray, np.ndarray]:
    """-> (predicted labels, raw max probability). Calibrate the confidence
    with calibration.apply_calibrator before comparing to any threshold."""
    X = embed_texts(texts, encoder)
    proba = clf.predict_proba(X)
    return clf.predict(X), proba.max(axis=1)


def nearest_examples(text: str, encoder, index: dict, k: int = 3) -> list[dict]:
    """Top-k most similar LABELED transactions — the model's 'reasoning' made
    visible in the review queue: "looks like 麦当劳 → Eating Out (cosine 0.83)"."""
    v = embed_texts([text], encoder)[0]
    E = index['embeddings']
    norms = np.linalg.norm(E, axis=1) * (np.linalg.norm(v) + 1e-12)
    sims = (E @ v) / np.where(norms == 0, 1e-12, norms)
    top = np.argsort(-sims)[:k]
    return [
        {'merchant': str(index['merchants'][i]),
         'category': str(index['labels'][i]),
         'similarity': round(float(sims[i]), 4)}
        for i in top
    ]


# --------------------------------------------------------------------------
# Artifact persistence
# --------------------------------------------------------------------------

def save_semantic_artifacts(model: dict, paths: Optional[dict] = None) -> None:
    """Save to paths['semantic_model']/paths['semantic_index'] when given
    (per-training-run isolation); otherwise the global data/processed/ files
    (CLI mode)."""
    model_path = paths['semantic_model'] if paths else SEMANTIC_MODEL
    index_path = paths['semantic_index'] if paths else SEMANTIC_INDEX
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({'clf': model['clf'],
                 'encoder_kind': model['encoder_kind'],
                 'lsa_encoder': model.get('lsa_encoder')}, model_path)
    joblib.dump(model['index'], index_path)


def load_semantic_artifacts(paths: Optional[dict] = None) -> Optional[dict]:
    """Load model + index + a usable encoder. None if anything is missing —
    callers then degrade to non-semantic behavior.

    `paths` (keys 'semantic_model'/'semantic_index', same dict shape as
    save_semantic_artifacts) loads a specific training run's artifacts;
    None keeps the global CLI behavior."""
    model_path = Path(paths['semantic_model']) if paths else SEMANTIC_MODEL
    index_path = Path(paths['semantic_index']) if paths else SEMANTIC_INDEX
    if not (model_path.exists() and index_path.exists()):
        return None
    try:
        blob = joblib.load(model_path)
        index = joblib.load(index_path)
    except Exception:
        return None

    if blob.get('lsa_encoder') is not None:
        encoder = blob['lsa_encoder']
    else:
        encoder = get_encoder(allow_download=False)  # scoring never downloads
        if encoder is None:
            return None

    return {'clf': blob['clf'], 'index': index,
            'encoder': encoder, 'encoder_kind': blob['encoder_kind']}
