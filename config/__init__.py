# Config package - import from parent config.py module

import sys
import os
from pathlib import Path

# Get the parent directory (workspace root)
_parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_parent_dir))

# Import the actual config module from parent
import importlib.util
spec = importlib.util.spec_from_file_location("_config_module", _parent_dir / "config.py")
_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_config)

# Re-export everything that exists
BASE_DIR = _config.BASE_DIR
WORKSPACE_DIR = _config.WORKSPACE_DIR
DATA_DIR = _config.DATA_DIR
REPORTS_DIR = _config.REPORTS_DIR
LOGS_DIR = _config.LOGS_DIR
DATABASE_PATH = _config.DATABASE_PATH

BYBIT_API_KEY = _config.BYBIT_API_KEY
BYBIT_API_SECRET = _config.BYBIT_API_SECRET
BYBIT_DEMO_API_KEY = _config.BYBIT_DEMO_API_KEY
BYBIT_DEMO_API_SECRET = _config.BYBIT_DEMO_API_SECRET
BINANCE_API_KEY = _config.BINANCE_API_KEY
BINANCE_API_SECRET = _config.BINANCE_API_SECRET
CRYPTOPANIC_API_KEY = _config.CRYPTOPANIC_API_KEY
NEWSAPI_KEY = _config.NEWSAPI_KEY

FIXED_SYMBOLS = _config.FIXED_SYMBOLS
DYNAMIC_SYMBOLS_CONFIG = _config.DYNAMIC_SYMBOLS_CONFIG
SYMBOLS = _config.SYMBOLS

TIMEFRAMES = _config.TIMEFRAMES
BYBIT_INTERVALS = _config.BYBIT_INTERVALS
BINANCE_INTERVALS = _config.BINANCE_INTERVALS

STRATEGY = _config.STRATEGY

LOG_LEVEL = _config.LOG_LEVEL
LOG_FILE = _config.LOG_FILE
LOG_MAX_BYTES = _config.LOG_MAX_BYTES
LOG_BACKUP_COUNT = _config.LOG_BACKUP_COUNT
