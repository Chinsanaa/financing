"""Two-stage routing: rules trusted, model suggestions on unseen merchants → review."""
import pandas as pd
from sklearn.linear_model import LogisticRegression

from segment import build_vectorizer, vectorize, clean_text, LR_HYPERPARAMS
from classify import classify_all


def _tiny_model(labeled):
    texts = labeled.apply(lambda r: clean_text(r["merchant"], r["description"]), axis=1).tolist()
    vec = build_vectorizer(texts)
    clf = LogisticRegression(**LR_HYPERPARAMS).fit(vectorize(texts, vec), labeled["category"])
    return vec, clf


def test_rule_covered_is_trusted_model_only_goes_to_review(synthetic_labeled):
    vec, clf = _tiny_model(synthetic_labeled)
    df = pd.DataFrame({
        "merchant": ["McDonalds", "TotallyNewMerchant"],  # one known rule, one unseen
        "description": ["lunch", "mystery purchase"],
        "amount": [20.0, 15.0],
    })
    rules = {"mcdonalds": "Eating Out"}
    out = classify_all(df, vec, clf, rules=rules)

    known = out[out["merchant"] == "McDonalds"].iloc[0]
    unseen = out[out["merchant"] == "TotallyNewMerchant"].iloc[0]

    assert known["label_source"] == "rule"
    assert known["needs_review"] == False  # noqa: E712
    assert unseen["label_source"] == "model"
    assert unseen["needs_review"] == True   # noqa: E712  routed to review regardless of confidence


def test_rules_only_mode_routes_everything_to_review(synthetic_labeled):
    df = pd.DataFrame({"merchant": ["Unknown"], "description": ["x"], "amount": [5.0]})
    out = classify_all(df, vectorizer=None, classifier=None, rules={})
    assert out.iloc[0]["label_source"] == "none"
    assert out.iloc[0]["needs_review"] == True  # noqa: E712
