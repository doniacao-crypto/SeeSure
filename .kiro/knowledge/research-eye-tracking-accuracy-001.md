# Research: Webcam Eye Tracking Accuracy Improvement Algorithms

**Date**: 2025-12-18
**Query**: How to improve webcam-based eye movement detection accuracy

## Executive Summary

Current implementation uses MediaPipe FaceLandmarker with RBF interpolation for gaze mapping. Research identifies several algorithmic improvements that can achieve 1-2 degree accuracy (compared to typical 3-4 degrees for basic implementations).

## Current Implementation Analysis

### Existing Components

- **Eye Tracker**: MediaPipe FaceLandmarker with iris landmarks (468-477)
- **Gaze Estimator**: RBF interpolation with thin_plate_spline kernel
- **Smoothing**: Simple weighted moving average (window=5)
- **Head Compensation**: Linear pitch/yaw factors

### Identified Limitations

1. Basic smoothing introduces lag without adaptive jitter control
2. RBF interpolation may not extrapolate well outside calibration region
3. No handling for blinks, occlusions, or lighting changes
4. Camera matrix assumes no lens distortion

## Recommended Improvements

### 1. Replace Smoothing with 1-Euro Filter (Priority: HIGH)

**What**: Adaptive low-pass filter that reduces jitter at low speeds and reduces lag at high speeds.

**Why**: The 1-Euro filter achieves SEM of 0.004mm vs 0.015mm for Kalman filters while being computationally cheap.

**Implementation**:

```python
class OneEuroFilter:
    def __init__(self, freq, mincutoff=1.0, beta=0.0, dcutoff=1.0):
        self.freq = freq
        self.mincutoff = mincutoff
        self.beta = beta
        self.dcutoff = dcutoff
        self.x_filter = LowPassFilter()
        self.dx_filter = LowPassFilter()
        self.last_time = None

    def __call__(self, x, timestamp=None):
        if self.last_time and timestamp:
            self.freq = 1.0 / (timestamp - self.last_time)
        self.last_time = timestamp

        dx = (x - self.x_filter.last_value) * self.freq if self.x_filter.last_value else 0
        edx = self.dx_filter.filter(dx, alpha(self.freq, self.dcutoff))
        cutoff = self.mincutoff + self.beta * abs(edx)
        return self.x_filter.filter(x, alpha(self.freq, cutoff))

def alpha(rate, cutoff):
    tau = 1.0 / (2 * math.pi * cutoff)
    te = 1.0 / rate
    return 1.0 / (1.0 + tau / te)
```

**Tuning**: Start with mincutoff=1.0, beta=0.0. Decrease mincutoff to reduce slow jitter, increase beta to reduce high-speed lag.

### 2. Add Kalman Filter for State Estimation (Priority: MEDIUM-HIGH)

**What**: Extended Kalman Filter (EKF) that models gaze position and velocity as state.

**Why**: Reduces noise by 300%+ while maintaining responsiveness. Handles prediction during blinks/occlusions.

**Key Features**:

- Observation models for both position and velocity
- Adaptive measurement noise (less filtering during saccades)
- Can predict gaze during brief tracking losses

**Implementation Approach**:

```python
class GazeKalmanFilter:
    def __init__(self):
        # State: [x, y, vx, vy]
        self.state = np.zeros(4)
        self.P = np.eye(4) * 1000  # Covariance

        # Process noise (tune based on expected movement)
        self.Q = np.diag([0.1, 0.1, 1.0, 1.0])

        # Measurement noise (adaptive)
        self.R_fixation = np.diag([1.0, 1.0])  # Low during fixation
        self.R_saccade = np.diag([10.0, 10.0])  # High during saccade
```

### 3. Improved Calibration Model (Priority: HIGH)

**What**: Replace RBF with polynomial regression + ridge regularization.

**Why**:

- Second-order polynomials are standard in eye tracking
- Ridge regression reduces overfitting, especially with few calibration points
- Better extrapolation outside calibration region

**Polynomial Model**:

```python
# Standard 2nd-order polynomial with 6 coefficients per axis
# screen_x = a0 + a1*ix + a2*iy + a3*ix² + a4*iy² + a5*ix*iy
# Plus head pose terms: a6*pitch + a7*yaw

from sklearn.linear_model import Ridge

def build_calibration_model(calibration_points):
    features = []
    for p in calibration_points:
        ix, iy = (p.left_iris[0] + p.right_iris[0])/2, (p.left_iris[1] + p.right_iris[1])/2
        features.append([
            1, ix, iy, ix**2, iy**2, ix*iy,
            p.head_pitch, p.head_yaw, p.head_pitch**2, p.head_yaw**2
        ])

    X = np.array(features)
    y_x = np.array([p.screen_x for p in calibration_points])
    y_y = np.array([p.screen_y for p in calibration_points])

    model_x = Ridge(alpha=1.0).fit(X, y_x)
    model_y = Ridge(alpha=1.0).fit(X, y_y)
    return model_x, model_y
```

