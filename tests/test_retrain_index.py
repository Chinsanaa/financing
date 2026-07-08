"""Regression test for the retrain/classify positional-index bug.

extract_numeric_features() returns df.index (LABEL index). The retrain path
slices with .iloc (POSITIONAL). When the pre-training row filters (labeled /
category / min-class) leave a gappy index, .iloc[valid_indices] overflowed with
"positional indexers are out-of-bounds". The fix resets the index before feature
extraction (retrain.py) and uses .loc in the inference path (classify.py). These
tests pin the filter -> reset -> extract -> .iloc contract that the fix restores.
"""
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

# Mock jieba so importing the feature module doesn't require the real dependency.
if 'jieba' not in sys.modules:
    sys.modules['jieba'] = MagicMock()
    sys.modules['jieba'].cut = lambda text, cut_all=False: text.split()

from src.feature_engineering import extract_numeric_features


def _labeled_frame_with_singleton_class() -> pd.DataFrame:
    """12 labeled rows across 3 valid categories + 1 singleton class.

    The singleton class is what the retrain '< 2 samples per class' filter drops,
    which is what leaves the surviving index non-contiguous (the bug trigger).
    """
    n = 12
    dates = [datetime(2026, 5, 1) + timedelta(days=i) for i in range(n)]
    # Singleton class FIRST (index 0). Dropping an early row is what pushes a
    # surviving label (11) past the new length (11) so .iloc[11] overflows —
    # dropping the last row would leave a harmless contiguous 0..n-1 index.
    categories = ['Shopping'] + (['Groceries'] * 4) + (['Eating Out'] * 4) + (['Transportation'] * 3)
    return pd.DataFrame({
        'merchant': [f'Merchant {i}' for i in range(n)],
        'description': [f'desc {i}' for i in range(n)],
        'amount': np.linspace(20, 100, n),
        'timestamp': dates,
        'category': categories,
        'is_manually_labeled': [True] * n,
    })


def _apply_retrain_prefilter(df: pd.DataFrame) -> pd.DataFrame:
    """Mirror retrain.py lines ~76-96 + the index reset the fix added."""
    df = df[df['is_manually_labeled'] == True].copy()  # noqa: E712 - pandas mask
    min_class_count = df['category'].value_counts().min()
    if min_class_count < 2:
        keep = df['category'].value_counts()[df['category'].value_counts() >= 2].index
        df = df[df['category'].isin(keep)].copy()
    # The fix: reset so positional == label before feature extraction.
    df = df.reset_index(drop=True)
    return df


def test_singleton_filter_produces_gappy_index_without_reset():
    """Sanity: without the reset, the surviving index really is gappy (bug setup)."""
    df = _labeled_frame_with_singleton_class()
    df = df[df['is_manually_labeled'] == True].copy()  # noqa: E712
    keep = df['category'].value_counts()[df['category'].value_counts() >= 2].index
    filtered = df[df['category'].isin(keep)].copy()

    # Shopping (index 0) is dropped -> surviving labels are 1..11 with length 11,
    # so the max label (11) >= len (11). That's exactly the condition that made
    # .iloc[valid_indices] overflow before the reset was added.
    assert 0 not in filtered.index
    assert max(filtered.index) >= len(filtered)


def test_retrain_prefilter_then_iloc_does_not_raise():
    """The regressed path: filter -> reset -> extract -> .iloc[valid_indices]."""
    df = _apply_retrain_prefilter(_labeled_frame_with_singleton_class())
    y = df['category']

    numeric_features, valid_indices = extract_numeric_features(df)

    # This is retrain.py:117-118 — it must not raise now that the index is reset.
    df_valid = df.iloc[valid_indices].copy()
    y_valid = y.iloc[valid_indices]

    assert len(df_valid) == len(numeric_features)
    assert len(y_valid) == len(numeric_features)
    # The singleton class was filtered out before training.
    assert 'Shopping' not in set(y_valid)


def test_classify_style_loc_indexing_on_gappy_index():
    """The inference path uses .loc[valid_indices]; verify it aligns on a gappy index."""
    df = _labeled_frame_with_singleton_class()
    # Force a gappy index directly (drop a couple of rows, no reset) as classify's
    # inference df is never reset — .loc must still line up with the returned labels.
    df = df.drop(index=[1, 3]).copy()

    numeric_features, valid_indices = extract_numeric_features(df)

    df_valid = df.loc[valid_indices].copy()  # classify.py:262 after the fix
    assert len(df_valid) == len(numeric_features)
    # Labels are preserved, so writing back via df.loc[df_valid.index] stays aligned.
    assert set(df_valid.index).issubset(set(df.index))
