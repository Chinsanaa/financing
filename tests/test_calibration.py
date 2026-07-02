"""Calibration: monotonicity, ECE reduction, and honest threshold derivation."""
import numpy as np

from calibration import (
    fit_top_label_calibrator,
    apply_calibrator,
    expected_calibration_error,
    reliability_table,
)
from eval_grouped import derive_threshold


def test_apply_calibrator_is_monotonic():
    rng = np.random.default_rng(0)
    raw_conf = rng.uniform(0.3, 1.0, 500)
    # correctness genuinely increases with raw confidence (well-behaved case)
    correct = (rng.uniform(0, 1, 500) < raw_conf).astype(int)

    cal = fit_top_label_calibrator(raw_conf, correct)
    order = np.argsort(raw_conf)
    calibrated = apply_calibrator(cal, raw_conf[order])

    diffs = np.diff(calibrated)
    assert (diffs >= -1e-9).all(), "calibrated confidence must be non-decreasing in raw confidence"


def test_apply_calibrator_identity_passthrough_when_none():
    raw = np.array([0.1, 0.5, 0.9])
    np.testing.assert_array_equal(apply_calibrator(None, raw), raw)


def test_ece_decreases_on_overconfident_synthetic_set():
    rng = np.random.default_rng(1)
    n = 400
    raw_conf = np.full(n, 0.9)  # always claims 90% confident...
    correct = (rng.uniform(0, 1, n) < 0.4).astype(int)  # ...but only 40% right

    ece_before = expected_calibration_error(raw_conf, correct)
    cal = fit_top_label_calibrator(raw_conf, correct)
    calibrated = apply_calibrator(cal, raw_conf)
    ece_after = expected_calibration_error(calibrated, correct)

    assert ece_before > 0.3  # badly miscalibrated to start (matches audit's 0.184-0.4 range)
    assert ece_after < ece_before


def test_fit_top_label_calibrator_degenerate_inputs_return_none():
    # too few pairs
    assert fit_top_label_calibrator([0.9, 0.8], [1, 1]) is None
    # all-correct: nothing to calibrate against
    assert fit_top_label_calibrator(np.full(20, 0.9), np.ones(20)) is None


def test_reliability_table_bins_sum_to_total():
    rng = np.random.default_rng(2)
    conf = rng.uniform(0, 1, 300)
    correct = rng.integers(0, 2, 300)
    table = reliability_table(conf, correct, n_bins=10)
    assert table['n'].sum() == 300


def test_derive_threshold_none_when_target_unreachable():
    import pandas as pd
    # Agreement rows exist but accuracy is mediocre everywhere -> no threshold
    # should reach 0.90 precision.
    rng = np.random.default_rng(3)
    n = 200
    df = pd.DataFrame({
        'agree': np.full(n, True),
        'is_other': np.full(n, False),
        'ensemble_conf': rng.uniform(0.5, 0.95, n),
        'correct': rng.uniform(0, 1, n) < 0.6,  # only 60% precision, never hits 90%
    })
    result = derive_threshold(df, target_precision=0.90, min_support=10)
    assert result is None


def test_derive_threshold_finds_safe_cutoff():
    import pandas as pd
    rng = np.random.default_rng(4)
    n = 200
    conf = rng.uniform(0.5, 0.99, n)
    # correctness strongly tied to confidence: high-conf rows are reliably right
    correct = conf > rng.uniform(0.3, 0.7, n)
    df = pd.DataFrame({
        'agree': np.full(n, True),
        'is_other': np.full(n, False),
        'ensemble_conf': conf,
        'correct': correct,
    })
    result = derive_threshold(df, target_precision=0.85, min_support=10)
    assert result is not None
    assert result['precision'] >= 0.85
    assert result['n'] >= 10
