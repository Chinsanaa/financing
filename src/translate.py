"""Translate transaction text to English for the web UI.

Hard rule: the web UI should never display Chinese text. If translation fails,
return a safe English placeholder instead of leaking original CJK text.
"""
import re
from functools import lru_cache

from merchant_display import display_merchant

_CJK_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]')


def has_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(str(text or '')))


def _mostly_ascii(text: str) -> bool:
    try:
        text.encode('ascii')
        return True
    except UnicodeEncodeError:
        return False


@lru_cache(maxsize=2048)
def translate_to_english(text: str) -> str:
    """Translate text to English; return unchanged if already non-CJK."""
    text = str(text or '').strip()
    if not text:
        return ''
    if not has_cjk(text):
        return text
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source='auto', target='en').translate(text[:500])
        return (translated or '').strip()
    except Exception:
        return ''


def _sanitize_english(text: str, fallback: str) -> str:
    """Guarantee an English-only display string (no CJK)."""
    text = str(text or '').strip()
    if not text:
        return fallback
    if has_cjk(text):
        return fallback
    return text


def shorten(text: str, max_len: int = 28) -> str:
    text = str(text or '').strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def merchant_label_english(merchant: str) -> str:
    """Short, official-ish English merchant label (never Chinese)."""
    merchant = str(merchant or '').strip()
    if not merchant:
        return "Unknown merchant"
    label = display_merchant(merchant)
    return _sanitize_english(label, "Unknown merchant") or "Unknown merchant"


def description_label_english(description: str) -> str:
    """English-only description (never Chinese)."""
    description = str(description or '').strip()
    if not description or description == '/':
        return ''
    if not has_cjk(description):
        return shorten(description, 80)
    translated = translate_to_english(description)
    translated = _sanitize_english(translated, '')
    return shorten(translated, 80) if translated else ''


def enrich_label_row(merchant: str, description: str) -> dict:
    """Build label-queue fields with English-only display strings."""
    merchant = str(merchant or '').strip()
    description = str(description or '').strip()
    merchant_en = merchant_label_english(merchant)
    description_en = description_label_english(description)
    return {
        # keep original merchant for training/rules only (never render in UI)
        'merchant': merchant,
        'merchant_label': merchant_en,
        'description_label': description_en,
    }
