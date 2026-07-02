"""Graduated trust: model predictions auto-apply ONLY when the TF-IDF model
and the semantic model agree, calibrated confidence clears the threshold, and
the prediction isn't 'Other'. Everything else keeps today's review-routing.

Both "models" here are deterministic stubs keyed by row text, so every
scenario (agree/disagree, high/low confidence, Other) is exact and doesn't
depend on any real vectorizer, embedding, or trained model.
"""
import numpy as np
import pandas as pd
import pytest

from classify import classify_all, ModelBundle


class _KeyedStub:
    """A minimal (vectorizer|encoder) + classifier pair. `.transform`/`.encode`
    map each text to a 1-column id array; predict/predict_proba look the id
    up in caller-supplied dicts. Works as either the TF-IDF vectorizer+clf or
    the semantic encoder+clf — classify_all/predict_semantic only ever call
    transform/encode then predict/predict_proba.max(axis=1)."""

    def __init__(self, text_to_id: dict, id_to_label: dict, id_to_conf: dict, classes):
        self.text_to_id = text_to_id
        self.id_to_label = id_to_label
        self.id_to_conf = id_to_conf
        self.classes_ = list(classes)

    # vectorizer-style
    def transform(self, texts):
        return np.array([[float(self.text_to_id[t])] for t in texts])

    # encoder-style
    def encode(self, texts):
        return self.transform(texts)

    # classifier-style
    def predict(self, X):
        return np.array([self.id_to_label[int(row[0])] for row in X], dtype=object)

    def predict_proba(self, X):
        n, k = X.shape[0], len(self.classes_)
        proba = np.zeros((n, k))
        for i, row in enumerate(X):
            conf = self.id_to_conf[int(row[0])]
            proba[i, 0] = conf
            for j in range(1, k):
                proba[i, j] = (1 - conf) / max(k - 1, 1)
        return proba


CLASSES = ['Eating Out', 'Transportation', 'Other']


def _make_bundle(rows: dict, threshold: float = 0.7):
    """rows: text -> (tfidf_label, tfidf_conf, sem_label, sem_conf).
    Builds a full ModelBundle wired to _KeyedStub pairs and identity
    calibrators (None -> passthrough), so 'calibrated confidence' == raw."""
    texts = list(rows.keys())
    text_to_id = {t: i for i, t in enumerate(texts)}

    tfidf_stub = _KeyedStub(
        text_to_id,
        {i: rows[t][0] for i, t in enumerate(texts)},
        {i: rows[t][1] for i, t in enumerate(texts)},
        CLASSES)
    sem_stub = _KeyedStub(
        text_to_id,
        {i: rows[t][2] for i, t in enumerate(texts)},
        {i: rows[t][3] for i, t in enumerate(texts)},
        CLASSES)

    bundle = ModelBundle(
        vectorizer=tfidf_stub,
        classifier=tfidf_stub,
        config={'use_hybrid': False},
        semantic={'clf': sem_stub, 'index': {}, 'encoder': sem_stub, 'encoder_kind': 'stub'},
        cal_tfidf=None,       # None -> apply_calibrator is identity passthrough
        cal_semantic=None,
        ensemble={'threshold': threshold},
    )
    return bundle


def _df_for(rows: dict):
    """One row per key; merchant/description chosen so clean_text(...) round-trips
    to exactly the dict key (clean_text lowercases + strips, so use already-clean
    lowercase ascii text)."""
    merchants, descs = [], []
    for text in rows:
        merchants.append(text)
        descs.append('')
    return pd.DataFrame({'merchant': merchants, 'description': descs,
                         'amount': [10.0] * len(rows)})


def test_agree_high_confidence_auto_applies():
    rows = {'newcafe': ('Eating Out', 0.9, 'Eating Out', 0.85)}
    bundle = _make_bundle(rows, threshold=0.7)
    out = classify_all(_df_for(rows), rules={}, bundle=bundle)
    row = out.iloc[0]
    assert row['label_source'] == 'model_agreed'
    assert row['needs_review'] == False  # noqa: E712
    assert row['confidence'] == pytest.approx(0.85)  # min(conf_t, conf_s)


