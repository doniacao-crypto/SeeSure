"""
Enterprise Features for Eye Movement Assessment.
Practice branding, multi-clinician support, and integrations.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


# =============================================================================
# Practice Branding (Feature 16)
# =============================================================================

@dataclass
class PracticeBranding:
    """Practice branding configuration for reports."""
    practice_name: str = "Eye Movement Assessment Center"
    address_line1: str = ""
    address_line2: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    phone: str = ""
    fax: str = ""
    email: str = ""
    website: str = ""
    logo_path: Optional[str] = None
    primary_color: str = "#3498db"
    secondary_color: str = "#2c3e50"
    disclaimer_text: str = "This is a screening tool only. Results should be interpreted by a qualified eye care professional."
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PracticeBranding':
        return cls(**data)
    
    def get_full_address(self) -> str:
        parts = []
        if self.address_line1:
            parts.append(self.address_line1)
        if self.address_line2:
            parts.append(self.address_line2)
        if self.city or self.state or self.zip_code:
            city_state = f"{self.city}, {self.state} {self.zip_code}".strip()
            parts.append(city_state)
        return "\n".join(parts)


class BrandingManager:
    """Manages practice branding profiles."""
    
    def __init__(self, config_path: str = "data/branding.json"):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._branding: Dict[str, PracticeBranding] = {}
        self._load()
    
    def _load(self):
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            for name, brand_data in data.items():
                self._branding[name] = PracticeBranding.from_dict(brand_data)
    
    def _save(self):
        data = {name: brand.to_dict() for name, brand in self._branding.items()}
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_branding(self, profile_name: str = "default") -> PracticeBranding:
        return self._branding.get(profile_name, PracticeBranding())
    
    def save_branding(self, branding: PracticeBranding, profile_name: str = "default"):
        self._branding[profile_name] = branding
        self._save()
    
    def list_profiles(self) -> List[str]:
        return list(self._branding.keys())


# =============================================================================
# Multi-Clinician Support (Feature 17)
# =============================================================================

class UserRole(Enum):
    """User roles for access control."""
    ADMIN = "admin"
    CLINICIAN = "clinician"
    TECHNICIAN = "technician"
    VIEWER = "viewer"


@dataclass
class Clinician:
    """Clinician user profile."""
    id: str = ""
    username: str = ""
    full_name: str = ""
    email: str = ""
    role: UserRole = UserRole.CLINICIAN
    credentials: str = ""  # e.g., "OD", "MD"
    active: bool = True
    created_at: str = ""
    last_login: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8].upper()
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['role'] = self.role.value
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Clinician':
        data['role'] = UserRole(data.get('role', 'clinician'))
        return cls(**data)


class ClinicianManager:
    """Manages clinician accounts."""
    
    def __init__(self, data_path: str = "data/clinicians.json"):
        self.data_path = Path(data_path)
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self._clinicians: Dict[str, Clinician] = {}
        self._load()
    
    def _load(self):
        if self.data_path.exists():
            with open(self.data_path, 'r') as f:
                data = json.load(f)
            for clin_data in data:
                clin = Clinician.from_dict(clin_data)
                self._clinicians[clin.id] = clin
    
    def _save(self):
        data = [c.to_dict() for c in self._clinicians.values()]
        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create(self, **kwargs) -> Clinician:
        clinician = Clinician(**kwargs)
        self._clinicians[clinician.id] = clinician
        self._save()
        return clinician
    
    def get(self, clinician_id: str) -> Optional[Clinician]:
        return self._clinicians.get(clinician_id)
    
    def list_active(self) -> List[Clinician]:
        return [c for c in self._clinicians.values() if c.active]
    
    def update(self, clinician_id: str, **kwargs) -> Optional[Clinician]:
        clin = self._clinicians.get(clinician_id)
        if not clin:
            return None
        for k, v in kwargs.items():
            if hasattr(clin, k):
                setattr(clin, k, v)
        self._save()
        return clin
    
    def record_login(self, clinician_id: str):
        clin = self._clinicians.get(clinician_id)
        if clin:
            clin.last_login = datetime.now().isoformat()
            self._save()


# =============================================================================
# EHR Integration (Feature 18)
# =============================================================================

@dataclass
class FHIRDiagnosticReport:
    """FHIR DiagnosticReport resource for EHR integration."""
    resource_type: str = "DiagnosticReport"
    id: str = ""
    status: str = "final"
    category_code: str = "OPH"
    category_display: str = "Ophthalmology"
    code_system: str = "http://loinc.org"
    code: str = "79899-9"
    code_display: str = "Eye movement assessment"
    subject_reference: str = ""
    effective_datetime: str = ""
    issued: str = ""
    conclusion: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.effective_datetime:
            self.effective_datetime = datetime.now().isoformat()
        if not self.issued:
            self.issued = datetime.now().isoformat()
    
    def to_fhir_json(self) -> Dict[str, Any]:
        """Convert to FHIR JSON format."""
        return {
            "resourceType": self.resource_type,
            "id": self.id,
            "status": self.status,
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                    "code": self.category_code,
                    "display": self.category_display
                }]
            }],
            "code": {
                "coding": [{
                    "system": self.code_system,
                    "code": self.code,
                    "display": self.code_display
                }]
            },
            "subject": {"reference": self.subject_reference} if self.subject_reference else None,
            "effectiveDateTime": self.effective_datetime,
            "issued": self.issued,
            "conclusion": self.conclusion
        }


def create_fhir_report(result, patient_id: str = "") -> FHIRDiagnosticReport:
    """Create a FHIR DiagnosticReport from test results."""
    conclusion_parts = []
    
    if hasattr(result, 'pursuit_gain'):
        conclusion_parts.append(f"Pursuit gain: {result.pursuit_gain:.2f}")
    if hasattr(result, 'accuracy_degrees'):
        conclusion_parts.append(f"Accuracy: {result.accuracy_degrees:.2f}°")
    if hasattr(result, 'mean_latency_ms'):
        conclusion_parts.append(f"Saccade latency: {result.mean_latency_ms:.0f}ms")
    
    return FHIRDiagnosticReport(
        subject_reference=f"Patient/{patient_id}" if patient_id else "",
        conclusion="; ".join(conclusion_parts) if conclusion_parts else "Eye movement assessment completed"
    )


# =============================================================================
# Multi-Language Support (Feature 20)
# =============================================================================

class Language(Enum):
    """Supported languages."""
    ENGLISH = "en"
    SPANISH = "es"
    CHINESE = "zh"
    FRENCH = "fr"
    GERMAN = "de"


# Basic translations for key UI strings
TRANSLATIONS: Dict[str, Dict[Language, str]] = {
    "start_calibration": {
        Language.ENGLISH: "Start Calibration",
        Language.SPANISH: "Iniciar Calibración",
        Language.CHINESE: "开始校准",
        Language.FRENCH: "Démarrer l'étalonnage",
        Language.GERMAN: "Kalibrierung starten"
    },
    "start_test": {
        Language.ENGLISH: "Start Test",
        Language.SPANISH: "Iniciar Prueba",
        Language.CHINESE: "开始测试",
        Language.FRENCH: "Démarrer le test",
        Language.GERMAN: "Test starten"
    },
    "export_results": {
        Language.ENGLISH: "Export Results",
        Language.SPANISH: "Exportar Resultados",
        Language.CHINESE: "导出结果",
        Language.FRENCH: "Exporter les résultats",
        Language.GERMAN: "Ergebnisse exportieren"
    },
    "face_detected": {
        Language.ENGLISH: "Face Detected",
        Language.SPANISH: "Rostro Detectado",
        Language.CHINESE: "检测到人脸",
        Language.FRENCH: "Visage détecté",
        Language.GERMAN: "Gesicht erkannt"
    },
    "calibration_complete": {
        Language.ENGLISH: "Calibration Complete",
        Language.SPANISH: "Calibración Completa",
        Language.CHINESE: "校准完成",
        Language.FRENCH: "Étalonnage terminé",
        Language.GERMAN: "Kalibrierung abgeschlossen"
    }
}


class Localizer:
    """Handles UI localization."""
    
    def __init__(self, language: Language = Language.ENGLISH):
        self.language = language
    
    def get(self, key: str) -> str:
        """Get localized string."""
        if key in TRANSLATIONS:
            return TRANSLATIONS[key].get(self.language, TRANSLATIONS[key][Language.ENGLISH])
        return key
    
    def set_language(self, language: Language):
        self.language = language


# =============================================================================
# Tablet/Touch Mode (Feature 19)
# =============================================================================

@dataclass
class TouchModeConfig:
    """Configuration for tablet/touch interface."""
    enabled: bool = False
    button_size_multiplier: float = 1.5  # Larger buttons for touch
    font_size_multiplier: float = 1.2
    show_on_screen_keyboard: bool = True
    simplified_workflow: bool = True
    auto_fullscreen: bool = True
    swipe_navigation: bool = True
    min_touch_target_px: int = 44  # Apple HIG minimum


def apply_touch_mode(config: TouchModeConfig) -> Dict[str, str]:
    """Generate CSS overrides for touch mode."""
    if not config.enabled:
        return {}
    
    return {
        "QPushButton": f"""
            min-height: {int(44 * config.button_size_multiplier)}px;
            min-width: {int(88 * config.button_size_multiplier)}px;
            font-size: {int(14 * config.font_size_multiplier)}px;
            padding: 12px 24px;
        """,
        "QComboBox": f"""
            min-height: {int(44 * config.button_size_multiplier)}px;
            font-size: {int(14 * config.font_size_multiplier)}px;
        """,
        "QLabel": f"""
            font-size: {int(12 * config.font_size_multiplier)}px;
        """
    }
