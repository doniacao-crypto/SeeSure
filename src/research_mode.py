"""
Research Mode for Eye Movement Assessment.
Extended protocols and batch processing for research applications.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import json
from pathlib import Path
from datetime import datetime


class ResearchProtocol(Enum):
    """Pre-defined research protocols."""
    STANDARD_PURSUIT = "standard_pursuit"
    EXTENDED_PURSUIT = "extended_pursuit"
    GAP_SACCADE = "gap_saccade"
    OVERLAP_SACCADE = "overlap_saccade"
    MEMORY_GUIDED = "memory_guided"
    ANTISACCADE_EXTENDED = "antisaccade_extended"
    FIXATION_30S = "fixation_30s"
    FIXATION_60S = "fixation_60s"


@dataclass
class ResearchConfig:
    """Configuration for research mode testing."""
    protocol: ResearchProtocol = ResearchProtocol.STANDARD_PURSUIT
    
    # Extended timing parameters
    num_trials: int = 50
    trial_duration_ms: float = 2000.0
    inter_trial_interval_ms: float = 1000.0
    
    # Pursuit parameters
    pursuit_speeds: List[float] = field(default_factory=lambda: [0.25, 0.5, 0.75, 1.0])
    pursuit_amplitudes_deg: List[float] = field(default_factory=lambda: [5, 10, 15])
    
    # Saccade parameters
    saccade_eccentricities: List[float] = field(default_factory=lambda: [5, 10, 15, 20])
    gap_duration_ms: float = 200.0
    overlap_duration_ms: float = 200.0
    
    # Data collection
    sample_rate_hz: float = 30.0
    log_raw_data: bool = True
    include_timestamps: bool = True
    
    # Metadata
    experiment_id: str = ""
    condition_label: str = ""
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocol": self.protocol.value,
            "num_trials": self.num_trials,
            "trial_duration_ms": self.trial_duration_ms,
            "inter_trial_interval_ms": self.inter_trial_interval_ms,
            "pursuit_speeds": self.pursuit_speeds,
            "pursuit_amplitudes_deg": self.pursuit_amplitudes_deg,
            "saccade_eccentricities": self.saccade_eccentricities,
            "gap_duration_ms": self.gap_duration_ms,
            "overlap_duration_ms": self.overlap_duration_ms,
            "sample_rate_hz": self.sample_rate_hz,
            "log_raw_data": self.log_raw_data,
            "include_timestamps": self.include_timestamps,
            "experiment_id": self.experiment_id,
            "condition_label": self.condition_label,
            "notes": self.notes
        }


@dataclass
class ResearchSession:
    """A research data collection session."""
    session_id: str
    config: ResearchConfig
    participant_id: str
    start_time: str
    end_time: str = ""
    results: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_trial_result(self, trial_data: Dict[str, Any]):
        """Add a trial result to the session."""
        self.results.append(trial_data)
    
    def finalize(self):
        """Finalize the session."""
        self.end_time = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "config": self.config.to_dict(),
            "participant_id": self.participant_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "results": self.results
        }


class ResearchDataManager:
    """Manages research data collection and export."""
    
    def __init__(self, data_dir: str = "data/research"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def create_session(self, config: ResearchConfig, participant_id: str) -> ResearchSession:
        """Create a new research session."""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return ResearchSession(
            session_id=session_id,
            config=config,
            participant_id=participant_id,
            start_time=datetime.now().isoformat()
        )
    
    def save_session(self, session: ResearchSession):
        """Save a research session to disk."""
        filepath = self.data_dir / f"session_{session.session_id}.json"
        with open(filepath, 'w') as f:
            json.dump(session.to_dict(), f, indent=2)
    
    def export_batch_csv(self, session_ids: List[str], output_path: str):
        """Export multiple sessions to a single CSV for analysis."""
        import csv
        
        rows = []
        headers = set()
        
        for sid in session_ids:
            filepath = self.data_dir / f"session_{sid}.json"
            if not filepath.exists():
                continue
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            for i, result in enumerate(data.get("results", [])):
                row = {
                    "session_id": sid,
                    "participant_id": data["participant_id"],
                    "trial_num": i + 1,
                    "condition": data["config"].get("condition_label", ""),
                    **result
                }
                rows.append(row)
                headers.update(row.keys())
        
        headers = sorted(headers)
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        
        return len(rows)
    
    def list_sessions(self) -> List[Dict[str, str]]:
        """List all research sessions."""
        sessions = []
        for filepath in self.data_dir.glob("session_*.json"):
            with open(filepath, 'r') as f:
                data = json.load(f)
            sessions.append({
                "session_id": data["session_id"],
                "participant_id": data["participant_id"],
                "protocol": data["config"]["protocol"],
                "start_time": data["start_time"],
                "num_trials": len(data.get("results", []))
            })
        return sorted(sessions, key=lambda s: s["start_time"], reverse=True)


# Pre-configured research protocols
RESEARCH_PROTOCOLS = {
    ResearchProtocol.EXTENDED_PURSUIT: ResearchConfig(
        protocol=ResearchProtocol.EXTENDED_PURSUIT,
        num_trials=60,
        trial_duration_ms=30000,
        pursuit_speeds=[0.2, 0.4, 0.6, 0.8, 1.0],
        pursuit_amplitudes_deg=[5, 10, 15, 20]
    ),
    ResearchProtocol.GAP_SACCADE: ResearchConfig(
        protocol=ResearchProtocol.GAP_SACCADE,
        num_trials=100,
        gap_duration_ms=200,
        overlap_duration_ms=0,
        saccade_eccentricities=[5, 10, 15]
    ),
    ResearchProtocol.OVERLAP_SACCADE: ResearchConfig(
        protocol=ResearchProtocol.OVERLAP_SACCADE,
        num_trials=100,
        gap_duration_ms=0,
        overlap_duration_ms=200,
        saccade_eccentricities=[5, 10, 15]
    ),
    ResearchProtocol.ANTISACCADE_EXTENDED: ResearchConfig(
        protocol=ResearchProtocol.ANTISACCADE_EXTENDED,
        num_trials=100,
        gap_duration_ms=200,
        saccade_eccentricities=[8, 12]
    ),
    ResearchProtocol.FIXATION_60S: ResearchConfig(
        protocol=ResearchProtocol.FIXATION_60S,
        num_trials=1,
        trial_duration_ms=60000
    )
}
