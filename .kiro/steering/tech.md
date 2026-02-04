# Technology Stack - Eye Movement Assessment System

## Core Technologies

| Component           | Technology               | Version | Rationale                                |
| ------------------- | ------------------------ | ------- | ---------------------------------------- |
| **Language**        | Python                   | 3.10+   | ML ecosystem, scientific computing       |
| **GUI Framework**   | PyQt6                    | 6.6+    | Cross-platform, professional UI          |
| **Eye Tracking**    | MediaPipe FaceLandmarker | 0.10+   | 478 landmarks, iris detection, head pose |
| **Computer Vision** | OpenCV                   | 4.8+    | Camera capture, image processing         |
| **ML/Scientific**   | NumPy, SciPy             | Latest  | Numerical computing, interpolation       |
| **Data Analysis**   | Pandas                   | 2.0+    | Data manipulation, export                |
| **Visualization**   | Matplotlib               | 3.7+    | Charts, trajectory plots                 |

## Architecture Decisions

### Eye Tracking Pipeline

```
Webcam → MediaPipe FaceLandmarker → Iris Detection → Gaze Estimation → Screen Mapping
                    ↓
              Head Pose (3D) → Compensation → Calibrated Gaze Position
```

### Key Design Choices

1. **MediaPipe Tasks API**: Using new tasks API (not legacy solutions) for better performance
2. **RBF Interpolation**: Radial Basis Function for smooth gaze mapping from calibration
3. **PnP Head Pose**: OpenCV solvePnP for 3D head orientation estimation
4. **Temporal Smoothing**: Weighted moving average to reduce jitter

### Data Flow

```
EyeTracker.process_frame() → EyeData
                              ↓
GazeEstimator.estimate_gaze() → Screen Coordinates
                              ↓
SmoothPursuitTest.record_frame() → TestResult
                              ↓
generate_report() → Clinical Report
```

## Performance Requirements

| Metric     | Target           | Current POC               |
| ---------- | ---------------- | ------------------------- |
| Frame Rate | ≥30 FPS          | ~30 FPS                   |
| Latency    | <50ms            | ~30ms                     |
| Accuracy   | <2° visual angle | ~2-3° (needs improvement) |
| CPU Usage  | <30%             | ~20%                      |

## File Structure

```
src/
├── eye_tracker.py      # MediaPipe integration, iris/head detection
├── gaze_estimator.py   # Calibration, gaze mapping, profiles
├── smooth_pursuit_test.py  # Test protocols, metrics
└── main_app.py         # PyQt6 GUI application
```

## Dependencies

See `requirements.txt` for full list. Key dependencies:

- mediapipe>=0.10.9
- opencv-python>=4.8.0
- PyQt6>=6.6.0
- scipy>=1.11.0
