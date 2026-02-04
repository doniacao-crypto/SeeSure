# Gap Analysis: Requirements vs POC Implementation

## Overview

This document analyzes the gap between the comprehensive requirements document and the existing Proof of Concept (POC) implementation in `src/`.

## Summary

| Category                      | Requirements | POC Coverage | Gap Level     |
| ----------------------------- | ------------ | ------------ | ------------- |
| Eye Tracking Core (FR-1)      | 5            | 5 (100%)     | ✅ Low        |
| Calibration System (FR-2)     | 7            | 5 (71%)      | 🟡 Medium     |
| Smooth Pursuit Testing (FR-3) | 8            | 7 (88%)      | 🟡 Low-Medium |
| Saccade Testing (FR-4)        | 5            | 1 (20%)      | 🔴 High       |
| Fixation Stability (FR-5)     | 3            | 0 (0%)       | 🔴 High       |
| Metrics and Analysis (FR-6)   | 7            | 4 (57%)      | 🟡 Medium     |
| Reporting (FR-7)              | 6            | 2 (33%)      | 🔴 High       |
| Profile Management (FR-8)     | 3            | 1 (33%)      | 🔴 High       |
| Non-Functional                | 20           | ~12 (60%)    | 🟡 Medium     |

---

## Detailed Gap Analysis

### FR-1: Eye Tracking Core

| Req ID | Requirement                                    | POC Status     | Gap                                                  |
| ------ | ---------------------------------------------- | -------------- | ---------------------------------------------------- |
| FR-1.1 | Initialize webcam and MediaPipe FaceLandmarker | ✅ Implemented | `eye_tracker.py:88-100` - Uses tasks API             |
| FR-1.2 | Detect face landmarks at ≥30 FPS               | ✅ Implemented | Running mode IMAGE, achieves ~30 FPS                 |
| FR-1.3 | Extract iris center positions for both eyes    | ✅ Implemented | `eye_tracker.py:123-138` - LEFT/RIGHT_IRIS_INDICES   |
| FR-1.4 | Estimate 3D head pose (pitch, yaw, roll)       | ✅ Implemented | `eye_tracker.py:179-215` - solvePnP algorithm        |
| FR-1.5 | Compensate gaze estimation for head movement   | ✅ Implemented | `gaze_estimator.py:267-272` - pitch/yaw compensation |

**Gap Level**: ✅ **Low** - Core eye tracking fully implemented

---

### FR-2: Calibration System

| Req ID | Requirement                                 | POC Status     | Gap                                                         |
| ------ | ------------------------------------------- | -------------- | ----------------------------------------------------------- |
| FR-2.1 | Display 9-point calibration grid            | ✅ Implemented | `main_app.py` CalibrationWidget                             |
| FR-2.2 | Collect ≥30 samples per point with feedback | ⚠️ Partial     | Collects samples but not exactly 30; visual feedback exists |
| FR-2.3 | Calculate and display quality score         | ✅ Implemented | `gaze_estimator.py:384-433`                                 |
| FR-2.4 | Recommend recalibration when quality <70%   | ❌ Missing     | No automatic recommendation logic                           |
| FR-2.5 | Save calibration profiles to JSON           | ✅ Implemented | `gaze_estimator.py:334-356`                                 |
| FR-2.6 | Load previously saved profiles              | ✅ Implemented | `gaze_estimator.py:358-382`                                 |
| FR-2.7 | Suggest recalibration on lighting change    | ❌ Missing     | No lighting/drift detection                                 |

**Gap Level**: 🟡 **Medium**

- Missing: Automatic recalibration recommendation (FR-2.4)
- Missing: Lighting change detection (FR-2.7)
- Partial: Sample collection not exactly 30 per point (FR-2.2)

---

### FR-3: Smooth Pursuit Testing

| Req ID | Requirement                                | POC Status     | Gap                                   |
| ------ | ------------------------------------------ | -------------- | ------------------------------------- |
| FR-3.1 | Horizontal smooth pursuit test             | ✅ Implemented | `smooth_pursuit_test.py:218-222`      |
| FR-3.2 | Vertical smooth pursuit test               | ✅ Implemented | `smooth_pursuit_test.py:224-228`      |
| FR-3.3 | Circular smooth pursuit test               | ✅ Implemented | `smooth_pursuit_test.py:230-235`      |
| FR-3.4 | Figure-8 pursuit test                      | ✅ Implemented | `smooth_pursuit_test.py:237-243`      |
| FR-3.5 | Target velocity configuration (5-40 deg/s) | ⚠️ Partial     | Speed 0-1 ratio, not deg/s conversion |
| FR-3.6 | Duration configuration (5-60 seconds)      | ✅ Implemented | `TestConfig.duration_seconds`         |
| FR-3.7 | Real-time gaze cursor overlay              | ✅ Implemented | `main_app.py` TestWidget draws gaze   |
| FR-3.8 | Record target, gaze, head pose per frame   | ✅ Implemented | `smooth_pursuit_test.py:259-287`      |

