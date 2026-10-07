"""
Saccade Testing Module for Eye Movement Assessment.
Implements pro-saccade and anti-saccade testing protocols.
"""

import time
import numpy as np
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import random


class SaccadeTestType(Enum):
    """Types of saccade tests."""
    PRO_SACCADE = "pro_saccade"      # Look toward the target
    ANTI_SACCADE = "anti_saccade"    # Look away from the target


class TrialPhase(Enum):
    """Phases of a saccade trial."""
    FIXATION = "fixation"     # Central fixation
    GAP = "gap"               # Optional gap (blank screen)
    TARGET = "target"         # Target presentation
    RESPONSE = "response"     # Response window
    FEEDBACK = "feedback"     # Optional feedback


@dataclass
class SaccadeTrialConfig:
    """Configuration for a single saccade trial."""
    target_eccentricity_deg: float = 10.0  # Target distance in degrees
    target_direction: str = "right"        # "left" or "right"
    fixation_duration_ms: float = 1000.0   # Fixation period
    gap_duration_ms: float = 200.0         # Gap period (0 = no gap)
    target_duration_ms: float = 1000.0     # Target presentation
    response_window_ms: float = 800.0      # Max time to respond


@dataclass
class SaccadeTrialResult:
    """Result of a single saccade trial."""
    trial_number: int
    test_type: SaccadeTestType
    target_direction: str
    target_eccentricity_deg: float
    
    # Timing metrics
    saccade_latency_ms: Optional[float] = None      # Time from target onset to saccade
    saccade_duration_ms: Optional[float] = None     # Duration of saccade
    
    # Accuracy metrics
    saccade_amplitude_deg: Optional[float] = None   # Size of saccade
    saccade_accuracy_deg: Optional[float] = None    # Error from target
    peak_velocity_deg_s: Optional[float] = None     # Peak velocity
    
    # Error classification
    direction_correct: bool = True                   # Correct direction?
    anticipatory_error: bool = False                 # Saccade before target (<80ms)?
    express_saccade: bool = False                    # Very fast (80-130ms)?
    
    # Raw data
    gaze_x: List[float] = field(default_factory=list)
    gaze_y: List[float] = field(default_factory=list)
    timestamps: List[float] = field(default_factory=list)


@dataclass
class SaccadeTestConfig:
    """Configuration for a complete saccade test."""
    test_type: SaccadeTestType = SaccadeTestType.PRO_SACCADE
    num_trials: int = 20
    eccentricities_deg: List[float] = field(default_factory=lambda: [10.0])
    fixation_duration_ms: float = 1000.0
    gap_duration_ms: float = 200.0          # 0 = overlap paradigm
    target_duration_ms: float = 1000.0
    response_window_ms: float = 800.0
    randomize_direction: bool = True
    randomize_timing: bool = True           # ±200ms jitter on fixation
    show_feedback: bool = False
    
    # Screen configuration
    screen_width_px: int = 1920
    screen_height_px: int = 1080
    viewing_distance_cm: float = 60.0
    screen_width_cm: float = 52.0           # Physical screen width


@dataclass
class SaccadeTestResult:
    """Complete saccade test results."""
    test_type: SaccadeTestType
    trials: List[SaccadeTrialResult] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    
    @property
    def num_trials(self) -> int:
        return len(self.trials)
    
    @property
    def num_correct(self) -> int:
        return sum(1 for t in self.trials if t.direction_correct)
    
    @property
    def error_rate(self) -> float:
        """Proportion of direction errors."""
        if not self.trials:
            return 0.0
        return 1.0 - (self.num_correct / self.num_trials)
    
    @property
    def mean_latency_ms(self) -> Optional[float]:
        """Mean saccade latency for correct trials."""
        latencies = [t.saccade_latency_ms for t in self.trials 
                    if t.direction_correct and t.saccade_latency_ms is not None]
        return np.mean(latencies) if latencies else None
    
    @property
    def std_latency_ms(self) -> Optional[float]:
        """Standard deviation of saccade latency."""
        latencies = [t.saccade_latency_ms for t in self.trials 
                    if t.direction_correct and t.saccade_latency_ms is not None]
        return np.std(latencies) if latencies else None
    
    @property
    def mean_accuracy_deg(self) -> Optional[float]:
        """Mean saccade accuracy (error from target)."""
        accuracies = [t.saccade_accuracy_deg for t in self.trials 
                     if t.direction_correct and t.saccade_accuracy_deg is not None]
        return np.mean(accuracies) if accuracies else None
    
    @property
    def mean_peak_velocity(self) -> Optional[float]:
        """Mean peak velocity."""
        velocities = [t.peak_velocity_deg_s for t in self.trials 
                     if t.peak_velocity_deg_s is not None]
        return np.mean(velocities) if velocities else None
    
    @property
    def anticipatory_rate(self) -> float:
        """Rate of anticipatory saccades (<80ms)."""
        if not self.trials:
            return 0.0
        return sum(1 for t in self.trials if t.anticipatory_error) / self.num_trials
    
    @property 
    def express_saccade_rate(self) -> float:
        """Rate of express saccades (80-130ms)."""
        if not self.trials:
            return 0.0
        return sum(1 for t in self.trials if t.express_saccade) / self.num_trials