### 4. Deep Learning Gaze Estimation (Priority: MEDIUM)

**What**: Replace MediaPipe iris-based estimation with trained CNN models.

**Options**:
| Model | Accuracy | Notes |
|-------|----------|-------|
| MPIIGaze | ~3.4° | Good for laptop use |
| ETH-XGaze | ~3.1° | Better head pose range |
| GazeFollower | 1.11cm (~0.8°) | Trained on 32M images |
| Custom ResNet-50 | ~2.5° | 33% better than VGG-16 |

**GazeFollower** is particularly promising with:

- 1.11 cm accuracy with calibration
- 0.92 cm with personalized fine-tuning
- Open source Python implementation

**Trade-off**: More computation but significantly better accuracy.

### 5. Blink Detection and Handling (Priority: MEDIUM)

**What**: Detect blinks to filter invalid gaze data and prevent artifacts.

**Methods**:

1. **EAR (Eye Aspect Ratio)**: Fast, uses existing landmarks

   ```python
   def eye_aspect_ratio(eye_landmarks):
       vertical1 = dist(eye_landmarks[1], eye_landmarks[5])
       vertical2 = dist(eye_landmarks[2], eye_landmarks[4])
       horizontal = dist(eye_landmarks[0], eye_landmarks[3])
       return (vertical1 + vertical2) / (2.0 * horizontal)

   # EAR < 0.2 typically indicates blink
   ```

2. **RT-BENE**: Deep learning blink detection, more robust

**During Blink**: Use Kalman filter prediction or hold last valid position.

### 6. Improve Head Pose Compensation (Priority: MEDIUM)

**Current**: Linear compensation with fixed factors (15 px/deg pitch, 20 px/deg yaw).

**Improvement**: Learn compensation factors during calibration.

```python
def learn_head_compensation(calibration_points):
    # Compute gaze error at each point
    # Fit linear model: error = f(head_pose_delta)
    # This personalizes the compensation factors
    pass
```

### 7. Multi-Sample Calibration Points (Priority: HIGH)

**What**: Collect multiple samples per calibration target and average.

**Why**: Reduces noise in calibration data, leading to better model fit.

```python
# Instead of single sample per point:
samples_per_point = 10
delay_between_samples = 100  # ms

for target in calibration_targets:
    samples = []
    for _ in range(samples_per_point):
        samples.append(get_eye_data())
        time.sleep(delay_between_samples / 1000)

    # Average the samples (exclude outliers)
    averaged_sample = robust_average(samples)
    calibration_profile.add_point(target, averaged_sample)
```

## Implementation Priority

| Priority | Improvement                    | Effort | Impact      |
| -------- | ------------------------------ | ------ | ----------- |
| 1        | 1-Euro Filter                  | Low    | High        |
| 2        | Multi-sample calibration       | Low    | Medium-High |
| 3        | Polynomial + Ridge calibration | Medium | High        |
| 4        | Blink detection (EAR)          | Low    | Medium      |
| 5        | Kalman Filter                  | Medium | Medium-High |
| 6        | GazeFollower integration       | High   | Very High   |

## Expected Accuracy Improvements

| Configuration                  | Expected Accuracy |
| ------------------------------ | ----------------- |
| Current (MediaPipe + RBF)      | ~3-4°             |
| + 1-Euro Filter                | ~2.5-3°           |
| + Better calibration           | ~2-2.5°           |
| + Kalman Filter                | ~1.5-2°           |
| + Deep learning (GazeFollower) | ~0.8-1.2°         |

## Sources

1. [Deep learning models for webcam eye tracking](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11133145/)
2. [Webcam eye tracking close to laboratory standards](https://link.springer.com/article/10.3758/s13428-023-02237-8)
3. [MediaPipe Iris and Kalman Filter](https://www.atlantis-press.com/proceedings/icsice-24/126011300)
4. [1-Euro Filter](https://github.com/casiez/OneEuroFilter)
5. [High-Accuracy Gaze Estimation for Interpolation-Based Methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC8482219/)
6. [GazeFollower](https://dl.acm.org/doi/10.1145/3729410)
7. [Real-Time Gaze Estimation Using CNN](https://www.mdpi.com/2073-431X/14/2/57)
8. [ETH-XGaze Dataset](https://dl.acm.org/doi/10.1007/978-3-030-58558-7_22)
