"""
Unit tests for normative_data.py - Age-matched reference values.
"""

import pytest
from src.normative_data import (
    AgeGroup, NormativeRange, get_age_group,
    NormativeComparison, ScreeningResult,
    PURSUIT_GAIN_NORMS, SACCADE_LATENCY_NORMS, ANTISACCADE_ERROR_NORMS
)


class TestAgeGroup:
    """Test age group classification."""
    
    def test_child_age_group(self):
        assert get_age_group(8) == AgeGroup.CHILD
        assert get_age_group(12) == AgeGroup.CHILD
    
    def test_adolescent_age_group(self):
        assert get_age_group(13) == AgeGroup.ADOLESCENT
        assert get_age_group(17) == AgeGroup.ADOLESCENT
    
    def test_young_adult_age_group(self):
        assert get_age_group(18) == AgeGroup.YOUNG_ADULT
        assert get_age_group(39) == AgeGroup.YOUNG_ADULT
    
    def test_middle_adult_age_group(self):
        assert get_age_group(40) == AgeGroup.MIDDLE_ADULT
        assert get_age_group(59) == AgeGroup.MIDDLE_ADULT
    
    def test_older_adult_age_group(self):
        assert get_age_group(60) == AgeGroup.OLDER_ADULT
        assert get_age_group(85) == AgeGroup.OLDER_ADULT


class TestNormativeRange:
    """Test NormativeRange calculations."""
    
    def test_is_normal_within_range(self):
        norm = NormativeRange(mean=0.9, std=0.05, lower_normal=0.8, upper_normal=1.0)
        assert norm.is_normal(0.85) is True
        assert norm.is_normal(0.95) is True
    
    def test_is_normal_outside_range(self):
        norm = NormativeRange(mean=0.9, std=0.05, lower_normal=0.8, upper_normal=1.0)
        assert norm.is_normal(0.7) is False
        assert norm.is_normal(1.1) is False
    
    def test_get_status_normal(self):
        norm = NormativeRange(mean=0.9, std=0.05, lower_normal=0.8, upper_normal=1.0)
        assert norm.get_status(0.9) == "normal"
    
    def test_get_status_low(self):
        norm = NormativeRange(mean=0.9, std=0.05, lower_normal=0.8, upper_normal=1.0)
        assert norm.get_status(0.7) == "low"
    
    def test_get_status_high(self):
        norm = NormativeRange(mean=0.9, std=0.05, lower_normal=0.8, upper_normal=1.0)
        assert norm.get_status(1.2) == "high"
    
    def test_percentile_at_mean(self):
        norm = NormativeRange(mean=100, std=15, lower_normal=70, upper_normal=130)
        percentile = norm.get_percentile(100)
        assert 49 < percentile < 51  # Should be ~50th percentile


class TestNormativeData:
    """Test normative data dictionaries."""
    
    def test_pursuit_gain_norms_exist(self):
        assert AgeGroup.YOUNG_ADULT in PURSUIT_GAIN_NORMS
        assert AgeGroup.OLDER_ADULT in PURSUIT_GAIN_NORMS
    
    def test_saccade_latency_norms_exist(self):
        assert AgeGroup.YOUNG_ADULT in SACCADE_LATENCY_NORMS
        assert AgeGroup.CHILD in SACCADE_LATENCY_NORMS
    
    def test_antisaccade_error_norms_exist(self):
        assert AgeGroup.YOUNG_ADULT in ANTISACCADE_ERROR_NORMS
    
    def test_pursuit_gain_values_reasonable(self):
        norm = PURSUIT_GAIN_NORMS[AgeGroup.YOUNG_ADULT]
        assert 0.8 <= norm.mean <= 1.0
        assert norm.std > 0


class TestNormativeComparison:
    """Test NormativeComparison evaluations."""
    
    def test_default_age_group(self):
        comp = NormativeComparison()
        assert comp.age_group == AgeGroup.YOUNG_ADULT
    
    def test_age_sets_group(self):
        comp = NormativeComparison(age=10)
        assert comp.age_group == AgeGroup.CHILD
    
    def test_evaluate_pursuit_gain_pass(self):
        comp = NormativeComparison(age=25)
        result = comp.evaluate_pursuit_gain(0.92)
        assert result.status == "pass"
        assert result.metric_name == "Pursuit Gain"
    
    def test_evaluate_pursuit_gain_fail(self):
        comp = NormativeComparison(age=25)
        result = comp.evaluate_pursuit_gain(0.5)
        assert result.status == "fail"
    
    def test_evaluate_saccade_latency_pass(self):
        comp = NormativeComparison(age=25)
        result = comp.evaluate_saccade_latency(200)
        assert result.status == "pass"
    
    def test_evaluate_saccade_latency_slow(self):
        comp = NormativeComparison(age=25)
        result = comp.evaluate_saccade_latency(400)
        assert result.status == "fail"
    
    def test_evaluate_antisaccade_error_pass(self):
        comp = NormativeComparison(age=25)
        result = comp.evaluate_antisaccade_error(10)
        assert result.status == "pass"
    
    def test_evaluate_antisaccade_error_high(self):
        comp = NormativeComparison(age=25)
        result = comp.evaluate_antisaccade_error(50)
        assert result.status == "fail"


class TestScreeningResult:
    """Test ScreeningResult dataclass."""
    
    def test_screening_result_fields(self):
        result = ScreeningResult(
            metric_name="Test",
            value=0.9,
            unit="",
            status="pass"
        )
        assert result.metric_name == "Test"
        assert result.value == 0.9
        assert result.status == "pass"


class TestOverallScreening:
    """Test overall screening recommendations."""
    
    def test_all_pass_returns_pass(self):
        comp = NormativeComparison(age=25)
        results = [
            ScreeningResult("A", 1.0, "", "pass"),
            ScreeningResult("B", 1.0, "", "pass"),
        ]
        status, _ = comp.get_overall_screening(results)
        assert status == "PASS"
    
    def test_one_fail_returns_refer(self):
        comp = NormativeComparison(age=25)
        results = [
            ScreeningResult("A", 1.0, "", "pass"),
            ScreeningResult("B", 0.5, "", "fail"),
        ]
        status, _ = comp.get_overall_screening(results)
        assert status == "REFER"
    
    def test_multiple_borderline_returns_monitor(self):
        comp = NormativeComparison(age=25)
        results = [
            ScreeningResult("A", 1.0, "", "borderline"),
            ScreeningResult("B", 1.0, "", "borderline"),
        ]
        status, _ = comp.get_overall_screening(results)
        assert status == "MONITOR"
