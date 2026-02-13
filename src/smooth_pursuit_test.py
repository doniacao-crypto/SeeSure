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
    accuracy_score: float = 0.0
    avg_distance_px: float = 0.0
    tracking_ratio: float = 0.0  # Frames with successful tracking
    smooth_score: float = 0.0    # How smooth vs jerky the tracking was (0-100)
    lag_ms: float = 0.0          # Average lag behind target

    # Clinical metrics (new)
    pursuit_gain: float = 0.0              # Eye velocity / Target velocity
    accuracy_degrees: float = 0.0          # RMS error in degrees visual angle
    smoothness: float = 0.0                # 0-1 scale smoothness
    catch_up_saccade_count: int = 0        # Number of corrective saccades
    clinical_metrics: Optional[PursuitMetrics] = None

    def compute_metrics(self, screen_diagonal: float, screen_config: Optional[ScreenConfig] = None):
        """
        Compute all metrics from the recorded frames.

        Args:
            screen_diagonal: Screen diagonal in pixels (for legacy accuracy score)
            screen_config: Optional ScreenConfig for clinical metrics calculation
        """
        if not self.frames:
            return

        valid_frames = [f for f in self.frames if f.gaze_x is not None and f.face_detected]
        self.tracking_ratio = len(valid_frames) / len(self.frames) if self.frames else 0

        if not valid_frames:
            return

        # Calculate distances for legacy metrics
        distances = []
        for f in valid_frames:
            dist = np.sqrt((f.gaze_x - f.target_x)**2 + (f.gaze_y - f.target_y)**2)
            distances.append(dist)

        self.avg_distance_px = np.mean(distances)

        # Legacy accuracy score (0-100, based on distance relative to screen)
        # Threshold increased from 0.2 to 0.4 for more realistic webcam-based tracking
        relative_dist = self.avg_distance_px / screen_diagonal
        self.accuracy_score = max(0, min(100, (1 - relative_dist / 0.4) * 100))

        # Legacy smoothness score (0-100)
        if len(valid_frames) > 2:
            gaze_velocities = []
            for i in range(1, len(valid_frames)):
                dt = valid_frames[i].timestamp - valid_frames[i-1].timestamp
                if dt > 0:
                    dx = valid_frames[i].gaze_x - valid_frames[i-1].gaze_x
                    dy = valid_frames[i].gaze_y - valid_frames[i-1].gaze_y
                    velocity = np.sqrt(dx**2 + dy**2) / dt
                    gaze_velocities.append(velocity)

            if gaze_velocities:
                velocity_std = np.std(gaze_velocities)
                velocity_mean = np.mean(gaze_velocities) + 1
                cv = velocity_std / velocity_mean
                self.smooth_score = max(0, min(100, (1 - cv) * 100))

        # Calculate clinical metrics if screen config is provided
        if screen_config is not None:
            self._compute_clinical_metrics(screen_config, valid_frames)

    def _compute_clinical_metrics(self, screen_config: ScreenConfig, valid_frames: List[TrackingFrame]):
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
            target_positions, gaze_positions, timestamps
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
            "metrics": {
                "tracking_ratio": round(self.tracking_ratio, 4),
                "avg_distance_px": round(self.avg_distance_px, 2),
                "accuracy_score": round(self.accuracy_score, 2),
                "smooth_score": round(self.smooth_score, 2),
                "lag_ms": round(self.lag_ms, 2),
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

    def stop(self) -> Optional[TestResult]:
        """Stop the test and return results."""
        if not self.is_running:
            return None

        self.is_running = False

        if self.current_result:
            self.current_result.compute_metrics(self.screen_diagonal)

        return self.current_result

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
    report.append(f"  ⏱️  Duration: {result.duration:.1f} seconds")
    report.append(f"  📊 Total Frames: {len(result.frames)}")
    report.append("")
    report.append("─" * 60)
    report.append("📈 PERFORMANCE METRICS")
    report.append("─" * 60)
    
    # Visual metrics with progress bars
    tracking_pct = result.tracking_ratio * 100
    report.append(f"  Tracking Rate:  {_progress_bar(tracking_pct)} {tracking_pct:.1f}%")
    report.append(f"  Accuracy:       {_progress_bar(result.accuracy_score)} {result.accuracy_score:.1f}/100")
    report.append(f"  Smoothness:     {_progress_bar(result.smooth_score, good_threshold=70, warn_threshold=50)} {result.smooth_score:.1f}/100")
    report.append(f"  Avg Distance:   {result.avg_distance_px:.1f} px from target")

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
    report.append("─" * 60)
    report.append("💡 INTERPRETATION")
    report.append("─" * 60)

    # Clinical interpretation based on pursuit gain
    if result.clinical_metrics is not None:
        if result.pursuit_gain >= 0.8:
            gain_interp = "✅ Pursuit gain NORMAL (≥0.8)"
        elif result.pursuit_gain >= 0.7:
            gain_interp = "⚠️ Pursuit gain BORDERLINE (0.7-0.8) - monitor"
        else:
            gain_interp = "❌ Pursuit gain ABNORMAL (<0.7) - recommend evaluation"
        report.append(f"  {gain_interp}")

        if result.accuracy_degrees <= 2.0:
            acc_interp = "✅ Tracking accuracy NORMAL (≤2°)"
        elif result.accuracy_degrees <= 3.0:
            acc_interp = "⚠️ Tracking accuracy BORDERLINE (2-3°)"
        else:
            acc_interp = "❌ Tracking accuracy ABNORMAL (>3°) - recommend evaluation"
        report.append(f"  {acc_interp}")
    else:
        # Fallback to legacy interpretation
        if result.accuracy_score >= 80:
            accuracy_interp = "✅ Excellent tracking accuracy"
        elif result.accuracy_score >= 60:
            accuracy_interp = "✅ Good tracking accuracy"
        elif result.accuracy_score >= 40:
            accuracy_interp = "⚠️ Moderate tracking accuracy - may indicate difficulties"
        else:
            accuracy_interp = "❌ Poor tracking accuracy - recommend evaluation"
        report.append(f"  {accuracy_interp}")

    if result.smooth_score >= 70:
        smooth_interp = "✅ Smooth eye movements"
    elif result.smooth_score >= 50:
        smooth_interp = "⚠️ Mostly smooth with some jerkiness"
    else:
        smooth_interp = "❌ Jerky eye movements detected - may indicate oculomotor issues"
    report.append(f"  {smooth_interp}")

    if result.tracking_ratio < 0.7:
        tracking_interp = "⚠️ Low tracking rate may affect reliability"
    else:
        tracking_interp = "✅ Data quality: Good"
    report.append(f"  {tracking_interp}")

    report.append("")
    report.append("─" * 60)
    report.append("⚕️  DISCLAIMER: This is a screening tool only.")
    report.append("   Consult an eye care professional for diagnosis.")
    report.append("─" * 60)

    return "\n".join(report)
