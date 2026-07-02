"""Translate Chinese transaction text to English for the labeling UI."""
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
    """Translate text to English; return unchanged if already Latin-only."""
    text = str(text or '').strip()
    if not text:
        return ''
    if not has_cjk(text):
        return text
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source='auto', target='en').translate(text[:500])
        return (translated or text).strip()
    except Exception:
        return text


def merchant_for_label(merchant: str) -> str:
    """English-friendly merchant name for the label UI."""
    merchant = str(merchant or '').strip()
    if not merchant:
        return ''
    mapped = display_merchant(merchant)
    if mapped != merchant and _mostly_ascii(mapped):
        return mapped
    return translate_to_english(merchant)


def description_for_label(description: str) -> str:
    """English-friendly description for the label UI."""
    description = str(description or '').strip()
    if not description or description == '/':
        return ''
    if not has_cjk(description):
        return description
    return translate_to_english(description)


def enrich_label_row(merchant: str, description: str) -> dict:
    """Build label-queue fields with originals + English display strings."""
    merchant = str(merchant or '').strip()
    description = str(description or '').strip()
    merchant_en = merchant_for_label(merchant)
    description_en = description_for_label(description)
    return {
        'merchant': merchant,
        'merchant_en': merchant_en,
        'sample_description': description[:120],
        'sample_description_en': description_en[:200] if description_en else '',
        'show_original': (
            merchant_en != merchant
            or (bool(description_en) and description_en != description)
        ),
    }
