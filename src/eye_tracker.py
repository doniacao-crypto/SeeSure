"""
Eye Tracker Module
Uses MediaPipe FaceLandmarker for eye/iris detection and 3D head pose estimation.
Updated for MediaPipe 0.10+ (tasks API).
"""

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from dataclasses import dataclass
from typing import Optional, Tuple, List
import urllib.request
import os


@dataclass
class EyeData:
    """Data structure for eye tracking results."""
    # Iris centers (normalized 0-1 within eye region)
    left_iris_center: Optional[Tuple[float, float]] = None
    right_iris_center: Optional[Tuple[float, float]] = None

    # Iris centers in pixel coordinates
    left_iris_pixel: Optional[Tuple[int, int]] = None
    right_iris_pixel: Optional[Tuple[int, int]] = None

    # Eye corners for reference
    left_eye_corners: Optional[List[Tuple[int, int]]] = None
    right_eye_corners: Optional[List[Tuple[int, int]]] = None

    # Head pose (rotation in degrees)
    head_pitch: float = 0.0  # Up/down
    head_yaw: float = 0.0    # Left/right
    head_roll: float = 0.0   # Tilt

    # Face detected flag
    face_detected: bool = False

    # Blink detection
    left_ear: float = 0.0   # Left Eye Aspect Ratio
    right_ear: float = 0.0  # Right Eye Aspect Ratio
    is_blinking: bool = False


