"""
Exchange Minimums Tracker
Fetches and caches minimum order sizes and tick sizes for each symbol from Bybit API.
"""

import time
import math
import asyncio
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR
from typing import Dict, Optional, Tuple, Union
from datetime import datetime, timedelta

from utils.logger import get_logger

log = get_logger("execution.minimums")


class ExchangeMinimums:
    """Track minimum order sizes and price precision for each symbol."""
    
    def __init__(self, executor):
        self.executor = executor
        self.minimums = {}  # symbol -> min_qty
        self.qty_steps = {}  # symbol -> qty_step (e.g., 0.1)
        self.tick_sizes = {}  # symbol -> tick_size (e.g., "0.01")
        self.tick_decimals = {}  # symbol -> number of decimals
        self.max_leverages = {}  # symbol -> max allowed leverage
        self.last_update = {}  # symbol -> timestamp
        self.cache_duration = 3600  # Cache for 1 hour
        
        log.info("ExchangeMinimums initialized")
    
    async def get_minimum(self, symbol: str) -> float:
        """Get minimum order size for symbol (async)."""
        # Check if we have cached data
        if symbol in self.minimums and not self._is_stale(symbol):
            return self.minimums[symbol]
        
        # Fetch from exchange
        await self._fetch_from_exchange(symbol)
        
        if symbol in self.minimums:
            return self.minimums[symbol]
        
        # Fallback to conservative default
        default = 0.01
        log.warning(f"Could not fetch minimum for {symbol}, using default: {default}")
        return default
    
    async def get_max_leverage(self, symbol: str) -> float:
        """Get maximum allowed leverage for symbol (async)."""
        # Check if we have cached data
        if symbol in self.max_leverages and not self._is_stale(symbol):
            return self.max_leverages[symbol]
        
        # Fetch from exchange
        await self._fetch_from_exchange(symbol)
        
        if symbol in self.max_leverages:
            return self.max_leverages[symbol]
        
        # Fallback to conservative default
        default = 25.0
        log.warning(f"Could not fetch max leverage for {symbol}, using default: {default}x")
        return default
    
    async def get_qty_step(self, symbol: str) -> float:
        """Get quantity step size for symbol (async)."""
        # Check if we have cached data
        if symbol in self.qty_steps and not self._is_stale(symbol):
            return self.qty_steps[symbol]
        
        # Fetch from exchange
        await self._fetch_from_exchange(symbol)
        
        if symbol in self.qty_steps:
            return self.qty_steps[symbol]
        
        # Fallback to conservative default
        default = 0.01
        log.warning(f"Could not fetch qty step for {symbol}, using default: {default}")
        return default
    
    async def round_quantity(self, symbol: str, qty: float) -> float:
        """Round quantity to exchange requirements (async)."""
        qty_step = await self.get_qty_step(symbol)
        
        # Round to nearest qty step using Decimal to avoid float errors
        d_qty = Decimal(str(qty))
        d_step = Decimal(str(qty_step))
        rounded = (d_qty / d_step).to_integral_value(rounding=ROUND_FLOOR) * d_step
        
        return float(rounded)
    
    async def get_tick_decimals(self, symbol: str, price: float = None) -> int:
        """Get number of decimal places for price precision (async)."""
        # 1. Check if we have cached data from API (PRIORITY)
        if symbol in self.tick_decimals and not self._is_stale(symbol):
            return self.tick_decimals[symbol]
        
        # 2. Try to fetch from exchange
        await self._fetch_from_exchange(symbol)
        
        if symbol in self.tick_decimals:
            return self.tick_decimals[symbol]
            
        # 3. Fallback only if API fails
        if price is not None:
            price_abs = abs(float(price))
            if price_abs < 0.0001:
                decimals = 8
            elif price_abs < 0.001:
                decimals = 7
            elif price_abs < 0.01:
                decimals = 6
            elif price_abs < 0.1:
                decimals = 5
            elif price_abs < 1.0:
                decimals = 4
            elif price_abs < 10.0:
                decimals = 3
            else:
                decimals = 2
            log.info(f"Using price-based fallback for {symbol} (API MISS): price=${price} -> {decimals} decimals")
            return decimals
        
        # Final fallback to 2 decimals
        default = 2
        log.warning(f"Could not fetch tick size for {symbol}, using default: {default} decimals")
        return default

    async def format_price(self, symbol: str, price: Union[float, Decimal], rounding=ROUND_HALF_UP) -> str:
        """Format price as string with exact exchange precision (async)."""
        if price is None:
            return "0.00"
            
        decimals = await self.get_tick_decimals(symbol, price=float(price))
        
        # Use Decimal for robust rounding
        try:
            d = Decimal(str(price))
            # Quantize to required decimals
            format_str = f"0.{'0' * decimals}" if decimals > 0 else "0"
            rounded = d.quantize(Decimal(format_str), rounding=rounding)
            return format(rounded, f'.{decimals}f')
        except Exception as e:
            log.error(f"Error formatting price {price} for {symbol}: {e}")
            return str(round(price, decimals))

    async def format_quantity(self, symbol: str, qty: Union[float, Decimal]) -> str:
        """Format quantity as string with exact exchange precision (async)."""
        if qty is None:
            return "0.00"
            
        qty_step = await self.get_qty_step(symbol)
        
        try:
            d_qty = Decimal(str(qty))
            d_step = Decimal(str(qty_step))
            
            # Use floor rounding for quantities to ensure we don't exceed balance
            # qty = floor(qty / step) * step
            multiplier = (d_qty / d_step).to_integral_value(rounding=ROUND_FLOOR)
            rounded = multiplier * d_step
            
            # Calculate required decimals based on step
            if d_step >= 1:
                decimals = 0
            else:
                # Count decimal places in step (e.g., 0.001 -> 3)
                decimals = abs(d_step.as_tuple().exponent)
            
            return format(rounded, f'.{decimals}f')
        except Exception as e:
            log.error(f"Error formatting quantity {qty} for {symbol}: {e}")
            return str(qty)
    
    def _is_stale(self, symbol: str) -> bool:
        """Check if cached data is stale."""
        if symbol not in self.last_update:
            return True
        
        age = (datetime.utcnow() - self.last_update[symbol]).total_seconds()
        return age > self.cache_duration
    
    async def _fetch_from_exchange(self, symbol: str) -> bool:
        """Fetch instrument info from Bybit API (async)."""
        try:
            # Convert symbol to ByBit format before API call
            bybit_symbol = symbol.replace("-", "")  # "LINK-USDT" → "LINKUSDT"
            log.debug(f"Fetching instrument info: {symbol} → {bybit_symbol}")
            
            params = {
                "category": "linear",
                "symbol": bybit_symbol,
            }
            
            # Use executor's client for authenticated call
            response = await self.executor.client._request("GET", "/v5/market/instruments-info", params)
            
            if response and "list" in response and len(response["list"]) > 0:
                instrument = response["list"][0]
                
                # Extract minimum order quantity and qty step
                lot_size_filter = instrument.get("lotSizeFilter", {})
                min_order_qty = lot_size_filter.get("minOrderQty")
                qty_step = lot_size_filter.get("qtyStep")
                
                if min_order_qty:
                    self.minimums[symbol] = float(min_order_qty)
                    log.info(f"Fetched minimum for {symbol}: {min_order_qty}")
                
                if qty_step:
                    self.qty_steps[symbol] = float(qty_step)
                    log.info(f"Fetched qty step for {symbol}: {qty_step}")
                
                # Extract tick size and calculate decimals
                price_filter = instrument.get("priceFilter", {})
                tick_size = price_filter.get("tickSize")
                
                if tick_size:
                    self.tick_sizes[symbol] = tick_size
                    # Calculate number of decimals from tick size
                    # e.g., "0.01" -> 2, "0.0001" -> 4, "0.00001" -> 5
                    tick_float = float(tick_size)
                    if tick_float >= 1:
                        decimals = 0
                    else:
                        # Count decimal places
                        decimals = len(tick_size.split('.')[-1].rstrip('0'))
                    
                    self.tick_decimals[symbol] = decimals
                    log.info(f"Fetched tick size for {symbol}: {tick_size} ({decimals} decimals)")
                
                # Extract max leverage
                leverage_filter = instrument.get("leverageFilter", {})
                max_leverage = leverage_filter.get("maxLeverage")
                
                if max_leverage:
                    self.max_leverages[symbol] = float(max_leverage)
                    log.info(f"Fetched max leverage for {symbol}: {max_leverage}x")

                # Update timestamp
                self.last_update[symbol] = datetime.utcnow()
                return True
            
            return False
            
        except Exception as e:
            log.error(f"Failed to fetch instrument info for {symbol}: {e}")
            return False
    
    async def preload_minimums(self, symbols: list):
        """Preload minimums and tick sizes for multiple symbols (async)."""
        log.info(f"Preloading instrument info for {len(symbols)} symbols...")
        
        for symbol in symbols:
            try:
                await self._fetch_from_exchange(symbol)
                await asyncio.sleep(0.1)  # Rate limiting
            except Exception as e:
                log.error(f"Failed to preload {symbol}: {e}")
        
        log.info(f"Preloaded {len(self.minimums)} minimums and {len(self.tick_decimals)} tick sizes")
