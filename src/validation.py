"""
Gaze Accuracy Validation Framework.
Measures and validates gaze estimation accuracy against known positions.
"""

import time
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum


class ValidationPattern(Enum):
    """Validation test patterns."""
    GRID_9 = "grid_9"          # 3x3 grid (9 points)
    GRID_16 = "grid_16"        # 4x4 grid (16 points)
    RANDOM_20 = "random_20"    # 20 random positions


@dataclass
class ValidationPoint:
    """A single validation point with collected data."""
    target_x: int
    target_y: int
    target_deg_x: float  # Position in degrees from center
    target_deg_y: float
    
    # Collected gaze samples
    gaze_samples_x: List[float] = field(default_factory=list)
    gaze_samples_y: List[float] = field(default_factory=list)
    timestamps: List[float] = field(default_factory=list)
    
    @property
    def num_samples(self) -> int:
        return len(self.gaze_samples_x)
    
    @property
    def mean_gaze_x(self) -> Optional[float]:
        return np.mean(self.gaze_samples_x) if self.gaze_samples_x else None
    
    @property
    def mean_gaze_y(self) -> Optional[float]:
        return np.mean(self.gaze_samples_y) if self.gaze_samples_y else None
    
    @property
    def std_gaze_x(self) -> Optional[float]:
        return np.std(self.gaze_samples_x) if len(self.gaze_samples_x) > 1 else None
    
    @property
    def std_gaze_y(self) -> Optional[float]:
        return np.std(self.gaze_samples_y) if len(self.gaze_samples_y) > 1 else None


@dataclass
class ValidationConfig:
    """Configuration for validation test."""
    pattern: ValidationPattern = ValidationPattern.GRID_9
    samples_per_point: int = 30          # Samples to collect at each point
    point_duration_ms: float = 2000.0    # Time at each point
    
    # Screen configuration
    screen_width_px: int = 1920
    screen_height_px: int = 1080
    viewing_distance_cm: float = 60.0
    screen_width_cm: float = 52.0
    screen_height_cm: float = 29.0
    
    # Grid margin (percentage from edge)
    margin_percent: float = 0.15


@dataclass
class ValidationResult:
    """Results of validation test."""
    config: ValidationConfig
    points: List[ValidationPoint] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    
    # Calculated after test
    _px_per_deg: float = 0.0
    
    def set_px_per_deg(self, value: float):
        self._px_per_deg = value
    
    @property
    def accuracy_degrees(self) -> Optional[float]:
        """Mean accuracy across all points in degrees visual angle."""
        errors = []
        for point in self.points:
            if point.mean_gaze_x is not None and point.mean_gaze_y is not None:
                error_px = np.sqrt(
                    (point.mean_gaze_x - point.target_x)**2 +
                    (point.mean_gaze_y - point.target_y)**2
                )
                if self._px_per_deg > 0:
                    errors.append(error_px / self._px_per_deg)
        return np.mean(errors) if errors else None
    
    @property
    def accuracy_std_degrees(self) -> Optional[float]:
        """Standard deviation of accuracy in degrees."""
        errors = []
        for point in self.points:
            if point.mean_gaze_x is not None and point.mean_gaze_y is not None:
                error_px = np.sqrt(
                    (point.mean_gaze_x - point.target_x)**2 +
                    (point.mean_gaze_y - point.target_y)**2
                )
                if self._px_per_deg > 0:
                    errors.append(error_px / self._px_per_deg)
        return np.std(errors) if len(errors) > 1 else None
    
    @property
    def precision_degrees(self) -> Optional[float]:
        """Mean precision (within-point variability) in degrees."""
        precisions = []
        for point in self.points:
            if point.std_gaze_x is not None and point.std_gaze_y is not None:
                precision_px = np.sqrt(point.std_gaze_x**2 + point.std_gaze_y**2)
                if self._px_per_deg > 0:
                    precisions.append(precision_px / self._px_per_deg)
        return np.mean(precisions) if precisions else None
    
    @property
    def worst_point_accuracy(self) -> Optional[float]:
        """Worst accuracy among all points in degrees."""
        errors = []
        for point in self.points:
            if point.mean_gaze_x is not None and point.mean_gaze_y is not None:
                error_px = np.sqrt(
                    (point.mean_gaze_x - point.target_x)**2 +
                    (point.mean_gaze_y - point.target_y)**2
                )
                if self._px_per_deg > 0:
                    errors.append(error_px / self._px_per_deg)
        return max(errors) if errors else None
    
    @property
    def valid_points(self) -> int:
        """Number of points with valid data."""
        return sum(1 for p in self.points if p.num_samples > 0)
    
    @property
    def meets_clinical_threshold(self) -> bool:
        """Check if accuracy meets <2° clinical threshold."""
        acc = self.accuracy_degrees
        return acc is not None and acc < 2.0


