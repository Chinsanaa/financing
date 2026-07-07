"""Translate transaction text to English for the web UI.

Hard rule: the web UI should never display Chinese text. If translation fails,
return a safe English placeholder instead of leaking original CJK text.
"""
import re
from functools import lru_cache


_CJK_RE = re.compile(r'[一-鿿㐀-䶿豈-﫿]')


def has_cjk(text: str) -> bool:
    """Check if text contains Chinese/Japanese/Korean characters."""
    return bool(_CJK_RE.search(str(text or '')))


def _mostly_ascii(text: str) -> bool:
    """Check if text is mostly ASCII."""
    try:
        text.encode('ascii')
        return True
    except UnicodeEncodeError:
        return False


@lru_cache(maxsize=2048)
def translate_to_english(text: str) -> str:
    """Translate text to English; return unchanged if already non-CJK.

    Caches results to avoid repeated API calls for the same text.
    Returns empty string if translation fails.
    """
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
    """Shorten text to max length, adding ellipsis if needed."""
    text = str(text or '').strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def merchant_label_english(merchant: str) -> str:
    """English-only merchant name (never Chinese).

    Returns 'Unknown merchant' if merchant is empty or untranslatable.
    """
    merchant = str(merchant or '').strip()
    if not merchant:
        return 'Unknown merchant'
    if not has_cjk(merchant):
        return shorten(merchant, 28)
    translated = translate_to_english(merchant)
    translated = _sanitize_english(translated, '')
    return shorten(translated, 28) if translated else 'Unknown merchant'


def description_label_english(description: str) -> str:
    """English-only description (never Chinese).

    Returns empty string if description is empty, slash-only, or untranslatable.
    """
    description = str(description or '').strip()
    if not description or description == '/':
        return ''
    if not has_cjk(description):
        return shorten(description, 80)
    translated = translate_to_english(description)
    translated = _sanitize_english(translated, '')
    return shorten(translated, 80) if translated else ''
