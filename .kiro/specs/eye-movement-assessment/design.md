# Technical Design Document

## Eye Movement Assessment System

### Version: 1.0

### Status: Draft

### Last Updated: 2025-12-18

---

## 1. Architecture Overview

### 1.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PyQt6 GUI Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  MainWindow │  │  Calibration │  │      Test Widgets       │ │
│  │             │  │    Widget    │  │ (Pursuit/Saccade/Fix)   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Application Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Profile   │  │    Test     │  │      Reporting          │ │
│  │   Manager   │  │ Orchestrator│  │      Engine             │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Core Layer                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ EyeTracker  │  │    Gaze     │  │       Metrics           │ │
│  │  (MediaPipe)│  │  Estimator  │  │      Calculator         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Test Modules                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Smooth    │  │   Saccade   │  │       Fixation          │ │
│  │   Pursuit   │  │    Test     │  │       Stability         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Output Layer                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Visualization│ │    Export   │  │       Storage           │ │
│  │   (Plots)   │  │  (CSV/PDF)  │  │      (JSON/SQLite)      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Module Dependencies

```
main_app.py
├── eye_tracker.py
├── gaze_estimator.py
├── smooth_pursuit_test.py
├── saccade_test.py (NEW)
├── fixation_test.py (NEW)
├── metrics.py (NEW)
├── visualization.py (NEW)
├── export.py (NEW)
└── profile_manager.py (NEW)
```

---

## 2. Data Models

### 2.1 Core Data Classes

```python
# In metrics.py

@dataclass
class VisualAngle:
    """Measurement in degrees visual angle."""
    degrees: float

    @classmethod
    def from_pixels(cls, pixels: float, screen_distance_cm: float,
                    pixels_per_cm: float) -> "VisualAngle":
        """Convert pixel distance to visual angle."""
        cm = pixels / pixels_per_cm
        radians = 2 * math.atan(cm / (2 * screen_distance_cm))
        return cls(degrees=math.degrees(radians))


@dataclass
class PursuitMetrics:
    """Metrics for smooth pursuit test."""
    gain: float                    # Eye velocity / Target velocity
    accuracy_degrees: float        # RMS error in degrees visual angle
    smoothness: float              # 0-1 scale
    tracking_ratio: float          # Valid frames percentage
    catch_up_saccade_count: int    # Number of corrective saccades
    phase_lag_ms: float            # Temporal lag behind target


@dataclass
class SaccadeMetrics:
    """Metrics for saccade test."""
    mean_latency_ms: float         # Average reaction time
    latency_std_ms: float          # Latency variability
    accuracy_degrees: float        # Mean endpoint error
    accuracy_std_degrees: float    # Accuracy variability
    peak_velocity_deg_s: float     # Peak saccade velocity
    correct_count: int             # Correct saccades (pro/anti)
    error_count: int               # Erroneous saccades


@dataclass
class FixationMetrics:
    """Metrics for fixation stability test."""
    bcea_degrees: float            # Bivariate Contour Ellipse Area
    horizontal_std_degrees: float  # Horizontal dispersion
    vertical_std_degrees: float    # Vertical dispersion
    microsaccade_count: int        # Detected microsaccades
    microsaccade_rate_hz: float    # Microsaccades per second
    fixation_duration_ms: float    # Stable fixation duration
```

### 2.2 User Profile Schema

```python
# In profile_manager.py

@dataclass
class UserProfile:
    """User profile with demographics and history."""
    id: str                        # UUID
    name: str
    created_at: datetime
    updated_at: datetime

    # Demographics (optional)
    age: Optional[int] = None
    gender: Optional[str] = None
    notes: str = ""

    # Calibration data
    calibration_profiles: List[CalibrationProfile] = field(default_factory=list)
    active_calibration_id: Optional[str] = None

    # Test history
    test_results: List[TestSession] = field(default_factory=list)


@dataclass
class TestSession:
    """A single test session with results."""
    id: str                        # UUID
    user_profile_id: str
    timestamp: datetime
    test_type: str                 # "pursuit", "saccade", "fixation"
    config: Dict[str, Any]         # Test configuration used
    raw_frames: List[TrackingFrame]
    metrics: Union[PursuitMetrics, SaccadeMetrics, FixationMetrics]
    report: str                    # Generated report text
```

---

## 3. Component Designs

### 3.1 Metrics Calculator (`metrics.py`)

**Purpose**: Centralized clinical-grade metrics calculation

