"""
User Account Management for Eye Tracking Assessment.
Handles user accounts, authentication, roles, and admin operations.
"""

import json
import hashlib
import secrets
import uuid
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

USER_ROLE_ADMIN = "admin"
USER_ROLE_USER = "user"


@dataclass
class User:
    """User account data."""
    id: str = ""
    username: str = ""
    email: str = ""
    password_hash: str = ""
    role: str = USER_ROLE_USER
    created_at: str = ""
    last_login: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        return cls(**data)


class UserManager:
    """Manages user accounts with encrypted storage."""

    def __init__(self, data_dir: str = "data/users"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._users: Dict[str, User] = {}
        self._load_all()

    def _load_all(self):
        """Load all user files."""
        self._users = {}
        for filepath in self.data_dir.glob("*.json"):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                user = User.from_dict(data)
                self._users[user.username] = user
            except Exception as e:
                logger.warning(f"Failed to load user file {filepath}: {e}")

        # Create default admin account if it doesn't exist
        if not self.user_exists("onoadmin"):
            try:
                self.create_user("onoadmin", "onoadmin@example.com", "onogiri", USER_ROLE_ADMIN)
                logger.info("Default admin account 'onoadmin' created")
            except ValueError:
                pass  # Already exists or error

    def _save_user(self, user: User):
        """Save a user to disk."""
        filepath = self.data_dir / f"{user.username}.json"
        filepath.write_text(json.dumps(user.to_dict(), indent=2), encoding="utf-8")

    @staticmethod
    def _hash_password(password: str, salt: Optional[str] = None) -> str:
        """Hash password with PBKDF2."""
        if salt is None:
            salt = secrets.token_hex(16)
        hash_value = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
        ).hex()
        return f"{salt}${hash_value}"

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt, _ = password_hash.split("$", 1)
            return self._hash_password(password, salt) == password_hash
        except (ValueError, AttributeError):
            return False

    def create_user(
        self, username: str, email: str, password: str, role: str = USER_ROLE_USER
    ) -> User:
        """Create a new user account."""
        if not username or not email or not password:
            raise ValueError("Username, email, and password are required")
        if username in self._users:
            raise ValueError(f"Username '{username}' already exists")

        user = User(
            id=uuid.uuid4().hex[:8],
            username=username,
            email=email,
            password_hash=self._hash_password(password),
            role=role,
            created_at=datetime.now().isoformat(),
        )
        self._users[username] = user
        self._save_user(user)
        return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user and update last login."""
        user = self._users.get(username)
        if user is None:
            return None
        if not self._verify_password(password, user.password_hash):
            return None
        user.last_login = datetime.now().isoformat()
        self._save_user(user)
        return user

    def get_user(self, username: str) -> Optional[User]:
        """Get a user by username."""
        return self._users.get(username)

    def list_users(self) -> List[User]:
        """List all users."""
        return list(self._users.values())

    def delete_user(self, username: str) -> bool:
        """Delete a user account."""
        if username not in self._users:
            return False
        del self._users[username]
        filepath = self.data_dir / f"{username}.json"
        if filepath.exists():
            filepath.unlink()
        return True

    def update_role(self, username: str, new_role: str) -> bool:
        """Update a user's role."""
        user = self._users.get(username)
        if user is None:
            return False
        user.role = new_role
        self._save_user(user)
        return True

    def user_exists(self, username: str) -> bool:
        """Check if a username exists."""
        return username in self._users

    def get_user_patients_dir(self, username: str) -> Path:
        """Get the data directory for a specific user's patients."""
        user_dir = Path("data") / "users" / username / "patients"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def get_user_results_dir(self, username: str) -> Path:
        """Get the results directory for a specific user."""
        user_dir = Path("data") / "users" / username / "results"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
