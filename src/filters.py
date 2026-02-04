"""
Advanced Filtering Module for Eye Tracking
Implements 1-Euro Filter and Kalman Filter for improved gaze smoothing.
"""

import math
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass


class LowPassFilter:
    """Simple first-order low-pass filter."""

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.y: Optional[float] = None
        self.initialized = False

    def filter(self, x: float, alpha: Optional[float] = None) -> float:
        """Apply low-pass filter to input value."""
        if alpha is not None:
            self.alpha = alpha

        if not self.initialized:
            self.y = x
            self.initialized = True
        else:
            self.y = self.alpha * x + (1 - self.alpha) * self.y

        return self.y

    def reset(self):
        """Reset filter state."""
        self.y = None
        self.initialized = False

    @property
    def last_value(self) -> Optional[float]:
        return self.y


class OneEuroFilter:
    """
    1-Euro Filter: A Simple Speed-based Low-pass Filter for Noisy Input.

    Reference: Casiez, G., Roussel, N., & Vogel, D. (2012).
    "1€ Filter: A Simple Speed-Based Low-Pass Filter for Noisy Input in
    Interactive Systems." CHI '12.

    The filter adaptively adjusts cutoff frequency based on signal velocity:
    - At low speeds: low cutoff reduces jitter (higher smoothing)
    - At high speeds: high cutoff reduces lag (less smoothing)
    """

    def __init__(
        self,
        freq: float = 30.0,
        mincutoff: float = 1.0,
        beta: float = 0.007,
        dcutoff: float = 1.0
    ):
        """
        Initialize 1-Euro Filter.

        Args:
            freq: Sampling frequency in Hz (e.g., 30 for 30 FPS webcam)
            mincutoff: Minimum cutoff frequency (lower = more smoothing at low speeds)
            beta: Speed coefficient (higher = less lag at high speeds)
            dcutoff: Cutoff frequency for derivative filter
        """
        self.freq = freq
        self.mincutoff = mincutoff
        self.beta = beta
        self.dcutoff = dcutoff

        self._x_filter = LowPassFilter()
        self._dx_filter = LowPassFilter()
        self._last_time: Optional[float] = None

    @staticmethod
    def _alpha(rate: float, cutoff: float) -> float:
        """Compute filter alpha from rate and cutoff frequency."""
        tau = 1.0 / (2.0 * math.pi * cutoff)
        te = 1.0 / rate
        return 1.0 / (1.0 + tau / te)

    def filter(self, x: float, timestamp: Optional[float] = None) -> float:
        """
        Apply 1-Euro filter to input value.

        Args:
            x: Input value
            timestamp: Optional timestamp in seconds. If provided, frequency
                       is computed from time delta.

        Returns:
            Filtered value
        """
        # Update frequency from timestamp if provided
        if timestamp is not None and self._last_time is not None:
            dt = timestamp - self._last_time
            if dt > 0:
                self.freq = 1.0 / dt
        self._last_time = timestamp

        # Compute derivative
        if self._x_filter.last_value is not None:
            dx = (x - self._x_filter.last_value) * self.freq
        else:
            dx = 0.0

        # Filter derivative to reduce noise
        edx = self._dx_filter.filter(dx, self._alpha(self.freq, self.dcutoff))

        # Compute adaptive cutoff based on signal velocity
        cutoff = self.mincutoff + self.beta * abs(edx)

        # Filter the signal
        return self._x_filter.filter(x, self._alpha(self.freq, cutoff))

    def reset(self):
        """Reset filter state."""
        self._x_filter.reset()
        self._dx_filter.reset()
        self._last_time = None


