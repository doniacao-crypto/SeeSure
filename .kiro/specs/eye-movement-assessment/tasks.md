# Implementation Tasks

## Eye Movement Assessment System

Generated from requirements and design documents.

---

## Task Overview

| Phase                   | Tasks   | Priority | Est. Effort |
| ----------------------- | ------- | -------- | ----------- |
| 1. Core Metrics         | 1.1-1.5 | Must     | 8-10 hours  |
| 2. Saccade Test         | 2.1-2.5 | Must     | 8-10 hours  |
| 3. Fixation Test        | 3.1-3.4 | Should   | 6-8 hours   |
| 4. Visualization        | 4.1-4.4 | Should   | 6-8 hours   |
| 5. Export & Report      | 5.1-5.4 | Must     | 6-8 hours   |
| 6. Profile Management   | 6.1-6.4 | Should   | 4-6 hours   |
| 7. Quality & Validation | 7.1-7.4 | Must     | 4-6 hours   |

**Total Estimated Effort**: 42-56 hours

---

## Phase 1: Core Metrics Module

### Task 1.1: Create metrics.py with ScreenConfig and Visual Angle Conversion

**Status**: [ ] Pending
**Priority**: Must
**Requirements**: NFR-1.1, NFR-1.2
**Files**:

- Create: `src/metrics.py`

**Description**:
Create the core metrics module with screen configuration and visual angle conversion utilities.

**Acceptance Criteria**:

- [ ] `ScreenConfig` dataclass with screen dimensions, physical size, viewing distance
- [ ] `pixels_to_degrees()` method using proper trigonometry
- [ ] `degrees_to_pixels()` inverse method
- [ ] `pixels_per_degree` property calculation
- [ ] Default config for 24" monitor at 60cm
- [ ] Unit tests for conversion accuracy (<0.1% error)

**Implementation Details**:

```python
# Key formula for visual angle:
# angle_rad = 2 * atan(size_cm / (2 * distance_cm))
# degrees = math.degrees(angle_rad)
```

---

### Task 1.2: Implement Pursuit Gain Calculation

**Status**: [ ] Pending
**Priority**: Must
**Requirements**: FR-6.1
**Dependencies**: Task 1.1
**Files**:

- Modify: `src/metrics.py`

**Description**:
Implement pursuit gain calculation as the ratio of eye velocity to target velocity during smooth pursuit.

**Acceptance Criteria**:

- [ ] `calculate_pursuit_gain()` function
- [ ] Velocity calculation from position/timestamp pairs
- [ ] Saccade exclusion (velocity > 30 deg/s threshold)
- [ ] Returns gain value (expected range 0.0-2.0)
- [ ] Unit tests with synthetic data (known gain values)

**Implementation Details**:

```python
# Algorithm:
# 1. Calculate dt between frames
# 2. Calculate target and gaze velocities in deg/s
# 3. Mask out saccadic segments (velocity > threshold)
# 4. Return mean(gaze_vel) / mean(target_vel)
```

---

### Task 1.3: Implement Saccade Detection Algorithm

**Status**: [ ] Pending
**Priority**: Must
**Requirements**: FR-6.4, FR-4.2, FR-4.3
**Dependencies**: Task 1.1
**Files**:

- Modify: `src/metrics.py`

**Description**:
Implement velocity-threshold based saccade detection.

**Acceptance Criteria**:

- [ ] `SaccadeEvent` dataclass (onset, offset, duration, peak_velocity, amplitude)
- [ ] `detect_saccades()` function using velocity threshold
- [ ] Configurable threshold (default 30 deg/s)
- [ ] Minimum duration filter (default 20ms)
- [ ] Returns list of `SaccadeEvent` objects
- [ ] Unit tests with injected saccade patterns

**Implementation Details**:

```python
# Algorithm:
# 1. Calculate instantaneous velocity
# 2. Find segments above threshold
# 3. For each segment: find onset/offset at 10% of peak
# 4. Calculate metrics and filter by min duration
```

---

### Task 1.4: Implement PursuitMetrics Dataclass

**Status**: [ ] Pending
**Priority**: Must
**Requirements**: FR-6.1, FR-6.2, FR-6.3, FR-6.4
**Dependencies**: Task 1.2, Task 1.3
**Files**:

- Modify: `src/metrics.py`

**Description**:
Create comprehensive pursuit metrics dataclass and calculator.

