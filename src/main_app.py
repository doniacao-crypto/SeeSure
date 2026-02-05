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
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QImage, QPixmap

from eye_tracker import EyeTracker, EyeData
from gaze_estimator import GazeEstimator
from smooth_pursuit_test import (
    TestConfig, TargetPattern, TestResult, generate_report
)

# Import UI widgets from separate modules
from widgets import CameraThread, CalibrationWidget, TestWidget


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
