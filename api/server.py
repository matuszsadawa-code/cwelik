"""
Legacy API server - maintained for backward compatibility
Use api.main for new dashboard implementation
"""

import asyncio
import json
from typing import Dict, List, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# Import new connection manager
from api.services.websocket_manager import ConnectionManager

# Global app instance
app = FastAPI(title="OpenClaw Dashboard API", version="2.0")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use new connection manager
manager = ConnectionManager()

# Global state to share between main_async and this API
class AppState:
    def __init__(self):
        self.system_instance = None
        self.db = None
        self.running = True

state = AppState()

@app.get("/")
def read_root():
    return {"status": "OpenClaw Dashboard API is running"}

@app.get("/api/summary")
def get_summary():
    """Get high-level system summary"""
    if not state.system_instance:
        return {"error": "System not initialized"}
    
    # Extract performance from DB if tracker not fully active
    db = state.db
    if not db:
        return {"error": "DB not initialized"}
        
    try:
        if hasattr(state.system_instance, 'tracker') and hasattr(state.system_instance.tracker, 'get_statistics'):
            stats = state.system_instance.tracker.get_statistics()
        else:
            stats = {"total_trades": 0, "win_rate": 0, "total_pnl": 0}
            
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "performance": stats,
            "active_trades": state.system_instance.pos_manager.get_active_positions() if hasattr(state.system_instance, 'pos_manager') else [],
            "status": "Running" if state.running else "Stopped"
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/trades")
def get_recent_trades(limit: int = 50):
    """Get historical trades from DB"""
    try:
        if state.db and hasattr(state.db, 'get_executions'):
            # The database.py likely has a get_executions or similar. 
            # Needs adaptation to the specific DB schema used.
            trades = state.db.get_executions(limit=limit) if hasattr(state.db, 'get_executions') else []
            return trades
        return []
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/control/toggle")
def toggle_trading():
    state.running = not state.running
    return {"status": "success", "running": state.running}

@app.get("/dashboard")
def get_dashboard():
    """Render interactive HTML dashboard"""
    try:
        if not state.db:
            return {"error": "Database not initialized"}
        
        from dashboard.performance_dashboard import PerformanceDashboard
        dashboard = PerformanceDashboard(state.db)
        html = dashboard.render_dashboard()
        
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html)
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/dashboard/metrics")
def get_dashboard_metrics():
    """Get real-time dashboard metrics (for WebSocket updates)"""
    try:
        if not state.db:
            return {"error": "Database not initialized"}
        
        from dashboard.performance_dashboard import PerformanceDashboard
        dashboard = PerformanceDashboard(state.db)
        metrics = dashboard.get_realtime_metrics()
        
        from dataclasses import asdict
        return asdict(metrics)
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/dashboard/export")
def export_dashboard_report(format: str = "json", lookback_days: int = 30):
    """Export performance report"""
    try:
        if not state.db:
            return {"error": "Database not initialized"}
        
        from dashboard.performance_dashboard import PerformanceDashboard
        dashboard = PerformanceDashboard(state.db)
        filepath = dashboard.export_report(format=format, lookback_days=lookback_days)
        
        return {"status": "success", "filepath": filepath}
    except Exception as e:
        return {"error": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We just keep connection open, pushing from the main loop
            data = await websocket.receive_text()
            # Handle client messages if necessary (e.g. heartbeat)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def broadcast_state_update():
    """Background task to periodically broadcast state to WS clients"""
    while True:
        try:
            if state.system_instance and state.db:
                from dashboard.performance_dashboard import PerformanceDashboard
                from dataclasses import asdict
                
                dashboard = PerformanceDashboard(state.db)
                metrics = dashboard.get_realtime_metrics()
                
                update_data = {
                    "type": "dashboard_update",
                    "data": asdict(metrics)
                }
                await manager.broadcast(update_data)
        except Exception:
            pass
        await asyncio.sleep(5)  # Update every 5 seconds