class SaccadeTest:
    """
    Manages saccade testing protocol.
    
    Implements gap/overlap paradigms for pro-saccade and anti-saccade tests.
    """
    
    def __init__(self, config: SaccadeTestConfig):
        """
        Initialize saccade test.
        
        Args:
            config: Test configuration
        """
        self.config = config
        self.result = SaccadeTestResult(test_type=config.test_type)
        
        # Calculate pixels per degree
        screen_distance_px = (config.screen_width_px / config.screen_width_cm) * config.viewing_distance_cm
        self.px_per_deg = screen_distance_px * np.tan(np.radians(1))
        
        # Screen center
        self.center_x = config.screen_width_px // 2
        self.center_y = config.screen_height_px // 2
        
        # Generate trial sequence
        self._trial_configs: List[SaccadeTrialConfig] = []
        self._generate_trials()
        
        # State
        self._current_trial_index = 0
        self._current_phase = TrialPhase.FIXATION
        self._phase_start_time = 0.0
        self._trial_start_time = 0.0
        self._target_onset_time = 0.0
        self._current_result: Optional[SaccadeTrialResult] = None
        
        self.is_running = False
        self._collecting_response = False
        self.on_trial_start = None  # Optional callback for filter reset

    def _generate_trials(self):
        """Generate the sequence of trials."""
        directions = ["left", "right"]
        
        for trial_num in range(self.config.num_trials):
            # Select eccentricity
            eccentricity = random.choice(self.config.eccentricities_deg)
            
            # Select direction
            if self.config.randomize_direction:
                direction = random.choice(directions)
            else:
                direction = directions[trial_num % 2]
            
            # Timing jitter
            fixation_jitter = 0.0
            if self.config.randomize_timing:
                fixation_jitter = random.uniform(-200, 200)
            
            trial_config = SaccadeTrialConfig(
                target_eccentricity_deg=eccentricity,
                target_direction=direction,
                fixation_duration_ms=self.config.fixation_duration_ms + fixation_jitter,
                gap_duration_ms=self.config.gap_duration_ms,
                target_duration_ms=self.config.target_duration_ms,
                response_window_ms=self.config.response_window_ms
            )
            self._trial_configs.append(trial_config)
    
    def start(self):
        """Start the test."""
        self.is_running = True
        self.result.start_time = time.time()
        self._current_trial_index = 0
        self._start_trial()
    
    def stop(self):
        """Stop the test."""
        self.is_running = False
        self.result.end_time = time.time()
    
    def _start_trial(self):
        """Start a new trial."""
        if self.on_trial_start:
            self.on_trial_start()

        if self._current_trial_index >= len(self._trial_configs):
            self.stop()
            return
        
        config = self._trial_configs[self._current_trial_index]
        self._current_result = SaccadeTrialResult(
            trial_number=self._current_trial_index + 1,
            test_type=self.config.test_type,
            target_direction=config.target_direction,
            target_eccentricity_deg=config.target_eccentricity_deg
        )
        
        self._current_phase = TrialPhase.FIXATION
        self._phase_start_time = time.time()
        self._trial_start_time = time.time()
        self._collecting_response = False
    
    def _advance_phase(self):
        """Advance to next trial phase."""
        config = self._trial_configs[self._current_trial_index]
        
        if self._current_phase == TrialPhase.FIXATION:
            if config.gap_duration_ms > 0:
                self._current_phase = TrialPhase.GAP
            else:
                self._current_phase = TrialPhase.TARGET
                self._target_onset_time = time.time()
                self._collecting_response = True
        elif self._current_phase == TrialPhase.GAP:
            self._current_phase = TrialPhase.TARGET
            self._target_onset_time = time.time()
            self._collecting_response = True
        elif self._current_phase == TrialPhase.TARGET:
            self._current_phase = TrialPhase.RESPONSE
        elif self._current_phase == TrialPhase.RESPONSE:
            # End trial
            self._end_trial()
            return
        
        self._phase_start_time = time.time()
    
    def _end_trial(self):
        """End current trial and move to next."""
        if self._current_result:
            # Analyze trial data
            self._analyze_trial()
            self.result.trials.append(self._current_result)
        
        self._current_trial_index += 1
        if self._current_trial_index < len(self._trial_configs):
            self._start_trial()
        else:
            self.stop()
    
    def _analyze_trial(self):
        """Analyze the current trial's gaze data."""
        if not self._current_result or not self._current_result.gaze_x:
            return
        
        config = self._trial_configs[self._current_trial_index]
        result = self._current_result
        
        gaze_x = np.array(result.gaze_x)
        gaze_y = np.array(result.gaze_y)
        timestamps = np.array(result.timestamps)
        
        # Find saccade onset using velocity threshold
        velocities = self._calculate_velocities(gaze_x, gaze_y, timestamps)
        saccade_threshold = 30.0  # deg/s
        
        saccade_onset_idx = None
        for i, v in enumerate(velocities):
            if v > saccade_threshold:
                saccade_onset_idx = i
                break
        
        if saccade_onset_idx is not None:
            # Calculate latency
            saccade_onset_time = timestamps[saccade_onset_idx]
            result.saccade_latency_ms = (saccade_onset_time - self._target_onset_time) * 1000
            
            # Classify latency
            if result.saccade_latency_ms < 80:
                result.anticipatory_error = True
            elif result.saccade_latency_ms < 130:
                result.express_saccade = True
            
            # Find saccade end
            saccade_end_idx = saccade_onset_idx
            for i in range(saccade_onset_idx, len(velocities)):
                if velocities[i] < saccade_threshold:
                    saccade_end_idx = i
                    break
            else:
                saccade_end_idx = len(velocities) - 1
            
            # Saccade duration
            result.saccade_duration_ms = (timestamps[saccade_end_idx] - timestamps[saccade_onset_idx]) * 1000
            
            # Peak velocity
            result.peak_velocity_deg_s = float(np.max(velocities[saccade_onset_idx:saccade_end_idx+1]))
            
            # Saccade amplitude and accuracy
            start_x = gaze_x[saccade_onset_idx]
            end_x = gaze_x[saccade_end_idx]
            amplitude_px = end_x - start_x
            result.saccade_amplitude_deg = abs(amplitude_px) / self.px_per_deg
            
            # Target position
            target_x = self._get_target_x()
            expected_direction = 1 if config.target_direction == "right" else -1
            
            # For anti-saccade, correct direction is opposite
            if self.config.test_type == SaccadeTestType.ANTI_SACCADE:
                expected_direction *= -1
            
            # Check direction correctness
            actual_direction = 1 if amplitude_px > 0 else -1
            result.direction_correct = actual_direction == expected_direction
            
            # Accuracy (error from expected target)
            expected_amplitude_px = expected_direction * config.target_eccentricity_deg * self.px_per_deg
            accuracy_error_px = abs(amplitude_px - expected_amplitude_px)
            result.saccade_accuracy_deg = accuracy_error_px / self.px_per_deg
    
    def _calculate_velocities(self, x: np.ndarray, y: np.ndarray, t: np.ndarray) -> np.ndarray:
        """Calculate instantaneous velocity in degrees/second."""
        if len(x) < 2:
            return np.array([0.0])
        
        dx = np.diff(x)
        dy = np.diff(y)
        dt = np.diff(t)
        dt = np.maximum(dt, 1e-6)  # Avoid division by zero
        
        # Convert pixels to degrees and calculate velocity
        velocity_px = np.sqrt(dx**2 + dy**2) / dt
        velocity_deg = velocity_px / self.px_per_deg
        
        return velocity_deg
    
    def _get_target_x(self) -> int:
        """Get target X position based on current trial config."""
        config = self._trial_configs[self._current_trial_index]
        offset_px = int(config.target_eccentricity_deg * self.px_per_deg)
        
        if config.target_direction == "right":
            return self.center_x + offset_px
        else:
            return self.center_x - offset_px
    
    def update(self, gaze_x: Optional[float], gaze_y: Optional[float], timestamp: float):
        """
        Update test with new gaze data.
        
        Args:
            gaze_x: Current gaze X position (pixels)
            gaze_y: Current gaze Y position (pixels)
            timestamp: Current timestamp
        """
        if not self.is_running:
            return
        
        config = self._trial_configs[self._current_trial_index]
        elapsed_ms = (time.time() - self._phase_start_time) * 1000
        
        # Record gaze data during response collection
        if self._collecting_response and gaze_x is not None and gaze_y is not None:
            self._current_result.gaze_x.append(gaze_x)
            self._current_result.gaze_y.append(gaze_y)
            self._current_result.timestamps.append(timestamp)
        
        # Check phase transitions
        if self._current_phase == TrialPhase.FIXATION:
            if elapsed_ms >= config.fixation_duration_ms:
                self._advance_phase()
        elif self._current_phase == TrialPhase.GAP:
            if elapsed_ms >= config.gap_duration_ms:
                self._advance_phase()
        elif self._current_phase == TrialPhase.TARGET:
            if elapsed_ms >= config.target_duration_ms:
                self._advance_phase()
        elif self._current_phase == TrialPhase.RESPONSE:
            if elapsed_ms >= config.response_window_ms:
                self._advance_phase()
    
    def get_display_state(self) -> dict:
        """
        Get current display state for rendering.
        
        Returns:
            Dict with fixation_visible, target_visible, target_x, target_y
        """
        state = {
            "fixation_visible": False,
            "target_visible": False,
            "target_x": self.center_x,
            "target_y": self.center_y,
            "phase": self._current_phase.value,
            "trial_number": self._current_trial_index + 1,
            "total_trials": len(self._trial_configs)
        }
        
        if not self.is_running:
            return state
        
        if self._current_phase == TrialPhase.FIXATION:
            state["fixation_visible"] = True
        elif self._current_phase == TrialPhase.GAP:
            pass  # Nothing visible
        elif self._current_phase in [TrialPhase.TARGET, TrialPhase.RESPONSE]:
            state["target_visible"] = True
            state["target_x"] = self._get_target_x()
            state["target_y"] = self.center_y
        
        return state


