"""Semantic (embedding) layer: train/predict roundtrip, nearest-example
explanations, and graceful degradation — all using a deterministic FakeEncoder
so these tests never require model2vec or network access."""
import numpy as np
import pandas as pd

from semantic import (
    LsaEncoder,
    build_semantic_texts,
    embed_texts,
    train_semantic_model,
    predict_semantic,
    nearest_examples,
    save_semantic_artifacts,
    load_semantic_artifacts,
    get_encoder,
)


class FakeEncoder:
    """Deterministic keyword -> basis-vector embedding. No model2vec import.

    Full coverage of tests/conftest.py's synthetic_labeled fixture merchants,
    one dim per category cluster, so roundtrip accuracy is meaningfully high
    (a partial-coverage stub would leave uncovered merchants indistinguishable
    from each other regardless of true category — a test-fixture artifact,
    not something semantic.py should be judged on).
    """

    _BASIS = {
        # Eating Out
        'mcdonalds': 0, 'kfc': 0, 'starbucks': 0, 'burgerking': 0, 'subway': 0, 'pizzahut': 0,
        # Groceries
        'aldi': 1, 'walmart': 1, 'familymart': 1, 'carrefour': 1, 'seveneleven': 1, 'lawson': 1,
        # Transportation
        'didi': 2, 'metro': 2, 'hellobike': 2, 'uber': 2, 'taxiabc': 2, 'buscard': 2,
        # Shopping
        'taobao': 3, 'jd': 3, 'ugreen': 3, 'nike': 3, 'uniqlo': 3, 'muji': 3,
    }
    DIM = 5  # dims 0-3 = category clusters, dim 4 = unknown bucket

    def encode(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.DIM), dtype=np.float32)
        for i, t in enumerate(texts):
            low = t.lower()
            hit = False
            for kw, dim in self._BASIS.items():
                if kw in low:
                    out[i, dim] = 1.0
                    hit = True
            if not hit:
                out[i, 4] = 1.0  # unknown bucket
        return out


def test_train_predict_roundtrip_recovers_categories(synthetic_labeled):
    encoder = FakeEncoder()
    model = train_semantic_model(synthetic_labeled, encoder)

    texts = build_semantic_texts(synthetic_labeled)
    preds, raw_conf = predict_semantic(texts, encoder, model['clf'])

    # Same-cluster merchants (fast food) should mostly predict the same
    # category as their training label — the model learned the mapping.
    accuracy = (preds == synthetic_labeled['category'].values).mean()
    assert accuracy > 0.8
    assert (raw_conf >= 0).all() and (raw_conf <= 1).all()


def test_nearest_examples_returns_same_category_neighbors(synthetic_labeled):
    encoder = FakeEncoder()
    model = train_semantic_model(synthetic_labeled, encoder)

    neighbors = nearest_examples("mcdonalds order", encoder, model['index'], k=3)
    assert len(neighbors) == 3
    # All neighbors should be Eating Out (same basis cluster) since FakeEncoder
    # gives fast-food merchants an identical vector.
    assert all(n['category'] == 'Eating Out' for n in neighbors)
    assert all('similarity' in n and 'merchant' in n for n in neighbors)


def test_adding_a_label_changes_prediction_for_similar_new_merchant(synthetic_labeled):
    """The 'smarter as it learns' property: appending one labeled row and
    retraining should let the index recognize a similar new merchant."""
    encoder = FakeEncoder()

    # Before: no Groceries-cluster merchant containing 'aldi' variant trained
    without = synthetic_labeled[synthetic_labeled['merchant'] != 'Aldi'].copy()
    model_before = train_semantic_model(without, encoder)
    pred_before, _ = predict_semantic(['aldi shop'], encoder, model_before['clf'])

    # After: add the Aldi rows back (simulates a fresh label from review queue)
    model_after = train_semantic_model(synthetic_labeled, encoder)
    pred_after, _ = predict_semantic(['aldi shop'], encoder, model_after['clf'])

    assert pred_after[0] == 'Groceries'
    # index grew — direct evidence the model incorporated the new label
    assert len(model_after['index']['labels']) > len(model_before['index']['labels'])


