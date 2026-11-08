"""
Calibration must not throw a modal at the operator when it succeeds.

The error figures belong in the report; the one case that still interrupts is a calibration
in which the head barely moved, because that calibration is worthless and has to be redone.
"""

import sys
from pathlib import Path

import pytest

_src_dir = str(Path(__file__).parent.parent.parent / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from PyQt6.QtWidgets import QMessageBox

from widgets.calibration_widget import CalibrationWidget


class _StubEstimator:
    def __init__(self, head_pose_ok=True):
        self.head_pose_ok = head_pose_ok

    def start_calibration(self):
        pass

    def start_collecting_samples(self):
        pass

    def add_calibration_sample(self, eye_data, timestamp):
        return False

    def finish_collecting_samples(self, x, y):
        pass

    def finish_calibration(self):
        return True

    def get_calibration_quality(self):
        return {"quality": 0.8, "points": 9, "coverage": 0.9, "avg_error_px": 3.0,
                "cv_error_px": 7.5, "training_rows": 180, "head_pitch_spread_deg": 4.0,
                "head_yaw_spread_deg": 6.0, "head_pose_ok": self.head_pose_ok}


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def popups(monkeypatch):
    """Record the popups raised instead of blocking on them."""
    recorded = []
    monkeypatch.setattr(QMessageBox, "information",
                        lambda *args, **kwargs: recorded.append("information"))
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *args, **kwargs: recorded.append("warning"))
    return recorded


class TestCalibrationCompletion:
    def test_successful_calibration_raises_no_popup(self, qapp, popups):
        widget = CalibrationWidget(_StubEstimator(head_pose_ok=True))

        widget._finish_calibration()

        assert popups == []

    def test_calibration_without_head_movement_still_warns(self, qapp, popups):
        widget = CalibrationWidget(_StubEstimator(head_pose_ok=False))

        widget._finish_calibration()

        assert popups == ["warning"]
