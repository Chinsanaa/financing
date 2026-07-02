"""Cross-validation helpers, including the merchant-leakage guard.

Phase 1 of the integrity audit showed that stratified CV on this dataset
inflates accuracy from ~36% (honest, unseen merchants) to ~96% because the same
merchant appears in both train and test folds and the merchant name is part of
the vectorized text. `assert_no_group_leakage` is the guard that makes that
mistake fail loudly instead of silently inflating a metric.
"""
from __future__ import annotations
from typing import Iterable, Sequence
import numpy as np


class GroupLeakageError(AssertionError):
    """Raised when a group (e.g. merchant) appears in both train and test."""


def assert_no_group_leakage(
    groups: Sequence,
    train_idx: Iterable[int],
    test_idx: Iterable[int],
) -> None:
    """Fail if any group value appears in both the train and test index sets.

    Use with GroupKFold-style splits where a group (merchant) must never
    straddle the split. Raises GroupLeakageError on overlap.
    """
    g = np.asarray(groups, dtype=object)
    train_groups = set(g[np.asarray(list(train_idx), dtype=int)])
    test_groups = set(g[np.asarray(list(test_idx), dtype=int)])
    overlap = train_groups & test_groups
    if overlap:
        sample = sorted(map(str, overlap))[:5]
        raise GroupLeakageError(
            f"Merchant leakage: {len(overlap)} group(s) in both train and test "
            f"(e.g. {sample}). Use GroupKFold(groups=merchant), not StratifiedKFold."
        )
