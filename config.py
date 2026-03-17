"""
Configuration for the OpenClaw Trading System.

API keys are loaded from environment variables or config file.
"""

import os
import json
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
WORKSPACE_DIR = BASE_DIR.parent
DATA_DIR = BASE_DIR / "db"
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"

# Create dirs
for d in [DATA_DIR, REPORTS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── API Keys ────────────────────────────────────────────────────────────────
# Set via environment variables or edit config.json
BYBIT_API_KEY = os.environ.get("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.environ.get("BYBIT_API_SECRET", "")
BYBIT_DEMO_API_KEY = os.environ.get("BYBIT_DEMO_API_KEY", "")
BYBIT_DEMO_API_SECRET = os.environ.get("BYBIT_DEMO_API_SECRET", "")
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET", "")

# News API Keys (for News Sentiment Integration)
CRYPTOPANIC_API_KEY = os.environ.get("CRYPTOPANIC_API_KEY", "")
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")

# Try loading from local config file
_config_file = BASE_DIR / "config.json"
if _config_file.exists():
    with open(_config_file, "r") as f:
        _cfg = json.load(f)
    BYBIT_API_KEY = _cfg.get("bybit_api_key", BYBIT_API_KEY)
    BYBIT_API_SECRET = _cfg.get("bybit_api_secret", BYBIT_API_SECRET)
    BYBIT_DEMO_API_KEY = _cfg.get("bybit_demo_api_key", BYBIT_DEMO_API_KEY)
    BYBIT_DEMO_API_SECRET = _cfg.get("bybit_demo_api_secret", BYBIT_DEMO_API_SECRET)
    BINANCE_API_KEY = _cfg.get("binance_api_key", BINANCE_API_KEY)
    BINANCE_API_SECRET = _cfg.get("binance_api_secret", BINANCE_API_SECRET)
    CRYPTOPANIC_API_KEY = _cfg.get("cryptopanic_api_key", CRYPTOPANIC_API_KEY)
    NEWSAPI_KEY = _cfg.get("newsapi_key", NEWSAPI_KEY)

# ─── Trading Symbols ─────────────────────────────────────────────────────────
# Fixed symbols - always monitored
FIXED_SYMBOLS = [
    "BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "LTC-USDT",
    "LINK-USDT", "AVAX-USDT", "NEAR-USDT", "TON-USDT", "SPX-USDT",
    "FARTCOIN-USDT", "ATOM-USDT", "BCH-USDT", "ADA-USDT", "LDO-USDT",
    "AAVE-USDT", "OP-USDT", "DOGE-USDT", "BNB-USDT", "DOT-USDT",
    "IP-USDT", "1000PEPE-USDT", "APT-USDT", "DASH-USDT", "NOT-USDT",
    "ARB-USDT", "WLD-USDT", "ETC-USDT", "JUP-USDT", "HBAR-USDT",
]

# Dynamic symbols configuration
DYNAMIC_SYMBOLS_CONFIG = {
    "top_gainers": 0,   # Disabled - use fixed symbols only
    "top_losers": 0,    # Disabled - use fixed symbols only
    "update_interval_minutes": 0,  # Disabled
}

# Use fixed symbols only - copy to prevent mutation
SYMBOLS = FIXED_SYMBOLS.copy()

# ─── Timeframes ──────────────────────────────────────────────────────────────
TIMEFRAMES = {
    "1m": "1",      # 1 minute (for MTF confluence)
    "confirmation": "5",    # 5 minutes
    "15m": "15",    # 15 minutes (for MTF confluence)
    "zones": "30",  # 30 minutes
    "1h": "60",     # 1 hour (for MTF confluence)
    "trend": "240", # 4 hours
}

# ByBit interval mapping
BYBIT_INTERVALS = {
    "1": "1",       # 1M
    "5": "5",       # 5M
    "15": "15",     # 15M
    "30": "30",     # 30M
    "60": "60",     # 1H
    "240": "240",   # 4H
}

# Binance interval mapping
BINANCE_INTERVALS = {
    "1": "1m",      # 1M
    "5": "5m",      # 5M
    "15": "15m",    # 15M
    "30": "30m",    # 30M
    "60": "1h",     # 1H
    "240": "4h",    # 4H
    "1440": "1d",   # 1D (Daily)
}

# ─── Strategy Parameters ─────────────────────────────────────────────────────
STRATEGY = {
    # Step 1: Trend
    "trend_candle_count": 50,          # Number of 4H candles to analyze
    "min_hh_for_bullish": 3,           # Minimum Higher Highs
    "min_hl_for_bullish": 2,           # Minimum Higher Lows
    "min_ll_for_bearish": 3,           # Minimum Lower Lows
    "min_lh_for_bearish": 2,           # Minimum Lower Highs
    "range_tolerance_pct": 1.0,        # Range detection tolerance (%)

    # Step 2: Zones
    "zone_candle_count": 100,          # Number of 30M candles
    "max_zone_distance_pct": 3.0,      # Max distance from current price to zone (%)
    "base_max_range_pct": 2.0,         # Max range for base/consolidation (%)
    "zone_min_strength": 60,           # Minimum zone strength to consider

    # Step 3: Volume
    "volume_candle_count": 50,         # Number of 5M candles
    "volume_shrink_threshold": 0.7,    # Volume must shrink to 70% of earlier (< = exhaustion)
    "volume_window_recent": 10,        # Recent candles window
    "volume_window_earlier": 10,       # Earlier candles window

    # Step 4: Order Flow
    "orderflow_candle_count": 20,      # Number of 5M candles for OF analysis
    "delta_flip_threshold": 0.3,       # Delta ratio flip threshold
    "imbalance_threshold": 1.5,        # Bid/ask imbalance ratio for confirmation
    "absorption_min_volume": 2.0,      # Min volume multiplier for absorption detection
    "cluster_min_trades": 10,          # Min trades in cluster
    "cluster_time_window_sec": 60,     # Cluster time window (seconds)

    # Signal Quality
    "min_quality_for_signal": "A",     # Minimum quality to emit signal (A+, A, B, C) — ONLY A and A+ signals
    "quality_thresholds": {
        "A+": 5,  # All 5 steps confirmed (trend + zones + volume + 5min shift + OF)
        "A": 4,   # 4 steps confirmed
        "B": 3,   # 3 steps confirmed
        "C": 2,   # 2 steps confirmed
    },

    # Risk Management
    "sl_buffer_pct": 0.5,             # Buffer below/above zone for SL (%)
    "tp_rr_ratio": 2.0,              # Primary TP at 2:1 R:R (TP1 for risk-off at 1:1)
    "use_dual_tp": True,             # Use dual TP system (TP1: 1:1, TP2: 2:1)
    "default_leverage": 25,           # Default leverage for position sizing (25x as per requirements)
    "order_expiration_minutes": 15,   # How long a limit entry order can stay open before cancellation

    # Monitoring
    "scan_interval_seconds": 300,      # How often to run full scan (5 min)
    "ws_reconnect_delay_sec": 5,       # WebSocket reconnect delay
}

# ─── Database ─────────────────────────────────────────────────────────────────
DATABASE_PATH = str(DATA_DIR / "trading_system.db")

# ─── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"
LOG_FILE = str(LOGS_DIR / "trading_system.log")
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5
