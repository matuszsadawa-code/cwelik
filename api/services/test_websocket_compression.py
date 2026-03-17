"""
Unit tests for WebSocket message compression
"""

import pytest
import gzip
import json
from unittest.mock import AsyncMock, Mock, patch
from api.services.websocket_manager import ConnectionManager


class TestWebSocketCompression:
    """Test WebSocket message compression functionality"""
    
    def test_compression_initialization(self):
        """Test that compression is enabled by default with correct settings"""
        manager = ConnectionManager()
        
        assert manager.enable_compression is True
        assert manager.compression_level == 6
        assert manager.min_compression_size == 256
        assert manager.compression_stats["total_messages"] == 0
        assert manager.compression_stats["compression_ratio"] == 0.0
    
    def test_compression_disabled_initialization(self):
        """Test initialization with compression disabled"""
        manager = ConnectionManager(enable_compression=False)
        
        assert manager.enable_compression is False
        assert manager.compression_stats["total_messages"] == 0
    
    def test_custom_compression_level(self):
        """Test initialization with custom compression level"""
        manager = ConnectionManager(compression_level=9)
        
        assert manager.compression_level == 9
    
    def test_compress_message(self):
        """Test message compression produces valid gzip data"""
        manager = ConnectionManager(min_compression_size=0)  # Compress all messages
        
        # Create a message large enough to compress well
        message = {
            "type": "market_data_update",
            "data": {
                "symbols": [
                    {"symbol": f"SYMBOL{i}", "price": 45000.50, "volume": 1234567.89}
                    for i in range(10)
                ]
            }
        }
        
        compressed_bytes, uncompressed_size, compressed_size = manager._compress_message(message)
        
        # Verify compression occurred
        assert compressed_size < uncompressed_size
        assert compressed_size > 0
        assert uncompressed_size > 0
        
        # Verify data can be decompressed
        decompressed_bytes = gzip.decompress(compressed_bytes)
        decompressed_message = json.loads(decompressed_bytes.decode('utf-8'))
        
        assert decompressed_message == message
    
    def test_compression_ratio_calculation(self):
        """Test compression ratio calculation for typical trading data"""
        manager = ConnectionManager(min_compression_size=0)  # Compress all messages
        
        # Large message with repetitive data (should compress well)
        message = {
            "type": "market_data_update",
            "data": {
                "symbols": [
                    {"symbol": f"BTC{i}USDT", "price": 45000.0, "volume": 1000000.0}
                    for i in range(50)
                ]
            }
        }
        
        compressed_bytes, uncompressed_size, compressed_size = manager._compress_message(message)
        
        # Calculate compression ratio
        ratio = (1.0 - (compressed_size / uncompressed_size)) * 100
        
        # Should achieve 60-90% compression for repetitive data
        assert ratio >= 60.0, f"Compression ratio {ratio:.1f}% is below target 60%"
        assert ratio <= 95.0, f"Compression ratio {ratio:.1f}% seems unrealistic"
        
        print(f"Compression ratio: {ratio:.1f}% (uncompressed: {uncompressed_size}, compressed: {compressed_size})")
    
    def test_update_compression_stats(self):
        """Test compression statistics tracking"""
        manager = ConnectionManager()
        
        # Simulate sending 3 messages
        manager._update_compression_stats(1000, 400, True)  # 60% compression
        manager._update_compression_stats(2000, 800, True)  # 60% compression
        manager._update_compression_stats(500, 500, False)  # No compression
        
        stats = manager.compression_stats
        
        assert stats["total_messages"] == 3
        assert stats["total_uncompressed_bytes"] == 3500
        assert stats["total_compressed_bytes"] == 1700
        assert stats["messages_compressed"] == 2
        assert stats["messages_uncompressed"] == 1
        
        # Overall compression ratio should be ~51.4%
        expected_ratio = (1.0 - (1700 / 3500)) * 100
        assert abs(stats["compression_ratio"] - expected_ratio) < 0.1
    
    @pytest.mark.asyncio
    async def test_broadcast_with_compression(self):
        """Test broadcasting compressed messages to WebSocket clients"""
        manager = ConnectionManager(enable_compression=True, min_compression_size=0)  # Compress all
        
        # Create mock WebSocket connections
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        
        # Add connections
        await manager.connect(mock_ws1)
        await manager.connect(mock_ws2)
        
        # Subscribe to channel
        await manager.subscribe(mock_ws1, ["market_data"])
        await manager.subscribe(mock_ws2, ["market_data"])
        
        # Broadcast large message that will compress well
        message = {
            "type": "market_data_update",
            "data": {
                "symbols": [
                    {"symbol": f"SYMBOL{i}", "price": 45000.0, "volume": 1000000.0}
                    for i in range(20)
                ]
            }
        }
        
        await manager.broadcast(message, channel="market_data")
        
        # Verify send_bytes was called (compressed data)
        assert mock_ws1.send_bytes.called
        assert mock_ws2.send_bytes.called
        
        # Verify compression stats updated
        stats = manager.get_compression_stats()
        assert stats["total_messages"] == 1
        assert stats["messages_compressed"] == 1
        assert stats["total_compressed_bytes"] > 0
        assert stats["compression_ratio"] > 0
    
    @pytest.mark.asyncio
    async def test_broadcast_without_compression(self):
        """Test broadcasting uncompressed messages when compression is disabled"""
        manager = ConnectionManager(enable_compression=False)
        
        # Create mock WebSocket connection
        mock_ws = AsyncMock()
        
        # Add connection
        await manager.connect(mock_ws)
        await manager.subscribe(mock_ws, ["signals"])
        
        # Broadcast message
        message = {
            "type": "signal_update",
            "data": {"signal_id": "123", "status": "ACTIVE"}
        }
        
        await manager.broadcast(message, channel="signals")
        
        # Verify send_json was called (uncompressed)
        assert mock_ws.send_json.called
        assert not mock_ws.send_bytes.called
        
        # Verify stats show no compression
        stats = manager.get_compression_stats()
        assert stats["messages_uncompressed"] == 1
        assert stats["messages_compressed"] == 0
    
    @pytest.mark.asyncio
    async def test_compression_fallback_on_error(self):
        """Test fallback to uncompressed when compression fails"""
        manager = ConnectionManager(enable_compression=True)
        
        mock_ws = AsyncMock()
        await manager.connect(mock_ws)
        
        # Patch _compress_message to raise exception
        with patch.object(manager, '_compress_message', side_effect=Exception("Compression error")):
            message = {"type": "test", "data": {}}
            await manager.broadcast(message)
        
        # Should fall back to send_json
        assert mock_ws.send_json.called
    
    def test_get_compression_stats(self):
        """Test retrieving compression statistics"""
        manager = ConnectionManager(enable_compression=True, compression_level=9, min_compression_size=512)
        
        # Simulate some activity
        manager._update_compression_stats(1000, 300, True)
        
        stats = manager.get_compression_stats()
        
        assert "total_messages" in stats
        assert "compression_ratio" in stats
        assert "compression_enabled" in stats
        assert "compression_level" in stats
        assert "min_compression_size" in stats
        assert stats["compression_enabled"] is True
        assert stats["compression_level"] == 9
        assert stats["min_compression_size"] == 512
        assert stats["total_messages"] == 1
    
    def test_reset_compression_stats(self):
        """Test resetting compression statistics"""
        manager = ConnectionManager()
        
        # Add some stats
        manager._update_compression_stats(1000, 400, True)
        assert manager.compression_stats["total_messages"] == 1
        
        # Reset
        manager.reset_compression_stats()
        
        # Verify all stats are zero
        assert manager.compression_stats["total_messages"] == 0
        assert manager.compression_stats["total_uncompressed_bytes"] == 0
        assert manager.compression_stats["total_compressed_bytes"] == 0
        assert manager.compression_stats["compression_ratio"] == 0.0
        assert manager.compression_stats["messages_compressed"] == 0
        assert manager.compression_stats["messages_uncompressed"] == 0
    
    def test_compression_with_large_payload(self):
        """Test compression with large realistic trading data payload"""
        manager = ConnectionManager(min_compression_size=0)  # Compress all
        
        # Simulate large market data update with 100 symbols
        message = {
            "type": "market_data_update",
            "data": {
                "timestamp": 1234567890,
                "symbols": [
                    {
                        "symbol": f"SYMBOL{i}USDT",
                        "price": 100.0 + i * 0.5,
                        "volume24h": 1000000.0 + i * 10000,
                        "change24h": 2.5 + i * 0.1,
                        "bidAskSpread": 0.01,
                        "cvd": 50000.0 + i * 100,
                        "orderbook": {
                            "bids": [[100.0 + j * 0.01, 1000.0] for j in range(20)],
                            "asks": [[100.1 + j * 0.01, 1000.0] for j in range(20)]
                        }
                    }
                    for i in range(100)
                ]
            }
        }
        
        compressed_bytes, uncompressed_size, compressed_size = manager._compress_message(message)
        
        ratio = (1.0 - (compressed_size / uncompressed_size)) * 100
        
        # Large payloads should compress well (target 60-80%)
        assert ratio >= 60.0, f"Large payload compression {ratio:.1f}% below 60% target"
        
        print(f"Large payload: {uncompressed_size} -> {compressed_size} bytes ({ratio:.1f}% reduction)")
    
    def test_compression_with_small_payload(self):
        """Test that small messages are not compressed due to size threshold"""
        manager = ConnectionManager(min_compression_size=256)  # Default threshold
        
        # Small message below threshold
        message = {"type": "ping", "timestamp": 1234567890}
        
        # Verify message size is below threshold
        json_str = json.dumps(message, separators=(',', ':'))
        message_size = len(json_str.encode('utf-8'))
        assert message_size < 256, "Test message should be below compression threshold"
        
        # The _compress_message method still works, but broadcast() won't use it
        compressed_bytes, uncompressed_size, compressed_size = manager._compress_message(message)
        
        # Verify decompression works
        decompressed = json.loads(gzip.decompress(compressed_bytes).decode('utf-8'))
        assert decompressed == message
    
    @pytest.mark.asyncio
    async def test_small_message_not_compressed(self):
        """Test that small messages below threshold are sent uncompressed"""
        manager = ConnectionManager(enable_compression=True, min_compression_size=256)
        
        mock_ws = AsyncMock()
        await manager.connect(mock_ws)
        
        # Small message
        message = {"type": "ping", "timestamp": 1234567890}
        
        await manager.broadcast(message)
        
        # Should use send_json (uncompressed) not send_bytes
        assert mock_ws.send_json.called
        assert not mock_ws.send_bytes.called
        
        # Stats should show uncompressed
        stats = manager.get_compression_stats()
        assert stats["messages_uncompressed"] == 1
        assert stats["messages_compressed"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
