"""Equivalence tests: optimized rule matching must match the old row-by-row logic.

These tests pin down that the performance rewrite of `apply_merchant_rules`
(src/label.py) and `apply_description_overrides` (src/classify.py) produces
byte-identical output to the original implementations they replaced.

The original (slow) implementations are reproduced here as reference oracles.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

# jieba does not build in CI; mock it before importing project modules.
if 'jieba' not in sys.modules:
    sys.modules['jieba'] = MagicMock()
    sys.modules['jieba'].cut = lambda text, cut_all=False: text.split()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

from label import apply_merchant_rules  # noqa: E402
from classify import apply_description_overrides  # noqa: E402
from merchant_categories import rules_as_dict, special_category  # noqa: E402


# --- Reference (original) implementations -----------------------------------

def _old_apply_merchant_rules(df: pd.DataFrame, rules: dict) -> pd.DataFrame:
    df = df.copy()
    df['category'] = pd.NA
    df['labeled'] = False
    for idx, row in df.iterrows():
        merchant = str(row['merchant']).strip().lower()
        if merchant in rules:
            df.loc[idx, 'category'] = rules[merchant]
            df.loc[idx, 'labeled'] = True
            continue
        for pattern, category in sorted(rules.items(), key=lambda x: len(x[0]), reverse=True):
            if pattern in merchant:
                df.loc[idx, 'category'] = category
                df.loc[idx, 'labeled'] = True
                break
    return df


def _old_apply_description_overrides(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for idx, row in df.iterrows():
        merchant = str(row['merchant'])
        desc = str(row['description'])
        merchant_lower = merchant.lower()
        special = special_category(merchant, desc)
        if special is not None:
            df.loc[idx, 'category'] = special
            df.loc[idx, 'confidence'] = 1.0
            df.loc[idx, 'needs_review'] = False
            if 'label_source' in df.columns:
                df.loc[idx, 'label_source'] = 'override'
            continue
        if 'catering' in merchant_lower or '餐饮' in merchant:
            df.loc[idx, 'category'] = 'Eating Out'
            df.loc[idx, 'confidence'] = 1.0
            df.loc[idx, 'needs_review'] = False
            if 'label_source' in df.columns:
                df.loc[idx, 'label_source'] = 'override'
    return df


# --- Fixtures ----------------------------------------------------------------

@pytest.fixture
def rules():
    return rules_as_dict()


@pytest.fixture
def transactions():
    """~50 transactions covering the tricky cases the rewrite must preserve."""
    merchants = [
        "星巴克",                    # exact / substring chain match
        "Starbucks Coffee",         # english substring
        "美团外卖订单",              # overlapping patterns (longest wins)
        "Nike Store 123",           # brand substring
        "ws**1",                    # masked taobao local rule
        "完全未知的商家XYZ",         # unknown merchant, no match
        "Random Merchant 999",      # unknown, no match
        "Bank of China ATM",        # bank -> transfers
        "catering services ltd",    # catering override path
        "某餐饮公司",                # 餐饮 override path
        "上海纽约大学",              # NYU special_category
        "上海蕤盛工贸",              # metro special_category
        "",                         # empty merchant
        "MART",                     # uppercase keyword -> lowercased match
    ]
    descriptions = [
        "coffee order",
        "latte",
        "noodle delivery",
        "blue shoes size 8",
        "some product",
        "vegetables and fruits",   # description keyword -> Groceries
        "ride to airport",         # description keyword -> Transportation
        "cash withdrawal",
        "food",
        "lunch",
        "Campus Card Top Up",      # NYU -> Utilities & Services
        "metro ride",
        "nothing here",
        "weekly shop",
    ]
    # Repeat to ~50 rows and vary index to ensure alignment is index-safe.
    n_repeat = 4
    m = (merchants * n_repeat)
    d = (descriptions * n_repeat)
    df = pd.DataFrame({
        'merchant': m,
        'description': d,
        'amount': [round(10 + i * 1.5, 2) for i in range(len(m))],
    })
    # non-default, non-monotonic index to catch index-alignment bugs
    df.index = list(range(100, 100 + len(df)))
    return df


# --- Tests -------------------------------------------------------------------

def test_apply_merchant_rules_equivalence(transactions, rules):
    old = _old_apply_merchant_rules(transactions, rules)
    new = apply_merchant_rules(transactions, rules)

    # Compare category (normalizing NA) and labeled exactly.
    assert list(old['category'].fillna('<NA>')) == list(new['category'].fillna('<NA>'))
    assert list(old['labeled'].astype(bool)) == list(new['labeled'].astype(bool))


def test_apply_description_overrides_equivalence_with_model_columns(transactions):
    # Simulate the state inside classify_all: category/confidence/label_source set.
    df = transactions.copy()
    df['category'] = 'Other'
    df['confidence'] = 0.5
    df['label_source'] = 'model'

    old = _old_apply_description_overrides(df)
    new = apply_description_overrides(df)

    for col in ['category', 'confidence', 'label_source']:
        assert list(old[col].fillna('<NA>')) == list(new[col].fillna('<NA>')), col
    # needs_review column created by the override path
    assert ('needs_review' in old.columns) == ('needs_review' in new.columns)
    if 'needs_review' in old.columns:
        assert list(old['needs_review'].fillna('<NA>')) == list(new['needs_review'].fillna('<NA>'))


def test_apply_description_overrides_equivalence_without_label_source(transactions):
    df = transactions.copy()
    df['category'] = 'Other'
    df['confidence'] = 0.5

    old = _old_apply_description_overrides(df)
    new = apply_description_overrides(df)

    for col in ['category', 'confidence']:
        assert list(old[col].fillna('<NA>')) == list(new[col].fillna('<NA>')), col
    assert ('label_source' in old.columns) == ('label_source' in new.columns)


def test_merchant_rules_single_and_empty(rules):
    # single row
    df1 = pd.DataFrame({'merchant': ['星巴克'], 'description': ['x'], 'amount': [1.0]})
    assert apply_merchant_rules(df1, rules)['labeled'].iloc[0] == True  # noqa: E712

    # empty df
    df0 = pd.DataFrame({'merchant': [], 'description': [], 'amount': []})
    out = apply_merchant_rules(df0, rules)
    assert len(out) == 0
    assert 'category' in out.columns and 'labeled' in out.columns
