"""
Camera selection: with more than one camera the operator is asked which to use.

The question is asked once - the answer is remembered, so the app does not nag on every
launch - and the operator can always change it from the panel. The capture is opened after
the probe, never during it: two handles on one camera make the running stream fail.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_src_dir = str(Path(__file__).parent.parent.parent / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from camera_devices import CameraDevice


class _FakeThread:
    def __init__(self, device_index=0):
        self.device_index = device_index
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


class _FakeSettings:
    def __init__(self):
        self.values = {}

    def value(self, key, default=None):
        return self.values.get(key, default)

    def setValue(self, key, value):
        self.values[key] = value


class _FakeWindow:
    """Just enough of MainWindow for the camera-selection logic."""

    def __init__(self, saved_index=None):
        self._camera_purpose = ""
        self._saved = saved_index
        self.asked = []
        self.camera_thread = _FakeThread(0)
        self.original_thread = self.camera_thread
        self.created_threads = []
        self.settings = _FakeSettings()
        self._capture_started = False

    # Methods the code under test calls.
    def _saved_camera_index(self):
        return self._saved

    def _resolve_startup_camera(self, cameras):
        """Exercise the real startup decision against the fake window."""
        import main_app
        return main_app.MainWindow._resolve_startup_camera(self, cameras)

    def _ask_which_camera(self, cameras):
        """Record the question; the operator cancels."""
        self.asked.append(list(cameras))
        return None

    def _create_camera_thread(self, device_index):
        thread = _FakeThread(device_index)
        self.created_threads.append(thread)
        return thread

    def _use_camera(self, device_index, start=False):
        """Exercise the real switching logic against the fake thread."""
        import main_app
        main_app.MainWindow._use_camera(self, device_index, start=start)

    def _camera_settings(self):
        return self.settings


@pytest.fixture(scope="module")
def main_app_module():
    """Import main_app once the real PyQt6 modules are restored by the conftest guard."""
    import main_app
    return main_app


TWO_CAMERAS = [
    CameraDevice(index=0, label="Camera 1 (index 0)"),
    CameraDevice(index=2, label="Camera 3 (index 2)"),
]


class TestStartupCameraChoice:
    def test_two_cameras_ask_the_operator(self, main_app_module):
        window = _FakeWindow()
        window._camera_purpose = "startup"

        main_app_module.MainWindow._on_cameras_found(window, TWO_CAMERAS)

        assert window.asked == [TWO_CAMERAS]

    def test_one_camera_is_used_without_asking(self, main_app_module):
        window = _FakeWindow()
        window._camera_purpose = "startup"

        main_app_module.MainWindow._on_cameras_found(window, TWO_CAMERAS[:1])

        assert window.asked == []
        assert window.camera_thread.device_index == 0
        assert window.camera_thread.started is True

    def test_no_camera_is_used_without_asking(self, main_app_module):
        window = _FakeWindow()
        window._camera_purpose = "startup"

        main_app_module.MainWindow._on_cameras_found(window, [])

        assert window.asked == []
        assert window.camera_thread.started is True

    def test_a_saved_choice_is_not_asked_again(self, main_app_module):
        window = _FakeWindow(saved_index=2)
        window._camera_purpose = "startup"

        main_app_module.MainWindow._on_cameras_found(window, TWO_CAMERAS)

        assert window.asked == []
        assert window.camera_thread.device_index == 2

    def test_a_saved_camera_that_is_gone_falls_back(self, main_app_module):
        """The remembered camera may be unplugged; the app must not stay blind."""
        window = _FakeWindow(saved_index=7)
        window._camera_purpose = "startup"

        main_app_module.MainWindow._on_cameras_found(window, TWO_CAMERAS)

        assert window.asked == []
        # The stale preference is replaced with a camera that exists.
        assert window.camera_thread.device_index == 0
        assert window.settings.values["camera_index"] == 0

    def test_manual_request_always_asks(self, main_app_module):
        """The panel button must open the chooser even when a choice was saved before."""
        window = _FakeWindow(saved_index=2)
        window._camera_purpose = "manual"

        main_app_module.MainWindow._on_cameras_found(window, TWO_CAMERAS)

        assert window.asked == [TWO_CAMERAS]


class TestSwitchingCamera:
    def test_switching_restarts_the_capture_on_the_new_camera(self, main_app_module):
        window = _FakeWindow()
        window._capture_started = True   # a capture is running on the old camera

        main_app_module.MainWindow._use_camera(window, 2, start=True)

        assert window.original_thread.stopped is True
        assert window.created_threads[-1].device_index == 2
        assert window.camera_thread.started is True
        assert window.camera_thread.device_index == 2

    def test_switching_before_the_capture_started_does_not_stop_anything(self, main_app_module):
        window = _FakeWindow()

        main_app_module.MainWindow._use_camera(window, 2, start=True)

        assert window.original_thread.stopped is False
        assert window.camera_thread.started is True

    def test_switching_remembers_the_choice(self, main_app_module):
        window = _FakeWindow()

        main_app_module.MainWindow._use_camera(window, 2, start=True)

        assert window.settings.values["camera_index"] == 2

    def test_switching_to_the_camera_in_use_does_not_restart(self, main_app_module):
        window = _FakeWindow()
        window.camera_thread.device_index = 0

        main_app_module.MainWindow._use_camera(window, 0, start=True)

        assert window.created_threads == []
        assert window.original_thread.stopped is False
