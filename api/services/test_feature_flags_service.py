"""
Unit tests for Feature Flags Service

Tests feature flag retrieval, validation, and update operations.
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from api.services.feature_flags_service import FeatureFlagsService


class TestFeatureFlagsService:
    """Test suite for FeatureFlagsService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = FeatureFlagsService()
    
    def test_get_all_flags_returns_four_phases(self):
        """Test that get_all_flags returns flags grouped by 4 phases"""
        flags = self.service.get_all_flags()
        
        assert "phase1" in flags
        assert "phase2" in flags
        assert "phase3" in flags
        assert "phase4" in flags
        
        # Verify each phase has flags
        assert len(flags["phase1"]) > 0
        assert len(flags["phase2"]) > 0
        assert len(flags["phase3"]) > 0
        assert len(flags["phase4"]) > 0
    
    def test_get_all_flags_structure(self):
        """Test that flags have correct structure"""
        flags = self.service.get_all_flags()
        
        # Check first flag in phase1
        first_flag = flags["phase1"][0]
        
        assert "name" in first_flag
        assert "enabled" in first_flag
        assert "description" in first_flag
        assert "confidenceBoost" in first_flag
        assert "phase" in first_flag
        
        # Verify types
        assert isinstance(first_flag["name"], str)
        assert isinstance(first_flag["enabled"], bool)
        assert isinstance(first_flag["description"], str)
        assert isinstance(first_flag["confidenceBoost"], int)
        assert isinstance(first_flag["phase"], int)
        assert first_flag["phase"] == 1
    
    def test_get_flag_state_valid_flag(self):
        """Test getting state for a valid feature flag"""
        flag = self.service.get_flag_state("vsa_analysis")
        
        assert flag is not None
        assert flag["name"] == "vsa_analysis"
        assert "enabled" in flag
        assert "description" in flag
        assert "confidenceBoost" in flag
        assert "phase" in flag
        assert flag["phase"] == 1
    
    def test_get_flag_state_invalid_flag(self):
        """Test getting state for an invalid feature flag"""
        flag = self.service.get_flag_state("invalid_flag_name")
        
        assert flag is None
    
    def test_validate_flag_name_valid(self):
        """Test validation of valid flag names"""
        assert self.service._validate_flag_name("vsa_analysis") is True
        assert self.service._validate_flag_name("wyckoff_method") is True
        assert self.service._validate_flag_name("mtf_confluence") is True
    
    def test_validate_flag_name_invalid(self):
        """Test validation of invalid flag names"""
        assert self.service._validate_flag_name("invalid_flag") is False
        assert self.service._validate_flag_name("") is False
        assert self.service._validate_flag_name("random_name") is False
    
    def test_get_flag_phase(self):
        """Test determining flag phase"""
        assert self.service._get_flag_phase("vsa_analysis") == 1
        assert self.service._get_flag_phase("wyckoff_method") == 1
        assert self.service._get_flag_phase("mtf_confluence") == 2
        assert self.service._get_flag_phase("dynamic_tp") == 3
        assert self.service._get_flag_phase("enhanced_risk") == 4
        assert self.service._get_flag_phase("invalid_flag") == 0
    
    def test_get_enabled_flags(self):
        """Test getting list of enabled flags"""
        enabled = self.service.get_enabled_flags()
        
        assert isinstance(enabled, list)
        # mtf_confluence and ml_confidence_calibration are enabled by default
        assert "mtf_confluence" in enabled
        assert "ml_confidence_calibration" in enabled
    
    def test_update_flag_invalid_name(self):
        """Test updating flag with invalid name"""
        result = self.service.update_flag("invalid_flag", True)
        
        assert result["success"] is False
        assert "error" in result
        assert "Invalid feature flag name" in result["error"]
    
    def test_update_in_memory(self):
        """Test in-memory flag update"""
        import config.feature_flags as ff
        
        # Get initial state
        initial_state = ff.PHASE_1_FEATURES["vsa_analysis"]["enabled"]
        
        # Update in memory
        self.service._update_in_memory("vsa_analysis", not initial_state)
        
        # Verify update
        assert ff.PHASE_1_FEATURES["vsa_analysis"]["enabled"] == (not initial_state)
        
        # Restore original state
        self.service._update_in_memory("vsa_analysis", initial_state)
    
    def test_get_service_status(self):
        """Test service status reporting"""
        status = self.service.get_service_status()
        
        assert "config_file_exists" in status
        assert "config_file_writable" in status
        assert "config_path" in status
        
        assert status["config_file_exists"] is True
        assert status["config_path"] == "config/feature_flags.py"
    
    def test_build_phase_flags(self):
        """Test building phase flags list"""
        import config.feature_flags as ff
        
        phase1_flags = self.service._build_phase_flags(ff.PHASE_1_FEATURES, 1)
        
        assert isinstance(phase1_flags, list)
        assert len(phase1_flags) == len(ff.PHASE_1_FEATURES)
        
        # Verify all flags have correct phase
        for flag in phase1_flags:
            assert flag["phase"] == 1
    
    def test_total_flag_count(self):
        """Test that all 20 feature flags are present"""
        flags = self.service.get_all_flags()
        
        total_count = (
            len(flags["phase1"]) +
            len(flags["phase2"]) +
            len(flags["phase3"]) +
            len(flags["phase4"])
        )
        
        assert total_count == 20, f"Expected 20 feature flags, found {total_count}"
    
    def test_confidence_boost_values(self):
        """Test that confidence boost values are non-negative integers"""
        flags = self.service.get_all_flags()
        
        for phase in ["phase1", "phase2", "phase3", "phase4"]:
            for flag in flags[phase]:
                assert isinstance(flag["confidenceBoost"], int)
                assert flag["confidenceBoost"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
