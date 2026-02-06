"""
Integration tests for clinical workflow.
Tests end-to-end scenarios across multiple modules.
"""

import pytest
import tempfile
import os
import json


class TestPatientWorkflow:
    """Test patient management integration."""
    
    def test_patient_create_and_track_progress(self):
        """Test creating patient and tracking progress."""
        from src.patient_manager import PatientManager
        from src.progress_tracking import ProgressTracker, SessionMetrics
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create patient
            patient_mgr = PatientManager(data_dir=os.path.join(tmpdir, "patients"))
            patient = patient_mgr.create(
                name="John Doe",
                date_of_birth="1990-05-15"
            )
            assert patient.id is not None
            
            # Track progress
            tracker = ProgressTracker(data_dir=os.path.join(tmpdir, "progress"))
            
            # Simulate sessions
            class MockResult:
                accuracy_score = 85
                tracking_ratio = 0.9
                pursuit_gain = 0.88
            
            tracker.record_session(patient.id, MockResult(), "pursuit")
            
            # Get progress
            report = tracker.get_progress(patient.id)
            assert report.num_sessions == 1


class TestNormativeScreening:
    """Test normative data screening integration."""
    
    def test_evaluate_pursuit_with_age(self):
        """Test age-matched evaluation."""
        from src.normative_data import NormativeComparison
        
        # Young adult
        comp_young = NormativeComparison(age=25)
        result = comp_young.evaluate_pursuit_gain(0.90)
        assert result.status == "pass"
        
        # Older adult (different norms)
        comp_older = NormativeComparison(age=70)
        result = comp_older.evaluate_pursuit_gain(0.85)
        assert result.status == "pass"  # Normal for age
    
    def test_overall_screening_workflow(self):
        """Test complete screening with multiple metrics."""
        from src.normative_data import NormativeComparison
        
        comp = NormativeComparison(age=30)
        
        results = [
            comp.evaluate_pursuit_gain(0.92),
            comp.evaluate_saccade_latency(190),
            comp.evaluate_antisaccade_error(8)
        ]
        
        status, interpretation = comp.get_overall_screening(results)
        assert status == "PASS"


class TestReportGeneration:
    """Test report generation integration."""
    
    def test_fhir_report_from_test_result(self):
        """Test FHIR report creation from results."""
        from src.enterprise import create_fhir_report
        
        class MockResult:
            pursuit_gain = 0.92
            accuracy_degrees = 1.5
            mean_latency_ms = 195
        
        report = create_fhir_report(MockResult(), patient_id="P123")
        fhir_json = report.to_fhir_json()
        
        assert fhir_json["resourceType"] == "DiagnosticReport"
        assert "Patient/P123" in fhir_json["subject"]["reference"]
        assert "Pursuit gain" in fhir_json["conclusion"]


class TestSessionComparison:
    """Test session comparison integration."""
    
    def test_compare_two_sessions(self):
        """Test comparing two test sessions."""
        from src.session_comparison import SessionComparator
        
        class Session1:
            tracking_ratio = 0.80
            accuracy_score = 75
            smooth_score = 70
            pursuit_gain = 0.85
            accuracy_degrees = 3.0
            smoothness = 0.75
            catch_up_saccade_count = 8
        
        class Session2:
            tracking_ratio = 0.88
            accuracy_score = 82
            smooth_score = 78
            pursuit_gain = 0.91
            accuracy_degrees = 2.5
            smoothness = 0.82
            catch_up_saccade_count = 5
        
        comp = SessionComparator()
        metrics = comp.compare_pursuit_results(Session1(), Session2())
        
        # Should show improvement in key metrics
        gain_metric = next((m for m in metrics if m.name == "Pursuit Gain"), None)
        assert gain_metric is not None
        assert gain_metric.improved is True
        
        # Generate report
        report = comp.generate_comparison_report("2024-01-01", "2024-01-15")
        assert "Improved" in report


class TestResearchWorkflow:
    """Test research mode integration."""
    
    def test_research_session_lifecycle(self):
        """Test complete research session workflow."""
        from src.research_mode import (
            ResearchDataManager, ResearchConfig, ResearchProtocol
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ResearchDataManager(data_dir=tmpdir)
            
            # Configure extended protocol
            config = ResearchConfig(
                protocol=ResearchProtocol.EXTENDED_PURSUIT,
                num_trials=10,
                experiment_id="TEST_EXP"
            )
            
            # Create session
            session = manager.create_session(config, "PARTICIPANT_001")
            
            # Simulate trials
            for i in range(10):
                session.add_trial_result({
                    "trial": i + 1,
                    "gain": 0.85 + (i * 0.01),
                    "accuracy": 2.5 - (i * 0.1)
                })
            
            session.finalize()
            manager.save_session(session)
            
            # Verify saved
            sessions = manager.list_sessions()
            assert len(sessions) == 1
            assert sessions[0]["num_trials"] == 10


class TestMultiClinicianWorkflow:
    """Test multi-clinician support integration."""
    
    def test_clinician_creates_and_logs_in(self):
        """Test clinician account workflow."""
        from src.enterprise import ClinicianManager, UserRole
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "clinicians.json")
            manager = ClinicianManager(data_path=path)
            
            # Admin creates clinician
            admin = manager.create(
                username="admin",
                full_name="System Admin",
                role=UserRole.ADMIN
            )
            
            # Admin creates technician
            tech = manager.create(
                username="tech1",
                full_name="Tech One",
                role=UserRole.TECHNICIAN
            )
            
            # Clinician logs in
            manager.record_login(tech.id)
            
            # Verify
            updated = manager.get(tech.id)
            assert updated.last_login != ""


class TestLocalizationWorkflow:
    """Test multi-language support integration."""
    
    def test_switch_language_runtime(self):
        """Test changing language at runtime."""
        from src.enterprise import Localizer, Language
        
        loc = Localizer(Language.ENGLISH)
        assert loc.get("start_calibration") == "Start Calibration"
        
        loc.set_language(Language.SPANISH)
        assert loc.get("start_calibration") == "Iniciar Calibración"
        
        loc.set_language(Language.CHINESE)
        assert loc.get("start_calibration") == "开始校准"
