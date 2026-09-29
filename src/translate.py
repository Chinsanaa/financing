"""Translate transaction text to English for the web UI.

Hard rule: the web UI should never display Chinese text. If translation fails,
return a safe English placeholder instead of leaking original CJK text.
"""
import re
import threading
from typing import Optional


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


GOOGLE_TIMEOUT_SECONDS = 10


def _google_translate(text: str) -> str:
    """One Google Translate call with a hard time limit.

    deep_translator calls requests.get without a timeout, so a stalled
    connection can block forever (this froze the background translation
    worker on 2026-09-29). The call runs on a throwaway daemon thread and we
    wait at most GOOGLE_TIMEOUT_SECONDS; on timeout we give up and return ''
    (a failure — the caller retries later). A stalled daemon thread is
    abandoned, which is harmless: it holds no locks and dies with the process.
    """
    result: dict = {}

    def _call():
        try:
            from deep_translator import GoogleTranslator
            result['text'] = GoogleTranslator(source='auto', target='en').translate(text[:500]) or ''
        except Exception:
            result['text'] = ''

    t = threading.Thread(target=_call, name='google-translate', daemon=True)
    t.start()
    t.join(GOOGLE_TIMEOUT_SECONDS)
    return str(result.get('text') or '').strip()


_TRANSLATION_CACHE_MAX = 4096
_translation_cache: dict = {}


def translate_to_english(text: str) -> str:
    """Translate text to English via Google (a live network call); return
    unchanged if already non-CJK.

    Only successful translations are cached — a failure (timeout after
    GOOGLE_TIMEOUT_SECONDS, 429)
    returns '' uncached so the next attempt can succeed. (The previous
    lru_cache also memoized failures, pinning a blank label until restart.)

    Write-path only: request handlers must use the `*_stored` label
    functions below, which never touch the network.
    """
    text = str(text or '').strip()
    if not text:
        return ''
    if not has_cjk(text):
        return text
    cached = _translation_cache.get(text)
    if cached is not None:
        return cached
    translated = _google_translate(text)
    if translated:
        if len(_translation_cache) >= _TRANSLATION_CACHE_MAX:
            _translation_cache.clear()
        _translation_cache[text] = translated
    return translated


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


# --- Stored translations (transactions.merchant_en / description_en) ---
#
# Translating on every page load meant one serial Google call per Chinese
# string (~200 for one Reports page). Instead, backend/translations.py
# translates each distinct string ONCE in the background after upload and
# stores the result on the row; the request path only formats stored text.


def english_for_storage(text: str) -> Optional[str]:
    """Value to store in a `*_en` column for `text`, or None to retry later.

    Non-CJK text (and empty text) is stored as-is so the row never needs
    another pass; CJK text is machine-translated (network call). None means
    translation failed — the column stays NULL and a later pass retries.
    """
    text = str(text or '').strip()
    if not text or not has_cjk(text):
        return text
    translated = _sanitize_english(translate_to_english(text), '')
    return translated or None


def merchant_label_stored(merchant: str, merchant_en: Optional[str]) -> str:
    """English-only merchant label from the stored translation — no network.

    Curated names (src/merchant_display.py) still win, so improving that map
    takes effect immediately without re-translating stored rows.
    """
    from src.merchant_display import curated_merchant_name
    merchant = str(merchant or '').strip()
    if not merchant:
        return 'Unknown merchant'
    curated = curated_merchant_name(merchant)
    if curated:
        return curated
    if not has_cjk(merchant):
        return merchant
    return shorten(_sanitize_english(merchant_en, 'Unknown merchant'), 28)


def description_label_stored(description: str, description_en: Optional[str]) -> str:
    """English-only description from the stored translation — no network."""
    description = str(description or '').strip()
    if not description or description == '/':
        return ''
    if not has_cjk(description):
        return shorten(description, 80)
    translated = _sanitize_english(description_en, '')
    return shorten(translated, 80) if translated else ''
