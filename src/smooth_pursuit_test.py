"""
Smooth Pursuit Test Module
Implements the eye movement assessment test where user follows a moving target.
Provides clinical-grade metrics including pursuit gain, accuracy in degrees visual angle,
and catch-up saccade detection.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
import time
import json
import os
from datetime import datetime

from metrics import ScreenConfig, MetricsCalculator, PursuitMetrics
from constants import DEFAULT_VIEWING_DISTANCE_CM, NOMINAL_SCREEN_HEIGHT_CM

# Nominal interpupillary distance the degree-domain metrics are implicitly calibrated against.
# Adult mean is ~63 mm; a subject's real IPD scales how far the iris travels per degree of gaze,
# so degree error is corrected by REFERENCE_IPD_MM / actual_ipd_mm.
REFERENCE_IPD_MM = 63.0


class TargetPattern(Enum):
    """Target movement patterns."""
    HORIZONTAL = "horizontal"      # Left-right oscillation
    VERTICAL = "vertical"          # Up-down oscillation
    CIRCULAR = "circular"          # Circular motion
    FIGURE_EIGHT = "figure_eight"  # Figure-8 pattern
    RANDOM_POINTS = "random"       # Jump between random points (saccade test)
    FIXATION = "fixation"          # Stationary target for fixation stability


@dataclass
class TestConfig:
    """Configuration for the smooth pursuit test."""
    pattern: TargetPattern = TargetPattern.HORIZONTAL
    duration_seconds: float = 10.0
    speed: float = 0.5  # 0.0 to 1.0, relative speed
    target_size: int = 20  # pixels
    margin: float = 0.03  # margin from screen edges (0-0.5) - reduced from 0.1 for edge-to-edge

    # For circular/figure-8 patterns
    radius_ratio: float = 0.45  # radius as ratio of screen height - increased from 0.3

    # For random points pattern (saccade test)
    num_points: int = 10
    point_duration: float = 1.0  # seconds per point


@dataclass
class TrackingFrame:
    """Single frame of tracking data."""
    timestamp: float
    target_x: int
    target_y: int
    gaze_x: Optional[int]
    gaze_y: Optional[int]
    head_pitch: float
    head_yaw: float
    face_detected: bool


@dataclass
class TestResult:
    """Results from a smooth pursuit test."""
    pattern: TargetPattern
    duration: float
    frames: List[TrackingFrame] = field(default_factory=list)

    # Legacy metrics (0-100 scale for backward compatibility)
    accuracy_score: float = 0.0      # Direction match: how often the gaze moved with the target
    avg_distance_px: float = 0.0
    tracking_ratio: float = 0.0      # Tracking rate: % of frames that produced a usable gaze
    speed_match_score: float = 0.0   # How closely the gaze speed matched the target speed
    smooth_score: float = 0.0    # How smooth vs jerky the tracking was (0-100)
    lag_ms: float = 0.0          # Average lag behind target
    pupil_distance_mm: float = 0.0  # Subject IPD used to correct degree-domain metrics
    head_stillness_score: float = 0.0  # 100 = head held still throughout
    uncalibrated: bool = False  # Scored without calibration: results are not meaningful
    target_angular_speed_deg_s: float = 0.0  # Peak demand placed on the pursuit system

    # Clinical metrics (new)
    pursuit_gain: float = 0.0              # Eye velocity / Target velocity
    accuracy_degrees: float = 0.0          # RMS error in degrees visual angle
    smoothness: float = 0.0                # 0-1 scale smoothness
    catch_up_saccade_count: int = 0        # Number of corrective saccades
    clinical_metrics: Optional[PursuitMetrics] = None

    def compute_metrics(self, screen_diagonal: float, screen_config: Optional[ScreenConfig] = None, pupil_distance_mm: float = 0.0):
        """
        Compute all metrics from the recorded frames.

        Args:
            screen_config: Optional ScreenConfig for clinical metrics calculation
            pupil_distance_mm: Patient's IPD in mm for accurate degree conversion (0 = use default)
        """
        if not self.frames:
            return

        valid_frames = [f for f in self.frames if f.gaze_x is not None and f.face_detected]
        if not valid_frames:
            return

        # Compute avg_distance_px for backward compatibility
        distances = [np.sqrt((f.gaze_x - f.target_x)**2 + (f.gaze_y - f.target_y)**2) for f in valid_frames]
        self.avg_distance_px = np.mean(distances)

        # Head monitoring, per frame, alongside the pupils. The subject's neutral pose is the
        # median pose across the session; every frame is then scored for how far the head has
        # drifted from it. Range-based scoring missed movement entirely when the head drifted
        # early and stayed there, which is exactly the case that must be penalised.
        pitches = np.array([f.head_pitch for f in valid_frames])
        yaws = np.array([f.head_yaw for f in valid_frames])
        ref_pitch = float(np.median(pitches))
        ref_yaw = float(np.median(yaws))
        head_drift = np.sqrt((pitches - ref_pitch) ** 2 + (yaws - ref_yaw) ** 2)

        # Stillness factor per frame: 1.0 while the head holds still, decaying to 0.0 as it
        # drifts. The 2 deg deadband absorbs solvePnP landmark jitter on a genuinely still head.
        HEAD_DEADBAND_DEG = 2.0
        HEAD_DECAY_DEG = 8.0
        stillness = np.clip(1.0 - (head_drift - HEAD_DEADBAND_DEG) / HEAD_DECAY_DEG, 0.0, 1.0)

        # Head stillness score: 100% only while the head holds still as the eyes move.
        self.head_stillness_score = float(np.mean(stillness) * 100)

        # Weight applied to the eye scores. Head movement is already reported on its own via
        # head_stillness_score, so charging it again at full strength triple-counted the same
        # motion and squashed every score. The square root keeps the penalty real but gentle,
        # so a couple of degrees of sway costs a few points instead of halving the result.
        def stillness_score(idx: int) -> float:
            return float(np.sqrt(stillness[idx]))

        # Direction-based accuracy: is the eye moving in the same direction as the target?
        # Velocities are smoothed over a short window first. Single-frame deltas from a webcam
        # are dominated by landmark jitter, which buried the actual tracking signal in noise.
        SMOOTH_WINDOW = 3
        direction_scores = []
        speed_scores = []
        for i in range(1, len(valid_frames)):
            dt = valid_frames[i].timestamp - valid_frames[i-1].timestamp
            if dt <= 0:
                continue
            lo = max(1, i - SMOOTH_WINDOW + 1)

            tdx = valid_frames[i].target_x - valid_frames[lo-1].target_x
            tdy = valid_frames[i].target_y - valid_frames[lo-1].target_y
            span = valid_frames[i].timestamp - valid_frames[lo-1].timestamp
            target_speed = np.sqrt(tdx**2 + tdy**2) / span

            gdx = valid_frames[i].gaze_x - valid_frames[lo-1].gaze_x
            gdy = valid_frames[i].gaze_y - valid_frames[lo-1].gaze_y
            gaze_speed = np.sqrt(gdx**2 + gdy**2) / span

            if target_speed <= 1:
                continue  # Target effectively stationary: nothing to match against.

            if gaze_speed > 1:
                dot = (gdx * tdx + gdy * tdy) / (gaze_speed * target_speed * span**2)
                # Graded, not cliffed. A hard dot > 0.5 gate threw away partial credit and
                # scored everything below it as a total failure; cosine similarity already
                # encodes "how aligned", so use it directly and clamp the wrong-way half.
                direction_scores.append(max(0.0, dot) * stillness_score(i))

            # Speed match with a tolerance band. Gaze and target velocity are derived from the
            # same noisy stream and never agree frame-for-frame, so scoring the raw ratio
            # punished ordinary measurement noise as if it were poor tracking. The band is
            # sized to swallow the spread a good tracker shows under realistic webcam jitter;
            # beyond it the shortfall is charged proportionally.
            SPEED_TOLERANCE = 0.35
            ratio = gaze_speed / target_speed
            deviation = max(0.0, abs(ratio - 1.0) - SPEED_TOLERANCE) / (1.0 - SPEED_TOLERANCE)
            speed_scores.append(max(0.0, 1.0 - deviation) * stillness_score(i))

        # Accuracy = average direction score (0-100), head movement weighted in
        if direction_scores:
            self.accuracy_score = float(np.mean(direction_scores) * 100)
        else:
            self.accuracy_score = 0

        # Tracking rate: the share of frames that produced a usable gaze estimate. This is a
        # data-validity measure -- it says nothing about how well the eyes followed the target.
        # The speed match used to be stored here, which reported the gaze estimate's own
        # damping as if the patient had failed to track. It is reported separately now.
        self.tracking_ratio = 100.0 * len(valid_frames) / len(self.frames)

        # Speed match: how closely the gaze velocity matched the target velocity. This is a
        # property of the gaze estimate (its gain), not of the patient.
        if speed_scores:
            self.speed_match_score = float(min(100.0, np.mean(speed_scores) * 100))
        else:
            self.speed_match_score = 0

        # Smoothness: 100 = smoothly tracked, 0 = very jerky. Velocities use the same windowed
        # difference as the other metrics. Single-frame deltas made this measure camera jitter
        # rather than the subject: a flawless tracker dropped from 100 to 64 under 8 px of
        # pixel noise, which says nothing about how smoothly the eyes moved.
        if len(valid_frames) > 2:
            gaze_velocities = []
            for i in range(1, len(valid_frames)):
                lo = max(1, i - SMOOTH_WINDOW + 1)
                span = valid_frames[i].timestamp - valid_frames[lo-1].timestamp
                if span > 0:
                    dx = valid_frames[i].gaze_x - valid_frames[lo-1].gaze_x
                    dy = valid_frames[i].gaze_y - valid_frames[lo-1].gaze_y
                    gaze_velocities.append(np.sqrt(dx**2 + dy**2) / span)

            if gaze_velocities and np.mean(gaze_velocities) > 0:
                cv = float(np.std(gaze_velocities) / (np.mean(gaze_velocities) + 1e-6))
                # Noise floor. A perfectly smooth tracker still shows CV ~0.27 under 2 px of
                # landmark jitter, and that variation is the camera, not the subject. Anything
                # inside the floor counts as perfectly smooth; only real jerk above it is charged.
                NOISE_FLOOR_CV = 0.40
                excess = max(0.0, cv - NOISE_FLOOR_CV)
                self.smooth_score = float(max(0.0, min(100.0, (1.0 - excess / 1.6) * 100)))
            else:
                self.smooth_score = 0

        # Calculate clinical metrics if screen config is provided
        if screen_config is not None:
            self._compute_clinical_metrics(screen_config, valid_frames, len(self.frames))

        # Pupil distance corrects the degree-domain metrics. Iris displacement for a given eye
        # rotation scales with IPD, so degree error computed against a nominal IPD is wrong for
        # anyone whose IPD differs -- a 71 mm subject was previously under-reported by ~11%.
        if pupil_distance_mm > 0 and self.accuracy_degrees > 0:
            ipd_scale = REFERENCE_IPD_MM / pupil_distance_mm
            self.accuracy_degrees *= ipd_scale
        self.pupil_distance_mm = pupil_distance_mm

    def _compute_clinical_metrics(self, screen_config: ScreenConfig,
                                  valid_frames: List[TrackingFrame],
                                  total_frames: int = 0):
        """Compute clinical-grade metrics using the MetricsCalculator."""
        if len(valid_frames) < 3:
            return

        # Extract arrays from frames
        timestamps = np.array([f.timestamp for f in valid_frames])
        target_positions = np.array([[f.target_x, f.target_y] for f in valid_frames])
        gaze_positions = np.array([[f.gaze_x, f.gaze_y] for f in valid_frames])

        # Create metrics calculator
        calc = MetricsCalculator(screen_config)

        # Calculate pursuit metrics
        self.clinical_metrics = calc.calculate_pursuit_metrics(
            target_positions, gaze_positions, timestamps, total_frames=total_frames
        )

        # Copy to instance attributes for easy access
        self.pursuit_gain = self.clinical_metrics.gain
        self.accuracy_degrees = self.clinical_metrics.accuracy_degrees
        self.smoothness = self.clinical_metrics.smoothness
        self.catch_up_saccade_count = self.clinical_metrics.catch_up_saccade_count
        self.lag_ms = self.clinical_metrics.phase_lag_ms

    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert result to a summary dictionary for JSON export."""
        return {
            "timestamp": datetime.now().isoformat(),
            "pattern": self.pattern.value,
            "duration": self.duration,
            "total_frames": len(self.frames),
            "target_angular_speed_deg_s": round(self.target_angular_speed_deg_s, 1),
            "uncalibrated": self.uncalibrated,
            "metrics": {
                "tracking_ratio": round(self.tracking_ratio, 4),
                "speed_match_score": round(self.speed_match_score, 2),
                "avg_distance_px": round(self.avg_distance_px, 2),
                "accuracy_score": round(self.accuracy_score, 2),
                "smooth_score": round(self.smooth_score, 2),
                "lag_ms": round(self.lag_ms, 2),
                "pupil_distance_mm": round(self.pupil_distance_mm, 1),
                "head_stillness_score": round(self.head_stillness_score, 2),
            },
            "clinical_metrics": {
                "pursuit_gain": round(self.pursuit_gain, 3),
                "accuracy_degrees": round(self.accuracy_degrees, 3),
                "smoothness": round(self.smoothness, 3),
                "catch_up_saccade_count": self.catch_up_saccade_count,
            } if self.clinical_metrics else None
        }

    def to_full_dict(self) -> Dict[str, Any]:
        """Convert result to full dictionary including all frame data."""
        summary = self.to_summary_dict()
        summary["frames"] = [
            {
                "timestamp": f.timestamp,
                "target_x": f.target_x,
                "target_y": f.target_y,
                "gaze_x": f.gaze_x,
                "gaze_y": f.gaze_y,
                "head_pitch": round(f.head_pitch, 4),
                "head_yaw": round(f.head_yaw, 4),
                "face_detected": f.face_detected
            }
            for f in self.frames
        ]
        return summary

    def save_summary(self, results_dir: str = "results") -> str:
        """
        Save summary results to JSON file.

        Args:
            results_dir: Directory to save results (created if not exists)

        Returns:
            Path to saved file
        """
        os.makedirs(results_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_{self.pattern.value}_{timestamp}.json"
        filepath = os.path.join(results_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(self.to_summary_dict(), f, indent=2)

        return filepath

    def save_full_data(self, results_dir: str = "results") -> str:
        """
        Save full test data including all frames to JSON file.

        Args:
            results_dir: Directory to save results (created if not exists)

        Returns:
            Path to saved file
        """
        os.makedirs(results_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_{self.pattern.value}_{timestamp}_full.json"
        filepath = os.path.join(results_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(self.to_full_dict(), f, indent=2)

        return filepath

    def save_csv(self, results_dir: str = "results") -> str:
        """
        Save test data to CSV file for spreadsheet analysis.

        Creates two files:
        - Summary CSV with test metadata and metrics
        - Frames CSV with per-frame tracking data

        Args:
            results_dir: Directory to save results (created if not exists)

        Returns:
            Path to the frames CSV file
        """
        os.makedirs(results_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"test_{self.pattern.value}_{timestamp}"

        # Save frames data
        frames_data = [
            {
                "timestamp": f.timestamp,
                "target_x": f.target_x,
                "target_y": f.target_y,
                "gaze_x": f.gaze_x,
                "gaze_y": f.gaze_y,
                "head_pitch": round(f.head_pitch, 4),
                "head_yaw": round(f.head_yaw, 4),
                "face_detected": f.face_detected
            }
            for f in self.frames
        ]
        frames_df = pd.DataFrame(frames_data)
        frames_path = os.path.join(results_dir, f"{base_name}_frames.csv")
        frames_df.to_csv(frames_path, index=False)

        # Save summary data
        summary = self.to_summary_dict()
        # Flatten nested metrics for CSV using keys from to_summary_dict()
        flat_summary = {
            "pattern": summary.get("pattern"),
            "duration": summary.get("duration"),
            "total_frames": summary.get("total_frames"),
        }
        if summary.get("metrics"):
            metrics = summary["metrics"]
            flat_summary.update({
                "tracking_ratio": metrics.get("tracking_ratio"),
                "avg_distance_px": metrics.get("avg_distance_px"),
                "accuracy_score": metrics.get("accuracy_score"),
                "smooth_score": metrics.get("smooth_score"),
                "lag_ms": metrics.get("lag_ms"),
            })
        if summary.get("clinical_metrics"):
            clinical = summary["clinical_metrics"]
            flat_summary.update({
                "pursuit_gain": clinical.get("pursuit_gain"),
                "accuracy_degrees": clinical.get("accuracy_degrees"),
                "smoothness": clinical.get("smoothness"),
                "catch_up_saccade_count": clinical.get("catch_up_saccade_count"),
            })

        summary_df = pd.DataFrame([flat_summary])
        summary_path = os.path.join(results_dir, f"{base_name}_summary.csv")
        summary_df.to_csv(summary_path, index=False)

        return frames_path


class SmoothPursuitTest:
    """
    Smooth pursuit eye movement test.
    Displays a moving target and records gaze position.
    """

    def __init__(self, screen_width: int, screen_height: int, config: TestConfig = None):
        """
        Initialize the test.

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
            config: Test configuration
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.config = config or TestConfig()

        self.screen_diagonal = np.sqrt(screen_width**2 + screen_height**2)

        # State
        self.is_running = False
        self.start_time: Optional[float] = None
        self.current_result: Optional[TestResult] = None

        # For random points pattern
        self._random_points: List[Tuple[int, int]] = []
        self._current_point_index = 0
        self._point_start_time = 0.0

        # Provenance of the gaze signal feeding this test. A run without calibration scores
        # uncalibrated gaze, which lands hundreds of pixels off and makes every metric
        # meaningless; recording it keeps such a result from being mistaken for real data.
        self.calibrated: bool = True
        self.uncalibrated: bool = False

    def peak_angular_speed_deg_s(self) -> float:
        """Peak angular demand this pattern places on the pursuit system, in deg/s.

        The target is far larger than the foveal field, so a sinusoidal sweep is the only
        shape that stays followable. Peak velocity of a sinusoid is pi/2 times its mean, and
        smooth pursuit tops out near 30-40 deg/s -- past that the subject cannot win regardless
        of how the scoring is tuned, so the number is recorded for interpretation.
        """
        usable_w = self.screen_width - 2 * self.screen_width * self.config.margin
        usable_h = self.screen_height - 2 * self.screen_height * self.config.margin

        if self.config.pattern == TargetPattern.HORIZONTAL:
            amplitude_px = usable_w / 2
            period = 3.0 / max(self.config.speed, 1e-6)
        elif self.config.pattern == TargetPattern.VERTICAL:
            amplitude_px = usable_h / 2
            period = 3.0 / max(self.config.speed, 1e-6)
        elif self.config.pattern in (TargetPattern.CIRCULAR, TargetPattern.FIGURE_EIGHT):
            amplitude_px = self.screen_height * self.config.radius_ratio
            period = 4.0 / max(self.config.speed, 1e-6)
        else:
            return 0.0

        # Pixels per degree via the nominal screen geometry the metrics module assumes.
        px_per_cm = self.screen_height / NOMINAL_SCREEN_HEIGHT_CM
        px_per_deg = 2 * 60.0 * np.tan(np.radians(0.5)) * px_per_cm
        amplitude_deg = amplitude_px / max(px_per_deg, 1e-6)

        # Mean speed around a full cycle, scaled by the sinusoid peak factor.
        return 4 * amplitude_deg / period * (np.pi / 2)

    def update_screen_dimensions(self, width: int, height: int):
        """
        Update the screen dimensions.

        This should be called when the widget is resized to ensure
        target positions stay within the visible area.

        Args:
            width: New screen/widget width in pixels
            height: New screen/widget height in pixels
        """
        self.screen_width = width
        self.screen_height = height
        self.screen_diagonal = np.sqrt(width**2 + height**2)

        # Regenerate random points if using that pattern
        if self.config.pattern == TargetPattern.RANDOM_POINTS and self.is_running:
            self._random_points = self._generate_random_points()

    def _generate_random_points(self) -> List[Tuple[int, int]]:
        """Generate random target points for saccade test."""
        margin_x = int(self.screen_width * self.config.margin)
        margin_y = int(self.screen_height * self.config.margin)

        points = []
        for _ in range(self.config.num_points):
            x = np.random.randint(margin_x, self.screen_width - margin_x)
            y = np.random.randint(margin_y, self.screen_height - margin_y)
            points.append((x, y))

        return points

    def start(self) -> bool:
        """Start the test."""
        if self.is_running:
            return False

        self.is_running = True
        self.start_time = time.time()
        self.current_result = TestResult(
            pattern=self.config.pattern,
            duration=self.config.duration_seconds
        )

        if self.config.pattern == TargetPattern.RANDOM_POINTS:
            self._random_points = self._generate_random_points()
            self._current_point_index = 0
            self._point_start_time = self.start_time

        return True

    def stop(self, pupil_distance_mm: float = 0.0) -> Optional[TestResult]:
        """Stop the test and return results."""
        if not self.is_running:
            return None

        self.is_running = False

        if self.current_result:
            self.current_result.uncalibrated = self.uncalibrated
            self.current_result.target_angular_speed_deg_s = self.peak_angular_speed_deg_s()
            self.current_result.compute_metrics(
                self.screen_diagonal,
                screen_config=self.screen_config(),
                pupil_distance_mm=pupil_distance_mm,
            )

        return self.current_result

    def screen_config(self) -> ScreenConfig:
        """Screen geometry used for the degree-domain metrics.

        The software cannot know the physical size of the panel the clinician is using, so the
        nominal 16:9 geometry the rest of the metrics module assumes is used, with the pixel
        size taken from the actual test area.
        """
        height_cm = NOMINAL_SCREEN_HEIGHT_CM
        width_cm = height_cm * (self.screen_width / max(self.screen_height, 1))
        return ScreenConfig(
            width_px=self.screen_width,
            height_px=self.screen_height,
            width_cm=width_cm,
            height_cm=height_cm,
            viewing_distance_cm=DEFAULT_VIEWING_DISTANCE_CM,
        )

    def get_elapsed_time(self) -> float:
        """Get elapsed time since test start."""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time

    def is_complete(self) -> bool:
        """Check if test duration has elapsed."""
        return self.get_elapsed_time() >= self.config.duration_seconds

    def get_target_position(self, at_time: Optional[float] = None) -> Tuple[int, int]:
        """
        Calculate target position based on pattern and time.

        Args:
            at_time: Optional timestamp to calculate position for (for synchronization).
                    If None, uses current time.

        Returns:
            (x, y) target position in pixels
        """
        if not self.is_running or self.start_time is None:
            return (self.screen_width // 2, self.screen_height // 2)

        # Use provided timestamp or current time
        if at_time is not None:
            elapsed = at_time - self.start_time
        else:
            elapsed = self.get_elapsed_time()

        t = elapsed * self.config.speed  # Time factor with speed adjustment

        margin_x = self.screen_width * self.config.margin
        margin_y = self.screen_height * self.config.margin
        usable_width = self.screen_width - 2 * margin_x
        usable_height = self.screen_height - 2 * margin_y

        center_x = self.screen_width // 2
        center_y = self.screen_height // 2

        if self.config.pattern == TargetPattern.HORIZONTAL:
            # Oscillate horizontally
            x = center_x + int((usable_width / 2) * np.sin(t * 2 * np.pi / 3))
            y = center_y
            return (x, y)

        elif self.config.pattern == TargetPattern.VERTICAL:
            # Oscillate vertically
            x = center_x
            y = center_y + int((usable_height / 2) * np.sin(t * 2 * np.pi / 3))
            return (x, y)

        elif self.config.pattern == TargetPattern.CIRCULAR:
            # Circular motion
            radius = self.screen_height * self.config.radius_ratio
            x = center_x + int(radius * np.cos(t * 2 * np.pi / 4))
            y = center_y + int(radius * np.sin(t * 2 * np.pi / 4))
            return (x, y)

        elif self.config.pattern == TargetPattern.FIGURE_EIGHT:
            # Figure-8 (lemniscate) pattern
            radius = self.screen_height * self.config.radius_ratio
            theta = t * 2 * np.pi / 4
            x = center_x + int(radius * np.sin(theta))
            y = center_y + int(radius * np.sin(theta) * np.cos(theta))
            return (x, y)

        elif self.config.pattern == TargetPattern.RANDOM_POINTS:
            # Jump between random points
            current_time = time.time()
            if current_time - self._point_start_time >= self.config.point_duration:
                self._current_point_index = (self._current_point_index + 1) % len(self._random_points)
                self._point_start_time = current_time

            if self._random_points:
                return self._random_points[self._current_point_index]
            else:
                return (center_x, center_y)

        elif self.config.pattern == TargetPattern.FIXATION:
            # Stationary target at center for fixation stability test
            return (center_x, center_y)

        return (center_x, center_y)

    def record_frame(self, gaze_x: Optional[int], gaze_y: Optional[int],
                     head_pitch: float, head_yaw: float, face_detected: bool,
                     capture_time: Optional[float] = None):
        """
        Record a tracking frame.

        Args:
            gaze_x: Estimated gaze X position (None if tracking failed)
            gaze_y: Estimated gaze Y position
            head_pitch: Current head pitch
            head_yaw: Current head yaw
            face_detected: Whether face was detected
            capture_time: Optional timestamp when the frame was captured.
                         Used for synchronizing target position with gaze.
                         If None, uses current time.
        """
        if not self.is_running or self.current_result is None:
            return

        # Use capture timestamp for synchronized target position calculation
        # This ensures the target position matches when the gaze was actually captured
        frame_time = capture_time if capture_time is not None else time.time()
        target_x, target_y = self.get_target_position(at_time=frame_time)

        frame = TrackingFrame(
            timestamp=frame_time,
            target_x=target_x,
            target_y=target_y,
            gaze_x=gaze_x,
            gaze_y=gaze_y,
            head_pitch=head_pitch,
            head_yaw=head_yaw,
            face_detected=face_detected
        )

        self.current_result.frames.append(frame)


def _progress_bar(value: float, max_val: float = 100, width: int = 20, 
                   good_threshold: float = 80, warn_threshold: float = 60) -> str:
    """Generate a visual progress bar with rating."""
    ratio = min(value / max_val, 1.0)
    filled = int(ratio * width)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    
    # Rating based on thresholds
    if value >= good_threshold:
        rating = "✓"
    elif value >= warn_threshold:
        rating = "~"
    else:
        rating = "✗"
    
    return f"[{bar}] {rating}"


def generate_report(result: TestResult, include_clinical: bool = True) -> str:
    """
    Generate a text report from test results.

    Args:
        result: Test result to report on
        include_clinical: Whether to include clinical metrics section

    Returns:
        Formatted report string
    """
    report = []
    report.append("╔" + "═" * 58 + "╗")
    report.append("║" + " EYE MOVEMENT ASSESSMENT REPORT ".center(58) + "║")
    report.append("╚" + "═" * 58 + "╝")
    report.append("")
    report.append(f"  📋 Test Pattern: {result.pattern.value}")
    if result.uncalibrated:
        report.append("")
        report.append("  ⚠️  SCORED WITHOUT CALIBRATION — THIS RESULT IS NOT VALID")
        report.append("     Gaze was estimated without calibration and lands far from the")
        report.append("     target. Calibrate before running a test you intend to score.")
    if result.target_angular_speed_deg_s > 40:
        report.append("")
        report.append(
            f"  ⚠️  Target peaked at {result.target_angular_speed_deg_s:.0f} deg/s, above the"
        )
        report.append(
            "     ~30-40 deg/s smooth-pursuit ceiling. A low score here reflects an"
        )
        report.append("     unwinnable target, not poor tracking. Lower the speed setting.")
    report.append(f"  ⏱️  Duration: {result.duration:.1f} seconds")
    report.append(f"  📊 Total Frames: {len(result.frames)}")
    report.append("")
    report.append("─" * 60)
    report.append("📈 PERFORMANCE METRICS")
    report.append("─" * 60)
    
    # Visual metrics with progress bars
    tracking_pct = result.tracking_ratio  # Already 0-100
    report.append(f"  {'Tracking Rate:':17s} {_progress_bar(tracking_pct)} {tracking_pct:.1f}%")
    report.append(f"  {'':17s} (frames with a usable gaze estimate)")
    report.append(f"  {'Direction Match:':17s} {_progress_bar(result.accuracy_score)} {result.accuracy_score:.1f}/100")
    report.append(f"  {'Speed Match:':17s} {_progress_bar(result.speed_match_score)} {result.speed_match_score:.1f}/100")
    report.append(
        f"  {'Head Stillness:':17s} {_progress_bar(result.head_stillness_score)} "
        f"{result.head_stillness_score:.1f}/100"
    )
    report.append(f"  {'Smoothness:':17s} {_progress_bar(result.smooth_score, good_threshold=70, warn_threshold=50)} {result.smooth_score:.1f}/100")
    report.append(f"  {'Avg Distance:':17s} {result.avg_distance_px:.1f} px from target")

    # Clinical metrics section
    if include_clinical and result.clinical_metrics is not None:
        report.append("")
        report.append("─" * 60)
        report.append("🏥 CLINICAL METRICS")
        report.append("─" * 60)
        
        # Pursuit gain (0.8-1.0 is normal, shown as 80-100%)
        gain_pct = result.pursuit_gain * 100
        gain_bar = _progress_bar(gain_pct, good_threshold=80, warn_threshold=70)
        report.append(f"  Pursuit Gain:   {gain_bar} {result.pursuit_gain:.2f}")
        report.append(f"                  (Normal: 0.80-1.00)")
        
        # Accuracy (lower is better, invert for display)
        acc_score = max(0, 100 - result.accuracy_degrees * 25)  # 0°=100, 4°=0
        acc_bar = _progress_bar(acc_score, good_threshold=50, warn_threshold=25)
        report.append(f"  Accuracy:       {acc_bar} {result.accuracy_degrees:.2f}°")
        report.append(f"                  (Normal: <2°)")
        
        # Smoothness (higher is better)
        smooth_pct = result.smoothness * 100
        smooth_bar = _progress_bar(smooth_pct, good_threshold=70, warn_threshold=50)
        report.append(f"  Smoothness:     {smooth_bar} {result.smoothness:.2f}")
        report.append(f"                  (Normal: >0.70)")
        
        report.append(f"  Saccades:       {result.catch_up_saccade_count} catch-up saccades")
        report.append("")
        report.append("  ⚠️  Provisional thresholds, not clinically validated")
        report.append("     (docs/clinical/sign-off-register.md) - measurements only.")

    report.append("")
    report.append("─" * 60)
    report.append("📏 READING AGAINST PROVISIONAL THRESHOLDS")
    report.append("─" * 60)
    report.append("  These are measurements compared with unvalidated thresholds, not a")
    report.append("  clinical interpretation. Interpretation is the clinician's job.")

    # Clinical reading based on pursuit gain
    if result.clinical_metrics is not None:
        if result.pursuit_gain >= 0.8:
            gain_interp = "✅ Pursuit gain within the provisional band (≥0.8)"
        elif result.pursuit_gain >= 0.7:
            gain_interp = "⚠️ Pursuit gain in the borderline band (0.7-0.8)"
        else:
            gain_interp = "❌ Pursuit gain below the provisional band (<0.7)"
        report.append(f"  {gain_interp}")

        if result.accuracy_degrees <= 2.0:
            acc_interp = "✅ Tracking accuracy within the provisional band (≤2°)"
        elif result.accuracy_degrees <= 3.0:
            acc_interp = "⚠️ Tracking accuracy in the borderline band (2-3°)"
        else:
            acc_interp = "❌ Tracking accuracy above the provisional band (>3°)"
        report.append(f"  {acc_interp}")
    else:
        # Fallback to legacy reading
        if result.accuracy_score >= 80:
            accuracy_interp = "✅ Direction match high"
        elif result.accuracy_score >= 60:
            accuracy_interp = "✅ Direction match good"
        elif result.accuracy_score >= 40:
            accuracy_interp = "⚠️ Direction match moderate"
        else:
            accuracy_interp = "❌ Direction match low"
        report.append(f"  {accuracy_interp}")

    if result.smooth_score >= 70:
        smooth_interp = "✅ Smooth eye movements"
    elif result.smooth_score >= 50:
        smooth_interp = "⚠️ Mostly smooth with some jerkiness"
    else:
        smooth_interp = "❌ Jerky eye movements detected"
    report.append(f"  {smooth_interp}")

    if result.tracking_ratio < 70:
        tracking_interp = "⚠️ Low tracking rate - much of the run had no usable gaze estimate"
    else:
        tracking_interp = "✅ Data quality: Good"
    report.append(f"  {tracking_interp}")

    report.append("")
    report.append("─" * 60)
    report.append("⚕️  DISCLAIMER: This is a screening tool only.")
    report.append("   Consult an eye care professional for diagnosis.")
    report.append("─" * 60)

    return "\n".join(report)
