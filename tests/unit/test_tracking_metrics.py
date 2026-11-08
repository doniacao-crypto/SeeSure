"""
Tests for how pursuit scores are computed and reported.

The tracking rate is the share of frames that produced a usable gaze estimate -- a data
validity measure. It used to hold a velocity-gain match, which reported the gaze estimate's
own damping as if the patient had failed to track. The gain match is now reported separately
as the speed match, and the clinical metrics (pursuit gain, RMS error in degrees) are computed
for every finished run instead of being left at zero.
"""

import math
import sys
import time
from pathlib import Path

import pytest

_src_dir = str(Path(__file__).parent.parent.parent / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from smooth_pursuit_test import (
    SmoothPursuitTest, TestConfig, TestResult, TrackingFrame, TargetPattern,
    generate_report,
)
from metrics import ScreenConfig


def _sweep(gain, count=90, dt=1 / 30.0, amplitude=800.0, period=3.0, center=960.0):
    """A target sweeping a sinusoid, with a gaze that follows it scaled by `gain`."""
    frames = []
    for i in range(count):
        t = i * dt
        offset = amplitude * math.sin(2 * math.pi * t / period)
        frames.append(TrackingFrame(
            timestamp=t,
            target_x=int(center + offset), target_y=500,
            gaze_x=int(center + gain * offset), gaze_y=500,
            head_pitch=0.0, head_yaw=0.0, face_detected=True,
        ))
    return frames


class TestTrackingRate:
    def test_tracking_rate_counts_frames_with_a_usable_estimate(self):
        """A run where 4 of 10 frames had no gaze estimate reports a 60% tracking rate."""
        result = TestResult(pattern=TargetPattern.HORIZONTAL, duration=1.0)
        for i in range(10):
            usable = i < 6
            result.frames.append(TrackingFrame(
                timestamp=i * (1 / 30.0),
                target_x=100 + i * 10, target_y=500,
                gaze_x=(100 + i * 10) if usable else None,
                gaze_y=500 if usable else None,
                head_pitch=0.0, head_yaw=0.0, face_detected=usable,
            ))

        result.compute_metrics(1000)

        assert result.tracking_ratio == pytest.approx(60.0)

    def test_tracking_rate_is_not_the_speed_match(self):
        """A damped estimate loses speed match, but the frames were still tracked."""
        result = TestResult(pattern=TargetPattern.HORIZONTAL, duration=1.0)
        result.frames = _sweep(gain=0.5)

        result.compute_metrics(1000)

        # The gaze covers half the target's travel: the speed match must show that, and the
        # tracking rate must not.
        assert result.speed_match_score < 100.0
        assert result.tracking_ratio == pytest.approx(100.0)

    def test_no_usable_estimate_reports_zero_tracking_rate(self):
        result = TestResult(pattern=TargetPattern.HORIZONTAL, duration=1.0)
        for i in range(5):
            result.frames.append(TrackingFrame(
                timestamp=i * (1 / 30.0), target_x=100, target_y=500,
                gaze_x=None, gaze_y=None, head_pitch=0.0, head_yaw=0.0,
                face_detected=False,
            ))

        result.compute_metrics(1000)

        assert result.tracking_ratio == 0.0


class TestClinicalMetrics:
    def test_a_finished_run_reports_clinical_metrics(self):
        """Every finished run must carry pursuit gain and an error in degrees.

        The clinical section of the report was dead because the screen geometry was never
        passed in, so these numbers stayed at zero on every run.
        """
        test = SmoothPursuitTest(1920, 1080, TestConfig(pattern=TargetPattern.HORIZONTAL))
        test.start()
        for i in range(60):
            test.record_frame(
                500 + i * 8, 500,        # gaze moves while the target sweeps
                0.0, 0.0, True,
                capture_time=time.time() + i / 30.0,
            )

        result = test.stop(pupil_distance_mm=63.0)

        assert result is not None
        assert result.clinical_metrics is not None
        assert result.pursuit_gain > 0.0
        assert result.accuracy_degrees > 0.0

    def test_pursuit_gain_follows_the_estimate(self):
        """A gaze that covers half the target's travel must report a gain near 0.5."""
        result = TestResult(pattern=TargetPattern.HORIZONTAL, duration=3.0)
        result.frames = _sweep(gain=0.5)
        screen = ScreenConfig(width_px=1920, height_px=1080, width_cm=53.1,
                              height_cm=29.9, viewing_distance_cm=60.0)

        result.compute_metrics(1000, screen_config=screen)

        assert result.pursuit_gain == pytest.approx(0.5, abs=0.15)
        assert result.accuracy_degrees > 5.0
        assert result.tracking_ratio == pytest.approx(100.0)

    def test_a_faithful_estimate_reports_a_gain_near_one(self):
        result = TestResult(pattern=TargetPattern.HORIZONTAL, duration=3.0)
        result.frames = _sweep(gain=1.0)
        screen = ScreenConfig(width_px=1920, height_px=1080, width_cm=53.1,
                              height_cm=29.9, viewing_distance_cm=60.0)

        result.compute_metrics(1000, screen_config=screen)

        assert result.pursuit_gain == pytest.approx(1.0, abs=0.15)
        assert result.accuracy_degrees < 2.0


class TestReportLabels:
    def test_report_separates_tracking_rate_from_the_direction_match(self):
        result = TestResult(pattern=TargetPattern.HORIZONTAL, duration=1.0)
        result.frames = _sweep(gain=0.5)
        result.compute_metrics(1000)

        report = generate_report(result)

        assert "Tracking Rate:" in report
        assert "Direction Match:" in report
        assert "Speed Match:" in report