```python
class MetricsCalculator:
    """Calculate clinical eye movement metrics."""

    def __init__(self, screen_config: ScreenConfig):
        self.screen = screen_config
        self.saccade_velocity_threshold = 30  # deg/s
        self.microsaccade_velocity_threshold = 15  # deg/s

    def calculate_pursuit_gain(self, frames: List[TrackingFrame]) -> float:
        """
        Calculate smooth pursuit gain.

        Gain = (mean gaze velocity) / (mean target velocity)

        Steps:
        1. Calculate target velocity for each frame pair
        2. Calculate gaze velocity for each frame pair
        3. Exclude saccadic movements (velocity > threshold)
        4. Return ratio of means
        """
        pass

    def detect_saccades(self, frames: List[TrackingFrame]) -> List[SaccadeEvent]:
        """
        Detect saccadic eye movements.

        Algorithm:
        1. Calculate gaze velocity for each frame
        2. Find velocity peaks above threshold (30 deg/s)
        3. Detect onset/offset using 10% of peak velocity
        4. Calculate saccade metrics (amplitude, duration, peak velocity)
        """
        pass

    def calculate_bcea(self, frames: List[TrackingFrame]) -> float:
        """
        Calculate Bivariate Contour Ellipse Area.

        BCEA = 2.291 * π * σH * σV * √(1 - ρ²)

        Where:
        - σH = horizontal standard deviation
        - σV = vertical standard deviation
        - ρ = correlation coefficient
        """
        pass

    def pixels_to_degrees(self, pixels: float) -> float:
        """Convert pixel distance to degrees visual angle."""
        pass
```

### 3.2 Saccade Test Module (`saccade_test.py`)

**Purpose**: Dedicated saccade assessment with latency measurement

```python
class SaccadeTest:
    """Pro-saccade and anti-saccade testing."""

    class SaccadeType(Enum):
        PRO = "pro"      # Look toward target
        ANTI = "anti"    # Look opposite to target

    def __init__(self, screen_config: ScreenConfig,
                 test_type: SaccadeType = SaccadeType.PRO):
        self.test_type = test_type
        self.trials: List[SaccadeTrial] = []
        self.current_trial: Optional[SaccadeTrial] = None

    def generate_trial(self) -> SaccadeTrial:
        """
        Generate next saccade trial.

        Steps:
        1. Show central fixation point
        2. Wait random interval (500-1500ms) - gap/overlap paradigm
        3. Show peripheral target (left or right)
        4. Record gaze for latency and accuracy
        """
        pass

    def detect_saccade_onset(self, frames: List[TrackingFrame]) -> float:
        """
        Detect saccade onset time.

        Algorithm:
        1. Find first frame where velocity exceeds threshold
        2. Trace back to find movement initiation
        3. Return latency from target onset
        """
        pass

    def calculate_saccade_endpoint(self, frames: List[TrackingFrame]) -> Tuple[float, float]:
        """
        Find saccade endpoint (first fixation after saccade).

        Algorithm:
        1. Find saccade offset (velocity drops below threshold)
        2. Average gaze position in post-saccadic fixation window
        """
        pass
```

### 3.3 Fixation Stability Module (`fixation_test.py`)

**Purpose**: Measure fixation stability and detect microsaccades

```python
class FixationTest:
    """Fixation stability assessment."""

    def __init__(self, screen_config: ScreenConfig,
                 target_position: Tuple[int, int] = None,
                 duration_seconds: float = 30.0):
        self.target = target_position or self._center_position()
        self.duration = duration_seconds

    def detect_microsaccades(self, frames: List[TrackingFrame]) -> List[MicrosaccadeEvent]:
        """
        Detect microsaccades during fixation.

        Algorithm (Engbert & Kliegl, 2003):
        1. Calculate velocity for each sample
        2. Compute velocity threshold: η * median(velocity)
        3. Detect binocular microsaccades (both eyes move together)
        4. Apply minimum duration criterion (6ms)
        """
        pass

    def calculate_dispersion(self, frames: List[TrackingFrame]) -> Tuple[float, float]:
        """
        Calculate horizontal and vertical gaze dispersion.

        Returns standard deviation in degrees visual angle.
        """
        pass
```

### 3.4 Visualization Module (`visualization.py`)

**Purpose**: Generate clinical visualization plots

