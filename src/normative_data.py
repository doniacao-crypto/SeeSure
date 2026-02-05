"""
Normative Data for Eye Movement Assessment.
Provides age-matched reference values for clinical metrics.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Tuple
from enum import Enum


class AgeGroup(Enum):
    """Age groups for normative data."""
    CHILD = "child"          # 6-12 years
    ADOLESCENT = "adolescent"  # 13-17 years
    YOUNG_ADULT = "young_adult"  # 18-39 years
    MIDDLE_ADULT = "middle_adult"  # 40-59 years
    OLDER_ADULT = "older_adult"  # 60+ years


@dataclass
class NormativeRange:
    """Normative range for a metric."""
    mean: float
    std: float
    lower_normal: float  # 5th percentile
    upper_normal: float  # 95th percentile
    unit: str = ""
    source: str = ""
    
    def get_percentile(self, value: float) -> float:
        """Estimate percentile for a value (assumes normal distribution)."""
        import scipy.stats as stats
        z = (value - self.mean) / self.std if self.std > 0 else 0
        return stats.norm.cdf(z) * 100
    
    def is_normal(self, value: float) -> bool:
        """Check if value is within normal range."""
        return self.lower_normal <= value <= self.upper_normal
    
    def get_status(self, value: float) -> str:
        """Get clinical status for a value."""
        if self.is_normal(value):
            return "normal"
        percentile = self.get_percentile(value)
        if percentile < 5:
            return "low"
        elif percentile > 95:
            return "high"
        return "borderline"


# Normative data from clinical literature
# Sources: Various peer-reviewed studies on eye movements

PURSUIT_GAIN_NORMS: Dict[AgeGroup, NormativeRange] = {
    AgeGroup.CHILD: NormativeRange(0.85, 0.10, 0.70, 1.00, "", "Ross et al., 2000"),
    AgeGroup.ADOLESCENT: NormativeRange(0.90, 0.08, 0.75, 1.00, "", "Munoz et al., 1998"),
    AgeGroup.YOUNG_ADULT: NormativeRange(0.95, 0.05, 0.85, 1.00, "", "Leigh & Zee, 2015"),
    AgeGroup.MIDDLE_ADULT: NormativeRange(0.92, 0.06, 0.80, 1.00, "", "Leigh & Zee, 2015"),
    AgeGroup.OLDER_ADULT: NormativeRange(0.85, 0.10, 0.70, 0.98, "", "Sharpe & Zackon, 1987"),
}

SACCADE_LATENCY_NORMS: Dict[AgeGroup, NormativeRange] = {
    AgeGroup.CHILD: NormativeRange(250, 50, 170, 350, "ms", "Munoz et al., 1998"),
    AgeGroup.ADOLESCENT: NormativeRange(220, 40, 150, 300, "ms", "Munoz et al., 1998"),
    AgeGroup.YOUNG_ADULT: NormativeRange(200, 30, 150, 260, "ms", "Leigh & Zee, 2015"),
    AgeGroup.MIDDLE_ADULT: NormativeRange(210, 35, 150, 280, "ms", "Leigh & Zee, 2015"),
    AgeGroup.OLDER_ADULT: NormativeRange(240, 45, 170, 330, "ms", "Abel et al., 1983"),
}

ANTISACCADE_ERROR_NORMS: Dict[AgeGroup, NormativeRange] = {
    AgeGroup.CHILD: NormativeRange(30, 15, 10, 55, "%", "Munoz et al., 1998"),
    AgeGroup.ADOLESCENT: NormativeRange(20, 12, 5, 40, "%", "Munoz et al., 1998"),
    AgeGroup.YOUNG_ADULT: NormativeRange(12, 8, 2, 25, "%", "Evdokimidis et al., 2002"),
    AgeGroup.MIDDLE_ADULT: NormativeRange(15, 10, 3, 30, "%", "Evdokimidis et al., 2002"),
    AgeGroup.OLDER_ADULT: NormativeRange(25, 12, 8, 45, "%", "Olincy et al., 1997"),
}

FIXATION_BCEA_NORMS: Dict[AgeGroup, NormativeRange] = {
    AgeGroup.YOUNG_ADULT: NormativeRange(0.5, 0.3, 0.1, 1.2, "deg²", "Crossland et al., 2004"),
    AgeGroup.MIDDLE_ADULT: NormativeRange(0.6, 0.35, 0.15, 1.4, "deg²", "Crossland et al., 2004"),
    AgeGroup.OLDER_ADULT: NormativeRange(0.8, 0.4, 0.2, 1.8, "deg²", "Crossland et al., 2004"),
}


def get_age_group(age: int) -> AgeGroup:
    """Determine age group from age in years."""
    if age < 13:
        return AgeGroup.CHILD
    elif age < 18:
        return AgeGroup.ADOLESCENT
    elif age < 40:
        return AgeGroup.YOUNG_ADULT
    elif age < 60:
        return AgeGroup.MIDDLE_ADULT
    else:
        return AgeGroup.OLDER_ADULT


@dataclass
class ScreeningResult:
    """Result of pass/fail screening."""
    metric_name: str
    value: float
    unit: str
    status: str  # "pass", "fail", "borderline"
    percentile: Optional[float] = None
    reference_range: str = ""
    interpretation: str = ""


class NormativeComparison:
    """Compare results against normative data."""
    
    def __init__(self, age: Optional[int] = None):
        """
        Initialize with patient age.
        
        Args:
            age: Patient age in years (None for adult defaults)
        """
        self.age = age
        self.age_group = get_age_group(age) if age else AgeGroup.YOUNG_ADULT
    
    def evaluate_pursuit_gain(self, gain: float) -> ScreeningResult:
        """Evaluate pursuit gain against norms."""
        norm = PURSUIT_GAIN_NORMS.get(self.age_group)
        if not norm:
            norm = PURSUIT_GAIN_NORMS[AgeGroup.YOUNG_ADULT]
        
        percentile = norm.get_percentile(gain)
        status = "pass" if norm.is_normal(gain) else ("borderline" if 0.7 <= gain < norm.lower_normal else "fail")
        
        return ScreeningResult(
            metric_name="Pursuit Gain",
            value=gain,
            unit="",
            status=status,
            percentile=percentile,
            reference_range=f"{norm.lower_normal:.2f}-{norm.upper_normal:.2f}",
            interpretation=self._get_gain_interpretation(gain, status)
        )
    
    def evaluate_saccade_latency(self, latency_ms: float) -> ScreeningResult:
        """Evaluate saccade latency against norms."""
        norm = SACCADE_LATENCY_NORMS.get(self.age_group)
        if not norm:
            norm = SACCADE_LATENCY_NORMS[AgeGroup.YOUNG_ADULT]
        
        percentile = norm.get_percentile(latency_ms)
        status_raw = norm.get_status(latency_ms)
        status = "pass" if status_raw == "normal" else ("borderline" if status_raw in ["low", "borderline"] else "fail")
        
        return ScreeningResult(
            metric_name="Saccade Latency",
            value=latency_ms,
            unit="ms",
            status=status,
            percentile=percentile,
            reference_range=f"{norm.lower_normal:.0f}-{norm.upper_normal:.0f} ms",
            interpretation=self._get_latency_interpretation(latency_ms, status)
        )
    
    def evaluate_antisaccade_error(self, error_rate: float) -> ScreeningResult:
        """Evaluate anti-saccade error rate against norms."""
        norm = ANTISACCADE_ERROR_NORMS.get(self.age_group)
        if not norm:
            norm = ANTISACCADE_ERROR_NORMS[AgeGroup.YOUNG_ADULT]
        
        # For error rate, lower is better
        percentile = 100 - norm.get_percentile(error_rate)  # Invert
        status = "pass" if error_rate <= norm.mean else ("borderline" if error_rate <= norm.upper_normal else "fail")
        
        return ScreeningResult(
            metric_name="Anti-saccade Errors",
            value=error_rate,
            unit="%",
            status=status,
            percentile=percentile,
            reference_range=f"<{norm.upper_normal:.0f}%",
            interpretation=self._get_error_interpretation(error_rate, status)
        )
    
    def _get_gain_interpretation(self, gain: float, status: str) -> str:
        if status == "pass":
            return "Pursuit gain within normal limits"
        elif status == "borderline":
            return "Pursuit gain slightly reduced - monitor"
        else:
            return "Pursuit gain significantly reduced - recommend evaluation"
    
    def _get_latency_interpretation(self, latency: float, status: str) -> str:
        if status == "pass":
            return "Saccade latency within normal limits"
        elif latency < 100:
            return "Anticipatory saccades noted"
        else:
            return "Saccade latency prolonged - recommend evaluation"
    
    def _get_error_interpretation(self, rate: float, status: str) -> str:
        if status == "pass":
            return "Inhibitory control within normal limits"
        elif status == "borderline":
            return "Mild difficulty with inhibitory control"
        else:
            return "Significant inhibitory control difficulties - may indicate executive dysfunction"
    
    def get_overall_screening(self, results: list) -> Tuple[str, str]:
        """
        Get overall screening result.
        
        Args:
            results: List of ScreeningResult objects
            
        Returns:
            Tuple of (status, interpretation)
        """
        fail_count = sum(1 for r in results if r.status == "fail")
        borderline_count = sum(1 for r in results if r.status == "borderline")
        
        if fail_count > 0:
            return ("REFER", f"Abnormal findings in {fail_count} metric(s) - recommend specialist referral")
        elif borderline_count > 1:
            return ("MONITOR", f"Borderline findings in {borderline_count} metrics - recommend follow-up")
        elif borderline_count == 1:
            return ("PASS*", "Passed with one borderline finding - continue routine monitoring")
        else:
            return ("PASS", "All metrics within normal limits")
