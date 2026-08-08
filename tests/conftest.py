"""
Shared test fixtures for the EyeExam test suite.
Provides sys.path configuration and common temporary directory fixtures.
"""

import sys
from pathlib import Path

import pytest

# Add src/ to sys.path so test files can import source modules directly
# without each file needing its own sys.path manipulation.
_src_dir = str(Path(__file__).parent.parent / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)


@pytest.fixture
def tmp_data_dir(tmp_path):
    """
    Provide a temporary directory for tests that need to write data files.
    The directory is automatically cleaned up after the test completes.

    Returns:
        pathlib.Path: A unique temporary directory path.
    """
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir


# --- Module-pollution guard ------------------------------------------------
# test_main_app.py mocks heavy deps (PyQt6/cv2/gaze_estimator/...) at IMPORT time
# (module top-level), which pytest runs during collection — BEFORE any test body.
# Its MagicMock for gaze_estimator leaks into sibling test files (collected
# alphabetically after it), so test_gaze_estimator's adaptive-filter tests saw a
# MagicMock instead of the real module and failed. This session fixture restores
# the real modules before the first test executes. main_app's own tests still get
# their mocks (they re-import inside their module-scoped fixture).
import importlib
import sys as _sys
from unittest.mock import MagicMock

_MOCKED_BY_MAIN_APP = ["PyQt6", "PyQt6.QtWidgets", "PyQt6.QtCore", "PyQt6.QtGui",
                       "cv2", "eye_tracker", "gaze_estimator", "visualization", "widgets"]


def pytest_collection_modifyitems():
    """Restore real modules after collection, before tests run.

    test_main_app mocks heavy deps at import (collection) time. Its MagicMock for
    gaze_estimator leaks into sibling tests collected after it; restoring here
    (post-collection, pre-execution) gives every test the real modules. main_app's
    own tests are unaffected — they import through their module-scoped fixture.
    """
    for name in _MOCKED_BY_MAIN_APP:
        if name in _sys.modules and isinstance(_sys.modules[name], MagicMock):
            _sys.modules.pop(name, None)