```python
class TrajectoryPlotter:
    """Generate trajectory visualization plots."""

    def plot_pursuit_trajectory(self, result: TestResult,
                                 save_path: Optional[str] = None) -> Figure:
        """
        Plot target path vs gaze path overlay.

        Features:
        - Target trajectory (blue line)
        - Gaze trajectory (red line with transparency)
        - Saccade markers (yellow dots)
        - Time annotations
        """
        pass

    def plot_gaze_heatmap(self, frames: List[TrackingFrame],
                          save_path: Optional[str] = None) -> Figure:
        """
        Generate gaze position heatmap.

        Uses kernel density estimation for smooth visualization.
        """
        pass

    def plot_velocity_profile(self, frames: List[TrackingFrame],
                              save_path: Optional[str] = None) -> Figure:
        """
        Plot gaze velocity over time.

        Useful for identifying smooth vs saccadic movements.
        """
        pass


class ReportVisualizer:
    """Generate clinical report visualizations."""

    def create_metric_dashboard(self, metrics: Union[PursuitMetrics, SaccadeMetrics, FixationMetrics],
                                  normative_data: NormativeRanges) -> Figure:
        """
        Create dashboard showing metrics vs normative ranges.

        Features:
        - Bar charts with normal range shading
        - Pass/fail indicators
        - Percentile rankings
        """
        pass
```

### 3.5 Export Module (`export.py`)

**Purpose**: Export data in various formats

```python
class DataExporter:
    """Export test data to various formats."""

    def export_raw_csv(self, frames: List[TrackingFrame],
                       filepath: str) -> bool:
        """
        Export raw frame data to CSV.

        Columns:
        - timestamp
        - target_x, target_y
        - gaze_x, gaze_y
        - head_pitch, head_yaw, head_roll
        - face_detected
        """
        pass

    def export_metrics_csv(self, metrics: Dict[str, Any],
                           filepath: str) -> bool:
        """Export computed metrics to CSV."""
        pass


class ReportGenerator:
    """Generate clinical reports."""

    def generate_pdf_report(self, session: TestSession,
                            filepath: str,
                            include_visualizations: bool = True) -> bool:
        """
        Generate PDF clinical report.

        Sections:
        - Patient information
        - Test summary
        - Metrics with normative comparison
        - Visualizations
        - Clinical interpretation
        - Disclaimer
        """
        pass
```

### 3.6 Profile Manager (`profile_manager.py`)

**Purpose**: User profile and result management

```python
class ProfileManager:
    """Manage user profiles and test history."""

    def __init__(self, storage_path: str = "profiles/"):
        self.storage_path = Path(storage_path)
        self.current_profile: Optional[UserProfile] = None

    def create_profile(self, name: str, **demographics) -> UserProfile:
        """Create new user profile."""
        pass

    def load_profile(self, profile_id: str) -> Optional[UserProfile]:
        """Load existing profile."""
        pass

    def save_profile(self, profile: UserProfile) -> bool:
        """Save profile to storage."""
        pass

    def add_test_session(self, session: TestSession) -> bool:
        """Add test session to current profile."""
        pass

    def get_test_history(self, profile_id: str,
                         test_type: Optional[str] = None) -> List[TestSession]:
        """Get test history for profile."""
        pass

    def get_longitudinal_data(self, profile_id: str,
                              metric_name: str) -> List[Tuple[datetime, float]]:
        """Get metric values over time for trend analysis."""
        pass
```

---

## 4. Clinical Algorithms

### 4.1 Pursuit Gain Calculation

```python
def calculate_pursuit_gain(target_positions: np.ndarray,
                           gaze_positions: np.ndarray,
                           timestamps: np.ndarray,
                           saccade_threshold_deg_s: float = 30.0) -> float:
    """
    Calculate smooth pursuit gain.

    Algorithm:
    1. Compute velocities:
       - target_vel[i] = (target[i+1] - target[i]) / (t[i+1] - t[i])
       - gaze_vel[i] = (gaze[i+1] - gaze[i]) / (t[i+1] - t[i])

    2. Identify smooth pursuit segments:
       - Exclude frames where gaze_vel > saccade_threshold
       - These are catch-up saccades

    3. Calculate gain:
       - gain = mean(gaze_vel) / mean(target_vel)
       - Only use smooth pursuit segments

    Normal range: 0.8 - 1.0
    """
    # Implementation
    dt = np.diff(timestamps)
    target_vel = np.linalg.norm(np.diff(target_positions, axis=0), axis=1) / dt
    gaze_vel = np.linalg.norm(np.diff(gaze_positions, axis=0), axis=1) / dt

    # Convert to degrees/second
    target_vel_deg = pixels_to_degrees(target_vel)
    gaze_vel_deg = pixels_to_degrees(gaze_vel)

    # Mask saccades
    smooth_mask = gaze_vel_deg < saccade_threshold_deg_s

    if not np.any(smooth_mask):
        return 0.0

    gain = np.mean(gaze_vel_deg[smooth_mask]) / np.mean(target_vel_deg[smooth_mask])
    return np.clip(gain, 0.0, 2.0)  # Clip to reasonable range
```

