import math

import numpy as np

from ai_engine.evaluation.statistics import (
    holm_adjust,
    paired_bootstrap_interval,
    paired_sign_flip_pvalue,
)


def test_paired_bootstrap_preserves_constant_seed_differences():
    mean, low, high, count = paired_bootstrap_interval(
        [0.25] * 30,
        rng=np.random.default_rng(4),
    )
    assert (mean, low, high, count) == (0.25, 0.25, 0.25, 30)


def test_paired_bootstrap_marks_single_seed_interval_unavailable():
    mean, low, high, count = paired_bootstrap_interval(
        [0.25], rng=np.random.default_rng(4)
    )
    assert mean == 0.25
    assert math.isnan(low) and math.isnan(high)
    assert count == 1


def test_sign_flip_is_deterministic_and_zero_effect_is_not_significant():
    p_a = paired_sign_flip_pvalue([0.0, 0.0, 0.0], rng=np.random.default_rng(9))
    p_b = paired_sign_flip_pvalue([0.0, 0.0, 0.0], rng=np.random.default_rng(9))
    assert p_a == p_b == 1.0


def test_holm_adjustment_is_monotonic_in_sorted_p_values():
    assert holm_adjust([0.01, 0.04, 0.03]) == [0.03, 0.06, 0.06]

