"""
Unit tests for progress_tracking.py - Longitudinal progress tracking.
"""

import pytest
import tempfile
import os
from src.progress_tracking import (
    SessionMetrics, ProgressReport, ProgressTracker
)


class TestSessionMetrics:
    """Test SessionMetrics dataclass."""
    
    def test_create_session_metrics(self):
        metrics = SessionMetrics(
            session_id="001",
            date="2024-01-01T10:00:00",
            test_type="pursuit"
        )
        assert metrics.session_id == "001"
        assert metrics.test_type == "pursuit"
    
    def test_optional_fields_default_none(self):
        metrics = SessionMetrics(
            session_id="001",
            date="2024-01-01",
            test_type="pursuit"
        )
        assert metrics.pursuit_gain is None
        assert metrics.saccade_latency_ms is None
    
    def test_set_pursuit_metrics(self):
        metrics = SessionMetrics(
            session_id="001",
            date="2024-01-01",
            test_type="pursuit",
            pursuit_gain=0.92,
            smoothness=0.85
        )
        assert metrics.pursuit_gain == 0.92
        assert metrics.smoothness == 0.85


class TestProgressReport:
    """Test ProgressReport class."""
    
    def test_empty_report(self):
        report = ProgressReport(patient_id="P001")
        assert report.num_sessions == 0
        assert report.date_range is None
    
    def test_add_session(self):
        report = ProgressReport(patient_id="P001")
        metrics = SessionMetrics("001", "2024-01-01", "pursuit")
        report.add_session(metrics)
        assert report.num_sessions == 1
    
    def test_sessions_sorted_by_date(self):
        report = ProgressReport(patient_id="P001")
        report.add_session(SessionMetrics("002", "2024-01-03", "pursuit"))
        report.add_session(SessionMetrics("001", "2024-01-01", "pursuit"))
        report.add_session(SessionMetrics("003", "2024-01-02", "pursuit"))
        
        assert report.sessions[0].date == "2024-01-01"
        assert report.sessions[2].date == "2024-01-03"
    
    def test_date_range(self):
        report = ProgressReport(patient_id="P001")
        report.add_session(SessionMetrics("001", "2024-01-01", "pursuit"))
        report.add_session(SessionMetrics("002", "2024-01-15", "pursuit"))
        
        assert report.date_range == ("2024-01-01", "2024-01-15")
    
    def test_get_metric_trend(self):
        report = ProgressReport(patient_id="P001")
        report.add_session(SessionMetrics("001", "2024-01-01", "pursuit", pursuit_gain=0.85))
        report.add_session(SessionMetrics("002", "2024-01-15", "pursuit", pursuit_gain=0.90))
        
        trend = report.get_metric_trend("pursuit_gain")
        assert len(trend) == 2
        assert trend[0] == ("2024-01-01", 0.85)
        assert trend[1] == ("2024-01-15", 0.90)
    
    def test_calculate_improvement_positive(self):
        report = ProgressReport(patient_id="P001")
        report.add_session(SessionMetrics("001", "2024-01-01", "pursuit", pursuit_gain=0.80))
        report.add_session(SessionMetrics("002", "2024-01-15", "pursuit", pursuit_gain=0.90))
        
        improvement = report.calculate_improvement("pursuit_gain", higher_is_better=True)
        assert improvement["improved"] is True
        assert improvement["baseline"] == 0.80
        assert improvement["current"] == 0.90
    
    def test_calculate_improvement_negative(self):
        report = ProgressReport(patient_id="P001")
        report.add_session(SessionMetrics("001", "2024-01-01", "pursuit", pursuit_gain=0.90))
        report.add_session(SessionMetrics("002", "2024-01-15", "pursuit", pursuit_gain=0.80))
        
        improvement = report.calculate_improvement("pursuit_gain", higher_is_better=True)
        assert improvement["improved"] is False
    
    def test_calculate_improvement_lower_is_better(self):
        report = ProgressReport(patient_id="P001")
        report.add_session(SessionMetrics("001", "2024-01-01", "pursuit", accuracy_degrees=3.0))
        report.add_session(SessionMetrics("002", "2024-01-15", "pursuit", accuracy_degrees=2.0))
        
        improvement = report.calculate_improvement("accuracy_degrees", higher_is_better=False)
        assert improvement["improved"] is True
    
    def test_calculate_improvement_insufficient_data(self):
        report = ProgressReport(patient_id="P001")
        report.add_session(SessionMetrics("001", "2024-01-01", "pursuit", pursuit_gain=0.85))
        
        improvement = report.calculate_improvement("pursuit_gain")
        assert improvement is None
    
    def test_get_summary(self):
        report = ProgressReport(patient_id="P001")
        report.add_session(SessionMetrics("001", "2024-01-01", "pursuit", pursuit_gain=0.80))
        report.add_session(SessionMetrics("002", "2024-01-15", "pursuit", pursuit_gain=0.90))
        
        summary = report.get_summary()
        assert summary["patient_id"] == "P001"
        assert summary["num_sessions"] == 2
        assert "pursuit_gain" in summary["metrics"]


class TestProgressTracker:
    """Test ProgressTracker class."""
    
    def test_create_tracker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ProgressTracker(data_dir=tmpdir)
            assert os.path.exists(tmpdir)
    
    def test_get_empty_progress(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ProgressTracker(data_dir=tmpdir)
            report = tracker.get_progress("NEW_PATIENT")
            assert report.num_sessions == 0
    
    def test_generate_progress_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ProgressTracker(data_dir=tmpdir)
            text = tracker.generate_progress_text("P001")
            assert "PROGRESS REPORT" in text
            assert "P001" in text
