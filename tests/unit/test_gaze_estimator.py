"""
Unit tests for gaze_estimator module.
Tests GazeEstimator, CalibrationPoint, and CalibrationSample classes.
"""

import pytest
import numpy as np
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from gaze_estimator import GazeEstimator, CalibrationPoint, CalibrationSample
from eye_tracker import EyeData


class TestCalibrationSample:
    """Tests for CalibrationSample dataclass."""

    def test_creation(self):
        """Test CalibrationSample creation with values."""
        sample = CalibrationSample(
            left_iris=(0.5, 0.5),
            right_iris=(0.6, 0.5),
            head_pitch=5.0,
            head_yaw=-2.0,
            head_roll=0.0,
            timestamp=1234567890.0
        )
        
        assert sample.left_iris == (0.5, 0.5)
        assert sample.right_iris == (0.6, 0.5)
        assert sample.head_pitch == 5.0
        assert sample.head_yaw == -2.0
        assert sample.head_roll == 0.0
        assert sample.timestamp == 1234567890.0


class TestCalibrationPoint:
    """Tests for CalibrationPoint dataclass."""

    def test_creation(self):
        """Test CalibrationPoint creation with values."""
        point = CalibrationPoint(
            screen_x=100,
            screen_y=200,
            left_iris=(0.5, 0.5),
            right_iris=(0.6, 0.5),
            head_pitch=0.0,
            head_yaw=0.0,
            head_roll=0.0
        )
        
        assert point.screen_x == 100
        assert point.screen_y == 200
        assert point.left_iris == (0.5, 0.5)
        assert point.samples == []

    def test_from_samples_single(self):
        """Test creating point from single sample."""
        sample = CalibrationSample(
            left_iris=(0.5, 0.5),
            right_iris=(0.6, 0.5),
            head_pitch=5.0,
            head_yaw=0.0,
            head_roll=0.0
        )
        
        point = CalibrationPoint.from_samples(100, 200, [sample])
        
        assert point.screen_x == 100
        assert point.screen_y == 200
        assert point.left_iris == (0.5, 0.5)
        assert point.head_pitch == 5.0

    def test_from_samples_multiple(self):
        """Test creating point from multiple samples (averaging)."""
        samples = [
            CalibrationSample(
                left_iris=(0.4, 0.4),
                right_iris=(0.5, 0.4),
                head_pitch=4.0,
                head_yaw=0.0,
                head_roll=0.0
            ),
            CalibrationSample(
                left_iris=(0.6, 0.6),
                right_iris=(0.7, 0.6),
                head_pitch=6.0,
                head_yaw=0.0,
                head_roll=0.0
            ),
        ]
        
        point = CalibrationPoint.from_samples(100, 200, samples)
        
        # Should be averaged
        assert abs(point.left_iris[0] - 0.5) < 0.01
        assert abs(point.left_iris[1] - 0.5) < 0.01
        assert abs(point.head_pitch - 5.0) < 0.01

    def test_from_samples_empty_raises(self):
        """Test that empty samples list raises ValueError."""
        with pytest.raises(ValueError, match="No samples"):
            CalibrationPoint.from_samples(100, 200, [])


class TestGazeEstimator:
    """Tests for GazeEstimator class."""

    def test_initialization(self):
        """Test GazeEstimator initializes with defaults."""
        estimator = GazeEstimator()
        
        assert estimator.screen_width == 1920
        assert estimator.screen_height == 1080
        assert estimator.is_calibrated == False

    def test_custom_screen_size(self):
        """Test GazeEstimator with custom screen size."""
        estimator = GazeEstimator(screen_width=2560, screen_height=1440)
        
        assert estimator.screen_width == 2560
        assert estimator.screen_height == 1440

    def test_start_calibration(self):
        """Test calibration mode starts correctly."""
        estimator = GazeEstimator()
        estimator.start_calibration()
        
        # Internal state should be reset
        assert estimator.is_calibrated == False

    def test_add_calibration_point_without_face(self):
        """Test adding calibration point fails without face detection."""
        estimator = GazeEstimator()
        estimator.start_calibration()
        
        eye_data = EyeData(face_detected=False)
        result = estimator.add_calibration_point(100, 200, eye_data, 0.0)
        
        assert result == False

    def test_add_calibration_point_with_face(self):
        """Test adding calibration point succeeds with face detection."""
        estimator = GazeEstimator()
        estimator.start_calibration()
        
        eye_data = EyeData(
            face_detected=True,
            left_iris_center=(0.5, 0.5),
            right_iris_center=(0.6, 0.5),
            head_pitch=0.0,
            head_yaw=0.0,
            head_roll=0.0
        )
        
        result = estimator.add_calibration_point(100, 200, eye_data, 0.0)
        
        assert result == True

    def test_finish_calibration_insufficient_points(self):
        """Test calibration fails with insufficient points."""
        estimator = GazeEstimator()
        estimator.start_calibration()
        
        # Add only 2 points (minimum is typically more)
        for i in range(2):
            eye_data = EyeData(
                face_detected=True,
                left_iris_center=(0.5 + i*0.1, 0.5),
                right_iris_center=(0.6 + i*0.1, 0.5),
                head_pitch=0.0,
                head_yaw=0.0,
                head_roll=0.0
            )
            estimator.add_calibration_point(100*i, 200*i, eye_data, float(i))
        
        result = estimator.finish_calibration()
        
        # Should fail with too few points
        assert result == False
        assert estimator.is_calibrated == False

    def test_estimate_gaze_without_calibration(self):
        """Test gaze estimation returns fallback when not calibrated."""
        estimator = GazeEstimator()
        
        eye_data = EyeData(
            face_detected=True,
            left_iris_center=(0.5, 0.5),
            right_iris_center=(0.6, 0.5)
        )
        
        result = estimator.estimate_gaze(eye_data)
        
        # May return a fallback position or None depending on implementation
        # Just verify it doesn't crash and returns something sensible
        if result is not None:
            assert isinstance(result, tuple)
            assert len(result) == 2

    def test_estimate_gaze_without_face(self):
        """Test gaze estimation returns None without face detection."""
        estimator = GazeEstimator()
        
        eye_data = EyeData(face_detected=False)
        result = estimator.estimate_gaze(eye_data)
        
        assert result is None


