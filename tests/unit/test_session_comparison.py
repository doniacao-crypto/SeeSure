"""
Unit tests for session_comparison.py - Multi-session comparison.
"""

import pytest
from src.session_comparison import (
    ComparisonMetric, SessionComparator, compare_sessions
)


class TestComparisonMetric:
    """Test ComparisonMetric dataclass."""
    
    def test_create_metric(self):
        metric = ComparisonMetric(
            name="Pursuit Gain",
            session1_value=0.85,
            session2_value=0.92,
            unit="",
            higher_is_better=True
        )
        assert metric.name == "Pursuit Gain"
        assert metric.session1_value == 0.85
        assert metric.session2_value == 0.92
    
    def test_difference_positive(self):
        metric = ComparisonMetric("Test", 0.80, 0.90, "", True)
        assert metric.difference == pytest.approx(0.10)
    
    def test_difference_negative(self):
        metric = ComparisonMetric("Test", 0.90, 0.80, "", True)
        assert metric.difference == pytest.approx(-0.10)
    
    def test_difference_with_none(self):
        metric = ComparisonMetric("Test", None, 0.90, "", True)
        assert metric.difference is None
    
    def test_percent_change(self):
        metric = ComparisonMetric("Test", 0.80, 0.88, "", True)
        assert metric.percent_change == pytest.approx(10.0)
    
    def test_percent_change_zero_baseline(self):
        metric = ComparisonMetric("Test", 0.0, 0.50, "", True)
        assert metric.percent_change is None
    
    def test_improved_higher_is_better(self):
        metric = ComparisonMetric("Test", 0.80, 0.90, "", higher_is_better=True)
        assert metric.improved is True
    
    def test_improved_lower_is_better(self):
        metric = ComparisonMetric("Latency", 250, 200, "ms", higher_is_better=False)
        assert metric.improved is True
    
    def test_declined_higher_is_better(self):
        metric = ComparisonMetric("Test", 0.90, 0.80, "", higher_is_better=True)
        assert metric.improved is False
    
    def test_status_symbol_improved(self):
        metric = ComparisonMetric("Test", 0.80, 0.90, "", True)
        assert metric.status_symbol == "↑"
    
    def test_status_symbol_declined(self):
        metric = ComparisonMetric("Test", 0.90, 0.80, "", True)
        assert metric.status_symbol == "↓"
    
    def test_status_symbol_none(self):
        metric = ComparisonMetric("Test", None, 0.90, "", True)
        assert metric.status_symbol == "—"


class TestSessionComparator:
    """Test SessionComparator class."""
    
    def test_create_comparator(self):
        comp = SessionComparator()
        assert comp.metrics == []
    
    def test_compare_pursuit_results(self):
        class MockResult:
            tracking_ratio = 0.85
            accuracy_score = 80
            smooth_score = 75
            pursuit_gain = 0.90
            accuracy_degrees = 2.5
            smoothness = 0.8
            catch_up_saccade_count = 5
        
        comp = SessionComparator()
        session1 = MockResult()
        session2 = MockResult()
        session2.tracking_ratio = 0.90
        session2.pursuit_gain = 0.95
        
        metrics = comp.compare_pursuit_results(session1, session2)
        assert len(metrics) > 0
        
        # Find tracking ratio metric
        tr_metric = next((m for m in metrics if m.name == "Tracking Ratio"), None)
        assert tr_metric is not None
        assert tr_metric.session1_value == 0.85
        assert tr_metric.session2_value == 0.90
    
    def test_compare_saccade_results(self):
        class MockResult:
            mean_latency_ms = 200
            std_latency_ms = 25
            error_rate = 0.1
            mean_accuracy_deg = 2.0
        
        comp = SessionComparator()
        session1 = MockResult()
        session2 = MockResult()
        session2.mean_latency_ms = 180
        
        metrics = comp.compare_saccade_results(session1, session2)
        assert len(metrics) > 0
        
        lat_metric = next((m for m in metrics if m.name == "Mean Latency"), None)
        assert lat_metric is not None
        assert lat_metric.higher_is_better is False
    
    def test_generate_comparison_report(self):
        comp = SessionComparator()
        comp.metrics = [
            ComparisonMetric("Gain", 0.85, 0.92, "", True),
            ComparisonMetric("Latency", 220, 200, "ms", False),
        ]
        
        report = comp.generate_comparison_report("2024-01-01", "2024-01-15")
        assert "SESSION COMPARISON REPORT" in report
        assert "Baseline: 2024-01-01" in report
        assert "Current:  2024-01-15" in report
        assert "Gain" in report
        assert "Latency" in report


class TestCompareSessionsFunction:
    """Test compare_sessions helper function."""
    
    def test_compare_unknown_type(self):
        metrics, report = compare_sessions(None, None, "unknown")
        assert metrics == []
        assert "Unknown test type" in report
