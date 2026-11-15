"""
Camera discovery must find the cameras that actually work.

A machine can expose several cameras - a laptop camera, an external webcam, a capture card -
and index 0 is not always the one facing the patient. Probing an index that cannot deliver
frames must not put it in front of the operator.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

_src_dir = str(Path(__file__).parent.parent.parent / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from camera_devices import CameraDevice, enumerate_cameras
import camera_devices


class _FakeCapture:
    """Stand-in for cv2.VideoCapture."""

    def __init__(self, index, delivers):
        self.index = index
        self.delivers = delivers
        self.released = False

    def isOpened(self):
        return True

    def read(self):
        if self.delivers:
            return True, np.zeros((4, 4, 3), dtype=np.uint8)
        return False, None

    def release(self):
        self.released = True


@pytest.fixture
def fake_cameras(monkeypatch):
    """Install a fake VideoCapture and report what was opened."""
    opened = []

    def factory(index, *args, **kwargs):
        # Only indices 0 and 2 deliver frames.
        capture = _FakeCapture(index, delivers=index in (0, 2))
        opened.append(capture)
        return capture

    monkeypatch.setattr(camera_devices.cv2, "VideoCapture", factory)
    return opened


class TestEnumerateCameras:
    def test_only_cameras_that_deliver_frames_are_listed(self, fake_cameras):
        devices = enumerate_cameras(max_devices=4)

        assert [d.index for d in devices] == [0, 2]

    def test_labels_name_the_camera_and_the_index(self, fake_cameras):
        devices = enumerate_cameras(max_devices=4)

        assert devices[0].label == "Camera 1 (index 0)"
        assert devices[1].label == "Camera 3 (index 2)"

    def test_every_probe_is_released(self, fake_cameras):
        enumerate_cameras(max_devices=4)

        assert fake_cameras
        assert all(capture.released for capture in fake_cameras), \
            "a probed camera left open would block the next application"

    def test_no_cameras_returns_an_empty_list(self, monkeypatch):
        class _Dead:
            def isOpened(self):
                return False

            def read(self):
                return False, None

            def release(self):
                pass

        monkeypatch.setattr(camera_devices.cv2, "VideoCapture", lambda *a, **k: _Dead())

        assert enumerate_cameras(max_devices=2) == []

    def test_camera_devices_are_immutable(self):
        device = CameraDevice(index=1, label="Camera 2 (index 1)")

        with pytest.raises(Exception):
            device.index = 2