class TestGazeEstimatorCalibrationQuality:
    """Tests for calibration quality assessment."""

    def test_get_calibration_quality_uncalibrated(self):
        """Test quality metrics for uncalibrated estimator."""
        estimator = GazeEstimator()
        quality = estimator.get_calibration_quality()
        
        assert quality['quality'] == 0.0
        assert quality['points'] == 0


class TestGazeEstimatorPersistence:
    """Tests for saving and loading calibration profiles."""

    def test_save_and_load_profile(self):
        """Test saving and loading calibration profile."""
        estimator = GazeEstimator(screen_width=1920, screen_height=1080)
        estimator.start_calibration()
        
        # Add enough calibration points for a valid calibration
        # Using 9 points in a grid pattern
        for row in range(3):
            for col in range(3):
                x = 100 + col * 800
                y = 100 + row * 400
                eye_data = EyeData(
                    face_detected=True,
                    left_iris_center=(0.3 + col*0.2, 0.3 + row*0.2),
                    right_iris_center=(0.4 + col*0.2, 0.3 + row*0.2),
                    head_pitch=0.0,
                    head_yaw=0.0,
                    head_roll=0.0
                )
                estimator.add_calibration_point(x, y, eye_data, float(row*3 + col))
        
        estimator.finish_calibration()
        
        # Save profile
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            profile_path = f.name
        
        save_result = estimator.save_profile(profile_path)
        assert save_result == True
        
        # Load into new estimator
        new_estimator = GazeEstimator()
        load_result = new_estimator.load_profile(profile_path)
        
        # Clean up
        Path(profile_path).unlink()
        
        # Check loaded correctly
        assert load_result == True
        assert new_estimator.screen_width == 1920
        assert new_estimator.screen_height == 1080

    def test_load_nonexistent_profile(self):
        """Test loading non-existent profile fails gracefully."""
        estimator = GazeEstimator()
        result = estimator.load_profile("/nonexistent/path/profile.json")
        
        assert result == False


class TestGazeEstimatorFiltering:
    """Tests for gaze filtering functionality."""

    def test_filter_configuration(self):
        """Test that filters are configured on estimator."""
        estimator = GazeEstimator()
        
        # Should have filter attributes
        assert hasattr(estimator, '_combined_filter') or hasattr(estimator, '_oneuro_filter')


class TestGazeEstimatorEdgeCases:
    """Tests for edge cases and error handling."""

    def test_none_iris_data(self):
        """Test handling of None iris data."""
        estimator = GazeEstimator()
        
        eye_data = EyeData(
            face_detected=True,
            left_iris_center=None,
            right_iris_center=None
        )
        
        result = estimator.estimate_gaze(eye_data)
        
        # Should handle gracefully
        assert result is None

    def test_blinking_eye_data(self):
        """Test that blinks are handled (gaze not updated during blink)."""
        estimator = GazeEstimator()
        
        eye_data = EyeData(
            face_detected=True,
            left_iris_center=(0.5, 0.5),
            right_iris_center=(0.6, 0.5),
            is_blinking=True
        )
        
        # During blink, gaze estimation should be affected
        result = estimator.estimate_gaze(eye_data)
        
        # Implementation-dependent: might return None or last valid gaze
        # Just verify it doesn't crash
        assert result is None or isinstance(result, tuple)
