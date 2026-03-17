"""
Symbol Manager - Dynamic symbol list management.

Combines:
- Fixed symbols (always monitored)
- TOP N GAINERS from Bybit (dynamic)
- TOP N LOSERS from Bybit (dynamic)

Updates the dynamic list periodically based on configuration.
Thread-safe implementation to prevent race conditions during symbol updates.
"""

import time
import threading
from typing import List, Set
from datetime import datetime

from config import FIXED_SYMBOLS, DYNAMIC_SYMBOLS_CONFIG
from data.bybit_client import BybitClient
from utils.logger import get_logger

log = get_logger("data.symbol_manager")


class SymbolManager:
    """
    Manages the dynamic symbol list for trading.
    
    Combines fixed symbols with top gainers and losers from Bybit,
    updating the dynamic portion periodically.
    """

    def __init__(self, bybit_client: BybitClient):
        self.bybit = bybit_client
        self.fixed_symbols = FIXED_SYMBOLS.copy()
        self.dynamic_config = DYNAMIC_SYMBOLS_CONFIG
        
        # Thread-safe lock for symbol list updates
        self._lock = threading.RLock()
        
        # Current symbol list
        self.current_symbols: List[str] = []
        self.last_update: float = 0
        
        # Update interval in seconds
        self.update_interval = self.dynamic_config.get("update_interval_minutes", 60) * 60
        
        # Initialize with fixed symbols
        with self._lock:
            self.current_symbols = self.fixed_symbols.copy()
        
        log.info(f"SymbolManager initialized with {len(self.fixed_symbols)} fixed symbols (thread-safe)")
        log.info(f"Dynamic update interval: {self.update_interval / 60:.0f} minutes")

    def get_symbols(self, force_update: bool = False) -> List[str]:
        """
        Get the current symbol list (thread-safe).
        
        Automatically updates the dynamic symbols if the update interval has passed.
        If dynamic symbols are disabled (top_gainers == 0 and top_losers == 0),
        returns the fixed symbol list directly without calling update_dynamic_symbols().
        
        Args:
            force_update: Force an immediate update regardless of interval
            
        Returns:
            List of symbols to monitor (copy to prevent external modification)
        """
        # Check if dynamic symbols are disabled
        top_gainers = self.dynamic_config.get("top_gainers", 10)
        top_losers = self.dynamic_config.get("top_losers", 10)
        
        if top_gainers == 0 and top_losers == 0:
            log.info("Dynamic symbols disabled, using fixed list only")
            with self._lock:
                return self.fixed_symbols.copy()
        
        current_time = time.time()
        
        with self._lock:
            time_since_update = current_time - self.last_update
            
            # Check if update is needed
            if force_update or time_since_update >= self.update_interval:
                log.info(f"Updating dynamic symbols (last update: {time_since_update / 60:.1f} minutes ago)")
                self.update_dynamic_symbols()
            
            # Return a copy to prevent external modification
            return self.current_symbols.copy()

    def update_dynamic_symbols(self):
        """
        Update the dynamic symbol list by fetching top gainers and losers from Bybit (thread-safe).
        
        Combines:
        - Fixed symbols (always included)
        - Top N gainers (from Bybit)
        - Top N losers (from Bybit)
        
        Removes duplicates and updates the current symbol list atomically.
        """
        try:
            # Fetch top gainers and losers (outside lock to avoid blocking)
            top_gainers_count = self.dynamic_config.get("top_gainers", 10)
            top_losers_count = self.dynamic_config.get("top_losers", 10)
            
            log.info(f"Fetching TOP {top_gainers_count} GAINERS and TOP {top_losers_count} LOSERS from Bybit...")
            
            gainers = self.bybit.get_top_gainers(limit=top_gainers_count)
            losers = self.bybit.get_top_losers(limit=top_losers_count)
            
            # Combine all symbols (fixed + gainers + losers)
            all_symbols = self.fixed_symbols + gainers + losers
            
            # Remove duplicates while preserving order (fixed symbols first)
            seen: Set[str] = set()
            unique_symbols = []
            for symbol in all_symbols:
                if symbol not in seen:
                    seen.add(symbol)
                    unique_symbols.append(symbol)
            
            # Atomic update with lock
            with self._lock:
                old_count = len(self.current_symbols)
                self.current_symbols = unique_symbols
                self.last_update = time.time()
                
                # Log the update
                log.info(f"✓ Symbol list updated: {old_count} → {len(self.current_symbols)} symbols (thread-safe)")
                log.info(f"  Fixed: {len(self.fixed_symbols)}")
                log.info(f"  Gainers: {len(gainers)} (unique: {len([g for g in gainers if g not in self.fixed_symbols])})")
                log.info(f"  Losers: {len(losers)} (unique: {len([l for l in losers if l not in self.fixed_symbols and l not in gainers])})")
                
                # Log the new symbols (not in fixed list)
                new_dynamic = [s for s in self.current_symbols if s not in self.fixed_symbols]
                if new_dynamic:
                    log.info(f"  Dynamic symbols: {', '.join(new_dynamic[:10])}{'...' if len(new_dynamic) > 10 else ''}")
        
        except Exception as e:
            log.error(f"Failed to update dynamic symbols: {e}", exc_info=True)
            log.warning("Continuing with current symbol list")

    def get_stats(self) -> dict:
        """
        Get statistics about the current symbol list (thread-safe).
        
        Returns:
            Dict with stats: total, fixed, dynamic, last_update, next_update
        """
        with self._lock:
            current_time = time.time()
            time_since_update = current_time - self.last_update
            time_until_next = max(0, self.update_interval - time_since_update)
            
            dynamic_count = len([s for s in self.current_symbols if s not in self.fixed_symbols])
            
            return {
                "total_symbols": len(self.current_symbols),
                "fixed_symbols": len(self.fixed_symbols),
                "dynamic_symbols": dynamic_count,
                "last_update": datetime.fromtimestamp(self.last_update).isoformat() if self.last_update > 0 else "Never",
                "next_update_in_minutes": time_until_next / 60,
                "update_interval_minutes": self.update_interval / 60,
            }

    def force_update(self):
        """Force an immediate update of the dynamic symbol list."""
        log.info("Forcing symbol list update...")
        self.update_dynamic_symbols()
