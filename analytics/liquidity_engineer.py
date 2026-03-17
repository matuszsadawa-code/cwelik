"""
Enhanced Liquidity Engineering Module

Advanced liquidity manipulation detection including:
- Equal highs/lows identification
- Stop cluster detection
- Liquidity sweep detection
- Liquidity void score calculation
- Turtle Soup pattern detection
- Unfilled liquidity pool tracking

Integrates with ICT_Liquidity_Pools for comprehensive liquidity analysis.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class LiquidityPool:
    """Represents a liquidity pool at a specific price level."""
    level: float
    pool_type: str  # EQUAL_HIGHS, EQUAL_LOWS, STOP_CLUSTER
    strength: float  # 0-100
    touches: int  # Number of times price touched this level
    unfilled: bool
    estimated_liquidity: float  # Estimated $ volume
    timestamp: datetime


@dataclass
class LiquiditySweep:
    """Represents a detected liquidity sweep event."""
    pool: LiquidityPool
    sweep_price: float
    reversal_price: float
    volume_spike: float
    confidence: float
    timestamp: datetime
    direction: str  # BULLISH_SWEEP, BEARISH_SWEEP


@dataclass
class TurtleSoupPattern:
    """Represents a Turtle Soup pattern (false breakout)."""
    breakout_level: float
    direction: str  # LONG, SHORT
    confidence: float
    entry_price: float
    timestamp: datetime


@dataclass
class StopCluster:
    """Represents a cluster of stop losses."""
    level: float
    cluster_type: str  # ABOVE_RESISTANCE, BELOW_SUPPORT
    estimated_stops: int
    strength: float  # 0-100


class LiquidityEngineer:
    """
    Enhanced Liquidity Engineering Module.
    
    Detects advanced liquidity manipulation patterns used by market makers
    and institutional traders.
    """
    
    def __init__(self):
        self.liquidity_pools: Dict[str, List[LiquidityPool]] = {}
        self.sweep_history: Dict[str, List[LiquiditySweep]] = {}
        
        # Configuration
        self.equal_level_tolerance_pct = 0.2  # 0.2% tolerance for equal highs/lows
        self.sweep_penetration_pct = 0.3  # Min 0.3% penetration for sweep
        self.sweep_reversal_candles = 3  # Max candles for reversal
        self.sweep_volume_multiplier = 1.5  # Volume must be 1.5x average
        self.void_volume_threshold = 0.5  # <50% average volume = void
        self.turtle_soup_lookback = 20  # 20-day high/low for turtle soup
        self.stop_cluster_radius_pct = 0.5  # Cluster stops within 0.5%
    
    def identify_equal_levels(self, candles: List[Dict], 
                             tolerance_pct: Optional[float] = None) -> List[LiquidityPool]:
        """
        Identify equal highs and equal lows as liquidity pools.
        
        Args:
            candles: OHLCV candle data
            tolerance_pct: Tolerance for "equal" levels (default: 0.2%)
        
        Returns:
            List of identified liquidity pools
        """
        if not candles or len(candles) < 3:
            return []
        
        tolerance = tolerance_pct if tolerance_pct is not None else self.equal_level_tolerance_pct
        pools = []
        
        # Find equal highs
        highs = [c['high'] for c in candles]
        equal_highs = self._find_equal_levels(highs, tolerance, "EQUAL_HIGHS")
        pools.extend(equal_highs)
        
        # Find equal lows
        lows = [c['low'] for c in candles]
        equal_lows = self._find_equal_levels(lows, tolerance, "EQUAL_LOWS")
        pools.extend(equal_lows)
        
        return pools
    
    def _find_equal_levels(self, prices: List[float], tolerance_pct: float, 
                          pool_type: str) -> List[LiquidityPool]:
        """Find equal price levels within tolerance."""
        if len(prices) < 3:
            return []
        
        pools = []
        visited = set()
        
        for i in range(len(prices)):
            if i in visited:
                continue
            
            base_price = prices[i]
            equal_count = 1
            equal_indices = [i]
            
            # Find all prices within tolerance of base_price
            for j in range(i + 1, len(prices)):
                if j in visited:
                    continue
                
                price_diff_pct = abs((prices[j] - base_price) / base_price) * 100
                
                if price_diff_pct <= tolerance_pct:
                    equal_count += 1
                    equal_indices.append(j)
                    visited.add(j)
            
            # If we found at least 2 equal levels, create a pool
            if equal_count >= 2:
                visited.add(i)
                avg_level = sum(prices[idx] for idx in equal_indices) / equal_count
                
                # Calculate strength based on number of touches
                strength = min(100, equal_count * 25)  # 2 touches = 50, 3 = 75, 4+ = 100
                
                pool = LiquidityPool(
                    level=avg_level,
                    pool_type=pool_type,
                    strength=strength,
                    touches=equal_count,
                    unfilled=True,
                    estimated_liquidity=equal_count * 10000,  # Rough estimate
                    timestamp=datetime.utcnow()
                )
                pools.append(pool)
        
        return pools
    
    def detect_stop_clusters(self, price_levels: List[float], 
                           current_price: float) -> List[StopCluster]:
        """
        Detect stop loss clusters above/below key levels.
        
        Args:
            price_levels: Key support/resistance levels
            current_price: Current market price
        
        Returns:
            List of detected stop clusters
        """
        if not price_levels:
            return []
        
        clusters = []
        
        for level in price_levels:
            # Determine if this is above or below current price
            if level > current_price:
                cluster_type = "ABOVE_RESISTANCE"
                # Stops would be above resistance (short stops)
                cluster_level = level * (1 + self.stop_cluster_radius_pct / 100)
            else:
                cluster_type = "BELOW_SUPPORT"
                # Stops would be below support (long stops)
                cluster_level = level * (1 - self.stop_cluster_radius_pct / 100)
            
            # Estimate cluster strength based on distance from current price
            distance_pct = abs((cluster_level - current_price) / current_price) * 100
            
            # Closer clusters are stronger (more likely to be hit)
            if distance_pct < 2.0:
                strength = 90
            elif distance_pct < 5.0:
                strength = 70
            elif distance_pct < 10.0:
                strength = 50
            else:
                strength = 30
            
            cluster = StopCluster(
                level=cluster_level,
                cluster_type=cluster_type,
                estimated_stops=int(strength * 10),  # Rough estimate
                strength=strength
            )
            clusters.append(cluster)
        
        return clusters
    
    def detect_liquidity_sweep(self, candles: List[Dict], 
                              liquidity_pool: LiquidityPool) -> Optional[LiquiditySweep]:
        """
        Detect liquidity sweep: spike above/below level with quick reversal.
        
        Criteria:
        - Price penetrates level by >0.3%
        - Reverses within 1-3 candles
        - Volume spike on penetration
        
        Args:
            candles: Recent candle data
            liquidity_pool: Pool to check for sweep
        
        Returns:
            LiquiditySweep if detected, None otherwise
        """
        if not candles or len(candles) < self.sweep_reversal_candles + 1:
            return None
        
        pool_level = liquidity_pool.level
        is_high_pool = liquidity_pool.pool_type == "EQUAL_HIGHS"
        
        # Calculate average volume
        volumes = [c.get('volume', 0) for c in candles[:-self.sweep_reversal_candles]]
        if not volumes or sum(volumes) == 0:
            return None
        avg_volume = sum(volumes) / len(volumes)
        
        # Check recent candles for sweep pattern
        for i in range(len(candles) - self.sweep_reversal_candles):
            candle = candles[i]
            
            # Check for penetration
            if is_high_pool:
                # Check if high penetrated the pool level
                penetration_pct = ((candle['high'] - pool_level) / pool_level) * 100
                
                if penetration_pct >= self.sweep_penetration_pct:
                    # Check for volume spike
                    volume_ratio = candle.get('volume', 0) / avg_volume if avg_volume > 0 else 0
                    
                    if volume_ratio >= self.sweep_volume_multiplier:
                        # Check for reversal in next candles
                        reversal_found = False
                        reversal_price = None
                        
                        for j in range(i + 1, min(i + 1 + self.sweep_reversal_candles, len(candles))):
                            reversal_candle = candles[j]
                            # Reversal = close back below pool level
                            if reversal_candle['close'] < pool_level:
                                reversal_found = True
                                reversal_price = reversal_candle['close']
                                break
                        
                        if reversal_found:
                            # Calculate confidence based on volume spike and reversal speed
                            reversal_speed = j - i  # Number of candles to reverse
                            confidence = min(100, 
                                           (volume_ratio / self.sweep_volume_multiplier) * 50 +
                                           ((self.sweep_reversal_candles - reversal_speed + 1) / 
                                            self.sweep_reversal_candles) * 50)
                            
                            sweep = LiquiditySweep(
                                pool=liquidity_pool,
                                sweep_price=candle['high'],
                                reversal_price=reversal_price,
                                volume_spike=volume_ratio,
                                confidence=confidence,
                                timestamp=datetime.utcnow(),
                                direction="BULLISH_SWEEP"  # Swept highs, likely reversal down
                            )
                            return sweep
            
            else:  # EQUAL_LOWS
                # Check if low penetrated the pool level
                penetration_pct = ((pool_level - candle['low']) / pool_level) * 100
                
                if penetration_pct >= self.sweep_penetration_pct:
                    # Check for volume spike
                    volume_ratio = candle.get('volume', 0) / avg_volume if avg_volume > 0 else 0
                    
                    if volume_ratio >= self.sweep_volume_multiplier:
                        # Check for reversal in next candles
                        reversal_found = False
                        reversal_price = None
                        
                        for j in range(i + 1, min(i + 1 + self.sweep_reversal_candles, len(candles))):
                            reversal_candle = candles[j]
                            # Reversal = close back above pool level
                            if reversal_candle['close'] > pool_level:
                                reversal_found = True
                                reversal_price = reversal_candle['close']
                                break
                        
                        if reversal_found:
                            # Calculate confidence
                            reversal_speed = j - i
                            confidence = min(100,
                                           (volume_ratio / self.sweep_volume_multiplier) * 50 +
                                           ((self.sweep_reversal_candles - reversal_speed + 1) /
                                            self.sweep_reversal_candles) * 50)
                            
                            sweep = LiquiditySweep(
                                pool=liquidity_pool,
                                sweep_price=candle['low'],
                                reversal_price=reversal_price,
                                volume_spike=volume_ratio,
                                confidence=confidence,
                                timestamp=datetime.utcnow(),
                                direction="BEARISH_SWEEP"  # Swept lows, likely reversal up
                            )
                            return sweep
        
        return None
    
    def calculate_liquidity_void_score(self, candles: List[Dict], 
                                      price_range: Tuple[float, float]) -> float:
        """
        Calculate 0-100 score for areas with low volume (liquidity voids).
        
        Args:
            candles: Candle data
            price_range: (low, high) price range to analyze
        
        Returns:
            Void score (0-100, higher = more void)
        """
        if not candles or len(candles) < 2:
            return 50.0  # Neutral
        
        low_range, high_range = price_range
        
        # Calculate average volume across all candles
        total_volume = sum(c.get('volume', 0) for c in candles)
        if total_volume == 0:
            return 100.0  # Complete void
        avg_volume = total_volume / len(candles)
        
        # Find candles within the price range
        range_candles = []
        for candle in candles:
            # Check if candle overlaps with the range
            if candle['low'] <= high_range and candle['high'] >= low_range:
                range_candles.append(candle)
        
        if not range_candles:
            return 100.0  # No trading in this range = complete void
        
        # Calculate volume in this range
        range_volume = sum(c.get('volume', 0) for c in range_candles)
        range_avg_volume = range_volume / len(range_candles)
        
        # Calculate void score
        volume_ratio = range_avg_volume / avg_volume if avg_volume > 0 else 0
        
        # Invert ratio to get void score (low volume = high void score)
        if volume_ratio >= 1.0:
            void_score = 0.0  # High volume = no void
        elif volume_ratio >= self.void_volume_threshold:
            # Partial void
            void_score = (1.0 - volume_ratio) * 100
        else:
            # Significant void
            void_score = 50 + (self.void_volume_threshold - volume_ratio) / self.void_volume_threshold * 50
        
        return min(100.0, max(0.0, void_score))
    
    def detect_turtle_soup(self, candles: List[Dict], 
                          lookback: Optional[int] = None) -> Optional[TurtleSoupPattern]:
        """
        Detect Turtle Soup: false breakout of 20-day high/low.
        
        Args:
            candles: Candle data
            lookback: Lookback period (default: 20)
        
        Returns:
            TurtleSoupPattern if detected, None otherwise
        """
        lookback_period = lookback if lookback is not None else self.turtle_soup_lookback
        
        if not candles or len(candles) < lookback_period + 2:
            return None
        
        # Get the lookback period
        lookback_candles = candles[:-2][-lookback_period:]
        
        # Find 20-day high and low
        period_high = max(c['high'] for c in lookback_candles)
        period_low = min(c['low'] for c in lookback_candles)
        
        # Check last 2 candles for false breakout
        breakout_candle = candles[-2]
        reversal_candle = candles[-1]
        
        # Check for false breakout above (bearish turtle soup)
        if breakout_candle['high'] > period_high:
            # Check if it reversed (closed back below)
            if reversal_candle['close'] < period_high:
                # Calculate confidence based on reversal strength
                breakout_distance = breakout_candle['high'] - period_high
                reversal_distance = period_high - reversal_candle['close']
                
                confidence = min(100, (reversal_distance / breakout_distance) * 100 if breakout_distance > 0 else 50)
                
                pattern = TurtleSoupPattern(
                    breakout_level=period_high,
                    direction="SHORT",  # False breakout up = short opportunity
                    confidence=confidence,
                    entry_price=reversal_candle['close'],
                    timestamp=datetime.utcnow()
                )
                return pattern
        
        # Check for false breakout below (bullish turtle soup)
        if breakout_candle['low'] < period_low:
            # Check if it reversed (closed back above)
            if reversal_candle['close'] > period_low:
                # Calculate confidence
                breakout_distance = period_low - breakout_candle['low']
                reversal_distance = reversal_candle['close'] - period_low
                
                confidence = min(100, (reversal_distance / breakout_distance) * 100 if breakout_distance > 0 else 50)
                
                pattern = TurtleSoupPattern(
                    breakout_level=period_low,
                    direction="LONG",  # False breakout down = long opportunity
                    confidence=confidence,
                    entry_price=reversal_candle['close'],
                    timestamp=datetime.utcnow()
                )
                return pattern
        
        return None
    
    def track_unfilled_pools(self, symbol: str, current_price: float) -> List[LiquidityPool]:
        """
        Track unfilled liquidity pools as potential price targets.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
        
        Returns:
            List of unfilled liquidity pools
        """
        if symbol not in self.liquidity_pools:
            return []
        
        unfilled = []
        
        for pool in self.liquidity_pools[symbol]:
            if not pool.unfilled:
                continue
            
            # Check if price has reached this pool
            distance_pct = abs((pool.level - current_price) / current_price) * 100
            
            # If price is within 0.5% of pool, mark as filled
            if distance_pct < 0.5:
                pool.unfilled = False
            else:
                unfilled.append(pool)
        
        return unfilled
    
    def analyze(self, candles: List[Dict], symbol: str, 
               current_price: float, ict_trend: Optional[str] = None) -> Dict:
        """
        Comprehensive liquidity engineering analysis.
        
        Args:
            candles: Candle data
            symbol: Trading symbol
            current_price: Current market price
            ict_trend: ICT trend direction (for sweep alignment check)
        
        Returns:
            Dictionary with complete analysis results
        """
        if not candles:
            return {
                'pools': [],
                'sweeps': [],
                'turtle_soup': None,
                'unfilled_pools': [],
                'confidence_boost': 0,
                'analysis_complete': False
            }
        
        # Identify equal highs/lows
        pools = self.identify_equal_levels(candles)
        
        # Store pools for tracking
        if symbol not in self.liquidity_pools:
            self.liquidity_pools[symbol] = []
        self.liquidity_pools[symbol].extend(pools)
        
        # Detect liquidity sweeps
        sweeps = []
        for pool in pools:
            sweep = self.detect_liquidity_sweep(candles, pool)
            if sweep:
                sweeps.append(sweep)
        
        # Store sweep history
        if symbol not in self.sweep_history:
            self.sweep_history[symbol] = []
        self.sweep_history[symbol].extend(sweeps)
        
        # Detect turtle soup pattern
        turtle_soup = self.detect_turtle_soup(candles)
        
        # Track unfilled pools
        unfilled_pools = self.track_unfilled_pools(symbol, current_price)
        
        # Calculate confidence boost
        confidence_boost = 0
        
        # Check for liquidity sweep aligned with ICT trend
        if sweeps and ict_trend:
            for sweep in sweeps:
                # Bullish sweep (swept highs, reversal down) aligns with SHORT trend
                if sweep.direction == "BULLISH_SWEEP" and ict_trend == "SHORT":
                    if sweep.confidence > 70:
                        confidence_boost = 18
                        break
                
                # Bearish sweep (swept lows, reversal up) aligns with LONG trend
                elif sweep.direction == "BEARISH_SWEEP" and ict_trend == "LONG":
                    if sweep.confidence > 70:
                        confidence_boost = 18
                        break
        
        return {
            'pools': pools,
            'sweeps': sweeps,
            'turtle_soup': turtle_soup,
            'unfilled_pools': unfilled_pools,
            'stop_clusters': self.detect_stop_clusters(
                [p.level for p in pools], current_price
            ),
            'confidence_boost': confidence_boost,
            'analysis_complete': True
        }
