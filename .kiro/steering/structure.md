# Code Structure - Eye Movement Assessment System

## Directory Organization

```
EyeExam/
├── .kiro/
│   ├── steering/           # Project context and guidelines
│   ├── specs/              # Feature specifications
│   │   └── eye-movement-assessment/
│   └── knowledge/          # Research and error documentation
├── src/
│   ├── __init__.py
│   ├── eye_tracker.py      # Core eye tracking module
│   ├── gaze_estimator.py   # Calibration and gaze mapping
│   ├── smooth_pursuit_test.py  # Test protocols
│   ├── main_app.py         # PyQt6 application
│   └── face_landmarker.task  # MediaPipe model (auto-downloaded)
├── tests/                  # Unit and integration tests
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── profiles/               # User calibration profiles
├── reports/                # Generated assessment reports
├── docs/
│   └── SETUP.md
├── requirements.txt
├── run.py                  # Application entry point
└── CLAUDE.md
```

## Module Responsibilities

### eye_tracker.py

- MediaPipe FaceLandmarker initialization
- Frame processing and landmark extraction
- Iris center calculation
- 3D head pose estimation (PnP)
- Debug visualization

### gaze_estimator.py

- Calibration point collection
- RBF interpolation model building
- Screen coordinate estimation
- Head pose compensation
- Profile save/load (JSON)
- Calibration quality metrics

### smooth_pursuit_test.py

- Test pattern generation (H/V/circular/figure-8/random)
- Frame recording during tests
- Metrics calculation (accuracy, smoothness, tracking ratio)
- Report generation

### main_app.py

- PyQt6 MainWindow and widgets
- Camera thread management
- Calibration UI workflow
- Test execution UI
- Results display

## Naming Conventions

| Type        | Convention  | Example                               |
| ----------- | ----------- | ------------------------------------- |
| Classes     | PascalCase  | `EyeTracker`, `GazeEstimator`         |
| Functions   | snake_case  | `process_frame()`, `estimate_gaze()`  |
| Constants   | UPPER_SNAKE | `LEFT_IRIS_INDICES`, `MODEL_POINTS`   |
| Files       | snake_case  | `eye_tracker.py`, `gaze_estimator.py` |
| Dataclasses | PascalCase  | `EyeData`, `CalibrationPoint`         |

## Code Patterns

### Dataclasses for Data Transfer

```python
@dataclass
class EyeData:
    left_iris_center: Optional[Tuple[float, float]] = None
    face_detected: bool = False
```

### Type Hints Throughout

```python
def process_frame(self, frame: np.ndarray) -> EyeData:
```

### Configuration via Dataclasses

```python
@dataclass
class TestConfig:
    pattern: TargetPattern = TargetPattern.HORIZONTAL
    duration_seconds: float = 10.0
```

## Testing Strategy

- **Unit Tests**: Individual function/method testing
- **Integration Tests**: Module interaction testing
- **Accuracy Tests**: Validation against known positions
- **Performance Tests**: FPS and latency benchmarks
