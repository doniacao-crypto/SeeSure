"""
Constants for Eye Movement Assessment System.
Centralizes magic numbers and configuration defaults.
"""

# =============================================================================
# Camera & Frame Rate
# =============================================================================
DEFAULT_FPS = 30.0                    # Default camera frame rate (Hz)
DEFAULT_FRAME_WIDTH = 640             # Default camera width (pixels)
DEFAULT_FRAME_HEIGHT = 480            # Default camera height (pixels)

# =============================================================================
# Eye Tracking Thresholds
# =============================================================================
EAR_THRESHOLD = 0.21                  # Eye Aspect Ratio for blink detection
EAR_CONSEC_FRAMES = 2                 # Consecutive frames to confirm blink

# =============================================================================
# Saccade Detection
# =============================================================================
SACCADE_VELOCITY_THRESHOLD = 30.0     # Velocity threshold for saccade (deg/s)
MICROSACCADE_VELOCITY_THRESHOLD = 15.0  # Velocity threshold for microsaccade (deg/s)
MIN_SACCADE_DURATION_MS = 20.0        # Minimum saccade duration (ms)
MICROSACCADE_MAX_AMPLITUDE_DEG = 1.0  # Maximum microsaccade amplitude (degrees)

# =============================================================================
# Gaze Estimation
# =============================================================================
HEAD_PITCH_FACTOR = 15.0              # Pixels per degree for pitch compensation
HEAD_YAW_FACTOR = 15.0                # Pixels per degree for yaw compensation

# =============================================================================
# Statistical Thresholds
# =============================================================================
BCEA_PROBABILITY = 0.68               # Probability for BCEA (≈1 SD, 68% contour)

# =============================================================================
# Filter Parameters
# =============================================================================
ONEURO_MINCUTOFF = 1.0                # 1-Euro filter minimum cutoff frequency
ONEURO_BETA = 0.007                   # 1-Euro filter speed coefficient
ONEURO_DCUTOFF = 1.0                  # 1-Euro filter derivative cutoff

# =============================================================================
# Screen Defaults
# =============================================================================
DEFAULT_SCREEN_WIDTH = 1920           # Default screen width (pixels)
DEFAULT_SCREEN_HEIGHT = 1080          # Default screen height (pixels)
DEFAULT_VIEWING_DISTANCE_CM = 60.0    # Default viewing distance (cm)

# =============================================================================
# Test Configuration Defaults
# =============================================================================
DEFAULT_TEST_DURATION_SECONDS = 10.0  # Default test duration
DEFAULT_TARGET_SIZE = 20              # Default target dot size (pixels)
DEFAULT_TEST_SPEED = 0.5              # Default target speed multiplier
DEFAULT_CALIBRATION_GRID_SIZE = 3     # 3x3 calibration grid
DEFAULT_SAMPLES_PER_POINT = 30        # Samples to collect per calibration point

# =============================================================================
# UI Constants
# =============================================================================
CAMERA_PREVIEW_WIDTH = 360            # Camera preview width in UI
CAMERA_PREVIEW_HEIGHT = 270           # Camera preview height in UI
