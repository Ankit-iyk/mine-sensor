"""
SUBSENSE — Per-Node Baseline Management & Protection (Phase 3)

Maintains individualized operational baselines per node (e.g. N01, N02, N03):
- Tracks baseline mean and standard deviation for tilt and vibration.
- Baseline initialization from initial stable samples.
- BASELINE PROTECTION RULE: Abnormal periods (excessive tilt deviation or high vibration)
  are strictly prevented from corrupting or redefining the baseline.
- Stable updates use a controlled exponential moving average (EMA).
"""

import math
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class NodeBaselineState:
    """Individual baseline characteristics for a single sensor node."""
    node_id: str
    baseline_mean_x: float = 0.0
    baseline_mean_y: float = 0.0
    baseline_std_x: float = 0.05
    baseline_std_y: float = 0.05
    baseline_vib_mean: float = 10.0
    baseline_vib_std: float = 5.0
    calibrated: bool = False
    samples_seen: int = 0


class NodeBaselineTracker:
    """
    Manages per-node baselines with strict anti-corruption update protection.
    """

    def __init__(
        self,
        node_id: str,
        init_samples: int = 20,
        max_stable_tilt_deviation: float = 0.35,  # degrees
        max_stable_vibration: float = 150.0,     # ADC counts
        update_alpha: float = 0.01,              # EMA update weight during stable periods
    ) -> None:
        self.node_id = node_id
        self.init_samples = init_samples
        self.max_stable_tilt_deviation = max_stable_tilt_deviation
        self.max_stable_vibration = max_stable_vibration
        self.update_alpha = update_alpha

        self.state = NodeBaselineState(node_id=node_id)
        self._init_samples_x: list[float] = []
        self._init_samples_y: list[float] = []
        self._init_samples_vib: list[float] = []

    def observe(self, tilt_x: float, tilt_y: float, vibration: float) -> None:
        """
        Observe a new sample. Initializes the baseline or updates it IF the sample is stable.
        Abnormal samples are rejected from baseline updating to prevent learning subsidence as normal.
        """
        self.state.samples_seen += 1

        # Phase 1: Initialization
        if not self.state.calibrated:
            self._init_samples_x.append(tilt_x)
            self._init_samples_y.append(tilt_y)
            self._init_samples_vib.append(vibration)

            if len(self._init_samples_x) >= self.init_samples:
                # Use robust median for initial mean and std
                self.state.baseline_mean_x = float(np.median(self._init_samples_x))
                self.state.baseline_mean_y = float(np.median(self._init_samples_y))
                self.state.baseline_std_x = max(0.01, float(np.std(self._init_samples_x)))
                self.state.baseline_std_y = max(0.01, float(np.std(self._init_samples_y)))
                self.state.baseline_vib_mean = float(np.median(self._init_samples_vib))
                self.state.baseline_vib_std = max(1.0, float(np.std(self._init_samples_vib)))
                self.state.calibrated = True
            return

        # Phase 2: Controlled Update with Protection
        # Check whether the reading is stable
        current_dev = self.calculate_deviation(tilt_x, tilt_y)
        is_stable = (
            current_dev <= self.max_stable_tilt_deviation
            and vibration <= self.max_stable_vibration
        )

        if is_stable:
            # Slow exponential moving average to adapt to seasonal thermal shifts
            a = self.update_alpha
            self.state.baseline_mean_x = (1.0 - a) * self.state.baseline_mean_x + a * tilt_x
            self.state.baseline_mean_y = (1.0 - a) * self.state.baseline_mean_y + a * tilt_y
            self.state.baseline_vib_mean = (1.0 - a) * self.state.baseline_vib_mean + a * vibration
        # If NOT stable (e.g. subsidence event, drilling blast): DO NOTHING, preserving baseline!

    def calculate_deviation(self, tilt_x: float, tilt_y: float) -> float:
        """
        Calculate scalar Euclidean tilt deviation from this node's baseline:
            deviation = sqrt((tilt_x - mean_x)^2 + (tilt_y - mean_y)^2)
        """
        if not self.state.calibrated:
            return 0.0
        dx = tilt_x - self.state.baseline_mean_x
        dy = tilt_y - self.state.baseline_mean_y
        return round(float(math.sqrt(dx * dx + dy * dy)), 4)

    def calculate_normalized_deviation(self, tilt_x: float, tilt_y: float) -> float:
        """
        Calculate Mahalanobis / Z-score normalized deviation based on baseline std:
            norm_dev = sqrt(((dx/std_x)^2 + (dy/std_y)^2) / 2)
        """
        if not self.state.calibrated:
            return 0.0
        dx = (tilt_x - self.state.baseline_mean_x) / max(0.005, self.state.baseline_std_x)
        dy = (tilt_y - self.state.baseline_mean_y) / max(0.005, self.state.baseline_std_y)
        return round(float(math.sqrt((dx * dx + dy * dy) / 2.0)), 4)