### 4.2 Saccade Detection (Velocity-Based)

```python
def detect_saccades(gaze_positions: np.ndarray,
                    timestamps: np.ndarray,
                    velocity_threshold_deg_s: float = 30.0,
                    min_duration_ms: float = 20.0) -> List[SaccadeEvent]:
    """
    Detect saccades using velocity threshold method.

    Algorithm:
    1. Calculate instantaneous velocity
    2. Find segments where velocity exceeds threshold
    3. For each segment:
       a. Find onset (first sample above 10% of peak)
       b. Find offset (last sample above 10% of peak)
       c. Calculate amplitude, duration, peak velocity
    4. Filter by minimum duration
    """
    dt = np.diff(timestamps)
    velocity = np.linalg.norm(np.diff(gaze_positions, axis=0), axis=1) / dt
    velocity_deg = pixels_to_degrees(velocity)

    # Find above-threshold segments
    above_threshold = velocity_deg > velocity_threshold_deg_s

    saccades = []
    in_saccade = False
    onset_idx = 0

    for i, is_above in enumerate(above_threshold):
        if is_above and not in_saccade:
            in_saccade = True
            onset_idx = i
        elif not is_above and in_saccade:
            in_saccade = False
            offset_idx = i

            # Calculate saccade metrics
            segment = velocity_deg[onset_idx:offset_idx]
            duration_ms = (timestamps[offset_idx] - timestamps[onset_idx]) * 1000

            if duration_ms >= min_duration_ms:
                saccade = SaccadeEvent(
                    onset_time=timestamps[onset_idx],
                    offset_time=timestamps[offset_idx],
                    duration_ms=duration_ms,
                    peak_velocity_deg_s=np.max(segment),
                    amplitude_deg=pixels_to_degrees(
                        np.linalg.norm(gaze_positions[offset_idx] - gaze_positions[onset_idx])
                    )
                )
                saccades.append(saccade)

    return saccades
```

### 4.3 BCEA Calculation

```python
def calculate_bcea(gaze_x: np.ndarray,
                   gaze_y: np.ndarray,
                   probability: float = 0.68) -> float:
    """
    Calculate Bivariate Contour Ellipse Area.

    BCEA formula:
    BCEA = 2 * k * π * σH * σV * √(1 - ρ²)

    Where:
    - k = chi-squared value for desired probability
    - σH = horizontal standard deviation (degrees)
    - σV = vertical standard deviation (degrees)
    - ρ = Pearson correlation coefficient

    For P=0.68: k = 1.14 (≈1 SD ellipse)
    For P=0.95: k = 2.29 (≈2 SD ellipse)
    """
    from scipy import stats

    # Convert to degrees
    gaze_x_deg = pixels_to_degrees(gaze_x)
    gaze_y_deg = pixels_to_degrees(gaze_y)

    # Calculate statistics
    sigma_h = np.std(gaze_x_deg)
    sigma_v = np.std(gaze_y_deg)
    rho = np.corrcoef(gaze_x_deg, gaze_y_deg)[0, 1]

    # Chi-squared value for probability
    k = stats.chi2.ppf(probability, df=2)

    # BCEA formula
    bcea = 2 * k * np.pi * sigma_h * sigma_v * np.sqrt(1 - rho**2)

    return bcea
```

---

## 5. Normative Data

### 5.1 Clinical Thresholds

```python
@dataclass
class NormativeRanges:
    """Normative ranges for clinical interpretation."""

    # Smooth Pursuit (adults)
    pursuit_gain_normal: Tuple[float, float] = (0.8, 1.0)
    pursuit_gain_abnormal_below: float = 0.7

    # Saccade Latency (adults, pro-saccade)
    saccade_latency_normal_ms: Tuple[float, float] = (150, 250)
    saccade_latency_abnormal_above_ms: float = 400

    # Saccade Accuracy
    saccade_accuracy_normal_deg: Tuple[float, float] = (0, 3)
    saccade_accuracy_abnormal_above_deg: float = 5

    # Fixation Stability (BCEA)
    bcea_normal_deg2: Tuple[float, float] = (0, 1.5)
    bcea_abnormal_above_deg2: float = 3.0

    # Tracking accuracy
    tracking_accuracy_normal_deg: Tuple[float, float] = (0, 2)
    tracking_accuracy_abnormal_above_deg: float = 3

    def get_interpretation(self, metric_name: str, value: float) -> str:
        """Get clinical interpretation for metric value."""
        pass

    def is_within_normal(self, metric_name: str, value: float) -> bool:
        """Check if value is within normal range."""
        pass
```

