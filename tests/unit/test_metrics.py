"""
Unit tests for the metrics module.
Tests visual angle conversion, pursuit gain, saccade detection, and BCEA calculation.
"""

import pytest
import numpy as np
import math
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from metrics import ScreenConfig, MetricsCalculator, PursuitMetrics, SaccadeEvent


class TestScreenConfig:
    """Tests for ScreenConfig and visual angle conversion."""

    def test_default_config_creation(self):
        """Test default configuration creation."""
        config = ScreenConfig.default_config()
        assert config.width_px == 1920
        assert config.height_px == 1080
        assert config.viewing_distance_cm == 60.0

    def test_pixels_per_cm_calculation(self):
        """Test pixels per centimeter calculation."""
        config = ScreenConfig(
            width_px=1920,
            height_px=1080,
            width_cm=53.1,
            height_cm=29.9,
            viewing_distance_cm=60.0
        )
        expected_ppcm = 1920 / 53.1
        assert abs(config.pixels_per_cm - expected_ppcm) < 0.01

    def test_pixels_to_degrees_at_center(self):
        """Test pixel to degree conversion accuracy."""
        config = ScreenConfig.default_config()

        # At 60cm viewing distance:
        # 1 degree ≈ 2 * 60 * tan(0.5°) ≈ 1.047 cm
        # With ~36.2 px/cm, 1 degree ≈ 37.9 pixels

        # Test 100 pixels conversion
        degrees = config.pixels_to_degrees(100)

        # Should be approximately 2.64 degrees
        # (100 / 37.9 ≈ 2.64)
        assert 2.0 < degrees < 3.5, f"Expected ~2.64 degrees, got {degrees}"

    def test_degrees_to_pixels_inverse(self):
        """Test that degrees_to_pixels is inverse of pixels_to_degrees."""
        config = ScreenConfig.default_config()

        original_pixels = 150.0
        degrees = config.pixels_to_degrees(original_pixels)
        recovered_pixels = config.degrees_to_pixels(degrees)

        assert abs(original_pixels - recovered_pixels) < 0.1, \
            f"Inverse failed: {original_pixels} -> {degrees} -> {recovered_pixels}"

    def test_visual_angle_known_value(self):
        """Test visual angle calculation against known value."""
        # At 57.3 cm distance, 1 cm subtends exactly 1 degree
        config = ScreenConfig(
            width_px=1000,
            height_px=1000,
            width_cm=10.0,
            height_cm=10.0,
            viewing_distance_cm=57.3  # 1 radian in cm
        )

        # 100 pixels = 1 cm, should be ~1 degree
        degrees = config.pixels_to_degrees(100)
        assert 0.9 < degrees < 1.1, f"Expected ~1 degree, got {degrees}"


