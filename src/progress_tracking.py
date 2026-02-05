"""
Longitudinal Progress Tracking for Eye Movement Assessment.
Tracks patient progress over multiple sessions.
"""

import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import numpy as np


@dataclass
class SessionMetrics:
    """Metrics from a single test session."""
    session_id: str
    date: str
    test_type: str
    
    # Common metrics
    accuracy_score: Optional[float] = None
    tracking_ratio: Optional[float] = None
    
    # Pursuit metrics
    pursuit_gain: Optional[float] = None
    smoothness: Optional[float] = None
    accuracy_degrees: Optional[float] = None
    
    # Saccade metrics
    saccade_latency_ms: Optional[float] = None
    error_rate: Optional[float] = None
    
    # Validation metrics
    validation_accuracy: Optional[float] = None


@dataclass
class ProgressReport:
    """Progress report for a patient."""
    patient_id: str
    sessions: List[SessionMetrics] = field(default_factory=list)
    
    def add_session(self, metrics: SessionMetrics):
        """Add a session to the progress report."""
        self.sessions.append(metrics)
        self.sessions.sort(key=lambda s: s.date)
    
    @property
    def num_sessions(self) -> int:
        return len(self.sessions)
    
    @property
    def date_range(self) -> Optional[tuple]:
        """Get date range of sessions."""
        if not self.sessions:
            return None
        return (self.sessions[0].date, self.sessions[-1].date)
    
    def get_metric_trend(self, metric_name: str) -> List[tuple]:
        """
        Get trend data for a specific metric.
        
        Args:
            metric_name: Name of metric to track
            
        Returns:
            List of (date, value) tuples
        """
        trend = []
        for session in self.sessions:
            value = getattr(session, metric_name, None)
            if value is not None:
                trend.append((session.date, value))
        return trend
    
    def calculate_improvement(self, metric_name: str, higher_is_better: bool = True) -> Optional[dict]:
        """
        Calculate improvement in a metric.
        
        Args:
            metric_name: Metric to analyze
            higher_is_better: Whether higher values indicate improvement
            
        Returns:
            Dict with baseline, current, change, and percent_change
        """
        trend = self.get_metric_trend(metric_name)
        if len(trend) < 2:
            return None
        
        baseline = trend[0][1]
        current = trend[-1][1]
        change = current - baseline
        
        if baseline != 0:
            percent_change = (change / baseline) * 100
        else:
            percent_change = 0
        
        if not higher_is_better:
            # Invert for metrics where lower is better
            percent_change = -percent_change
            improvement = change < 0
        else:
            improvement = change > 0
        
        return {
            "baseline": baseline,
            "current": current,
            "change": change,
            "percent_change": percent_change,
            "improved": improvement,
            "num_sessions": len(trend)
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of progress across all metrics."""
        summary = {
            "patient_id": self.patient_id,
            "num_sessions": self.num_sessions,
            "date_range": self.date_range,
            "metrics": {}
        }
        
        # Track key metrics
        metrics_config = [
            ("pursuit_gain", True),
            ("accuracy_degrees", False),  # Lower is better
            ("smoothness", True),
            ("saccade_latency_ms", False),  # Lower is better for latency
            ("error_rate", False),  # Lower is better
        ]
        
        for metric_name, higher_better in metrics_config:
            improvement = self.calculate_improvement(metric_name, higher_better)
            if improvement:
                summary["metrics"][metric_name] = improvement
        
        return summary


class ProgressTracker:
    """Tracks and analyzes patient progress over time."""
    
    def __init__(self, data_dir: str = "data/progress"):
        """Initialize progress tracker."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def record_session(self, patient_id: str, result, test_type: str) -> str:
        """
        Record a test session for a patient.
        
        Args:
            patient_id: Patient ID
            result: Test result object
            test_type: Type of test ("pursuit", "saccade", "validation")
            
        Returns:
            Session ID
        """
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        metrics = SessionMetrics(
            session_id=session_id,
            date=datetime.now().isoformat(),
            test_type=test_type
        )
        
        # Extract metrics based on test type
        if test_type == "pursuit":
            metrics.accuracy_score = getattr(result, 'accuracy_score', None)
            metrics.tracking_ratio = getattr(result, 'tracking_ratio', None)
            metrics.pursuit_gain = getattr(result, 'pursuit_gain', None)
            metrics.smoothness = getattr(result, 'smoothness', None)
            metrics.accuracy_degrees = getattr(result, 'accuracy_degrees', None)
        elif test_type == "saccade":
            metrics.saccade_latency_ms = getattr(result, 'mean_latency_ms', None)
            metrics.error_rate = getattr(result, 'error_rate', None)
        elif test_type == "validation":
            metrics.validation_accuracy = getattr(result, 'accuracy_degrees', None)
        
        # Load or create progress report
        report = self.get_progress(patient_id)
        report.add_session(metrics)
        
        # Save
        self._save_progress(patient_id, report)
        
        return session_id
    
    def get_progress(self, patient_id: str) -> ProgressReport:
        """Get progress report for a patient."""
        filepath = self.data_dir / f"{patient_id}.json"
        
        if filepath.exists():
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            sessions = [SessionMetrics(**s) for s in data.get("sessions", [])]
            return ProgressReport(patient_id=patient_id, sessions=sessions)
        
        return ProgressReport(patient_id=patient_id)
    
    def _save_progress(self, patient_id: str, report: ProgressReport):
        """Save progress report to disk."""
        filepath = self.data_dir / f"{patient_id}.json"
        
        data = {
            "patient_id": patient_id,
            "sessions": [
                {
                    "session_id": s.session_id,
                    "date": s.date,
                    "test_type": s.test_type,
                    "accuracy_score": s.accuracy_score,
                    "tracking_ratio": s.tracking_ratio,
                    "pursuit_gain": s.pursuit_gain,
                    "smoothness": s.smoothness,
                    "accuracy_degrees": s.accuracy_degrees,
                    "saccade_latency_ms": s.saccade_latency_ms,
                    "error_rate": s.error_rate,
                    "validation_accuracy": s.validation_accuracy
                }
                for s in report.sessions
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def generate_progress_text(self, patient_id: str) -> str:
        """Generate text progress report."""
        report = self.get_progress(patient_id)
        summary = report.get_summary()
        
        lines = []
        lines.append("=" * 60)
        lines.append("PROGRESS REPORT")
        lines.append("=" * 60)
        lines.append(f"Patient ID: {patient_id}")
        lines.append(f"Sessions: {summary['num_sessions']}")
        
        if summary['date_range']:
            lines.append(f"Period: {summary['date_range'][0][:10]} to {summary['date_range'][1][:10]}")
        
        lines.append("")
        lines.append("-" * 60)
        lines.append("PROGRESS SUMMARY")
        lines.append("-" * 60)
        
        metric_labels = {
            "pursuit_gain": "Pursuit Gain",
            "accuracy_degrees": "Tracking Accuracy",
            "smoothness": "Smoothness",
            "saccade_latency_ms": "Saccade Latency",
            "error_rate": "Error Rate"
        }
        
        for metric_name, data in summary.get("metrics", {}).items():
            label = metric_labels.get(metric_name, metric_name)
            status = "↑" if data["improved"] else "↓"
            lines.append(f"  {label}: {data['baseline']:.2f} → {data['current']:.2f} ({data['percent_change']:+.1f}%) {status}")
        
        if not summary.get("metrics"):
            lines.append("  Insufficient data for progress analysis")
        
        return "\n".join(lines)
