"""Seed-level paired bootstrap and multiple-comparison utilities."""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np


def paired_bootstrap_interval(
    differences: Iterable[float],
    *,
    rng: np.random.Generator,
    replicates: int = 10_000,
) -> tuple[float, float, float, int]:
    values = np.asarray([x for x in differences if math.isfinite(float(x))], dtype=float)
    n = int(values.size)
    if n == 0:
        return math.nan, math.nan, math.nan, 0
    mean = float(np.mean(values))
    if n == 1:
        return mean, math.nan, math.nan, n
    samples = rng.choice(values, size=(replicates, n), replace=True)
    low, high = np.percentile(np.mean(samples, axis=1), [2.5, 97.5])
    return mean, float(low), float(high), n


def paired_sign_flip_pvalue(
    differences: Iterable[float],
    *,
    rng: np.random.Generator,
    replicates: int = 10_000,
) -> float:
    values = np.asarray([x for x in differences if math.isfinite(float(x))], dtype=float)
    if values.size == 0:
        return math.nan
    observed = abs(float(np.mean(values)))
    if observed == 0.0:
        return 1.0
    signs = rng.choice(np.asarray([-1.0, 1.0]), size=(replicates, values.size))
    null_means = np.abs(np.mean(signs * values, axis=1))
    exceedances = int(np.count_nonzero(null_means >= observed))
    return (exceedances + 1) / (replicates + 1)


def holm_adjust(p_values: Iterable[float]) -> list[float]:
    """Return Holm-adjusted p-values in the original order."""
    values = [float(value) for value in p_values]
    finite_positions = [index for index, value in enumerate(values) if math.isfinite(value)]
    ordered = sorted(finite_positions, key=lambda index: values[index])
    adjusted = [math.nan] * len(values)
    running_max = 0.0
    count = len(ordered)
    for rank, index in enumerate(ordered):
        candidate = min(1.0, (count - rank) * values[index])
        running_max = max(running_max, candidate)
        adjusted[index] = running_max
    return adjusted
