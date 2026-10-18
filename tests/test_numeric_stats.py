"""Numeric features are fitted at training time (fit_numeric_stats) so a
transaction's features don't depend on what else is classified with it."""
import numpy as np
import pandas as pd
import pytest

from feature_engineering import (
    NUMERIC_COLUMNS,
    create_hybrid_feature_matrix,
    build_hybrid_vectorizers,
    extract_numeric_features,
    fit_numeric_stats,
)


@pytest.fixture
def history():
    rng = np.random.default_rng(0)
    n = 60
    merchants = rng.choice(['KFC', 'DiDi', 'Aldi', 'Nike', 'Metro'], n)
    return pd.DataFrame({
        'merchant': merchants,
        'description': [f'{m} order {i % 3}' for i, m in enumerate(merchants)],
        'amount': rng.uniform(5, 500, n).round(2),
        'timestamp': pd.date_range('2026-01-01 08:00', periods=n, freq='7h'),
    })


def test_training_features_identical_to_legacy(history):
    # Fitting stats must not change what the model trains on.
    legacy, idx_legacy = extract_numeric_features(history)
    fitted, idx_fitted = extract_numeric_features(history, fit_numeric_stats(history))
    assert list(idx_legacy) == list(idx_fitted)
    pd.testing.assert_frame_equal(legacy.reset_index(drop=True), fitted.reset_index(drop=True))


def test_features_independent_of_batch(history):
    stats = fit_numeric_stats(history)
    desc_vec, merch_vec = build_hybrid_vectorizers(history['description'].tolist(),
                                                   history['merchant'].tolist())
    new = history.sample(30, random_state=1).reset_index(drop=True)

    def row_vector(batch, i):
        num, _ = extract_numeric_features(batch, stats)
        X = create_hybrid_feature_matrix(batch, desc_vec, merch_vec, num, stats)
        return X.toarray()[i]

    alone = row_vector(new.iloc[[0]].reset_index(drop=True), 0)
    in_batch = row_vector(new, 0)
    np.testing.assert_allclose(alone, in_batch)


def test_out_of_range_amount_and_unseen_merchant_stay_in_range(history):
    stats = fit_numeric_stats(history)
    odd = pd.DataFrame({'merchant': ['Brand New Shop'], 'description': ['x'],
                        'amount': [1e9], 'timestamp': [pd.Timestamp('2026-03-01 12:00')]})
    num, _ = extract_numeric_features(odd, stats)
    assert num.loc[:, 'amount_bucket'].iloc[0] == len(stats['amount_edges']) - 2
    assert num.loc[:, 'merchant_frequency_norm'].iloc[0] == 0
    desc_vec, merch_vec = build_hybrid_vectorizers(history['description'].tolist(),
                                                   history['merchant'].tolist())
    X = create_hybrid_feature_matrix(odd, desc_vec, merch_vec, num, stats).toarray()
    assert (X[:, -len(NUMERIC_COLUMNS):] <= 1).all()


def test_missing_columns_give_empty_stats_and_zero_features():
    df = pd.DataFrame({'merchant': ['a'], 'description': ['b']})
    assert fit_numeric_stats(df) == {}
    num, _ = extract_numeric_features(df, {})
    assert (num.to_numpy() == 0).all()


def test_retrain_saves_stats_and_classify_uses_them(tmp_path, synthetic_labeled, monkeypatch):
    import joblib
    # Offline LSA encoder (as on the server); avoids a model2vec download.
    monkeypatch.setenv('MODEL2VEC_ENABLED', '0')
    from retrain import retrain_model
    from classify import classify_all, load_model_bundle

    labeled = synthetic_labeled.copy()
    labeled['timestamp'] = pd.date_range('2026-01-01', periods=len(labeled), freq='5h')
    from paths import artifact_paths
    paths = artifact_paths(tmp_path)
    retrain_model(labeled, paths=paths)

    vec = joblib.load(paths['vectorizer_hybrid'])
    assert vec['numeric_stats']['amount_edges']

    bundle = load_model_bundle(paths)
    batch = labeled.drop(columns=['category', 'labeled']).head(8)
    one = classify_all(batch.head(1).copy(), bundle=bundle)
    many = classify_all(batch.copy(), bundle=bundle)
    assert one['category'].iloc[0] == many['category'].iloc[0]
    assert one['confidence'].iloc[0] == pytest.approx(many['confidence'].iloc[0])

    # A model saved before stats existed (no 'numeric_stats' key) still works.
    del vec['numeric_stats']
    joblib.dump(vec, paths['vectorizer_hybrid'])
    legacy = classify_all(batch.copy(), bundle=load_model_bundle(paths))
    assert len(legacy) == len(batch)