**Acceptance Criteria**:

- [ ] `PursuitMetrics` dataclass with all fields
- [ ] `calculate_pursuit_metrics()` function
- [ ] Gain calculation using Task 1.2
- [ ] RMS error in degrees visual angle
- [ ] Smoothness score (coefficient of variation)
- [ ] Catch-up saccade count using Task 1.3
- [ ] Phase lag estimation

---

### Task 1.5: Update smooth_pursuit_test.py to Use New Metrics

**Status**: [ ] Pending
**Priority**: Must
**Requirements**: FR-6.1, FR-6.2, FR-6.3
**Dependencies**: Task 1.4
**Files**:

- Modify: `src/smooth_pursuit_test.py`

**Description**:
Integrate the new metrics calculator into the existing smooth pursuit test.

**Acceptance Criteria**:

- [ ] Import and use `MetricsCalculator`
- [ ] Replace `accuracy_score` with `accuracy_degrees`
- [ ] Add `pursuit_gain` to TestResult
- [ ] Add `catch_up_saccade_count` to TestResult
- [ ] Update `generate_report()` with new metrics
- [ ] Integration tests pass

---

## Phase 2: Saccade Test Module

### Task 2.1: Create saccade_test.py Module Structure

**Status**: [ ] Pending
**Priority**: Must
**Requirements**: FR-4.1
**Files**:

- Create: `src/saccade_test.py`

**Description**:
Create the saccade test module with core classes and enums.

**Acceptance Criteria**:

- [ ] `SaccadeType` enum (PRO, ANTI)
- [ ] `SaccadeTrial` dataclass (target_position, onset_time, response_frames)
- [ ] `SaccadeTestConfig` dataclass (trial_count, gap_duration_range, target_eccentricity)
- [ ] `SaccadeTest` class skeleton
- [ ] Module documentation

---

### Task 2.2: Implement Pro-Saccade Trial Generation

**Status**: [ ] Pending
**Priority**: Must
**Requirements**: FR-4.1, FR-4.5
**Dependencies**: Task 2.1
**Files**:

- Modify: `src/saccade_test.py`

**Description**:
Implement the trial generation for pro-saccade test.

**Acceptance Criteria**:

- [ ] `generate_trial()` method with gap/overlap paradigm
- [ ] Random target position (left or right at configurable eccentricity)
- [ ] Random foreperiod (500-1500ms default)
- [ ] State machine: FIXATION → GAP → TARGET → RESPONSE
- [ ] Configurable number of trials (5-20)

---

### Task 2.3: Implement Saccade Latency Measurement

**Status**: [ ] Pending
**Priority**: Must
**Requirements**: FR-4.2, FR-6.5
**Dependencies**: Task 2.2, Task 1.3
**Files**:

- Modify: `src/saccade_test.py`

**Description**:
Implement saccade latency measurement from target onset to saccade initiation.

**Acceptance Criteria**:

- [ ] `detect_saccade_onset()` method
- [ ] Uses velocity threshold from metrics.py
- [ ] Returns latency in milliseconds
- [ ] Handles no-saccade trials (timeout)
- [ ] Handles anticipatory saccades (<100ms)
- [ ] Unit tests with known latency values

---

### Task 2.4: Implement Saccade Accuracy Measurement

**Status**: [ ] Pending
**Priority**: Must
**Requirements**: FR-4.3, FR-6.6
**Dependencies**: Task 2.3
**Files**:

- Modify: `src/saccade_test.py`

**Description**:
Implement saccade endpoint accuracy measurement.

**Acceptance Criteria**:

- [ ] `calculate_saccade_endpoint()` method
- [ ] Find post-saccadic fixation
- [ ] Calculate endpoint error in degrees
- [ ] Handle hypometric/hypermetric saccades
- [ ] `SaccadeMetrics` dataclass with mean/std accuracy

---

### Task 2.5: Create Saccade Test UI Widget

**Status**: [ ] Pending
**Priority**: Must
**Requirements**: FR-4.1
**Dependencies**: Task 2.4
**Files**:

- Modify: `src/main_app.py`

**Description**:
Create PyQt6 widget for saccade test execution.

**Acceptance Criteria**:

- [ ] `SaccadeTestWidget` class
- [ ] Central fixation point display
- [ ] Peripheral target appearance
- [ ] Trial progress indicator
- [ ] Real-time gaze overlay
- [ ] Integration with main window menu

