"""
Integration tests for TimeframeConfigService with API endpoints

Tests the complete flow from API request to service to configuration file.
"""

import pytest
import json
from unittest.mock import patch, mock_open
from api.services.timeframe_config_service import TimeframeConfigService


class TestTimeframeConfigIntegration:
    """Integration tests for timeframe configuration"""
    
    @pytest.fixture
    def service(self):
        """Create service instance"""
        return TimeframeConfigService()
    
    def test_get_available_timeframes_api_flow(self, service):
        """Test getting available timeframes (API flow)"""
        result = service.get_available_timeframes()
        
        # Verify response structure matches API requirements
        assert isinstance(result, dict)
        assert "timeframes" in result
        assert "count" in result
        
        # Verify all required timeframes are available
        timeframe_values = [tf["value"] for tf in result["timeframes"]]
        required_timeframes = ["1", "5", "15", "30", "60", "240", "1440"]
        
        for required in required_timeframes:
            assert required in timeframe_values, f"Missing required timeframe: {required}"
        
        # Verify each timeframe has required fields
        for tf in result["timeframes"]:
            assert "value" in tf
            assert "label" in tf
            assert "minutes" in tf
            assert "description" in tf
            assert "fetch_time_ms" in tf
            
            # Verify label format
            assert tf["label"] in ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
    
    @patch('config.TIMEFRAMES', {
        "trend": "240",
        "zones": "30",
        "confirmation": "5"
    })
    def test_get_configured_timeframes_api_flow(self, service):
        """Test getting configured timeframes (API flow)"""
        result = service.get_configured_timeframes()
        
        # Verify response structure
        assert isinstance(result, dict)
        assert "timeframes" in result
        assert "timeframe_list" in result
        assert "count" in result
        assert "estimated_fetch_time_ms" in result
        
        # Verify timeframe mapping
        assert result["timeframes"]["trend"] == "240"
        assert result["timeframes"]["zones"] == "30"
        assert result["timeframes"]["confirmation"] == "5"
        
        # Verify list is sorted
        assert result["timeframe_list"] == ["5", "30", "240"]
        
        # Verify count matches
        assert result["count"] == len(result["timeframe_list"])
        
        # Verify estimated time is reasonable
        assert 0 < result["estimated_fetch_time_ms"] < 10000
    
    @patch('config.TIMEFRAMES', {})
    @patch('builtins.open', new_callable=mock_open, read_data='''
TIMEFRAMES = {
    "trend": "240",
    "zones": "30",
    "confirmation": "5",
}
''')
    def test_update_timeframes_complete_flow(self, mock_file, service):
        """Test complete update flow from API to persistence"""
        # Simulate API request
        new_timeframes = ["5", "15", "60"]
        
        # Call service
        result = service.update_timeframes(new_timeframes)
        
        # Verify success response
        assert result["success"] is True
        assert result["count"] == 3
        assert set(result["timeframes"]) == set(new_timeframes)
        
        # Verify timeframe mapping
        mapping = result["timeframe_mapping"]
        assert mapping["trend"] == "60"  # Highest
        assert mapping["zones"] == "15"  # Middle
        assert mapping["confirmation"] == "5"  # Lowest
        
        # Verify estimated fetch time
        assert result["estimated_fetch_time_ms"] > 0
        
        # Verify file operations
        assert mock_file.call_count == 2  # Read and write
        
        # Verify write was called with updated content
        handle = mock_file()
        handle.write.assert_called_once()
        written_content = handle.write.call_args[0][0]
        
        # Check new values are in written content
        assert '"trend": "60"' in written_content
        assert '"zones": "15"' in written_content
        assert '"confirmation": "5"' in written_content
    
    def test_validation_minimum_timeframes(self, service):
        """Test validation: minimum 2 timeframes (Requirement 19.8)"""
        # Try with only 1 timeframe
        result = service.update_timeframes(["5"])
        
        assert result["success"] is False
        assert "error" in result
        assert "at least 2" in result["error"].lower()
        assert "timestamp" in result
    
    def test_validation_invalid_timeframe(self, service):
        """Test validation: invalid timeframe value"""
        # Try with invalid timeframe
        result = service.update_timeframes(["5", "999"])
        
        assert result["success"] is False
        assert "error" in result
        assert "invalid" in result["error"].lower()
    
    def test_validation_duplicate_timeframes(self, service):
        """Test validation: duplicate timeframes not allowed"""
        result = service.update_timeframes(["5", "30", "5"])
        
        assert result["success"] is False
        assert "error" in result
        assert "duplicate" in result["error"].lower()
    
    def test_estimated_fetch_time_calculation(self, service):
        """Test estimated fetch time calculation (Requirement 19.9)"""
        # Test with different timeframe combinations
        test_cases = [
            (["5", "30"], 30),
            (["5", "30", "240"], 30),
            (["1", "5", "15", "30"], 30),
        ]
        
        for timeframes, num_symbols in test_cases:
            estimated_time = service._calculate_fetch_time(timeframes, num_symbols)
            
            # Should be positive
            assert estimated_time > 0
            
            # Should be reasonable (not too high)
            assert estimated_time < 10000  # Less than 10 seconds
    
    def test_timeframe_role_mapping_two_timeframes(self, service):
        """Test role mapping with 2 timeframes"""
        mapping = service._map_timeframes_to_roles(["5", "240"])
        
        # With 2 timeframes, highest is used for both trend and zones
        assert mapping["trend"] == "240"
        assert mapping["zones"] == "240"
        assert mapping["confirmation"] == "5"
    
    def test_timeframe_role_mapping_three_timeframes(self, service):
        """Test role mapping with 3 timeframes"""
        mapping = service._map_timeframes_to_roles(["5", "30", "240"])
        
        # With 3 timeframes, each gets a distinct role
        assert mapping["trend"] == "240"  # Highest
        assert mapping["zones"] == "30"   # Middle
        assert mapping["confirmation"] == "5"  # Lowest
    
    def test_timeframe_role_mapping_many_timeframes(self, service):
        """Test role mapping with many timeframes"""
        mapping = service._map_timeframes_to_roles(["1", "5", "15", "30", "60", "240"])
        
        # Should use highest, middle, and lowest
        assert mapping["trend"] == "240"  # Highest
        assert mapping["zones"] == "30"   # Middle (index 3 of 6)
        assert mapping["confirmation"] == "1"  # Lowest
    
    @patch('config.TIMEFRAMES', {})
    def test_update_sorts_timeframes(self, service):
        """Test that update sorts timeframes correctly"""
        # Provide unsorted list
        unsorted = ["240", "5", "30", "15"]
        
        result = service.update_timeframes(unsorted)
        
        # Should be sorted in result
        assert result["success"] is True
        assert result["timeframes"] == ["5", "15", "30", "240"]
    
    def test_api_response_format_consistency(self, service):
        """Test that all API responses have consistent format"""
        # Test successful update
        with patch.object(service, '_persist_to_file'):
            success_result = service.update_timeframes(["5", "30"])
            
            assert "success" in success_result
            assert "timestamp" in success_result
            assert isinstance(success_result["timestamp"], int)
        
        # Test failed update
        fail_result = service.update_timeframes(["5"])  # Too few
        
        assert "success" in fail_result
        assert "timestamp" in fail_result
        assert "error" in fail_result
        assert isinstance(fail_result["timestamp"], int)
    
    def test_timeframe_labels_match_values(self, service):
        """Test that timeframe labels correctly represent values"""
        result = service.get_available_timeframes()
        
        expected_mapping = {
            "1": "1m",
            "5": "5m",
            "15": "15m",
            "30": "30m",
            "60": "1h",
            "240": "4h",
            "1440": "1d"
        }
        
        for tf in result["timeframes"]:
            value = tf["value"]
            label = tf["label"]
            assert expected_mapping[value] == label, \
                f"Label mismatch for {value}: expected {expected_mapping[value]}, got {label}"
    
    def test_fetch_time_scales_with_symbols(self, service):
        """Test that estimated fetch time scales with number of symbols"""
        timeframes = ["5", "30", "240"]
        
        time_10 = service._calculate_fetch_time(timeframes, num_symbols=10)
        time_30 = service._calculate_fetch_time(timeframes, num_symbols=30)
        time_50 = service._calculate_fetch_time(timeframes, num_symbols=50)
        
        # More symbols should take more time
        assert time_10 < time_30 < time_50
    
    @patch('config.TIMEFRAMES', {
        "trend": "240",
        "zones": "30",
        "confirmation": "5"
    })
    def test_get_configured_returns_unique_timeframes(self, service):
        """Test that configured timeframes list contains unique values only"""
        result = service.get_configured_timeframes()
        
        timeframe_list = result["timeframe_list"]
        
        # Should have no duplicates
        assert len(timeframe_list) == len(set(timeframe_list))
        
        # Should be sorted
        assert timeframe_list == sorted(timeframe_list, key=lambda x: int(x))


