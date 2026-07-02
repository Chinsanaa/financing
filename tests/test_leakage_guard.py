"""Leakage guard: fail if a train/test split shares merchants when grouping is expected."""
import numpy as np
import pytest
from sklearn.model_selection import GroupKFold, StratifiedKFold

from cv_utils import assert_no_group_leakage, GroupLeakageError


def test_groupkfold_has_no_merchant_leakage(synthetic_labeled):
    df = synthetic_labeled.reset_index(drop=True)
    groups = df["merchant"].values
    gkf = GroupKFold(n_splits=4)
    # Every GroupKFold fold must pass the guard.
    for train_idx, test_idx in gkf.split(df, df["category"], groups):
        assert_no_group_leakage(groups, train_idx, test_idx)


def test_guard_catches_stratified_leakage(synthetic_labeled):
    df = synthetic_labeled.reset_index(drop=True)
    groups = df["merchant"].values
    skf = StratifiedKFold(n_splits=4, shuffle=True, random_state=42)
    # StratifiedKFold ignores merchants, so with 4 rows/merchant across 4 folds
    # a merchant will straddle the split → the guard MUST fire on at least one.
    leaked = False
    for train_idx, test_idx in skf.split(df, df["category"]):
        try:
            assert_no_group_leakage(groups, train_idx, test_idx)
        except GroupLeakageError:
            leaked = True
    assert leaked, "Guard failed to detect known merchant leakage in stratified split"


def test_guard_raises_on_explicit_overlap():
    groups = np.array(["A", "A", "B", "B"])
    with pytest.raises(GroupLeakageError):
        assert_no_group_leakage(groups, train_idx=[0, 2], test_idx=[1, 3])