---

## Phase 3: Fixation Stability Test Module

### Task 3.1: Create fixation_test.py Module Structure

**Status**: [ ] Pending
**Priority**: Should
**Requirements**: FR-5.1
**Files**:

- Create: `src/fixation_test.py`

**Description**:
Create the fixation stability test module.

**Acceptance Criteria**:

- [ ] `FixationTestConfig` dataclass
- [ ] `FixationTest` class with start/stop/record methods
- [ ] `FixationMetrics` dataclass
- [ ] Central fixation target display logic

---

### Task 3.2: Implement BCEA Calculation

**Status**: [ ] Pending
**Priority**: Should
**Requirements**: FR-5.2
**Dependencies**: Task 3.1, Task 1.1
**Files**:

- Modify: `src/metrics.py`

**Description**:
Implement Bivariate Contour Ellipse Area calculation.

**Acceptance Criteria**:

- [ ] `calculate_bcea()` function
- [ ] Horizontal/vertical standard deviation in degrees
- [ ] Pearson correlation coefficient
- [ ] BCEA formula: 2.291 _ π _ σH _ σV _ √(1 - ρ²)
- [ ] Configurable probability (P=0.68 or P=0.95)
- [ ] Unit tests with known dispersion data

---

### Task 3.3: Implement Microsaccade Detection

**Status**: [ ] Pending
**Priority**: Could
**Requirements**: FR-5.3
**Dependencies**: Task 3.1
**Files**:

- Modify: `src/fixation_test.py`

**Description**:
Implement microsaccade detection during fixation (Engbert & Kliegl algorithm).

**Acceptance Criteria**:

- [ ] `detect_microsaccades()` function
- [ ] Velocity threshold based on median velocity
- [ ] Minimum duration criterion (6ms)
- [ ] Returns `MicrosaccadeEvent` list
- [ ] Microsaccade rate calculation (Hz)

---

### Task 3.4: Create Fixation Test UI Widget

**Status**: [ ] Pending
**Priority**: Should
**Dependencies**: Task 3.2
**Files**:

- Modify: `src/main_app.py`

**Description**:
Create PyQt6 widget for fixation stability test.

**Acceptance Criteria**:

- [ ] `FixationTestWidget` class
- [ ] Central fixation target
- [ ] Real-time gaze position display
- [ ] Timer/countdown display
- [ ] Integration with main window

---

## Phase 4: Visualization Module

### Task 4.1: Create visualization.py Module

**Status**: [ ] Pending
**Priority**: Should
**Requirements**: FR-7.3, FR-7.4
**Files**:

- Create: `src/visualization.py`

**Description**:
Create the visualization module with matplotlib integration.

**Acceptance Criteria**:

- [ ] Import matplotlib with Qt backend
- [ ] `TrajectoryPlotter` class
- [ ] Color scheme constants for clinical visualization
- [ ] Figure size and DPI configuration

---

### Task 4.2: Implement Trajectory Plot

**Status**: [ ] Pending
**Priority**: Should
**Requirements**: FR-7.3
**Dependencies**: Task 4.1
**Files**:

- Modify: `src/visualization.py`

**Description**:
Implement target vs gaze trajectory overlay plot.

**Acceptance Criteria**:

- [ ] `plot_pursuit_trajectory()` method
- [ ] Target path (blue solid line)
- [ ] Gaze path (red line with transparency)
- [ ] Saccade markers (yellow dots)
- [ ] Time annotations or colormap
- [ ] Save to file option

---

### Task 4.3: Implement Gaze Heatmap

**Status**: [ ] Pending
**Priority**: Could
**Requirements**: FR-7.4
**Dependencies**: Task 4.1
**Files**:

- Modify: `src/visualization.py`

**Description**:
Implement gaze position heatmap using kernel density estimation.

**Acceptance Criteria**:

- [ ] `plot_gaze_heatmap()` method
- [ ] KDE-based density estimation
- [ ] Colormap with clinical palette
- [ ] Screen boundary overlay
- [ ] Target position marker

---

### Task 4.4: Implement Metrics Dashboard

**Status**: [ ] Pending
**Priority**: Should
**Dependencies**: Task 4.1
**Files**:

- Modify: `src/visualization.py`

**Description**:
Create dashboard showing metrics vs normative ranges.

