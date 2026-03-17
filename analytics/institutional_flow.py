"""
Institutional Order Flow Patterns Detection

Implements detection of characteristic institutional execution patterns:
- Iceberg execution (consistent trade sizes, regular intervals)
- TWAP/VWAP algorithmic execution
- Layering (building positions at multiple levels)
- Sweep orders (aggressive multi-level hits)
- Institutional activity score calculation (0-100)

Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque
import statistics

try:
    from utils.logger import get_logger
    log = get_logger("analytics.institutional_flow")
except ImportError:
    # Fallback for standalone testing
    import logging
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("analytics.institutional_flow")


@dataclass
class InstitutionalPattern:
    """Detected institutional pattern."""
    pattern_type: str  # ICEBERG, TWAP, VWAP, LAYERING, SWEEP
    direction: str  # BUY, SELL
    confidence: float  # 0-1
    volume: float
    duration_seconds: float
    timestamp: datetime


@dataclass
class IcebergExecution:
    """Iceberg execution pattern."""
    avg_trade_size: float
    trade_count: int
    total_volume: float
    side: str  # BUY, SELL
    confidence: float
    size_consistency: float  # 0-1
    interval_consistency: float  # 0-1


@dataclass
class AlgoExecution:
    """TWAP/VWAP algorithmic execution."""
    algo_type: str  # TWAP, VWAP
    participation_rate: float  # % of market volume
    total_volume: float
    side: str  # BUY, SELL
    confidence: float
    vwap_deviation: Optional[float] = None  # For VWAP algo


@dataclass
class LayeringPattern:
    """Layering pattern (orders at multiple levels)."""
    price_levels: List[float]
    total_volume: float
    side: str  # BUY, SELL
    confidence: float
    level_consistency: float  # 0-1


@dataclass
class SweepOrder:
    """Sweep order pattern."""
    levels_swept: int
    total_volume: float
    avg_price: float
    side: str  # BUY, SELL
    confidence: float
    sweep_speed: float  # seconds per level


class InstitutionalFlowDetector:
    """Detect characteristic institutional execution patterns."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize detector with configuration."""
        self.config = config or {}
        
        # Configuration parameters
        self.iceberg_min_trades = self.config.get("iceberg_min_trades", 10)
        self.iceberg_size_consistency = self.config.get("iceberg_size_consistency", 0.8)
        self.twap_interval_consistency = self.config.get("twap_interval_consistency", 0.7)
        self.vwap_price_tolerance_pct = self.config.get("vwap_price_tolerance_pct", 0.1)
        self.layering_min_levels = self.config.get("layering_min_levels", 3)
        self.sweep_min_levels = self.config.get("sweep_min_levels", 3)
        self.high_activity_threshold = self.config.get("high_activity_threshold", 80)
        
        # History tracking
        self.pattern_history: Dict[str, deque] = {}  # symbol -> deque of patterns
        self.max_history_length = 100
        
        log.info(
            f"InstitutionalFlowDetector initialized "
            f"(iceberg_min={self.iceberg_min_trades}, "
            f"layering_min={self.layering_min_levels})"
        )

    
    def detect_iceberg_execution(self, trades: List[Dict]) -> Optional[IcebergExecution]:
        """
        Detect iceberg execution pattern.
        
        Criteria:
        - Consistent trade sizes (80%+ similarity)
        - Same side (all BUY or all SELL)
        - Regular intervals
        - Large cumulative volume
        
        Args:
            trades: List of recent trades
            
        Returns:
            IcebergExecution if detected, None otherwise
            
        Validates: Requirement 8.1
        """
        if len(trades) < self.iceberg_min_trades:
            return None
        
        # Group by side
        buy_trades = [t for t in trades if t.get("side") in ["BUY", "Buy"]]
        sell_trades = [t for t in trades if t.get("side") in ["SELL", "Sell"]]
        
        # Check both sides
        for side, side_trades in [("BUY", buy_trades), ("SELL", sell_trades)]:
            if len(side_trades) < self.iceberg_min_trades:
                continue
            
            # Calculate trade sizes
            sizes = [t.get("size", 0) for t in side_trades]
            if not sizes:
                continue
            
            avg_size = statistics.mean(sizes)
            if avg_size == 0:
                continue
            
            # Calculate size consistency (coefficient of variation)
            std_dev = statistics.stdev(sizes) if len(sizes) > 1 else 0
            cv = std_dev / avg_size if avg_size > 0 else 1.0
            size_consistency = max(0, 1 - cv)  # Lower CV = higher consistency
            
            # Check if sizes are consistent enough
            if size_consistency < self.iceberg_size_consistency:
                continue
            
            # Calculate time intervals
            timestamps = [t.get("time", 0) for t in side_trades]
            if len(timestamps) < 2:
                continue
            
            intervals = []
            for i in range(1, len(timestamps)):
                interval = (timestamps[i] - timestamps[i-1]) / 1000  # Convert to seconds
                if interval > 0:
                    intervals.append(interval)
            
            if not intervals:
                continue
            
            # Calculate interval consistency
            avg_interval = statistics.mean(intervals)
            if avg_interval == 0:
                interval_consistency = 0
            else:
                interval_std = statistics.stdev(intervals) if len(intervals) > 1 else 0
                interval_cv = interval_std / avg_interval
                interval_consistency = max(0, 1 - interval_cv)
            
            # Calculate total volume
            total_volume = sum(sizes)
            
            # Calculate confidence based on consistency metrics
            confidence = (size_consistency * 0.6 + interval_consistency * 0.4)
            
            # Require minimum confidence
            if confidence >= 0.6:
                iceberg = IcebergExecution(
                    avg_trade_size=avg_size,
                    trade_count=len(side_trades),
                    total_volume=total_volume,
                    side=side,
                    confidence=confidence,
                    size_consistency=size_consistency,
                    interval_consistency=interval_consistency
                )
                
                log.info(
                    f"[ICEBERG] Detected {side} execution: "
                    f"{len(side_trades)} trades, avg size {avg_size:.2f}, "
                    f"total vol {total_volume:.2f}, "
                    f"size consistency {size_consistency:.2%}, "
                    f"interval consistency {interval_consistency:.2%}, "
                    f"confidence {confidence:.2%}"
                )
                
                return iceberg
        
        return None

    
    def detect_twap_vwap_execution(self, trades: List[Dict], candles: List[Dict]) -> Optional[AlgoExecution]:
        """
        Detect TWAP/VWAP algorithmic execution.
        
        Criteria:
        - TWAP: Trades distributed evenly over time (70%+ consistency)
        - VWAP: Trades concentrated near VWAP (within 0.1%)
        - Consistent participation rate
        
        Args:
            trades: List of recent trades
            candles: Recent candle data for VWAP calculation
            
        Returns:
            AlgoExecution if detected, None otherwise
            
        Validates: Requirement 8.2
        """
        if len(trades) < self.iceberg_min_trades or not candles:
            return None
        
        # Calculate VWAP from candles
        vwap = self._calculate_vwap(candles)
        if vwap == 0:
            return None
        
        # Group by side
        buy_trades = [t for t in trades if t.get("side") in ["BUY", "Buy"]]
        sell_trades = [t for t in trades if t.get("side") in ["SELL", "Sell"]]
        
        for side, side_trades in [("BUY", buy_trades), ("SELL", sell_trades)]:
            if len(side_trades) < self.iceberg_min_trades:
                continue
            
            # Check for TWAP pattern (even time distribution)
            timestamps = [t.get("time", 0) for t in side_trades]
            if len(timestamps) < 2:
                continue
            
            # Calculate time intervals
            intervals = []
            for i in range(1, len(timestamps)):
                interval = (timestamps[i] - timestamps[i-1]) / 1000
                if interval > 0:
                    intervals.append(interval)
            
            if not intervals:
                continue
            
            avg_interval = statistics.mean(intervals)
            interval_std = statistics.stdev(intervals) if len(intervals) > 1 else 0
            interval_cv = interval_std / avg_interval if avg_interval > 0 else 1.0
            interval_consistency = max(0, 1 - interval_cv)
            
            # Check for VWAP pattern (prices near VWAP)
            prices = [t.get("price", 0) for t in side_trades]
            vwap_deviations = [abs(p - vwap) / vwap * 100 for p in prices if p > 0]
            avg_vwap_deviation = statistics.mean(vwap_deviations) if vwap_deviations else 100
            
            # Determine algo type
            is_twap = interval_consistency >= self.twap_interval_consistency
            is_vwap = avg_vwap_deviation <= self.vwap_price_tolerance_pct
            
            if is_twap or is_vwap:
                total_volume = sum(t.get("size", 0) for t in side_trades)
                
                # Calculate participation rate (vs total market volume)
                total_market_volume = sum(t.get("size", 0) for t in trades)
                participation_rate = (total_volume / total_market_volume * 100) if total_market_volume > 0 else 0
                
                # Calculate confidence
                if is_twap and is_vwap:
                    algo_type = "VWAP"  # VWAP is more specific
                    confidence = min(0.9, 0.6 + interval_consistency * 0.2 + (1 - avg_vwap_deviation / 10) * 0.2)
                elif is_twap:
                    algo_type = "TWAP"
                    confidence = min(0.85, 0.6 + interval_consistency * 0.25)
                else:
                    algo_type = "VWAP"
                    confidence = min(0.85, 0.6 + (1 - avg_vwap_deviation / 10) * 0.25)
                
                algo = AlgoExecution(
                    algo_type=algo_type,
                    participation_rate=participation_rate,
                    total_volume=total_volume,
                    side=side,
                    confidence=confidence,
                    vwap_deviation=avg_vwap_deviation if is_vwap else None
                )
                
                log.info(
                    f"[{algo_type}] Detected {side} algo execution: "
                    f"{len(side_trades)} trades, vol {total_volume:.2f}, "
                    f"participation {participation_rate:.1f}%, "
                    f"confidence {confidence:.2%}"
                )
                
                return algo
        
        return None

    
    def detect_layering(self, orderbook_snapshots: List[Dict]) -> Optional[LayeringPattern]:
        """
        Detect layering (building position at multiple levels).
        
        Criteria:
        - Orders at multiple price levels (3+)
        - Similar sizes across levels
        - Gradual accumulation/distribution
        
        Args:
            orderbook_snapshots: Recent orderbook snapshots
            
        Returns:
            LayeringPattern if detected, None otherwise
            
        Validates: Requirement 8.3
        """
        if len(orderbook_snapshots) < 3:
            return None
        
        # Analyze most recent snapshot
        latest_ob = orderbook_snapshots[-1]
        bids = latest_ob.get("bids", [])[:10]
        asks = latest_ob.get("asks", [])[:10]
        
        # Check both sides
        for side, levels in [("BUY", bids), ("SELL", asks)]:
            if len(levels) < self.layering_min_levels:
                continue
            
            # Extract prices and sizes
            price_size_pairs = []
            for level in levels:
                if isinstance(level, dict):
                    price = level.get("price", 0)
                    size = level.get("size", 0)
                elif isinstance(level, (list, tuple)) and len(level) >= 2:
                    price = level[0]
                    size = level[1]
                else:
                    continue
                
                if price > 0 and size > 0:
                    price_size_pairs.append((price, size))
            
            if len(price_size_pairs) < self.layering_min_levels:
                continue
            
            # Calculate size consistency across levels
            sizes = [size for _, size in price_size_pairs]
            avg_size = statistics.mean(sizes)
            
            if avg_size == 0:
                continue
            
            std_dev = statistics.stdev(sizes) if len(sizes) > 1 else 0
            cv = std_dev / avg_size
            level_consistency = max(0, 1 - cv)
            
            # Require consistent sizes (similar order sizes at multiple levels)
            if level_consistency >= 0.6:
                prices = [price for price, _ in price_size_pairs]
                total_volume = sum(sizes)
                
                confidence = min(0.9, 0.6 + level_consistency * 0.3)
                
                layering = LayeringPattern(
                    price_levels=prices,
                    total_volume=total_volume,
                    side=side,
                    confidence=confidence,
                    level_consistency=level_consistency
                )
                
                log.info(
                    f"[LAYERING] Detected {side} layering: "
                    f"{len(prices)} levels, total vol {total_volume:.2f}, "
                    f"consistency {level_consistency:.2%}, "
                    f"confidence {confidence:.2%}"
                )
                
                return layering
        
        return None

    
    def detect_sweep_orders(self, trades: List[Dict], orderbook: Dict) -> Optional[SweepOrder]:
        """
        Detect aggressive sweep orders eating through order book.
        
        Criteria:
        - Multiple price levels hit in quick succession (3+)
        - Large volume
        - Market orders (aggressive)
        
        Args:
            trades: Recent trades
            orderbook: Current orderbook
            
        Returns:
            SweepOrder if detected, None otherwise
            
        Validates: Requirement 8.4
        """
        if len(trades) < self.sweep_min_levels:
            return None
        
        # Look for rapid price level changes in recent trades
        # Group trades by side
        buy_trades = [t for t in trades if t.get("side") in ["BUY", "Buy"]]
        sell_trades = [t for t in trades if t.get("side") in ["SELL", "Sell"]]
        
        for side, side_trades in [("BUY", buy_trades), ("SELL", sell_trades)]:
            if len(side_trades) < self.sweep_min_levels:
                continue
            
            # Get unique price levels hit
            prices = sorted(set(t.get("price", 0) for t in side_trades if t.get("price", 0) > 0))
            
            if len(prices) < self.sweep_min_levels:
                continue
            
            # Calculate time span
            timestamps = [t.get("time", 0) for t in side_trades]
            if not timestamps:
                continue
            
            time_span = (max(timestamps) - min(timestamps)) / 1000  # seconds
            
            # Calculate sweep speed (seconds per level)
            sweep_speed = time_span / len(prices) if len(prices) > 0 else 0
            
            # Fast sweeps are more indicative of institutional activity
            # Typical sweep: <1 second per level
            if sweep_speed > 2.0:  # Too slow
                continue
            
            # Calculate total volume
            total_volume = sum(t.get("size", 0) for t in side_trades)
            avg_price = statistics.mean(prices)
            
            # Calculate confidence based on speed and volume
            speed_score = max(0, 1 - sweep_speed / 2.0)  # Faster = higher score
            volume_score = min(1.0, total_volume / (avg_price * 10))  # Normalize by price
            confidence = min(0.9, 0.6 + speed_score * 0.2 + volume_score * 0.2)
            
            sweep = SweepOrder(
                levels_swept=len(prices),
                total_volume=total_volume,
                avg_price=avg_price,
                side=side,
                confidence=confidence,
                sweep_speed=sweep_speed
            )
            
            log.info(
                f"[SWEEP] Detected {side} sweep order: "
                f"{len(prices)} levels, vol {total_volume:.2f}, "
                f"avg price ${avg_price:.2f}, "
                f"speed {sweep_speed:.2f}s/level, "
                f"confidence {confidence:.2%}"
            )
            
            return sweep
        
        return None

    
    def calculate_institutional_activity_score(self, patterns: List[InstitutionalPattern]) -> float:
        """
        Calculate 0-100 score for institutional activity level.
        
        Score calculation:
        - Each pattern contributes based on confidence
        - Multiple patterns increase score
        - Recent patterns weighted more heavily
        
        Args:
            patterns: List of detected patterns
            
        Returns:
            Institutional activity score (0-100)
            
        Validates: Requirement 8.6
        """
        if not patterns:
            return 0.0
        
        # Weight patterns by recency (exponential decay)
        now = datetime.utcnow()
        weighted_scores = []
        
        for pattern in patterns:
            age_seconds = (now - pattern.timestamp).total_seconds()
            age_minutes = age_seconds / 60
            
            # Decay factor: 0.95^minutes (5% decay per minute)
            decay = 0.95 ** age_minutes
            
            # Pattern base score (0-100)
            base_score = pattern.confidence * 100
            
            # Pattern type multiplier
            type_multipliers = {
                "ICEBERG": 1.2,  # Strong institutional signal
                "TWAP": 1.1,
                "VWAP": 1.1,
                "LAYERING": 1.0,
                "SWEEP": 1.3,  # Very strong signal
            }
            multiplier = type_multipliers.get(pattern.pattern_type, 1.0)
            
            weighted_score = base_score * multiplier * decay
            weighted_scores.append(weighted_score)
        
        # Aggregate score with diminishing returns
        if not weighted_scores:
            return 0.0
        
        # Use logarithmic aggregation to prevent score inflation
        total_score = sum(weighted_scores)
        pattern_count_bonus = min(20, len(patterns) * 5)  # Max +20 for multiple patterns
        
        final_score = min(100, total_score / len(patterns) + pattern_count_bonus)
        
        return final_score

    
    def analyze_comprehensive(self, symbol: str, trades: List[Dict], 
                            orderbook: Dict, orderbook_snapshots: List[Dict],
                            candles: List[Dict]) -> Dict:
        """
        Comprehensive institutional flow analysis.
        
        Combines all detection methods and generates final assessment.
        
        Args:
            symbol: Trading symbol
            trades: Recent trades
            orderbook: Current orderbook
            orderbook_snapshots: Recent orderbook snapshots
            candles: Recent candle data
            
        Returns:
            Dict with comprehensive analysis results
            
        Validates: Requirements 8.1-8.8
        """
        # Initialize pattern history for this symbol
        if symbol not in self.pattern_history:
            self.pattern_history[symbol] = deque(maxlen=self.max_history_length)
        
        patterns = []
        now = datetime.utcnow()
        
        # 1. Detect iceberg execution
        iceberg = self.detect_iceberg_execution(trades)
        if iceberg:
            pattern = InstitutionalPattern(
                pattern_type="ICEBERG",
                direction=iceberg.side,
                confidence=iceberg.confidence,
                volume=iceberg.total_volume,
                duration_seconds=0,  # Not time-based
                timestamp=now
            )
            patterns.append(pattern)
            self.pattern_history[symbol].append(pattern)
        
        # 2. Detect TWAP/VWAP execution
        algo = self.detect_twap_vwap_execution(trades, candles)
        if algo:
            pattern = InstitutionalPattern(
                pattern_type=algo.algo_type,
                direction=algo.side,
                confidence=algo.confidence,
                volume=algo.total_volume,
                duration_seconds=0,
                timestamp=now
            )
            patterns.append(pattern)
            self.pattern_history[symbol].append(pattern)
        
        # 3. Detect layering
        layering = self.detect_layering(orderbook_snapshots)
        if layering:
            pattern = InstitutionalPattern(
                pattern_type="LAYERING",
                direction=layering.side,
                confidence=layering.confidence,
                volume=layering.total_volume,
                duration_seconds=0,
                timestamp=now
            )
            patterns.append(pattern)
            self.pattern_history[symbol].append(pattern)
        
        # 4. Detect sweep orders
        sweep = self.detect_sweep_orders(trades, orderbook)
        if sweep:
            pattern = InstitutionalPattern(
                pattern_type="SWEEP",
                direction=sweep.side,
                confidence=sweep.confidence,
                volume=sweep.total_volume,
                duration_seconds=0,
                timestamp=now
            )
            patterns.append(pattern)
            self.pattern_history[symbol].append(pattern)
        
        # 5. Calculate institutional activity score
        # Include recent patterns from history
        recent_cutoff = now - timedelta(minutes=30)
        recent_patterns = [
            p for p in self.pattern_history[symbol]
            if p.timestamp >= recent_cutoff
        ]
        
        activity_score = self.calculate_institutional_activity_score(recent_patterns)
        
        # 6. Determine overall signal
        if not patterns:
            signal = "NEUTRAL"
            confidence = 0.0
        else:
            # Majority vote weighted by confidence
            buy_score = sum(p.confidence for p in patterns if p.direction == "BUY")
            sell_score = sum(p.confidence for p in patterns if p.direction == "SELL")
            
            if buy_score > sell_score * 1.2:  # 20% threshold
                signal = "LONG"
                confidence = buy_score / len(patterns)
            elif sell_score > buy_score * 1.2:
                signal = "SHORT"
                confidence = sell_score / len(patterns)
            else:
                signal = "NEUTRAL"
                confidence = 0.5
        
        result = {
            "signal": signal,
            "confidence": confidence,
            "institutional_activity_score": activity_score,
            "patterns_detected": len(patterns),
            "pattern_types": [p.pattern_type for p in patterns],
            "iceberg": {
                "detected": iceberg is not None,
                "side": iceberg.side if iceberg else None,
                "confidence": iceberg.confidence if iceberg else 0,
                "volume": iceberg.total_volume if iceberg else 0,
                "trade_count": iceberg.trade_count if iceberg else 0,
            },
            "algo_execution": {
                "detected": algo is not None,
                "type": algo.algo_type if algo else None,
                "side": algo.side if algo else None,
                "confidence": algo.confidence if algo else 0,
                "volume": algo.total_volume if algo else 0,
                "participation_rate": algo.participation_rate if algo else 0,
            },
            "layering": {
                "detected": layering is not None,
                "side": layering.side if layering else None,
                "confidence": layering.confidence if layering else 0,
                "levels": len(layering.price_levels) if layering else 0,
                "volume": layering.total_volume if layering else 0,
            },
            "sweep": {
                "detected": sweep is not None,
                "side": sweep.side if sweep else None,
                "confidence": sweep.confidence if sweep else 0,
                "levels_swept": sweep.levels_swept if sweep else 0,
                "volume": sweep.total_volume if sweep else 0,
            },
        }
        
        return result

    
    def _calculate_vwap(self, candles: List[Dict]) -> float:
        """Calculate VWAP from candles."""
        if not candles:
            return 0.0
        
        total_pv = 0.0
        total_volume = 0.0
        
        for candle in candles:
            typical_price = (candle.get("high", 0) + candle.get("low", 0) + candle.get("close", 0)) / 3
            volume = candle.get("volume", 0)
            
            total_pv += typical_price * volume
            total_volume += volume
        
        return total_pv / total_volume if total_volume > 0 else 0.0
