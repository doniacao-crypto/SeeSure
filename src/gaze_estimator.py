"""
Gaze Estimation Module - Enhanced Version
Maps eye/iris positions to screen coordinates with head pose compensation.
Uses calibration data to build a personalized mapping model.

Improvements over baseline:
- Polynomial regression with Ridge regularization (replaces RBF)
- 1-Euro Filter for adaptive jitter reduction
- Kalman Filter for state estimation and velocity tracking
- Multi-sample calibration support
- Learned head pose compensation
- Blink detection integration
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict
import json
from pathlib import Path
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.pipeline import Pipeline
from eye_tracker import EyeData
from filters import OneEuroFilter2D, GazeKalmanFilter, CombinedFilter


@dataclass
class CalibrationSample:
    """A single sample within a calibration point."""
    left_iris: Tuple[float, float]
    right_iris: Tuple[float, float]
    head_pitch: float
    head_yaw: float
    head_roll: float
    timestamp: float = 0.0


@dataclass
class CalibrationPoint:
    """A calibration point with multiple samples."""
    screen_x: int
    screen_y: int
    left_iris: Tuple[float, float]
    right_iris: Tuple[float, float]
    head_pitch: float
    head_yaw: float
    head_roll: float
    timestamp: float = 0.0
    # Multi-sample support
    samples: List[CalibrationSample] = field(default_factory=list)

    @classmethod
    def from_samples(
        cls,
        screen_x: int,
        screen_y: int,
        samples: List[CalibrationSample]
    ) -> "CalibrationPoint":
        """Create a calibration point by averaging multiple samples."""
        if not samples:
            raise ValueError("No samples provided")

        # Compute robust average (exclude outliers using IQR)
        left_iris_x = [s.left_iris[0] for s in samples]
        left_iris_y = [s.left_iris[1] for s in samples]
        right_iris_x = [s.right_iris[0] for s in samples]
        right_iris_y = [s.right_iris[1] for s in samples]
        pitches = [s.head_pitch for s in samples]
        yaws = [s.head_yaw for s in samples]
        rolls = [s.head_roll for s in samples]

        def robust_mean(values: List[float]) -> float:
            """Compute mean after removing outliers."""
            if len(values) < 4:
                return np.mean(values)
            q1, q3 = np.percentile(values, [25, 75])
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            filtered = [v for v in values if lower <= v <= upper]
            return np.mean(filtered) if filtered else np.mean(values)

        return cls(
            screen_x=screen_x,
            screen_y=screen_y,
            left_iris=(robust_mean(left_iris_x), robust_mean(left_iris_y)),
            right_iris=(robust_mean(right_iris_x), robust_mean(right_iris_y)),
            head_pitch=robust_mean(pitches),
            head_yaw=robust_mean(yaws),
            head_roll=robust_mean(rolls),
            timestamp=samples[-1].timestamp,
            samples=samples
        )


@dataclass
class CalibrationProfile:
    """User calibration profile."""
    name: str = "default"
    screen_width: int = 1920
    screen_height: int = 1080
    points: List[CalibrationPoint] = field(default_factory=list)
    created_at: str = ""
    # Learned head compensation factors
    pitch_factor: float = 15.0
    yaw_factor: float = 20.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "created_at": self.created_at,
            "pitch_factor": self.pitch_factor,
            "yaw_factor": self.yaw_factor,
            "points": [
                {
                    "screen_x": p.screen_x,
                    "screen_y": p.screen_y,
                    "left_iris": p.left_iris,
                    "right_iris": p.right_iris,
                    "head_pitch": p.head_pitch,
                    "head_yaw": p.head_yaw,
                    "head_roll": p.head_roll,
                    "timestamp": p.timestamp,
                    "samples": [
                        {
                            "left_iris": s.left_iris,
                            "right_iris": s.right_iris,
                            "head_pitch": s.head_pitch,
                            "head_yaw": s.head_yaw,
                            "head_roll": s.head_roll,
                            "timestamp": s.timestamp
                        }
                        for s in p.samples
                    ] if p.samples else []
                }
                for p in self.points
            ]
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CalibrationProfile":
        """Create from dictionary."""
        profile = cls(
            name=data.get("name", "default"),
            screen_width=data.get("screen_width", 1920),
            screen_height=data.get("screen_height", 1080),
            created_at=data.get("created_at", ""),
            pitch_factor=data.get("pitch_factor", 15.0),
            yaw_factor=data.get("yaw_factor", 20.0)
        )
        for p in data.get("points", []):
            samples = []
            for s in p.get("samples", []):
                samples.append(CalibrationSample(
                    left_iris=tuple(s["left_iris"]),
                    right_iris=tuple(s["right_iris"]),
                    head_pitch=s["head_pitch"],
                    head_yaw=s["head_yaw"],
                    head_roll=s["head_roll"],
                    timestamp=s.get("timestamp", 0.0)
                ))
            profile.points.append(CalibrationPoint(
                screen_x=p["screen_x"],
                screen_y=p["screen_y"],
                left_iris=tuple(p["left_iris"]),
                right_iris=tuple(p["right_iris"]),
                head_pitch=p["head_pitch"],
                head_yaw=p["head_yaw"],
                head_roll=p["head_roll"],
                timestamp=p.get("timestamp", 0.0),
                samples=samples
            ))
        return profile


class GazeEstimator:
    """
    Enhanced gaze estimator with improved accuracy.

    Features:
    - Polynomial regression with Ridge regularization
    - 1-Euro Filter for adaptive smoothing
    - Kalman Filter for state estimation
    - Multi-sample calibration
    - Learned head pose compensation
    - Blink handling with prediction
    """

    # Filter mode options
    FILTER_NONE = 'none'
    FILTER_ONE_EURO = 'one_euro'
    FILTER_KALMAN = 'kalman'
    FILTER_COMBINED = 'combined'

    def __init__(
        self,
        screen_width: int = 1920,
        screen_height: int = 1080,
        filter_mode: str = 'combined',
        polynomial_degree: int = 2
    ):
        """
        Initialize the gaze estimator.

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
            filter_mode: Filtering mode ('none', 'one_euro', 'kalman', 'combined')
            polynomial_degree: Degree of polynomial features (1, 2, or 3)
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.polynomial_degree = polynomial_degree

        # Calibration data
        self.calibration_profile: Optional[CalibrationProfile] = None
        self.is_calibrated = False

        # Polynomial regression models with scaling (replaces RBF)
        self._poly_features: Optional[PolynomialFeatures] = None
        self._scaler: Optional[StandardScaler] = None
        self._model_x: Optional[Ridge] = None
        self._model_y: Optional[Ridge] = None

        # Reference head pose (recorded during calibration)
        self._ref_head_pitch = 0.0
        self._ref_head_yaw = 0.0
        self._ref_head_roll = 0.0

        # Head pose compensation factors (can be learned)
        self._pitch_factor = 15.0  # pixels per degree
        self._yaw_factor = 20.0    # pixels per degree

        # Filtering
        self.filter_mode = filter_mode
        self._setup_filters()

        # Multi-sample calibration state
        self._current_samples: List[CalibrationSample] = []
        self._samples_per_point = 10

        # Blink handling
        self._last_valid_gaze: Optional[Tuple[float, float]] = None
        self._blink_frames = 0
        self._max_blink_prediction_frames = 5

    def _setup_filters(self):
        """Initialize filtering components."""
        # 1-Euro Filter (adaptive jitter reduction)
        self._one_euro_filter = OneEuroFilter2D(
            freq=30.0,
            mincutoff=1.0,
            beta=0.007,
            dcutoff=1.0
        )

        # Kalman Filter (state estimation)
        self._kalman_filter = GazeKalmanFilter(
            process_noise_pos=0.5,
            process_noise_vel=2.0,
            measurement_noise_fixation=10.0,
            measurement_noise_saccade=50.0,
            saccade_threshold=100.0
        )

        # Combined Filter
        self._combined_filter = CombinedFilter(
            freq=30.0,
            one_euro_mincutoff=1.5,
            one_euro_beta=0.01,
            kalman_process_noise=0.5,
            kalman_measurement_noise=10.0
        )

    def set_filter_mode(self, mode: str):
        """Change the filtering mode."""
        if mode not in [self.FILTER_NONE, self.FILTER_ONE_EURO,
                        self.FILTER_KALMAN, self.FILTER_COMBINED]:
            raise ValueError(f"Invalid filter mode: {mode}")
        self.filter_mode = mode
        self._reset_filters()

    def _reset_filters(self):
        """Reset all filter states."""
        self._one_euro_filter.reset()
        self._kalman_filter.reset()
        self._combined_filter.reset()

    def start_calibration(self, profile_name: str = "default") -> CalibrationProfile:
        """
        Start a new calibration session.

        Args:
            profile_name: Name for the calibration profile

        Returns:
            New calibration profile
        """
        from datetime import datetime

        self.calibration_profile = CalibrationProfile(
            name=profile_name,
            screen_width=self.screen_width,
            screen_height=self.screen_height,
            created_at=datetime.now().isoformat()
        )
        self.is_calibrated = False
        self._reset_filters()
        return self.calibration_profile

    def start_collecting_samples(self):
        """Start collecting samples for a calibration point."""
        self._current_samples = []

    def add_calibration_sample(self, eye_data: EyeData, timestamp: float = 0.0) -> bool:
        """
        Add a sample for the current calibration point.

        Args:
            eye_data: Current eye tracking data
            timestamp: Recording timestamp

        Returns:
            True if sample was added successfully
        """
        if not eye_data.face_detected:
            return False

        if eye_data.left_iris_center is None or eye_data.right_iris_center is None:
            return False

        sample = CalibrationSample(
            left_iris=eye_data.left_iris_center,
            right_iris=eye_data.right_iris_center,
            head_pitch=eye_data.head_pitch,
            head_yaw=eye_data.head_yaw,
            head_roll=eye_data.head_roll,
            timestamp=timestamp
        )
        self._current_samples.append(sample)
        return True

    def finish_collecting_samples(
        self,
        screen_x: int,
        screen_y: int,
        min_samples: int = 5
    ) -> bool:
        """
        Finish collecting samples and create averaged calibration point.

        Args:
            screen_x: Target X position on screen
            screen_y: Target Y position on screen
            min_samples: Minimum number of samples required

        Returns:
            True if point was created successfully
        """
        if self.calibration_profile is None:
            return False

        if len(self._current_samples) < min_samples:
            return False

        point = CalibrationPoint.from_samples(
            screen_x=screen_x,
            screen_y=screen_y,
            samples=self._current_samples
        )
        self.calibration_profile.points.append(point)
        self._current_samples = []
        return True

    def add_calibration_point(
        self,
        screen_x: int,
        screen_y: int,
        eye_data: EyeData,
        timestamp: float = 0.0
    ) -> bool:
        """
        Add a single-sample calibration point (legacy interface).

        Args:
            screen_x: Target X position on screen
            screen_y: Target Y position on screen
            eye_data: Current eye tracking data
            timestamp: Recording timestamp

        Returns:
            True if point was added successfully
        """
        if self.calibration_profile is None:
            return False

        if not eye_data.face_detected:
            return False

        if eye_data.left_iris_center is None or eye_data.right_iris_center is None:
            return False

        point = CalibrationPoint(
            screen_x=screen_x,
            screen_y=screen_y,
            left_iris=eye_data.left_iris_center,
            right_iris=eye_data.right_iris_center,
            head_pitch=eye_data.head_pitch,
            head_yaw=eye_data.head_yaw,
            head_roll=eye_data.head_roll,
            timestamp=timestamp
        )

        self.calibration_profile.points.append(point)
        return True

    def _build_features(self, iris_x: float, iris_y: float,
                        pitch: float, yaw: float) -> np.ndarray:
        """Build scaled polynomial feature vector."""
        base_features = np.array([[iris_x, iris_y, pitch, yaw]])

        if self._poly_features is None or self._scaler is None:
            # Not fitted yet - return raw features (will be fitted during calibration)
            return base_features

        # Scale raw features first, then apply polynomial transformation
        scaled = self._scaler.transform(base_features)
        # Handle any inf/nan from scaling (e.g., zero variance features)
        scaled = np.nan_to_num(scaled, nan=0.0, posinf=0.0, neginf=0.0)
        poly_features = self._poly_features.transform(scaled)
        # Ensure no inf/nan in polynomial features
        return np.nan_to_num(poly_features, nan=0.0, posinf=0.0, neginf=0.0)

    def _learn_head_compensation(self, features: np.ndarray,
                                 target_x: np.ndarray,
                                 target_y: np.ndarray,
                                 head_pitches: np.ndarray,
                                 head_yaws: np.ndarray):
        """Learn optimal head pose compensation factors."""
        # Get predictions without head compensation
        pred_x = self._model_x.predict(features)
        pred_y = self._model_y.predict(features)

        # Compute residual errors
        error_x = target_x - pred_x
        error_y = target_y - pred_y

        # Center head pose
        pitch_delta = head_pitches - self._ref_head_pitch
        yaw_delta = head_yaws - self._ref_head_yaw

        # Fit linear relationship: error = factor * head_delta
        # Using simple linear regression
        if np.std(yaw_delta) > 0.1:
            # Negative because looking right (positive yaw) should decrease x
            self._yaw_factor = -np.sum(error_x * yaw_delta) / np.sum(yaw_delta**2)
            self._yaw_factor = np.clip(self._yaw_factor, 5.0, 50.0)

        if np.std(pitch_delta) > 0.1:
            # Positive because looking down (positive pitch) should increase y
            self._pitch_factor = np.sum(error_y * pitch_delta) / np.sum(pitch_delta**2)
            self._pitch_factor = np.clip(self._pitch_factor, 5.0, 50.0)

        # Store in profile
        if self.calibration_profile:
            self.calibration_profile.pitch_factor = self._pitch_factor
            self.calibration_profile.yaw_factor = self._yaw_factor

    def finish_calibration(self) -> bool:
        """
        Finish calibration and build the mapping model.

        Returns:
            True if calibration was successful
        """
        if self.calibration_profile is None:
            return False

        if len(self.calibration_profile.points) < 5:
            print(f"Not enough calibration points: {len(self.calibration_profile.points)} (need at least 5)")
            return False

        # Build feature vectors from calibration points
        features_raw = []
        target_x = []
        target_y = []
        head_pitches = []
        head_yaws = []

        for point in self.calibration_profile.points:
            # Average iris position (combining both eyes)
            avg_iris_x = (point.left_iris[0] + point.right_iris[0]) / 2
            avg_iris_y = (point.left_iris[1] + point.right_iris[1]) / 2

            features_raw.append([avg_iris_x, avg_iris_y, point.head_pitch, point.head_yaw])
            target_x.append(point.screen_x)
            target_y.append(point.screen_y)
            head_pitches.append(point.head_pitch)
            head_yaws.append(point.head_yaw)

        features_raw = np.array(features_raw)
        target_x = np.array(target_x)
        target_y = np.array(target_y)
        head_pitches = np.array(head_pitches)
        head_yaws = np.array(head_yaws)

        # Store reference head pose (average during calibration)
        self._ref_head_pitch = np.mean(head_pitches)
        self._ref_head_yaw = np.mean(head_yaws)

        # Scale features first to prevent numerical overflow in polynomial expansion
        self._scaler = StandardScaler()
        features_scaled = self._scaler.fit_transform(features_raw)

        # Handle edge case where scaler produces inf/nan (zero variance in a feature)
        # Replace any inf/nan with 0 (centered value)
        features_scaled = np.nan_to_num(features_scaled, nan=0.0, posinf=0.0, neginf=0.0)

        # Build polynomial features on scaled data
        self._poly_features = PolynomialFeatures(
            degree=self.polynomial_degree,
            include_bias=True
        )
        features = self._poly_features.fit_transform(features_scaled)

        # Ensure no inf/nan in polynomial features
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)

        # Build Ridge regression models
        # Alpha (regularization strength) prevents overfitting
        try:
            self._model_x = Ridge(alpha=1.0)
            self._model_x.fit(features, target_x)

            self._model_y = Ridge(alpha=1.0)
            self._model_y.fit(features, target_y)

            # Learn head compensation factors
            self._learn_head_compensation(
                features, target_x, target_y, head_pitches, head_yaws
            )

            self.is_calibrated = True
            self._reset_filters()
            return True

        except Exception as e:
            print(f"Calibration failed: {e}")
            return False

    def estimate_gaze(
        self,
        eye_data: EyeData,
        apply_smoothing: bool = True,
        timestamp: Optional[float] = None,
        is_blink: bool = False
    ) -> Optional[Tuple[int, int]]:
        """
        Estimate gaze position on screen.

        Args:
            eye_data: Current eye tracking data
            apply_smoothing: Whether to apply temporal smoothing
            timestamp: Optional timestamp for filtering
            is_blink: Whether a blink is detected

        Returns:
            (x, y) screen coordinates or None if estimation failed
        """
        # Handle blink with prediction
        if is_blink:
            return self._handle_blink(timestamp)

        if not self.is_calibrated:
            return self._estimate_gaze_uncalibrated(eye_data, apply_smoothing, timestamp)

        if not eye_data.face_detected:
            return self._handle_blink(timestamp)

        if eye_data.left_iris_center is None or eye_data.right_iris_center is None:
            return self._handle_blink(timestamp)

        # Reset blink counter
        self._blink_frames = 0

        # Build feature vector
        avg_iris_x = (eye_data.left_iris_center[0] + eye_data.right_iris_center[0]) / 2
        avg_iris_y = (eye_data.left_iris_center[1] + eye_data.right_iris_center[1]) / 2

        features = self._build_features(
            avg_iris_x, avg_iris_y,
            eye_data.head_pitch, eye_data.head_yaw
        )

        # Estimate screen position
        try:
            gaze_x = float(self._model_x.predict(features)[0])
            gaze_y = float(self._model_y.predict(features)[0])
        except Exception:
            return None

        # Apply head pose compensation for movement beyond calibration range
        pitch_delta = eye_data.head_pitch - self._ref_head_pitch
        yaw_delta = eye_data.head_yaw - self._ref_head_yaw

        gaze_y += pitch_delta * self._pitch_factor
        gaze_x -= yaw_delta * self._yaw_factor

        # Clamp to screen bounds (before filtering)
        gaze_x = np.clip(gaze_x, 0, self.screen_width - 1)
        gaze_y = np.clip(gaze_y, 0, self.screen_height - 1)

        # Apply filtering
        if apply_smoothing:
            gaze_x, gaze_y = self._apply_filter(gaze_x, gaze_y, timestamp)

        # Store last valid gaze for blink prediction
        self._last_valid_gaze = (gaze_x, gaze_y)

        return (int(gaze_x), int(gaze_y))

    def _handle_blink(self, timestamp: Optional[float]) -> Optional[Tuple[int, int]]:
        """Handle blink by predicting gaze position."""
        self._blink_frames += 1

        if self._blink_frames > self._max_blink_prediction_frames:
            return None

        # Use Kalman filter prediction during blink
        if self.filter_mode in [self.FILTER_KALMAN, self.FILTER_COMBINED]:
            dt = 1.0 / 30.0  # Assume 30 FPS
            if self.filter_mode == self.FILTER_COMBINED:
                gaze_x, gaze_y = self._combined_filter.predict(dt)
            else:
                gaze_x, gaze_y = self._kalman_filter.predict(dt)
            return (int(gaze_x), int(gaze_y))

        # Fallback: return last valid gaze
        if self._last_valid_gaze:
            return (int(self._last_valid_gaze[0]), int(self._last_valid_gaze[1]))

        return None

    def _apply_filter(
        self,
        x: float,
        y: float,
        timestamp: Optional[float]
    ) -> Tuple[float, float]:
        """Apply the configured filter to gaze coordinates."""
        if self.filter_mode == self.FILTER_NONE:
            return (x, y)

        elif self.filter_mode == self.FILTER_ONE_EURO:
            return self._one_euro_filter.filter(x, y, timestamp)

        elif self.filter_mode == self.FILTER_KALMAN:
            return self._kalman_filter.update(x, y, timestamp)

        elif self.filter_mode == self.FILTER_COMBINED:
            return self._combined_filter.filter(x, y, timestamp)

        return (x, y)

    def _estimate_gaze_uncalibrated(
        self,
        eye_data: EyeData,
        apply_smoothing: bool = True,
        timestamp: Optional[float] = None
    ) -> Optional[Tuple[int, int]]:
        """
        Estimate gaze without calibration (less accurate).
        Uses a simple linear mapping.
        """
        if not eye_data.face_detected:
            return None

        if eye_data.left_iris_center is None or eye_data.right_iris_center is None:
            return None

        # Average iris position
        avg_x = (eye_data.left_iris_center[0] + eye_data.right_iris_center[0]) / 2
        avg_y = (eye_data.left_iris_center[1] + eye_data.right_iris_center[1]) / 2

        # Simple linear mapping with head compensation
        base_x = avg_x * self.screen_width
        base_y = avg_y * self.screen_height

        # Head pose compensation
        base_x -= eye_data.head_yaw * self._yaw_factor
        base_y += eye_data.head_pitch * self._pitch_factor

        # Clamp
        gaze_x = np.clip(base_x, 0, self.screen_width - 1)
        gaze_y = np.clip(base_y, 0, self.screen_height - 1)

        # Apply filtering
        if apply_smoothing:
            gaze_x, gaze_y = self._apply_filter(gaze_x, gaze_y, timestamp)

        return (int(gaze_x), int(gaze_y))

    def get_velocity(self) -> Optional[Tuple[float, float]]:
        """Get current gaze velocity from Kalman filter."""
        if self.filter_mode in [self.FILTER_KALMAN, self.FILTER_COMBINED]:
            if self.filter_mode == self.FILTER_COMBINED:
                return self._combined_filter.kalman.get_velocity()
            return self._kalman_filter.get_velocity()
        return None

    def is_saccade(self) -> bool:
        """Check if currently in a saccade movement."""
        if self.filter_mode == self.FILTER_COMBINED:
            return self._combined_filter.is_saccade
        elif self.filter_mode == self.FILTER_KALMAN:
            return self._kalman_filter.is_saccade
        return False

    def save_profile(self, filepath: str) -> bool:
        """
        Save calibration profile to file.

        Args:
            filepath: Path to save the profile

        Returns:
            True if saved successfully
        """
        if self.calibration_profile is None:
            return False

        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w') as f:
                json.dump(self.calibration_profile.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save profile: {e}")
            return False

    def load_profile(self, filepath: str) -> bool:
        """
        Load calibration profile from file.

        Args:
            filepath: Path to the profile file

        Returns:
            True if loaded and calibration built successfully
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            self.calibration_profile = CalibrationProfile.from_dict(data)

            # Update screen dimensions from profile
            self.screen_width = self.calibration_profile.screen_width
            self.screen_height = self.calibration_profile.screen_height

            # Restore head compensation factors
            self._pitch_factor = self.calibration_profile.pitch_factor
            self._yaw_factor = self.calibration_profile.yaw_factor

            # Rebuild the mapping model
            return self.finish_calibration()
        except Exception as e:
            print(f"Failed to load profile: {e}")
            return False

    def get_calibration_quality(self) -> Dict[str, float]:
        """
        Assess calibration quality.

        Returns:
            Dictionary with quality metrics
        """
        if not self.is_calibrated or self.calibration_profile is None:
            return {"quality": 0.0, "points": 0, "coverage": 0.0}

        num_points = len(self.calibration_profile.points)

        # Check screen coverage
        xs = [p.screen_x for p in self.calibration_profile.points]
        ys = [p.screen_y for p in self.calibration_profile.points]

        x_coverage = (max(xs) - min(xs)) / self.screen_width
        y_coverage = (max(ys) - min(ys)) / self.screen_height
        coverage = (x_coverage + y_coverage) / 2

        # Calculate reprojection error
        total_error = 0.0
        for point in self.calibration_profile.points:
            avg_iris_x = (point.left_iris[0] + point.right_iris[0]) / 2
            avg_iris_y = (point.left_iris[1] + point.right_iris[1]) / 2
            features = self._build_features(
                avg_iris_x, avg_iris_y,
                point.head_pitch, point.head_yaw
            )

            try:
                pred_x = float(self._model_x.predict(features)[0])
                pred_y = float(self._model_y.predict(features)[0])
                error = np.sqrt((pred_x - point.screen_x)**2 + (pred_y - point.screen_y)**2)
                total_error += error
            except Exception:
                total_error += 100  # Penalty for failed prediction

        avg_error = total_error / num_points if num_points > 0 else float('inf')

        # Quality score
        error_quality = max(0, 1 - avg_error / 100)
        samples_quality = sum(1 for p in self.calibration_profile.points if len(p.samples) >= 5) / num_points

        overall_quality = (
            error_quality * 0.5 +
            coverage * 0.25 +
            min(num_points / 9, 1) * 0.15 +
            samples_quality * 0.1
        )

        return {
            "quality": overall_quality,
            "points": num_points,
            "coverage": coverage,
            "avg_error_px": avg_error,
            "error_quality": error_quality,
            "samples_quality": samples_quality
        }
