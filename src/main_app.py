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
from session_history import SessionHistoryManager, SessionSummary

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
        self.session_history = SessionHistoryManager()

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
        
        # History view
        self.stack.addWidget(self._create_history_view())
        
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
        
        # History button
        self.history_btn = QPushButton("📋 View History")
        self.history_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a6a;
                color: white;
                padding: 8px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #5a5a7a; }
        """)
        self.history_btn.setToolTip("View and manage past test sessions")
        self.history_btn.clicked.connect(self._show_history)
        layout.addWidget(self.history_btn)
        
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
        self.calibrate_btn.setToolTip("Run 9-point calibration to map your eye movements to screen coordinates")
        layout.addWidget(self.calibrate_btn)

        btn_layout = QHBoxLayout()
        self.save_profile_btn = QPushButton("Save Profile")
        self.save_profile_btn.setToolTip("Save calibration to file for later use")
        self.load_profile_btn = QPushButton("Load Profile")
        self.load_profile_btn.setToolTip("Load a previously saved calibration profile")
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
            "Horizontal", "Vertical", "Circular", "Figure-8", "Random Points", "Fixation"
        ])
        self.pattern_combo.setToolTip(
            "Horizontal/Vertical: Smooth pursuit\n"
            "Circular/Figure-8: Complex pursuit\n"
            "Random Points: Saccade testing\n"
            "Fixation: Stability assessment"
        )
        layout.addWidget(self.pattern_combo)

        layout.addWidget(QLabel("Duration (seconds):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 60)
        self.duration_spin.setValue(10)
        self.duration_spin.setToolTip("Test duration in seconds (5-60)")
        layout.addWidget(self.duration_spin)

        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Speed:"))
        self.speed_label = QLabel("0.5")
        self.speed_label.setStyleSheet("color: #74b9ff; font-weight: bold;")
        speed_row.addWidget(self.speed_label)
        speed_row.addStretch()
        layout.addLayout(speed_row)
        
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(5)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        self.speed_slider.setToolTip("Target movement speed (0.1 = slow, 1.0 = fast)")
        layout.addWidget(self.speed_slider)

        self.start_test_btn = QPushButton("Start Test")
        self.start_test_btn.setToolTip("Start the eye movement test (requires calibration)")
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
        self.export_full_btn.setToolTip("Export complete test data as JSON (all frames)")
        btn_layout.addWidget(self.export_full_btn)

        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.setToolTip("Export data as CSV for spreadsheet analysis")
        self.export_csv_btn.setStyleSheet("""
            QPushButton {
                background-color: #0984e3;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0873c4; }
        """)
        self.export_csv_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(self.export_csv_btn)

        layout.addLayout(btn_layout)
        return widget

    def _create_history_view(self) -> QWidget:
        """Create the session history view."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("📋 Test History")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #74b9ff;")
        layout.addWidget(title)

        # Session list
        from PyQt6.QtWidgets import QListWidget, QListWidgetItem
        self.history_list = QListWidget()
        self.history_list.setStyleSheet("""
            QListWidget {
                background-color: #2d2d44;
                color: #dfe6e9;
                font-family: monospace;
                font-size: 12px;
                border-radius: 5px;
                padding: 10px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #4a4a6a;
            }
            QListWidget::item:selected {
                background-color: #4a4a6a;
            }
        """)
        self.history_list.itemDoubleClicked.connect(self._load_history_session)
        layout.addWidget(self.history_list)

        # Button row
        btn_layout = QHBoxLayout()
        
        back_btn = QPushButton("Back to Home")
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        btn_layout.addWidget(back_btn)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._refresh_history)
        btn_layout.addWidget(refresh_btn)
        
        delete_btn = QPushButton("🗑️ Delete Selected")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #d63031;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #c02020; }
        """)
        delete_btn.clicked.connect(self._delete_history_session)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)
        return widget

    def _show_history(self):
        """Show the history view."""
        self._refresh_history()
        self.stack.setCurrentIndex(4)  # History view index

    def _refresh_history(self):
        """Refresh the history list."""
        self.history_list.clear()
        sessions = self.session_history.list_sessions()
        
        for session in sessions:
            item_text = session.to_display_string()
            from PyQt6.QtWidgets import QListWidgetItem
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, session.filename)
            self.history_list.addItem(item)
        
        if not sessions:
            self.history_list.addItem("No saved sessions found")

    def _load_history_session(self, item):
        """Load and display a historical session."""
        filename = item.data(Qt.ItemDataRole.UserRole)
        if not filename:
            return
        
        data = self.session_history.load_session(filename)
        if data:
            # Display in results view
            report = f"=== Historical Session ===\n"
            report += f"File: {filename}\n"
            report += f"Pattern: {data.get('pattern', 'unknown')}\n"
            report += f"Duration: {data.get('duration_seconds', 0):.1f}s\n\n"
            
            metrics = data.get('metrics', {})
            if metrics:
                report += "=== Metrics ===\n"
                for key, value in metrics.items():
                    if isinstance(value, float):
                        report += f"{key}: {value:.3f}\n"
                    else:
                        report += f"{key}: {value}\n"
            
            self.results_text.setText(report)
            self.stack.setCurrentIndex(3)  # Results view

    def _delete_history_session(self):
        """Delete the selected history session."""
        current = self.history_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a session to delete.")
            return
        
        filename = current.data(Qt.ItemDataRole.UserRole)
        if not filename:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete session '{filename}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.session_history.delete_session(filename):
                self._refresh_history()

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

    def _on_speed_changed(self, value: int):
        """Update speed label when slider changes."""
        speed = value / 10.0
        self.speed_label.setText(f"{speed:.1f}")

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
            TargetPattern.RANDOM_POINTS,
            TargetPattern.FIXATION
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

    def _export_csv(self):
        """Export test data to CSV format for spreadsheet analysis."""
        if self._last_result is None:
            QMessageBox.warning(self, "No Data", "No test results to export.")
            return

        try:
            filepath = self._last_result.save_csv()
            QMessageBox.information(
                self, "Export Successful",
                f"CSV data exported to:\n{filepath}\n\n"
                f"Also created a summary CSV file.\n"
                "Import into Excel, Google Sheets, or any spreadsheet app."
            )
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", f"Failed to export CSV: {e}")

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
