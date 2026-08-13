"""Tests for the LLM fallback tier wired into backend/ml.py.

Rows classify_all() leaves as label_source='none' (no rule matched, no
trained model) get one more try via a batched, deduped LLM call. These
suggestions must never auto-apply — needs_review stays True — and the
whole tier must no-op cleanly when no API key is configured.
"""
import pandas as pd
import pytest

import ml
from config import settings


@pytest.fixture(autouse=True)
def _restore_api_key():
    """settings is a module-level singleton — don't leak the test key."""
    original = settings.groq_api_key
    yield
    settings.groq_api_key = original


def _none_row(id_, merchant, description=""):
    return {
        "id": id_, "merchant": merchant, "description": description,
        "category": "Other", "confidence": 0.0, "label_source": "none",
    }


def test_no_api_key_skips_llm_entirely(monkeypatch):
    settings.groq_api_key = None
    called = []
    monkeypatch.setattr(ml, "classify_with_llm", lambda items, cats: called.append(1) or [])

    result = pd.DataFrame([_none_row("t1", "Unknown Shop")])
    suggestions = ml._llm_fallback_suggestions(result, ["Eating Out"])

    assert suggestions == {}
    assert called == []


def test_no_none_rows_skips_llm_call(monkeypatch):
    settings.groq_api_key = "test-key"
    called = []
    monkeypatch.setattr(ml, "classify_with_llm", lambda items, cats: called.append(1) or [])

    result = pd.DataFrame([{
        "id": "t1", "merchant": "Known Shop", "description": "",
        "category": "Eating Out", "confidence": 0.6, "label_source": "model",
    }])
    suggestions = ml._llm_fallback_suggestions(result, ["Eating Out"])

    assert suggestions == {}
    assert called == []


def test_only_none_rows_are_sent_and_result_maps_back_by_row(monkeypatch):
    settings.groq_api_key = "test-key"

    def fake_classify_with_llm(items, categories):
        assert categories == ["Eating Out", "Groceries"]  # catch-all excluded
        assert [i["merchant"] for i in items] == ["Ramen Spot"]
        return [{"category": "Eating Out", "confidence": 0.77}]

    monkeypatch.setattr(ml, "classify_with_llm", fake_classify_with_llm)

    result = pd.DataFrame([
        _none_row("t1", "Ramen Spot"),
        {
            "id": "t2", "merchant": "Known Merchant", "description": "",
            "category": "Groceries", "confidence": 0.9, "label_source": "model_agreed",
        },
    ])
    suggestions = ml._llm_fallback_suggestions(result, ["Eating Out", "Groceries"])

    assert suggestions == {"t1": {"category": "Eating Out", "confidence": 0.77}}


def test_dedupes_same_merchant_into_one_line_item(monkeypatch):
    settings.groq_api_key = "test-key"
    calls = []

    def fake_classify_with_llm(items, categories):
        calls.append(items)
        return [{"category": "Eating Out", "confidence": 0.7}]

    monkeypatch.setattr(ml, "classify_with_llm", fake_classify_with_llm)

    result = pd.DataFrame([
        _none_row("t1", "Same Cafe"),
        _none_row("t2", "Same Cafe"),
        _none_row("t3", "Same Cafe"),
    ])
    suggestions = ml._llm_fallback_suggestions(result, ["Eating Out"])

    assert len(calls) == 1
    assert len(calls[0]) == 1  # one distinct merchant, not three rows
    assert suggestions == {
        "t1": {"category": "Eating Out", "confidence": 0.7},
        "t2": {"category": "Eating Out", "confidence": 0.7},
        "t3": {"category": "Eating Out", "confidence": 0.7},
    }


def test_caps_distinct_merchants_per_pass(monkeypatch):
    settings.groq_api_key = "test-key"
    monkeypatch.setattr(ml, "_LLM_MERCHANT_CAP", 2)

    def fake_classify_with_llm(items, categories):
        return [{"category": "Eating Out", "confidence": 0.5}] * len(items)

    monkeypatch.setattr(ml, "classify_with_llm", fake_classify_with_llm)

    result = pd.DataFrame([
        _none_row("t1", "Shop A"),
        _none_row("t2", "Shop B"),
        _none_row("t3", "Shop C"),
    ])
    suggestions = ml._llm_fallback_suggestions(result, ["Eating Out"])

    assert len(suggestions) == 2  # third merchant left for a future pass


def test_unanswered_merchant_is_absent_from_suggestions(monkeypatch):
    settings.groq_api_key = "test-key"
    monkeypatch.setattr(ml, "classify_with_llm", lambda items, cats: [None])

    result = pd.DataFrame([_none_row("t1", "Mystery Merchant")])
    suggestions = ml._llm_fallback_suggestions(result, ["Eating Out"])

    assert suggestions == {}


def test_end_to_end_llm_suggestion_never_auto_applies(monkeypatch, fake_db):
    """Full _classify_user_transactions wiring: an unclassifiable row ends
    up with an LLM suggestion, but needs_review stays True."""
    monkeypatch.setattr(ml, "supabase_client", fake_db)
    fake_db.seed("transactions", [{
        "id": "t1", "user_id": "u1", "merchant": "Obscure Local Ramen",
        "description": "", "amount": -25.0,
        "needs_review": True, "is_manually_labeled": False,
    }])

    monkeypatch.setattr(
        ml, "_fetch_categories",
        lambda user_id: ({"Eating Out": "cat-eat", "Other": "cat-other"}, ["Eating Out", "Other"], "Other"),
    )
    monkeypatch.setattr(ml, "_fetch_rules", lambda user_id: {})
    monkeypatch.setattr(ml, "get_user_bundle", lambda user_id: None)
    monkeypatch.setattr(ml, "classify_with_llm", lambda items, cats: [{"category": "Eating Out", "confidence": 0.8}])
    settings.groq_api_key = "test-key"

    updated = ml._classify_user_transactions("u1")

    assert updated == 1
    txn = fake_db._tables["transactions"].rows[0]
    assert txn["label_source"] == "llm"
    assert txn["needs_review"] is True  # never auto-applied
    assert txn["category_id"] == "cat-eat"
