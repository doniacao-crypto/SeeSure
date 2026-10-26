# EyeExam 👁️

**Clinical-grade eye movement assessment using standard webcam hardware.**

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![PyQt6](https://img.shields.io/badge/UI-PyQt6-green.svg)](https://pypi.org/project/PyQt6/)
[![MediaPipe](https://img.shields.io/badge/tracking-MediaPipe-orange.svg)](https://mediapipe.dev)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](./LICENSE)

---

## Overview

EyeExam is a desktop application that performs professional eye movement assessments using a standard webcam. It provides clinical-grade metrics typically requiring expensive specialized equipment.

### Key Features

- **Smooth Pursuit Testing** — Track a moving target to assess pursuit gain and accuracy
- **Saccade Testing** — Measure rapid eye movements between points
- **Fixation Testing** — Assess fixation stability with BCEA and microsaccade detection
- **Real-time Calibration** — 9-point calibration with quality feedback
- **Clinical Metrics** — Visual angle accuracy, pursuit gain, phase lag, saccade detection
- **Data Export** — JSON and CSV export for analysis

---

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Webcam
- macOS, Windows, or Linux

### Installation

```bash
# Clone the repository
git clone https://github.com/ibetterai/EyeExam.git
cd EyeExam

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python src/main_app.py
```

---

## Usage

### 1. Calibration

1. Launch the application
2. Click **"Start Calibration"**
3. Work through the three head-pose levels (head centred, then slightly left, then slightly
   right). Between levels a countdown gives the patient 3 seconds to move their head before
   the next level starts — hold the new pose once the count reaches zero.
4. Follow the 9 dots in each level with your eyes
5. Read the calibration report (held-out error and head-pose spread) when it finishes

### 2. Running Tests

1. Select a test pattern:
   - **Horizontal/Vertical** — Smooth pursuit
   - **Circular/Figure-8** — Complex pursuit
   - **Random Points** — Saccade testing
   - **Fixation** — Stability assessment
2. Set duration and speed
3. Click **"Start Test"**
4. Follow the yellow target with your eyes

### 3. Viewing Results

After each test:

- View metrics summary on screen
- Export to JSON (full data) or CSV (spreadsheet-friendly)
- Results saved to `results/` directory

---

## Clinical Metrics

| Metric            | Description                       | Normal Range |
| ----------------- | --------------------------------- | ------------ |
| Pursuit Gain      | Eye velocity / Target velocity    | 0.9 - 1.0    |
| Accuracy          | RMS error in degrees visual angle | < 2°         |
| Phase Lag         | Temporal delay behind target      | < 100 ms     |
| Saccade Rate      | Catch-up saccades per second      | < 1 Hz       |
| BCEA              | Fixation stability area           | < 1 deg²     |
| Microsaccade Rate | Small fixation movements          | 1-2 Hz       |

### What the report shows

| Reading          | What it means                                                        |
| ---------------- | -------------------------------------------------------------------- |
| Tracking Rate    | Share of frames that produced a usable gaze estimate (data validity) |
| Direction Match  | How often the gaze moved in the same direction as the target         |
| Speed Match      | How closely the gaze speed matched the target speed                  |
| Pursuit Gain     | Clinical: eye velocity / target velocity                             |
| Accuracy         | Clinical: RMS error in degrees of visual angle                       |

The thresholds are **provisional and not clinically validated** — see
`docs/clinical/sign-off-register.md`. A low pursuit gain reflects the gaze estimate's own
gain as much as the subject's tracking, so read it with the tracking rate next to it.

---

## Architecture

```
src/
├── main_app.py          # Application entry point
├── eye_tracker.py       # MediaPipe face landmark tracking
├── gaze_estimator.py    # Calibration and gaze estimation
├── smooth_pursuit_test.py # Test patterns and recording
├── metrics.py           # Clinical metrics calculation
├── filters.py           # Signal filtering (1-Euro, Kalman)
├── constants.py         # Configuration constants
└── widgets/             # UI components
    ├── camera_thread.py
    ├── calibration_widget.py
    └── test_widget.py
```

---

## Development

### Running Tests

```bash
# Run all unit tests
python -m pytest tests/unit/ -v

# Run with coverage
python -m pytest tests/unit/ --cov=src
```

### Code Quality

```bash
# Type checking
mypy src/

# Linting
flake8 src/
```

---

## Configuration

Key parameters can be adjusted in `src/constants.py`:

```python
# Detection thresholds
SACCADE_VELOCITY_THRESHOLD = 30.0  # deg/s
EAR_THRESHOLD = 0.21               # Blink detection

# Test defaults
DEFAULT_TEST_DURATION_SECONDS = 10.0
DEFAULT_FPS = 30.0
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License — see [LICENSE](./LICENSE) for details.

---

## Acknowledgments

- [MediaPipe](https://mediapipe.dev) for face landmark detection
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the UI framework
- Clinical metrics based on established oculomotor research standards