**Gap Level**: 🟡 **Low-Medium**

- Partial: Speed not in degrees/second (FR-3.5)

---

### FR-4: Saccade Testing

| Req ID | Requirement                        | POC Status | Gap                                                           |
| ------ | ---------------------------------- | ---------- | ------------------------------------------------------------- |
| FR-4.1 | Pro-saccade test (jump to targets) | ⚠️ Partial | RANDOM_POINTS pattern exists but no dedicated saccade metrics |
| FR-4.2 | Measure latency (reaction time)    | ❌ Missing | No saccade latency calculation                                |
| FR-4.3 | Measure accuracy (endpoint error)  | ❌ Missing | No saccade-specific accuracy                                  |
| FR-4.4 | Anti-saccade test                  | ❌ Missing | Not implemented                                               |
| FR-4.5 | Configurable number of trials      | ⚠️ Partial | `num_points` exists but no trial logic                        |

**Gap Level**: 🔴 **High**

- Missing: Proper saccade detection algorithm
- Missing: Latency measurement (FR-4.2)
- Missing: Saccade-specific accuracy metrics (FR-4.3)
- Missing: Anti-saccade test (FR-4.4)

---

### FR-5: Fixation Stability Testing

| Req ID | Requirement                    | POC Status | Gap             |
| ------ | ------------------------------ | ---------- | --------------- |
| FR-5.1 | Fixation stability test        | ❌ Missing | Not implemented |
| FR-5.2 | Measure gaze dispersion (BCEA) | ❌ Missing | Not implemented |
| FR-5.3 | Detect microsaccades           | ❌ Missing | Not implemented |

**Gap Level**: 🔴 **High**

- Entire fixation stability module missing

---

### FR-6: Metrics and Analysis

| Req ID | Requirement                             | POC Status     | Gap                                          |
| ------ | --------------------------------------- | -------------- | -------------------------------------------- |
| FR-6.1 | Calculate pursuit gain                  | ❌ Missing     | No eye velocity / target velocity ratio      |
| FR-6.2 | Calculate tracking accuracy (RMS error) | ⚠️ Partial     | `avg_distance_px` exists, not RMS in degrees |
| FR-6.3 | Calculate smoothness score              | ✅ Implemented | `smooth_pursuit_test.py:91-105`              |
| FR-6.4 | Detect catch-up saccades                | ❌ Missing     | Not implemented                              |
| FR-6.5 | Calculate mean saccade latency          | ❌ Missing     | Not implemented                              |
| FR-6.6 | Calculate saccade accuracy              | ❌ Missing     | Not implemented                              |
| FR-6.7 | Tracking success rate                   | ✅ Implemented | `tracking_ratio` in TestResult               |

**Gap Level**: 🟡 **Medium**

- Missing: Pursuit gain calculation (FR-6.1)
- Missing: Catch-up saccade detection (FR-6.4)
- Missing: Saccade metrics (FR-6.5, FR-6.6)
- Partial: Accuracy not in visual angle degrees (FR-6.2)

---

### FR-7: Reporting

| Req ID | Requirement                         | POC Status     | Gap                                            |
| ------ | ----------------------------------- | -------------- | ---------------------------------------------- |
| FR-7.1 | Generate text summary report        | ✅ Implemented | `smooth_pursuit_test.py:290-352`               |
| FR-7.2 | Pass/fail screening with thresholds | ⚠️ Partial     | Interpretation exists, not clinical thresholds |
| FR-7.3 | Trajectory visualization plot       | ❌ Missing     | Not implemented                                |
| FR-7.4 | Gaze heatmap visualization          | ❌ Missing     | Not implemented                                |
| FR-7.5 | Export raw data to CSV              | ❌ Missing     | Not implemented                                |
| FR-7.6 | Export report to PDF                | ❌ Missing     | Not implemented                                |

**Gap Level**: 🔴 **High**

- Missing: Visualization (FR-7.3, FR-7.4)
- Missing: Export functionality (FR-7.5, FR-7.6)
- Partial: Clinical pass/fail thresholds (FR-7.2)

---

### FR-8: Profile Management

| Req ID | Requirement                          | POC Status | Gap                                              |
| ------ | ------------------------------------ | ---------- | ------------------------------------------------ |
| FR-8.1 | Create user profiles                 | ⚠️ Partial | Calibration profiles exist, no user demographics |
| FR-8.2 | Associate test results with profiles | ❌ Missing | Results not linked to profiles                   |
| FR-8.3 | Display longitudinal progress        | ❌ Missing | No historical tracking                           |

**Gap Level**: 🔴 **High**