**Acceptance Criteria**:

- [ ] `create_metric_dashboard()` method
- [ ] Bar charts for each metric
- [ ] Normal range shading (green)
- [ ] Abnormal range indication (red)
- [ ] Pass/fail indicators

---

## Phase 5: Export and Reporting

### Task 5.1: Create export.py Module

**Status**: [ ] Pending
**Priority**: Must
**Requirements**: FR-7.5
**Files**:

- Create: `src/export.py`

**Description**:
Create the data export module.

**Acceptance Criteria**:

- [ ] `DataExporter` class
- [ ] Pandas DataFrame conversion utilities
- [ ] File path validation

---

### Task 5.2: Implement CSV Export

**Status**: [ ] Pending
**Priority**: Must
**Requirements**: FR-7.5
**Dependencies**: Task 5.1
**Files**:

- Modify: `src/export.py`

**Description**:
Implement raw data and metrics CSV export.

**Acceptance Criteria**:

- [ ] `export_raw_csv()` - frame-by-frame data
- [ ] `export_metrics_csv()` - computed metrics
- [ ] Column headers with units
- [ ] UTF-8 encoding
- [ ] Timestamp formatting

---

### Task 5.3: Implement PDF Report Generation

**Status**: [ ] Pending
**Priority**: Should
**Requirements**: FR-7.6
**Dependencies**: Task 5.1, Task 4.2, Task 4.4
**Files**:

- Modify: `src/export.py`
- Update: `requirements.txt` (add reportlab)

**Description**:
Implement clinical PDF report generation.

**Acceptance Criteria**:

- [ ] `ReportGenerator` class
- [ ] `generate_pdf_report()` method
- [ ] Header with patient info (if available)
- [ ] Test summary section
- [ ] Metrics table with normative comparison
- [ ] Embedded visualizations
- [ ] Clinical interpretation text
- [ ] Disclaimer footer

---

### Task 5.4: Create Normative Data Module

**Status**: [ ] Pending
**Priority**: Must
**Requirements**: FR-7.2
**Files**:

- Create: `src/normative_data.py`

**Description**:
Create module with clinical normative ranges.

**Acceptance Criteria**:

- [ ] `NormativeRanges` dataclass
- [ ] Pursuit gain thresholds (0.8-1.0 normal)
- [ ] Saccade latency thresholds (150-250ms normal)
- [ ] BCEA thresholds (0-1.5 deg² normal)
- [ ] `get_interpretation()` method
- [ ] `is_within_normal()` method
- [ ] Pass/fail determination logic

---

## Phase 6: Profile Management

### Task 6.1: Create profile_manager.py Module

**Status**: [ ] Pending
**Priority**: Should
**Requirements**: FR-8.1
**Files**:

- Create: `src/profile_manager.py`

**Description**:
Create user profile management module.

**Acceptance Criteria**:

- [ ] `UserProfile` dataclass with demographics
- [ ] `ProfileManager` class
- [ ] UUID generation for profile IDs
- [ ] Storage path configuration

---

### Task 6.2: Implement Profile CRUD Operations

**Status**: [ ] Pending
**Priority**: Should
**Requirements**: FR-8.1
**Dependencies**: Task 6.1
**Files**:

- Modify: `src/profile_manager.py`

**Description**:
Implement create, read, update, delete for profiles.

**Acceptance Criteria**:

- [ ] `create_profile()` method
- [ ] `load_profile()` method
- [ ] `save_profile()` method
- [ ] `delete_profile()` method
- [ ] `list_profiles()` method
- [ ] JSON file storage

---

### Task 6.3: Implement Test Session Association

**Status**: [ ] Pending
**Priority**: Should
**Requirements**: FR-8.2
**Dependencies**: Task 6.2
**Files**:

- Modify: `src/profile_manager.py`

**Description**:
Link test results to user profiles.

**Acceptance Criteria**:

- [ ] `TestSession` dataclass
- [ ] `add_test_session()` method
- [ ] `get_test_history()` method
- [ ] Session timestamp and test type indexing

---

### Task 6.4: Implement Longitudinal Data Tracking

**Status**: [ ] Pending
**Priority**: Could
**Requirements**: FR-8.3
**Dependencies**: Task 6.3
**Files**:

- Modify: `src/profile_manager.py`

**Description**:
Enable tracking metrics over time.

