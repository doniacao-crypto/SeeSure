"""
Validation Widget for Gaze Accuracy Testing.
Provides full-screen display for accuracy validation.
"""

from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont

from validation import ValidationTest, ValidationConfig, ValidationResult


class ValidationWidget(QWidget):
    """
    Full-screen widget for gaze accuracy validation.
    Displays target points and collects gaze data.
    """
    
    validation_complete = pyqtSignal(ValidationResult)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #1a1a1a;")
        
        self._test: ValidationTest = None
        self._gaze_estimator = None
        
        # Colors
        self.target_color = QColor(0, 255, 0)       # Green
        self.ring_color = QColor(100, 255, 100)     # Light green
        self.bg_color = QColor(26, 26, 26)          # Dark gray
        
        # Sizes
        self.target_size = 15
        self.ring_size = 40
        
        # Status label
        self.status_label = QLabel("", self)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #74b9ff;
                font-size: 18px;
                padding: 10px;
            }
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Instructions label
        self.instructions_label = QLabel("Look at the green dot", self)
        self.instructions_label.setStyleSheet("""
            QLabel {
                color: #dfe6e9;
                font-size: 24px;
                padding: 20px;
            }
        """)
        self.instructions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    def set_gaze_estimator(self, estimator):
        """Set the gaze estimator."""
        self._gaze_estimator = estimator
    
    def start_validation(self, config: ValidationConfig):
        """
        Start a validation test.
        
        Args:
            config: Validation configuration
        """
        # Update config with current screen size
        config.screen_width_px = self.width()
        config.screen_height_px = self.height()
        
        self._test = ValidationTest(config)
        self._test.start()
        self.update()
    
    def stop_validation(self):
        """Stop the validation test."""
        if self._test:
            self._test.stop()
            result = self._test.result
            self._test = None
            self.validation_complete.emit(result)
            self.update()
    
    def process_eye_data(self, eye_data):
        """
        Process incoming eye tracking data.
        
        Args:
            eye_data: EyeData from eye tracker
        """
        if not self._test or not self._test.is_running:
            return
        
        # Get gaze position from estimator
        gaze_x, gaze_y = None, None
        if self._gaze_estimator and self._gaze_estimator.is_calibrated:
            gaze_x, gaze_y = self._gaze_estimator.estimate(
                eye_data.left_pupil, eye_data.right_pupil,
                eye_data.head_pitch, eye_data.head_yaw,
                eye_data.capture_time
            )
        
        # Update test
        import time
        self._test.update(gaze_x, gaze_y, time.time())
        
        # Check if test is complete
        if not self._test.is_running:
            self.stop_validation()
        
        self.update()
    
    def paintEvent(self, event):
        """Draw the validation display."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), self.bg_color)
        
        if not self._test or not self._test.is_running:
            # Draw waiting message
            painter.setPen(QPen(QColor(100, 100, 100)))
            font = QFont("Arial", 18)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 
                           "Waiting to start validation...")
            return
        
        # Get current target
        target_x, target_y = self._test.get_current_target()
        current, total = self._test.get_progress()
        
        # Draw target ring (outer)
        painter.setPen(QPen(self.ring_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(
            target_x - self.ring_size // 2,
            target_y - self.ring_size // 2,
            self.ring_size,
            self.ring_size
        )
        
        # Draw target dot (inner)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.target_color))
        painter.drawEllipse(
            target_x - self.target_size // 2,
            target_y - self.target_size // 2,
            self.target_size,
            self.target_size
        )
        
        # Update status
        self.status_label.setText(f"Point {current}/{total}")
        self.status_label.adjustSize()
        self.status_label.move(10, 10)
        
        # Position instructions at bottom
        self.instructions_label.adjustSize()
        self.instructions_label.move(
            (self.width() - self.instructions_label.width()) // 2,
            self.height() - 80
        )
    
    def resizeEvent(self, event):
        """Handle resize."""
        super().resizeEvent(event)
