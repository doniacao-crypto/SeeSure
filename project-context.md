# Project Context — EyeExam

## Overview

**EyeExam** is a clinical eye movement assessment application built with PyQt6 and MediaPipe. It provides automated screening for oculomotor function including smooth pursuit, saccades, fixation stability, and gaze accuracy validation.

## Technology Stack

- **Language:** Python 3.11+
- **GUI Framework:** PyQt6
- **Eye Tracking:** MediaPipe Face Mesh (468 landmarks)
- **Signal Processing:** NumPy, SciPy (Kalman filtering, FFT analysis)
- **Visualization:** Matplotlib (trajectories, heatmaps)
- **PDF Reports:** ReportLab
- **Testing:** pytest

## Architecture

### Core Modules

| Module              | Purpose                           |
| ------------------- | --------------------------------- |
| `main_app.py`       | Main window, UI orchestration     |
| `eye_tracker.py`    | MediaPipe face mesh integration   |
| `gaze_estimator.py` | Pupil-based gaze estimation       |
| `filters.py`        | Kalman filter for noise reduction |
| `metrics.py`        | Clinical metrics calculation      |

### Test Modules

| Module                   | Purpose                               |
| ------------------------ | ------------------------------------- |
| `smooth_pursuit_test.py` | Horizontal/vertical pursuit protocols |
| `saccade_test.py`        | Pro-saccade and anti-saccade testing  |
| `validation.py`          | Gaze accuracy validation (9/16-point) |

### Clinical Features

| Module                  | Purpose                        |
| ----------------------- | ------------------------------ |
| `normative_data.py`     | Age-matched reference values   |
| `progress_tracking.py`  | Longitudinal patient tracking  |
| `session_comparison.py` | Multi-session comparison       |
| `pdf_report.py`         | Clinical PDF report generation |
| `patient_manager.py`    | Patient profile CRUD           |

### Enterprise Features

| Module             | Purpose                                     |
| ------------------ | ------------------------------------------- |
| `enterprise.py`    | Branding, multi-clinician, EHR (FHIR), i18n |
| `research_mode.py` | Extended protocols, batch processing        |

### UI Widgets (`src/widgets/`)

| Widget                  | Stack Index | Purpose                     |
| ----------------------- | ----------- | --------------------------- |
| `home_widget.py`        | 0           | Home screen, camera preview |
| `calibration_widget.py` | 1           | 5-point calibration         |
| `test_widget.py`        | 2           | Smooth pursuit testing      |
| `saccade_widget.py`     | 3           | Saccade testing             |
| `validation_widget.py`  | 4           | Accuracy validation         |
| Results                 | 5           | Results display             |
| History                 | 6           | Session history             |

## Key Clinical Metrics

### Smooth Pursuit

- **Pursuit Gain:** Eye velocity / target velocity (normal: 0.85-1.0)
- **Accuracy:** RMS error in degrees
- **Smoothness:** Absence of catch-up saccades
- **BCEA:** Bivariate contour ellipse area for fixation

### Saccades

- **Latency:** Time to saccade onset (normal: 150-250ms)
- **Accuracy:** Landing error in degrees
- **Peak Velocity:** Maximum velocity (deg/s)
- **Error Rate:** Wrong-direction saccades (anti-saccade)

### Validation

- **Accuracy:** Mean error across calibration points
- **Clinical Threshold:** <2° for valid calibration

## Data Flow

1. Camera → MediaPipe Face Mesh → 468 landmarks
2. Landmarks → Gaze Estimator → Raw gaze coordinates
3. Raw gaze → Kalman Filter → Smoothed gaze
4. Smoothed gaze → Metrics Calculator → Clinical scores
5. Scores → PDF Report / CSV Export

## File Structure

```
EyeExam/
├── src/
│   ├── main_app.py
│   ├── widgets/
│   └── [modules listed above]
├── tests/
│   ├── unit/
│   └── integration/
├── data/
│   ├── patients/
│   ├── progress/
│   └── research/
├── results/
└── models/
```

## Development Guidelines

- Branch naming: `x.yy.zzz` (version.category.issue)
- Squash-merge all PRs with conventional commits
- 1 known test failure allowed: `test_smooth_pursuit_test.py::TestTestConfig::test_default_config`
- Target: ≥80% test coverage

## Version History

- `v0.1.0` — Auto-Claude specs (security, refactoring, tests)
- `v0.2.0` — Phase 1: Core clinical testing
- `v0.3.0` — Phase 2: Clinical workflow
- `v0.4.0` — Phase 3: Research & tracking
- `v0.5.0` — Phase 4: Enterprise features
