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
