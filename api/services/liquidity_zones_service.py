"""
Liquidity Zones Service for OpenClaw Trading Dashboard

Identifies liquidity zones from order book imbalances and historical volume profile.
Classifies zones as support or resistance with strength ratings.

Features:
- Order book imbalance analysis for liquidity concentration
- Historical volume profile analysis for high-volume price levels
- Support/resistance classification based on price position
- Strength rating (high/medium/low) based on liquidity amount
- Estimated liquidity calculation for each zone
- REST API endpoint for querying zones by symbol
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from collections import defaultdict

from data.bybit_client_async import AsyncBybitClient
from data.binance_client_async import AsyncBinanceClient
from data.candle_manager_async import AsyncCandleManager
from config import SYMBOLS

logger = logging.getLogger(__name__)


class LiquidityZonesService:
    """
    Service for identifying and analyzing liquidity zones.
    
    Responsibilities:
    - Identify liquidity zones from order book imbalances
    - Identify liquidity zones from historical volume profile
    - Classify zones as support (below price) or resistance (above price)
    - Assign strength rating (high/medium/low) based on liquidity amount
    - Calculate estimated liquidity amount for each zone
    - Provide REST API endpoint for querying zones
    """
    
    def __init__(self, candle_manager: AsyncCandleManager, symbols: List[str] = None):
        """
        Initialize liquidity zones service.
        
        Args:
            candle_manager: Async candle manager for fetching historical data
            symbols: List of symbols to monitor (defaults to config.SYMBOLS)
        """
        self.candle_manager = candle_manager
        self.symbols = symbols or SYMBOLS
        
        # Exchange clients for order book data
        self.bybit_client = AsyncBybitClient(use_demo=False)
        self.binance_client = AsyncBinanceClient()
        
        # Liquidity zones cache per symbol
        self.zones_cache: Dict[str, List[Dict]] = {}
        
        # Service state
        self.running = False
        self.task: Optional[asyncio.Task] = None
        
        logger.info(f"LiquidityZonesService initialized with {len(self.symbols)} symbols")
    
    async def start(self):
        """Start the liquidity zones service background task."""
        if self.running:
            logger.warning("LiquidityZonesService already running")
            return
        
        self.running = True
        
        # Initialize Binance valid symbols cache
        await self.binance_client.update_valid_symbols()
        
        # Start background task for periodic updates
        self.task = asyncio.create_task(self._zones_update_loop())
        
        logger.info("LiquidityZonesService started")
    
    async def stop(self):
        """Stop the liquidity zones service and cleanup."""
        if not self.running:
            return
        
        self.running = False
        
        # Cancel background task
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        # Close exchange clients
        await self.bybit_client.close()
        await self.binance_client.close()
        
        logger.info("LiquidityZonesService stopped")
    
    async def _zones_update_loop(self):
        """
        Background task: Update liquidity zones every 5 minutes.
        
        Fetches order book and volume profile data to identify zones.
        """
        logger.info("Liquidity zones update loop started (5min interval)")
        
        while self.running:
            try:
                await self._update_all_zones()
                await asyncio.sleep(300.0)  # 5 minute interval
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in zones update loop: {e}", exc_info=True)
                await asyncio.sleep(300.0)  # Continue on error
    
    async def _update_all_zones(self):
        """
        Update liquidity zones for all symbols in parallel.
        
        Combines order book imbalances and volume profile analysis.
        """
        # Update zones for all symbols in parallel
        tasks = [self._update_zones_for_symbol(symbol) for symbol in self.symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error updating zones for {self.symbols[i]}: {result}")
    
    async def _update_zones_for_symbol(self, symbol: str):
        """
        Identify and update liquidity zones for a single symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
        """
        try:
            # Fetch data in parallel
            orderbook_task = self._fetch_orderbook(symbol)
            candles_task = self.candle_manager.get_candles(
                symbol=symbol,
                timeframe="1h",
                limit=200
            )
            
            orderbook, candles = await asyncio.gather(
                orderbook_task, candles_task, return_exceptions=True
            )
            
            if isinstance(orderbook, Exception):
                orderbook = None
            if isinstance(candles, Exception):
                candles = []
            
            # Get current price
            current_price = candles[-1]["close"] if candles else 0
            if current_price == 0:
                logger.warning(f"No price data for {symbol}")
                return
            
            # Identify zones from both sources
            ob_zones = self._identify_orderbook_zones(symbol, orderbook, current_price) if orderbook else []
            vp_zones = self._identify_volume_profile_zones(symbol, candles, current_price)
            
            # Merge and deduplicate zones
            all_zones = self._merge_zones(ob_zones, vp_zones, current_price)
            
            # Cache zones
            self.zones_cache[symbol] = all_zones
            
            logger.debug(f"Updated {len(all_zones)} liquidity zones for {symbol}")
            
        except Exception as e:
            logger.error(f"Error updating zones for {symbol}: {e}", exc_info=True)
    
    async def _fetch_orderbook(self, symbol: str) -> Optional[Dict]:
        """
        Fetch order book from both exchanges and merge.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            dict: Merged order book or None on error
        """
        try:
            # Fetch from both exchanges in parallel
            bybit_task = self.bybit_client.get_orderbook(symbol, limit=200)
            binance_task = self.binance_client.get_orderbook(symbol, limit=100)
            
            bybit_ob, binance_ob = await asyncio.gather(
                bybit_task, binance_task, return_exceptions=True
            )
            
            if isinstance(bybit_ob, Exception):
                bybit_ob = {}
            if isinstance(binance_ob, Exception):
                binance_ob = {}
            
            # Merge order books
            return self._merge_orderbooks(bybit_ob, binance_ob)
            
        except Exception as e:
            logger.debug(f"Error fetching orderbook for {symbol}: {e}")
            return None
    
    def _merge_orderbooks(self, bybit_ob: Dict, binance_ob: Dict) -> Dict:
        """
        Merge order books from both exchanges.
        
        Args:
            bybit_ob: Bybit order book
            binance_ob: Binance order book
            
        Returns:
            dict: Merged order book
        """
        if not bybit_ob and not binance_ob:
            return {}
        
        if not bybit_ob:
            return binance_ob
        if not binance_ob:
            return bybit_ob
        
        # Combine bids and asks
        all_bids = {}
        for bid in bybit_ob.get("bids", []) + binance_ob.get("bids", []):
            price = round(bid["price"], 2)
            all_bids[price] = all_bids.get(price, 0) + bid["size"]
        
        all_asks = {}
        for ask in bybit_ob.get("asks", []) + binance_ob.get("asks", []):
            price = round(ask["price"], 2)
            all_asks[price] = all_asks.get(price, 0) + ask["size"]
        
        bids = sorted(
            [{"price": p, "size": s} for p, s in all_bids.items()],
            key=lambda x: -x["price"]
        )
        asks = sorted(
            [{"price": p, "size": s} for p, s in all_asks.items()],
            key=lambda x: x["price"]
        )
        
        return {
            "bids": bids,
            "asks": asks,
            "best_bid": bids[0]["price"] if bids else 0,
            "best_ask": asks[0]["price"] if asks else 0,
        }
    
    def _identify_orderbook_zones(self, symbol: str, orderbook: Dict, 
                                  current_price: float) -> List[Dict]:
        """
        Identify liquidity zones from order book imbalances.
        
        Looks for price levels with significantly higher order concentration
        than surrounding levels (walls, large resting orders).
        
        Args:
            symbol: Trading pair symbol
            orderbook: Merged order book data
            current_price: Current market price
            
        Returns:
            list: List of liquidity zone dictionaries
        """
        zones = []
        
        if not orderbook:
            return zones
        
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])
        
        # Calculate average order size for threshold
        all_sizes = [b["size"] for b in bids] + [a["size"] for a in asks]
        if not all_sizes:
            return zones
        
        avg_size = sum(all_sizes) / len(all_sizes)
        threshold_multiplier = 3.0  # Zone must be 3x average size
        
        # Identify bid zones (support)
        for bid in bids:
            if bid["size"] >= avg_size * threshold_multiplier:
                # Calculate zone range (±0.2% around price level)
                zone_range = bid["price"] * 0.002
                
                zones.append({
                    "symbol": symbol,
                    "priceLevel": bid["price"],
                    "priceRangeLow": bid["price"] - zone_range,
                    "priceRangeHigh": bid["price"] + zone_range,
                    "type": "support",
                    "strength": self._calculate_strength(bid["size"], avg_size),
                    "liquidityAmount": round(bid["size"], 4),
                    "source": "orderbook",
                    "isNearPrice": abs(bid["price"] - current_price) / current_price <= 0.005,
                })
        
        # Identify ask zones (resistance)
        for ask in asks:
            if ask["size"] >= avg_size * threshold_multiplier:
                # Calculate zone range (±0.2% around price level)
                zone_range = ask["price"] * 0.002
                
                zones.append({
                    "symbol": symbol,
                    "priceLevel": ask["price"],
                    "priceRangeLow": ask["price"] - zone_range,
                    "priceRangeHigh": ask["price"] + zone_range,
                    "type": "resistance",
                    "strength": self._calculate_strength(ask["size"], avg_size),
                    "liquidityAmount": round(ask["size"], 4),
                    "source": "orderbook",
                    "isNearPrice": abs(ask["price"] - current_price) / current_price <= 0.005,
                })
        
        return zones
    
    def _identify_volume_profile_zones(self, symbol: str, candles: List[Dict],
                                       current_price: float) -> List[Dict]:
        """
        Identify liquidity zones from historical volume profile.
        
        Analyzes volume distribution across price levels to find
        high-volume areas (POC, VAH, VAL, and other significant levels).
        
        Args:
            symbol: Trading pair symbol
            candles: Historical candle data
            current_price: Current market price
            
        Returns:
            list: List of liquidity zone dictionaries
        """
        zones = []
        
        if not candles or len(candles) < 20:
            return zones
        
        # Build volume profile: aggregate volume by price level
        price_volume = defaultdict(float)
        
        for candle in candles:
            # Approximate volume distribution across the candle's range
            # Use close price as representative level
            price_level = round(candle["close"], 2)
            price_volume[price_level] += candle["volume"]
        
        if not price_volume:
            return zones
        
        # Calculate statistics
        volumes = list(price_volume.values())
        avg_volume = sum(volumes) / len(volumes)
        max_volume = max(volumes)
        
        # Find Point of Control (POC) - highest volume level
        poc_price = max(price_volume.items(), key=lambda x: x[1])[0]
        poc_volume = price_volume[poc_price]
        
        # Calculate Value Area (70% of volume)
        sorted_levels = sorted(price_volume.items(), key=lambda x: -x[1])
        total_volume = sum(volumes)
        value_area_volume = total_volume * 0.70
        
        cumulative_volume = 0
        value_area_prices = []
        for price, vol in sorted_levels:
            cumulative_volume += vol
            value_area_prices.append(price)
            if cumulative_volume >= value_area_volume:
                break
        
        vah = max(value_area_prices) if value_area_prices else poc_price
        val = min(value_area_prices) if value_area_prices else poc_price
        
        # Add POC as a zone (strongest)
        zones.append({
            "symbol": symbol,
            "priceLevel": poc_price,
            "priceRangeLow": poc_price * 0.998,
            "priceRangeHigh": poc_price * 1.002,
            "type": "support" if poc_price < current_price else "resistance",
            "strength": "high",
            "liquidityAmount": round(poc_volume, 4),
            "source": "volume_profile",
            "isNearPrice": abs(poc_price - current_price) / current_price <= 0.005,
            "label": "POC",
        })
        
        # Add VAH as a zone (medium strength)
        if vah != poc_price:
            zones.append({
                "symbol": symbol,
                "priceLevel": vah,
                "priceRangeLow": vah * 0.998,
                "priceRangeHigh": vah * 1.002,
                "type": "support" if vah < current_price else "resistance",
                "strength": "medium",
                "liquidityAmount": round(price_volume.get(vah, 0), 4),
                "source": "volume_profile",
                "isNearPrice": abs(vah - current_price) / current_price <= 0.005,
                "label": "VAH",
            })
        
        # Add VAL as a zone (medium strength)
        if val != poc_price and val != vah:
            zones.append({
                "symbol": symbol,
                "priceLevel": val,
                "priceRangeLow": val * 0.998,
                "priceRangeHigh": val * 1.002,
                "type": "support" if val < current_price else "resistance",
                "strength": "medium",
                "liquidityAmount": round(price_volume.get(val, 0), 4),
                "source": "volume_profile",
                "isNearPrice": abs(val - current_price) / current_price <= 0.005,
                "label": "VAL",
            })
        
        # Add other significant volume levels (above 2x average)
        threshold = avg_volume * 2.0
        for price, volume in price_volume.items():
            # Skip if already added (POC, VAH, VAL)
            if price in [poc_price, vah, val]:
                continue
            
            if volume >= threshold:
                zones.append({
                    "symbol": symbol,
                    "priceLevel": price,
                    "priceRangeLow": price * 0.998,
                    "priceRangeHigh": price * 1.002,
                    "type": "support" if price < current_price else "resistance",
                    "strength": self._calculate_strength_from_volume(volume, avg_volume, max_volume),
                    "liquidityAmount": round(volume, 4),
                    "source": "volume_profile",
                    "isNearPrice": abs(price - current_price) / current_price <= 0.005,
                })
        
        return zones
    
    def _calculate_strength(self, size: float, avg_size: float) -> str:
        """
        Calculate zone strength based on order size relative to average.
        
        Args:
            size: Order size at this level
            avg_size: Average order size
            
        Returns:
            str: Strength rating (high/medium/low)
        """
        multiplier = size / avg_size if avg_size > 0 else 1
        
        if multiplier >= 5.0:
            return "high"
        elif multiplier >= 3.0:
            return "medium"
        else:
            return "low"
    
    def _calculate_strength_from_volume(self, volume: float, avg_volume: float, 
                                       max_volume: float) -> str:
        """
        Calculate zone strength based on volume relative to average and max.
        
        Args:
            volume: Volume at this level
            avg_volume: Average volume across all levels
            max_volume: Maximum volume at any level
            
        Returns:
            str: Strength rating (high/medium/low)
        """
        # Normalize volume relative to max
        volume_pct = volume / max_volume if max_volume > 0 else 0
        
        if volume_pct >= 0.7:  # Within 70% of max volume
            return "high"
        elif volume_pct >= 0.4:  # Within 40% of max volume
            return "medium"
        else:
            return "low"
    
    def _merge_zones(self, ob_zones: List[Dict], vp_zones: List[Dict],
                    current_price: float) -> List[Dict]:
        """
        Merge zones from order book and volume profile, removing duplicates.
        
        Zones within 0.5% of each other are considered duplicates.
        The zone with higher liquidity amount is kept.
        
        Args:
            ob_zones: Zones from order book analysis
            vp_zones: Zones from volume profile analysis
            current_price: Current market price
            
        Returns:
            list: Merged and deduplicated zones
        """
        all_zones = ob_zones + vp_zones
        
        if not all_zones:
            return []
        
        # Sort by price level
        all_zones.sort(key=lambda z: z["priceLevel"])
        
        # Deduplicate zones within 0.5% of each other
        merged = []
        skip_indices = set()
        
        for i, zone in enumerate(all_zones):
            if i in skip_indices:
                continue
            
            # Find nearby zones (within 0.5%)
            nearby = [zone]
            for j in range(i + 1, len(all_zones)):
                if j in skip_indices:
                    continue
                
                other = all_zones[j]
                price_diff_pct = abs(zone["priceLevel"] - other["priceLevel"]) / zone["priceLevel"]
                
                if price_diff_pct <= 0.005:  # Within 0.5%
                    nearby.append(other)
                    skip_indices.add(j)
                else:
                    break  # Zones are sorted, so no more nearby zones
            
            # Merge nearby zones - keep the one with highest liquidity
            best_zone = max(nearby, key=lambda z: z["liquidityAmount"])
            
            # If multiple sources, mark as "combined"
            if len(nearby) > 1:
                sources = set(z["source"] for z in nearby)
                if len(sources) > 1:
                    best_zone["source"] = "combined"
                    # Upgrade strength if confirmed by multiple sources
                    if best_zone["strength"] == "medium":
                        best_zone["strength"] = "high"
                    elif best_zone["strength"] == "low":
                        best_zone["strength"] = "medium"
            
            merged.append(best_zone)
        
        # Limit to top 20 zones by liquidity amount
        merged.sort(key=lambda z: z["liquidityAmount"], reverse=True)
        merged = merged[:20]
        
        # Re-sort by price for output
        merged.sort(key=lambda z: z["priceLevel"])
        
        # Add timestamp
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        for zone in merged:
            zone["timestamp"] = timestamp
        
        return merged
    
    async def get_liquidity_zones(self, symbol: str) -> List[Dict]:
        """
        Get liquidity zones for a symbol.
        
        If zones are not cached, calculates them on-demand.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            list: List of liquidity zone dictionaries
        """
        # Return cached zones if available
        if symbol in self.zones_cache:
            return self.zones_cache[symbol]
        
        # Calculate zones on-demand
        await self._update_zones_for_symbol(symbol)
        
        return self.zones_cache.get(symbol, [])
    
    def get_service_status(self) -> Dict:
        """
        Get service status for health monitoring.
        
        Returns:
            dict: Service status including running state and symbol count
        """
        return {
            "running": self.running,
            "symbols_monitored": len(self.symbols),
            "symbols_with_zones": len(self.zones_cache),
            "total_zones": sum(len(zones) for zones in self.zones_cache.values()),
        }
