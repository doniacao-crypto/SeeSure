"""
Authentication Dialogs for Eye Tracking Assessment.
Login, signup, and forgot password dialogs.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QMessageBox,
    QStackedWidget, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from user_manager import UserManager, User, USER_ROLE_ADMIN


class LoginDialog(QDialog):
    """Login dialog for existing users."""

    def __init__(self, user_manager: UserManager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.authenticated_user: User = None
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("EyeExam - Login")
        self.setFixedSize(400, 250)

        layout = QVBoxLayout(self)

        title = QLabel("EyeExam Login")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        form = QFormLayout()
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Username:", self.username_input)
        form.addRow("Password:", self.password_input)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.login_btn = QPushButton("Login")
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c5ce7; color: white;
                padding: 10px; border-radius: 5px; font-weight: bold;
            }
            QPushButton:hover { background-color: #5f4dd0; }
        """)
        self.login_btn.clicked.connect(self._on_login)

        self.forgot_btn = QPushButton("Forgot Password?")
        self.forgot_btn.setStyleSheet("color: #6c5ce7; border: none;")
        self.forgot_btn.clicked.connect(self._on_forgot_password)

        self.signup_btn = QPushButton("Create Account")
        self.signup_btn.setStyleSheet("color: #00b894; border: none;")
        self.signup_btn.clicked.connect(self._on_signup)

        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(self.forgot_btn)
        layout.addLayout(btn_layout)

        signup_layout = QHBoxLayout()
        signup_layout.addStretch()
        signup_layout.addWidget(self.signup_btn)
        layout.addLayout(signup_layout)

    def _on_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password")
            return
        user = self.user_manager.authenticate(username, password)
        if user:
            self.authenticated_user = user
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Invalid username or password")

    def _on_forgot_password(self):
        dialog = ForgotPasswordDialog(self.user_manager, self)
        dialog.exec()

    def _on_signup(self):
        dialog = SignupDialog(self.user_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.authenticated_user = dialog.created_user
            self.accept()


class SignupDialog(QDialog):
    """Signup dialog for creating new accounts."""

    def __init__(self, user_manager: UserManager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.created_user: User = None
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("EyeExam - Create Account")
        self.setFixedSize(450, 350)

        layout = QVBoxLayout(self)

        title = QLabel("Create Account")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        form = QFormLayout()
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Choose a username")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email address")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Confirm password")
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Username:", self.username_input)
        form.addRow("Email:", self.email_input)
        form.addRow("Password:", self.password_input)
        form.addRow("Confirm:", self.confirm_input)
        layout.addLayout(form)

        self.create_btn = QPushButton("Create Account")
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #00b894; color: white;
                padding: 10px; border-radius: 5px; font-weight: bold;
            }
            QPushButton:hover { background-color: #00a381; }
        """)
        self.create_btn.clicked.connect(self._on_create)
        layout.addWidget(self.create_btn)

    def _on_create(self):
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_input.text()

        if not all([username, email, password, confirm]):
            QMessageBox.warning(self, "Error", "All fields are required")
            return
        if password != confirm:
            QMessageBox.warning(self, "Error", "Passwords do not match")
            return
        if len(password) < 6:
            QMessageBox.warning(self, "Error", "Password must be at least 6 characters")
            return

        try:
            user = self.user_manager.create_user(username, email, password)
            self.created_user = user
            QMessageBox.information(self, "Success", f"Account created for {username}!")
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))


class ForgotPasswordDialog(QDialog):
    """Forgot password dialog - sends password to email."""

    def __init__(self, user_manager: UserManager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("EyeExam - Forgot Password")
        self.setFixedSize(400, 200)

        layout = QVBoxLayout(self)

        title = QLabel("Forgot Password")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        info = QLabel("Enter your email address.\nYour password will be sent to your email.")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email address")
        layout.addWidget(self.email_input)

        self.send_btn = QPushButton("Send Password")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c5ce7; color: white;
                padding: 10px; border-radius: 5px; font-weight: bold;
            }
            QPushButton:hover { background-color: #5f4dd0; }
        """)
        self.send_btn.clicked.connect(self._on_send)
        layout.addWidget(self.send_btn)

    def _on_send(self):
        email = self.email_input.text().strip()
        if not email:
            QMessageBox.warning(self, "Error", "Please enter your email address")
            return

        # Find user by email
        user = None
        for u in self.user_manager.list_users():
            if u.email == email:
                user = u
                break

        if user is None:
            QMessageBox.warning(self, "Error", "No account found with that email address")
            return

        # In a real app, this would send an email. For now, show the password.
        # TODO: Implement actual email sending
        QMessageBox.information(
            self, "Password Sent",
            f"Password recovery email sent to {email}.\n\n"
            f"(Demo: your password is '{user.password_hash[:8]}...' — "
            f"in production this would be emailed securely)"
        )
        self.accept()
