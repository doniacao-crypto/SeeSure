"""
Unit tests for enterprise.py - Enterprise features.
"""

import pytest
import tempfile
import os
from src.enterprise import (
    PracticeBranding, BrandingManager,
    Clinician, ClinicianManager, UserRole,
    FHIRDiagnosticReport, create_fhir_report,
    Language, Localizer, TRANSLATIONS,
    TouchModeConfig, apply_touch_mode
)


class TestPracticeBranding:
    """Test PracticeBranding dataclass."""
    
    def test_default_branding(self):
        branding = PracticeBranding()
        assert branding.practice_name == "Eye Movement Assessment Center"
        assert branding.primary_color == "#3498db"
    
    def test_custom_branding(self):
        branding = PracticeBranding(
            practice_name="My Eye Clinic",
            phone="555-1234"
        )
        assert branding.practice_name == "My Eye Clinic"
        assert branding.phone == "555-1234"
    
    def test_to_dict(self):
        branding = PracticeBranding(practice_name="Test")
        data = branding.to_dict()
        assert data["practice_name"] == "Test"
        assert "primary_color" in data
    
    def test_from_dict(self):
        data = {"practice_name": "Loaded", "phone": "555-0000"}
        branding = PracticeBranding.from_dict(data)
        assert branding.practice_name == "Loaded"
    
    def test_get_full_address(self):
        branding = PracticeBranding(
            address_line1="123 Main St",
            city="Boston",
            state="MA",
            zip_code="02101"
        )
        address = branding.get_full_address()
        assert "123 Main St" in address
        assert "Boston" in address


class TestBrandingManager:
    """Test BrandingManager class."""
    
    def test_create_manager(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "branding.json")
            manager = BrandingManager(config_path=path)
            assert manager is not None
    
    def test_get_default_branding(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "branding.json")
            manager = BrandingManager(config_path=path)
            branding = manager.get_branding("default")
            assert branding.practice_name == "Eye Movement Assessment Center"
    
    def test_save_and_load_branding(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "branding.json")
            manager = BrandingManager(config_path=path)
            
            custom = PracticeBranding(practice_name="Saved Clinic")
            manager.save_branding(custom, "test")
            
            # Reload
            manager2 = BrandingManager(config_path=path)
            loaded = manager2.get_branding("test")
            assert loaded.practice_name == "Saved Clinic"


class TestClinician:
    """Test Clinician dataclass."""
    
    def test_create_clinician(self):
        clin = Clinician(username="drsmith", full_name="Dr. Smith")
        assert clin.username == "drsmith"
        assert clin.full_name == "Dr. Smith"
        assert clin.id != ""  # Auto-generated
    
    def test_default_role(self):
        clin = Clinician(username="user")
        assert clin.role == UserRole.CLINICIAN
    
    def test_to_dict(self):
        clin = Clinician(username="test", role=UserRole.ADMIN)
        data = clin.to_dict()
        assert data["username"] == "test"
        assert data["role"] == "admin"
    
    def test_from_dict(self):
        data = {"username": "loaded", "role": "technician", "id": "ABC123"}
        clin = Clinician.from_dict(data)
        assert clin.username == "loaded"
        assert clin.role == UserRole.TECHNICIAN


class TestClinicianManager:
    """Test ClinicianManager class."""
    
    def test_create_clinician(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "clinicians.json")
            manager = ClinicianManager(data_path=path)
            
            clin = manager.create(username="drjones", full_name="Dr. Jones")
            assert clin.username == "drjones"
    
    def test_list_active(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "clinicians.json")
            manager = ClinicianManager(data_path=path)
            
            manager.create(username="active1", active=True)
            manager.create(username="inactive", active=False)
            
            active = manager.list_active()
            assert len(active) == 1
            assert active[0].username == "active1"


class TestFHIRDiagnosticReport:
    """Test FHIR integration."""
    
    def test_create_report(self):
        report = FHIRDiagnosticReport()
        assert report.resource_type == "DiagnosticReport"
        assert report.status == "final"
    
    def test_to_fhir_json(self):
        report = FHIRDiagnosticReport(
            subject_reference="Patient/123",
            conclusion="Normal findings"
        )
        json_data = report.to_fhir_json()
        
        assert json_data["resourceType"] == "DiagnosticReport"
        assert json_data["subject"]["reference"] == "Patient/123"
        assert json_data["conclusion"] == "Normal findings"
    
    def test_create_fhir_report_from_result(self):
        class MockResult:
            pursuit_gain = 0.92
            accuracy_degrees = 1.5
        
        report = create_fhir_report(MockResult(), patient_id="P456")
        assert "Patient/P456" in report.subject_reference
        assert "Pursuit gain" in report.conclusion


class TestLanguage:
    """Test multi-language support."""
    
    def test_language_enum(self):
        assert Language.ENGLISH.value == "en"
        assert Language.SPANISH.value == "es"
        assert Language.CHINESE.value == "zh"
    
    def test_translations_exist(self):
        assert "start_calibration" in TRANSLATIONS
        assert "start_test" in TRANSLATIONS
    
    def test_english_translation(self):
        assert TRANSLATIONS["start_calibration"][Language.ENGLISH] == "Start Calibration"
    
    def test_spanish_translation(self):
        assert TRANSLATIONS["start_calibration"][Language.SPANISH] == "Iniciar Calibración"
    
    def test_chinese_translation(self):
        assert TRANSLATIONS["start_test"][Language.CHINESE] == "开始测试"


class TestLocalizer:
    """Test Localizer class."""
    
    def test_default_english(self):
        loc = Localizer()
        assert loc.language == Language.ENGLISH
    
    def test_get_english(self):
        loc = Localizer(Language.ENGLISH)
        assert loc.get("start_calibration") == "Start Calibration"
    
    def test_get_spanish(self):
        loc = Localizer(Language.SPANISH)
        assert loc.get("start_calibration") == "Iniciar Calibración"
    
    def test_get_unknown_key(self):
        loc = Localizer()
        assert loc.get("unknown_key") == "unknown_key"
    
    def test_set_language(self):
        loc = Localizer(Language.ENGLISH)
        loc.set_language(Language.FRENCH)
        assert loc.language == Language.FRENCH


class TestTouchMode:
    """Test tablet/touch mode configuration."""
    
    def test_default_disabled(self):
        config = TouchModeConfig()
        assert config.enabled is False
    
    def test_button_multiplier(self):
        config = TouchModeConfig(enabled=True, button_size_multiplier=2.0)
        assert config.button_size_multiplier == 2.0
    
    def test_apply_touch_mode_disabled(self):
        config = TouchModeConfig(enabled=False)
        css = apply_touch_mode(config)
        assert css == {}
    
    def test_apply_touch_mode_enabled(self):
        config = TouchModeConfig(enabled=True)
        css = apply_touch_mode(config)
        assert "QPushButton" in css
        assert "min-height" in css["QPushButton"]
