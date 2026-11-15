"""
The camera thread must not fail silently.

A webcam that stops delivering frames used to spin on the grab call: the preview stayed
dead, nothing told the operator why, and the log filled with thousands of warnings. The
thread now reports the failure once, reopens the device, and reports the recovery.
"""

import sys
import threading
import time
from pathlib import Path

import numpy as np
import pytest

_src_dir = str(Path(__file__).parent.parent.parent / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from PyQt6.QtWidgets import QApplication

from widgets import camera_thread as camera_thread_module
from widgets.camera_thread import CameraThread
from eye_tracker import EyeData


class _FakeCapture:
    """Stand-in for cv2.VideoCapture with a scripted sequence of read outcomes."""

    def __init__(self, script):
        self.script = list(script)
        self.index = 0
        self.released = False

    def isOpened(self):
        return True

    def set(self, *args):
        return True

    def read(self):
        if self.index < len(self.script):
            outcome = self.script[self.index]
        else:
            outcome = self.script[-1] if self.script else False
        self.index += 1
        if outcome:
            return True, np.zeros((4, 4, 3), dtype=np.uint8)
        return False, None

    def release(self):
        self.released = True


class _StubTracker:
    def process_frame(self, frame):
        return EyeData(face_detected=False)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _run_until(thread, event, timeout=15.0):
    """Wait for a signal to arrive.

    The thread emits from its own thread, so the signal is delivered through the event loop
    of the thread that owns the camera thread object: the Qt events have to be pumped here.
    """
    app = QApplication.instance()
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if event.is_set():
            return True
        time.sleep(0.01)
    return False


class TestCameraFailure:
    def test_a_camera_that_never_delivers_is_reported(self, qapp, monkeypatch):
        """The operator has to be told, not left with a dead preview."""
        monkeypatch.setattr(camera_thread_module.cv2, "VideoCapture",
                            lambda *args, **kwargs: _FakeCapture([False]))
        monkeypatch.setattr(camera_thread_module.CameraThread, "MAX_CONSECUTIVE_FAILURES", 5)

        thread = CameraThread(_StubTracker())
        failed = threading.Event()
        messages = []
        thread.camera_failed.connect(messages.append)
        thread.camera_failed.connect(lambda *_: failed.set())

        thread.start()
        try:
            assert _run_until(thread, failed), "the camera failure was never reported"
        finally:
            thread.stop()

        assert messages
        assert "camera" in messages[0].lower()

    def test_a_camera_that_comes_back_is_reported(self, qapp, monkeypatch):
        """A device that recovers must clear the error, otherwise the app stays stale."""
        captures = []

        def factory(*args, **kwargs):
            # The first device never delivers; the reopened one works.
            script = [False] * 50 if not captures else [True] * 50
            capture = _FakeCapture(script)
            captures.append(capture)
            return capture

        monkeypatch.setattr(camera_thread_module.cv2, "VideoCapture", factory)
        monkeypatch.setattr(camera_thread_module.CameraThread, "MAX_CONSECUTIVE_FAILURES", 3)

        thread = CameraThread(_StubTracker())
        failed = threading.Event()
        recovered = threading.Event()
        thread.camera_failed.connect(lambda *_: failed.set())
        thread.camera_recovered.connect(lambda *_: recovered.set())

        thread.start()
        try:
            assert _run_until(thread, failed), "the camera failure was never reported"
            assert _run_until(thread, recovered), "the camera recovery was never reported"
        finally:
            thread.stop()

        assert len(captures) >= 2, "a dead stream must be reopened, not retried in place"
