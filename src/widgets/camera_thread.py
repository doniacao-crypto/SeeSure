"""
Camera Thread for Eye Tracking Application.
Handles camera capture in a separate thread to avoid blocking UI.
"""

import cv2
import numpy as np
import time

from PyQt6.QtCore import QThread, pyqtSignal

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from eye_tracker import EyeTracker, EyeData


class CameraThread(QThread):
    """Thread for camera capture to avoid blocking UI."""
    # Signal now includes capture timestamp for timing synchronization
    frame_ready = pyqtSignal(np.ndarray, EyeData, float)

    def __init__(self, eye_tracker: EyeTracker):
        super().__init__()
        self.eye_tracker = eye_tracker
        self.running = False
        self.cap = None

        # FPS measurement
        self._frame_times = []
        self._fps_window = 30  # Rolling window for FPS calculation
        self._actual_fps = 0.0

    def run(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        self.running = True
        while self.running:
            ret, frame = self.cap.read()
            # Capture timestamp immediately after reading frame
            capture_time = time.time()

            if ret:
                # Update FPS measurement
                self._frame_times.append(capture_time)
                if len(self._frame_times) > self._fps_window:
                    self._frame_times.pop(0)
                if len(self._frame_times) >= 2:
                    time_span = self._frame_times[-1] - self._frame_times[0]
                    if time_span > 0:
                        self._actual_fps = (len(self._frame_times) - 1) / time_span

                # Mirror the frame for more intuitive interaction
                frame = cv2.flip(frame, 1)
                eye_data = self.eye_tracker.process_frame(frame)
                # Pass capture timestamp with frame
                self.frame_ready.emit(frame, eye_data, capture_time)

            # Reduced sleep to minimize latency (was 16ms)
            self.msleep(5)

    def get_actual_fps(self) -> float:
        """Get the measured actual FPS."""
        return self._actual_fps

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.wait()
