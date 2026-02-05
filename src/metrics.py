"""
Metrics Module for Eye Movement Assessment System.
Provides clinical-grade metrics calculation including:
- Visual angle conversion
- Pursuit gain calculation
- Saccade detection
- BCEA (Bivariate Contour Ellipse Area) calculation
"""

import math
import numpy as np
from scipy import signal
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class ScreenConfig:
    """Screen configuration for visual angle calculations."""
    width_px: int                  # Screen width in pixels
    height_px: int                 # Screen height in pixels
    width_cm: float                # Physical width in cm
    height_cm: float               # Physical height in cm
    viewing_distance_cm: float     # Distance from eyes to screen

    @property
    def pixels_per_cm(self) -> float:
        """Calculate pixels per centimeter."""
        return self.width_px / self.width_cm

    @property
    def pixels_per_degree(self) -> float:
        """Calculate pixels per degree visual angle at center."""
        # At viewing distance D, 1 degree = 2 * D * tan(0.5°) cm
        cm_per_degree = 2 * self.viewing_distance_cm * math.tan(math.radians(0.5))
        return cm_per_degree * self.pixels_per_cm

    def pixels_to_degrees(self, pixels: float) -> float:
        """Convert pixel distance to degrees visual angle."""
        return pixels / self.pixels_per_degree

    def degrees_to_pixels(self, degrees: float) -> float:
        """Convert degrees visual angle to pixels."""
        return degrees * self.pixels_per_degree

    @classmethod
    def default_config(cls) -> "ScreenConfig":
        """Create default configuration (24" monitor at 60cm)."""
        return cls(
            width_px=1920,
            height_px=1080,
            width_cm=53.1,    # 24" diagonal, 16:9
            height_cm=29.9,
            viewing_distance_cm=60.0
        )


@dataclass
class SaccadeEvent:
    """Represents a detected saccade."""
    onset_time: float              # Saccade start time (seconds)
    offset_time: float             # Saccade end time (seconds)
    duration_ms: float             # Duration in milliseconds
    peak_velocity_deg_s: float     # Peak velocity in degrees/second
    amplitude_deg: float           # Amplitude in degrees visual angle
    start_position: Tuple[float, float] = (0.0, 0.0)  # Starting position (px)
    end_position: Tuple[float, float] = (0.0, 0.0)    # Ending position (px)


@dataclass
class PursuitMetrics:
    """Metrics for smooth pursuit test."""
    gain: float                    # Eye velocity / Target velocity
    accuracy_degrees: float        # RMS error in degrees visual angle
    smoothness: float              # 0-1 scale (1 = perfectly smooth)
    tracking_ratio: float          # Valid frames percentage (0-1)
    catch_up_saccade_count: int    # Number of corrective saccades
    phase_lag_ms: float            # Temporal lag behind target


@dataclass
class SaccadeMetrics:
    """Metrics for saccade test."""
    mean_latency_ms: float         # Average reaction time
    latency_std_ms: float          # Latency variability
    accuracy_degrees: float        # Mean endpoint error
    accuracy_std_degrees: float    # Accuracy variability
    peak_velocity_deg_s: float     # Average peak saccade velocity
    correct_count: int             # Correct saccades (pro/anti)
    error_count: int               # Erroneous saccades


@dataclass
class FixationMetrics:
    """Metrics for fixation stability test."""
    bcea_degrees_sq: float         # Bivariate Contour Ellipse Area in deg²
    horizontal_std_degrees: float  # Horizontal dispersion
    vertical_std_degrees: float    # Vertical dispersion
    microsaccade_count: int        # Detected microsaccades
    microsaccade_rate_hz: float    # Microsaccades per second
    fixation_duration_ms: float    # Total stable fixation duration


