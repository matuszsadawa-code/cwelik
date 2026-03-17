"""
Logging setup for the trading system.
Provides a premium, colored console output with icons and structural alignment.
"""

import logging
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

# Import from root config.py (not config package)
try:
    from config import LOG_LEVEL, LOG_FILE
except ImportError:
    # Fallback defaults if config not available
    LOG_LEVEL = "INFO"
    LOG_FILE = "logs/trading_system.log"

# ─── ANSI Color Constants ───────────────────────────────────────────────────
class Colors:
    """ANSI color codes for professional console output."""
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    GREY = "\033[90m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    RESET = "\033[0m"

# ─── Custom Success Level ────────────────────────────────────────────────────
# Level 25 is between INFO (20) and WARNING (30)
SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")

def success(self, message, *args, **kws):
    """Log a SUCCESS message."""
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kws)

# Inject into Logger class
logging.Logger.success = success

# ─── Custom Formatter ────────────────────────────────────────────────────────
class PremiumColoredFormatter(logging.Formatter):
    """
    Highly readable, color-coded formatter with icons for the console.
    """
    
    LEVEL_DEFAULTS = {
        logging.DEBUG:    {"icon": "🔍", "color": Colors.GREY,    "label": "DEBUG"},
        logging.INFO:     {"icon": "ℹ️", "color": Colors.BLUE,    "label": "INFO"},
        SUCCESS_LEVEL_NUM:{"icon": "✅", "color": Colors.GREEN,   "label": "SUCCESS"},
        logging.WARNING:  {"icon": "⚠️", "color": Colors.YELLOW,  "label": "WARNING"},
        logging.ERROR:    {"icon": "❌", "color": Colors.RED,     "label": "ERROR"},
        logging.CRITICAL: {"icon": "🔥", "color": Colors.MAGENTA + Colors.BOLD, "label": "CRITICAL"},
    }

    def format(self, record):
        cfg = self.LEVEL_DEFAULTS.get(record.levelno, {"icon": "●", "color": Colors.WHITE, "label": record.levelname})
        
        # Color & Icon
        icon = cfg["icon"]
        color = cfg["color"]
        label = cfg["label"]
        
        # Time formatting
        dt = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        time_fmt = f"{Colors.GREY}{dt}{Colors.RESET}"
        
        # Component Name (strip openclaw. prefix)
        name = record.name.split(".")[-1]
        name_fmt = f"{Colors.CYAN}{name:<12}{Colors.RESET}"
        
        # Level Label
        level_fmt = f"{color}{label:<8}{Colors.RESET}"
        
        # Message processing
        message = record.getMessage()
        
        # Add extra visual emphasis for WARNING and above
        if record.levelno >= logging.WARNING:
            message = f"{color}{message}{Colors.RESET}"
        elif record.levelno == SUCCESS_LEVEL_NUM:
             message = f"{Colors.GREEN}{message}{Colors.RESET}"
        
        # Final construction
        formatted = f"{time_fmt} | {icon} {level_fmt} | {name_fmt} | {message}"
        
        # Handle exceptions if any
        if record.exc_info:
            if not formatted.endswith('\n'):
                formatted += '\n'
            formatted += self.formatException(record.exc_info)
            
        return formatted

# ─── Logger Factory ──────────────────────────────────────────────────────────
def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance with colored console and plain file output."""
    logger = logging.getLogger(f"openclaw.{name}")

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Set base level
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    logger.propagate = False

    # 1. Console Handler (Premium Display)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)  # Ensure console handler accepts INFO level
    console_handler.setFormatter(PremiumColoredFormatter())
    logger.addHandler(console_handler)

    # 2. File Handler (Clean Rotation)
    try:
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        # Use TimedRotatingFileHandler to avoid Windows file locking issues
        # Rotates at midnight, keeps 5 days of logs
        file_handler = TimedRotatingFileHandler(
            LOG_FILE,
            when='midnight',
            interval=1,
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception:
        # Silently fail if log directory isn't writable
        pass

    return logger
