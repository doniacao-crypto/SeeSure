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
    QFileDialog, QSpinBox, QDoubleSpinBox, QScrollArea,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QCheckBox,
    QListWidget, QListWidgetItem, QTabWidget
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QImage, QPixmap, QFont

from eye_tracker import EyeTracker, EyeData
from gaze_estimator import GazeEstimator
from smooth_pursuit_test import (
    TestConfig, TargetPattern, TestResult, generate_report
)
from session_history import SessionHistoryManager, SessionSummary
from visualization import TrajectoryVisualizer, generate_trajectory_from_result
from saccade_test import SaccadeTest, SaccadeTestConfig, SaccadeTestType, SaccadeTestResult, generate_saccade_report
from validation import ValidationTest, ValidationConfig, ValidationPattern, ValidationResult, generate_validation_report
from pdf_report import PDFReportGenerator, PatientInfo, ClinicInfo
from patient_manager import PatientManager, Patient
from user_manager import UserManager, User, USER_ROLE_ADMIN
from auth_dialog import LoginDialog

# Import UI widgets from separate modules
from widgets import CameraThread, CalibrationWidget, TestWidget, SaccadeWidget, ValidationWidget


class MainWindow(QMainWindow):
    """Main application window."""

    # View indices for QStackedWidget
    HOME_VIEW = 0
    CALIBRATION_VIEW = 1
    TEST_VIEW = 2
    SACCADE_VIEW = 3
    VALIDATION_VIEW = 4
    RESULTS_VIEW = 5
    HISTORY_VIEW = 6
    ADMIN_VIEW = 7

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Eye Movement Assessment System")
        self.setMinimumSize(1200, 800)

        # Core components
        self.eye_tracker = EyeTracker()
        self.gaze_estimator = GazeEstimator(filter_mode='adaptive')
        self.session_history = SessionHistoryManager()
        self.patient_manager = PatientManager()
        self.current_patient: Optional[Patient] = None
        self.user_manager = UserManager()
        self.current_user: Optional[User] = None

        # Camera thread
        self.camera_thread = CameraThread(self.eye_tracker)
        self.camera_thread.frame_ready.connect(self._on_frame_ready)
        self.camera_thread.camera_failed.connect(self._on_camera_failed)
        self.camera_thread.camera_recovered.connect(self._on_camera_recovered)

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
        
        # Saccade test widget
        self.saccade_widget = SaccadeWidget()
        self.saccade_widget.set_gaze_estimator(self.gaze_estimator)
        self.saccade_widget.test_complete.connect(self._on_saccade_complete)
        self.stack.addWidget(self.saccade_widget)
        
        # Validation widget
        self.validation_widget = ValidationWidget()
        self.validation_widget.set_gaze_estimator(self.gaze_estimator)
        self.validation_widget.validation_complete.connect(self._on_validation_complete)
        self.stack.addWidget(self.validation_widget)
        
        # Results view
        self.stack.addWidget(self._create_results_view())
        
        # History view
        self.stack.addWidget(self._create_history_view())

        # Admin panel view (only visible to admins)
        self.stack.addWidget(self._create_admin_view())
        
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
        self.camera_label = QLabel("📷 Initializing camera...")
        self.camera_label.setFixedSize(360, 270)
        self.camera_label.setStyleSheet("""
            background-color: #1a1a2e;
            border-radius: 5px;
            color: #74b9ff;
            font-size: 14px;
        """)
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.camera_label)
        self._camera_initialized = False

        # Status indicators (pinned above scroll area)
        layout.addWidget(self._create_status_group())

        # Scrollable area for remaining controls
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollArea > QWidget > QWidget { background-color: transparent; }
        """)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        # Patient selector
        scroll_layout.addWidget(self._create_patient_group())

        # Calibration controls
        scroll_layout.addWidget(self._create_calibration_group())

        # Test configuration
        scroll_layout.addWidget(self._create_test_config_group())

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
        scroll_layout.addWidget(self.history_btn)

        # Admin button (only visible to admins)
        self.admin_btn = QPushButton("⚙️ Admin Panel")
        self.admin_btn.setStyleSheet("""
            QPushButton {
                background-color: #e17055;
                color: white;
                padding: 8px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #d35400; }
        """)
        self.admin_btn.clicked.connect(self._show_admin)
        self.admin_btn.hide()
        scroll_layout.addWidget(self.admin_btn)

        # Login button
        self.login_btn = QPushButton("🔑 Login / Sign Up")
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #0984e3;
                color: white;
                padding: 8px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0770c2; }
        """)
        self.login_btn.clicked.connect(self._show_login)
        scroll_layout.addWidget(self.login_btn)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        return panel

    def _create_status_group(self) -> QGroupBox:
        """Create status indicators group."""
        group = QGroupBox("Status")
        layout = QVBoxLayout(group)

        self.face_status = QLabel("👤 Face: Not Detected")
        self.face_status.setStyleSheet("color: #ff6b6b;")
        layout.addWidget(self.face_status)

        self.calibration_status = QLabel("🎯 Calibration: Not Done")
        self.calibration_status.setStyleSheet("color: #ffd93d;")
        layout.addWidget(self.calibration_status)

        self.tracking_status = QLabel("👁️ Tracking: Inactive")
        self.tracking_status.setStyleSheet("color: #636e72;")
        layout.addWidget(self.tracking_status)

        self.head_pose_label = QLabel("📐 Head Pose: --")
        layout.addWidget(self.head_pose_label)

        return group

    def _create_patient_group(self) -> QGroupBox:
        """Create patient selection group."""
        group = QGroupBox("Patient")
        layout = QVBoxLayout(group)
        
        # Patient selector dropdown
        self.patient_combo = QComboBox()
        self.patient_combo.addItem("-- No Patient Selected --", None)
        self._refresh_patient_list()
        self.patient_combo.currentIndexChanged.connect(self._on_patient_changed)
        layout.addWidget(self.patient_combo)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        new_btn = QPushButton("➕ New")
        new_btn.setToolTip("Create new patient profile")
        new_btn.clicked.connect(self._create_new_patient)
        btn_layout.addWidget(new_btn)
        
        edit_btn = QPushButton("✏️ Edit")
        edit_btn.setToolTip("Edit selected patient")
        edit_btn.clicked.connect(self._edit_patient)
        btn_layout.addWidget(edit_btn)
        
        layout.addLayout(btn_layout)
        
        return group

    def _refresh_patient_list(self):
        """Refresh patient dropdown list."""
        current_id = None
        if self.current_patient:
            current_id = self.current_patient.id
        
        # Clear except first item
        while self.patient_combo.count() > 1:
            self.patient_combo.removeItem(1)
        
        # Add patients
        for patient in self.patient_manager.list_all():
            self.patient_combo.addItem(patient.display_name(), patient.id)
        
        # Restore selection
        if current_id:
            for i in range(self.patient_combo.count()):
                if self.patient_combo.itemData(i) == current_id:
                    self.patient_combo.setCurrentIndex(i)
                    break

    def _on_patient_changed(self, index: int):
        """Handle patient selection change."""
        patient_id = self.patient_combo.itemData(index)
        if patient_id:
            self.current_patient = self.patient_manager.get(patient_id)
        else:
            self.current_patient = None

    def _create_new_patient(self):
        """Show dialog to create new patient."""
        dialog = QDialog(self)
        dialog.setWindowTitle("New Patient")
        dialog.setMinimumWidth(300)
        layout = QFormLayout(dialog)
        
        name_edit = QLineEdit()
        pd_edit = QLineEdit()
        pd_edit.setPlaceholderText("cm (e.g. 6.3)")
        
        layout.addRow("Name:", name_edit)
        layout.addRow("Pupil Distance (cm):", pd_edit)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            pd_text = pd_edit.text().strip()
            pd_value = float(pd_text) if pd_text else 6.3
            patient = self.patient_manager.create(
                name=name_edit.text(),
                pupil_distance_mm=pd_value * 10
            )
            self._refresh_patient_list()
            # Select new patient
            for i in range(self.patient_combo.count()):
                if self.patient_combo.itemData(i) == patient.id:
                    self.patient_combo.setCurrentIndex(i)
                    break

    def _edit_patient(self):
        """Edit current patient."""
        if not self.current_patient:
            QMessageBox.warning(self, "No Patient", "Please select a patient first.")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Patient")
        dialog.setMinimumWidth(300)
        layout = QFormLayout(dialog)
        
        name_edit = QLineEdit(self.current_patient.name)
        dob_edit = QLineEdit(self.current_patient.date_of_birth)
        gender_edit = QLineEdit(self.current_patient.gender)
        glasses_check = QCheckBox()
        glasses_check.setChecked(self.current_patient.wears_glasses)
        notes_edit = QLineEdit(self.current_patient.notes)
        
        layout.addRow("Name:", name_edit)
        layout.addRow("Date of Birth:", dob_edit)
        layout.addRow("Gender:", gender_edit)
        layout.addRow("Wears Glasses:", glasses_check)
        layout.addRow("Notes:", notes_edit)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.patient_manager.update(
                self.current_patient.id,
                name=name_edit.text(),
                date_of_birth=dob_edit.text(),
                gender=gender_edit.text(),
                wears_glasses=glasses_check.isChecked(),
                notes=notes_edit.text()
            )
            self._refresh_patient_list()

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

        # Validation button
        self.validate_btn = QPushButton("🎯 Validate Accuracy")
        self.validate_btn.setStyleSheet("""
            QPushButton {
                background-color: #00b894;
                color: white;
                padding: 8px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #00a884; }
        """)
        self.validate_btn.setToolTip("Test gaze accuracy against known positions (requires calibration)")
        self.validate_btn.clicked.connect(self._start_validation)
        layout.addWidget(self.validate_btn)

        return group

    def _create_test_config_group(self) -> QGroupBox:
        """Create test configuration group."""
        group = QGroupBox("Test Configuration")
        layout = QVBoxLayout(group)

        layout.addWidget(QLabel("Pattern:"))
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems([
            "Horizontal", "Vertical", "Circular", "Figure-8", "Random Points", "Fixation",
            "Pro-Saccade", "Anti-Saccade"
        ])
        self.pattern_combo.setToolTip(
            "Horizontal/Vertical: Smooth pursuit\n"
            "Circular/Figure-8: Complex pursuit\n"
            "Random Points: Saccade testing\n"
            "Fixation: Stability assessment\n"
            "Pro-Saccade: Look toward target\n"
            "Anti-Saccade: Look away from target"
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
        # Capped at 0.7. At 1.0 the horizontal sweep peaks near 50 deg/s, above the ~30-40 deg/s
        # smooth-pursuit ceiling, so the subject physically cannot follow it and every score
        # reads as failure regardless of how well they track.
        self.speed_slider.setRange(1, 7)
        self.speed_slider.setValue(5)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        self.speed_slider.setToolTip(
            "Target movement speed. Higher is harder: smooth pursuit tops out near 30-40 deg/s."
        )
        layout.addWidget(self.speed_slider)

        self.start_test_btn = QPushButton("Start Test")
        self.start_test_btn.setToolTip(
            "Start the eye movement test. Calibrate first for a valid score."
        )
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
        self.back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(self.HOME_VIEW))
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

        self.trajectory_btn = QPushButton("📈 View Trajectory")
        self.trajectory_btn.setToolTip("View gaze trajectory plots")
        self.trajectory_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #8e44ad; }
        """)
        self.trajectory_btn.clicked.connect(self._show_trajectory)
        btn_layout.addWidget(self.trajectory_btn)

        self.pdf_btn = QPushButton("📄 Export PDF")
        self.pdf_btn.setToolTip("Generate professional PDF clinical report")
        self.pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        self.pdf_btn.clicked.connect(self._export_pdf)
        btn_layout.addWidget(self.pdf_btn)

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
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(self.HOME_VIEW))
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
        # Deleting a score destroys clinical data, so the control is only offered to an admin
        # who is actually signed in. _delete_history_session re-checks this.
        self.history_delete_btn = delete_btn
        delete_btn.hide()
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)
        return widget

    def _show_history(self):
        """Show the history view."""
        self._refresh_history()
        self.stack.setCurrentIndex(self.HISTORY_VIEW)

    def _show_admin(self):
        """Show the admin panel."""
        if not self.current_user or self.current_user.role != USER_ROLE_ADMIN:
            QMessageBox.warning(self, "Access Denied", "Admin access required.")
            return
        self._refresh_admin_users()
        self.stack.setCurrentIndex(self.ADMIN_VIEW)

    def _show_login(self):
        """Show the login/signup dialog."""
        try:
            from auth_dialog import LoginDialog
            login = LoginDialog(self.user_manager, self)
            if login.exec() == QDialog.DialogCode.Accepted and login.authenticated_user:
                self.current_user = login.authenticated_user
                is_admin = self.current_user.role == USER_ROLE_ADMIN
                self.admin_btn.setVisible(is_admin)
                # Deleting a stored score stays an admin-only action.
                self.history_delete_btn.setVisible(is_admin)
                QMessageBox.information(
                    self, "Welcome",
                    f"Logged in as {self.current_user.username} ({self.current_user.role})"
                )
        except Exception as e:
            QMessageBox.warning(self, "Login Error", f"Failed to show login: {e}")

    def _history_item_text(self, data: dict, session) -> str:
        """One line describing a stored run."""
        metrics = data.get('metrics', {})
        accuracy = metrics.get('accuracy_score', 0)
        tracking = metrics.get('tracking_ratio', 0)
        smooth = metrics.get('smooth_score', 0)
        # Absent in results saved before the head score existed; show "n/a" rather
        # than a misleading 0% for those runs.
        head = metrics.get('head_stillness_score')
        head_text = f"{head:.0f}%" if head is not None else "n/a"
        timestamp = data.get('timestamp', session.timestamp.strftime('%Y-%m-%d %H:%M'))
        pattern = data.get('pattern', session.pattern)
        # "Match" is the direction match; "Track" is the share of frames that produced a usable
        # gaze estimate. The clinical error in degrees is shown when the run has it, because
        # that is the number a clinician reads.
        clinical = data.get('clinical_metrics') or {}
        error_text = f" | Err: {clinical['accuracy_degrees']:.1f}°" if clinical.get('accuracy_degrees') else ""
        if "speed_match_score" in metrics:
            track_text = f"Track: {tracking:.0f}% | Speed: {metrics['speed_match_score']:.0f}%"
        else:
            # Saved before the tracking rate was split from the speed match: the stored value
            # is the speed match, and the share of valid frames was never recorded.
            track_text = f"Speed: {tracking:.0f}%"
        item_text = (
            f"{timestamp} | {pattern} | {track_text} | Match: {accuracy:.0f}% | "
            f"Smooth: {smooth:.0f}% | Head: {head_text}{error_text}"
        )
        # Carry validity through to the list so a bad run is obvious without
        # opening it: uncalibrated data, or a target faster than pursuit can follow.
        if data.get('uncalibrated'):
            item_text += "  ⚠ UNCALIBRATED"
        peak = data.get('target_angular_speed_deg_s')
        if peak and peak > 40:
            item_text += f"  ⚠ TARGET {peak:.0f} deg/s"
        return item_text

    def _refresh_history(self):
        """Refresh the history list."""
        self.history_list.clear()

        # Test sessions with scores
        sessions = self.session_history.list_sessions()
        for session in sessions:
            # Load full data to get scores
            data = self.session_history.load_session(session.filename)
            if data:
                item_text = self._history_item_text(data, session)
            else:
                item_text = session.to_display_string()
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, session.filename)
            self.history_list.addItem(item)

        # Calibration history
        cal_dir = Path("data/calibrations")
        if cal_dir.exists():
            for cal_file in sorted(cal_dir.glob("*.json"), reverse=True):
                try:
                    import json
                    data = json.loads(cal_file.read_text(encoding="utf-8"))
                    name = data.get("name", cal_file.stem)
                    created = data.get("created_at", "unknown")
                    points = len(data.get("points", []))
                    item_text = f"[CAL] {name} — {created} — {points} points"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.ItemDataRole.UserRole, str(cal_file))
                    self.history_list.addItem(item)
                except Exception:
                    pass

        if not sessions and not cal_dir.exists():
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
            self.stack.setCurrentIndex(self.RESULTS_VIEW)

    def _delete_history_session(self):
        """Delete the selected history session.

        Only a signed-in admin may remove a stored score. Hiding the button is not enough --
        the check is repeated here so the action cannot be reached another way.
        """
        if not self.current_user:
            QMessageBox.warning(
                self, "Access Denied",
                "Sign in as an administrator to delete a session."
            )
            return
        if self.current_user.role != USER_ROLE_ADMIN:
            QMessageBox.warning(
                self, "Access Denied",
                "Only an administrator can delete a session. Your account is signed in as a "
                "regular user."
            )
            return

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

    def _create_admin_view(self) -> QWidget:
        """Create the admin panel view."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        title = QLabel("⚙️ Admin Panel")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #e17055;")
        layout.addWidget(title)

        # User list
        self.admin_user_list = QListWidget()
        self.admin_user_list.setStyleSheet("""
            QListWidget {
                background-color: #2d2d44;
                color: #dfe6e9;
                font-size: 13px;
                border-radius: 5px;
                padding: 10px;
            }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #4a4a6a; }
            QListWidget::item:selected { background-color: #4a4a6a; }
        """)
        self.admin_user_list.itemClicked.connect(self._on_admin_user_selected)
        layout.addWidget(self.admin_user_list)

        # User details
        self.admin_user_details = QLabel("Select a user to view details")
        self.admin_user_details.setStyleSheet("color: #b2bec3; padding: 10px;")
        layout.addWidget(self.admin_user_details)

        # Action buttons
        btn_layout = QHBoxLayout()

        self.admin_refresh_btn = QPushButton("🔄 Refresh")
        self.admin_refresh_btn.clicked.connect(self._refresh_admin_users)
        btn_layout.addWidget(self.admin_refresh_btn)

        self.admin_delete_btn = QPushButton("🗑️ Delete User")
        self.admin_delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #d63031; color: white;
                padding: 8px 16px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #c02020; }
        """)
        self.admin_delete_btn.clicked.connect(self._admin_delete_user)
        btn_layout.addWidget(self.admin_delete_btn)

        self.admin_promote_btn = QPushButton("⬆️ Make Admin")
        self.admin_promote_btn.setStyleSheet("""
            QPushButton {
                background-color: #00b894; color: white;
                padding: 8px 16px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #00a381; }
        """)
        self.admin_promote_btn.clicked.connect(self._admin_promote_user)
        btn_layout.addWidget(self.admin_promote_btn)

        layout.addLayout(btn_layout)

        # Back button
        back_btn = QPushButton("Back to Home")
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(self.HOME_VIEW))
        layout.addWidget(back_btn)

        return widget

    def _refresh_admin_users(self):
        """Refresh the admin user list."""
        self.admin_user_list.clear()
        users = self.user_manager.list_users()
        for user in users:
            role_label = " [ADMIN]" if user.role == USER_ROLE_ADMIN else ""
            item_text = f"{user.username}{role_label} — {user.email}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, user.username)
            self.admin_user_list.addItem(item)

    def _on_admin_user_selected(self, item):
        """Handle admin user selection."""
        username = item.data(Qt.ItemDataRole.UserRole)
        user = self.user_manager.get_user(username)
        if user:
            self.admin_user_details.setText(
                f"Username: {user.username}\n"
                f"Email: {user.email}\n"
                f"Role: {user.role}\n"
                f"Created: {user.created_at}\n"
                f"Last Login: {user.last_login or 'Never'}"
            )

    def _admin_delete_user(self):
        """Delete a user from the admin panel."""
        current = self.admin_user_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a user to delete.")
            return
        username = current.data(Qt.ItemDataRole.UserRole)
        if username == self.current_user.username:
            QMessageBox.warning(self, "Error", "You cannot delete your own account.")
            return
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete user '{username}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.user_manager.delete_user(username):
                self._refresh_admin_users()
                QMessageBox.information(self, "Deleted", f"User '{username}' deleted.")

    def _admin_promote_user(self):
        """Promote a user to admin."""
        current = self.admin_user_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a user to promote.")
            return
        username = current.data(Qt.ItemDataRole.UserRole)
        user = self.user_manager.get_user(username)
        if user.role == USER_ROLE_ADMIN:
            QMessageBox.information(self, "Info", "User is already an admin.")
            return
        if self.user_manager.update_role(username, USER_ROLE_ADMIN):
            self._refresh_admin_users()
            QMessageBox.information(self, "Promoted", f"User '{username}' is now an admin.")

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
            QMessageBox { background-color: #2d2d44; }
            QMessageBox QLabel {
                color: #b2bec3;
                font-size: 14px;
            }
        """)

    def _connect_signals(self):
        """Connect UI signals."""
        self.calibrate_btn.clicked.connect(self._start_calibration)
        self.save_profile_btn.clicked.connect(self._save_profile)
        self.load_profile_btn.clicked.connect(self._load_profile)
        self.start_test_btn.clicked.connect(self._start_test)
        self.calibration_widget.calibration_complete.connect(self._on_calibration_complete)
        self.calibration_widget.calibration_stopped.connect(self._on_calibration_stopped)
        self.test_widget.test_complete.connect(self._on_test_complete)

    def _on_speed_changed(self, value: int):
        """Update speed label when slider changes."""
        speed = value / 10.0
        self.speed_label.setText(f"{speed:.1f}")

    def _on_camera_failed(self, message: str):
        """The camera stopped delivering frames: say so instead of showing a dead preview."""
        self.camera_label.setText(f"📷 {message}")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setToolTip(message)
        self.face_status.setText("👤 Face: — camera unavailable")
        self.face_status.setStyleSheet("color: #ff6b6b;")
        self.tracking_status.setText("👁️ Tracking: No camera")
        self.tracking_status.setStyleSheet("color: #ff6b6b;")

    def _on_camera_recovered(self):
        """The camera came back: the next frame repaints the preview."""
        self.camera_label.setToolTip("")
        self.face_status.setText("👤 Face: waiting…")
        self.face_status.setStyleSheet("color: #ffd93d;")

    def _on_frame_ready(self, frame: np.ndarray, eye_data: EyeData, capture_time: float):
        """Handle new camera frame.

        Args:
            frame: Camera frame
            eye_data: Eye tracking data
            capture_time: Timestamp when frame was captured
        """
        self.current_eye_data = eye_data

        # Mark camera as initialized on first frame
        if not self._camera_initialized:
            self._camera_initialized = True

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
            self.face_status.setText(f"👤 Face: ✓ Detected ({actual_fps:.1f} FPS)")
            self.face_status.setStyleSheet("color: #00b894;")
            self.tracking_status.setText("👁️ Tracking: Active")
            self.tracking_status.setStyleSheet("color: #00b894;")
        else:
            self.face_status.setText(f"👤 Face: ✗ Not Detected ({actual_fps:.1f} FPS)")
            self.face_status.setStyleSheet("color: #ff6b6b;")
            self.tracking_status.setText("👁️ Tracking: No Face")
            self.tracking_status.setStyleSheet("color: #ff6b6b;")

        self.head_pose_label.setText(
            f"📐 Head: P={eye_data.head_pitch:.1f}° Y={eye_data.head_yaw:.1f}° R={eye_data.head_roll:.1f}°"
        )

        # Forward to active widget with capture timestamp
        if self.stack.currentWidget() == self.calibration_widget:
            self.calibration_widget.process_eye_data(eye_data)
        elif self.stack.currentWidget() == self.test_widget:
            self.test_widget.process_eye_data(eye_data, capture_time)
        elif self.stack.currentWidget() == self.saccade_widget:
            self.saccade_widget.process_eye_data(eye_data)
        elif self.stack.currentWidget() == self.validation_widget:
            self.validation_widget.process_eye_data(eye_data)

    def _start_calibration(self):
        """Start calibration process."""
        # Toggle button to Stop
        self.calibrate_btn.setText("Stop Calibration")
        self.calibrate_btn.setStyleSheet("""
            QPushButton {
                background-color: #d63031;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #c02020; }
        """)
        self.calibrate_btn.clicked.disconnect()
        self.calibrate_btn.clicked.connect(self._stop_calibration)

        # Get pupil distance: use patient's if selected, otherwise ask
        pd_mm = self._resolve_pupil_distance_mm()
        if pd_mm <= 0:
            self._reset_calibrate_button()
            return
        self._pupil_distance_mm = pd_mm
        self.stack.setCurrentWidget(self.calibration_widget)
        self.calibration_widget.showFullScreen()
        self.calibration_widget.start_calibration()

    def _resolve_pupil_distance_mm(self) -> float:
        """Use the selected patient's IPD, otherwise prompt. Returns 0.0 if cancelled."""
        if self.current_patient and self.current_patient.pupil_distance_mm > 0:
            return self.current_patient.pupil_distance_mm

        from PyQt6.QtWidgets import QInputDialog
        pd, ok = QInputDialog.getDouble(
            self, "Pupil Distance",
            "Enter pupil distance (cm):",
            value=6.3, min=4.0, max=8.0, decimals=2
        )
        return pd * 10 if ok else 0.0  # Convert cm to mm

    def _stop_calibration(self):
        """Stop calibration early."""
        self.calibration_widget.stop_calibration()

    def _on_calibration_stopped(self):
        """Handle early calibration stop."""
        self._reset_calibrate_button()
        self.calibration_widget.showNormal()
        self.stack.setCurrentIndex(self.HOME_VIEW)
        # Measured error, not a score. A percentage here reads as a validated grade, and nothing
        # in this software is clinically validated yet (see docs/BACKLOG.md A-6).
        held_out = None
        if self.gaze_estimator.is_calibrated:
            held_out = self.gaze_estimator.get_calibration_quality().get('cv_error_px')
        status = "🎯 Calibration: Partial"
        if held_out is not None:
            status = f"{status} ({held_out:.1f} px held-out)"
        self.calibration_status.setText(status)
        self.calibration_status.setStyleSheet("color: #ffd93d;")

    def _reset_calibrate_button(self):
        """Reset button to Start state."""
        self.calibrate_btn.setText("Start Calibration")
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
        self.calibrate_btn.clicked.disconnect()
        self.calibrate_btn.clicked.connect(self._start_calibration)

    def _on_calibration_complete(self):
        """Handle calibration completion."""
        self._reset_calibrate_button()
        self.calibration_widget.showNormal()
        self.stack.setCurrentIndex(self.HOME_VIEW)
        self.calibration_status.setText("🎯 Calibration: ✓ Done")
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
                self.calibration_status.setText("🎯 Calibration: ✓ Loaded")
                self.calibration_status.setStyleSheet("color: #00b894;")
                QMessageBox.information(self, "Loaded", "Profile loaded successfully.")
            else:
                QMessageBox.warning(self, "Error", "Failed to load profile.")

    def _start_test(self):
        """Start the eye movement test."""
        # Uncalibrated gaze is not accurate enough to score: the fallback mapping treats the
        # full camera width as the full gaze range, so the estimate lands hundreds of pixels
        # from the target. That is worth saying -- but it is the operator's call whether to
        # proceed, so this warns and records the run as uncalibrated rather than blocking it.
        if not self.gaze_estimator.is_calibrated:
            reply = QMessageBox.question(
                self, "Not Calibrated",
                "Calibration has not been completed.\n\n"
                "Uncalibrated gaze estimates are not accurate enough to score and will "
                "land far from the target. You can run the test anyway, but the result "
                "will be recorded as uncalibrated and is not a valid measurement.\n\n"
                "Run the test anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        pattern_index = self.pattern_combo.currentIndex()
        
        # Check if it's a saccade test (indices 6 and 7)
        if pattern_index == 6:  # Pro-Saccade
            self._start_saccade_test(SaccadeTestType.PRO_SACCADE)
            return
        elif pattern_index == 7:  # Anti-Saccade
            self._start_saccade_test(SaccadeTestType.ANTI_SACCADE)
            return
        
        # Get test configuration for standard patterns
        patterns = [
            TargetPattern.HORIZONTAL,
            TargetPattern.VERTICAL,
            TargetPattern.CIRCULAR,
            TargetPattern.FIGURE_EIGHT,
            TargetPattern.RANDOM_POINTS,
            TargetPattern.FIXATION
        ]
        pattern = patterns[pattern_index]

        config = TestConfig(
            pattern=pattern,
            duration_seconds=self.duration_spin.value(),
            speed=self.speed_slider.value() / 10.0
        )

        self.stack.setCurrentWidget(self.test_widget)
        self.test_widget.showFullScreen()
        self.test_widget.start_test(config, pupil_distance_mm=self._resolve_pupil_distance_mm())
    
    def _start_saccade_test(self, test_type: SaccadeTestType):
        """Start a saccade test."""
        if not self.gaze_estimator.is_calibrated:
            reply = QMessageBox.question(
                self, "Not Calibrated",
                "Calibration has not been completed.\n\n"
                "Uncalibrated gaze estimates are not accurate enough to score. "
                "You can run the test anyway, but the result will be recorded as "
                "uncalibrated and is not a valid measurement.\n\n"
                "Run the test anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        config = SaccadeTestConfig(
            test_type=test_type,
            num_trials=20,
            eccentricities_deg=[10.0],  # 10 degrees eccentricity
            fixation_duration_ms=1000.0,
            gap_duration_ms=200.0,
            randomize_direction=True,
            randomize_timing=True
        )
        
        self.stack.setCurrentWidget(self.saccade_widget)
        self.saccade_widget.showFullScreen()
        self.saccade_widget.start_test(config)

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

        self.stack.setCurrentIndex(self.RESULTS_VIEW)


    def _on_saccade_complete(self, result: SaccadeTestResult):
        """Handle saccade test completion."""
        if result is None:
            return
        self.saccade_widget.showNormal()
        
        # Store result (note: different type than smooth pursuit result)
        self._last_saccade_result = result
        
        # Generate and display report
        report = generate_saccade_report(result)
        self.results_text.setText(report)

        self.stack.setCurrentIndex(self.RESULTS_VIEW)

    def _start_validation(self):
        """Start gaze accuracy validation."""
        if not self.gaze_estimator.is_calibrated:
            QMessageBox.warning(
                self, "Calibration Required",
                "Please complete calibration before running validation."
            )
            return
        
        config = ValidationConfig(
            pattern=ValidationPattern.GRID_9,
            samples_per_point=30,
            point_duration_ms=2000.0
        )
        
        self.stack.setCurrentWidget(self.validation_widget)
        self.validation_widget.showFullScreen()
        self.validation_widget.start_validation(config)

    def _on_validation_complete(self, result: ValidationResult):
        """Handle validation completion."""
        self.validation_widget.showNormal()
        
        # Store result
        self._last_validation_result = result
        
        # Generate and display report
        report = generate_validation_report(result)
        self.results_text.setText(report)
        
        # Update calibration status with accuracy info
        if result.accuracy_degrees is not None:
            acc = result.accuracy_degrees
            if acc < 2.0:
                self.calibration_status.setText(f"🎯 Calibration: ✓ Validated ({acc:.2f}°)")
                self.calibration_status.setStyleSheet("color: #00b894;")
            else:
                self.calibration_status.setText(f"🎯 Calibration: ⚠️ {acc:.2f}° (>2°)")
                self.calibration_status.setStyleSheet("color: #fdcb6e;")

        self.stack.setCurrentIndex(self.RESULTS_VIEW)

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

    def _show_trajectory(self):
        """Show trajectory visualization dialog."""
        if self._last_result is None:
            QMessageBox.warning(self, "No Data", "No test results to visualize.")
            return

        try:
            # Generate trajectory plots
            visualizer = TrajectoryVisualizer()
            xy_fig, time_fig = generate_trajectory_from_result(self._last_result, visualizer)
            
            # Create dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Trajectory Visualization")
            dialog.setMinimumSize(800, 600)
            layout = QVBoxLayout(dialog)
            
            # Tab widget for different views
            tabs = QTabWidget()
            
            # XY Trajectory tab
            xy_widget = QWidget()
            xy_layout = QVBoxLayout(xy_widget)
            xy_label = QLabel()
            xy_img = visualizer.figure_to_image(xy_fig)
            xy_pixmap = QPixmap()
            xy_pixmap.loadFromData(xy_img)
            xy_label.setPixmap(xy_pixmap.scaled(750, 500, Qt.AspectRatioMode.KeepAspectRatio))
            xy_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            xy_layout.addWidget(xy_label)
            tabs.addTab(xy_widget, "XY Trajectory")
            
            # Time Series tab
            time_widget = QWidget()
            time_layout = QVBoxLayout(time_widget)
            time_label = QLabel()
            time_img = visualizer.figure_to_image(time_fig)
            time_pixmap = QPixmap()
            time_pixmap.loadFromData(time_img)
            time_label.setPixmap(time_pixmap.scaled(750, 500, Qt.AspectRatioMode.KeepAspectRatio))
            time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            time_layout.addWidget(time_label)
            tabs.addTab(time_widget, "Position vs Time")
            
            # Heatmap tab
            gaze_x = [f.gaze_x for f in self._last_result.frames if f.gaze_x is not None]
            gaze_y = [f.gaze_y for f in self._last_result.frames if f.gaze_y is not None]
            if gaze_x:
                heat_fig = visualizer.plot_heatmap(gaze_x, gaze_y, 
                    title=f"Gaze Heatmap - {self._last_result.pattern.value}")
                heat_widget = QWidget()
                heat_layout = QVBoxLayout(heat_widget)
                heat_label = QLabel()
                heat_img = visualizer.figure_to_image(heat_fig)
                heat_pixmap = QPixmap()
                heat_pixmap.loadFromData(heat_img)
                heat_label.setPixmap(heat_pixmap.scaled(750, 500, Qt.AspectRatioMode.KeepAspectRatio))
                heat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                heat_layout.addWidget(heat_label)
                tabs.addTab(heat_widget, "Heatmap")
            
            layout.addWidget(tabs)
            
            # Export button
            btn_layout = QHBoxLayout()
            export_btn = QPushButton("💾 Save Images")
            export_btn.clicked.connect(lambda: self._export_trajectory_images())
            btn_layout.addWidget(export_btn)
            
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.close)
            btn_layout.addWidget(close_btn)
            layout.addLayout(btn_layout)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.warning(self, "Visualization Error", f"Failed to generate trajectory: {e}")

    def _export_pdf(self):
        """Export results to PDF clinical report."""
        pdf_gen = PDFReportGenerator()
        
        try:
            # Determine which result to export
            if hasattr(self, '_last_result') and self._last_result is not None:
                pdf_path = pdf_gen.generate_pursuit_report(self._last_result)
                report_type = "Smooth Pursuit"
            elif hasattr(self, '_last_saccade_result') and self._last_saccade_result is not None:
                pdf_path = pdf_gen.generate_saccade_report(self._last_saccade_result)
                report_type = "Saccade"
            elif hasattr(self, '_last_validation_result') and self._last_validation_result is not None:
                pdf_path = pdf_gen.generate_validation_report(self._last_validation_result)
                report_type = "Validation"
            else:
                QMessageBox.warning(self, "No Data", "No test results to export.")
                return
            
            QMessageBox.information(
                self, "PDF Export Successful",
                f"{report_type} report saved to:\n{pdf_path}"
            )
        except Exception as e:
            QMessageBox.warning(self, "PDF Export Failed", f"Failed to generate PDF: {e}")

    def _export_trajectory_images(self):
        """Export trajectory plots to image files."""
        if self._last_result is None:
            return
        
        try:
            visualizer = TrajectoryVisualizer()
            xy_fig, time_fig = generate_trajectory_from_result(self._last_result, visualizer)
            
            # Save to results directory
            results_dir = Path("results")
            results_dir.mkdir(exist_ok=True)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            pattern = self._last_result.pattern.value
            
            xy_path = results_dir / f"trajectory_xy_{pattern}_{timestamp}.png"
            time_path = results_dir / f"trajectory_time_{pattern}_{timestamp}.png"
            
            visualizer.save_figure(xy_fig, str(xy_path))
            visualizer.save_figure(time_fig, str(time_path))
            
            QMessageBox.information(
                self, "Export Successful",
                f"Trajectory images saved:\n{xy_path}\n{time_path}"
            )
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", f"Failed to save images: {e}")

    def closeEvent(self, event):
        """Clean up on close."""
        self.camera_thread.stop()
        self.eye_tracker.release()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Initialize PHI encryption key for patient data storage
    try:
        from crypto import init_key, get_fernet, MissingEncryptionKey
        try:
            get_fernet()
        except MissingEncryptionKey:
            init_key()
    except Exception as e:
        print(f"Warning: Could not initialize encryption key: {e}")

    window = MainWindow()
    window.showMaximized()

    # Ensure window comes to front on macOS
    window.raise_()
    window.activateWindow()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
