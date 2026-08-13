"""Tests for the LLM fallback classifier (src/llm_classify.py).

No real network calls — a fake Anthropic client stands in for
`anthropic.Anthropic()`, shaped like the real SDK's `messages.create()`
response (a list of content blocks, tool_use blocks carrying `.input`).
"""
from types import SimpleNamespace

from llm_classify import classify_with_llm


class _FakeMessages:
    def __init__(self, tool_input: dict | None = None, raise_error: bool = False):
        self._tool_input = tool_input
        self._raise_error = raise_error
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._raise_error:
            raise RuntimeError("simulated API failure")
        block = SimpleNamespace(type="tool_use", name="classify_transactions", input=self._tool_input)
        return SimpleNamespace(content=[block])


class _FakeClient:
    def __init__(self, tool_input: dict | None = None, raise_error: bool = False):
        self.messages = _FakeMessages(tool_input, raise_error)


CATEGORIES = ["Eating Out", "Groceries", "Shopping"]


def test_classifies_items_from_tool_response():
    client = _FakeClient({
        "results": [
            {"index": 0, "category": "Eating Out", "confidence": 0.9},
            {"index": 1, "category": "Groceries", "confidence": 0.8},
        ]
    })
    items = [
        {"merchant": "Some Ramen Shop", "description": ""},
        {"merchant": "Local Fruit Stand", "description": ""},
    ]

    result = classify_with_llm(items, CATEGORIES, client=client)

    assert result == [
        {"category": "Eating Out", "confidence": 0.9},
        {"category": "Groceries", "confidence": 0.8},
    ]


def test_single_batched_call_for_multiple_items():
    client = _FakeClient({"results": []})
    items = [{"merchant": f"Merchant {i}", "description": ""} for i in range(10)]

    classify_with_llm(items, CATEGORIES, client=client)

    assert len(client.messages.calls) == 1


def test_tool_schema_only_offers_passed_categories():
    client = _FakeClient({"results": []})
    classify_with_llm([{"merchant": "X", "description": ""}], CATEGORIES, client=client)

    call = client.messages.calls[0]
    tool = call["tools"][0]
    assert tool["input_schema"]["properties"]["results"]["items"]["properties"]["category"]["enum"] == CATEGORIES


def test_category_outside_allowed_set_is_ignored():
    client = _FakeClient({
        "results": [{"index": 0, "category": "Made Up Category", "confidence": 0.9}]
    })
    result = classify_with_llm([{"merchant": "X", "description": ""}], CATEGORIES, client=client)
    assert result == [None]


def test_out_of_range_index_is_ignored():
    client = _FakeClient({
        "results": [{"index": 5, "category": "Groceries", "confidence": 0.9}]
    })
    result = classify_with_llm([{"merchant": "X", "description": ""}], CATEGORIES, client=client)
    assert result == [None]


def test_client_error_returns_all_none():
    client = _FakeClient(raise_error=True)
    items = [{"merchant": "A", "description": ""}, {"merchant": "B", "description": ""}]
    result = classify_with_llm(items, CATEGORIES, client=client)
    assert result == [None, None]


def test_malformed_response_returns_all_none():
    client = _FakeClient(tool_input=None)  # missing "results" entirely
    items = [{"merchant": "A", "description": ""}]
    result = classify_with_llm(items, CATEGORIES, client=client)
    assert result == [None]


def test_empty_items_returns_empty_list():
    client = _FakeClient({"results": []})
    assert classify_with_llm([], CATEGORIES, client=client) == []
    assert client.messages.calls == []


def test_empty_categories_returns_all_none_without_calling_client():
    client = _FakeClient({"results": []})
    items = [{"merchant": "A", "description": ""}]
    result = classify_with_llm(items, [], client=client)
    assert result == [None]
    assert client.messages.calls == []


def test_confidence_is_clamped_to_0_1():
    client = _FakeClient({
        "results": [{"index": 0, "category": "Groceries", "confidence": 5.0}]
    })
    result = classify_with_llm([{"merchant": "X", "description": ""}], CATEGORIES, client=client)
    assert result[0]["confidence"] == 1.0