class TestPursuitGain:
    """Tests for pursuit gain calculation."""

    def test_perfect_pursuit_gain_one(self):
        """Test that identical target and gaze velocities give gain of 1.0."""
        config = ScreenConfig.default_config()
        calc = MetricsCalculator(config)

        # Create synthetic data where gaze exactly follows target
        timestamps = np.linspace(0, 1, 31)  # 30 FPS for 1 second
        # Sinusoidal horizontal movement
        target_x = 500 * np.sin(2 * np.pi * timestamps) + 960
        target_y = np.full_like(target_x, 540)
        gaze_x = target_x.copy()
        gaze_y = target_y.copy()

        target_positions = np.column_stack([target_x, target_y])
        gaze_positions = np.column_stack([gaze_x, gaze_y])

        gain = calc.calculate_pursuit_gain(target_positions, gaze_positions, timestamps)

        assert 0.95 < gain < 1.05, f"Expected gain ~1.0, got {gain}"

    def test_pursuit_gain_half(self):
        """Test pursuit gain of 0.5 when gaze moves at half target speed."""
        config = ScreenConfig.default_config()
        calc = MetricsCalculator(config)

        timestamps = np.linspace(0, 1, 31)
        target_x = 500 * np.sin(2 * np.pi * timestamps) + 960
        target_y = np.full_like(target_x, 540)
        # Gaze moves at half the amplitude (half velocity)
        gaze_x = 250 * np.sin(2 * np.pi * timestamps) + 960
        gaze_y = target_y.copy()

        target_positions = np.column_stack([target_x, target_y])
        gaze_positions = np.column_stack([gaze_x, gaze_y])

        gain = calc.calculate_pursuit_gain(target_positions, gaze_positions, timestamps)

        assert 0.45 < gain < 0.55, f"Expected gain ~0.5, got {gain}"

    def test_pursuit_gain_excludes_saccades(self):
        """Test that high-velocity saccadic movements are excluded from gain calculation."""
        config = ScreenConfig.default_config()
        calc = MetricsCalculator(config)

        timestamps = np.linspace(0, 2, 61)  # 2 seconds at 30 FPS

        # Smooth pursuit for most of the time
        target_x = 300 * np.sin(2 * np.pi * 0.5 * timestamps) + 960
        gaze_x = target_x.copy()

        # Inject a saccade at frame 30 (big jump)
        gaze_x[30] = gaze_x[29] + 200  # Large jump
        gaze_x[31:] = target_x[31:]  # Resume tracking

        target_y = np.full_like(target_x, 540)
        gaze_y = target_y.copy()

        target_positions = np.column_stack([target_x, target_y])
        gaze_positions = np.column_stack([gaze_x, gaze_y])

        gain = calc.calculate_pursuit_gain(target_positions, gaze_positions, timestamps)

        # Despite the saccade, gain should still be close to 1.0
        # because saccades are excluded
        assert 0.8 < gain < 1.2, f"Expected gain ~1.0 with saccade excluded, got {gain}"


class TestSaccadeDetection:
    """Tests for saccade detection algorithm."""

    def test_detect_single_saccade(self):
        """Test detection of a single saccade."""
        config = ScreenConfig.default_config()
        calc = MetricsCalculator(config)

        # Create data with one clear saccade
        timestamps = np.linspace(0, 1, 101)  # 100 FPS for 1 second
        gaze_x = np.full(101, 500.0)
        gaze_y = np.full(101, 500.0)

        # Insert saccade at frames 50-52 (20ms duration)
        gaze_x[50] = 500
        gaze_x[51] = 600
        gaze_x[52] = 700
        gaze_x[53:] = 700

        gaze_positions = np.column_stack([gaze_x, gaze_y])

        saccades = calc.detect_saccades(gaze_positions, timestamps)

        assert len(saccades) == 1, f"Expected 1 saccade, detected {len(saccades)}"
        assert saccades[0].amplitude_deg > 0

    def test_no_saccade_in_smooth_movement(self):
        """Test that smooth movement doesn't trigger saccade detection."""
        config = ScreenConfig.default_config()
        calc = MetricsCalculator(config)

        # Slow, smooth movement
        timestamps = np.linspace(0, 2, 61)  # 30 FPS for 2 seconds
        gaze_x = np.linspace(400, 600, 61)  # Slow drift
        gaze_y = np.full(61, 500.0)

        gaze_positions = np.column_stack([gaze_x, gaze_y])

        saccades = calc.detect_saccades(gaze_positions, timestamps)

        assert len(saccades) == 0, f"Expected 0 saccades in smooth movement, got {len(saccades)}"

    def test_saccade_metrics_accuracy(self):
        """Test that saccade metrics are calculated correctly."""
        config = ScreenConfig.default_config()
        calc = MetricsCalculator(config)

        timestamps = np.linspace(0, 0.5, 51)  # 100 FPS for 0.5 seconds
        gaze_x = np.full(51, 500.0)
        gaze_y = np.full(51, 500.0)

        # Insert a known saccade: 200px jump over 30ms (3 frames at 100Hz)
        gaze_x[20] = 500
        gaze_x[21] = 567
        gaze_x[22] = 633
        gaze_x[23] = 700
        gaze_x[24:] = 700

        gaze_positions = np.column_stack([gaze_x, gaze_y])

        saccades = calc.detect_saccades(gaze_positions, timestamps)

        if len(saccades) > 0:
            saccade = saccades[0]
            # Check duration is roughly 30ms
            assert 20 < saccade.duration_ms < 50, f"Duration {saccade.duration_ms}ms unexpected"


