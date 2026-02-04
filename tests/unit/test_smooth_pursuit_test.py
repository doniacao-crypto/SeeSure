"""
Unit tests for the smooth_pursuit_test module.
Tests target position calculations and boundary compliance.
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from smooth_pursuit_test import (
    SmoothPursuitTest, TestConfig, TargetPattern,
    TestResult, TrackingFrame, generate_report
)


class TestTargetBounds:
    """Tests for target position boundary compliance (Issue #2)."""

    def test_horizontal_pattern_stays_within_bounds(self):
        """Test that horizontal pattern target never exceeds screen bounds."""
        width, height = 800, 600
        config = TestConfig(
            pattern=TargetPattern.HORIZONTAL,
            duration_seconds=5.0,
            speed=1.0,
            margin=0.1
        )
        test = SmoothPursuitTest(width, height, config)
        test.start()

        # Sample positions over the full test duration
        for i in range(100):
            # Simulate time progression
            test.start_time = test.start_time - (i * config.duration_seconds / 100)
            x, y = test.get_target_position()

            assert 0 <= x <= width, f"X position {x} out of bounds [0, {width}]"
            assert 0 <= y <= height, f"Y position {y} out of bounds [0, {height}]"

    def test_vertical_pattern_stays_within_bounds(self):
        """Test that vertical pattern target never exceeds screen bounds."""
        width, height = 800, 600
        config = TestConfig(
            pattern=TargetPattern.VERTICAL,
            duration_seconds=5.0,
            speed=1.0,
            margin=0.1
        )
        test = SmoothPursuitTest(width, height, config)
        test.start()

        for i in range(100):
            test.start_time = test.start_time - (i * config.duration_seconds / 100)
            x, y = test.get_target_position()

            assert 0 <= x <= width, f"X position {x} out of bounds [0, {width}]"
            assert 0 <= y <= height, f"Y position {y} out of bounds [0, {height}]"

    def test_circular_pattern_stays_within_bounds(self):
        """Test that circular pattern target never exceeds screen bounds."""
        width, height = 800, 600
        config = TestConfig(
            pattern=TargetPattern.CIRCULAR,
            duration_seconds=5.0,
            speed=1.0,
            margin=0.1,
            radius_ratio=0.3
        )
        test = SmoothPursuitTest(width, height, config)
        test.start()

        for i in range(100):
            test.start_time = test.start_time - (i * config.duration_seconds / 100)
            x, y = test.get_target_position()

            assert 0 <= x <= width, f"X position {x} out of bounds [0, {width}]"
            assert 0 <= y <= height, f"Y position {y} out of bounds [0, {height}]"

    def test_figure_eight_pattern_stays_within_bounds(self):
        """Test that figure-8 pattern target never exceeds screen bounds."""
        width, height = 800, 600
        config = TestConfig(
            pattern=TargetPattern.FIGURE_EIGHT,
            duration_seconds=5.0,
            speed=1.0,
            margin=0.1,
            radius_ratio=0.3
        )
        test = SmoothPursuitTest(width, height, config)
        test.start()

        for i in range(100):
            test.start_time = test.start_time - (i * config.duration_seconds / 100)
            x, y = test.get_target_position()

            assert 0 <= x <= width, f"X position {x} out of bounds [0, {width}]"
            assert 0 <= y <= height, f"Y position {y} out of bounds [0, {height}]"

    def test_random_points_stay_within_bounds(self):
        """Test that random points are generated within screen bounds."""
        width, height = 800, 600
        config = TestConfig(
            pattern=TargetPattern.RANDOM_POINTS,
            duration_seconds=5.0,
            margin=0.1,
            num_points=20
        )
        test = SmoothPursuitTest(width, height, config)
        test.start()

        # Check that all random points are within bounds
        for point in test._random_points:
            x, y = point
            assert 0 <= x <= width, f"Random point X {x} out of bounds [0, {width}]"
            assert 0 <= y <= height, f"Random point Y {y} out of bounds [0, {height}]"

    def test_target_respects_margin(self):
        """Test that target positions respect the configured margin."""
        width, height = 1000, 800
        margin = 0.15  # 15% margin
        config = TestConfig(
            pattern=TargetPattern.HORIZONTAL,
            duration_seconds=5.0,
            speed=1.0,
            margin=margin
        )
        test = SmoothPursuitTest(width, height, config)
        test.start()

        min_x = int(width * margin)
        max_x = int(width * (1 - margin))
        min_y = int(height * margin)
        max_y = int(height * (1 - margin))

        for i in range(100):
            test.start_time = test.start_time - (i * config.duration_seconds / 100)
            x, y = test.get_target_position()

            # For horizontal pattern, Y should be center, X should be within margin
            assert min_x <= x <= max_x, f"X {x} outside margin bounds [{min_x}, {max_x}]"

    def test_update_screen_dimensions(self):
        """Test that screen dimensions can be updated after initialization."""
        initial_width, initial_height = 1920, 1080
        config = TestConfig(pattern=TargetPattern.HORIZONTAL)
        test = SmoothPursuitTest(initial_width, initial_height, config)

        # Update to smaller dimensions (simulating widget resize)
        new_width, new_height = 800, 600
        test.update_screen_dimensions(new_width, new_height)

        assert test.screen_width == new_width
        assert test.screen_height == new_height

        # Start test and verify target stays within new bounds
        test.start()
        for i in range(50):
            test.start_time = test.start_time - (i * config.duration_seconds / 50)
            x, y = test.get_target_position()

            assert 0 <= x <= new_width, f"X {x} outside new bounds [0, {new_width}]"
            assert 0 <= y <= new_height, f"Y {y} outside new bounds [0, {new_height}]"


class TestTargetBoundsWithSmallDimensions:
    """Tests for target bounds with small/edge-case screen dimensions."""

    @pytest.mark.parametrize("width,height", [
        (640, 480),   # VGA
        (800, 600),   # SVGA
        (1024, 768),  # XGA
        (1280, 720),  # HD
        (1920, 1080), # Full HD
        (400, 300),   # Very small
    ])
    def test_all_patterns_within_bounds_various_sizes(self, width, height):
        """Test all patterns stay within bounds for various screen sizes."""
        patterns = [
            TargetPattern.HORIZONTAL,
            TargetPattern.VERTICAL,
            TargetPattern.CIRCULAR,
            TargetPattern.FIGURE_EIGHT,
        ]

        for pattern in patterns:
            config = TestConfig(
                pattern=pattern,
                duration_seconds=3.0,
                speed=1.0,
                margin=0.1,
                radius_ratio=0.25  # Conservative radius for small screens
            )
            test = SmoothPursuitTest(width, height, config)
            test.start()

            for i in range(50):
                test.start_time = test.start_time - (i * config.duration_seconds / 50)
                x, y = test.get_target_position()

                assert 0 <= x <= width, \
                    f"{pattern.value}: X {x} out of bounds for {width}x{height}"
                assert 0 <= y <= height, \
                    f"{pattern.value}: Y {y} out of bounds for {width}x{height}"

    def test_circular_pattern_radius_constrained(self):
        """Test that circular pattern radius doesn't exceed available space."""
        width, height = 600, 400  # Wide but short screen
        config = TestConfig(
            pattern=TargetPattern.CIRCULAR,
            duration_seconds=3.0,
            radius_ratio=0.4  # Large radius
        )
        test = SmoothPursuitTest(width, height, config)
        test.start()

        for i in range(100):
            test.start_time = test.start_time - (i * config.duration_seconds / 100)
            x, y = test.get_target_position()

            assert 0 <= x <= width, f"X {x} out of bounds"
            assert 0 <= y <= height, f"Y {y} out of bounds"


class TestTestConfig:
    """Tests for TestConfig defaults and validation."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TestConfig()
        assert config.pattern == TargetPattern.HORIZONTAL
        assert config.duration_seconds == 10.0
        assert config.speed == 0.5
        assert config.target_size == 20
        assert config.margin == 0.1

    def test_margin_bounds(self):
        """Test that margin affects usable area correctly."""
        config = TestConfig(margin=0.2)
        width, height = 1000, 800
        test = SmoothPursuitTest(width, height, config)

        # Expected usable area
        expected_margin_x = 200  # 20% of 1000
        expected_margin_y = 160  # 20% of 800

        test.start()
        positions = []
        for i in range(100):
            test.start_time = test.start_time - (i * config.duration_seconds / 100)
            x, y = test.get_target_position()
            positions.append((x, y))

        # All positions should be within margin
        for x, y in positions:
            assert x >= expected_margin_x - 1, f"X {x} below margin {expected_margin_x}"
            assert x <= width - expected_margin_x + 1, f"X {x} above margin"


class TestSmoothPursuitTestState:
    """Tests for SmoothPursuitTest state management."""

    def test_initial_state(self):
        """Test initial state before start."""
        test = SmoothPursuitTest(800, 600)
        assert not test.is_running
        assert test.start_time is None
        assert test.current_result is None

    def test_start_initializes_state(self):
        """Test that start() initializes state correctly."""
        test = SmoothPursuitTest(800, 600)
        result = test.start()

        assert result is True
        assert test.is_running
        assert test.start_time is not None
        assert test.current_result is not None

    def test_stop_finalizes_result(self):
        """Test that stop() finalizes and returns result."""
        test = SmoothPursuitTest(800, 600)
        test.start()
        result = test.stop()

        assert result is not None
        assert not test.is_running

    def test_elapsed_time(self):
        """Test elapsed time calculation."""
        test = SmoothPursuitTest(800, 600)
        assert test.get_elapsed_time() == 0.0

        test.start()
        import time
        time.sleep(0.1)
        elapsed = test.get_elapsed_time()

        assert elapsed >= 0.1

    def test_is_complete(self):
        """Test completion detection."""
        config = TestConfig(duration_seconds=0.1)  # Very short
        test = SmoothPursuitTest(800, 600, config)
        test.start()

        import time
        time.sleep(0.15)

        assert test.is_complete()


class TestTrackingFrame:
    """Tests for TrackingFrame data class."""

    def test_tracking_frame_creation(self):
        """Test TrackingFrame creation."""
        frame = TrackingFrame(
            timestamp=1.0,
            target_x=100,
            target_y=200,
            gaze_x=105,
            gaze_y=195,
            head_pitch=5.0,
            head_yaw=-3.0,
            face_detected=True
        )

        assert frame.timestamp == 1.0
        assert frame.target_x == 100
        assert frame.gaze_x == 105
        assert frame.face_detected is True


class TestTestResult:
    """Tests for TestResult and metrics computation."""

    def test_result_compute_metrics_empty(self):
        """Test compute_metrics with no frames."""
        result = TestResult(pattern=TargetPattern.HORIZONTAL, duration=5.0)
        result.compute_metrics(1000)  # Should not crash

        assert result.tracking_ratio == 0.0

    def test_result_compute_metrics_with_data(self):
        """Test compute_metrics with valid frames."""
        result = TestResult(pattern=TargetPattern.HORIZONTAL, duration=5.0)

        # Add some frames
        for i in range(10):
            frame = TrackingFrame(
                timestamp=i * 0.1,
                target_x=100 + i * 10,
                target_y=200,
                gaze_x=105 + i * 10,  # 5px offset
                gaze_y=205,
                head_pitch=0.0,
                head_yaw=0.0,
                face_detected=True
            )
            result.frames.append(frame)

        result.compute_metrics(1000)

        assert result.tracking_ratio == 1.0  # All frames valid
        assert result.avg_distance_px > 0


class TestGenerateReport:
    """Tests for report generation."""

    def test_generate_report_basic(self):
        """Test basic report generation."""
        result = TestResult(pattern=TargetPattern.HORIZONTAL, duration=5.0)
        result.tracking_ratio = 0.85
        result.accuracy_score = 75.0
        result.smooth_score = 80.0

        report = generate_report(result, include_clinical=False)

        assert "EYE MOVEMENT ASSESSMENT REPORT" in report
        assert "horizontal" in report.lower()
        assert "85" in report  # tracking ratio


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