def test_train_semantic_model_drops_tiny_classes():
    df = pd.DataFrame({
        'merchant': ['A', 'A', 'B', 'B', 'C'],
        'description': ['x', 'x', 'y', 'y', 'z'],
        'category': ['Eating Out', 'Eating Out', 'Groceries', 'Groceries', 'Shopping'],
        'labeled': [True, True, True, True, True],
    })
    model = train_semantic_model(df, FakeEncoder())
    # 'Shopping' has only 1 sample -> dropped (mirrors retrain.py's < 2 filter)
    assert 'Shopping' not in set(model['index']['labels'])
    assert set(model['index']['labels']) == {'Eating Out', 'Groceries'}


def test_get_encoder_missing_package_returns_none(monkeypatch):
    """When model2vec isn't installed, get_encoder must return None, never raise."""
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == 'model2vec':
            raise ImportError("no module named model2vec")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', fake_import)
    assert get_encoder(allow_download=False) is None


def test_load_semantic_artifacts_missing_returns_none(tmp_path, monkeypatch):
    import paths
    monkeypatch.setattr(paths, 'SEMANTIC_MODEL', tmp_path / 'nope.pkl')
    monkeypatch.setattr(paths, 'SEMANTIC_INDEX', tmp_path / 'nope_index.pkl')
    import semantic
    monkeypatch.setattr(semantic, 'SEMANTIC_MODEL', tmp_path / 'nope.pkl')
    monkeypatch.setattr(semantic, 'SEMANTIC_INDEX', tmp_path / 'nope_index.pkl')
    assert load_semantic_artifacts() is None


def test_lsa_encoder_fit_encode_roundtrip():
    texts = ["麦当劳 lunch order", "肯德基 dinner", "滴滴出行 taxi ride", "淘宝 shopping"]
    enc = LsaEncoder(n_components=2).fit(texts)
    vectors = enc.encode(texts)
    assert vectors.shape[0] == len(texts)
    assert vectors.shape[1] <= 2

    # Serialization roundtrip (joblib-compatible: plain attrs, sklearn objects)
    import joblib
    import io
    buf = io.BytesIO()
    joblib.dump(enc, buf)
    buf.seek(0)
    enc2 = joblib.load(buf)
    np.testing.assert_allclose(enc2.encode(texts), vectors)


def test_embed_texts_works_with_either_encoder_type(synthetic_labeled):
    texts = build_semantic_texts(synthetic_labeled)
    fake_vecs = embed_texts(texts, FakeEncoder())
    assert fake_vecs.shape == (len(texts), FakeEncoder.DIM)

    lsa = LsaEncoder(n_components=5).fit(texts)
    lsa_vecs = embed_texts(texts, lsa)
    assert lsa_vecs.shape[0] == len(texts)


def test_save_and_load_semantic_artifacts_roundtrip(synthetic_labeled, tmp_path, monkeypatch):
    import semantic
    monkeypatch.setattr(semantic, 'SEMANTIC_MODEL', tmp_path / 'sem.pkl')
    monkeypatch.setattr(semantic, 'SEMANTIC_INDEX', tmp_path / 'sem_index.pkl')

    encoder = LsaEncoder(n_components=5).fit(build_semantic_texts(synthetic_labeled))
    model = train_semantic_model(synthetic_labeled, encoder)
    save_semantic_artifacts(model)

    loaded = load_semantic_artifacts()
    assert loaded is not None
    assert loaded['encoder_kind'] == 'LsaEncoder'
    preds = loaded['clf'].predict(loaded['encoder'].encode(['mcdonalds lunch']))
    assert preds[0] in synthetic_labeled['category'].unique()
