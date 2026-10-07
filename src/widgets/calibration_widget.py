"""
Calibration Widget for Eye Tracking Application.
Handles the calibration process with visual feedback.
"""

import numpy as np
import time

from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from gaze_estimator import GazeEstimator
from eye_tracker import EyeData


class CalibrationWidget(QWidget):
    """Widget for the calibration process."""
    calibration_complete = pyqtSignal()

    def __init__(self, gaze_estimator: GazeEstimator, parent=None):
        super().__init__(parent)
        self.gaze_estimator = gaze_estimator

        # Calibration grid (3x3 = 9 points)
        self.grid_size = 3
        self.current_point_index = 0
        self.calibration_points = []
        self.samples_per_point = 20  # Frames per (point, pose) cell
        self.current_samples = 0

        # The grid is walked once per head pose. Without this spread the pitch/yaw coefficients are
        # fitted to landmark noise, and gaze collapses as soon as the subject turns their head --
        # a 5 deg turn was enough to throw the estimate to the screen edge. Holding a pose while
        # still fixating the dot is what makes head compensation learnable.
        self.head_poses = [
            ("Look straight ahead", "Head centred, facing the screen"),
            ("Turn your head slightly LEFT", "Keep looking at the dot with your eyes"),
            ("Turn your head slightly RIGHT", "Keep looking at the dot with your eyes"),
        ]
        self.current_pose_index = 0

        self.is_calibrating = False
        self.countdown = 0

        # Settling time state: let the eye fixate before collecting
        self._settling = False
        self._settling_start_time = 0.0
        self._settling_duration = 0.5  # 500ms settling period
        self._collecting = False  # True once start_collecting_samples has been called

        # Timer for countdown and sampling
        self.timer = QTimer()
        self.timer.timeout.connect(self._on_timer)

        self.setStyleSheet("background-color: #1a1a2e;")

    def resizeEvent(self, event):
        """Handle resize to regenerate calibration points."""
        super().resizeEvent(event)
        # Only regenerate if not in the middle of calibration
        if not self.is_calibrating:
            self._generate_points()
        self.update()

    def _generate_points(self):
        """Generate calibration point positions based on current widget size."""
        self.calibration_points = []
        # Use widget's own geometry, not screen geometry
        width = self.width()
        height = self.height()

        # Ensure we have valid dimensions
        if width <= 0 or height <= 0:
            return

        from constants import DEFAULT_CALIBRATION_MARGIN
        margin_x = int(width * DEFAULT_CALIBRATION_MARGIN)
        margin_y = int(height * DEFAULT_CALIBRATION_MARGIN)

        for row in range(self.grid_size):
            for col in range(self.grid_size):
                if self.grid_size > 1:
                    x = margin_x + col * (width - 2 * margin_x) // (self.grid_size - 1)
                    y = margin_y + row * (height - 2 * margin_y) // (self.grid_size - 1)
                else:
                    x = width // 2
                    y = height // 2
                self.calibration_points.append((x, y))

    def start_calibration(self):
        """Start the calibration process."""
        # Regenerate points based on current widget size (after fullscreen)
        # Use a short delay to ensure the widget has been resized
        QTimer.singleShot(100, self._begin_calibration)

    def _begin_calibration(self):
        """Actually begin calibration after widget is properly sized."""
        # Generate points based on actual widget dimensions
        self._generate_points()

        # Set gaze estimator screen size to match widget size
        self.gaze_estimator.start_calibration()
        self.gaze_estimator.screen_width = self.width()
        self.gaze_estimator.screen_height = self.height()

        self.current_point_index = 0
        self.current_pose_index = 0
        self.current_samples = 0
        self._settling = False
        self._settling_start_time = 0.0
        self._collecting = False
        self.is_calibrating = True
        self.countdown = 3  # 3 second countdown before first point

        self.timer.start(1000)  # 1 second intervals for countdown
        self.update()

    def process_eye_data(self, eye_data: EyeData):
        """Process eye data during calibration."""
        if not self.is_calibrating or self.countdown > 0:
            return

        if self.current_point_index >= len(self.calibration_points):
            return

        # Handle settling period: wait for eye to fixate on target
        if self._settling:
            if (time.time() - self._settling_start_time) < self._settling_duration:
                self.update()
                return
            # Settling complete, begin sample collection
            self._settling = False
            self._collecting = True
            self.gaze_estimator.start_collecting_samples()

        # Collect sample using multi-sample API
        if self._collecting:
            if self.gaze_estimator.add_calibration_sample(eye_data, time.time()):
                self.current_samples += 1

        # Check if we have enough samples for this point
        if self.current_samples >= self.samples_per_point:
            point = self.calibration_points[self.current_point_index]
            self.gaze_estimator.finish_collecting_samples(point[0], point[1])
            self._collecting = False
            self.current_samples = 0
            self.current_point_index += 1
            self.countdown = 2  # Short countdown between points

            if self.current_point_index >= len(self.calibration_points):
                # Grid done for this head pose -- move to the next pose, or finish.
                self.current_pose_index += 1
                if self.current_pose_index >= len(self.head_poses):
                    self._finish_calibration()
                else:
                    self.current_point_index = 0
                    self.countdown = 5  # Longer pause: the subject must change head pose
                    self.timer.start(1000)
            else:
                self.timer.start(1000)

        self.update()

    def _on_timer(self):
        """Handle timer for countdown."""
        self.countdown -= 1
        if self.countdown <= 0:
            self.timer.stop()
            # Start settling period before collecting samples
            self._settling = True
            self._settling_start_time = time.time()
            self._collecting = False
        self.update()

    def _finish_calibration(self):
        """Finish the calibration process."""
        self.is_calibrating = False
        self.timer.stop()

        if self.gaze_estimator.finish_calibration():
            quality = self.gaze_estimator.get_calibration_quality()

            # Report the held-out error, not avg_error_px. avg_error_px scores the model on the rows
            # it was fitted to, so it looks near-perfect even when the model generalises terribly.
            message = (
                f"Calibration complete.\n\n"
                f"Held-out error: {quality['cv_error_px']:.1f} px "
                f"(error at screen locations not used for fitting)\n"
                f"Training-fit error: {quality['avg_error_px']:.1f} px "
                f"(optimistic - same rows the model was fitted to)\n\n"
                f"Head yaw spread: {quality['head_yaw_spread_deg']:.1f} deg\n"
                f"Head pitch spread: {quality['head_pitch_spread_deg']:.1f} deg\n"
                f"Samples: {quality['training_rows']} rows over {quality['points']} points"
            )

            if not quality['head_pose_ok']:
                QMessageBox.warning(
                    self, "Calibration Complete - Head Pose Warning",
                    message + (
                        "\n\nWARNING: head pose barely varied during calibration, so the model "
                        "could not learn head compensation. Gaze will degrade sharply as soon as "
                        "the subject turns their head. Redo the calibration and hold the requested "
                        "head poses."
                    )
                )
            else:
                QMessageBox.information(self, "Calibration Complete", message)

            self.calibration_complete.emit()
        else:
            QMessageBox.warning(
                self, "Calibration Failed",
                "Calibration failed. Please try again with better lighting."
            )

    def paintEvent(self, event):
        """Draw calibration points and status."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(26, 26, 46))

        if not self.is_calibrating:
            # Draw instructions
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 24))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                           "Click 'Start Calibration' to begin")
            return

        # Draw all calibration points (dimmed)
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        for i, (x, y) in enumerate(self.calibration_points):
            if i < self.current_point_index:
                painter.setBrush(QColor(0, 200, 0))  # Completed - green
            elif i == self.current_point_index:
                continue  # Draw current point separately
            else:
                painter.setBrush(QColor(50, 50, 50))  # Future - dark
            painter.drawEllipse(x - 15, y - 15, 30, 30)

        # Draw current point (highlighted)
        if self.current_point_index < len(self.calibration_points):
            x, y = self.calibration_points[self.current_point_index]

            if self.countdown > 0:
                # Countdown display
                painter.setPen(QColor(255, 255, 0))
                painter.setBrush(QColor(255, 255, 0, 100))
                painter.drawEllipse(x - 40, y - 40, 80, 80)

                painter.setPen(QColor(255, 255, 255))
                painter.setFont(QFont("Arial", 48, QFont.Weight.Bold))
                painter.drawText(x - 20, y + 15, str(self.countdown))
            else:
                # Active point - pulsing animation
                pulse = abs(np.sin(time.time() * 4)) * 10 + 20
                painter.setPen(QPen(QColor(255, 100, 100), 3))
                painter.setBrush(QColor(255, 50, 50))
                painter.drawEllipse(int(x - pulse), int(y - pulse), int(pulse * 2), int(pulse * 2))

                # Progress indicator
                progress = self.current_samples / self.samples_per_point
                painter.setPen(QPen(QColor(0, 255, 0), 4))
                painter.drawArc(x - 35, y - 35, 70, 70, 90 * 16, int(-progress * 360 * 16))

        # Draw the head-pose instruction for this round, centred and prominent: the subject has to
        # actually change head pose between rounds or the calibration learns no head compensation.
        if self.current_pose_index < len(self.head_poses):
            title, subtitle = self.head_poses[self.current_pose_index]
            painter.setPen(QColor(255, 210, 80))
            painter.setFont(QFont("Arial", 26, QFont.Weight.Bold))
            painter.drawText(0, 70, self.width(), 40,
                             Qt.AlignmentFlag.AlignHCenter, title)
            painter.setPen(QColor(200, 200, 200))
            painter.setFont(QFont("Arial", 15))
            painter.drawText(0, 112, self.width(), 28,
                             Qt.AlignmentFlag.AlignHCenter, subtitle)

        # Draw status text
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 16))
        status = (
            f"Pose {self.current_pose_index + 1} of {len(self.head_poses)}  |  "
            f"Point {self.current_point_index + 1} of {len(self.calibration_points)}"
        )
        if self.countdown > 0:
            status += f" - Look at the point in {self.countdown}..."
        else:
            status += " - Keep looking at the red dot"
        painter.drawText(20, 40, status)
