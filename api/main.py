"""
OpenClaw Trading Dashboard API - Main Application

FastAPI backend providing REST endpoints and WebSocket connections
for real-time market monitoring, performance analytics, and configuration management.
"""

import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import json

from api.services.websocket_manager import ConnectionManager
from api.services.market_data_service import MarketDataService
from api.services.market_regime_service import MarketRegimeService
from api.services.liquidity_zones_service import LiquidityZonesService
from api.services.position_service import PositionService
from api.services.system_health_service import SystemHealthService
from api.services.alert_service import AlertService
from api.utils.database import get_database
from api.utils.services import set_position_service
from api.utils.sentry_config import init_sentry
from api.routes import auth_router, market_router, signals_router, positions_router, analytics_router, config_router, trades_router
from api.routes import performance
from api.routes.backtest import router as backtest_router
from api.routes.experiments import router as experiments_router
from api.routes.export import router as export_router
from api.routes.health import router as health_router
from api.auth import verify_websocket_token
from api.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from data.candle_manager_async import AsyncCandleManager

# Initialize Sentry error tracking (must be done before other imports)
init_sentry()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global connection manager
manager = ConnectionManager()

# Global services
market_data_service = None
market_regime_service = None
liquidity_zones_service = None
position_service = None
system_health_service = None
alert_service = None
candle_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    
    Handles startup and shutdown events
    """
    global market_data_service, market_regime_service, liquidity_zones_service, position_service, system_health_service, alert_service, candle_manager
    
    # Startup
    logger.info("Starting OpenClaw Trading Dashboard API...")
    
    # Initialize database connection
    db = get_database()
    logger.info("Database connection initialized")
    
    # Initialize alert service
    from api.services.alert_service import AlertService
    alert_service = AlertService(db=db, websocket_manager=manager)
    logger.info("Alert service initialized")
    
    # Initialize configuration services
    from api.routes.config import init_config_services
    init_config_services()
    logger.info("Configuration services initialized")
    
    # Initialize trade journal service
    from api.routes.trades import init_trade_journal_service
    init_trade_journal_service()
    logger.info("Trade journal service initialized")
    
    # Initialize backtest service
    from api.routes.backtest import backtest_service
    logger.info("Backtest service initialized")
    
    # Initialize A/B testing service
    from api.routes.experiments import init_ab_testing_service
    init_ab_testing_service()
    logger.info("A/B testing service initialized")
    
    # Initialize report service
    from api.routes.export import init_report_service
    init_report_service()
    logger.info("Report service initialized")
    
    # Initialize analytics services
    from api.routes.analytics import init_analytics_services
    init_analytics_services()
    logger.info("Analytics services initialized")
    
    # Initialize candle manager for regime service
    from data.bybit_client_async import AsyncBybitClient
    from data.binance_client_async import AsyncBinanceClient
    bybit_client = AsyncBybitClient()
    binance_client = AsyncBinanceClient()
    candle_manager = AsyncCandleManager(bybit_client, binance_client, db)
    logger.info("Candle manager initialized")
    
    # Initialize performance monitoring
    from api.middleware import get_performance_monitor
    from api.utils.query_timer import get_query_timer
    perf_monitor = get_performance_monitor()
    query_timer = get_query_timer()
    query_timer.set_performance_monitor(perf_monitor)
    logger.info("Performance monitoring initialized")
    
    # Initialize and start system health service
    system_health_service = SystemHealthService(manager, db)
    await system_health_service.start()
    logger.info("System health service started")
    
    # Initialize and start market data service
    market_data_service = MarketDataService(manager)
    await market_data_service.start()
    logger.info("Market data service started")
    
    # Initialize and start market regime service
    market_regime_service = MarketRegimeService(manager, candle_manager)
    await market_regime_service.start()
    logger.info("Market regime service started")
    
    # Initialize and start liquidity zones service
    liquidity_zones_service = LiquidityZonesService(candle_manager)
    await liquidity_zones_service.start()
    logger.info("Liquidity zones service started")
    
    # Initialize and start position service
    position_service = PositionService(manager, market_data_service, db)
    await position_service.start()
    set_position_service(position_service)
    logger.info("Position service started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down OpenClaw Trading Dashboard API...")
    
    # Stop position service
    if position_service:
        await position_service.stop()
        logger.info("Position service stopped")
    
    # Stop liquidity zones service
    if liquidity_zones_service:
        await liquidity_zones_service.stop()
        logger.info("Liquidity zones service stopped")
    
    # Stop market regime service
    if market_regime_service:
        await market_regime_service.stop()
        logger.info("Market regime service stopped")
    
    # Stop market data service
    if market_data_service:
        await market_data_service.stop()
        logger.info("Market data service stopped")
    
    # Stop system health service
    if system_health_service:
        await system_health_service.stop()
        logger.info("System health service stopped")
    
    # Close candle manager and exchange clients
    if candle_manager:
        await candle_manager.close()
        logger.info("Candle manager closed")


# Create FastAPI application
app = FastAPI(
    title="OpenClaw Trading Dashboard API",
    description="Real-time market monitoring and performance analytics for OpenClaw v3.0",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security headers middleware
# Must be added early to ensure all responses include security headers
app.add_middleware(SecurityHeadersMiddleware)

# Add performance monitoring middleware
# Must be added before rate limiting to track all requests including rate-limited ones
from api.middleware import PerformanceMonitorMiddleware, get_performance_monitor
app.add_middleware(PerformanceMonitorMiddleware)

# Add rate limiting middleware
# Must be added after CORS to ensure rate limit headers are included in CORS responses
app.add_middleware(RateLimitMiddleware)

# Register API routers
app.include_router(auth_router)
app.include_router(market_router)
app.include_router(signals_router)
app.include_router(positions_router)
app.include_router(analytics_router)
app.include_router(config_router)
app.include_router(trades_router)
app.include_router(backtest_router)
app.include_router(experiments_router)
app.include_router(export_router)
app.include_router(health_router)
app.include_router(performance.router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "OpenClaw Trading Dashboard API",
        "version": "1.0.0"
    }


@app.get("/api/health")
async def health_check():
    """
    System health check
    
    Returns:
        dict: System health metrics including:
            - status: Overall system status
            - websocket_connections: Number of active WebSocket connections
            - database: Database health metrics (status, query performance, WAL mode)
            - market_data_service: Market data service status
            - market_regime_service: Market regime service status
            - position_service: Position service status
            - system_health: Real-time system health metrics (API success rates, response times, etc.)
    """
    from api.database import get_health_check
    
    db_health = get_health_check()
    
    # Get market data service status
    market_data_status = None
    if market_data_service:
        market_data_status = market_data_service.get_service_status()
    
    # Get market regime service status
    market_regime_status = None
    if market_regime_service:
        market_regime_status = market_regime_service.get_service_status()
    
    # Get liquidity zones service status
    liquidity_zones_status = None
    if liquidity_zones_service:
        liquidity_zones_status = liquidity_zones_service.get_service_status()
    
    # Get position service status
    position_service_status = None
    if position_service:
        position_service_status = position_service.get_service_status()
    
    # Get system health metrics
    system_health_metrics = None
    if system_health_service:
        system_health_metrics = system_health_service.get_cached_health()
    
    # Determine overall status based on database health
    overall_status = "healthy"
    if db_health.get("status") == "degraded":
        overall_status = "degraded"
    elif db_health.get("status") == "error":
        overall_status = "error"
    
    return {
        "status": overall_status,
        "websocket_connections": manager.get_connection_count(),
        "websocket_compression": manager.get_compression_stats(),
        "database": db_health,
        "market_data_service": market_data_status,
        "market_regime_service": market_regime_status,
        "liquidity_zones_service": liquidity_zones_status,
        "position_service": position_service_status,
        "system_health": system_health_metrics
    }


@app.get("/api/market/data")
async def get_market_data(symbol: str = None):
    """
    Get current market data for one or all symbols
    
    Args:
        symbol: Optional symbol filter (e.g., BTCUSDT)
        
    Returns:
        dict: Market data for requested symbol(s)
    """
    if not market_data_service:
        return {"error": "Market data service not initialized"}
    
    if symbol:
        data = market_data_service.get_market_data(symbol)
        if not data:
            return {"error": f"No data available for {symbol}"}
        return data
    else:
        return market_data_service.get_all_market_data()


@app.get("/api/market/cvd/{symbol}")
async def get_cvd(symbol: str):
    """
    Get current CVD (Cumulative Volume Delta) for a symbol
    
    Args:
        symbol: Trading pair symbol (e.g., BTCUSDT)
        
    Returns:
        dict: CVD value and symbol
    """
    if not market_data_service:
        return {"error": "Market data service not initialized"}
    
    cvd = market_data_service.get_cvd(symbol)
    return {
        "symbol": symbol,
        "cvd": cvd
    }


@app.post("/api/market/cvd/{symbol}/reset")
async def reset_cvd(symbol: str):
    """
    Reset CVD for a symbol to zero
    
    Args:
        symbol: Trading pair symbol (e.g., BTCUSDT)
        
    Returns:
        dict: Success message
    """
    if not market_data_service:
        return {"error": "Market data service not initialized"}
    
    market_data_service.reset_cvd(symbol)
    return {
        "status": "success",
        "message": f"CVD reset for {symbol}"
    }


@app.get("/api/market/regime")
async def get_market_regime(symbol: str = None):
    """
    Get current market regime for one or all symbols
    
    Args:
        symbol: Optional symbol filter (e.g., BTCUSDT)
        
    Returns:
        dict: Market regime data including:
            - regime: TRENDING, RANGING, VOLATILE, or QUIET
            - confidence: Confidence score (0-100%)
            - volatilityPercentile: Volatility percentile (0-100%)
            - trendStrength: ADX trend strength indicator
            - timestamp: Unix timestamp in milliseconds
    """
    if not market_regime_service:
        return {"error": "Market regime service not initialized"}
    
    if symbol:
        regime = market_regime_service.get_regime(symbol)
        if not regime:
            return {"error": f"No regime data available for {symbol}"}
        return regime
    else:
        return market_regime_service.get_all_regimes()


@app.get("/api/market/{symbol}/liquidity-zones")
async def get_liquidity_zones(symbol: str):
    """
    Get liquidity zones for a symbol
    
    Identifies liquidity zones from:
    - Order book imbalances (large resting orders)
    - Historical volume profile (high-volume price levels)
    
    Args:
        symbol: Trading pair symbol (e.g., BTCUSDT)
        
    Returns:
        dict: Liquidity zones data including:
            - symbol: Trading pair symbol
            - zones: List of liquidity zones, each containing:
                - priceLevel: Central price of the zone
                - priceRangeLow: Lower bound of the zone
                - priceRangeHigh: Upper bound of the zone
                - type: "support" (below price) or "resistance" (above price)
                - strength: "high", "medium", or "low"
                - liquidityAmount: Estimated liquidity amount
                - source: "orderbook", "volume_profile", or "combined"
                - isNearPrice: True if price is within 0.5% of zone
                - label: Optional label (e.g., "POC", "VAH", "VAL")
                - timestamp: Unix timestamp in milliseconds
    """
    if not liquidity_zones_service:
        return {"error": "Liquidity zones service not initialized"}
    
    zones = await liquidity_zones_service.get_liquidity_zones(symbol)
    
    return {
        "symbol": symbol,
        "zones": zones,
        "count": len(zones)
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time bidirectional communication
    
    Authentication:
    - Token can be provided in query parameter: /ws?token=<jwt_token>
    - Or in the first message: {"type": "auth", "token": "<jwt_token>"}
    
    Supported client message types:
    - {"type": "auth", "token": "<jwt_token>"}
    - {"type": "subscribe", "channels": ["market_data", "signals", "positions", "performance"]}
    - {"type": "unsubscribe", "channels": ["market_data"]}
    - {"type": "ping", "timestamp": 1234567890}
    
    Server message types:
    - {"type": "pong", "timestamp": 1234567890}
    - {"type": "market_data_update", "data": {...}}
    - {"type": "signal_update", "data": {...}}
    - {"type": "position_update", "data": {...}}
    - {"type": "performance_update", "data": {...}}
    """
    # Check for token in query parameters
    token = websocket.query_params.get("token")
    user = None
    
    if token:
        user = verify_websocket_token(token)
        if not user:
            await websocket.close(code=1008, reason="Invalid authentication token")
            logger.warning("WebSocket connection rejected: Invalid token in query params")
            return
    
    # Accept connection (authentication may happen in first message if not in query params)
    await manager.connect(websocket)
    
    # If not authenticated via query params, require auth message
    if not user:
        try:
            # Wait for auth message (timeout after 10 seconds)
            data = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
            message = json.loads(data)
            
            if message.get("type") != "auth":
                await websocket.close(code=1008, reason="Authentication required")
                manager.disconnect(websocket)
                logger.warning("WebSocket connection rejected: No auth message")
                return
            
            token = message.get("token")
            if not token:
                await websocket.close(code=1008, reason="Token required")
                manager.disconnect(websocket)
                logger.warning("WebSocket connection rejected: No token provided")
                return
            
            user = verify_websocket_token(token)
            if not user:
                await websocket.close(code=1008, reason="Invalid authentication token")
                manager.disconnect(websocket)
                logger.warning("WebSocket connection rejected: Invalid token in auth message")
                return
            
            # Send auth success message
            await websocket.send_json({
                "type": "auth_success",
                "user_id": user.user_id,
                "username": user.username,
                "role": user.role
            })
            logger.info(f"WebSocket authenticated: {user.username} (role: {user.role})")
            
        except asyncio.TimeoutError:
            await websocket.close(code=1008, reason="Authentication timeout")
            manager.disconnect(websocket)
            logger.warning("WebSocket connection rejected: Authentication timeout")
            return
        except json.JSONDecodeError:
            await websocket.close(code=1008, reason="Invalid JSON")
            manager.disconnect(websocket)
            logger.warning("WebSocket connection rejected: Invalid JSON in auth message")
            return
        except Exception as e:
            await websocket.close(code=1011, reason="Authentication error")
            manager.disconnect(websocket)
            logger.error(f"WebSocket authentication error: {e}")
            return
    else:
        # Already authenticated via query params
        await websocket.send_json({
            "type": "auth_success",
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role
        })
        logger.info(f"WebSocket authenticated: {user.username} (role: {user.role})")
    
    try:
        # Start heartbeat monitoring task
        heartbeat_task = asyncio.create_task(monitor_heartbeat(websocket))
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "ping":
                    # Respond to ping with pong
                    await manager.send_heartbeat(websocket, message.get("timestamp"))
                    logger.debug(f"Received ping from client, sent pong")
                    
                elif message_type == "subscribe":
                    # Subscribe to channels
                    channels = message.get("channels", [])
                    await manager.subscribe(websocket, channels)
                    await websocket.send_json({
                        "type": "subscribed",
                        "channels": channels
                    })
                    logger.info(f"Client subscribed to channels: {channels}")
                    
                elif message_type == "unsubscribe":
                    # Unsubscribe from channels
                    channels = message.get("channels", [])
                    await manager.unsubscribe(websocket, channels)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "channels": channels
                    })
                    logger.info(f"Client unsubscribed from channels: {channels}")
                    
                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    })
                    
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {data}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                
    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {user.username if user else 'unknown'}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Cancel heartbeat task
        if 'heartbeat_task' in locals():
            heartbeat_task.cancel()
        manager.disconnect(websocket)