class EyeTracker:
    """
    Eye tracking using MediaPipe FaceLandmarker (tasks API).
    Provides iris detection and 3D head pose estimation.
    """

    # MediaPipe FaceMesh landmark indices
    # Left eye landmarks
    LEFT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
    LEFT_IRIS_INDICES = [468, 469, 470, 471, 472]  # Iris landmarks (center + 4 points)

    # Right eye landmarks
    RIGHT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
    RIGHT_IRIS_INDICES = [473, 474, 475, 476, 477]  # Iris landmarks (center + 4 points)

    # Eye landmarks for EAR (Eye Aspect Ratio) blink detection
    # These are the 6 landmarks forming the eye contour for EAR calculation
    # Format: [outer_corner, upper1, upper2, inner_corner, lower2, lower1]
    LEFT_EYE_EAR_INDICES = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE_EAR_INDICES = [362, 385, 387, 263, 373, 380]

    # EAR threshold for blink detection (typical range: 0.15-0.25)
    EAR_THRESHOLD = 0.21
    # Number of consecutive frames with low EAR to confirm blink
    EAR_CONSEC_FRAMES = 2

    # Key facial landmarks for head pose estimation
    # Nose tip, chin, left eye corner, right eye corner, left mouth, right mouth
    POSE_LANDMARKS = [1, 152, 33, 263, 61, 291]

    # 3D model points for head pose estimation (generic face model)
    MODEL_POINTS = np.array([
        (0.0, 0.0, 0.0),          # Nose tip
        (0.0, -330.0, -65.0),     # Chin
        (-225.0, 170.0, -135.0),  # Left eye corner
        (225.0, 170.0, -135.0),   # Right eye corner
        (-150.0, -150.0, -125.0), # Left mouth corner
        (150.0, -150.0, -125.0)   # Right mouth corner
    ], dtype=np.float64)

    # Model download URL
    MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
    MODEL_PATH = os.path.join(os.path.dirname(__file__), "face_landmarker.task")

    def __init__(self, max_faces: int = 1, min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5):
        """
        Initialize the eye tracker.

        Args:
            max_faces: Maximum number of faces to detect
            min_detection_confidence: Minimum confidence for face detection
            min_tracking_confidence: Minimum confidence for face tracking
        """
        # Download model if not present
        self._ensure_model_exists()

        # Create FaceLandmarker
        base_options = python.BaseOptions(model_asset_path=self.MODEL_PATH)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=True,
            num_faces=max_faces,
            min_face_detection_confidence=min_detection_confidence,
            min_face_presence_confidence=min_tracking_confidence,
            min_tracking_confidence=min_tracking_confidence,
            running_mode=vision.RunningMode.IMAGE
        )
        self.face_landmarker = vision.FaceLandmarker.create_from_options(options)

        # Camera matrix placeholder (will be set based on frame size)
        self.camera_matrix = None
        self.dist_coeffs = np.zeros((4, 1))  # Assume no lens distortion

        # Blink detection state
        self._blink_counter = 0
        self._ear_threshold = self.EAR_THRESHOLD

    def _ensure_model_exists(self):
        """Download the model file if it doesn't exist."""
        if not os.path.exists(self.MODEL_PATH):
            print(f"Downloading face landmarker model to {self.MODEL_PATH}...")
            urllib.request.urlretrieve(self.MODEL_URL, self.MODEL_PATH)
            print("Model downloaded successfully.")

    def _init_camera_matrix(self, frame_width: int, frame_height: int):
        """Initialize camera matrix based on frame dimensions."""
        focal_length = frame_width
        center = (frame_width / 2, frame_height / 2)
        self.camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)

    def _get_iris_center(self, landmarks, iris_indices: List[int],
                         frame_width: int, frame_height: int) -> Tuple[Tuple[int, int], Tuple[float, float]]:
        """
        Calculate iris center from landmarks.

        Returns:
            Tuple of (pixel_coords, normalized_coords)
        """
        # Get iris center landmark (first index is the center)
        iris_center = landmarks[iris_indices[0]]

        # Pixel coordinates
        px = int(iris_center.x * frame_width)
        py = int(iris_center.y * frame_height)

        return (px, py), (iris_center.x, iris_center.y)

    def _get_eye_corners(self, landmarks, eye_indices: List[int],
                         frame_width: int, frame_height: int) -> List[Tuple[int, int]]:
        """Get eye corner pixel coordinates."""
        corners = []
        # Use first and middle landmarks as approximate corners
        for idx in [eye_indices[0], eye_indices[8]]:  # Outer and inner corners
            lm = landmarks[idx]
            corners.append((int(lm.x * frame_width), int(lm.y * frame_height)))
        return corners

    def _calculate_iris_position_in_eye(self, iris_center: Tuple[int, int],
                                         eye_corners: List[Tuple[int, int]],
                                         frame_width: int = 640,
                                         frame_height: int = 480) -> Tuple[float, float]:
        """
        Calculate normalized iris position for gaze estimation.

        Uses a combination of:
        1. Iris position relative to eye center (for within-eye gaze direction)
        2. Overall iris position in frame (for head position compensation)

        Returns:
            Tuple of (x, y) in 0-1 range representing gaze direction
        """
        if len(eye_corners) < 2:
            return (0.5, 0.5)

        outer_corner = eye_corners[0]
        inner_corner = eye_corners[1]

        # Calculate eye center
        eye_center_x = (outer_corner[0] + inner_corner[0]) / 2
        eye_center_y = (outer_corner[1] + inner_corner[1]) / 2

        # Calculate eye width for normalization
        eye_width = np.sqrt((inner_corner[0] - outer_corner[0])**2 +
                           (inner_corner[1] - outer_corner[1])**2)

        if eye_width < 1:
            return (0.5, 0.5)

        # Method 1: Iris offset from eye center (sensitive to gaze direction)
        # This captures the actual eye movement within the socket
        iris_offset_x = (iris_center[0] - eye_center_x) / eye_width
        iris_offset_y = (iris_center[1] - eye_center_y) / (eye_width * 0.5)

        # Map to 0-1 range (typical range is about -0.3 to +0.3)
        # Scale up to make it more sensitive
        gaze_x = 0.5 + iris_offset_x * 1.5  # Scale factor to increase sensitivity
        gaze_y = 0.5 + iris_offset_y * 1.5

        # Clamp to valid range
        gaze_x = np.clip(gaze_x, 0.0, 1.0)
        gaze_y = np.clip(gaze_y, 0.0, 1.0)

        return (gaze_x, gaze_y)

    def _calculate_ear(self, landmarks, eye_indices: List[int]) -> float:
        """
        Calculate Eye Aspect Ratio (EAR) for blink detection.

        EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)

        Where:
        - p1, p4 are the horizontal eye corners
        - p2, p6 and p3, p5 are the vertical eye landmarks

        Returns:
            EAR value (typically 0.2-0.3 when open, < 0.2 when closed)
        """
        def distance(p1, p2) -> float:
            return np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

        # Get the 6 eye landmarks
        p1 = landmarks[eye_indices[0]]  # Outer corner
        p2 = landmarks[eye_indices[1]]  # Upper 1
        p3 = landmarks[eye_indices[2]]  # Upper 2
        p4 = landmarks[eye_indices[3]]  # Inner corner
        p5 = landmarks[eye_indices[4]]  # Lower 2
        p6 = landmarks[eye_indices[5]]  # Lower 1

        # Calculate vertical distances
        vertical1 = distance(p2, p6)
        vertical2 = distance(p3, p5)

        # Calculate horizontal distance
        horizontal = distance(p1, p4)

        if horizontal < 0.001:  # Avoid division by zero
            return 0.0

        # EAR formula
        ear = (vertical1 + vertical2) / (2.0 * horizontal)
        return ear

    def _detect_blink(self, left_ear: float, right_ear: float) -> bool:
        """
        Detect blink based on EAR values.

        Args:
            left_ear: Left eye EAR
            right_ear: Right eye EAR

        Returns:
            True if blink is detected
        """
        avg_ear = (left_ear + right_ear) / 2.0

        if avg_ear < self._ear_threshold:
            self._blink_counter += 1
        else:
            self._blink_counter = 0

        # Confirm blink after consecutive frames
        return self._blink_counter >= self.EAR_CONSEC_FRAMES

    def set_ear_threshold(self, threshold: float):
        """Set custom EAR threshold for blink detection."""
        self._ear_threshold = max(0.1, min(0.4, threshold))

    def _estimate_head_pose(self, landmarks, frame_width: int, frame_height: int) -> Tuple[float, float, float]:
        """
        Estimate 3D head pose using PnP algorithm.

        Returns:
            Tuple of (pitch, yaw, roll) in degrees
        """
        # Get 2D image points for pose landmarks
        image_points = np.array([
            (landmarks[idx].x * frame_width, landmarks[idx].y * frame_height)
            for idx in self.POSE_LANDMARKS
        ], dtype=np.float64)

        # Solve PnP
        success, rotation_vec, translation_vec = cv2.solvePnP(
            self.MODEL_POINTS,
            image_points,
            self.camera_matrix,
            self.dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )

        if not success:
            return (0.0, 0.0, 0.0)

        # Convert rotation vector to rotation matrix
        rotation_mat, _ = cv2.Rodrigues(rotation_vec)

        # Get Euler angles
        pose_mat = cv2.hconcat([rotation_mat, translation_vec])
        _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(pose_mat)

        pitch = euler_angles[0][0]
        yaw = euler_angles[1][0]
        roll = euler_angles[2][0]

        return (pitch, yaw, roll)

    def process_frame(self, frame: np.ndarray) -> EyeData:
        """
        Process a video frame and extract eye tracking data.

        Args:
            frame: BGR image from webcam

        Returns:
            EyeData with tracking results
        """
        eye_data = EyeData()

        frame_height, frame_width = frame.shape[:2]

        # Initialize camera matrix if needed
        if self.camera_matrix is None:
            self._init_camera_matrix(frame_width, frame_height)

        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Create MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Process frame
        results = self.face_landmarker.detect(mp_image)

        if not results.face_landmarks or len(results.face_landmarks) == 0:
            return eye_data

        # Get first face landmarks
        face_landmarks = results.face_landmarks[0]
        eye_data.face_detected = True

        # Check if we have enough landmarks (need iris landmarks which are indices 468+)
        if len(face_landmarks) < 478:
            # No iris landmarks available
            return eye_data

        # Extract left eye data
        eye_data.left_iris_pixel, left_norm = self._get_iris_center(
            face_landmarks, self.LEFT_IRIS_INDICES, frame_width, frame_height
        )
        eye_data.left_eye_corners = self._get_eye_corners(
            face_landmarks, self.LEFT_EYE_INDICES, frame_width, frame_height
        )
        eye_data.left_iris_center = self._calculate_iris_position_in_eye(
            eye_data.left_iris_pixel, eye_data.left_eye_corners
        )

        # Extract right eye data
        eye_data.right_iris_pixel, right_norm = self._get_iris_center(
            face_landmarks, self.RIGHT_IRIS_INDICES, frame_width, frame_height
        )
        eye_data.right_eye_corners = self._get_eye_corners(
            face_landmarks, self.RIGHT_EYE_INDICES, frame_width, frame_height
        )
        eye_data.right_iris_center = self._calculate_iris_position_in_eye(
            eye_data.right_iris_pixel, eye_data.right_eye_corners
        )

        # Estimate head pose
        pitch, yaw, roll = self._estimate_head_pose(face_landmarks, frame_width, frame_height)
        eye_data.head_pitch = pitch
        eye_data.head_yaw = yaw
        eye_data.head_roll = roll

        # Calculate EAR for blink detection
        eye_data.left_ear = self._calculate_ear(face_landmarks, self.LEFT_EYE_EAR_INDICES)
        eye_data.right_ear = self._calculate_ear(face_landmarks, self.RIGHT_EYE_EAR_INDICES)
        eye_data.is_blinking = self._detect_blink(eye_data.left_ear, eye_data.right_ear)

        return eye_data

    def draw_debug(self, frame: np.ndarray, eye_data: EyeData) -> np.ndarray:
        """
        Draw debug visualization on frame.

        Args:
            frame: Original BGR frame
            eye_data: Eye tracking data

        Returns:
            Frame with debug drawings
        """
        debug_frame = frame.copy()

        if not eye_data.face_detected:
            cv2.putText(debug_frame, "No face detected", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            return debug_frame

        # Draw iris centers
        if eye_data.left_iris_pixel:
            cv2.circle(debug_frame, eye_data.left_iris_pixel, 3, (0, 255, 0), -1)
        if eye_data.right_iris_pixel:
            cv2.circle(debug_frame, eye_data.right_iris_pixel, 3, (0, 255, 0), -1)

        # Draw eye corners
        if eye_data.left_eye_corners:
            for corner in eye_data.left_eye_corners:
                cv2.circle(debug_frame, corner, 2, (255, 0, 0), -1)
        if eye_data.right_eye_corners:
            for corner in eye_data.right_eye_corners:
                cv2.circle(debug_frame, corner, 2, (255, 0, 0), -1)

        # Draw head pose info
        pose_text = f"Pitch: {eye_data.head_pitch:.1f} Yaw: {eye_data.head_yaw:.1f} Roll: {eye_data.head_roll:.1f}"
        cv2.putText(debug_frame, pose_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Draw iris position info
        if eye_data.left_iris_center and eye_data.right_iris_center:
            avg_x = (eye_data.left_iris_center[0] + eye_data.right_iris_center[0]) / 2
            avg_y = (eye_data.left_iris_center[1] + eye_data.right_iris_center[1]) / 2
            iris_text = f"Iris pos: ({avg_x:.2f}, {avg_y:.2f})"
            cv2.putText(debug_frame, iris_text, (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Draw EAR and blink status
        avg_ear = (eye_data.left_ear + eye_data.right_ear) / 2
        blink_color = (0, 0, 255) if eye_data.is_blinking else (0, 255, 0)
        ear_text = f"EAR: {avg_ear:.2f}"
        if eye_data.is_blinking:
            ear_text += " [BLINK]"
        cv2.putText(debug_frame, ear_text, (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, blink_color, 1)

        return debug_frame

    def release(self):
        """Release resources."""
        pass  # FaceLandmarker doesn't need explicit cleanup
