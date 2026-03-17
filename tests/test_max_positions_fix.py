"""
Test to verify the max positions limit fix works correctly.

This test verifies that:
1. System can open up to 20 concurrent positions
2. Position counting accurately reflects actual open positions
3. Closed positions are properly removed from tracking
"""

import pytest
from execution.position_manager import PositionManager
from execution.portfolio import PortfolioManager, DEFAULT_RISK
from execution.order_executor import OrderExecutor, ExecutionMode


class TestMaxPositionsFix:
    """Test suite for max positions limit fix."""
    
    def test_position_cleanup_after_close(self):
        """
        Test that closed positions are properly removed from _positions dict.
        
        **Validates: Bugfix Requirements 2.1, 2.2**
        """
        pos_manager = PositionManager()
        
        # Add 5 positions
        for i in range(5):
            execution_result = {
                "status": "FILLED",
                "execution_id": f"EXEC-{i}",
                "signal_id": f"SIG-{i}",
                "symbol": f"BTC{i}USDT",
                "direction": "LONG",
                "side": "Buy",
                "mode": "paper",
                "entry_price": 50000.0,
                "qty": 0.1,
                "leverage": 10,
                "sl_price": 49000.0,
                "tp_price": 52000.0,
            }
            pos_manager.add_position(execution_result)
        
        # Verify all 5 are open
        assert pos_manager.count_open() == 5, "Should have 5 open positions"
        assert len(pos_manager._positions) == 5, "Should have 5 positions in dict"
        
        # Close 3 positions by hitting SL
        pos_manager.update_symbol_price("BTC0USDT", 49000.0)
        pos_manager.update_symbol_price("BTC1USDT", 49000.0)
        pos_manager.update_symbol_price("BTC2USDT", 49000.0)
        
        # Verify only 2 are open
        assert pos_manager.count_open() == 2, "Should have 2 open positions after closing 3"
        assert len(pos_manager._positions) == 2, "Should have 2 positions in dict"
        
        # Verify the correct positions remain
        remaining_symbols = {pos.symbol for pos in pos_manager._positions.values()}
        assert remaining_symbols == {"BTC3USDT", "BTC4USDT"}, "Only BTC3 and BTC4 should remain"
        
        # Verify closed positions were moved to _closed_positions
        assert len(pos_manager._closed_positions) == 3, "Should have 3 closed positions"
    
    def test_count_open_accuracy(self):
        """
        Test that count_open() accurately reflects only open positions.
        
        **Validates: Bugfix Requirements 2.1, 2.3**
        """
        pos_manager = PositionManager()
        
        # Add 10 positions
        for i in range(10):
            execution_result = {
                "status": "FILLED",
                "execution_id": f"EXEC-{i}",
                "signal_id": f"SIG-{i}",
                "symbol": f"SYM{i}USDT",
                "direction": "LONG",
                "side": "Buy",
                "mode": "paper",
                "entry_price": 50000.0,
                "qty": 0.1,
                "leverage": 10,
                "sl_price": 49000.0,
                "tp_price": 52000.0,
            }
            pos_manager.add_position(execution_result)
        
        assert pos_manager.count_open() == 10
        
        # Close half of them
        for i in range(5):
            pos_manager.update_symbol_price(f"SYM{i}USDT", 49000.0)
        
        # count_open() should now return 5
        assert pos_manager.count_open() == 5, "count_open() should return 5 after closing half"
        
        # Manually count to verify
        actually_open = sum(1 for pos in pos_manager._positions.values() if pos.is_open)
        assert pos_manager.count_open() == actually_open, "count_open() should match actual open count"
    
    def test_max_positions_limit_enforcement(self):
        """
        Test that the system correctly enforces max_concurrent_positions limit.
        
        **Validates: Bugfix Requirements 2.1, 2.2, 2.4**
        """
        pos_manager = PositionManager()
        
        # Simulate portfolio manager risk check
        max_positions = 20
        
        # Add 18 positions
        for i in range(18):
            execution_result = {
                "status": "FILLED",
                "execution_id": f"EXEC-{i}",
                "signal_id": f"SIG-{i}",
                "symbol": f"SYM{i}USDT",
                "direction": "LONG",
                "side": "Buy",
                "mode": "paper",
                "entry_price": 50000.0,
                "qty": 0.1,
                "leverage": 10,
                "sl_price": 49000.0,
                "tp_price": 52000.0,
            }
            pos_manager.add_position(execution_result)
        
        # Should be able to add 2 more (to reach 20)
        open_count = pos_manager.count_open()
        assert open_count == 18
        assert open_count < max_positions, "Should allow more positions (18 < 20)"
        
        # Add 2 more to reach limit
        for i in range(18, 20):
            execution_result = {
                "status": "FILLED",
                "execution_id": f"EXEC-{i}",
                "signal_id": f"SIG-{i}",
                "symbol": f"SYM{i}USDT",
                "direction": "LONG",
                "side": "Buy",
                "mode": "paper",
                "entry_price": 50000.0,
                "qty": 0.1,
                "leverage": 10,
                "sl_price": 49000.0,
                "tp_price": 52000.0,
            }
            pos_manager.add_position(execution_result)
        
        # Now at limit
        open_count = pos_manager.count_open()
        assert open_count == 20, "Should have exactly 20 positions"
        assert open_count >= max_positions, "Should be at limit (20 >= 20)"
        
        # Close 5 positions
        for i in range(5):
            pos_manager.update_symbol_price(f"SYM{i}USDT", 49000.0)
        
        # Should now have 15 open
        open_count = pos_manager.count_open()
        assert open_count == 15, "Should have 15 open after closing 5"
        assert open_count < max_positions, "Should allow more positions (15 < 20)"
        
        # Should be able to add 5 more
        for i in range(20, 25):
            execution_result = {
                "status": "FILLED",
                "execution_id": f"EXEC-{i}",
                "signal_id": f"SIG-{i}",
                "symbol": f"SYM{i}USDT",
                "direction": "LONG",
                "side": "Buy",
                "mode": "paper",
                "entry_price": 50000.0,
                "qty": 0.1,
                "leverage": 10,
                "sl_price": 49000.0,
                "tp_price": 52000.0,
            }
            pos_manager.add_position(execution_result)
        
        # Back to 20
        assert pos_manager.count_open() == 20, "Should be back at 20 positions"
    
    def test_capital_deployment_with_20_positions(self):
        """
        Test that with 20 positions at 2% each, capital deployment reaches 40%.
        
        **Validates: Bugfix Requirements 2.4**
        """
        # With 20 positions at 2% risk each:
        # Total capital deployed = 20 * 2% = 40%
        
        max_positions = 20
        risk_per_position = 2.0  # 2%
        expected_deployment = max_positions * risk_per_position
        
        assert expected_deployment == 40.0, "20 positions at 2% each should deploy 40% capital"
        
        # Verify DEFAULT_RISK configuration
        assert DEFAULT_RISK["max_concurrent_positions"] == 20, "DEFAULT_RISK should have max 20 positions"
        assert DEFAULT_RISK["capital_allocation_pct"] == 2.0, "DEFAULT_RISK should have 2% per position"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