---

## 6. Screen Configuration

### 6.1 Visual Angle Conversion

```python
@dataclass
class ScreenConfig:
    """Screen configuration for visual angle calculations."""
    width_px: int                  # Screen width in pixels
    height_px: int                 # Screen height in pixels
    width_cm: float                # Physical width in cm
    height_cm: float               # Physical height in cm
    viewing_distance_cm: float     # Distance from eyes to screen

    @property
    def pixels_per_cm(self) -> float:
        """Calculate pixels per centimeter."""
        return self.width_px / self.width_cm

    @property
    def pixels_per_degree(self) -> float:
        """Calculate pixels per degree visual angle at center."""
        # At viewing distance D, 1 degree = 2 * D * tan(0.5°)
        cm_per_degree = 2 * self.viewing_distance_cm * math.tan(math.radians(0.5))
        return cm_per_degree * self.pixels_per_cm

    def pixels_to_degrees(self, pixels: float) -> float:
        """Convert pixel distance to degrees visual angle."""
        return pixels / self.pixels_per_degree

    def degrees_to_pixels(self, degrees: float) -> float:
        """Convert degrees visual angle to pixels."""
        return degrees * self.pixels_per_degree

    @classmethod
    def default_config(cls) -> "ScreenConfig":
        """Create default configuration (24" monitor at 60cm)."""
        return cls(
            width_px=1920,
            height_px=1080,
            width_cm=53.1,    # 24" diagonal, 16:9
            height_cm=29.9,
            viewing_distance_cm=60.0
        )
```

---

## 7. Error Handling

### 7.1 Calibration Quality Monitoring

```python
class CalibrationMonitor:
    """Monitor calibration quality and suggest recalibration."""

    def __init__(self, quality_threshold: float = 0.7):
        self.threshold = quality_threshold
        self.baseline_quality: Optional[float] = None
        self.quality_history: List[Tuple[datetime, float]] = []

    def check_quality(self, current_quality: float) -> CalibrationStatus:
        """
        Check if recalibration is needed.

        Returns:
        - CalibrationStatus.OK: Quality is good
        - CalibrationStatus.DEGRADED: Quality dropped >10% from baseline
        - CalibrationStatus.POOR: Quality below threshold
        """
        if current_quality < self.threshold:
            return CalibrationStatus.POOR

        if self.baseline_quality:
            degradation = (self.baseline_quality - current_quality) / self.baseline_quality
            if degradation > 0.1:
                return CalibrationStatus.DEGRADED

        return CalibrationStatus.OK

    def estimate_drift(self, recent_frames: List[TrackingFrame]) -> float:
        """
        Estimate tracking drift from recent data.

        Uses variance of calibration point reprojection error.
        """
        pass
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

```python
# tests/unit/test_metrics.py
class TestMetricsCalculator:
    def test_pursuit_gain_calculation(self):
        """Test pursuit gain with known synthetic data."""
        pass

    def test_saccade_detection(self):
        """Test saccade detection with injected saccade patterns."""
        pass

    def test_bcea_calculation(self):
        """Test BCEA calculation with known dispersion."""
        pass

    def test_visual_angle_conversion(self):
        """Test pixel to degree conversion accuracy."""
        pass


# tests/unit/test_saccade.py
class TestSaccadeTest:
    def test_latency_calculation(self):
        """Test saccade latency detection."""
        pass

    def test_accuracy_calculation(self):
        """Test endpoint accuracy calculation."""
        pass
```

### 8.2 Integration Tests

```python
# tests/integration/test_full_workflow.py
class TestFullWorkflow:
    def test_calibration_to_test_flow(self):
        """Test complete workflow from calibration to test."""
        pass

    def test_profile_persistence(self):
        """Test profile save/load cycle."""
        pass

    def test_export_functionality(self):
        """Test CSV and PDF export."""
        pass