class MetricsCalculator:
    """Calculate clinical eye movement metrics."""

    def __init__(self, screen_config: ScreenConfig):
        """
        Initialize the metrics calculator.

        Args:
            screen_config: Screen configuration for visual angle conversion
        """
        self.screen = screen_config
        self.saccade_velocity_threshold = 30.0  # deg/s
        self.microsaccade_velocity_threshold = 15.0  # deg/s
        self.min_saccade_duration_ms = 20.0  # Minimum saccade duration

    def calculate_pursuit_gain(self,
                               target_positions: np.ndarray,
                               gaze_positions: np.ndarray,
                               timestamps: np.ndarray,
                               saccade_threshold_deg_s: float = None) -> float:
        """
        Calculate smooth pursuit gain.

        Gain = (mean gaze velocity) / (mean target velocity)
        Saccadic movements are excluded from the calculation.

        Args:
            target_positions: Nx2 array of target (x, y) positions in pixels
            gaze_positions: Nx2 array of gaze (x, y) positions in pixels
            timestamps: N array of timestamps in seconds

        Returns:
            Pursuit gain (typically 0.8-1.0 for normal pursuit)
        """
        if saccade_threshold_deg_s is None:
            saccade_threshold_deg_s = self.saccade_velocity_threshold

        if len(timestamps) < 2:
            return 0.0

        # Calculate time differences
        dt = np.diff(timestamps)

        # Avoid division by zero
        dt = np.maximum(dt, 1e-6)

        # Calculate displacements
        target_disp = np.diff(target_positions, axis=0)
        gaze_disp = np.diff(gaze_positions, axis=0)

        # Calculate velocities in pixels/second
        target_vel_px = np.linalg.norm(target_disp, axis=1) / dt
        gaze_vel_px = np.linalg.norm(gaze_disp, axis=1) / dt

        # Convert to degrees/second
        target_vel_deg = self.screen.pixels_to_degrees(target_vel_px)
        gaze_vel_deg = self.screen.pixels_to_degrees(gaze_vel_px)

        # Mask out saccades (high velocity movements)
        smooth_mask = gaze_vel_deg < saccade_threshold_deg_s

        # Also require target to be moving (avoid divide by zero)
        moving_mask = target_vel_deg > 1.0  # At least 1 deg/s

        valid_mask = smooth_mask & moving_mask

        if not np.any(valid_mask):
            return 0.0

        # Calculate gain as ratio of mean velocities
        mean_gaze_vel = np.mean(gaze_vel_deg[valid_mask])
        mean_target_vel = np.mean(target_vel_deg[valid_mask])

        if mean_target_vel < 1e-6:
            return 0.0

        gain = mean_gaze_vel / mean_target_vel

        # Clip to reasonable range
        return np.clip(gain, 0.0, 2.0)

    def detect_saccades(self,
                        gaze_positions: np.ndarray,
                        timestamps: np.ndarray,
                        velocity_threshold_deg_s: float = None,
                        min_duration_ms: float = None) -> List[SaccadeEvent]:
        """
        Detect saccades using velocity threshold method.

        Args:
            gaze_positions: Nx2 array of gaze (x, y) positions in pixels
            timestamps: N array of timestamps in seconds
            velocity_threshold_deg_s: Velocity threshold for saccade detection
            min_duration_ms: Minimum saccade duration

        Returns:
            List of detected SaccadeEvent objects
        """
        if velocity_threshold_deg_s is None:
            velocity_threshold_deg_s = self.saccade_velocity_threshold
        if min_duration_ms is None:
            min_duration_ms = self.min_saccade_duration_ms

        if len(timestamps) < 3:
            return []

        # Calculate time differences
        dt = np.diff(timestamps)
        dt = np.maximum(dt, 1e-6)

        # Calculate velocities
        gaze_disp = np.diff(gaze_positions, axis=0)
        velocity_px = np.linalg.norm(gaze_disp, axis=1) / dt
        velocity_deg = self.screen.pixels_to_degrees(velocity_px)

        # Find above-threshold segments
        above_threshold = velocity_deg > velocity_threshold_deg_s

        saccades = []
        in_saccade = False
        onset_idx = 0

        for i, is_above in enumerate(above_threshold):
            if is_above and not in_saccade:
                in_saccade = True
                onset_idx = i
            elif not is_above and in_saccade:
                in_saccade = False
                offset_idx = i

                # Calculate saccade metrics
                duration_ms = (timestamps[offset_idx + 1] - timestamps[onset_idx]) * 1000

                if duration_ms >= min_duration_ms:
                    segment_vel = velocity_deg[onset_idx:offset_idx + 1]
                    peak_velocity = np.max(segment_vel) if len(segment_vel) > 0 else 0

                    # Calculate amplitude
                    start_pos = gaze_positions[onset_idx]
                    end_pos = gaze_positions[offset_idx + 1]
                    amplitude_px = np.linalg.norm(end_pos - start_pos)
                    amplitude_deg = self.screen.pixels_to_degrees(amplitude_px)

                    saccade = SaccadeEvent(
                        onset_time=timestamps[onset_idx],
                        offset_time=timestamps[offset_idx + 1],
                        duration_ms=duration_ms,
                        peak_velocity_deg_s=peak_velocity,
                        amplitude_deg=amplitude_deg,
                        start_position=tuple(start_pos),
                        end_position=tuple(end_pos)
                    )
                    saccades.append(saccade)

        # Handle saccade that extends to end of data
        if in_saccade:
            offset_idx = len(above_threshold)
            duration_ms = (timestamps[-1] - timestamps[onset_idx]) * 1000

            if duration_ms >= min_duration_ms:
                segment_vel = velocity_deg[onset_idx:]
                peak_velocity = np.max(segment_vel) if len(segment_vel) > 0 else 0

                start_pos = gaze_positions[onset_idx]
                end_pos = gaze_positions[-1]
                amplitude_px = np.linalg.norm(end_pos - start_pos)
                amplitude_deg = self.screen.pixels_to_degrees(amplitude_px)

                saccade = SaccadeEvent(
                    onset_time=timestamps[onset_idx],
                    offset_time=timestamps[-1],
                    duration_ms=duration_ms,
                    peak_velocity_deg_s=peak_velocity,
                    amplitude_deg=amplitude_deg,
                    start_position=tuple(start_pos),
                    end_position=tuple(end_pos)
                )
                saccades.append(saccade)

        return saccades

    def calculate_bcea(self,
                       gaze_positions: np.ndarray,
                       probability: float = 0.68) -> float:
        """
        Calculate Bivariate Contour Ellipse Area.

        BCEA = 2 * k * π * σH * σV * √(1 - ρ²)

        Where:
        - k = chi-squared value for desired probability
        - σH = horizontal standard deviation (degrees)
        - σV = vertical standard deviation (degrees)
        - ρ = Pearson correlation coefficient

        Args:
            gaze_positions: Nx2 array of gaze (x, y) positions in pixels
            probability: Probability for the contour ellipse (default 0.68 ≈ 1 SD)

        Returns:
            BCEA in degrees² visual angle
        """
        from scipy import stats

        if len(gaze_positions) < 3:
            return 0.0

        gaze_x = gaze_positions[:, 0]
        gaze_y = gaze_positions[:, 1]

        # Convert to degrees
        gaze_x_deg = self.screen.pixels_to_degrees(gaze_x - np.mean(gaze_x))
        gaze_y_deg = self.screen.pixels_to_degrees(gaze_y - np.mean(gaze_y))

        # Calculate statistics
        sigma_h = np.std(gaze_x_deg)
        sigma_v = np.std(gaze_y_deg)

        # Calculate correlation coefficient
        if sigma_h > 1e-6 and sigma_v > 1e-6:
            rho = np.corrcoef(gaze_x_deg, gaze_y_deg)[0, 1]
        else:
            rho = 0.0

        # Handle NaN correlation (can happen with constant data)
        if np.isnan(rho):
            rho = 0.0

        # Chi-squared value for probability with 2 degrees of freedom
        k = stats.chi2.ppf(probability, df=2)

        # BCEA formula
        rho_term = np.sqrt(1 - rho**2)
        bcea = 2 * k * np.pi * sigma_h * sigma_v * rho_term

        return bcea

    def detect_microsaccades(self,
                             gaze_positions: np.ndarray,
                             timestamps: np.ndarray,
                             max_amplitude_deg: float = 1.0) -> List[SaccadeEvent]:
        """
        Detect microsaccades during fixation using velocity threshold.

        Microsaccades are small, involuntary eye movements (< 1 degree amplitude)
        that occur during attempted fixation.

        Args:
            gaze_positions: Nx2 array of gaze (x, y) positions in pixels
            timestamps: N array of timestamps in seconds
            max_amplitude_deg: Maximum amplitude for microsaccade classification

        Returns:
            List of detected microsaccade events (as SaccadeEvent objects)
        """
        # Use microsaccade velocity threshold and shorter min duration
        all_movements = self.detect_saccades(
            gaze_positions,
            timestamps,
            velocity_threshold_deg_s=self.microsaccade_velocity_threshold,
            min_duration_ms=10.0  # Microsaccades can be very brief
        )

        # Filter by amplitude (microsaccades are small)
        microsaccades = [
            m for m in all_movements
            if m.amplitude_deg <= max_amplitude_deg
        ]

        return microsaccades

    def calculate_fixation_metrics(self,
                                   gaze_positions: np.ndarray,
                                   timestamps: np.ndarray,
                                   bcea_probability: float = 0.68) -> FixationMetrics:
        """
        Calculate comprehensive fixation stability metrics.

        Args:
            gaze_positions: Nx2 array of gaze (x, y) positions in pixels
            timestamps: N array of timestamps in seconds
            bcea_probability: Probability for BCEA calculation (default 0.68)

        Returns:
            FixationMetrics object with all calculated metrics
        """
        if len(timestamps) < 3:
            return FixationMetrics(
                bcea_degrees_sq=0.0,
                horizontal_std_degrees=0.0,
                vertical_std_degrees=0.0,
                microsaccade_count=0,
                microsaccade_rate_hz=0.0,
                fixation_duration_ms=0.0
            )

        # Calculate BCEA
        bcea = self.calculate_bcea(gaze_positions, bcea_probability)

        # Calculate dispersion
        gaze_x = gaze_positions[:, 0]
        gaze_y = gaze_positions[:, 1]
        h_std = self.screen.pixels_to_degrees(np.std(gaze_x))
        v_std = self.screen.pixels_to_degrees(np.std(gaze_y))

        # Detect microsaccades
        microsaccades = self.detect_microsaccades(gaze_positions, timestamps)
        microsaccade_count = len(microsaccades)

        # Calculate microsaccade rate
        duration_s = timestamps[-1] - timestamps[0]
        if duration_s > 0:
            microsaccade_rate_hz = microsaccade_count / duration_s
        else:
            microsaccade_rate_hz = 0.0

        # Calculate stable fixation duration (time not in microsaccades)
        total_duration_ms = duration_s * 1000
        microsaccade_duration_ms = sum(m.duration_ms for m in microsaccades)
        fixation_duration_ms = total_duration_ms - microsaccade_duration_ms

        return FixationMetrics(
            bcea_degrees_sq=bcea,
            horizontal_std_degrees=h_std,
            vertical_std_degrees=v_std,
            microsaccade_count=microsaccade_count,
            microsaccade_rate_hz=microsaccade_rate_hz,
            fixation_duration_ms=max(0.0, fixation_duration_ms)
        )

    def calculate_rms_error(self,
                            target_positions: np.ndarray,
                            gaze_positions: np.ndarray) -> float:
        """
        Calculate RMS (Root Mean Square) error between target and gaze.

        Args:
            target_positions: Nx2 array of target positions in pixels
            gaze_positions: Nx2 array of gaze positions in pixels

        Returns:
            RMS error in degrees visual angle
        """
        if len(target_positions) == 0 or len(gaze_positions) == 0:
            return 0.0

        # Calculate distances
        distances_px = np.linalg.norm(target_positions - gaze_positions, axis=1)

        # Convert to degrees
        distances_deg = self.screen.pixels_to_degrees(distances_px)

        # Calculate RMS
        rms = np.sqrt(np.mean(distances_deg**2))

        return rms

    def calculate_smoothness(self, gaze_positions: np.ndarray, timestamps: np.ndarray) -> float:
        """
        Calculate smoothness score based on velocity variance.

        Lower velocity variance indicates smoother pursuit.

        Args:
            gaze_positions: Nx2 array of gaze positions in pixels
            timestamps: N array of timestamps in seconds

        Returns:
            Smoothness score (0-1, where 1 is perfectly smooth)
        """
        if len(timestamps) < 3:
            return 1.0

        dt = np.diff(timestamps)
        dt = np.maximum(dt, 1e-6)

        gaze_disp = np.diff(gaze_positions, axis=0)
        velocity_px = np.linalg.norm(gaze_disp, axis=1) / dt
        velocity_deg = self.screen.pixels_to_degrees(velocity_px)

        if len(velocity_deg) < 2:
            return 1.0

        # Calculate coefficient of variation
        mean_vel = np.mean(velocity_deg)
        if mean_vel < 1e-6:
            return 1.0

        std_vel = np.std(velocity_deg)
        cv = std_vel / mean_vel

        # Convert to 0-1 score (lower CV = higher smoothness)
        # CV of 0 = smoothness of 1.0
        # CV of 2 or higher = smoothness of 0.0
        smoothness = max(0.0, min(1.0, 1.0 - cv / 2.0))

        return smoothness

    def calculate_phase_lag(self,
                            target_positions: np.ndarray,
                            gaze_positions: np.ndarray,
                            timestamps: np.ndarray) -> float:
        """
        Calculate temporal phase lag between gaze and target using cross-correlation.

        Args:
            target_positions: Target positions array (N, 2)
            gaze_positions: Gaze positions array (N, 2)
            timestamps: Timestamps array (N,)

        Returns:
            Phase lag in milliseconds (positive = gaze lags behind target)
        """
        if len(timestamps) < 10:
            return 0.0

        # Calculate average sample rate
        dt = np.mean(np.diff(timestamps))
        if dt <= 0:
            return 0.0
        sample_rate = 1.0 / dt

        # Use x-component for horizontal pursuit (most common)
        target_x = target_positions[:, 0] - np.mean(target_positions[:, 0])
        gaze_x = gaze_positions[:, 0] - np.mean(gaze_positions[:, 0])

        # Normalize signals
        target_norm = target_x / (np.std(target_x) + 1e-8)
        gaze_norm = gaze_x / (np.std(gaze_x) + 1e-8)

        # Cross-correlation
        correlation = signal.correlate(gaze_norm, target_norm, mode='full')
        lags = signal.correlation_lags(len(gaze_norm), len(target_norm), mode='full')

        # Find peak correlation (should be near zero lag for good tracking)
        peak_idx = np.argmax(correlation)
        lag_samples = lags[peak_idx]

        # Convert to milliseconds
        lag_ms = (lag_samples / sample_rate) * 1000.0

        # Clamp to reasonable range (typically -500 to +500 ms)
        lag_ms = np.clip(lag_ms, -500.0, 500.0)

        return float(lag_ms)

    def calculate_pursuit_metrics(self,
                                  target_positions: np.ndarray,
                                  gaze_positions: np.ndarray,
                                  timestamps: np.ndarray) -> PursuitMetrics:
        """
        Calculate comprehensive smooth pursuit metrics.

        Args:
            target_positions: Nx2 array of target positions in pixels
            gaze_positions: Nx2 array of gaze positions in pixels
            timestamps: N array of timestamps in seconds

        Returns:
            PursuitMetrics object with all calculated metrics
        """
        # Calculate pursuit gain
        gain = self.calculate_pursuit_gain(target_positions, gaze_positions, timestamps)

        # Calculate RMS accuracy
        accuracy_degrees = self.calculate_rms_error(target_positions, gaze_positions)

        # Calculate smoothness
        smoothness = self.calculate_smoothness(gaze_positions, timestamps)

        # Detect catch-up saccades
        saccades = self.detect_saccades(gaze_positions, timestamps)
        catch_up_saccade_count = len(saccades)

        # Calculate tracking ratio (assume all frames are valid for now)
        # In practice, this would be based on face detection success
        tracking_ratio = 1.0

        # Phase lag estimation using cross-correlation
        phase_lag_ms = self.calculate_phase_lag(target_positions, gaze_positions, timestamps)

        return PursuitMetrics(
            gain=gain,
            accuracy_degrees=accuracy_degrees,
            smoothness=smoothness,
            tracking_ratio=tracking_ratio,
            catch_up_saccade_count=catch_up_saccade_count,
            phase_lag_ms=phase_lag_ms
        )
