"""
Unit tests for TimeframeConfigService

Tests timeframe configuration management including:
- Retrieving available timeframes
- Getting configured timeframes
- Updating timeframes with validation
- Calculating estimated fetch time
- Persisting changes to configuration file
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from api.services.timeframe_config_service import TimeframeConfigService


class TestTimeframeConfigService:
    """Test suite for TimeframeConfigService"""
    
    @pytest.fixture
    def service(self):
        """Create service instance"""
        return TimeframeConfigService()
    
    def test_initialization(self, service):
        """Test service initialization"""
        assert service.config_path == "config.py"
        assert len(service.AVAILABLE_TIMEFRAMES) == 7
    
    def test_get_available_timeframes(self, service):
        """Test retrieving available timeframes"""
        result = service.get_available_timeframes()
        
        assert "timeframes" in result
        assert "count" in result
        assert result["count"] == 7
        assert len(result["timeframes"]) == 7
        
        # Check first timeframe structure
        tf = result["timeframes"][0]
        assert "value" in tf
        assert "label" in tf
        assert "minutes" in tf
        assert "description" in tf
        assert "fetch_time_ms" in tf
        
        # Check sorting by minutes
        minutes = [tf["minutes"] for tf in result["timeframes"]]
        assert minutes == sorted(minutes)
    
    @patch('config.TIMEFRAMES', {
        "trend": "240",
        "zones": "30",
        "confirmation": "5"
    })
    def test_get_configured_timeframes(self, service):
        """Test retrieving configured timeframes"""
        result = service.get_configured_timeframes()
        
        assert "timeframes" in result
        assert "timeframe_list" in result
        assert "count" in result
        assert "estimated_fetch_time_ms" in result
        
        assert result["timeframes"]["trend"] == "240"
        assert result["timeframes"]["zones"] == "30"
        assert result["timeframes"]["confirmation"] == "5"
        assert set(result["timeframe_list"]) == {"5", "30", "240"}
        assert result["count"] == 3
        assert result["estimated_fetch_time_ms"] > 0
    
    def test_validate_timeframes_success(self, service):
        """Test successful timeframe validation"""
        valid_lists = [
            ["5", "30"],
            ["5", "30", "240"],
            ["1", "5", "15", "30", "60", "240", "1440"]
        ]
        
        for tf_list in valid_lists:
            error = service._validate_timeframes(tf_list)
            assert error == "", f"Expected no error for {tf_list}, got: {error}"
    
    def test_validate_timeframes_minimum_count(self, service):
        """Test validation fails with fewer than 2 timeframes"""
        error = service._validate_timeframes(["5"])
        assert "at least 2 timeframes" in error.lower()
    
    def test_validate_timeframes_empty_list(self, service):
        """Test validation fails with empty list"""
        error = service._validate_timeframes([])
        assert "non-empty list" in error.lower()
    
    def test_validate_timeframes_invalid_value(self, service):
        """Test validation fails with invalid timeframe"""
        error = service._validate_timeframes(["5", "999"])
        assert "invalid timeframe" in error.lower()
    
    def test_validate_timeframes_duplicates(self, service):
        """Test validation fails with duplicate timeframes"""
        error = service._validate_timeframes(["5", "30", "5"])
        assert "duplicate" in error.lower()
    
    def test_validate_timeframes_maximum_count(self, service):
        """Test validation fails with too many timeframes"""
        error = service._validate_timeframes(["1", "5", "15", "30", "60", "240", "1440", "999"])
        assert "maximum" in error.lower() or "invalid" in error.lower()
    
    def test_map_timeframes_to_roles_two_timeframes(self, service):
        """Test mapping 2 timeframes to roles"""
        mapping = service._map_timeframes_to_roles(["5", "240"])
        
        assert mapping["trend"] == "240"
        assert mapping["zones"] == "240"
        assert mapping["confirmation"] == "5"
    
    def test_map_timeframes_to_roles_three_timeframes(self, service):
        """Test mapping 3 timeframes to roles"""
        mapping = service._map_timeframes_to_roles(["5", "30", "240"])
        
        assert mapping["trend"] == "240"
        assert mapping["zones"] == "30"
        assert mapping["confirmation"] == "5"
    
    def test_map_timeframes_to_roles_many_timeframes(self, service):
        """Test mapping many timeframes to roles"""
        mapping = service._map_timeframes_to_roles(["1", "5", "15", "30", "60"])
        
        assert mapping["trend"] == "60"  # Highest
        assert mapping["zones"] == "15"  # Middle
        assert mapping["confirmation"] == "1"  # Lowest
    
    def test_calculate_fetch_time(self, service):
        """Test estimated fetch time calculation"""
        # Test with 2 timeframes
        time1 = service._calculate_fetch_time(["5", "30"], num_symbols=30)
        assert time1 > 0
        
        # Test with 3 timeframes
        time2 = service._calculate_fetch_time(["5", "30", "240"], num_symbols=30)
        assert time2 > 0
        
        # Both should be positive
        assert time1 > 0 and time2 > 0
    
    def test_calculate_fetch_time_different_symbols(self, service):
        """Test fetch time scales with symbol count"""
        time_10 = service._calculate_fetch_time(["5", "30"], num_symbols=10)
        time_30 = service._calculate_fetch_time(["5", "30"], num_symbols=30)
        
        # More symbols should take more time
        assert time_30 > time_10
    
    @patch('config.TIMEFRAMES', {})
    def test_update_in_memory(self, service):
        """Test updating in-memory configuration"""
        import config
        mapping = {"trend": "240", "zones": "30", "confirmation": "5"}
        service._update_in_memory(mapping)
        
        assert config.TIMEFRAMES == mapping
    
    @patch('builtins.open', new_callable=mock_open, read_data='''
TIMEFRAMES = {
    "trend": "240",
    "zones": "30",
    "confirmation": "5",
}
''')
    def test_persist_to_file_success(self, mock_file, service):
        """Test persisting timeframes to file"""
        mapping = {"trend": "60", "zones": "15", "confirmation": "5"}
        
        service._persist_to_file(mapping)
        
        # Check file was opened for reading and writing
        assert mock_file.call_count == 2
        
        # Check write was called
        handle = mock_file()
        handle.write.assert_called_once()
        
        # Check written content contains new values
        written_content = handle.write.call_args[0][0]
        assert '"trend": "60"' in written_content
        assert '"zones": "15"' in written_content
        assert '"confirmation": "5"' in written_content
    
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_persist_to_file_not_found(self, mock_file, service):
        """Test persist fails when file not found"""
        mapping = {"trend": "240", "zones": "30", "confirmation": "5"}
        
        with pytest.raises(IOError, match="not found"):
            service._persist_to_file(mapping)
    
    @patch('builtins.open', new_callable=mock_open, read_data='# No TIMEFRAMES here')
    def test_persist_to_file_pattern_not_found(self, mock_file, service):
        """Test persist fails when TIMEFRAMES not in file"""
        mapping = {"trend": "240", "zones": "30", "confirmation": "5"}
        
        with pytest.raises(IOError):
            service._persist_to_file(mapping)
    
    @patch('config.TIMEFRAMES', {})
    @patch.object(TimeframeConfigService, '_persist_to_file')
    def test_update_timeframes_success(self, mock_persist, service):
        """Test successful timeframe update"""
        timeframe_list = ["5", "30", "240"]
        
        result = service.update_timeframes(timeframe_list)
        
        assert result["success"] is True
        assert result["count"] == 3
        assert set(result["timeframes"]) == set(timeframe_list)
        assert "timeframe_mapping" in result
        assert result["estimated_fetch_time_ms"] > 0
        assert "message" in result
        assert "timestamp" in result
        
        # Check persist was called
        mock_persist.assert_called_once()
    
    @patch('config.TIMEFRAMES', {})
    def test_update_timeframes_validation_error(self, service):
        """Test update fails with validation error"""
        # Only 1 timeframe (minimum is 2)
        result = service.update_timeframes(["5"])
        
        assert result["success"] is False
        assert "error" in result
        assert "at least 2" in result["error"].lower()
    
    @patch('config.TIMEFRAMES', {})
    def test_update_timeframes_invalid_timeframe(self, service):
        """Test update fails with invalid timeframe"""
        result = service.update_timeframes(["5", "999"])
        
        assert result["success"] is False
        assert "error" in result
        assert "invalid" in result["error"].lower()
    
    @patch('config.TIMEFRAMES', {})
    @patch.object(TimeframeConfigService, '_persist_to_file', side_effect=IOError("Write failed"))
    def test_update_timeframes_persist_error(self, mock_persist, service):
        """Test update fails when persist fails"""
        result = service.update_timeframes(["5", "30"])
        
        assert result["success"] is False
        assert "error" in result
    
    def test_timeframe_sorting(self, service):
        """Test timeframes are sorted correctly"""
        # Provide unsorted list
        unsorted = ["240", "5", "30"]
        
        result = service.update_timeframes(unsorted)
        
        # Should be sorted in result
        assert result["timeframes"] == ["5", "30", "240"]
    
    @patch('config.TIMEFRAMES', {})
    def test_update_timeframes_removes_duplicates_implicitly(self, service):
        """Test that validation catches duplicates"""
        result = service.update_timeframes(["5", "30", "5"])
        
        assert result["success"] is False
        assert "duplicate" in result["error"].lower()


class TestTimeframeConfigServiceIntegration:
    """Integration tests with actual config module"""
    
    @pytest.fixture
    def service(self):
        """Create service instance"""
        return TimeframeConfigService()
    
    def test_get_configured_timeframes_real_config(self, service):
        """Test getting timeframes from real config module"""
        try:
            result = service.get_configured_timeframes()
            
            assert "timeframes" in result
            assert "timeframe_list" in result
            assert result["count"] >= 2  # Should have at least 2 timeframes
            
        except ImportError:
            pytest.skip("config module not available")
    
    def test_available_timeframes_match_config(self, service):
        """Test that available timeframes match config intervals"""
        try:
            import config
            
            # Check that all configured timeframes are in available list
            configured = service.get_configured_timeframes()
            for tf in configured["timeframe_list"]:
                assert tf in service.AVAILABLE_TIMEFRAMES, \
                    f"Configured timeframe {tf} not in available timeframes"
            
        except ImportError:
            pytest.skip("config module not available")