class TestBCEA:
    """Tests for Bivariate Contour Ellipse Area calculation."""

    def test_bcea_known_dispersion(self):
        """Test BCEA calculation with known dispersion."""
        config = ScreenConfig.default_config()
        calc = MetricsCalculator(config)

        # Generate gaze data with known standard deviation
        np.random.seed(42)
        n_samples = 1000

        # Create circular dispersion (σH = σV, ρ = 0)
        gaze_x = np.random.normal(500, 20, n_samples)  # σ = 20 pixels
        gaze_y = np.random.normal(500, 20, n_samples)

        gaze_positions = np.column_stack([gaze_x, gaze_y])

        bcea = calc.calculate_bcea(gaze_positions, probability=0.68)

        # BCEA should be positive
        assert bcea > 0, f"BCEA should be positive, got {bcea}"

    def test_bcea_increases_with_dispersion(self):
        """Test that BCEA increases with larger dispersion."""
        config = ScreenConfig.default_config()
        calc = MetricsCalculator(config)

        np.random.seed(42)
        n_samples = 1000

        # Small dispersion
        gaze_small = np.column_stack([
            np.random.normal(500, 10, n_samples),
            np.random.normal(500, 10, n_samples)
        ])

        # Large dispersion
        gaze_large = np.column_stack([
            np.random.normal(500, 40, n_samples),
            np.random.normal(500, 40, n_samples)
        ])

        bcea_small = calc.calculate_bcea(gaze_small)
        bcea_large = calc.calculate_bcea(gaze_large)

        assert bcea_large > bcea_small, \
            f"Larger dispersion should give larger BCEA: {bcea_small} vs {bcea_large}"


class TestPursuitMetrics:
    """Tests for comprehensive pursuit metrics calculation."""

    def test_pursuit_metrics_dataclass(self):
        """Test PursuitMetrics dataclass creation."""
        metrics = PursuitMetrics(
            gain=0.9,
            accuracy_degrees=1.5,
            smoothness=0.85,
            tracking_ratio=0.95,
            catch_up_saccade_count=3,
            phase_lag_ms=50.0
        )

        assert metrics.gain == 0.9
        assert metrics.accuracy_degrees == 1.5
        assert metrics.catch_up_saccade_count == 3

    def test_calculate_pursuit_metrics_integration(self):
        """Integration test for full pursuit metrics calculation."""
        config = ScreenConfig.default_config()
        calc = MetricsCalculator(config)

        # Create realistic pursuit data
        timestamps = np.linspace(0, 5, 151)  # 5 seconds at 30 FPS
        target_x = 400 * np.sin(2 * np.pi * 0.2 * timestamps) + 960
        target_y = np.full_like(target_x, 540)

        # Gaze follows with slight noise but same velocity profile
        np.random.seed(42)
        gaze_x = 400 * np.sin(2 * np.pi * 0.2 * timestamps) + 960 + np.random.normal(0, 5, 151)
        gaze_y = target_y + np.random.normal(0, 5, 151)

        target_positions = np.column_stack([target_x, target_y])
        gaze_positions = np.column_stack([gaze_x, gaze_y])

        metrics = calc.calculate_pursuit_metrics(target_positions, gaze_positions, timestamps)

        assert isinstance(metrics, PursuitMetrics)
        assert 0.7 < metrics.gain < 1.3, f"Gain {metrics.gain} out of expected range"
        assert metrics.accuracy_degrees > 0
        assert 0 <= metrics.smoothness <= 1
        assert 0 <= metrics.tracking_ratio <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
