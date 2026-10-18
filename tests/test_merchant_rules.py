"""Safety-net regression tests for merchant_categories.py rule fragility.

Rule matches are trusted at confidence=1.0 and never routed to review, so a
false-positive here is invisible in production. These tests pin down the
specific failure modes found during a rule audit (short/generic patterns
colliding with unrelated merchants or with verbs in free-text descriptions)
so they can't silently regress, and guard against new equally-fragile
patterns being added later.
"""
import pandas as pd
import pytest

from label import apply_merchant_rules
from merchant_categories import MERCHANT_CATEGORY_RULES, special_category

# Short brand codes/abbreviations that are legitimately safe despite their
# length (well-known exact brand names, not ordinary words).
SHORT_PATTERN_ALLOWLIST = {
    "lg", "hp", "ems", "kfc", "b站", "lv", "**", "ws**1", "**店",
    "m.i", "12306", "amd", "gap", "asos", "kkv", "h&m", "dji", "p2p", "tip",
}
MIN_SAFE_PATTERN_LENGTH = 4


@pytest.fixture
def rules():
    # The global rule set as seeded into merchant_rules.
    return {p.lower(): c for p, c in MERCHANT_CATEGORY_RULES}


# --- Decoy-corpus regression cases -------------------------------------

DECOY_MERCHANT_CASES = [
    # (merchant, expected_category, note)
    ("Alex's Pizza", "Eating Out", "bare 'alex' personal-name rule removed"),
    ("Bankside Cafe", "Eating Out", "bare 'bank' catch-all removed"),
    ("Hi-Lo Bakery", "Groceries", "bare 'Hi' personal-name rule removed"),
]


@pytest.mark.parametrize("merchant,expected,note", DECOY_MERCHANT_CASES)
def test_decoy_merchants_not_hijacked(rules, merchant, expected, note):
    df = pd.DataFrame({"merchant": [merchant], "description": ["x"], "amount": [1.0]})
    out = apply_merchant_rules(df, rules)
    got = out.iloc[0]["category"]
    assert got == expected, f"{note}: {merchant!r} matched {got!r}, expected {expected!r}"


DECOY_DESCRIPTION_CASES = [
    "watch a movie together",
    "watch out for the delivery",
]


@pytest.mark.parametrize("description", DECOY_DESCRIPTION_CASES)
def test_watch_verb_in_description_not_hijacked_to_shopping(description):
    # An unrelated, unmapped merchant with a "watch"-containing description
    # must not be overridden to Shopping by DESCRIPTION_KEYWORD_RULES.
    result = special_category("Random Unmapped Merchant XYZ", description)
    assert result != "Shopping", f"description {description!r} incorrectly triggered Shopping"


METRO_STATION_DESCRIPTION_CASES = [
    "Metro card top-up near Houtan",
    "地铁站-后滩",
    "Jing'an Temple exit 3",
    "静安寺地铁站",
    "Lujiazui station",
    "陆家嘴地铁",
    "Hongqiao transfer",
    "虹桥火车站",
    "Pudong line 2",
    "浦东大道",
    "Century Avenue interchange",
    "世纪大道",
]


@pytest.mark.parametrize("description", METRO_STATION_DESCRIPTION_CASES)
def test_metro_station_names_classify_as_transportation(description):
    result = special_category("Random Unmapped Merchant XYZ", description)
    assert result == "Transportation", f"description {description!r} did not classify as Transportation"


# --- Structural guards ---------------------------------------------------

def test_no_dangerously_short_unallowlisted_patterns():
    """New short/generic ASCII patterns are the main source of silent false
    positives (e.g. bare English words/names as substrings).

    Scoped to ASCII patterns only: a 2-4 character CJK pattern (e.g. "山姆",
    "星巴克") is typically already a specific brand name, not a generic
    collision risk the way a 2-4 letter English word/name is.

    Any ASCII pattern under MIN_SAFE_PATTERN_LENGTH chars must be explicitly
    allow-listed as a known-safe brand code/abbreviation.
    """
    offenders = []
    for pattern, _category in MERCHANT_CATEGORY_RULES:
        if not pattern.isascii():
            continue
        if len(pattern) < MIN_SAFE_PATTERN_LENGTH and pattern.lower() not in SHORT_PATTERN_ALLOWLIST:
            offenders.append(pattern)
    assert not offenders, (
        f"Short pattern(s) not in SHORT_PATTERN_ALLOWLIST: {offenders}. "
        "Bare short/generic patterns are never reviewed and silently misfire on "
        "unrelated merchants — add to the allowlist only if genuinely a specific "
        "brand code, otherwise use a longer/more specific pattern."
    )


def test_bare_bank_rule_removed():
    """Bare 'bank'/'Bank' was the single most generic collision-prone rule in
    the file; explicit bank names should carry this category instead."""
    all_patterns_lower = {p.lower() for p, _ in MERCHANT_CATEGORY_RULES}
    assert "bank" not in all_patterns_lower


# --- Description keywords: word boundaries + rule precedence (Session 77) ---

@pytest.mark.parametrize("description,not_category", [
    ("current account fee", "Housing"),          # "rent" inside "current"
    ("facebook ads", "Shopping"),                # "book" inside "facebook"
    ("override charge", "Transportation"),       # "ride" inside "override"
    ("refund for order 12", "Investments"),      # "fund" inside "refund"
    ("面包 bakery", "Eating Out"),                # 面 inside 面包 (bread)
])
def test_keywords_do_not_fire_inside_other_words(description, not_category):
    assert special_category("Random Unmapped Merchant XYZ", description) != not_category


@pytest.mark.parametrize("description,category", [
    ("monthly rent", "Housing"),
    ("noodles to go", "Eating Out"),
    ("two books", "Shopping"),
    ("牛肉拉面", "Eating Out"),
])
def test_keywords_still_match_whole_words_and_plurals(description, category):
    assert special_category("Random Unmapped Merchant XYZ", description) == category


def test_merchant_rule_beats_description_keyword():
    from classify import classify_all

    df = pd.DataFrame({
        "merchant": ["Starbucks Coffee", "Unknown Shop"],
        "description": ["payment", "payment"],
        "amount": [30.0, 30.0],
    })
    out = classify_all(df, rules={"starbucks": "Eating Out"})
    assert out.loc[0, "category"] == "Eating Out"
    assert out.loc[0, "label_source"] == "rule"
    # Rows no rule covers still get the description override.
    assert out.loc[1, "category"] == "Transfers & Gifts"
    assert out.loc[1, "label_source"] == "override"
