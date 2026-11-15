"""
Regression cover for the between-level notice in calibration.

The patient has to physically turn the head between calibration levels. Without a warning the
first samples of the new level are collected while the head is still turning, which pollutes
the head-pose coefficients the level exists to teach. The widget must therefore hold a
notice for a fixed number of seconds before each new level, and must not collect anything
while the notice is up.
"""

import sys
import time
from pathlib import Path

import pytest

_src_dir = str(Path(__file__).parent.parent.parent / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from constants import CALIBRATION_POSE_TRANSITION_SECONDS
from eye_tracker import EyeData
from widgets.calibration_widget import CalibrationWidget


class _StubEstimator:
    """Duck-typed stand-in for GazeEstimator: records the points it is told to finish."""

    def __init__(self):
        self.screen_width = 800
        self.screen_height = 600
        self.collecting = False
        self.finished_points = []
        self.sample_calls = 0

    def start_calibration(self):
        pass

    def start_collecting_samples(self):
        self.collecting = True

    def add_calibration_sample(self, eye_data, timestamp):
        self.sample_calls += 1
        return self.collecting

    def finish_collecting_samples(self, x, y):
        self.finished_points.append((x, y))
        self.collecting = False

    def finish_calibration(self):
        return True

    def get_calibration_quality(self):
        return {"quality": 0.0, "points": len(self.finished_points), "coverage": 0.0,
                "avg_error_px": 0.0, "cv_error_px": 0.0, "training_rows": 0,
                "head_pitch_spread_deg": 0.0, "head_yaw_spread_deg": 0.0,
                "head_pose_ok": False}


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def widget(qapp):
    """A calibration widget mid-run, with one sample per point to keep the test quick."""
    est = _StubEstimator()
    w = CalibrationWidget(est)
    w.resize(800, 600)
    w.samples_per_point = 1
    w._begin_calibration()
    yield w
    w.timer.stop()


def _advance(widget, points=1):
    """Advance the calibration by `points` points, with no dependency on the wall clock.

    Each point needs a timer tick (to start the settle period) and one settled frame.
    """
    eye = EyeData(face_detected=True)
    for _ in range(points):
        widget.process_eye_data(eye)
        widget._on_timer()
        widget._settling_start_time = time.time() - 1.0  # settle period already over
        widget.process_eye_data(eye)


class TestBetweenLevelNotice:
    def test_notice_only_appears_between_levels(self, widget):
        """Inside a level the patient keeps chasing dots; no notice, no countdown."""
        _advance(widget, 2)
        assert widget.current_pose_index == 0
        assert widget.current_point_index == 2
        assert widget._pose_transition is False
        assert widget.countdown == 0

    def test_notice_starts_the_next_level_with_three_seconds(self, widget):
        """Finishing a level must hold a notice before the next level collects anything."""
        _advance(widget, len(widget.calibration_points))
        assert widget.current_pose_index == 1
        assert widget.current_point_index == 0
        assert widget._pose_transition is True
        assert widget.countdown == CALIBRATION_POSE_TRANSITION_SECONDS
        assert CALIBRATION_POSE_TRANSITION_SECONDS == 3

    def test_nothing_is_collected_while_the_notice_is_up(self, widget):
        """The whole point of the notice: no samples are taken while the head is moving."""
        est = widget.gaze_estimator
        _advance(widget, len(widget.calibration_points))
        points_before = len(est.finished_points)
        calls_before = est.sample_calls

        eye = EyeData(face_detected=True)
        countdowns = []
        for _ in range(CALIBRATION_POSE_TRANSITION_SECONDS):
            countdowns.append(widget.countdown)
            widget.process_eye_data(eye)
            widget._on_timer()

        assert countdowns == [3, 2, 1]
        assert est.sample_calls == calls_before
        assert len(est.finished_points) == points_before
        assert widget._pose_transition is False
        assert widget._settling is True  # collection resumes right after the notice

    def test_notice_is_drawn(self, widget):
        """Rendering the notice must not raise (it draws the upcoming pose instruction)."""
        _advance(widget, len(widget.calibration_points))
        pixmap = widget.grab()
        assert not pixmap.isNull()
        assert pixmap.width() > 0 and pixmap.height() > 0
