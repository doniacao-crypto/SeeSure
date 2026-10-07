"""
Saccade Test Widget for Eye Movement Assessment.
Provides full-screen display for saccade testing protocol.
"""

from typing import Optional

from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont

from saccade_test import SaccadeTest, SaccadeTestConfig, SaccadeTestType, SaccadeTestResult


class SaccadeWidget(QWidget):
    """
    Full-screen widget for saccade testing.
    Displays fixation cross and targets according to protocol.
    """
    
    test_complete = pyqtSignal(SaccadeTestResult)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #1a1a1a;")
        
        self._test: Optional[SaccadeTest] = None
        self._gaze_estimator = None
        
        # Colors
        self.fixation_color = QColor(255, 255, 255)  # White
        self.target_color = QColor(255, 255, 0)       # Yellow
        self.bg_color = QColor(26, 26, 26)            # Dark gray
        
        # Sizes
        self.fixation_size = 20
        self.target_size = 25
        
        # Status label
        self.status_label = QLabel("", self)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #74b9ff;
                font-size: 16px;
                padding: 10px;
            }
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    def set_gaze_estimator(self, estimator):
        """Set the gaze estimator for obtaining gaze data."""
        self._gaze_estimator = estimator
    
    def start_test(self, config: SaccadeTestConfig):
        """
        Start a saccade test.
        
        Args:
            config: Test configuration
        """
        # Update config with current screen size
        config.screen_width_px = self.width()
        config.screen_height_px = self.height()
        
        self._test = SaccadeTest(config)
        if self._gaze_estimator:
            self._test.on_trial_start = self._gaze_estimator.reset_filters
        self._test.start()
        self.update()
    
    def stop_test(self):
        """Stop the current test."""
        if self._test:
            self._test.stop()
            result = self._test.result
            self._test = None
            if result is not None:
                self.test_complete.emit(result)
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
            result = self._gaze_estimator.estimate_gaze(
                eye_data,
                timestamp=time.time(),
                is_blink=eye_data.is_blinking,
            )
            if result is not None:
                gaze_x, gaze_y = result
        
        # Update test
        import time
        self._test.update(gaze_x, gaze_y, time.time())
        
        # Check if test is complete
        if not self._test.is_running:
            self.stop_test()
        
        self.update()
    
    def paintEvent(self, event):
        """Draw the test display."""
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
                           "Waiting to start saccade test...")
            return
        
        state = self._test.get_display_state()
        
        # Draw fixation cross
        if state["fixation_visible"]:
            self._draw_fixation(painter)
        
        # Draw target
        if state["target_visible"]:
            self._draw_target(painter, state["target_x"], state["target_y"])
        
        # Update status
        self.status_label.setText(
            f"Trial {state['trial_number']}/{state['total_trials']} - {state['phase']}"
        )
        self.status_label.adjustSize()
        self.status_label.move(10, 10)
    
    def _draw_fixation(self, painter: QPainter):
        """Draw central fixation cross."""
        center_x = self.width() // 2
        center_y = self.height() // 2
        size = self.fixation_size
        
        pen = QPen(self.fixation_color, 3)
        painter.setPen(pen)
        
        # Horizontal line
        painter.drawLine(center_x - size, center_y, center_x + size, center_y)
        # Vertical line
        painter.drawLine(center_x, center_y - size, center_x, center_y + size)
    
    def _draw_target(self, painter: QPainter, x: int, y: int):
        """Draw target dot."""
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.target_color))
        painter.drawEllipse(
            x - self.target_size // 2,
            y - self.target_size // 2,
            self.target_size,
            self.target_size
        )
    
    def resizeEvent(self, event):
        """Handle resize to reposition status label."""
        super().resizeEvent(event)
        if hasattr(self, 'status_label'):
            self.status_label.move(10, 10)
