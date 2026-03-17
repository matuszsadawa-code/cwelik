"""
Test symbol format conversion in ByBit client.

This test verifies that the symbol format conversion fix works correctly.
"""

import pytest
from data.bybit_client_async import AsyncBybitClient


class TestSymbolFormatConversion:
    """Test symbol format conversion utility methods."""
    
    def test_to_bybit_format_converts_hyphenated_symbols(self):
        """Test that _to_bybit_format() converts hyphenated symbols correctly."""
        client = AsyncBybitClient(use_demo=True)
        
        # Test hyphenated format
        assert client._to_bybit_format("LINK-USDT") == "LINKUSDT"
        assert client._to_bybit_format("BTC-USDT") == "BTCUSDT"
        assert client._to_bybit_format("ETH-USDT") == "ETHUSDT"
        
        # Test already converted format (idempotent)
        assert client._to_bybit_format("LINKUSDT") == "LINKUSDT"
        assert client._to_bybit_format("BTCUSDT") == "BTCUSDT"
        
        # Test edge cases
        assert client._to_bybit_format("") == ""
        assert client._to_bybit_format("MULTI-HYPHEN-SYMBOL") == "MULTIHYPHENSYMBOL"
    
    def test_from_bybit_format_converts_to_internal_format(self):
        """Test that _from_bybit_format() converts to internal format correctly."""
        client = AsyncBybitClient(use_demo=True)
        
        # Test ByBit format
        assert client._from_bybit_format("LINKUSDT") == "LINK-USDT"
        assert client._from_bybit_format("BTCUSDT") == "BTC-USDT"
        assert client._from_bybit_format("ETHUSDT") == "ETH-USDT"
        
        # Test already in internal format (idempotent)
        assert client._from_bybit_format("LINK-USDT") == "LINK-USDT"
        assert client._from_bybit_format("BTC-USDT") == "BTC-USDT"
        
        # Test edge cases
        assert client._from_bybit_format("") == ""
        assert client._from_bybit_format("NOSUFFIX") == "NOSUFFIX"
    
    def test_format_conversion_roundtrip(self):
        """Test that format conversion is reversible."""
        client = AsyncBybitClient(use_demo=True)
        
        internal_symbols = ["LINK-USDT", "BTC-USDT", "ETH-USDT"]
        
        for symbol in internal_symbols:
            # Convert to ByBit format and back
            bybit_format = client._to_bybit_format(symbol)
            back_to_internal = client._from_bybit_format(bybit_format)
            
            assert back_to_internal == symbol, (
                f"Roundtrip failed: {symbol} -> {bybit_format} -> {back_to_internal}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