def generate_saccade_report(result: SaccadeTestResult) -> str:
    """Generate a text report from saccade test results."""
    report = []
    report.append("╔" + "═" * 58 + "╗")
    report.append("║" + " SACCADE TEST REPORT ".center(58) + "║")
    report.append("╚" + "═" * 58 + "╝")
    report.append("")
    report.append(f"  📋 Test Type: {result.test_type.value}")
    report.append(f"  📊 Total Trials: {result.num_trials}")
    report.append(f"  ✅ Correct: {result.num_correct} ({(1-result.error_rate)*100:.1f}%)")
    report.append("")
    report.append("─" * 60)
    report.append("📈 LATENCY METRICS")
    report.append("─" * 60)
    
    if result.mean_latency_ms:
        report.append(f"  Mean Latency: {result.mean_latency_ms:.1f} ms")
        report.append(f"  Std Latency: {result.std_latency_ms:.1f} ms")
        report.append(f"  (Normal pro-saccade: 150-250 ms)")
    else:
        report.append("  Latency: N/A")
    
    report.append("")
    report.append("─" * 60)
    report.append("🎯 ACCURACY METRICS")
    report.append("─" * 60)
    
    if result.mean_accuracy_deg:
        report.append(f"  Mean Error: {result.mean_accuracy_deg:.2f}°")
        report.append(f"  (Normal: <2°)")
    
    if result.mean_peak_velocity:
        report.append(f"  Mean Peak Velocity: {result.mean_peak_velocity:.1f} deg/s")
        report.append(f"  (Normal: 300-500 deg/s for 10° saccade)")
    
    report.append("")
    report.append("─" * 60)
    report.append("⚠️ ERROR ANALYSIS")
    report.append("─" * 60)
    report.append(f"  Direction Errors: {result.error_rate*100:.1f}%")
    report.append(f"  Anticipatory (<80ms): {result.anticipatory_rate*100:.1f}%")
    report.append(f"  Express Saccades (80-130ms): {result.express_saccade_rate*100:.1f}%")
    
    if result.test_type == SaccadeTestType.ANTI_SACCADE:
        report.append("")
        if result.error_rate > 0.30:
            report.append("  ❌ High anti-saccade error rate (>30%) - may indicate executive dysfunction")
        elif result.error_rate > 0.15:
            report.append("  ⚠️ Elevated anti-saccade error rate (15-30%)")
        else:
            report.append("  ✅ Anti-saccade error rate within normal limits (<15%)")
    
    report.append("")
    report.append("─" * 60)
    
    return "\n".join(report)
