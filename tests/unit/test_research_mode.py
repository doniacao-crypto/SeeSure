"""
Unit tests for research_mode.py - Extended research protocols.
"""

import pytest
import tempfile
import os
from src.research_mode import (
    ResearchProtocol, ResearchConfig, ResearchSession,
    ResearchDataManager, RESEARCH_PROTOCOLS
)


class TestResearchProtocol:
    """Test ResearchProtocol enum."""
    
    def test_protocol_values(self):
        assert ResearchProtocol.STANDARD_PURSUIT.value == "standard_pursuit"
        assert ResearchProtocol.EXTENDED_PURSUIT.value == "extended_pursuit"
        assert ResearchProtocol.GAP_SACCADE.value == "gap_saccade"
        assert ResearchProtocol.ANTISACCADE_EXTENDED.value == "antisaccade_extended"


class TestResearchConfig:
    """Test ResearchConfig dataclass."""
    
    def test_default_config(self):
        config = ResearchConfig()
        assert config.num_trials == 50
        assert config.trial_duration_ms == 2000.0
        assert config.log_raw_data is True
    
    def test_custom_config(self):
        config = ResearchConfig(
            protocol=ResearchProtocol.EXTENDED_PURSUIT,
            num_trials=100,
            sample_rate_hz=60.0
        )
        assert config.num_trials == 100
        assert config.sample_rate_hz == 60.0
    
    def test_default_pursuit_speeds(self):
        config = ResearchConfig()
        assert 0.25 in config.pursuit_speeds
        assert 1.0 in config.pursuit_speeds
    
    def test_default_saccade_eccentricities(self):
        config = ResearchConfig()
        assert 5 in config.saccade_eccentricities
        assert 20 in config.saccade_eccentricities
    
    def test_to_dict(self):
        config = ResearchConfig(
            protocol=ResearchProtocol.GAP_SACCADE,
            experiment_id="EXP001"
        )
        data = config.to_dict()
        assert data["protocol"] == "gap_saccade"
        assert data["experiment_id"] == "EXP001"
        assert "pursuit_speeds" in data


class TestResearchSession:
    """Test ResearchSession dataclass."""
    
    def test_create_session(self):
        config = ResearchConfig()
        session = ResearchSession(
            session_id="S001",
            config=config,
            participant_id="P001",
            start_time="2024-01-01T10:00:00"
        )
        assert session.session_id == "S001"
        assert session.participant_id == "P001"
    
    def test_add_trial_result(self):
        config = ResearchConfig()
        session = ResearchSession(
            session_id="S001",
            config=config,
            participant_id="P001",
            start_time="2024-01-01T10:00:00"
        )
        
        session.add_trial_result({"trial": 1, "latency": 200})
        session.add_trial_result({"trial": 2, "latency": 210})
        
        assert len(session.results) == 2
    
    def test_finalize_sets_end_time(self):
        config = ResearchConfig()
        session = ResearchSession(
            session_id="S001",
            config=config,
            participant_id="P001",
            start_time="2024-01-01T10:00:00"
        )
        
        assert session.end_time == ""
        session.finalize()
        assert session.end_time != ""
    
    def test_to_dict(self):
        config = ResearchConfig()
        session = ResearchSession(
            session_id="S001",
            config=config,
            participant_id="P001",
            start_time="2024-01-01T10:00:00"
        )
        
        data = session.to_dict()
        assert data["session_id"] == "S001"
        assert data["participant_id"] == "P001"
        assert "config" in data


class TestResearchDataManager:
    """Test ResearchDataManager class."""
    
    def test_create_manager(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ResearchDataManager(data_dir=tmpdir)
            assert os.path.exists(tmpdir)
    
    def test_create_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ResearchDataManager(data_dir=tmpdir)
            config = ResearchConfig()
            
            session = manager.create_session(config, participant_id="P001")
            assert session.participant_id == "P001"
            assert session.session_id != ""
    
    def test_save_and_list_sessions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ResearchDataManager(data_dir=tmpdir)
            config = ResearchConfig()
            
            session = manager.create_session(config, "P001")
            session.finalize()
            manager.save_session(session)
            
            sessions = manager.list_sessions()
            assert len(sessions) == 1
            assert sessions[0]["participant_id"] == "P001"


class TestPredefinedProtocols:
    """Test pre-configured research protocols."""
    
    def test_extended_pursuit_exists(self):
        assert ResearchProtocol.EXTENDED_PURSUIT in RESEARCH_PROTOCOLS
    
    def test_extended_pursuit_config(self):
        config = RESEARCH_PROTOCOLS[ResearchProtocol.EXTENDED_PURSUIT]
        assert config.num_trials == 60
        assert config.trial_duration_ms == 30000
    
    def test_gap_saccade_exists(self):
        assert ResearchProtocol.GAP_SACCADE in RESEARCH_PROTOCOLS
    
    def test_gap_saccade_config(self):
        config = RESEARCH_PROTOCOLS[ResearchProtocol.GAP_SACCADE]
        assert config.gap_duration_ms == 200
        assert config.num_trials == 100
    
    def test_overlap_saccade_exists(self):
        assert ResearchProtocol.OVERLAP_SACCADE in RESEARCH_PROTOCOLS
    
    def test_antisaccade_extended_config(self):
        config = RESEARCH_PROTOCOLS[ResearchProtocol.ANTISACCADE_EXTENDED]
        assert config.num_trials == 100
    
    def test_fixation_60s_config(self):
        config = RESEARCH_PROTOCOLS[ResearchProtocol.FIXATION_60S]
        assert config.trial_duration_ms == 60000
        assert config.num_trials == 1
