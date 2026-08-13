"""LLM fallback classifier for merchants no rule or trained model can place.

This is the last, most expensive tier of the classification pipeline (rules >
ML model > this). It never runs on its own — callers (backend/ml.py) decide
which rows qualify, dedupe by merchant first, and treat every result here as
an unconfirmed suggestion (never auto-applied).

Deliberately pure / DB-free, matching the rest of src/ (importable by both
backend/ and tests/ with no network access required for the latter — pass a
fake `client` and nothing here touches the real API).

Rename-proofing: `categories` must be the caller's CURRENT category names
(fetched fresh from the categories table), not any hardcoded list. The tool
schema below constrains the model to pick only from that exact set, so a
renamed category is picked up automatically on the next call — no stale
category name can ever be returned.
"""
from __future__ import annotations

MODEL = "claude-haiku-4-5"

_TOOL_NAME = "classify_transactions"


def _build_tool(categories: list[str]) -> dict:
    return {
        "name": _TOOL_NAME,
        "description": "Assign each transaction to exactly one of the given categories.",
        "input_schema": {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "index": {"type": "integer", "description": "0-based index of the transaction in the input list"},
                            "category": {"type": "string", "enum": categories},
                            "confidence": {"type": "number", "description": "0.0-1.0 how confident this category is correct"},
                        },
                        "required": ["index", "category", "confidence"],
                    },
                },
            },
            "required": ["results"],
        },
    }


def _build_prompt(items: list[dict]) -> str:
    lines = [
        "Classify each of the following personal-finance transactions into a "
        "spending category. Merchant/description text may be in Chinese, "
        "English, or a mix of both. Use your best judgement of what the "
        "merchant actually sells or the transaction is for.",
        "",
    ]
    for i, item in enumerate(items):
        merchant = str(item.get("merchant") or "").strip()
        description = str(item.get("description") or "").strip()
        lines.append(f"{i}. merchant={merchant!r} description={description!r}")
    return "\n".join(lines)


def classify_with_llm(
    items: list[dict],
    categories: list[str],
    client=None,
) -> list[dict | None]:
    """Classify a batch of {merchant, description} items in ONE API call.

    Returns a list the same length as `items`; each entry is either
    {"category": str, "confidence": float} (category always drawn from
    `categories`) or None if the LLM didn't return a usable answer for that
    item. Never raises — any failure (missing API key, network error,
    malformed response) returns all-None so callers can treat it exactly
    like "still unclassified".
    """
    if not items:
        return []
    if not categories:
        return [None] * len(items)

    try:
        if client is None:
            import anthropic

            client = anthropic.Anthropic()

        tool = _build_tool(categories)
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=[tool],
            tool_choice={"type": "tool", "name": _TOOL_NAME},
            messages=[{"role": "user", "content": _build_prompt(items)}],
        )

        results: list[dict | None] = [None] * len(items)
        for block in response.content:
            if getattr(block, "type", None) != "tool_use" or block.name != _TOOL_NAME:
                continue
            for entry in block.input.get("results", []):
                idx = entry.get("index")
                category = entry.get("category")
                if not isinstance(idx, int) or not (0 <= idx < len(items)):
                    continue
                if category not in categories:
                    continue
                try:
                    confidence = float(entry.get("confidence", 0.5))
                except (TypeError, ValueError):
                    confidence = 0.5
                confidence = min(max(confidence, 0.0), 1.0)
                results[idx] = {"category": category, "confidence": confidence}
        return results
    except Exception:
        return [None] * len(items)
