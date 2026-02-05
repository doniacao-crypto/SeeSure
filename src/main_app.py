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
from PyQt6.QtGui import QImage, QPixmap, QFont

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
        left_panel = self._create_left_panel()
        main_layout.addWidget(left_panel)

        # Right panel - stacked views
        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_home_view())
        
        # Calibration and test views
        self.calibration_widget = CalibrationWidget(self.gaze_estimator)
        self.stack.addWidget(self.calibration_widget)
        
        self.test_widget = TestWidget(self.gaze_estimator)
        self.stack.addWidget(self.test_widget)
        
        # Results view
        self.stack.addWidget(self._create_results_view())
        
        # Initialize last result storage
        self._last_result: Optional[TestResult] = None
        
        main_layout.addWidget(self.stack)
        self._apply_theme()

    def _create_left_panel(self) -> QFrame:
        """Create the left control panel with camera preview and controls."""
        panel = QFrame()
        panel.setMaximumWidth(400)
        panel.setStyleSheet("QFrame { background-color: #2d2d44; border-radius: 10px; }")
        layout = QVBoxLayout(panel)

        # Camera preview
        self.camera_label = QLabel("Camera Preview")
        self.camera_label.setFixedSize(360, 270)
        self.camera_label.setStyleSheet("background-color: #1a1a2e; border-radius: 5px;")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.camera_label)

        # Status indicators
        layout.addWidget(self._create_status_group())
        
        # Calibration controls
        layout.addWidget(self._create_calibration_group())
        
        # Test configuration
        layout.addWidget(self._create_test_config_group())
        
        layout.addStretch()
        return panel

    def _create_status_group(self) -> QGroupBox:
        """Create status indicators group."""
        group = QGroupBox("Status")
        layout = QVBoxLayout(group)

        self.face_status = QLabel("Face: Not Detected")
        self.face_status.setStyleSheet("color: #ff6b6b;")
        layout.addWidget(self.face_status)

        self.calibration_status = QLabel("Calibration: Not Done")
        self.calibration_status.setStyleSheet("color: #ffd93d;")
        layout.addWidget(self.calibration_status)

        self.head_pose_label = QLabel("Head Pose: --")
        layout.addWidget(self.head_pose_label)

        return group

    def _create_calibration_group(self) -> QGroupBox:
        """Create calibration controls group."""
        group = QGroupBox("Calibration")
        layout = QVBoxLayout(group)

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
        layout.addWidget(self.calibrate_btn)

        btn_layout = QHBoxLayout()
        self.save_profile_btn = QPushButton("Save Profile")
        self.load_profile_btn = QPushButton("Load Profile")
        btn_layout.addWidget(self.save_profile_btn)
        btn_layout.addWidget(self.load_profile_btn)
        layout.addLayout(btn_layout)

        return group

    def _create_test_config_group(self) -> QGroupBox:
        """Create test configuration group."""
        group = QGroupBox("Test Configuration")
        layout = QVBoxLayout(group)

        layout.addWidget(QLabel("Pattern:"))
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems([
            "Horizontal", "Vertical", "Circular", "Figure-8", "Random Points"
        ])
        layout.addWidget(self.pattern_combo)

        layout.addWidget(QLabel("Duration (seconds):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 60)
        self.duration_spin.setValue(10)
        layout.addWidget(self.duration_spin)

        layout.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(5)
        layout.addWidget(self.speed_slider)

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
        layout.addWidget(self.start_test_btn)

        return group

    def _create_home_view(self) -> QWidget:
        """Create the home/welcome view."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("Eye Movement Assessment System")
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #74b9ff;")
        layout.addWidget(title)

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
        layout.addWidget(instructions)

        return widget

    def _create_results_view(self) -> QWidget:
        """Create the results display view."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("Test Results")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #74b9ff;")
        layout.addWidget(title)

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
        layout.addWidget(self.results_text)

        # Button row
        btn_layout = QHBoxLayout()
        
        self.back_btn = QPushButton("Back to Home")
        self.back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        btn_layout.addWidget(self.back_btn)

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
        btn_layout.addWidget(self.export_full_btn)

        layout.addLayout(btn_layout)
        return widget

    def _apply_theme(self):
        """Apply the dark theme stylesheet."""
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