def test_agree_low_confidence_stays_in_review():
    rows = {'newcafe': ('Eating Out', 0.9, 'Eating Out', 0.5)}  # min=0.5 < threshold
    bundle = _make_bundle(rows, threshold=0.7)
    out = classify_all(_df_for(rows), rules={}, bundle=bundle)
    row = out.iloc[0]
    assert row['label_source'] == 'model'
    assert row['needs_review'] == True  # noqa: E712


def test_disagree_high_confidence_stays_in_review():
    rows = {'ambiguous': ('Eating Out', 0.95, 'Transportation', 0.95)}
    bundle = _make_bundle(rows, threshold=0.7)
    out = classify_all(_df_for(rows), rules={}, bundle=bundle)
    row = out.iloc[0]
    assert row['label_source'] == 'model'
    assert row['needs_review'] == True  # noqa: E712


def test_other_prediction_never_auto_applies_even_if_agreed():
    rows = {'mystery': ('Other', 0.99, 'Other', 0.99)}
    bundle = _make_bundle(rows, threshold=0.5)
    out = classify_all(_df_for(rows), rules={}, bundle=bundle)
    row = out.iloc[0]
    assert row['label_source'] == 'model'
    assert row['needs_review'] == True  # noqa: E712


def test_rule_beats_model_agreed():
    rows = {'starbucks': ('Eating Out', 0.9, 'Eating Out', 0.9)}
    bundle = _make_bundle(rows, threshold=0.5)
    rules = {'starbucks': 'Eating Out'}
    out = classify_all(_df_for(rows), rules=rules, bundle=bundle)
    row = out.iloc[0]
    assert row['label_source'] == 'rule'
    assert row['confidence'] == 1.0
    assert row['needs_review'] == False  # noqa: E712


def test_missing_semantic_artifacts_routes_identically_to_legacy():
    """bundle.semantic/ensemble absent -> agreement_ready False -> byte-identical
    to the pre-upgrade behavior (every model prediction -> review)."""
    rows = {'newcafe': ('Eating Out', 0.99, 'Eating Out', 0.99)}
    texts = list(rows.keys())
    text_to_id = {t: i for i, t in enumerate(texts)}
    tfidf_stub = _KeyedStub(text_to_id, {0: 'Eating Out'}, {0: 0.99}, CLASSES)

    bundle = ModelBundle(vectorizer=tfidf_stub, classifier=tfidf_stub,
                         config={'use_hybrid': False})  # no semantic/ensemble
    assert bundle.agreement_ready is False

    out = classify_all(_df_for(rows), rules={}, bundle=bundle)
    row = out.iloc[0]
    assert row['label_source'] == 'model'
    assert row['needs_review'] == True  # noqa: E712


def test_bundle_none_matches_pre_upgrade_two_arg_call(synthetic_labeled):
    """Sanity: calling classify_all without a bundle at all (the pre-Session-31
    call signature) still works — this is the same assertion as
    test_classify_routing.py, re-affirmed here for the new code path."""
    from segment import build_vectorizer, vectorize, clean_text, LR_HYPERPARAMS
    from sklearn.linear_model import LogisticRegression

    texts = synthetic_labeled.apply(
        lambda r: clean_text(r['merchant'], r['description']), axis=1).tolist()
    vec = build_vectorizer(texts)
    clf = LogisticRegression(**LR_HYPERPARAMS).fit(vectorize(texts, vec), synthetic_labeled['category'])

    df = pd.DataFrame({'merchant': ['TotallyNewMerchant'], 'description': ['mystery'],
                       'amount': [15.0]})
    out = classify_all(df, vec, clf, rules={})
    assert out.iloc[0]['label_source'] == 'model'
    assert out.iloc[0]['needs_review'] == True  # noqa: E712