class OneEuroFilter2D:
    """2D version of 1-Euro Filter for gaze coordinates."""

    def __init__(
        self,
        freq: float = 30.0,
        mincutoff: float = 1.0,
        beta: float = 0.007,
        dcutoff: float = 1.0
    ):
        """
        Initialize 2D 1-Euro Filter.

        Args:
            freq: Sampling frequency in Hz
            mincutoff: Minimum cutoff frequency
            beta: Speed coefficient
            dcutoff: Cutoff frequency for derivative
        """
        self._filter_x = OneEuroFilter(freq, mincutoff, beta, dcutoff)
        self._filter_y = OneEuroFilter(freq, mincutoff, beta, dcutoff)

    def filter(
        self,
        x: float,
        y: float,
        timestamp: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        Apply 1-Euro filter to 2D coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            timestamp: Optional timestamp in seconds

        Returns:
            Filtered (x, y) coordinates
        """
        filtered_x = self._filter_x.filter(x, timestamp)
        filtered_y = self._filter_y.filter(y, timestamp)
        return (filtered_x, filtered_y)

    def reset(self):
        """Reset both filters."""
        self._filter_x.reset()
        self._filter_y.reset()


@dataclass
class KalmanState:
    """State for 2D Kalman filter."""
    x: np.ndarray  # State vector [x, y, vx, vy]
    P: np.ndarray  # Covariance matrix


class GazeKalmanFilter:
    """
    Extended Kalman Filter for gaze tracking.

    Models gaze as a 2D point with velocity:
    State: [x, y, vx, vy]

    Provides:
    - Noise reduction through optimal state estimation
    - Velocity estimation for saccade detection
    - Prediction during brief tracking losses (blinks)
    """

    def __init__(
        self,
        process_noise_pos: float = 0.1,
        process_noise_vel: float = 1.0,
        measurement_noise_fixation: float = 5.0,
        measurement_noise_saccade: float = 50.0,
        saccade_threshold: float = 100.0
    ):
        """
        Initialize Kalman Filter.

        Args:
            process_noise_pos: Process noise for position (lower = smoother)
            process_noise_vel: Process noise for velocity
            measurement_noise_fixation: Measurement noise during fixation
            measurement_noise_saccade: Measurement noise during saccade
            saccade_threshold: Velocity threshold for saccade detection (px/s)
        """
        self.process_noise_pos = process_noise_pos
        self.process_noise_vel = process_noise_vel
        self.measurement_noise_fixation = measurement_noise_fixation
        self.measurement_noise_saccade = measurement_noise_saccade
        self.saccade_threshold = saccade_threshold

        # State vector: [x, y, vx, vy]
        self.state = np.zeros(4)
        # Covariance matrix (high initial uncertainty)
        self.P = np.eye(4) * 1000.0

        self._initialized = False
        self._last_time: Optional[float] = None

        # Detection state
        self.is_saccade = False
        self.velocity = 0.0

    def _get_F(self, dt: float) -> np.ndarray:
        """State transition matrix."""
        return np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])

    def _get_Q(self, dt: float) -> np.ndarray:
        """Process noise covariance matrix."""
        # Discretized continuous white noise model
        dt2 = dt * dt
        dt3 = dt2 * dt
        dt4 = dt3 * dt

        q_pos = self.process_noise_pos
        q_vel = self.process_noise_vel

        return np.array([
            [dt4/4*q_pos, 0, dt3/2*q_pos, 0],
            [0, dt4/4*q_pos, 0, dt3/2*q_pos],
            [dt3/2*q_pos, 0, dt2*q_vel, 0],
            [0, dt3/2*q_pos, 0, dt2*q_vel]
        ])

    def _get_R(self) -> np.ndarray:
        """Measurement noise covariance (adaptive)."""
        if self.is_saccade:
            r = self.measurement_noise_saccade
        else:
            r = self.measurement_noise_fixation
        return np.diag([r, r])

    @property
    def H(self) -> np.ndarray:
        """Observation matrix (we only measure position)."""
        return np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ])

    def predict(self, dt: float) -> Tuple[float, float]:
        """
        Predict next state (useful during blinks).

        Args:
            dt: Time step in seconds

        Returns:
            Predicted (x, y) position
        """
        F = self._get_F(dt)
        Q = self._get_Q(dt)

        # State prediction
        self.state = F @ self.state
        # Covariance prediction
        self.P = F @ self.P @ F.T + Q

        return (self.state[0], self.state[1])

    def update(
        self,
        x: float,
        y: float,
        timestamp: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        Update filter with new measurement.

        Args:
            x: Measured X position
            y: Measured Y position
            timestamp: Optional timestamp in seconds

        Returns:
            Filtered (x, y) position
        """
        # Initialize on first measurement
        if not self._initialized:
            self.state = np.array([x, y, 0.0, 0.0])
            self._initialized = True
            self._last_time = timestamp
            return (x, y)

        # Compute time delta
        dt = 1.0 / 30.0  # Default 30 FPS
        if timestamp is not None and self._last_time is not None:
            dt = max(timestamp - self._last_time, 0.001)
        self._last_time = timestamp

        # Predict step
        F = self._get_F(dt)
        Q = self._get_Q(dt)

        state_pred = F @ self.state
        P_pred = F @ self.P @ F.T + Q

        # Compute velocity for saccade detection
        self.velocity = np.sqrt(state_pred[2]**2 + state_pred[3]**2)
        self.is_saccade = self.velocity > self.saccade_threshold

        # Update step
        z = np.array([x, y])
        R = self._get_R()

        # Innovation
        y_innov = z - self.H @ state_pred

        # Innovation covariance
        S = self.H @ P_pred @ self.H.T + R

        # Kalman gain
        K = P_pred @ self.H.T @ np.linalg.inv(S)

        # State update
        self.state = state_pred + K @ y_innov

        # Covariance update (Joseph form for numerical stability)
        I_KH = np.eye(4) - K @ self.H
        self.P = I_KH @ P_pred @ I_KH.T + K @ R @ K.T

        return (self.state[0], self.state[1])

    def get_velocity(self) -> Tuple[float, float]:
        """Get current velocity estimate."""
        return (self.state[2], self.state[3])

    def reset(self):
        """Reset filter state."""
        self.state = np.zeros(4)
        self.P = np.eye(4) * 1000.0
        self._initialized = False
        self._last_time = None
        self.is_saccade = False
        self.velocity = 0.0


class CombinedFilter:
    """
    Combined filtering pipeline: Kalman + 1-Euro.

    Uses Kalman filter for state estimation and velocity tracking,
    then applies 1-Euro filter for final jitter reduction.
    """

    def __init__(
        self,
        freq: float = 30.0,
        one_euro_mincutoff: float = 1.5,
        one_euro_beta: float = 0.01,
        kalman_process_noise: float = 0.5,
        kalman_measurement_noise: float = 10.0
    ):
        """
        Initialize combined filter.

        Args:
            freq: Sampling frequency
            one_euro_mincutoff: 1-Euro minimum cutoff
            one_euro_beta: 1-Euro beta parameter
            kalman_process_noise: Kalman process noise
            kalman_measurement_noise: Kalman measurement noise
        """
        self.kalman = GazeKalmanFilter(
            process_noise_pos=kalman_process_noise,
            measurement_noise_fixation=kalman_measurement_noise
        )
        self.one_euro = OneEuroFilter2D(
            freq=freq,
            mincutoff=one_euro_mincutoff,
            beta=one_euro_beta
        )

    def filter(
        self,
        x: float,
        y: float,
        timestamp: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        Apply combined filtering.

        Args:
            x: Input X coordinate
            y: Input Y coordinate
            timestamp: Optional timestamp

        Returns:
            Filtered (x, y) coordinates
        """
        # First pass: Kalman filter for state estimation
        kx, ky = self.kalman.update(x, y, timestamp)

        # Second pass: 1-Euro filter for jitter reduction
        fx, fy = self.one_euro.filter(kx, ky, timestamp)

        return (fx, fy)

    def predict(self, dt: float) -> Tuple[float, float]:
        """Predict during tracking loss (uses Kalman only)."""
        return self.kalman.predict(dt)

    @property
    def is_saccade(self) -> bool:
        """Check if currently in saccade."""
        return self.kalman.is_saccade

    @property
    def velocity(self) -> float:
        """Get current velocity magnitude."""
        return self.kalman.velocity

    def reset(self):
        """Reset all filters."""
        self.kalman.reset()
        self.one_euro.reset()
