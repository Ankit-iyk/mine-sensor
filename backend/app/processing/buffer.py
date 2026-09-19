"""
SUBSENSE — Temporal Buffer & Node State Management (Phase 5)

Maintains in-memory rolling windows per node:
- Sliding deque of recent samples (default: 60 seconds / readings)
- Node baseline tracking (calibrates undisturbed reference angles)
- Conversion to structured NumPy arrays for vectorised feature extraction
"""

from collections import deque
from datetime import datetime
import math
from typing import Optional
import numpy as np

from app.processing.schemas import ProcessedSample


class NodeBuffer:
    """
    Sliding window buffer and baseline reference tracker for one sensor node.
    """

    def __init__(self, node_id: str, max_size: int = 60, baseline_init_samples: int = 30) -> None:
        self.node_id = node_id
        self.max_size = max_size
        self.baseline_init_samples = baseline_init_samples

        self._buffer: deque[ProcessedSample] = deque(maxlen=max_size)

        # Baseline angles (undisturbed ground level)
        self.baseline_tilt_x: Optional[float] = None
        self.baseline_tilt_y: Optional[float] = None
        self.baseline_calibrated: bool = False

    def add_sample(self, sample: ProcessedSample) -> None:
        """Add a new processed sample to the rolling window."""
        self._buffer.append(sample)

        # Calibrate baseline if not yet calibrated
        if not self.baseline_calibrated:
            if len(self._buffer) >= min(self.baseline_init_samples, 10):
                # Median across initial samples gives a robust baseline against initial transients
                samples_x = [s.tilt_x for s in self._buffer]
                samples_y = [s.tilt_y for s in self._buffer]
                self.baseline_tilt_x = float(np.median(samples_x))
                self.baseline_tilt_y = float(np.median(samples_y))
                self.baseline_calibrated = True

    def calculate_deviation(self, tilt_x: float, tilt_y: float) -> float:
        """
        Calculate scalar tilt deviation from node baseline in degrees.
        If baseline not calibrated yet, returns deviation from current sample (0.0).
        """
        if not self.baseline_calibrated or self.baseline_tilt_x is None or self.baseline_tilt_y is None:
            return 0.0

        dx = tilt_x - self.baseline_tilt_x
        dy = tilt_y - self.baseline_tilt_y
        return math.sqrt(dx * dx + dy * dy)

    @property
    def size(self) -> int:
        return len(self._buffer)

    @property
    def is_ready(self) -> bool:
        """Buffer has sufficient history to extract meaningful features (>= 5 samples)."""
        return len(self._buffer) >= 5

    def get_latest(self) -> Optional[ProcessedSample]:
        if not self._buffer:
            return None
        return self._buffer[-1]

    def get_tilt_magnitudes(self) -> np.ndarray:
        return np.array([s.tilt_magnitude for s in self._buffer], dtype=np.float64)

    def get_tilt_x_series(self) -> np.ndarray:
        return np.array([s.tilt_x for s in self._buffer], dtype=np.float64)

    def get_tilt_y_series(self) -> np.ndarray:
        return np.array([s.tilt_y for s in self._buffer], dtype=np.float64)

    def get_rates(self) -> np.ndarray:
        return np.array([math.sqrt(s.rate_x**2 + s.rate_y**2) for s in self._buffer], dtype=np.float64)

    def get_vibrations_norm(self) -> np.ndarray:
        return np.array([s.vibration_norm for s in self._buffer], dtype=np.float64)

    def get_accel_magnitudes(self) -> np.ndarray:
        return np.array([s.accel_magnitude for s in self._buffer], dtype=np.float64)

    def get_timestamps(self) -> list[datetime]:
        return [s.timestamp for s in self._buffer]

