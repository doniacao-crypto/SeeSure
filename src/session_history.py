"""
Session History Manager for Eye Movement Assessment.
Manages storage, retrieval, and comparison of test sessions.
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class SessionSummary:
    """Summary of a test session for display."""
    filename: str
    timestamp: datetime
    pattern: str
    duration_seconds: float
    accuracy_degrees: Optional[float]
    pursuit_gain: Optional[float]
    
    def to_display_string(self) -> str:
        """Format for list display."""
        date_str = self.timestamp.strftime("%Y-%m-%d %H:%M")
        accuracy = f"{self.accuracy_degrees:.2f}°" if self.accuracy_degrees else "N/A"
        gain = f"{self.pursuit_gain:.2f}" if self.pursuit_gain else "N/A"
        return f"{date_str} | {self.pattern:12} | Acc: {accuracy} | Gain: {gain}"


class SessionHistoryManager:
    """Manages test session history."""
    
    def __init__(self, results_dir: str = "results"):
        """
        Initialize the history manager.
        
        Args:
            results_dir: Directory containing test result files
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
    
    def list_sessions(self, limit: int = 50) -> List[SessionSummary]:
        """
        List available test sessions, most recent first.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of SessionSummary objects
        """
        sessions = []
        
        for filepath in self.results_dir.glob("*.json"):
            try:
                summary = self._load_summary(filepath)
                if summary:
                    sessions.append(summary)
            except Exception:
                continue  # Skip invalid files
        
        # Sort by timestamp, newest first
        sessions.sort(key=lambda s: s.timestamp, reverse=True)
        return sessions[:limit]
    
    def _load_summary(self, filepath: Path) -> Optional[SessionSummary]:
        """Load summary from a result file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Parse timestamp from filename or data
        timestamp = self._parse_timestamp(filepath.name, data)
        if not timestamp:
            return None
        
        # Extract metrics
        metrics = data.get('metrics', {})
        
        return SessionSummary(
            filename=filepath.name,
            timestamp=timestamp,
            pattern=data.get('pattern', 'unknown'),
            duration_seconds=data.get('duration_seconds', 0),
            accuracy_degrees=metrics.get('accuracy_degrees'),
            pursuit_gain=metrics.get('pursuit_gain')
        )
    
    def _parse_timestamp(self, filename: str, data: Dict[str, Any]) -> Optional[datetime]:
        """Parse timestamp from filename or data."""
        # Try to get from data first
        if 'timestamp' in data:
            try:
                return datetime.fromisoformat(data['timestamp'])
            except ValueError:
                pass
        
        # Parse from filename: test_pattern_YYYYMMDD_HHMMSS.json
        parts = filename.replace('.json', '').split('_')
        if len(parts) >= 3:
            try:
                date_str = parts[-2]  # YYYYMMDD
                time_str = parts[-1]  # HHMMSS
                return datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            except ValueError:
                pass
        
        # Fall back to file modification time
        filepath = self.results_dir / filename
        if filepath.exists():
            return datetime.fromtimestamp(filepath.stat().st_mtime)
        
        return None
    
    def load_session(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Load full session data.
        
        Args:
            filename: Name of the result file
            
        Returns:
            Full session data or None if not found
        """
        filepath = self.results_dir / filename
        if not filepath.exists():
            return None
        
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def delete_session(self, filename: str) -> bool:
        """
        Delete a session file.
        
        Args:
            filename: Name of the result file
            
        Returns:
            True if deleted, False if not found
        """
        filepath = self.results_dir / filename
        if filepath.exists():
            filepath.unlink()
            return True
        return False
    
    def get_session_count(self) -> int:
        """Get total number of saved sessions."""
        return len(list(self.results_dir.glob("*.json")))