async def monitor_heartbeat(websocket: WebSocket):
    """
    Monitor heartbeat and send periodic pings
    
    - Sends ping every 30 seconds
    - Disconnects if no response for 60 seconds
    """
    try:
        while True:
            # Wait 30 seconds
            await asyncio.sleep(30)
            
            # Check if connection is still alive
            if not manager.is_connection_alive(websocket, timeout_seconds=60):
                logger.warning("Connection timeout - no heartbeat for 60 seconds")
                await websocket.close(code=1000, reason="Heartbeat timeout")
                break
            
            # Send server-initiated ping
            try:
                await websocket.send_json({
                    "type": "ping",
                    "timestamp": manager.get_current_timestamp()
                })
                logger.debug("Sent ping to client")
            except Exception as e:
                logger.error(f"Error sending ping: {e}")
                break
                
    except asyncio.CancelledError:
        logger.debug("Heartbeat monitor cancelled")
    except Exception as e:
        logger.error(f"Heartbeat monitor error: {e}")


def get_alert_service() -> AlertService:
    """
    Get the global alert service instance.
    
    Returns:
        AlertService: The alert service instance
        
    Raises:
        RuntimeError: If alert service is not initialized
    """
    if alert_service is None:
        raise RuntimeError("Alert service not initialized")
    return alert_service

