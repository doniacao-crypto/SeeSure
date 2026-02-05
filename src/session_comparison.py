"""
Multi-Session Comparison for Eye Movement Assessment.
Compare results from different test sessions side-by-side.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import numpy as np


@dataclass
class ComparisonMetric:
    """A single metric comparison between sessions."""
    name: str
    session1_value: Optional[float]
    session2_value: Optional[float]
    unit: str = ""
    higher_is_better: bool = True
    
    @property
    def difference(self) -> Optional[float]:
        if self.session1_value is None or self.session2_value is None:
            return None
        return self.session2_value - self.session1_value
    
    @property
    def percent_change(self) -> Optional[float]:
        if self.session1_value is None or self.session2_value is None:
            return None
        if self.session1_value == 0:
            return None
        return ((self.session2_value - self.session1_value) / abs(self.session1_value)) * 100
    
    @property
    def improved(self) -> Optional[bool]:
        diff = self.difference
        if diff is None:
            return None
        if self.higher_is_better:
            return diff > 0
        return diff < 0
    
    @property
    def status_symbol(self) -> str:
        improved = self.improved
        if improved is None:
            return "—"
        return "↑" if improved else "↓"


class SessionComparator:
    """Compare two test sessions."""
    
    def __init__(self):
        self.metrics: List[ComparisonMetric] = []
    
    def compare_pursuit_results(self, session1, session2) -> List[ComparisonMetric]:
        """
        Compare two pursuit test results.
        
        Args:
            session1: First (baseline) result
            session2: Second (current) result
            
        Returns:
            List of comparison metrics
        """
        self.metrics = []
        
        # Add common metrics
        self._add_metric("Tracking Ratio", 
            getattr(session1, 'tracking_ratio', None),
            getattr(session2, 'tracking_ratio', None),
            "%", higher_is_better=True)
        
        self._add_metric("Accuracy Score",
            getattr(session1, 'accuracy_score', None),
            getattr(session2, 'accuracy_score', None),
            "/100", higher_is_better=True)
        
        self._add_metric("Smoothness Score",
            getattr(session1, 'smooth_score', None),
            getattr(session2, 'smooth_score', None),
            "/100", higher_is_better=True)
        
        # Clinical metrics
        self._add_metric("Pursuit Gain",
            getattr(session1, 'pursuit_gain', None),
            getattr(session2, 'pursuit_gain', None),
            "", higher_is_better=True)
        
        self._add_metric("Accuracy (degrees)",
            getattr(session1, 'accuracy_degrees', None),
            getattr(session2, 'accuracy_degrees', None),
            "°", higher_is_better=False)
        
        self._add_metric("Smoothness Index",
            getattr(session1, 'smoothness', None),
            getattr(session2, 'smoothness', None),
            "", higher_is_better=True)
        
        self._add_metric("Catch-up Saccades",
            getattr(session1, 'catch_up_saccade_count', None),
            getattr(session2, 'catch_up_saccade_count', None),
            "", higher_is_better=False)
        
        return self.metrics
    
    def compare_saccade_results(self, session1, session2) -> List[ComparisonMetric]:
        """Compare two saccade test results."""
        self.metrics = []
        
        self._add_metric("Mean Latency",
            getattr(session1, 'mean_latency_ms', None),
            getattr(session2, 'mean_latency_ms', None),
            "ms", higher_is_better=False)
        
        self._add_metric("Latency Std Dev",
            getattr(session1, 'std_latency_ms', None),
            getattr(session2, 'std_latency_ms', None),
            "ms", higher_is_better=False)
        
        self._add_metric("Error Rate",
            (getattr(session1, 'error_rate', None) or 0) * 100,
            (getattr(session2, 'error_rate', None) or 0) * 100,
            "%", higher_is_better=False)
        
        self._add_metric("Accuracy (degrees)",
            getattr(session1, 'mean_accuracy_deg', None),
            getattr(session2, 'mean_accuracy_deg', None),
            "°", higher_is_better=False)
        
        return self.metrics
    
    def _add_metric(self, name: str, val1: Any, val2: Any, unit: str, higher_is_better: bool):
        """Add a metric to the comparison."""
        self.metrics.append(ComparisonMetric(
            name=name,
            session1_value=float(val1) if val1 is not None else None,
            session2_value=float(val2) if val2 is not None else None,
            unit=unit,
            higher_is_better=higher_is_better
        ))
    
    def generate_comparison_report(self, session1_date: str, session2_date: str) -> str:
        """Generate text comparison report."""
        lines = []
        lines.append("=" * 70)
        lines.append("SESSION COMPARISON REPORT")
        lines.append("=" * 70)
        lines.append(f"Baseline: {session1_date}")
        lines.append(f"Current:  {session2_date}")
        lines.append("")
        lines.append("-" * 70)
        lines.append(f"{'Metric':<25} {'Baseline':>12} {'Current':>12} {'Change':>12} {'Status':>6}")
        lines.append("-" * 70)
        
        improved_count = 0
        declined_count = 0
        
        for m in self.metrics:
            val1 = f"{m.session1_value:.2f}{m.unit}" if m.session1_value is not None else "N/A"
            val2 = f"{m.session2_value:.2f}{m.unit}" if m.session2_value is not None else "N/A"
            
            if m.percent_change is not None:
                change = f"{m.percent_change:+.1f}%"
            else:
                change = "—"
            
            lines.append(f"{m.name:<25} {val1:>12} {val2:>12} {change:>12} {m.status_symbol:>6}")
            
            if m.improved is True:
                improved_count += 1
            elif m.improved is False:
                declined_count += 1
        
        lines.append("-" * 70)
        lines.append("")
        lines.append("SUMMARY")
        lines.append(f"  Improved: {improved_count} metrics")
        lines.append(f"  Declined: {declined_count} metrics")
        
        if improved_count > declined_count:
            lines.append("  Overall: IMPROVEMENT ↑")
        elif declined_count > improved_count:
            lines.append("  Overall: DECLINE ↓")
        else:
            lines.append("  Overall: NO SIGNIFICANT CHANGE")
        
        return "\n".join(lines)


def compare_sessions(session1, session2, test_type: str) -> Tuple[List[ComparisonMetric], str]:
    """
    Compare two sessions and generate report.
    
    Args:
        session1: First session result
        session2: Second session result
        test_type: Type of test ("pursuit" or "saccade")
        
    Returns:
        Tuple of (metrics list, report text)
    """
    comparator = SessionComparator()
    
    if test_type == "pursuit":
        metrics = comparator.compare_pursuit_results(session1, session2)
    elif test_type == "saccade":
        metrics = comparator.compare_saccade_results(session1, session2)
    else:
        return [], "Unknown test type"
    
    report = comparator.generate_comparison_report(
        str(getattr(session1, 'start_time', 'Session 1')),
        str(getattr(session2, 'start_time', 'Session 2'))
    )
    
    return metrics, report
