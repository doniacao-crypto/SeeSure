"""
Unit tests for eye_tracker module.
Tests EyeTracker class and EyeData dataclass.
"""

import pytest
import numpy as np
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from eye_tracker import EyeTracker, EyeData


class TestEyeData:
    """Tests for EyeData dataclass."""

    def test_default_values(self):
        """Test EyeData has correct default values."""
        data = EyeData()
        
        assert data.left_iris_center is None
        assert data.right_iris_center is None
        assert data.left_iris_pixel is None
        assert data.right_iris_pixel is None
        assert data.left_eye_corners is None
        assert data.right_eye_corners is None
        assert data.head_pitch == 0.0
        assert data.head_yaw == 0.0
        assert data.head_roll == 0.0
        assert data.face_detected == False
        assert data.left_ear == 0.0
        assert data.right_ear == 0.0
        assert data.is_blinking == False

    def test_with_values(self):
        """Test EyeData with custom values."""
        data = EyeData(
            left_iris_center=(0.5, 0.5),
            right_iris_center=(0.6, 0.5),
            face_detected=True,
            head_yaw=10.5
        )
        
        assert data.left_iris_center == (0.5, 0.5)
        assert data.right_iris_center == (0.6, 0.5)
        assert data.face_detected == True
        assert data.head_yaw == 10.5


class TestEyeTrackerConstants:
    """Tests for EyeTracker class constants."""

    def test_landmark_indices_exist(self):
        """Test that landmark index constants are defined."""
        assert hasattr(EyeTracker, 'LEFT_EYE_INDICES')
        assert hasattr(EyeTracker, 'RIGHT_EYE_INDICES')
        assert hasattr(EyeTracker, 'LEFT_IRIS_INDICES')
        assert hasattr(EyeTracker, 'RIGHT_IRIS_INDICES')
        assert hasattr(EyeTracker, 'POSE_LANDMARKS')

    def test_ear_threshold_reasonable(self):
        """Test EAR threshold is in reasonable range."""
        assert 0.1 <= EyeTracker.EAR_THRESHOLD <= 0.4

    def test_model_url_valid(self):
        """Test model URL points to Google storage."""
        assert 'storage.googleapis.com' in EyeTracker.MODEL_URL
        assert 'mediapipe' in EyeTracker.MODEL_URL

    def test_model_sha256_valid(self):
        """Test SHA256 hash is valid hex string."""
        sha256 = EyeTracker.MODEL_SHA256
        assert len(sha256) == 64
        assert all(c in '0123456789abcdef' for c in sha256)


class TestEyeTrackerModelVerification:
    """Tests for model integrity verification."""

    def test_verify_model_hash_with_valid_model(self):
        """Test hash verification succeeds with valid model file."""
        # This test requires the actual model file to be present
        model_path = Path(__file__).parent.parent.parent / "src" / "face_landmarker.task"
        
        if model_path.exists():
            tracker = EyeTracker.__new__(EyeTracker)
            tracker.MODEL_PATH = str(model_path)
            tracker.MODEL_SHA256 = EyeTracker.MODEL_SHA256
            
            assert tracker._verify_model_hash() == True


class TestEyeTrackerEARCalculation:
    """Tests for Eye Aspect Ratio calculation."""

    def test_set_ear_threshold_valid_range(self):
        """Test EAR threshold setter clamps to valid range."""
        # Create mock tracker without full initialization
        tracker = EyeTracker.__new__(EyeTracker)
        tracker._ear_threshold = EyeTracker.EAR_THRESHOLD
        
        # Test clamping to max
        tracker.set_ear_threshold(0.5)
        assert tracker._ear_threshold == 0.4
        
        # Test clamping to min
        tracker.set_ear_threshold(0.05)
        assert tracker._ear_threshold == 0.1
        
        # Test valid value
        tracker.set_ear_threshold(0.25)
        assert tracker._ear_threshold == 0.25


class TestEyeTrackerBlinkDetection:
    """Tests for blink detection logic."""

    def test_detect_blink_below_threshold(self):
        """Test blink detected when EAR below threshold."""
        tracker = EyeTracker.__new__(EyeTracker)
        tracker._blink_counter = 0
        tracker._ear_threshold = 0.21
        tracker.EAR_CONSEC_FRAMES = 2
        
        # First frame below threshold
        result1 = tracker._detect_blink(0.15, 0.15)
        assert result1 == False  # Not yet, need consecutive frames
        assert tracker._blink_counter == 1
        
        # Second frame below threshold
        result2 = tracker._detect_blink(0.15, 0.15)
        assert result2 == True  # Now detected
        assert tracker._blink_counter == 2

    def test_detect_blink_resets_on_open(self):
        """Test blink counter resets when eyes open."""
        tracker = EyeTracker.__new__(EyeTracker)
        tracker._blink_counter = 5
        tracker._ear_threshold = 0.21
        tracker.EAR_CONSEC_FRAMES = 2
        
        # EAR above threshold (eyes open)
        result = tracker._detect_blink(0.30, 0.30)
        assert result == False
        assert tracker._blink_counter == 0


class TestEyeTrackerProcessing:
    """Tests for frame processing (requires mocking MediaPipe)."""

    def test_process_frame_no_face(self):
        """Test processing returns empty data when no face detected."""
        # This would require mocking MediaPipe
        # For now, test with a black frame that won't have faces
        pass  # Placeholder for integration test


class TestEyeTrackerHelperMethods:
    """Tests for helper geometry methods."""

    def test_iris_position_in_eye_no_corners(self):
        """Test iris position calculation handles missing corners."""
        tracker = EyeTracker.__new__(EyeTracker)
        
        result = tracker._calculate_iris_position_in_eye(
            (100, 100),  # iris center
            [],  # no corners
            640, 480
        )
        
        assert result == (0.5, 0.5)  # Default center

    def test_iris_position_in_eye_valid_corners(self):
        """Test iris position calculation with valid corners."""
        tracker = EyeTracker.__new__(EyeTracker)
        
        # Eye corners at x=50 and x=150, iris at center
        result = tracker._calculate_iris_position_in_eye(
            (100, 100),  # iris center - exactly at eye center
            [(50, 100), (150, 100)],  # eye corners
            640, 480
        )
        
        # Iris at eye center should give ~0.5
        x, y = result
        assert 0.3 < x < 0.7  # Should be near center


class TestEyeTrackerVideoMode:
    """Tests for VIDEO mode functionality."""

    def test_video_mode_default_true(self):
        """Test VIDEO mode is enabled by default."""
        # Would need to mock MediaPipe initialization
        pass  # Placeholder

    def test_image_mode_option(self):
        """Test IMAGE mode can be explicitly selected."""
        # Would need to mock MediaPipe initialization
        pass  # Placeholder
