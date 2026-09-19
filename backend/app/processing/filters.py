"""
SUBSENSE — Signal Processing & State Estimation (Phase 5)

Implements a discrete 2D state-space Kalman Filter for tilt angle and angular rate estimation:
State:
    x = [angle (deg), rate (deg/s)]^T

State Transition:
    x_{k} = F * x_{k-1} + w_k
    F = [[1, dt],
         [0,  1]]

Measurement:
    z_k = H * x_k + v_k
    H = [[1, 0]]  (only angle is directly measured from accelerometer)

Noise Covariances:
    Q = [[q_angle * dt, 0],
         [0, q_rate * dt]]
    R = [[r_measure]]

Benefits for Subsidence Monitoring:
1. Removes high-frequency mechanical vibration and sensor noise from tilt.
2. Directly estimates angular rate (tilt velocity, deg/s) without noisy finite differences.
3. Adapts smoothly to variable sampling intervals (dt).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Optional


@dataclass
class FilterEstimate:
    """Estimated state from Kalman filter."""
    angle: float       # Denoised angle (degrees)
    rate: float        # Denoised angular velocity (degrees / second)
    variance: float    # Estimation error covariance of the angle


class KalmanFilter2D:
    """
    2D Kalman Filter tracking position (angle) and velocity (rate).
    """

    def __init__(
        self,
        initial_angle: float = 0.0,
        initial_rate: float = 0.0,
        q_angle: float = 0.001,
        q_rate: float = 0.003,
        r_measure: float = 0.03,
    ) -> None:
        self.q_angle = q_angle
        self.q_rate = q_rate
        self.r_measure = r_measure

        # State vector [angle, rate]
        self.angle = initial_angle
        self.rate = initial_rate

        # Error covariance matrix P = [[P00, P01], [P10, P11]]
        self.p00 = 1.0
        self.p01 = 0.0
        self.p10 = 0.0
        self.p11 = 1.0

        self.initialized = False

    def update(self, measured_angle: float, dt: float = 1.0) -> FilterEstimate:
        """
        Predict and update the filter state with a new angle measurement.

        Parameters
        ----------
        measured_angle : Raw measured angle in degrees
        dt : Elapsed time since last measurement in seconds (clamped to [0.01, 10.0])
        """
        # Clamp dt to avoid singularity on duplicate or delayed timestamps
        dt = max(0.01, min(dt, 10.0))

        if not self.initialized:
            self.angle = measured_angle
            self.rate = 0.0
            self.p00 = self.r_measure
            self.p11 = 1.0
            self.initialized = True
            return FilterEstimate(angle=self.angle, rate=0.0, variance=self.p00)

        # ── 1. Predict Step ──────────────────────────
        # x_pred = F * x
        self.angle += dt * self.rate

        # P_pred = F * P * F^T + Q
        # Compute manually for 2x2 performance and clarity
        p00_pred = self.p00 + dt * (self.p10 + self.p01) + (dt * dt) * self.p11 + self.q_angle * dt
        p01_pred = self.p01 + dt * self.p11
        p10_pred = self.p10 + dt * self.p11
        p11_pred = self.p11 + self.q_rate * dt

        # ── 2. Measurement Update (Correction) ───────
        # Innovation (measurement residual)
        y = measured_angle - self.angle

        # Innovation covariance: S = H * P_pred * H^T + R = p00_pred + R
        s = p00_pred + self.r_measure

        # Kalman gain: K = P_pred * H^T * inv(S)
        k0 = p00_pred / s
        k1 = p10_pred / s

        # State correction: x = x_pred + K * y
        self.angle += k0 * y
        self.rate += k1 * y

        # Covariance correction: P = (I - K * H) * P_pred
        self.p00 = p00_pred - k0 * p00_pred
        self.p01 = p01_pred - k0 * p01_pred
        self.p10 = p10_pred - k1 * p00_pred
        self.p11 = p11_pred - k1 * p01_pred

        return FilterEstimate(angle=self.angle, rate=self.rate, variance=self.p00)


class NodeTiltFilter:
    """
    Dual-axis filter managing tilt_x and tilt_y Kalman filters for a single node.
    """

    def __init__(
        self,
        node_id: str,
        q_angle: float = 0.001,
        q_rate: float = 0.003,
        r_measure: float = 0.03,
    ) -> None:
        self.node_id = node_id
        self.filter_x = KalmanFilter2D(q_angle=q_angle, q_rate=q_rate, r_measure=r_measure)
        self.filter_y = KalmanFilter2D(q_angle=q_angle, q_rate=q_rate, r_measure=r_measure)
        self.last_timestamp: Optional[datetime] = None

    def filter_sample(
        self,
        raw_tilt_x: float,
        raw_tilt_y: float,
        timestamp: datetime,
    ) -> tuple[FilterEstimate, FilterEstimate]:
        """
        Process incoming tilt_x and tilt_y measurements.
        Calculates dt based on timestamp difference.
        """
        dt = 1.0
        if self.last_timestamp is not None:
            delta = (timestamp - self.last_timestamp).total_seconds()
            if delta > 0:
                dt = delta

        self.last_timestamp = timestamp
        est_x = self.filter_x.update(raw_tilt_x, dt=dt)
        est_y = self.filter_y.update(raw_tilt_y, dt=dt)
        return est_x, est_y