class ValidationTest:
    """
    Gaze accuracy validation test.
    
    Presents known target positions and measures gaze accuracy.
    """
    
    def __init__(self, config: ValidationConfig):
        """
        Initialize validation test.
        
        Args:
            config: Test configuration
        """
        self.config = config
        self.result = ValidationResult(config=config)
        
        # Calculate pixels per degree
        screen_distance_px = (config.screen_width_px / config.screen_width_cm) * config.viewing_distance_cm
        self.px_per_deg = screen_distance_px * np.tan(np.radians(1))
        self.result.set_px_per_deg(self.px_per_deg)
        
        # Screen center
        self.center_x = config.screen_width_px // 2
        self.center_y = config.screen_height_px // 2
        
        # Generate validation points
        self._points: List[ValidationPoint] = []
        self._generate_points()
        
        # State
        self._current_point_index = 0
        self._point_start_time = 0.0
        self.is_running = False
    
    def _generate_points(self):
        """Generate validation point positions."""
        cfg = self.config
        
        # Calculate margins
        margin_x = int(cfg.screen_width_px * cfg.margin_percent)
        margin_y = int(cfg.screen_height_px * cfg.margin_percent)
        
        if cfg.pattern == ValidationPattern.GRID_9:
            # 3x3 grid
            cols = [margin_x, cfg.screen_width_px // 2, cfg.screen_width_px - margin_x]
            rows = [margin_y, cfg.screen_height_px // 2, cfg.screen_height_px - margin_y]
            
            for y in rows:
                for x in cols:
                    self._add_point(x, y)
        
        elif cfg.pattern == ValidationPattern.GRID_16:
            # 4x4 grid
            x_step = (cfg.screen_width_px - 2 * margin_x) / 3
            y_step = (cfg.screen_height_px - 2 * margin_y) / 3
            
            for i in range(4):
                for j in range(4):
                    x = int(margin_x + j * x_step)
                    y = int(margin_y + i * y_step)
                    self._add_point(x, y)
        
        elif cfg.pattern == ValidationPattern.RANDOM_20:
            # 20 random positions
            np.random.seed(42)  # Reproducible
            for _ in range(20):
                x = np.random.randint(margin_x, cfg.screen_width_px - margin_x)
                y = np.random.randint(margin_y, cfg.screen_height_px - margin_y)
                self._add_point(x, y)
    
    def _add_point(self, x: int, y: int):
        """Add a validation point."""
        # Convert to degrees from center
        deg_x = (x - self.center_x) / self.px_per_deg
        deg_y = (y - self.center_y) / self.px_per_deg
        
        point = ValidationPoint(
            target_x=x,
            target_y=y,
            target_deg_x=deg_x,
            target_deg_y=deg_y
        )
        self._points.append(point)
    
    def start(self):
        """Start the validation test."""
        self.is_running = True
        self.result.start_time = time.time()
        self._current_point_index = 0
        self._point_start_time = time.time()
    
    def stop(self):
        """Stop the validation test."""
        self.is_running = False
        self.result.end_time = time.time()
        self.result.points = self._points.copy()
    
    def update(self, gaze_x: Optional[float], gaze_y: Optional[float], timestamp: float):
        """
        Update test with new gaze data.
        
        Args:
            gaze_x: Current gaze X position (pixels)
            gaze_y: Current gaze Y position (pixels)
            timestamp: Current timestamp
        """
        if not self.is_running:
            return
        
        # Check if we need to advance to next point
        elapsed_ms = (time.time() - self._point_start_time) * 1000
        if elapsed_ms >= self.config.point_duration_ms:
            self._current_point_index += 1
            if self._current_point_index >= len(self._points):
                self.stop()
                return
            self._point_start_time = time.time()
        
        # Record gaze data for current point
        if gaze_x is not None and gaze_y is not None:
            current_point = self._points[self._current_point_index]
            current_point.gaze_samples_x.append(gaze_x)
            current_point.gaze_samples_y.append(gaze_y)
            current_point.timestamps.append(timestamp)
    
    def get_current_target(self) -> Tuple[int, int]:
        """Get current target position."""
        if not self.is_running or self._current_point_index >= len(self._points):
            return (self.center_x, self.center_y)
        
        point = self._points[self._current_point_index]
        return (point.target_x, point.target_y)
    
    def get_progress(self) -> Tuple[int, int]:
        """Get current progress (current point, total points)."""
        return (self._current_point_index + 1, len(self._points))


def generate_validation_report(result: ValidationResult) -> str:
    """Generate a text report from validation results."""
    report = []
    report.append("╔" + "═" * 58 + "╗")
    report.append("║" + " GAZE ACCURACY VALIDATION REPORT ".center(58) + "║")
    report.append("╚" + "═" * 58 + "╝")
    report.append("")
    report.append(f"  📋 Pattern: {result.config.pattern.value}")
    report.append(f"  📊 Points Tested: {result.valid_points}/{len(result.points)}")
    report.append("")
    report.append("─" * 60)
    report.append("🎯 ACCURACY METRICS")
    report.append("─" * 60)
    
    acc = result.accuracy_degrees
    if acc is not None:
        # Progress bar for accuracy (inverted - lower is better)
        bar_value = max(0, 100 - acc * 25)  # 0°=100, 4°=0
        filled = int(bar_value / 5)
        bar = "█" * filled + "░" * (20 - filled)
        
        if acc < 2.0:
            status = "✅ CLINICAL GRADE"
        elif acc < 3.0:
            status = "⚠️ BORDERLINE"
        else:
            status = "❌ NEEDS IMPROVEMENT"
        
        report.append(f"  Mean Accuracy: [{bar}] {acc:.2f}°")
        report.append(f"  Status: {status}")
        report.append(f"  (Clinical threshold: <2°)")
    else:
        report.append("  Accuracy: N/A (insufficient data)")
    
    report.append("")
    
    if result.accuracy_std_degrees:
        report.append(f"  Accuracy Std: {result.accuracy_std_degrees:.2f}°")
    
    if result.precision_degrees:
        report.append(f"  Precision: {result.precision_degrees:.2f}°")
        report.append(f"  (Within-point variability)")
    
    if result.worst_point_accuracy:
        report.append(f"  Worst Point: {result.worst_point_accuracy:.2f}°")
    
    report.append("")
    report.append("─" * 60)
    report.append("📍 PER-POINT BREAKDOWN")
    report.append("─" * 60)
    
    for i, point in enumerate(result.points):
        if point.mean_gaze_x is not None:
            error_px = np.sqrt(
                (point.mean_gaze_x - point.target_x)**2 +
                (point.mean_gaze_y - point.target_y)**2
            )
            error_deg = error_px / result._px_per_deg if result._px_per_deg > 0 else 0
            
            status = "✓" if error_deg < 2.0 else "✗"
            report.append(f"  Point {i+1}: {error_deg:.2f}° {status}  ({point.num_samples} samples)")
        else:
            report.append(f"  Point {i+1}: No data")
    
    report.append("")
    report.append("─" * 60)
    report.append("💡 INTERPRETATION")
    report.append("─" * 60)
    
    if result.meets_clinical_threshold:
        report.append("  ✅ Gaze accuracy meets clinical requirements (<2°)")
        report.append("  System is suitable for clinical eye movement assessment.")
    else:
        report.append("  ❌ Gaze accuracy does not meet clinical threshold (≥2°)")
        report.append("  Recommendations:")
        report.append("  • Re-run calibration with better lighting")
        report.append("  • Ensure stable head position")
        report.append("  • Check camera focus and positioning")
    
    report.append("")
    report.append("─" * 60)
    
    return "\n".join(report)