- Missing: Full user profile system (FR-8.1)
- Missing: Result-profile association (FR-8.2)
- Missing: Longitudinal tracking (FR-8.3)

---

## Non-Functional Requirements Gap

### NFR-1: Accuracy

| Req ID  | Target                     | POC Status | Gap                                 |
| ------- | -------------------------- | ---------- | ----------------------------------- |
| NFR-1.1 | Gaze <2° visual angle      | ⚠️ Unknown | No validation performed             |
| NFR-1.2 | Precision <1° visual angle | ⚠️ Unknown | No validation performed             |
| NFR-1.3 | Head pose <5° accuracy     | ⚠️ Unknown | solvePnP implemented, not validated |
| NFR-1.4 | Temporal ≥30 Hz            | ✅ Met     | Running at ~30 FPS                  |

### NFR-2: Performance

| Req ID  | Target             | POC Status | Gap                   |
| ------- | ------------------ | ---------- | --------------------- |
| NFR-2.1 | Latency <50ms      | ⚠️ Unknown | Not measured          |
| NFR-2.2 | CPU <40%           | ⚠️ Unknown | Not measured          |
| NFR-2.3 | Memory <500MB      | ⚠️ Unknown | Not measured          |
| NFR-2.4 | Startup <5 seconds | ✅ Met     | Starts within seconds |

### NFR-3: Usability

| Req ID  | Target                    | POC Status | Gap                  |
| ------- | ------------------------- | ---------- | -------------------- |
| NFR-3.1 | Calibration success >95%  | ⚠️ Unknown | Not validated        |
| NFR-3.2 | Test completion >90%      | ⚠️ Unknown | Not validated        |
| NFR-3.3 | Time to first test <3 min | ⚠️ Unknown | Not measured         |
| NFR-3.4 | Clear error guidance      | ⚠️ Partial | Basic error messages |

---

## Priority Implementation Roadmap

### Phase 1: Clinical Accuracy (High Priority)

1. **Pursuit Gain Calculation** (FR-6.1) - Critical for clinical validity
2. **Visual Angle Conversion** - Convert all measurements to degrees
3. **Saccade Detection Algorithm** (FR-4.1-4.3) - Core clinical metric
4. **Accuracy Validation** (NFR-1.1, NFR-1.2) - Validate against known positions

### Phase 2: Missing Test Types

5. **Fixation Stability Test** (FR-5.1-5.3) - BCEA calculation
6. **Anti-Saccade Test** (FR-4.4) - Cognitive component
7. **Catch-up Saccade Detection** (FR-6.4) - Pursuit quality metric

### Phase 3: Reporting & Export

8. **Trajectory Visualization** (FR-7.3) - Matplotlib integration
9. **CSV Export** (FR-7.5) - Pandas DataFrame export
10. **PDF Report** (FR-7.6) - ReportLab or similar
11. **Clinical Thresholds** (FR-7.2) - Research-based normative data

### Phase 4: Profile Management

12. **User Profile System** (FR-8.1) - Demographics, notes
13. **Result Association** (FR-8.2) - Link results to profiles
14. **Longitudinal Tracking** (FR-8.3) - History visualization

### Phase 5: Calibration Enhancement

15. **Recalibration Recommendation** (FR-2.4) - Quality-based triggers
16. **Drift Detection** (FR-2.7) - Lighting/tracking quality monitoring

---

## Files Requiring Modification

| File                             | Changes Needed                                                   |
| -------------------------------- | ---------------------------------------------------------------- |
| `src/smooth_pursuit_test.py`     | Add pursuit gain, visual angle conversion, saccade detection     |
| `src/gaze_estimator.py`          | Add recalibration triggers, drift detection                      |
| `src/main_app.py`                | Add visualization widgets, export buttons, profile management UI |
| **NEW** `src/saccade_test.py`    | Dedicated saccade test module                                    |
| **NEW** `src/fixation_test.py`   | Fixation stability test module                                   |
| **NEW** `src/metrics.py`         | Centralized metrics calculation                                  |
| **NEW** `src/visualization.py`   | Trajectory plots, heatmaps                                       |
| **NEW** `src/export.py`          | CSV/PDF export functionality                                     |
| **NEW** `src/profile_manager.py` | User profile management                                          |

---

## Conclusion

The POC provides a solid foundation for:

- ✅ Eye tracking core functionality
- ✅ Basic calibration system
- ✅ Smooth pursuit test patterns
- ✅ Basic metrics and reporting

Major gaps requiring implementation:

- 🔴 Saccade testing with latency/accuracy metrics
- 🔴 Fixation stability testing (BCEA)
- 🔴 Pursuit gain calculation (critical for clinical use)
- 🔴 Visualization and export features
- 🔴 Full profile management system
- 🔴 Visual angle conversions throughout

**Estimated Implementation Effort**: 40-60 hours for full requirements coverage
