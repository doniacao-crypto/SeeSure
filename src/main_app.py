"""
Eye Tracking Assessment Application
Main PyQt6 application with calibration, testing, and visualization.
"""

import sys
import cv2
import numpy as np
from pathlib import Path
from typing import Optional
import time

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QStackedWidget, QFrame,
    QProgressBar, QTextEdit, QSlider, QGroupBox, QMessageBox,
    QFileDialog, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont

from eye_tracker import EyeTracker, EyeData
from gaze_estimator import GazeEstimator
from smooth_pursuit_test import (
    SmoothPursuitTest, TestConfig, TargetPattern,
    TestResult, generate_report
)


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
        self.samples_per_point = 30  # Frames to average per point
        self.current_samples = 0

        self.is_calibrating = False
        self.countdown = 0

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

        margin_x = int(width * 0.1)
        margin_y = int(height * 0.1)

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
        self.current_samples = 0
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

        # Collect sample
        point = self.calibration_points[self.current_point_index]
        if self.gaze_estimator.add_calibration_point(point[0], point[1], eye_data, time.time()):
            self.current_samples += 1

        # Check if we have enough samples for this point
        if self.current_samples >= self.samples_per_point:
            self.current_samples = 0
            self.current_point_index += 1
            self.countdown = 2  # Short countdown between points

            if self.current_point_index >= len(self.calibration_points):
                self._finish_calibration()
            else:
                self.timer.start(1000)

        self.update()

    def _on_timer(self):
        """Handle timer for countdown."""
        self.countdown -= 1
        if self.countdown <= 0:
            self.timer.stop()
        self.update()

    def _finish_calibration(self):
        """Finish the calibration process."""
        self.is_calibrating = False
        self.timer.stop()

        if self.gaze_estimator.finish_calibration():
            quality = self.gaze_estimator.get_calibration_quality()
            QMessageBox.information(
                self, "Calibration Complete",
                f"Calibration successful!\n\n"
                f"Quality Score: {quality['quality']*100:.1f}%\n"
                f"Average Error: {quality['avg_error_px']:.1f} pixels\n"
                f"Points Used: {quality['points']}"
            )
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

        # Draw status text
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 16))
        status = f"Point {self.current_point_index + 1} of {len(self.calibration_points)}"
        if self.countdown > 0:
            status += f" - Look at the point in {self.countdown}..."
        else:
            status += " - Keep looking at the red dot"
        painter.drawText(20, 40, status)


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


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Eye Movement Assessment System")
        self.setMinimumSize(1200, 800)

        # Core components
        self.eye_tracker = EyeTracker()
        self.gaze_estimator = GazeEstimator()

        # Camera thread
        self.camera_thread = CameraThread(self.eye_tracker)
        self.camera_thread.frame_ready.connect(self._on_frame_ready)

        # Current eye data
        self.current_eye_data: Optional[EyeData] = None

        self._setup_ui()
        self._connect_signals()

        # Start camera
        self.camera_thread.start()

    def _setup_ui(self):
        """Set up the user interface."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)

        # Left panel - camera preview and controls
        left_panel = QFrame()
        left_panel.setMaximumWidth(400)
        left_panel.setStyleSheet("QFrame { background-color: #2d2d44; border-radius: 10px; }")
        left_layout = QVBoxLayout(left_panel)

        # Camera preview
        self.camera_label = QLabel("Camera Preview")
        self.camera_label.setFixedSize(360, 270)
        self.camera_label.setStyleSheet("background-color: #1a1a2e; border-radius: 5px;")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.camera_label)

        # Status indicators
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)

        self.face_status = QLabel("Face: Not Detected")
        self.face_status.setStyleSheet("color: #ff6b6b;")
        status_layout.addWidget(self.face_status)

        self.calibration_status = QLabel("Calibration: Not Done")
        self.calibration_status.setStyleSheet("color: #ffd93d;")
        status_layout.addWidget(self.calibration_status)

        self.head_pose_label = QLabel("Head Pose: --")
        status_layout.addWidget(self.head_pose_label)

        left_layout.addWidget(status_group)

        # Calibration controls
        calib_group = QGroupBox("Calibration")
        calib_layout = QVBoxLayout(calib_group)

        self.calibrate_btn = QPushButton("Start Calibration")
        self.calibrate_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c5ce7;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #5f4dd0; }
        """)
        calib_layout.addWidget(self.calibrate_btn)

        calib_btn_layout = QHBoxLayout()
        self.save_profile_btn = QPushButton("Save Profile")
        self.load_profile_btn = QPushButton("Load Profile")
        calib_btn_layout.addWidget(self.save_profile_btn)
        calib_btn_layout.addWidget(self.load_profile_btn)
        calib_layout.addLayout(calib_btn_layout)

        left_layout.addWidget(calib_group)

        # Test configuration
        test_group = QGroupBox("Test Configuration")
        test_layout = QVBoxLayout(test_group)

        test_layout.addWidget(QLabel("Pattern:"))
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems([
            "Horizontal", "Vertical", "Circular", "Figure-8", "Random Points"
        ])
        test_layout.addWidget(self.pattern_combo)

        test_layout.addWidget(QLabel("Duration (seconds):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 60)
        self.duration_spin.setValue(10)
        test_layout.addWidget(self.duration_spin)

        test_layout.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(5)
        test_layout.addWidget(self.speed_slider)

        self.start_test_btn = QPushButton("Start Test")
        self.start_test_btn.setStyleSheet("""
            QPushButton {
                background-color: #00b894;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #00a884; }
        """)
        test_layout.addWidget(self.start_test_btn)

        left_layout.addWidget(test_group)
        left_layout.addStretch()

        main_layout.addWidget(left_panel)

        # Right panel - main view (stacked widget)
        self.stack = QStackedWidget()

        # Home view
        home_widget = QWidget()
        home_layout = QVBoxLayout(home_widget)
        home_label = QLabel("Eye Movement Assessment System")
        home_label.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        home_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        home_label.setStyleSheet("color: #74b9ff;")
        home_layout.addWidget(home_label)

        instructions = QLabel(
            "1. Ensure good lighting and face the camera\n"
            "2. Run calibration (look at each point when prompted)\n"
            "3. Select a test pattern and start the test\n"
            "4. Follow the yellow dot with your eyes\n"
            "5. View your results and recommendations"
        )
        instructions.setFont(QFont("Arial", 14))
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setStyleSheet("color: #b2bec3;")
        home_layout.addWidget(instructions)

        self.stack.addWidget(home_widget)

        # Calibration view
        self.calibration_widget = CalibrationWidget(self.gaze_estimator)
        self.stack.addWidget(self.calibration_widget)

        # Test view
        self.test_widget = TestWidget(self.gaze_estimator)
        self.stack.addWidget(self.test_widget)

        # Results view
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_label = QLabel("Test Results")
        results_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        results_label.setStyleSheet("color: #74b9ff;")
        results_layout.addWidget(results_label)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d44;
                color: #dfe6e9;
                font-family: monospace;
                font-size: 12px;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        results_layout.addWidget(self.results_text)

        # Button row
        results_btn_layout = QHBoxLayout()

        self.back_btn = QPushButton("Back to Home")
        self.back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        results_btn_layout.addWidget(self.back_btn)

        self.export_full_btn = QPushButton("Export Full Data")
        self.export_full_btn.setStyleSheet("""
            QPushButton {
                background-color: #00b894;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #00a884; }
        """)
        self.export_full_btn.clicked.connect(self._export_full_data)
        results_btn_layout.addWidget(self.export_full_btn)

        results_layout.addLayout(results_btn_layout)

        self.stack.addWidget(results_widget)

        # Initialize last result storage
        self._last_result: Optional[TestResult] = None

        main_layout.addWidget(self.stack)

        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a2e; }
            QGroupBox {
                color: #dfe6e9;
                font-weight: bold;
                border: 1px solid #4a4a6a;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title { subcontrol-position: top left; padding: 0 5px; }
            QLabel { color: #dfe6e9; }
            QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #3d3d5c;
                color: #dfe6e9;
                border: 1px solid #4a4a6a;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton {
                background-color: #4a4a6a;
                color: #dfe6e9;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #5a5a7a; }
            QSlider::groove:horizontal {
                background: #4a4a6a;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #6c5ce7;
                width: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
        """)

    def _connect_signals(self):
        """Connect UI signals."""
        self.calibrate_btn.clicked.connect(self._start_calibration)
        self.save_profile_btn.clicked.connect(self._save_profile)
        self.load_profile_btn.clicked.connect(self._load_profile)
        self.start_test_btn.clicked.connect(self._start_test)
        self.calibration_widget.calibration_complete.connect(self._on_calibration_complete)
        self.test_widget.test_complete.connect(self._on_test_complete)

    def _on_frame_ready(self, frame: np.ndarray, eye_data: EyeData, capture_time: float):
        """Handle new camera frame.

        Args:
            frame: Camera frame
            eye_data: Eye tracking data
            capture_time: Timestamp when frame was captured
        """
        self.current_eye_data = eye_data

        # Update camera preview with debug visualization
        debug_frame = self.eye_tracker.draw_debug(frame, eye_data)

        # Convert to QPixmap
        rgb_frame = cv2.cvtColor(debug_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img).scaled(
            self.camera_label.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.camera_label.setPixmap(pixmap)

        # Update status including FPS
        actual_fps = self.camera_thread.get_actual_fps()
        if eye_data.face_detected:
            self.face_status.setText(f"Face: ✓ Detected ({actual_fps:.1f} FPS)")
            self.face_status.setStyleSheet("color: #00b894;")
        else:
            self.face_status.setText(f"Face: ✗ Not Detected ({actual_fps:.1f} FPS)")
            self.face_status.setStyleSheet("color: #ff6b6b;")

        self.head_pose_label.setText(
            f"Head: P={eye_data.head_pitch:.1f}° Y={eye_data.head_yaw:.1f}° R={eye_data.head_roll:.1f}°"
        )

        # Forward to active widget with capture timestamp
        if self.stack.currentWidget() == self.calibration_widget:
            self.calibration_widget.process_eye_data(eye_data)
        elif self.stack.currentWidget() == self.test_widget:
            self.test_widget.process_eye_data(eye_data, capture_time)

    def _start_calibration(self):
        """Start calibration process."""
        self.stack.setCurrentWidget(self.calibration_widget)
        self.calibration_widget.showFullScreen()
        self.calibration_widget.start_calibration()

    def _on_calibration_complete(self):
        """Handle calibration completion."""
        self.calibration_widget.showNormal()
        self.stack.setCurrentIndex(0)
        self.calibration_status.setText("Calibration: ✓ Done")
        self.calibration_status.setStyleSheet("color: #00b894;")

    def _save_profile(self):
        """Save calibration profile."""
        if not self.gaze_estimator.is_calibrated:
            QMessageBox.warning(self, "No Calibration", "Please calibrate first.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Profile", "", "JSON Files (*.json)"
        )
        if filepath:
            if self.gaze_estimator.save_profile(filepath):
                QMessageBox.information(self, "Saved", "Profile saved successfully.")
            else:
                QMessageBox.warning(self, "Error", "Failed to save profile.")

    def _load_profile(self):
        """Load calibration profile."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Load Profile", "", "JSON Files (*.json)"
        )
        if filepath:
            if self.gaze_estimator.load_profile(filepath):
                self.calibration_status.setText("Calibration: ✓ Loaded")
                self.calibration_status.setStyleSheet("color: #00b894;")
                QMessageBox.information(self, "Loaded", "Profile loaded successfully.")
            else:
                QMessageBox.warning(self, "Error", "Failed to load profile.")

    def _start_test(self):
        """Start the eye movement test."""
        # Get test configuration
        patterns = [
            TargetPattern.HORIZONTAL,
            TargetPattern.VERTICAL,
            TargetPattern.CIRCULAR,
            TargetPattern.FIGURE_EIGHT,
            TargetPattern.RANDOM_POINTS
        ]
        pattern = patterns[self.pattern_combo.currentIndex()]

        config = TestConfig(
            pattern=pattern,
            duration_seconds=self.duration_spin.value(),
            speed=self.speed_slider.value() / 10.0
        )

        self.stack.setCurrentWidget(self.test_widget)
        self.test_widget.showFullScreen()
        self.test_widget.start_test(config)

    def _on_test_complete(self, result: TestResult):
        """Handle test completion."""
        self.test_widget.showNormal()

        # Store result for export
        self._last_result = result

        # Auto-save summary to results directory
        try:
            summary_path = result.save_summary()
            save_message = f"\n[Results auto-saved to: {summary_path}]"
        except Exception as e:
            save_message = f"\n[Warning: Failed to auto-save results: {e}]"

        # Generate and display report
        report = generate_report(result)
        self.results_text.setText(report + save_message)

        self.stack.setCurrentIndex(3)  # Results view

    def _export_full_data(self):
        """Export full test data including all frame-by-frame details."""
        if self._last_result is None:
            QMessageBox.warning(self, "No Data", "No test results to export.")
            return

        try:
            filepath = self._last_result.save_full_data()
            QMessageBox.information(
                self, "Export Successful",
                f"Full test data exported to:\n{filepath}\n\n"
                f"Includes {len(self._last_result.frames)} frames with "
                "gaze/target positions and head pose data."
            )
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", f"Failed to export data: {e}")

    def closeEvent(self, event):
        """Clean up on close."""
        self.camera_thread.stop()
        self.eye_tracker.release()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    # Ensure window comes to front on macOS
    window.raise_()
    window.activateWindow()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
