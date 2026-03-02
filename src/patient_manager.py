"""
Patient Profile Management for Eye Movement Assessment.
Manages patient records, demographics, and test history.
"""

import json
import logging
import re
import uuid
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from .crypto import encrypt_json, decrypt_json, init_key, MissingEncryptionKey
from typing import List, Optional, Dict, Any


@dataclass
class Patient:
    """Patient profile data."""
    id: str = ""
    name: str = ""
    date_of_birth: str = ""
    gender: str = ""
    dominant_eye: str = ""
    wears_glasses: bool = False
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""
    test_sessions: List[str] = field(default_factory=list)  # List of session IDs
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8].upper()
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Patient':
        return cls(**data)
    
    def add_session(self, session_id: str):
        """Add a test session to patient history."""
        if session_id not in self.test_sessions:
            self.test_sessions.append(session_id)
            self.updated_at = datetime.now().isoformat()
    
    @property
    def age(self) -> Optional[int]:
        """Calculate age from date of birth."""
        if not self.date_of_birth:
            return None
        try:
            dob = datetime.strptime(self.date_of_birth, "%Y-%m-%d")
            today = datetime.now()
            age = today.year - dob.year
            if (today.month, today.day) < (dob.month, dob.day):
                age -= 1
            return age
        except ValueError:
            return None
    
    def display_name(self) -> str:
        """Format name for display."""
        if self.date_of_birth:
            age = self.age
            if age is not None:
                return f"{self.name} ({age}y)"
        return self.name


_VALID_GENDERS = {"male", "female", "other", "prefer_not_to_say", ""}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PROTECTED_FIELDS = {"id", "created_at", "test_sessions"}


_logger = logging.getLogger(__name__)

class PatientManager:
    """Manages patient profiles."""

    @staticmethod
    def _validate_fields(kwargs: Dict[str, Any]) -> None:
        """
        Validate patient field values.

        Args:
            kwargs: Field name/value pairs to validate

        Raises:
            ValueError: If any field value is invalid
        """
        if "name" in kwargs:
            name = kwargs["name"]
            if not isinstance(name, str) or not name.strip():
                raise ValueError("name must be a non-empty string")

        if "date_of_birth" in kwargs:
            dob = kwargs["date_of_birth"]
            if dob:  # allow empty string to clear the field
                if not isinstance(dob, str) or not _DATE_RE.match(dob):
                    raise ValueError(
                        "date_of_birth must match YYYY-MM-DD format"
                    )
                # Verify it parses to a real date
                try:
                    datetime.strptime(dob, "%Y-%m-%d")
                except ValueError:
                    raise ValueError(
                        "date_of_birth is not a valid calendar date"
                    )

        if "gender" in kwargs:
            gender = kwargs["gender"]
            if not isinstance(gender, str) or gender.lower() not in _VALID_GENDERS:
                raise ValueError(
                    f"gender must be one of: {', '.join(sorted(_VALID_GENDERS - {''})) or 'empty string'}"
                )

    def __init__(self, data_dir: str = "data/patients"):
        """
        Initialize patient manager.
        
        Args:
            data_dir: Directory for storing patient data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._patients: Dict[str, Patient] = {}
        self._load_all()
    
    def _load_all(self):
        """Load all encrypted patient profiles from disk.

        Raises MissingEncryptionKey if the OS keychain key is absent so the
        caller cannot silently proceed with an empty patient list.
        """
        for filepath in self.data_dir.glob("*.phi"):
            try:
                data = decrypt_json(filepath.read_bytes())
                patient = Patient.from_dict(data)
                self._patients[patient.id] = patient
            except MissingEncryptionKey:
                raise  # Loud failure — never silently ignore missing key
            except Exception as exc:
                _logger.warning("Skipping unreadable patient file %s: %s", filepath.name, exc)
                continue  # Skip corrupt individual files but keep loading others
    
    def _save_patient(self, patient: Patient):
        """Save a patient profile to disk as encrypted .phi file."""
        filepath = self.data_dir / f"{patient.id}.phi"
        filepath.write_bytes(encrypt_json(patient.to_dict()))
    
    def create(self, **kwargs) -> Patient:
        """
        Create a new patient profile.

        Args:
            **kwargs: Patient attributes (name, date_of_birth, etc.)

        Returns:
            Created Patient object

        Raises:
            ValueError: If any field value is invalid
        """
        self._validate_fields(kwargs)
        patient = Patient(**kwargs)
        self._patients[patient.id] = patient
        self._save_patient(patient)
        return patient
    
    def get(self, patient_id: str) -> Optional[Patient]:
        """Get a patient by ID."""
        return self._patients.get(patient_id)
    
    def update(self, patient_id: str, **kwargs) -> Optional[Patient]:
        """
        Update a patient profile.

        Args:
            patient_id: Patient ID to update
            **kwargs: Attributes to update

        Returns:
            Updated Patient or None if not found

        Raises:
            ValueError: If attempting to overwrite protected fields or
                        if any field value is invalid
        """
        patient = self._patients.get(patient_id)
        if not patient:
            return None

        # Block protected fields from being overwritten
        protected_overlap = _PROTECTED_FIELDS & set(kwargs.keys())
        if protected_overlap:
            raise ValueError(
                f"Cannot overwrite protected fields: {', '.join(sorted(protected_overlap))}"
            )

        self._validate_fields(kwargs)

        for key, value in kwargs.items():
            if hasattr(patient, key):
                setattr(patient, key, value)

        patient.updated_at = datetime.now().isoformat()
        self._save_patient(patient)
        return patient
    
    def delete(self, patient_id: str) -> bool:
        """
        Delete a patient profile.
        
        Args:
            patient_id: Patient ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        if patient_id not in self._patients:
            return False
        
        filepath = self.data_dir / f"{patient_id}.json"
        if filepath.exists():
            filepath.unlink()
        
        del self._patients[patient_id]
        return True
    
    def list_all(self) -> List[Patient]:
        """Get all patients sorted by name."""
        return sorted(self._patients.values(), key=lambda p: p.name.lower())
    
    def search(self, query: str) -> List[Patient]:
        """
        Search patients by name or ID.
        
        Args:
            query: Search query
            
        Returns:
            Matching patients
        """
        query = query.lower()
        results = []
        for patient in self._patients.values():
            if query in patient.name.lower() or query in patient.id.lower():
                results.append(patient)
        return sorted(results, key=lambda p: p.name.lower())
    
    def add_session_to_patient(self, patient_id: str, session_id: str) -> bool:
        """
        Associate a test session with a patient.
        
        Args:
            patient_id: Patient ID
            session_id: Session/result file identifier
            
        Returns:
            True if successful
        """
        patient = self._patients.get(patient_id)
        if not patient:
            return False
        
        patient.add_session(session_id)
        self._save_patient(patient)
        return True
    
    @property
    def count(self) -> int:
        """Get total number of patients."""
        return len(self._patients)
