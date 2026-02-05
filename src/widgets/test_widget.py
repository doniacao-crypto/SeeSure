"""
Test Widget for Eye Tracking Application.
Handles the smooth pursuit test visualization and data collection.
"""

from typing import Optional

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from gaze_estimator import GazeEstimator
from eye_tracker import EyeData
from smooth_pursuit_test import SmoothPursuitTest, TestConfig, TestResult


class TestWidget(QWidget):
    """Widget for the smooth pursuit test."""
    test_complete = pyqtSignal(TestResult)

    def __init__(self, gaze_estimator: GazeEstimator, parent=None):
        super().__init__(parent)
        self.gaze_estimator = gaze_estimator
        self.test: Optional[SmoothPursuitTest] = None
        self._pending_config: Optional[TestConfig] = None

        self.is_testing = False
        self.current_gaze: Optional[tuple] = None
        self.show_gaze_cursor = True

        # Capture timestamp for synchronization
        self._last_capture_time: Optional[float] = None

        self.setStyleSheet("background-color: #0f0f23;")

        # Timer for test updates
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_test_complete)

    def start_test(self, config: TestConfig):
        """Start the test after widget is properly sized."""
        # Store config and delay start to ensure widget is resized after fullscreen
        self._pending_config = config
        QTimer.singleShot(100, self._begin_test)

    def _begin_test(self):
        """Actually begin the test after widget is properly sized."""
        if self._pending_config is None:
            return

        config = self._pending_config
        self._pending_config = None

        # Use widget's actual dimensions, not screen dimensions
        # This ensures target positions stay within the visible area
        width = self.width()
        height = self.height()

        self.test = SmoothPursuitTest(width, height, config)
        self.test.start()
        self.is_testing = True
        self.timer.start(100)  # Check every 100ms
        self.update()

    def resizeEvent(self, event):
        """Handle widget resize to update test dimensions."""
        super().resizeEvent(event)
        # Update test dimensions if test is running
        if self.test is not None and self.is_testing:
            self.test.update_screen_dimensions(self.width(), self.height())
        self.update()

    def process_eye_data(self, eye_data: EyeData, capture_time: Optional[float] = None):
        """Process eye data during test.

        Args:
            eye_data: Eye tracking data
            capture_time: Timestamp when frame was captured (for synchronization)
        """
        if not self.is_testing or self.test is None:
            return

        # Store capture time for synchronized recording
        self._last_capture_time = capture_time

        # Get gaze position
        gaze = self.gaze_estimator.estimate_gaze(eye_data)
        self.current_gaze = gaze

        # Record frame with capture timestamp for proper synchronization
        if gaze:
            self.test.record_frame(
                gaze[0], gaze[1],
                eye_data.head_pitch, eye_data.head_yaw,
                eye_data.face_detected,
                capture_time=capture_time
            )
        else:
            self.test.record_frame(
                None, None,
                eye_data.head_pitch, eye_data.head_yaw,
                eye_data.face_detected,
                capture_time=capture_time
            )

        self.update()

    def _check_test_complete(self):
        """Check if test is complete."""
        if self.test and self.test.is_complete():
            self.timer.stop()
            self.is_testing = False
            result = self.test.stop()
            if result:
                self.test_complete.emit(result)

    def paintEvent(self, event):
        """Draw test elements."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(15, 15, 35))

        if not self.is_testing or self.test is None:
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 24))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                           "Configure test settings and click 'Start Test'")
            return

        # Draw target
        target_x, target_y = self.test.get_target_position()
        target_size = self.test.config.target_size

        # Target glow effect
        for i in range(3):
            alpha = 100 - i * 30
            size = target_size + i * 10
            painter.setBrush(QColor(255, 200, 0, alpha))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(target_x - size//2, target_y - size//2, size, size)

        # Target center
        painter.setBrush(QColor(255, 255, 0))
        painter.drawEllipse(target_x - target_size//2, target_y - target_size//2,
                           target_size, target_size)

        # Draw gaze cursor if enabled
        if self.show_gaze_cursor and self.current_gaze:
            gx, gy = self.current_gaze
            # Gaze cursor (crosshair)
            painter.setPen(QPen(QColor(0, 255, 255), 2))
            painter.drawLine(gx - 15, gy, gx + 15, gy)
            painter.drawLine(gx, gy - 15, gx, gy + 15)
            painter.drawEllipse(gx - 8, gy - 8, 16, 16)

        # Draw progress bar
        elapsed = self.test.get_elapsed_time()
        total = self.test.config.duration_seconds
        progress = min(elapsed / total, 1.0)

        bar_width = 400
        bar_height = 10
        bar_x = (self.width() - bar_width) // 2
        bar_y = 30

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(50, 50, 50))
        painter.drawRect(bar_x, bar_y, bar_width, bar_height)

        painter.setBrush(QColor(0, 200, 100))
        painter.drawRect(bar_x, bar_y, int(bar_width * progress), bar_height)

        # Time remaining
        remaining = max(0, total - elapsed)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 14))
        painter.drawText(bar_x + bar_width + 10, bar_y + 10, f"{remaining:.1f}s")