```

### 8.3 Accuracy Validation

```python
# tests/accuracy/test_accuracy_validation.py
class TestAccuracyValidation:
    def test_gaze_accuracy_known_positions(self):
        """Validate gaze accuracy against known fixation targets."""
        pass

    def test_calibration_reproducibility(self):
        """Test calibration consistency across sessions."""
        pass
```

---

## 9. Implementation Phases

### Phase 1: Core Metrics (Priority: Must)

1. Create `metrics.py` with visual angle conversion
2. Implement pursuit gain calculation
3. Add velocity-based saccade detection
4. Update `smooth_pursuit_test.py` to use new metrics

### Phase 2: Saccade Test (Priority: Must)

5. Create `saccade_test.py` module
6. Implement pro-saccade test with latency measurement
7. Add saccade accuracy calculation
8. Create UI widget for saccade test

### Phase 3: Fixation Test (Priority: Should)

9. Create `fixation_test.py` module
10. Implement BCEA calculation
11. Add microsaccade detection
12. Create UI widget for fixation test

### Phase 4: Visualization (Priority: Should)

13. Create `visualization.py` module
14. Implement trajectory plotting
15. Add gaze heatmap generation
16. Create metric dashboard

### Phase 5: Export & Reporting (Priority: Must)

17. Create `export.py` module
18. Implement CSV export
19. Add PDF report generation with ReportLab
20. Integrate clinical thresholds

### Phase 6: Profile Management (Priority: Should)

21. Create `profile_manager.py` module
22. Implement full user profiles with demographics
23. Add test session association
24. Create longitudinal data tracking

### Phase 7: Quality & Validation (Priority: Must)

25. Implement calibration quality monitoring
26. Add drift detection
27. Create accuracy validation tests
28. Document clinical validation procedures

---

## 10. Dependencies

### New Dependencies Required

```
# In requirements.txt (additions)
reportlab>=4.0.0        # PDF generation
pillow>=10.0.0          # Image handling for reports
```

### Existing Dependencies (already in requirements.txt)

- opencv-python>=4.8.0
- mediapipe>=0.10.9
- numpy>=1.24.0
- PyQt6>=6.6.0
- pandas>=2.0.0
- matplotlib>=3.7.0
- scipy>=1.11.0
- screeninfo>=0.8.1

---

## 11. File Structure After Implementation

```
EyeExam/
├── src/
│   ├── __init__.py
│   ├── eye_tracker.py          # Existing - MediaPipe integration
│   ├── gaze_estimator.py       # Existing - Calibration & estimation
│   ├── smooth_pursuit_test.py  # Existing - Enhanced with new metrics
│   ├── saccade_test.py         # NEW - Saccade testing module
│   ├── fixation_test.py        # NEW - Fixation stability module
│   ├── metrics.py              # NEW - Clinical metrics calculation
│   ├── visualization.py        # NEW - Plots and visualizations
│   ├── export.py               # NEW - CSV/PDF export
│   ├── profile_manager.py      # NEW - User profile management
│   ├── normative_data.py       # NEW - Clinical thresholds
│   └── main_app.py             # Existing - Enhanced UI
├── tests/
│   ├── unit/
│   │   ├── test_metrics.py
│   │   ├── test_saccade.py
│   │   ├── test_fixation.py
│   │   └── test_export.py
│   ├── integration/
│   │   ├── test_full_workflow.py
│   │   └── test_profile_persistence.py
│   └── accuracy/
│       └── test_accuracy_validation.py
├── profiles/                   # User profiles storage
├── reports/                    # Generated reports
├── requirements.txt
└── run.py
```

---

## 12. Risk Assessment

| Risk                                      | Impact | Mitigation                                                |
| ----------------------------------------- | ------ | --------------------------------------------------------- |
| Accuracy below clinical standards         | High   | Rigorous validation, clear disclaimers                    |
| Performance degradation with new features | Medium | Profile-guided optimization, async processing             |
| Complex UI overwhelming users             | Medium | Progressive disclosure, wizard-style flows                |
| Calibration drift in production           | High   | Continuous quality monitoring, auto-recalibration prompts |
| Export PDF generation fails               | Low    | Graceful fallback to text report                          |

---

## 13. Success Criteria

1. **Pursuit gain accuracy**: ±5% agreement with manual scoring
2. **Saccade latency accuracy**: ±10ms compared to EOG gold standard
3. **BCEA reproducibility**: ICC > 0.8 across sessions
4. **Processing latency**: <50ms per frame
5. **Export functionality**: Successfully generates CSV and PDF for all test types
6. **User workflow**: Complete test cycle in <5 minutes including calibration
