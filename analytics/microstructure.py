"""
Market Microstructure Analysis

Implements market microstructure analysis including:
- Effective spread calculation
- Spread widening detection (>2x average spread)
- Price impact calculation for different order sizes
- Order flow classification (TOXIC vs NOISE)
- Order Flow Toxicity Score calculation (0-100)
- Quote stuffing detection (>100 updates/sec)

Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 17.8
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque
import statistics

from utils.logger import get_logger

log = get_logger("analytics.microstructure")


@dataclass
class SpreadMeasurement:
    """Spread measurement data."""
    bid_ask_spread: float
    effective_spread: float
    timestamp: datetime


@dataclass
class SpreadWidening:
    """Spread widening event."""
    current_spread: float
    avg_spread: float
    widening_ratio: float
    duration_minutes: float
    timestamp: datetime


@dataclass
class PriceImpact:
    """Price impact estimation."""
    order_size: float
    estimated_slippage_pct: float
    levels_consumed: int
    avg_execution_price: float


@dataclass
class OrderFlowClassification:
    """Order flow classification result."""
    flow_type: str  # TOXIC, NOISE, MIXED
    toxicity_score: float  # 0-100
    informed_volume_pct: float
    characteristics: List[str]


@dataclass
class QuoteStuffing:
    """Quote stuffing detection."""
    updates_per_second: float
    cancel_rate: float
    duration_seconds: float
    timestamp: datetime


class MicrostructureAnalyzer:
    """Market microstructure analysis engine."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize analyzer with configuration."""
        self.config = config or {}
        
        # Configuration parameters
        self.spread_widening_threshold = self.config.get("spread_widening_threshold", 2.0)
        self.spread_widening_duration_min = self.config.get("spread_widening_duration_min", 5)
        self.toxic_flow_threshold = self.config.get("toxic_flow_threshold", 70)
        self.quote_stuffing_threshold = self.config.get("quote_stuffing_threshold", 100)
        self.price_impact_levels = self.config.get("price_impact_levels", [1000, 5000, 10000, 50000])
        
        # History tracking
        self.spread_history: Dict[str, deque] = {}  # symbol -> deque of SpreadMeasurement
        self.orderbook_update_history: Dict[str, deque] = {}  # symbol -> deque of update timestamps
        self.max_history_length = 1000
        
        log.info(
            f"MicrostructureAnalyzer initialized "
            f"(spread_threshold={self.spread_widening_threshold}x, "
            f"toxic_threshold={self.toxic_flow_threshold})"
        )

    
    def calculate_effective_spread(self, trades: List[Dict], mid_price: float) -> float:
        """
        Calculate effective spread.
        
        Effective Spread = 2 * |Trade Price - Mid Price|
        
        Args:
            trades: List of recent trades
            mid_price: Current mid price
            
        Returns:
            Average effective spread
            
        Validates: Requirement 17.1
        """
        if not trades or mid_price == 0:
            return 0.0
        
        effective_spreads = []
        
        for trade in trades:
            trade_price = trade.get("price", 0)
            if trade_price > 0:
                # Effective spread = 2 * |trade_price - mid_price|
                eff_spread = 2 * abs(trade_price - mid_price)
                effective_spreads.append(eff_spread)
        
        if not effective_spreads:
            return 0.0
        
        avg_effective_spread = sum(effective_spreads) / len(effective_spreads)
        return avg_effective_spread

    
    def detect_spread_widening(self, symbol: str, current_spread: float) -> Optional[SpreadWidening]:
        """
        Detect spread widening (sign of uncertainty).
        
        Criteria:
        - Spread >2x average
        - Sustained for >5 minutes
        
        Args:
            symbol: Trading symbol
            current_spread: Current bid-ask spread
            
        Returns:
            SpreadWidening if detected, None otherwise
            
        Validates: Requirement 17.2
        """
        # Initialize history for this symbol
        if symbol not in self.spread_history:
            self.spread_history[symbol] = deque(maxlen=self.max_history_length)
        
        history = self.spread_history[symbol]
        now = datetime.utcnow()
        
        # Add current measurement
        measurement = SpreadMeasurement(
            bid_ask_spread=current_spread,
            effective_spread=0.0,  # Will be calculated separately
            timestamp=now
        )
        history.append(measurement)
        
        # Need sufficient history
        if len(history) < 10:
            return None
        
        # Calculate average spread over last 30 minutes
        cutoff = now - timedelta(minutes=30)
        recent_spreads = [
            m.bid_ask_spread for m in history
            if m.timestamp > cutoff and m.bid_ask_spread > 0
        ]
        
        if not recent_spreads:
            return None
        
        avg_spread = sum(recent_spreads) / len(recent_spreads)
        
        if avg_spread == 0:
            return None
        
        widening_ratio = current_spread / avg_spread
        
        # Check if spread is widened
        if widening_ratio >= self.spread_widening_threshold:
            # Check duration of widening
            widening_start = None
            for m in reversed(list(history)):
                if m.bid_ask_spread / avg_spread >= self.spread_widening_threshold:
                    widening_start = m.timestamp
                else:
                    break
            
            if widening_start:
                duration_minutes = (now - widening_start).total_seconds() / 60
                
                if duration_minutes >= self.spread_widening_duration_min:
                    widening = SpreadWidening(
                        current_spread=current_spread,
                        avg_spread=avg_spread,
                        widening_ratio=widening_ratio,
                        duration_minutes=duration_minutes,
                        timestamp=now
                    )
                    
                    log.warning(
                        f"[SPREAD WIDENING] {symbol}: "
                        f"${current_spread:.4f} vs avg ${avg_spread:.4f} "
                        f"({widening_ratio:.1f}x) for {duration_minutes:.1f} min"
                    )
                    
                    return widening
        
        return None

    
    def calculate_price_impact(self, order_size: float, orderbook: Dict, side: str = "BUY") -> PriceImpact:
        """
        Calculate price impact for different order sizes.
        
        Args:
            order_size: Order size in base currency
            orderbook: Current order book
            side: Order side (BUY or SELL)
            
        Returns:
            PriceImpact with estimated slippage
            
        Validates: Requirement 17.3
        """
        if side == "BUY":
            levels = orderbook.get("asks", [])
        else:
            levels = orderbook.get("bids", [])
        
        if not levels:
            return PriceImpact(
                order_size=order_size,
                estimated_slippage_pct=0.0,
                levels_consumed=0,
                avg_execution_price=0.0
            )
        
        # Get best price
        if isinstance(levels[0], dict):
            best_price = levels[0].get("price", 0)
        elif isinstance(levels[0], (list, tuple)) and len(levels[0]) >= 2:
            best_price = levels[0][0]
        else:
            best_price = 0
        
        if best_price == 0:
            return PriceImpact(
                order_size=order_size,
                estimated_slippage_pct=0.0,
                levels_consumed=0,
                avg_execution_price=0.0
            )
        
        # Simulate order execution
        remaining_size = order_size
        total_cost = 0.0
        levels_consumed = 0
        
        for level in levels:
            if remaining_size <= 0:
                break
            
            if isinstance(level, dict):
                price = level.get("price", 0)
                size = level.get("size", 0)
            elif isinstance(level, (list, tuple)) and len(level) >= 2:
                price = level[0]
                size = level[1]
            else:
                continue
            
            if price == 0 or size == 0:
                continue
            
            # Take from this level
            take_size = min(remaining_size, size)
            total_cost += take_size * price
            remaining_size -= take_size
            levels_consumed += 1
        
        # Calculate average execution price
        if order_size > remaining_size:
            filled_size = order_size - remaining_size
            avg_execution_price = total_cost / filled_size
            slippage_pct = abs(avg_execution_price - best_price) / best_price * 100
        else:
            # Could not fill entire order
            avg_execution_price = 0.0
            slippage_pct = 100.0  # Extreme slippage
        
        return PriceImpact(
            order_size=order_size,
            estimated_slippage_pct=slippage_pct,
            levels_consumed=levels_consumed,
            avg_execution_price=avg_execution_price
        )

    
    def classify_order_flow(self, trades: List[Dict], orderbook: Dict) -> OrderFlowClassification:
        """
        Classify order flow as toxic (informed) or noise (uninformed).
        
        Toxic flow indicators:
        - Large trades
        - Aggressive execution (market orders)
        - Directional persistence
        - Price impact
        
        Args:
            trades: Recent trades
            orderbook: Current order book
            
        Returns:
            OrderFlowClassification
            
        Validates: Requirement 17.4
        """
        if not trades:
            return OrderFlowClassification(
                flow_type="UNKNOWN",
                toxicity_score=50.0,
                informed_volume_pct=0.0,
                characteristics=[]
            )
        
        # Calculate average trade size
        trade_sizes = [t.get("size", 0) for t in trades]
        avg_size = sum(trade_sizes) / len(trade_sizes) if trade_sizes else 0
        
        # Analyze characteristics
        characteristics = []
        toxicity_indicators = []
        
        # 1. Large trade detection (>3x average)
        large_trades = [t for t in trades if t.get("size", 0) > avg_size * 3]
        large_trade_volume = sum(t.get("size", 0) for t in large_trades)
        total_volume = sum(trade_sizes)
        
        if total_volume > 0:
            large_trade_pct = large_trade_volume / total_volume * 100
            if large_trade_pct > 30:
                characteristics.append("LARGE_TRADES")
                toxicity_indicators.append(min(large_trade_pct / 2, 30))  # Max 30 points
        
        # 2. Directional persistence
        buy_volume = sum(t.get("size", 0) for t in trades if t.get("side") == "Buy")
        sell_volume = sum(t.get("size", 0) for t in trades if t.get("side") == "Sell")
        
        if total_volume > 0:
            imbalance = abs(buy_volume - sell_volume) / total_volume * 100
            if imbalance > 60:
                characteristics.append("DIRECTIONAL")
                toxicity_indicators.append(min(imbalance / 2, 30))  # Max 30 points
        
        # 3. Aggressive execution (check if trades are taking liquidity)
        # Trades at ask = aggressive buy, trades at bid = aggressive sell
        if orderbook:
            bids = orderbook.get("bids", [])
            asks = orderbook.get("asks", [])
            
            if bids and asks:
                if isinstance(bids[0], dict):
                    best_bid = bids[0].get("price", 0)
                elif isinstance(bids[0], (list, tuple)) and len(bids[0]) >= 2:
                    best_bid = bids[0][0]
                else:
                    best_bid = 0
                
                if isinstance(asks[0], dict):
                    best_ask = asks[0].get("price", 0)
                elif isinstance(asks[0], (list, tuple)) and len(asks[0]) >= 2:
                    best_ask = asks[0][0]
                else:
                    best_ask = 0
                
                if best_bid > 0 and best_ask > 0:
                    aggressive_trades = 0
                    for t in trades:
                        price = t.get("price", 0)
                        # Trade at ask or above = aggressive buy
                        # Trade at bid or below = aggressive sell
                        if price >= best_ask or price <= best_bid:
                            aggressive_trades += 1
                    
                    aggressive_pct = aggressive_trades / len(trades) * 100 if trades else 0
                    if aggressive_pct > 70:
                        characteristics.append("AGGRESSIVE")
                        toxicity_indicators.append(min(aggressive_pct / 3, 25))  # Max 25 points
        
        # 4. Trade velocity (rapid succession)
        if len(trades) >= 2:
            timestamps = [t.get("time", 0) for t in trades if t.get("time", 0) > 0]
            if len(timestamps) >= 2:
                time_span = (timestamps[-1] - timestamps[0]) / 1000  # Convert to seconds
                if time_span > 0:
                    velocity = len(trades) / time_span  # Trades per second
                    if velocity > 2:  # More than 2 trades per second
                        characteristics.append("HIGH_VELOCITY")
                        toxicity_indicators.append(min(velocity * 5, 15))  # Max 15 points
        
        # Calculate toxicity score
        toxicity_score = sum(toxicity_indicators) if toxicity_indicators else 50.0
        toxicity_score = min(toxicity_score, 100.0)
        
        # Classify flow type
        if toxicity_score >= self.toxic_flow_threshold:
            flow_type = "TOXIC"
        elif toxicity_score <= 40:
            flow_type = "NOISE"
        else:
            flow_type = "MIXED"
        
        # Calculate informed volume percentage
        informed_volume_pct = large_trade_pct if 'large_trade_pct' in locals() else 0.0
        
        return OrderFlowClassification(
            flow_type=flow_type,
            toxicity_score=toxicity_score,
            informed_volume_pct=informed_volume_pct,
            characteristics=characteristics
        )

    
    def calculate_toxicity_score(self, trades: List[Dict], orderbook: Dict) -> float:
        """
        Calculate Order Flow Toxicity Score (0-100).
        
        Higher score = more informed trading
        
        Args:
            trades: Recent trades
            orderbook: Current order book
            
        Returns:
            Toxicity score (0-100)
            
        Validates: Requirement 17.5, 17.6
        """
        classification = self.classify_order_flow(trades, orderbook)
        return classification.toxicity_score

    
    def detect_quote_stuffing(self, symbol: str, orderbook_updates: List[Dict]) -> Optional[QuoteStuffing]:
        """
        Detect quote stuffing (excessive order book updates).
        
        Criteria:
        - >100 updates per second
        - Most orders cancelled quickly
        - Manipulation signal
        
        Args:
            symbol: Trading symbol
            orderbook_updates: Recent order book updates
            
        Returns:
            QuoteStuffing if detected, None otherwise
            
        Validates: Requirement 17.7
        """
        # Initialize history for this symbol
        if symbol not in self.orderbook_update_history:
            self.orderbook_update_history[symbol] = deque(maxlen=self.max_history_length)
        
        history = self.orderbook_update_history[symbol]
        now = datetime.utcnow()
        
        # Add current updates
        for update in orderbook_updates:
            timestamp = update.get("timestamp", now)
            history.append(timestamp)
        
        # Need sufficient history
        if len(history) < 10:
            return None
        
        # Check update rate over last 1 second
        cutoff = now - timedelta(seconds=1)
        recent_updates = [ts for ts in history if ts > cutoff]
        
        updates_per_second = len(recent_updates)
        
        if updates_per_second > self.quote_stuffing_threshold:
            # Check cancel rate (if available in updates)
            cancels = sum(1 for u in orderbook_updates if u.get("type") == "cancel")
            cancel_rate = cancels / len(orderbook_updates) if orderbook_updates else 0
            
            # Find duration of stuffing
            stuffing_start = None
            for ts in reversed(list(history)):
                # Count updates in 1-second window before this timestamp
                window_start = ts - timedelta(seconds=1)
                window_updates = sum(1 for t in history if window_start <= t <= ts)
                
                if window_updates > self.quote_stuffing_threshold:
                    stuffing_start = ts
                else:
                    break
            
            duration_seconds = (now - stuffing_start).total_seconds() if stuffing_start else 1.0
            
            stuffing = QuoteStuffing(
                updates_per_second=updates_per_second,
                cancel_rate=cancel_rate,
                duration_seconds=duration_seconds,
                timestamp=now
            )
            
            log.warning(
                f"[QUOTE STUFFING] {symbol}: "
                f"{updates_per_second:.0f} updates/sec "
                f"(cancel rate: {cancel_rate:.1%}) "
                f"for {duration_seconds:.1f}s"
            )
            
            return stuffing
        
        return None

    
    def analyze_comprehensive(self, symbol: str, orderbook: Dict, recent_trades: List[Dict],
                             orderbook_updates: Optional[List[Dict]] = None) -> Dict:
        """
        Comprehensive market microstructure analysis.
        
        Combines all analysis methods and generates final assessment.
        
        Args:
            symbol: Trading symbol
            orderbook: Current order book
            recent_trades: Recent trades
            orderbook_updates: Recent order book updates (optional)
            
        Returns:
            Dict with comprehensive analysis results
            
        Validates: Requirements 17.1-17.8
        """
        # Get best bid and ask
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])
        
        if not bids or not asks:
            return {
                "signal": "NEUTRAL",
                "confidence": 0.0,
                "error": "Insufficient orderbook data"
            }
        
        # Extract best bid and ask
        if isinstance(bids[0], dict):
            best_bid = bids[0].get("price", 0)
        elif isinstance(bids[0], (list, tuple)) and len(bids[0]) >= 2:
            best_bid = bids[0][0]
        else:
            best_bid = 0
        
        if isinstance(asks[0], dict):
            best_ask = asks[0].get("price", 0)
        elif isinstance(asks[0], (list, tuple)) and len(asks[0]) >= 2:
            best_ask = asks[0][0]
        else:
            best_ask = 0
        
        if best_bid == 0 or best_ask == 0:
            return {
                "signal": "NEUTRAL",
                "confidence": 0.0,
                "error": "Invalid orderbook prices"
            }
        
        mid_price = (best_bid + best_ask) / 2
        bid_ask_spread = best_ask - best_bid
        
        # 1. Calculate effective spread
        effective_spread = self.calculate_effective_spread(recent_trades, mid_price)
        
        # 2. Detect spread widening
        spread_widening = self.detect_spread_widening(symbol, bid_ask_spread)
        
        # 3. Calculate price impact for different sizes
        price_impacts = {}
        for size in self.price_impact_levels:
            buy_impact = self.calculate_price_impact(size, orderbook, "BUY")
            sell_impact = self.calculate_price_impact(size, orderbook, "SELL")
            price_impacts[size] = {
                "buy": {
                    "slippage_pct": buy_impact.estimated_slippage_pct,
                    "levels": buy_impact.levels_consumed,
                    "avg_price": buy_impact.avg_execution_price
                },
                "sell": {
                    "slippage_pct": sell_impact.estimated_slippage_pct,
                    "levels": sell_impact.levels_consumed,
                    "avg_price": sell_impact.avg_execution_price
                }
            }
        
        # 4. Classify order flow
        flow_classification = self.classify_order_flow(recent_trades, orderbook)
        
        # 5. Calculate toxicity score
        toxicity_score = flow_classification.toxicity_score
        
        # 6. Detect quote stuffing
        quote_stuffing = None
        if orderbook_updates:
            quote_stuffing = self.detect_quote_stuffing(symbol, orderbook_updates)
        
        # 7. Generate overall assessment
        signals = []
        confidence_scores = []
        
        # Toxic flow signal
        if flow_classification.flow_type == "TOXIC":
            # Determine direction from trade imbalance
            buy_volume = sum(t.get("size", 0) for t in recent_trades if t.get("side") == "Buy")
            sell_volume = sum(t.get("size", 0) for t in recent_trades if t.get("side") == "Sell")
            
            if buy_volume > sell_volume * 1.2:
                signals.append("LONG")
                confidence_scores.append(toxicity_score / 100)
            elif sell_volume > buy_volume * 1.2:
                signals.append("SHORT")
                confidence_scores.append(toxicity_score / 100)
        
        # Spread widening signal (uncertainty - reduce confidence)
        spread_widening_detected = spread_widening is not None
        
        # Quote stuffing signal (manipulation - caution)
        quote_stuffing_detected = quote_stuffing is not None
        
        # Determine final signal
        if not signals:
            final_signal = "NEUTRAL"
            final_confidence = 0.0
        else:
            # Majority vote
            long_count = signals.count("LONG")
            short_count = signals.count("SHORT")
            
            if long_count > short_count:
                final_signal = "LONG"
                long_confidences = [c for s, c in zip(signals, confidence_scores) if s == "LONG"]
                final_confidence = sum(long_confidences) / len(long_confidences)
            elif short_count > long_count:
                final_signal = "SHORT"
                short_confidences = [c for s, c in zip(signals, confidence_scores) if s == "SHORT"]
                final_confidence = sum(short_confidences) / len(short_confidences)
            else:
                final_signal = "NEUTRAL"
                final_confidence = 0.5
        
        # Adjust confidence based on spread widening and quote stuffing
        if spread_widening_detected:
            final_confidence *= 0.9  # Reduce by 10%
        
        if quote_stuffing_detected:
            final_confidence *= 0.85  # Reduce by 15%
        
        result = {
            "signal": final_signal,
            "confidence": final_confidence,
            "spread": {
                "bid_ask_spread": bid_ask_spread,
                "effective_spread": effective_spread,
                "mid_price": mid_price
            },
            "spread_widening": {
                "detected": spread_widening_detected,
                "current_spread": spread_widening.current_spread if spread_widening else bid_ask_spread,
                "avg_spread": spread_widening.avg_spread if spread_widening else bid_ask_spread,
                "ratio": spread_widening.widening_ratio if spread_widening else 1.0,
                "duration_min": spread_widening.duration_minutes if spread_widening else 0.0
            },
            "price_impact": price_impacts,
            "order_flow": {
                "flow_type": flow_classification.flow_type,
                "toxicity_score": toxicity_score,
                "informed_volume_pct": flow_classification.informed_volume_pct,
                "characteristics": flow_classification.characteristics
            },
            "quote_stuffing": {
                "detected": quote_stuffing_detected,
                "updates_per_sec": quote_stuffing.updates_per_second if quote_stuffing else 0.0,
                "cancel_rate": quote_stuffing.cancel_rate if quote_stuffing else 0.0,
                "duration_sec": quote_stuffing.duration_seconds if quote_stuffing else 0.0
            }
        }
        
        return result