**Acceptance Criteria**:

- [ ] `get_longitudinal_data()` method
- [ ] Returns time-series of metric values
- [ ] Supports filtering by test type
- [ ] Trend analysis utilities

---

## Phase 7: Quality and Validation

### Task 7.1: Implement Calibration Quality Monitoring

**Status**: [ ] Pending
**Priority**: Must
**Requirements**: FR-2.4
**Files**:

- Modify: `src/gaze_estimator.py`

**Description**:
Add continuous calibration quality monitoring.

**Acceptance Criteria**:

- [ ] `CalibrationMonitor` class
- [ ] Quality threshold configuration (default 70%)
- [ ] `check_quality()` method returning status
- [ ] Baseline quality tracking
- [ ] Degradation detection (>10% drop)

---

### Task 7.2: Implement Drift Detection

**Status**: [ ] Pending
**Priority**: Could
**Requirements**: FR-2.7
**Dependencies**: Task 7.1
**Files**:

- Modify: `src/gaze_estimator.py`

**Description**:
Detect tracking drift that may require recalibration.

**Acceptance Criteria**:

- [ ] `estimate_drift()` method
- [ ] Rolling window analysis of reprojection error
- [ ] Alert when drift exceeds threshold
- [ ] Integration with UI for recalibration prompt

---

### Task 7.3: Create Unit Test Suite

**Status**: [ ] Pending
**Priority**: Must
**Files**:

- Create: `tests/unit/test_metrics.py`
- Create: `tests/unit/test_saccade.py`
- Create: `tests/unit/test_fixation.py`
- Create: `tests/unit/test_export.py`

**Description**:
Create comprehensive unit test suite.

**Acceptance Criteria**:

- [ ] Test visual angle conversion accuracy
- [ ] Test pursuit gain with synthetic data
- [ ] Test saccade detection with known patterns
- [ ] Test BCEA with known dispersion
- [ ] Test CSV/PDF export functionality
- [ ] All tests pass with >80% coverage

---

### Task 7.4: Create Accuracy Validation Tests

**Status**: [ ] Pending
**Priority**: Must
**Files**:

- Create: `tests/accuracy/test_accuracy_validation.py`

**Description**:
Create tests to validate clinical accuracy targets.

**Acceptance Criteria**:

- [ ] Test gaze accuracy against known fixation targets
- [ ] Test calibration reproducibility (ICC calculation)
- [ ] Document validation methodology
- [ ] Generate validation report

---

## Task Dependencies Graph

```
Phase 1 (Core Metrics):
1.1 → 1.2 → 1.4 → 1.5
1.1 → 1.3 → 1.4

Phase 2 (Saccade):
2.1 → 2.2 → 2.3 → 2.4 → 2.5
      1.3 ↗

Phase 3 (Fixation):
3.1 → 3.2 → 3.4
      1.1 ↗
3.1 → 3.3

Phase 4 (Visualization):
4.1 → 4.2 → 4.4
4.1 → 4.3

Phase 5 (Export):
5.1 → 5.2
5.1 → 5.3
      4.2 ↗
      4.4 ↗
5.4 (independent)

Phase 6 (Profile):
6.1 → 6.2 → 6.3 → 6.4

Phase 7 (Quality):
7.1 → 7.2
7.3 (requires 1.x, 2.x, 3.x, 5.x)
7.4 (requires all phases)
```

---

## Implementation Order (Recommended)

### Sprint 1: Foundation (Tasks 1.1-1.5)

Focus: Core metrics module with visual angle and pursuit gain

### Sprint 2: Saccade (Tasks 2.1-2.5)

Focus: Complete saccade test module with UI

### Sprint 3: Export & Normative (Tasks 5.1-5.4)

Focus: Data export and clinical interpretation

### Sprint 4: Fixation & Visualization (Tasks 3.1-3.4, 4.1-4.4)

Focus: Fixation test and visualization

### Sprint 5: Profile & Quality (Tasks 6.1-6.4, 7.1-7.4)

Focus: User profiles and quality assurance

---

## Completion Checklist

- [ ] All Must tasks completed
- [ ] All Should tasks completed (or deferred with justification)
- [ ] Unit tests passing with >80% coverage
- [ ] Integration tests passing
- [ ] Accuracy validation completed
- [ ] Documentation updated
- [ ] Code reviewed
