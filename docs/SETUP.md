# Eye Movement Assessment System - Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Install packages
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python run.py
```

## Features

| Feature                | Description                                            |
| ---------------------- | ------------------------------------------------------ |
| **Eye Tracking**       | MediaPipe FaceMesh with iris detection (478 landmarks) |
| **Head Compensation**  | Full 3D head pose estimation via PnP algorithm         |
| **Calibration**        | 9-point grid calibration with profile saving           |
| **Tests**              | Smooth pursuit (H/V/Circular/Figure-8) + Saccades      |
| **Real-time Feedback** | Gaze cursor overlay during tests                       |
| **Reports**            | Accuracy, smoothness, and tracking metrics             |

## Test Patterns

- **Horizontal**: Tests left-right smooth pursuit
- **Vertical**: Tests up-down smooth pursuit
- **Circular**: Tests full range of motion
- **Figure-8**: Tests complex pursuit coordination
- **Random Points**: Tests saccadic (quick jump) movements

## Accuracy Notes

- Typical accuracy: ~2-3° visual angle (50-100px on standard monitor)
- Calibration significantly improves accuracy
- Good lighting is essential
- Keep face 40-60cm from camera

## Architecture

```
src/
├── eye_tracker.py       # MediaPipe integration, iris + head pose
├── gaze_estimator.py    # Calibration system + gaze mapping
├── smooth_pursuit_test.py # Test logic + metrics
└── main_app.py          # PyQt6 GUI application
```

## Disclaimer

This is a screening tool only. Consult an eye care professional for diagnosis.