class TestTimeframeConfigErrorHandling:
    """Test error handling in timeframe configuration"""
    
    @pytest.fixture
    def service(self):
        """Create service instance"""
        return TimeframeConfigService()
    
    def test_persist_handles_file_not_found(self, service):
        """Test graceful handling of missing config file"""
        with patch('builtins.open', side_effect=FileNotFoundError):
            with pytest.raises(IOError, match="not found"):
                service._persist_to_file({"trend": "240", "zones": "30", "confirmation": "5"})
    
    def test_persist_handles_invalid_config_format(self, service):
        """Test handling of config file without TIMEFRAMES"""
        with patch('builtins.open', mock_open(read_data='# No TIMEFRAMES here')):
            with pytest.raises(IOError):
                service._persist_to_file({"trend": "240", "zones": "30", "confirmation": "5"})
    
    def test_update_handles_persist_failure(self, service):
        """Test that update returns error when persist fails"""
        with patch.object(service, '_persist_to_file', side_effect=IOError("Disk full")):
            result = service.update_timeframes(["5", "30"])
            
            assert result["success"] is False
            assert "error" in result
            assert "failed" in result["error"].lower()
    
    def test_validation_handles_none_input(self, service):
        """Test validation handles None input"""
        error = service._validate_timeframes(None)
        assert "non-empty list" in error.lower()
    
    def test_validation_handles_empty_string(self, service):
        """Test validation handles empty string in list"""
        error = service._validate_timeframes(["5", ""])
        assert "invalid" in error.lower()
    
    def test_validation_handles_non_numeric(self, service):
        """Test validation handles non-numeric timeframe"""
        error = service._validate_timeframes(["5", "abc"])
        assert "invalid" in error.lower()
