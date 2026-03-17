"""
WebSocket connection manager for real-time data broadcasting
"""

import asyncio
import gzip
import json
import logging
from typing import List, Set, Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting
    
    Features:
    - Connection lifecycle management (accept, track, remove)
    - Channel-based subscriptions (market_data, signals, positions, performance)
    - Heartbeat mechanism (ping every 30s, timeout after 60s)
    - Connection status tracking and logging
    - Broadcast to all or specific channels
    - Gzip compression for WebSocket messages (60-80% compression ratio)
    """
    
    def __init__(self, enable_compression: bool = True, compression_level: int = 6, min_compression_size: int = 256):
        """
        Initialize ConnectionManager
        
        Args:
            enable_compression: Enable gzip compression for messages (default: True)
            compression_level: Gzip compression level 1-9 (default: 6, balanced speed/ratio)
            min_compression_size: Minimum message size in bytes to compress (default: 256)
        """
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[WebSocket, Set[str]] = {}
        self.last_heartbeat: Dict[WebSocket, datetime] = {}
        self.connection_metadata: Dict[WebSocket, Dict] = {}
        
        # Compression settings
        self.enable_compression = enable_compression
        self.compression_level = compression_level
        self.min_compression_size = min_compression_size
        
        # Compression statistics
        self.compression_stats = {
            "total_messages": 0,
            "total_uncompressed_bytes": 0,
            "total_compressed_bytes": 0,
            "compression_ratio": 0.0,
            "messages_compressed": 0,
            "messages_uncompressed": 0
        }
        
    async def connect(self, websocket: WebSocket):
        """Accept and track new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = set()
        self.last_heartbeat[websocket] = datetime.now(timezone.utc)
        self.connection_metadata[websocket] = {
            "connected_at": datetime.now(timezone.utc),
            "client_address": websocket.client.host if websocket.client else "unknown"
        }
        logger.info(f"WebSocket connected from {self.connection_metadata[websocket]['client_address']}. Total connections: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection and cleanup"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        if websocket in self.last_heartbeat:
            del self.last_heartbeat[websocket]
        if websocket in self.connection_metadata:
            metadata = self.connection_metadata[websocket]
            duration = (datetime.now(timezone.utc) - metadata["connected_at"]).total_seconds()
            logger.info(f"WebSocket disconnected from {metadata['client_address']} after {duration:.1f}s. Total connections: {len(self.active_connections)}")
            del self.connection_metadata[websocket]

    async def subscribe(self, websocket: WebSocket, channels: List[str]):
        """
        Subscribe connection to specific channels
        
        Supported channels:
        - market_data: Real-time price, volume, orderbook updates
        - signals: New signals and signal status changes
        - positions: Position P&L and status changes
        - performance: Performance metrics updates
        """
        if websocket in self.subscriptions:
            self.subscriptions[websocket].update(channels)
            logger.info(f"WebSocket subscribed to channels: {channels}. Total subscriptions: {self.subscriptions[websocket]}")
            
    async def unsubscribe(self, websocket: WebSocket, channels: List[str]):
        """Unsubscribe connection from specific channels"""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].difference_update(channels)
            logger.info(f"WebSocket unsubscribed from channels: {channels}. Remaining subscriptions: {self.subscriptions[websocket]}")
    
    def _compress_message(self, message: dict) -> tuple[bytes, int, int]:
        """
        Compress JSON message using gzip
        
        Args:
            message: Message dictionary to compress
            
        Returns:
            tuple: (compressed_bytes, uncompressed_size, compressed_size)
        """
        # Serialize to JSON
        json_str = json.dumps(message, separators=(',', ':'))  # Compact JSON
        uncompressed_bytes = json_str.encode('utf-8')
        uncompressed_size = len(uncompressed_bytes)
        
        # Compress with gzip
        compressed_bytes = gzip.compress(uncompressed_bytes, compresslevel=self.compression_level)
        compressed_size = len(compressed_bytes)
        
        return compressed_bytes, uncompressed_size, compressed_size
    
    def _update_compression_stats(self, uncompressed_size: int, compressed_size: int, was_compressed: bool):
        """
        Update compression statistics
        
        Args:
            uncompressed_size: Size of uncompressed message in bytes
            compressed_size: Size of compressed message in bytes
            was_compressed: Whether message was actually compressed
        """
        self.compression_stats["total_messages"] += 1
        self.compression_stats["total_uncompressed_bytes"] += uncompressed_size
        self.compression_stats["total_compressed_bytes"] += compressed_size
        
        if was_compressed:
            self.compression_stats["messages_compressed"] += 1
        else:
            self.compression_stats["messages_uncompressed"] += 1
        
        # Calculate overall compression ratio (percentage saved)
        if self.compression_stats["total_uncompressed_bytes"] > 0:
            ratio = 1.0 - (self.compression_stats["total_compressed_bytes"] / 
                          self.compression_stats["total_uncompressed_bytes"])
            self.compression_stats["compression_ratio"] = round(ratio * 100, 2)
            
    async def broadcast(self, message: dict, channel: str = None):
        """
        Broadcast message to all connected clients or specific channel
        
        Messages are compressed using gzip if compression is enabled and message
        size exceeds min_compression_size threshold. Compression statistics are
        tracked for monitoring.
        
        Args:
            message: Message dictionary to broadcast
            channel: Optional channel filter (broadcasts to all if None)
        """
        import time
        start_time = time.time()
        
        disconnected = []
        
        # Serialize to JSON first to check size
        json_str = json.dumps(message, separators=(',', ':'))  # Compact JSON
        uncompressed_bytes = json_str.encode('utf-8')
        uncompressed_size = len(uncompressed_bytes)
        
        # Decide whether to compress based on size threshold
        should_compress = (self.enable_compression and 
                          uncompressed_size >= self.min_compression_size)
        
        if should_compress:
            try:
                # Compress with gzip
                compressed_bytes = gzip.compress(uncompressed_bytes, compresslevel=self.compression_level)
                compressed_size = len(compressed_bytes)
                
                # Only use compression if it actually reduces size
                if compressed_size < uncompressed_size:
                    # Log compression ratio for this message
                    msg_ratio = (1.0 - (compressed_size / uncompressed_size)) * 100
                    logger.debug(f"Compressed message: {uncompressed_size} -> {compressed_size} bytes ({msg_ratio:.1f}% reduction)")
                    
                    # Update statistics
                    self._update_compression_stats(uncompressed_size, compressed_size, True)
                    
                    # Send compressed binary data
                    for connection in self.active_connections:
                        if channel is None or channel in self.subscriptions.get(connection, set()):
                            try:
                                await connection.send_bytes(compressed_bytes)
                            except Exception as e:
                                logger.error(f"Error broadcasting compressed message to WebSocket: {e}")
                                disconnected.append(connection)
                else:
                    # Compression made it bigger - send uncompressed
                    logger.debug(f"Compression increased size ({uncompressed_size} -> {compressed_size}), sending uncompressed")
                    self._update_compression_stats(uncompressed_size, uncompressed_size, False)
                    
                    for connection in self.active_connections:
                        if channel is None or channel in self.subscriptions.get(connection, set()):
                            try:
                                await connection.send_json(message)
                            except Exception as e:
                                logger.error(f"Error broadcasting to WebSocket: {e}")
                                disconnected.append(connection)
                            
            except Exception as e:
                logger.error(f"Error compressing message: {e}. Falling back to uncompressed.")
                # Fall back to uncompressed
                self._update_compression_stats(uncompressed_size, uncompressed_size, False)
                
                for connection in self.active_connections:
                    if channel is None or channel in self.subscriptions.get(connection, set()):
                        try:
                            await connection.send_json(message)
                        except Exception as e:
                            logger.error(f"Error broadcasting to WebSocket: {e}")
                            disconnected.append(connection)
        else:
            # Message too small or compression disabled - send uncompressed
            self._update_compression_stats(uncompressed_size, uncompressed_size, False)
            
            for connection in self.active_connections:
                if channel is None or channel in self.subscriptions.get(connection, set()):
                    try:
                        await connection.send_json(message)
                    except Exception as e:
                        logger.error(f"Error broadcasting to WebSocket: {e}")
                        disconnected.append(connection)
        
        # Cleanup disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
        
        # Track WebSocket message latency
        latency_ms = (time.time() - start_time) * 1000
        message_type = message.get('type', 'unknown')
        
        try:
            from api.middleware import get_performance_monitor
            monitor = get_performance_monitor()
            monitor.record_websocket_message(message_type, latency_ms)
        except Exception as e:
            logger.debug(f"Could not record WebSocket latency: {e}")
            
    async def send_heartbeat(self, websocket: WebSocket, client_timestamp: Optional[int] = None):
        """
        Send heartbeat pong to specific connection
        
        Args:
            websocket: WebSocket connection
            client_timestamp: Optional timestamp from client ping (for round-trip measurement)
        """
        try:
            response = {
                "type": "pong",
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
            }
            if client_timestamp is not None:
                response["client_timestamp"] = client_timestamp
                
            await websocket.send_json(response)
            self.last_heartbeat[websocket] = datetime.now(timezone.utc)
            logger.debug(f"Sent heartbeat pong to client")
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            self.disconnect(websocket)
            
    def is_connection_alive(self, websocket: WebSocket, timeout_seconds: int = 60) -> bool:
        """
        Check if connection is still alive based on last heartbeat
        
        Args:
            websocket: WebSocket connection to check
            timeout_seconds: Timeout threshold in seconds (default: 60)
            
        Returns:
            bool: True if connection received heartbeat within timeout, False otherwise
        """
        if websocket not in self.last_heartbeat:
            return False
            
        last_beat = self.last_heartbeat[websocket]
        time_since_heartbeat = (datetime.now(timezone.utc) - last_beat).total_seconds()
        
        return time_since_heartbeat < timeout_seconds
    
    def get_current_timestamp(self) -> int:
        """Get current timestamp in milliseconds"""
        return int(datetime.now(timezone.utc).timestamp() * 1000)
    
    def get_connection_status(self, websocket: WebSocket) -> Dict:
        """
        Get detailed status for a specific connection
        
        Returns:
            dict: Connection status including subscriptions, last heartbeat, duration
        """
        if websocket not in self.active_connections:
            return {"status": "disconnected"}
            
        metadata = self.connection_metadata.get(websocket, {})
        last_beat = self.last_heartbeat.get(websocket)
        
        return {
            "status": "connected",
            "connected_at": metadata.get("connected_at").isoformat() if metadata.get("connected_at") else None,
            "client_address": metadata.get("client_address", "unknown"),
            "subscriptions": list(self.subscriptions.get(websocket, set())),
            "last_heartbeat": last_beat.isoformat() if last_beat else None,
            "seconds_since_heartbeat": (datetime.now(timezone.utc) - last_beat).total_seconds() if last_beat else None
        }
            
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
    
    def get_all_connection_statuses(self) -> List[Dict]:
        """
        Get status for all active connections
        
        Returns:
            list: List of connection status dictionaries
        """
        return [self.get_connection_status(ws) for ws in self.active_connections]
    
    def get_channel_subscriber_count(self, channel: str) -> int:
        """
        Get number of connections subscribed to a specific channel
        
        Args:
            channel: Channel name (market_data, signals, positions, performance)
            
        Returns:
            int: Number of subscribers
        """
        count = 0
        for subscriptions in self.subscriptions.values():
            if channel in subscriptions:
                count += 1
        return count
    
    def get_compression_stats(self) -> Dict:
        """
        Get compression statistics
        
        Returns:
            dict: Compression statistics including:
                - total_messages: Total number of messages sent
                - total_uncompressed_bytes: Total uncompressed data size
                - total_compressed_bytes: Total compressed data size
                - compression_ratio: Overall compression ratio (percentage saved)
                - messages_compressed: Number of messages sent compressed
                - messages_uncompressed: Number of messages sent uncompressed
                - compression_enabled: Whether compression is enabled
                - compression_level: Gzip compression level (1-9)
                - min_compression_size: Minimum message size to compress (bytes)
        """
        return {
            **self.compression_stats,
            "compression_enabled": self.enable_compression,
            "compression_level": self.compression_level,
            "min_compression_size": self.min_compression_size
        }
    
    def reset_compression_stats(self):
        """Reset compression statistics to zero"""
        self.compression_stats = {
            "total_messages": 0,
            "total_uncompressed_bytes": 0,
            "total_compressed_bytes": 0,
            "compression_ratio": 0.0,
            "messages_compressed": 0,
            "messages_uncompressed": 0
        }
        logger.info("Compression statistics reset")
