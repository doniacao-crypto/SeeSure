# Requirements Document

## Feature: Eye Movement Assessment System

## Project Description (Input)

Eye Movement Assessment System - A clinical-grade desktop application for assessing eye movement capabilities (smooth pursuit, saccades, fixation stability) using webcam-based eye tracking with MediaPipe.

### Key Requirements Summary

1. **High-precision gaze estimation** with head pose compensation achieving <2° visual angle accuracy
2. **Validated calibration system** with quality metrics
3. **Multiple standardized test protocols** (smooth pursuit H/V/circular, saccade tests, fixation stability)
4. **Comprehensive metrics** including accuracy scores, latency measurement, smoothness analysis
5. **Clinical-grade reporting** with trajectory visualization and normative comparisons
6. **Profile management** for longitudinal tracking

### Target Users

- Ophthalmologists
- Optometrists
- Vision therapists
- Researchers

### Platform

- Desktop (Python/PyQt6) with future web expansion

---

## Research Summary

Based on clinical eye tracking standards research:

- [Clinical smooth pursuit analysis](https://www.nature.com/articles/s41598-022-12630-6) - Target velocity 1-40 deg/s, gain >0.8 is normal
- [DEMoNS saccade protocol](https://pmc.ncbi.nlm.nih.gov/articles/PMC6047815/) - Standardized saccade testing parameters
- [Webcam vs EyeLink comparison](https://pmc.ncbi.nlm.nih.gov/articles/PMC11289017/) - 80-90% correlation with lab standards
- [Deep learning webcam tracking](https://pmc.ncbi.nlm.nih.gov/articles/PMC11133145/) - Best accuracy: 2.4° with 0.47° precision

---

## Functional Requirements

### FR-1: Eye Tracking Core

| ID     | Requirement (EARS Format)                                                                                      | Priority | Acceptance Criteria                                      |
| ------ | -------------------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------- |
| FR-1.1 | **When** the application starts, **the system shall** initialize the webcam and MediaPipe FaceLandmarker model | Must     | Camera feed displays within 3 seconds                    |
| FR-1.2 | **While** camera is active, **the system shall** detect face landmarks at ≥30 FPS                              | Must     | Frame rate ≥30 FPS on standard hardware                  |
| FR-1.3 | **When** a face is detected, **the system shall** extract iris center positions for both eyes                  | Must     | Iris detection succeeds >95% of frames with face visible |
| FR-1.4 | **While** tracking, **the system shall** estimate 3D head pose (pitch, yaw, roll)                              | Must     | Head pose updates each frame                             |
| FR-1.5 | **When** head moves, **the system shall** compensate gaze estimation accordingly                               | Must     | Gaze remains stable within ±5° head movement             |

### FR-2: Calibration System

| ID     | Requirement (EARS Format)                                                                     | Priority | Acceptance Criteria                              |
| ------ | --------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------ |
| FR-2.1 | **When** user initiates calibration, **the system shall** display a 9-point calibration grid  | Must     | Points distributed across screen with 10% margin |
| FR-2.2 | **For each** calibration point, **the system shall** collect ≥30 samples with visual feedback | Must     | Progress indicator shows collection status       |
| FR-2.3 | **After** calibration completes, **the system shall** calculate and display quality score     | Must     | Score includes accuracy estimate and coverage    |
| FR-2.4 | **When** calibration quality <70%, **the system shall** recommend recalibration               | Should   | Warning displayed with specific guidance         |
| FR-2.5 | **The system shall** allow saving calibration profiles to JSON files                          | Must     | Profile includes all calibration data            |
| FR-2.6 | **The system shall** allow loading previously saved calibration profiles                      | Must     | Loaded profile restores gaze estimation          |
| FR-2.7 | **When** lighting conditions change significantly, **the system shall** suggest recalibration | Could    | Automatic drift detection                        |

### FR-3: Smooth Pursuit Testing

| ID     | Requirement (EARS Format)                                                                             | Priority | Acceptance Criteria                         |
| ------ | ----------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------- |
| FR-3.1 | **The system shall** provide horizontal smooth pursuit test (left-right oscillation)                  | Must     | Sinusoidal motion at configurable frequency |
| FR-3.2 | **The system shall** provide vertical smooth pursuit test (up-down oscillation)                       | Must     | Sinusoidal motion at configurable frequency |
| FR-3.3 | **The system shall** provide circular smooth pursuit test                                             | Must     | Circular target path                        |
| FR-3.4 | **The system shall** provide figure-8 pursuit test                                                    | Should   | Lemniscate pattern                          |
| FR-3.5 | **When** test runs, **the system shall** allow target velocity configuration (5-40 deg/s)             | Must     | Speed slider 0.1-1.0 mapping to velocity    |
| FR-3.6 | **When** test runs, **the system shall** allow duration configuration (5-60 seconds)                  | Must     | Duration input field                        |
| FR-3.7 | **During** test, **the system shall** display real-time gaze cursor overlay                           | Must     | Cyan crosshair showing estimated gaze       |
| FR-3.8 | **During** test, **the system shall** record target position, gaze position, and head pose each frame | Must     | All data stored in TestResult               |

### FR-4: Saccade Testing

| ID     | Requirement (EARS Format)                                                    | Priority | Acceptance Criteria                                 |
| ------ | ---------------------------------------------------------------------------- | -------- | --------------------------------------------------- |
| FR-4.1 | **The system shall** provide pro-saccade test (jump to appearing targets)    | Must     | Random target positions with configurable hold time |
| FR-4.2 | **For each** saccade, **the system shall** measure latency (reaction time)   | Must     | Time from target appear to gaze shift               |
| FR-4.3 | **For each** saccade, **the system shall** measure accuracy (endpoint error) | Must     | Distance from target to gaze endpoint               |
| FR-4.4 | **The system shall** provide anti-saccade test (look opposite to target)     | Should   | Score correct vs. erroneous saccades                |
| FR-4.5 | **The system shall** support configurable number of saccade trials (5-20)    | Must     | Trial count configuration                           |

### FR-5: Fixation Stability Testing

| ID     | Requirement (EARS Format)                                                             | Priority | Acceptance Criteria                        |
| ------ | ------------------------------------------------------------------------------------- | -------- | ------------------------------------------ |
| FR-5.1 | **The system shall** provide fixation stability test (hold gaze on stationary target) | Should   | Central fixation point                     |
| FR-5.2 | **During** fixation test, **the system shall** measure gaze dispersion (BCEA)         | Should   | Bivariate contour ellipse area calculation |
| FR-5.3 | **During** fixation test, **the system shall** detect microsaccades                   | Could    | Velocity threshold detection               |

### FR-6: Metrics and Analysis

| ID     | Requirement (EARS Format)                                                                   | Priority | Acceptance Criteria                          |
| ------ | ------------------------------------------------------------------------------------------- | -------- | -------------------------------------------- |
| FR-6.1 | **After** smooth pursuit test, **the system shall** calculate pursuit gain                  | Must     | Gain = eye velocity / target velocity        |
| FR-6.2 | **After** smooth pursuit test, **the system shall** calculate tracking accuracy (RMS error) | Must     | Distance from target in degrees visual angle |
| FR-6.3 | **After** smooth pursuit test, **the system shall** calculate smoothness score              | Must     | Based on velocity variance                   |
| FR-6.4 | **After** smooth pursuit test, **the system shall** detect catch-up saccades                | Should   | Count of corrective saccades during pursuit  |
| FR-6.5 | **After** saccade test, **the system shall** calculate mean latency                         | Must     | Average reaction time in ms                  |
| FR-6.6 | **After** saccade test, **the system shall** calculate saccade accuracy                     | Must     | Mean endpoint error                          |
| FR-6.7 | **The system shall** provide tracking success rate (% valid frames)                         | Must     | Frames with successful tracking / total      |

### FR-7: Reporting

| ID     | Requirement (EARS Format)                                                      | Priority | Acceptance Criteria                     |
| ------ | ------------------------------------------------------------------------------ | -------- | --------------------------------------- |
| FR-7.1 | **After** test completion, **the system shall** generate text summary report   | Must     | Includes all metrics and interpretation |
| FR-7.2 | **The system shall** provide pass/fail screening based on normative thresholds | Must     | Clear indication of normal vs. abnormal |
| FR-7.3 | **The system shall** generate trajectory visualization plot                    | Should   | Target path vs. gaze path overlay       |
| FR-7.4 | **The system shall** generate gaze heatmap visualization                       | Could    | Density map of gaze positions           |
| FR-7.5 | **The system shall** allow export of raw data to CSV                           | Must     | All frame data exportable               |
| FR-7.6 | **The system shall** allow export of report to PDF                             | Should   | Clinical documentation format           |

### FR-8: Profile Management

| ID     | Requirement (EARS Format)                                              | Priority | Acceptance Criteria       |
| ------ | ---------------------------------------------------------------------- | -------- | ------------------------- |
| FR-8.1 | **The system shall** support creating user profiles                    | Should   | Name, demographics, notes |
| FR-8.2 | **The system shall** associate test results with user profiles         | Should   | Historical tracking       |
| FR-8.3 | **The system shall** display longitudinal progress for returning users | Could    | Trend visualization       |

---

## Non-Functional Requirements

### NFR-1: Accuracy

| ID      | Requirement                   | Target           | Validation Method                  |
| ------- | ----------------------------- | ---------------- | ---------------------------------- |
| NFR-1.1 | Gaze estimation accuracy      | <2° visual angle | Validation against known positions |
| NFR-1.2 | Gaze estimation precision     | <1° visual angle | Repeated measurements std dev      |
| NFR-1.3 | Head pose estimation accuracy | <5° rotation     | Comparison with reference          |
| NFR-1.4 | Temporal resolution           | ≥30 Hz           | Frame rate measurement             |

### NFR-2: Performance

| ID      | Requirement        | Target                  | Validation Method     |
| ------- | ------------------ | ----------------------- | --------------------- |
| NFR-2.1 | Processing latency | <50ms end-to-end        | Timestamp measurement |
| NFR-2.2 | CPU utilization    | <40% on modern hardware | System monitoring     |
| NFR-2.3 | Memory usage       | <500MB                  | System monitoring     |
| NFR-2.4 | Startup time       | <5 seconds              | Timer measurement     |

### NFR-3: Usability

| ID      | Requirement              | Target                       | Validation Method |
| ------- | ------------------------ | ---------------------------- | ----------------- |
| NFR-3.1 | Calibration success rate | >95% of users                | User testing      |
| NFR-3.2 | Test completion rate     | >90%                         | User testing      |
| NFR-3.3 | Time to first test       | <3 minutes                   | User testing      |
| NFR-3.4 | Error recovery           | Clear guidance on all errors | Review            |

### NFR-4: Reliability

| ID      | Requirement          | Target                         | Validation Method |
| ------- | -------------------- | ------------------------------ | ----------------- |
| NFR-4.1 | Face detection rate  | >98% when face visible         | Automated testing |
| NFR-4.2 | Crash-free operation | No crashes during normal use   | Stress testing    |
| NFR-4.3 | Reproducibility      | <10% variance between sessions | Repeated testing  |

### NFR-5: Compatibility

| ID      | Requirement         | Target                        | Validation Method   |
| ------- | ------------------- | ----------------------------- | ------------------- |
| NFR-5.1 | Camera support      | 720p+ USB/integrated webcams  | Hardware testing    |
| NFR-5.2 | OS support          | macOS 12+, Windows 10+, Linux | Platform testing    |
| NFR-5.3 | Lighting conditions | Standard office lighting      | Environment testing |

---

## Test Scenarios

### TS-1: Calibration Flow

1. User clicks "Start Calibration"
2. System goes fullscreen with dark background
3. Each of 9 points appears with countdown
4. User looks at each point
5. System shows progress ring filling
6. After completion, quality score displayed
7. Profile can be saved

**Expected**: Quality score >70%, gaze estimation functional

### TS-2: Smooth Pursuit Test

1. User selects "Horizontal" pattern
2. User sets duration to 10 seconds
3. User clicks "Start Test"
4. Yellow target moves left-right
5. User follows with eyes
6. Cyan gaze cursor overlays estimated position
7. Test completes, results displayed

**Expected**: Accuracy score calculated, report generated

### TS-3: Saccade Test

1. User selects "Random Points" pattern
2. Target appears at random positions
3. User looks at each target
4. System measures latency and accuracy
5. Results show mean latency and accuracy

**Expected**: Latency <400ms normal, accuracy <3° normal

### TS-4: Profile Persistence

1. User completes calibration
2. User saves profile
3. User closes application
4. User reopens application
5. User loads profile
6. Gaze estimation works without recalibration

**Expected**: Profile loads successfully, tracking accurate

---

## Clinical Validation Requirements

### CV-1: Accuracy Validation

- Compare gaze estimation to known fixation targets
- Calculate mean error in degrees visual angle
- Target: <2° mean error, <1° standard deviation

### CV-2: Normative Data

- Collect baseline data from healthy adults (N≥50)
- Establish normal ranges for:
  - Pursuit gain (expected: >0.8)
  - Saccade latency (expected: 150-250ms)
  - Tracking accuracy (expected: <3° error)

### CV-3: Test-Retest Reliability

- Same subjects tested on multiple sessions
- Calculate intraclass correlation coefficient (ICC)
- Target: ICC >0.7 for primary metrics

---

## Constraints

1. Must work with standard consumer webcams (no infrared)
2. Must function in typical office lighting
3. Must not require specialized hardware
4. Must run on consumer-grade computers
5. Must complete calibration in <2 minutes
6. Must provide results immediately after test completion
