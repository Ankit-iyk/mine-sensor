"""
SUBSENSE — Rolling Window Management & Statistics (Phase 3)

Configures and calculates rolling statistical aggregations over temporal windows:
- Short window (e.g. 5 seconds / samples)
- Medium window (e.g. 30 seconds / samples)
- Long window (e.g. 60 seconds / samples)
"""

from dataclasses import dataclass
from typing import Sequence
import numpy as np


@dataclass(frozen=True)
class WindowConfig:
    """Central configuration for temporal rolling windows."""
    short_window_samples: int = 5      # Fast transient detection (~5s at 1Hz)
    medium_window_samples: int = 30    # Micro-creep and temporal trend (~30s at 1Hz)
    long_window_samples: int = 60      # Statistical baseline & persistence (~60s at 1Hz)


default_window_config = WindowConfig()


def rolling_mean(series: Sequence[float] | np.ndarray) -> float:
    """Calculate arithmetic mean of a sequence. Returns 0.0 if empty."""
    arr = np.asarray(series, dtype=np.float64)
    if arr.size == 0:
        return 0.0
    return round(float(np.mean(arr)), 4)


def rolling_std(series: Sequence[float] | np.ndarray) -> float:
    """Calculate sample standard deviation of a sequence. Returns 0.0 if fewer than 2 elements."""
    arr = np.asarray(series, dtype=np.float64)
    if arr.size <= 1:
        return 0.0
    return round(float(np.std(arr)), 4)


def rolling_peak(series: Sequence[float] | np.ndarray) -> float:
    """Calculate maximum absolute peak in the sequence. Returns 0.0 if empty."""
    arr = np.asarray(series, dtype=np.float64)
    if arr.size == 0:
        return 0.0
    return round(float(np.max(np.abs(arr))), 4)


def rate_of_change(series: Sequence[float] | np.ndarray, dt_seconds: float = 1.0) -> float:
    """
    Calculate rate of change (derivative / linear trend slope) per second.
    Uses closed-form linear regression slope across the series:
        slope = cov(t, y) / var(t)
    """
    arr = np.asarray(series, dtype=np.float64)
    n = arr.size
    if n < 2:
        return 0.0

    t = np.arange(n, dtype=np.float64) * max(0.01, dt_seconds)
    t_mean = np.mean(t)
    y_mean = np.mean(arr)
    t_var = np.sum((t - t_mean) ** 2)

    if t_var < 1e-9:
        return 0.0

    cov = np.sum((t - t_mean) * (arr - y_mean))
    return round(float(cov / t_var), 5)
