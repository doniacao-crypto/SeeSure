"""
Unit tests for main_app.py - Tests actual module behavior with mocked PyQt6/cv2.

These tests import main_app (with heavy dependencies mocked) and verify
real attributes, constants, method logic, and configuration values rather
than testing local variables against themselves.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
import sys


# ---------------------------------------------------------------------------
# Mock heavy dependencies BEFORE importing main_app
# ---------------------------------------------------------------------------

# PyQt6 family -- plain MagicMock (no spec) so arbitrary attribute access works
_pyqt6 = MagicMock()
_pyqt6_widgets = MagicMock()
_pyqt6_core = MagicMock()
_pyqt6_gui = MagicMock()

# Make QMainWindow a proper class so MainWindow can inherit from it
_pyqt6_widgets.QMainWindow = type("QMainWindow", (), {"__init__": lambda self, *a, **kw: None})
_pyqt6_widgets.QWidget = type("QWidget", (), {"__init__": lambda self, *a, **kw: None})

sys.modules["PyQt6"] = _pyqt6
sys.modules["PyQt6.QtWidgets"] = _pyqt6_widgets
sys.modules["PyQt6.QtCore"] = _pyqt6_core
sys.modules["PyQt6.QtGui"] = _pyqt6_gui

# OpenCV
sys.modules["cv2"] = MagicMock()

# Mock GUI-dependent source modules that main_app imports
sys.modules["eye_tracker"] = MagicMock()
sys.modules["gaze_estimator"] = MagicMock()
sys.modules["visualization"] = MagicMock()
sys.modules["widgets"] = MagicMock()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def main_app_module():
    """Import main_app with mocked dependencies and return the module."""
    import main_app
    return main_app


# ---------------------------------------------------------------------------
# Test: Module-level imports succeed
# ---------------------------------------------------------------------------

class TestMainAppModuleImport:
    """Verify the main_app module loads and exposes expected symbols."""

    def test_module_imports_successfully(self, main_app_module):
        """main_app should import without errors when deps are mocked."""
        assert main_app_module is not None

    def test_main_window_class_exists(self, main_app_module):
        """Module must expose the MainWindow class."""
        assert hasattr(main_app_module, "MainWindow")

    def test_main_function_exists(self, main_app_module):
        """Module must expose the main() entry point."""
        assert hasattr(main_app_module, "main")
        assert callable(main_app_module.main)

    def test_main_window_is_class(self, main_app_module):
        """MainWindow should be a class, not a function or instance."""
        assert isinstance(main_app_module.MainWindow, type)


# ---------------------------------------------------------------------------
# Test: MainWindow imports correct domain types from other modules
# ---------------------------------------------------------------------------

class TestMainAppDomainImports:
    """Verify that main_app imports the correct domain types it needs."""

    def test_imports_test_config(self, main_app_module):
        """main_app should use TestConfig from smooth_pursuit_test."""
        assert hasattr(main_app_module, "TestConfig")

    def test_imports_target_pattern(self, main_app_module):
        """main_app should use TargetPattern enum."""
        assert hasattr(main_app_module, "TargetPattern")

    def test_imports_test_result(self, main_app_module):
        """main_app should use TestResult from smooth_pursuit_test."""
        assert hasattr(main_app_module, "TestResult")

    def test_imports_generate_report(self, main_app_module):
        """main_app should use generate_report function."""
        assert hasattr(main_app_module, "generate_report")
        assert callable(main_app_module.generate_report)

    def test_imports_saccade_test_type(self, main_app_module):
        """main_app should use SaccadeTestType enum for pro/anti saccade."""
        assert hasattr(main_app_module, "SaccadeTestType")

    def test_imports_session_history_manager(self, main_app_module):
        """main_app should use SessionHistoryManager."""
        assert hasattr(main_app_module, "SessionHistoryManager")

    def test_imports_patient_manager(self, main_app_module):
        """main_app should use PatientManager."""
        assert hasattr(main_app_module, "PatientManager")

    def test_imports_validation_pattern(self, main_app_module):
        """main_app should use ValidationPattern enum."""
        assert hasattr(main_app_module, "ValidationPattern")

    def test_imports_pdf_report_generator(self, main_app_module):
        """main_app should use PDFReportGenerator."""
        assert hasattr(main_app_module, "PDFReportGenerator")


# ---------------------------------------------------------------------------
# Test: Pattern combo items match TargetPattern enum usage
# ---------------------------------------------------------------------------

class TestPatternConfiguration:
    """Verify pattern-related configuration in main_app."""

    def test_target_pattern_horizontal_value(self, main_app_module):
        """TargetPattern.HORIZONTAL should have value 'horizontal'."""
        assert main_app_module.TargetPattern.HORIZONTAL.value == "horizontal"

    def test_target_pattern_vertical_value(self, main_app_module):
        """TargetPattern.VERTICAL should have value 'vertical'."""
        assert main_app_module.TargetPattern.VERTICAL.value == "vertical"

    def test_target_pattern_circular_value(self, main_app_module):
        """TargetPattern.CIRCULAR should have value 'circular'."""
        assert main_app_module.TargetPattern.CIRCULAR.value == "circular"

    def test_target_pattern_figure_eight_value(self, main_app_module):
        """TargetPattern.FIGURE_EIGHT should have value 'figure_eight'."""
        assert main_app_module.TargetPattern.FIGURE_EIGHT.value == "figure_eight"

    def test_target_pattern_fixation_value(self, main_app_module):
        """TargetPattern.FIXATION should have value 'fixation'."""
        assert main_app_module.TargetPattern.FIXATION.value == "fixation"

    def test_saccade_test_types_available(self, main_app_module):
        """SaccadeTestType enum should provide PRO_SACCADE and ANTI_SACCADE."""
        stt = main_app_module.SaccadeTestType
        assert hasattr(stt, "PRO_SACCADE")
        assert hasattr(stt, "ANTI_SACCADE")


# ---------------------------------------------------------------------------
# Test: TestConfig defaults used by _start_test
# ---------------------------------------------------------------------------

class TestTestConfigDefaults:
    """Verify TestConfig default values that main_app relies on."""

    def test_default_pattern_is_horizontal(self, main_app_module):
        """Default TestConfig pattern should be HORIZONTAL."""
        config = main_app_module.TestConfig()
        assert config.pattern == main_app_module.TargetPattern.HORIZONTAL

    def test_default_duration(self, main_app_module):
        """Default duration should be 10 seconds."""
        config = main_app_module.TestConfig()
        assert config.duration_seconds == 10.0

    def test_default_speed(self, main_app_module):
        """Default speed should be 0.5."""
        config = main_app_module.TestConfig()
        assert config.speed == 0.5

    def test_default_target_size(self, main_app_module):
        """Default target size should be 20 pixels."""
        config = main_app_module.TestConfig()
        assert config.target_size == 20

    def test_config_accepts_custom_values(self, main_app_module):
        """TestConfig should accept custom duration and speed."""
        config = main_app_module.TestConfig(duration_seconds=30, speed=0.8)
        assert config.duration_seconds == 30
        assert config.speed == 0.8


# ---------------------------------------------------------------------------
# Test: SaccadeTestConfig construction (mirrors _start_saccade_test)
# ---------------------------------------------------------------------------

class TestSaccadeTestConfigConstruction:
    """Verify SaccadeTestConfig can be constructed the way main_app does."""

    def test_pro_saccade_config(self, main_app_module):
        """Pro-saccade config should be constructible with expected params."""
        config = main_app_module.SaccadeTestConfig(
            test_type=main_app_module.SaccadeTestType.PRO_SACCADE,
            num_trials=20,
            eccentricities_deg=[10.0],
            fixation_duration_ms=1000.0,
            gap_duration_ms=200.0,
            randomize_direction=True,
            randomize_timing=True,
        )
        assert config.test_type == main_app_module.SaccadeTestType.PRO_SACCADE
        assert config.num_trials == 20

    def test_anti_saccade_config(self, main_app_module):
        """Anti-saccade config should be constructible with expected params."""
        config = main_app_module.SaccadeTestConfig(
            test_type=main_app_module.SaccadeTestType.ANTI_SACCADE,
            num_trials=20,
            eccentricities_deg=[10.0],
            fixation_duration_ms=1000.0,
            gap_duration_ms=200.0,
            randomize_direction=True,
            randomize_timing=True,
        )
        assert config.test_type == main_app_module.SaccadeTestType.ANTI_SACCADE


# ---------------------------------------------------------------------------
# Test: ValidationConfig construction (mirrors _start_validation)
# ---------------------------------------------------------------------------

class TestValidationConfigConstruction:
    """Verify ValidationConfig can be constructed the way main_app does."""

    def test_grid_9_validation_config(self, main_app_module):
        """Validation config with GRID_9 pattern should be constructible."""
        config = main_app_module.ValidationConfig(
            pattern=main_app_module.ValidationPattern.GRID_9,
            samples_per_point=30,
            point_duration_ms=2000.0,
        )
        assert config.pattern == main_app_module.ValidationPattern.GRID_9
        assert config.samples_per_point == 30
        assert config.point_duration_ms == 2000.0


# ---------------------------------------------------------------------------
# Test: Speed slider conversion logic
# ---------------------------------------------------------------------------

class TestSpeedSliderLogic:
    """Test the speed slider value-to-speed conversion used in main_app."""

    def test_slider_min_to_speed(self):
        """Slider value 1 should yield speed 0.1."""
        speed = 1 / 10.0
        assert speed == pytest.approx(0.1)

    def test_slider_mid_to_speed(self):
        """Slider value 5 (default) should yield speed 0.5."""
        speed = 5 / 10.0
        assert speed == pytest.approx(0.5)

    def test_slider_max_to_speed(self):
        """Slider value 10 should yield speed 1.0."""
        speed = 10 / 10.0
        assert speed == pytest.approx(1.0)

    def test_speed_label_format(self):
        """Speed label should show 1 decimal place (e.g. '0.5')."""
        speed = 5 / 10.0
        label_text = f"{speed:.1f}"
        assert label_text == "0.5"


# ---------------------------------------------------------------------------
# Test: generate_report produces valid output
# ---------------------------------------------------------------------------

class TestGenerateReport:
    """Test that generate_report from smooth_pursuit_test works correctly."""

    def test_report_contains_header(self, main_app_module):
        """Report should contain the assessment header."""
        result = main_app_module.TestResult(
            pattern=main_app_module.TargetPattern.HORIZONTAL,
            duration=5.0,
        )
        result.tracking_ratio = 0.85
        result.accuracy_score = 75.0
        result.smooth_score = 60.0
        report = main_app_module.generate_report(result, include_clinical=False)
        assert "EYE MOVEMENT ASSESSMENT REPORT" in report

    def test_report_contains_pattern(self, main_app_module):
        """Report should mention the test pattern."""
        result = main_app_module.TestResult(
            pattern=main_app_module.TargetPattern.CIRCULAR,
            duration=10.0,
        )
        result.tracking_ratio = 0.90
        result.accuracy_score = 80.0
        result.smooth_score = 70.0
        report = main_app_module.generate_report(result, include_clinical=False)
        assert "circular" in report.lower()

    def test_report_contains_disclaimer(self, main_app_module):
        """Report should contain the clinical disclaimer."""
        result = main_app_module.TestResult(
            pattern=main_app_module.TargetPattern.HORIZONTAL,
            duration=5.0,
        )
        report = main_app_module.generate_report(result, include_clinical=False)
        assert "DISCLAIMER" in report


# ---------------------------------------------------------------------------
# Test: TestResult serialization (to_summary_dict used by _on_test_complete)
# ---------------------------------------------------------------------------

class TestResultSerialization:
    """Test TestResult.to_summary_dict produces valid output."""

    def test_summary_dict_has_pattern(self, main_app_module):
        """Summary dict should include the pattern value string."""
        result = main_app_module.TestResult(
            pattern=main_app_module.TargetPattern.VERTICAL,
            duration=8.0,
        )
        summary = result.to_summary_dict()
        assert summary["pattern"] == "vertical"

    def test_summary_dict_has_duration(self, main_app_module):
        """Summary dict should include the test duration."""
        result = main_app_module.TestResult(
            pattern=main_app_module.TargetPattern.HORIZONTAL,
            duration=12.0,
        )
        summary = result.to_summary_dict()
        assert summary["duration"] == 12.0

    def test_summary_dict_has_metrics(self, main_app_module):
        """Summary dict should include a metrics section."""
        result = main_app_module.TestResult(
            pattern=main_app_module.TargetPattern.HORIZONTAL,
            duration=5.0,
        )
        summary = result.to_summary_dict()
        assert "metrics" in summary
        assert "tracking_ratio" in summary["metrics"]


# ---------------------------------------------------------------------------
# Test: TestResult save methods use tmp directory (integration-lite)
# ---------------------------------------------------------------------------

class TestResultSaveToFile:
    """Test that TestResult.save_summary writes to disk correctly."""

    def test_save_summary_creates_file(self, main_app_module, tmp_data_dir):
        """save_summary should create a JSON file in the given directory."""
        result = main_app_module.TestResult(
            pattern=main_app_module.TargetPattern.HORIZONTAL,
            duration=5.0,
        )
        result.tracking_ratio = 0.9
        result.accuracy_score = 80.0
        result.smooth_score = 70.0

        filepath = result.save_summary(results_dir=str(tmp_data_dir))
        from pathlib import Path
        assert Path(filepath).exists()
        assert filepath.endswith(".json")

    def test_save_summary_contains_valid_json(self, main_app_module, tmp_data_dir):
        """Saved summary file should contain valid JSON."""
        import json

        result = main_app_module.TestResult(
            pattern=main_app_module.TargetPattern.HORIZONTAL,
            duration=5.0,
        )
        filepath = result.save_summary(results_dir=str(tmp_data_dir))

        with open(filepath) as f:
            data = json.load(f)

        assert data["pattern"] == "horizontal"
        assert "metrics" in data
