---
name: realtime-websocket-system
description: Management of real-time market data streams via WebSockets. Use when implementing data listeners, handling stream reconnections, or optimizing message processing concurrency.
---

# Realtime WebSocket System

Low-latency infrastructure for streaming price, orderbook, and trade data.

## Features
- **Auto-Reconnection**: Robust logic to recover from network drops with exponential backoff.
- **Message Dispatching**: Efficient handling of high-frequency data using internal event emitters.
- **Exchange Aggregation**: Unified interface for managing streams from multiple exchanges simultaneously.

## Implementation Pattern
```python
from core.websocket import WSManager

ws_mgr = WSManager()
ws_mgr.subscribe_kline("BTCUSDT", interval="1m", callback=on_kline_update)
```

## Best Practices
- **Minimize Handler Logic**: Keep WebSocket callbacks extremely lightweight to avoid blocking the listener thread.
- **Monitor Latency**: Log any delays in message processing to identify bottlenecks.
- **Handle Heartbeats**: Correctly respond to exchange pings to prevent session timeouts.
- **Resource Cleanup**: Always unsubscribe from streams and close connections on system shutdown.
