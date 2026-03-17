"""
Advanced Order Book Imbalance Detection

Implements advanced order book analysis including:
- Bid-ask imbalance ratio calculation per level
- Iceberg order detection (repeated refills at same price)
- Spoofing detection (large orders cancelled quickly)
- Flash imbalance detection (>30% change in 10 seconds)
- Pressure score calculation (0-100)
- Absorption event detection

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque

from utils.logger import get_logger

log = get_logger("analytics.orderbook_imbalance")


@dataclass
class ImbalanceRatio:
    """Bid-ask imbalance ratio data."""
    bid_volume: float
    ask_volume: float
    ratio: float  # bid/ask
    imbalance_pct: float  # (bid-ask)/(bid+ask) * 100
    levels: Dict[float, float]  # price -> imbalance ratio


@dataclass
class IcebergOrder:
    """Detected iceberg order."""
    price: float
    side: str  # BID, ASK
    estimated_total_size: float
    visible_size: float
    refill_count: int
    confidence: float
    timestamp: datetime


@dataclass
class SpoofingEvent:
    """Detected spoofing event."""
    price: float
    side: str  # BID, ASK
    size: float
    duration_seconds: float
    cancelled: bool
    timestamp: datetime


@dataclass
class FlashImbalance:
    """Flash imbalance alert."""
    previous_imbalance: float
    current_imbalance: float
    change_pct: float
    direction: str  # BUY_PRESSURE, SELL_PRESSURE
    timestamp: datetime


@dataclass
class PressureScore:
    """Order book pressure score."""
    score: float  # 0-100 (0=strong sell, 100=strong buy)
    direction: str  # BUY, SELL, NEUTRAL
    confidence: float


@dataclass
class AbsorptionEvent:
    """Detected absorption event."""
    price: float
    side: str  # Which side is absorbing (BID, ASK)
    volume_absorbed: float
    timestamp: datetime
    confidence: float


class OrderBookImbalanceDetector:
    """Advanced order book imbalance detection and analysis."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize detector with configuration."""
        self.config = config or {}
        
        # Configuration parameters
        self.flash_imbalance_threshold_pct = self.config.get("flash_imbalance_threshold_pct", 30)
        self.flash_imbalance_window_sec = self.config.get("flash_imbalance_window_sec", 10)
        self.iceberg_refill_threshold = self.config.get("iceberg_refill_threshold", 3)
        self.spoofing_max_duration_sec = self.config.get("spoofing_max_duration_sec", 30)
        self.absorption_volume_multiplier = self.config.get("absorption_volume_multiplier", 2.0)
        self.pressure_score_levels = self.config.get("pressure_score_levels", 10)
        
        # History tracking
        self.imbalance_history: Dict[str, deque] = {}  # symbol -> deque of (timestamp, imbalance_pct)
        self.iceberg_tracker: Dict[str, Dict] = {}  # symbol -> {price: {refills, sizes, timestamps}}
        self.orderbook_snapshots: Dict[str, deque] = {}  # symbol -> deque of snapshots
        self.max_history_length = 100
        
        log.info(
            f"OrderBookImbalanceDetector initialized "
            f"(flash_threshold={self.flash_imbalance_threshold_pct}%, "
            f"window={self.flash_imbalance_window_sec}s)"
        )

    
    def calculate_bid_ask_imbalance(self, orderbook: Dict) -> ImbalanceRatio:
        """
        Calculate bid-ask imbalance ratio for each price level.
        
        Args:
            orderbook: Order book with bids and asks
            
        Returns:
            ImbalanceRatio with per-level and aggregate ratios
            
        Validates: Requirement 7.1
        """
        bids_data = orderbook.get("bids", [])[:self.pressure_score_levels]
        asks_data = orderbook.get("asks", [])[:self.pressure_score_levels]
        
        # Calculate total volumes
        bid_volume = 0.0
        ask_volume = 0.0
        level_imbalances = {}
        
        # Support both formats: [{"price": X, "size": Y}] and [[price, size]]
        for b in bids_data:
            if isinstance(b, dict):
                price, size = b.get("price", 0), b.get("size", 0)
            elif isinstance(b, (list, tuple)) and len(b) >= 2:
                price, size = b[0], b[1]
            else:
                continue
            
            bid_volume += size
            level_imbalances[price] = size
        
        for a in asks_data:
            if isinstance(a, dict):
                price, size = a.get("price", 0), a.get("size", 0)
            elif isinstance(a, (list, tuple)) and len(a) >= 2:
                price, size = a[0], a[1]
            else:
                continue
            
            ask_volume += size
            # Negative for asks to distinguish from bids
            level_imbalances[price] = -size
        
        # Calculate aggregate metrics
        total_volume = bid_volume + ask_volume
        
        if total_volume == 0:
            ratio = 1.0
            imbalance_pct = 0.0
        else:
            ratio = bid_volume / ask_volume if ask_volume > 0 else float('inf')
            imbalance_pct = ((bid_volume - ask_volume) / total_volume) * 100
        
        return ImbalanceRatio(
            bid_volume=bid_volume,
            ask_volume=ask_volume,
            ratio=ratio,
            imbalance_pct=imbalance_pct,
            levels=level_imbalances
        )

    
    def detect_iceberg_orders(self, symbol: str, orderbook: Dict, recent_trades: List[Dict]) -> List[IcebergOrder]:
        """
        Detect iceberg orders (large orders hidden in small pieces).
        
        Criteria:
        - Same price level repeatedly refilled
        - Consistent size after fills
        - Multiple refills within short time
        
        Args:
            symbol: Trading symbol
            orderbook: Current order book
            recent_trades: Recent trades to detect fills
            
        Returns:
            List of detected iceberg orders
            
        Validates: Requirement 7.2
        """
        # Initialize tracker for this symbol
        if symbol not in self.iceberg_tracker:
            self.iceberg_tracker[symbol] = {}
        
        tracker = self.iceberg_tracker[symbol]
        detected_icebergs = []
        
        # Track current order book levels
        current_levels = {}
        
        for b in orderbook.get("bids", [])[:10]:
            if isinstance(b, dict):
                price, size = b.get("price", 0), b.get("size", 0)
            elif isinstance(b, (list, tuple)) and len(b) >= 2:
                price, size = b[0], b[1]
            else:
                continue
            
            current_levels[price] = {"side": "BID", "size": size}
        
        for a in orderbook.get("asks", [])[:10]:
            if isinstance(a, dict):
                price, size = a.get("price", 0), a.get("size", 0)
            elif isinstance(a, (list, tuple)) and len(a) >= 2:
                price, size = a[0], a[1]
            else:
                continue
            
            current_levels[price] = {"side": "ASK", "size": size}
        
        # Check for refills at tracked prices
        now = datetime.utcnow()
        
        for price, level_data in current_levels.items():
            if price in tracker:
                # Check if this is a refill (size similar to previous)
                prev_data = tracker[price]
                size_diff_pct = abs(level_data["size"] - prev_data["last_size"]) / prev_data["last_size"] * 100 if prev_data["last_size"] > 0 else 100
                
                # If size is similar (within 20%), count as refill
                if size_diff_pct < 20:
                    prev_data["refill_count"] += 1
                    prev_data["timestamps"].append(now)
                    prev_data["sizes"].append(level_data["size"])
                    
                    # Check if meets iceberg criteria
                    if prev_data["refill_count"] >= self.iceberg_refill_threshold:
                        avg_size = sum(prev_data["sizes"]) / len(prev_data["sizes"])
                        estimated_total = avg_size * prev_data["refill_count"]
                        
                        iceberg = IcebergOrder(
                            price=price,
                            side=level_data["side"],
                            estimated_total_size=estimated_total,
                            visible_size=level_data["size"],
                            refill_count=prev_data["refill_count"],
                            confidence=min(0.6 + (prev_data["refill_count"] - self.iceberg_refill_threshold) * 0.1, 0.95),
                            timestamp=now
                        )
                        detected_icebergs.append(iceberg)
                        
                        log.info(
                            f"[ICEBERG] Detected at ${price:.2f} {level_data['side']}: "
                            f"{prev_data['refill_count']} refills, "
                            f"est. total {estimated_total:.0f}, "
                            f"visible {level_data['size']:.0f}"
                        )
                else:
                    # Size changed significantly, reset tracking
                    tracker[price] = {
                        "side": level_data["side"],
                        "last_size": level_data["size"],
                        "refill_count": 1,
                        "timestamps": [now],
                        "sizes": [level_data["size"]]
                    }
            else:
                # New price level, start tracking
                tracker[price] = {
                    "side": level_data["side"],
                    "last_size": level_data["size"],
                    "refill_count": 1,
                    "timestamps": [now],
                    "sizes": [level_data["size"]]
                }
        
        # Clean up old tracked prices (not in current book)
        prices_to_remove = [p for p in tracker.keys() if p not in current_levels]
        for p in prices_to_remove:
            del tracker[p]
        
        return detected_icebergs

    
    def detect_spoofing(self, symbol: str, orderbook: Dict) -> List[SpoofingEvent]:
        """
        Detect spoofing (fake large orders that get cancelled).
        
        Criteria:
        - Large order appears
        - Stays for <30 seconds
        - Gets cancelled before execution
        
        Args:
            symbol: Trading symbol
            orderbook: Current order book
            
        Returns:
            List of detected spoofing events
            
        Validates: Requirement 7.3
        """
        # Initialize snapshot history for this symbol
        if symbol not in self.orderbook_snapshots:
            self.orderbook_snapshots[symbol] = deque(maxlen=self.max_history_length)
        
        snapshots = self.orderbook_snapshots[symbol]
        
        # Add current snapshot
        now = datetime.utcnow()
        snapshot = {
            "timestamp": now,
            "bids": orderbook.get("bids", [])[:10],
            "asks": orderbook.get("asks", [])[:10]
        }
        snapshots.append(snapshot)
        
        # Need at least 2 snapshots
        if len(snapshots) < 2:
            return []
        
        detected_spoofs = []
        
        # Calculate average order size from recent snapshots
        all_sizes = []
        for snap in list(snapshots)[-10:]:
            for b in snap["bids"][:5]:
                if isinstance(b, dict):
                    all_sizes.append(b.get("size", 0))
                elif isinstance(b, (list, tuple)) and len(b) >= 2:
                    all_sizes.append(b[1])
            
            for a in snap["asks"][:5]:
                if isinstance(a, dict):
                    all_sizes.append(a.get("size", 0))
                elif isinstance(a, (list, tuple)) and len(a) >= 2:
                    all_sizes.append(a[1])
        
        avg_size = sum(all_sizes) / len(all_sizes) if all_sizes else 0
        spoof_size_threshold = avg_size * 5.0  # 5x average
        
        # Check recent snapshots for disappeared large orders
        for i in range(max(0, len(snapshots) - 5), len(snapshots) - 1):
            old_snap = snapshots[i]
            new_snap = snapshots[-1]
            
            time_diff = (new_snap["timestamp"] - old_snap["timestamp"]).total_seconds()
            
            # Only check if within spoofing window
            if time_diff > self.spoofing_max_duration_sec:
                continue
            
            # Build set of current prices for fast lookup
            new_bid_prices = set()
            for b in new_snap["bids"]:
                if isinstance(b, dict):
                    new_bid_prices.add(b.get("price", 0))
                elif isinstance(b, (list, tuple)) and len(b) >= 2:
                    new_bid_prices.add(b[0])
            
            new_ask_prices = set()
            for a in new_snap["asks"]:
                if isinstance(a, dict):
                    new_ask_prices.add(a.get("price", 0))
                elif isinstance(a, (list, tuple)) and len(a) >= 2:
                    new_ask_prices.add(a[0])
            
            # Check for disappeared large bids
            for old_bid in old_snap["bids"][:5]:
                if isinstance(old_bid, dict):
                    price, size = old_bid.get("price", 0), old_bid.get("size", 0)
                elif isinstance(old_bid, (list, tuple)) and len(old_bid) >= 2:
                    price, size = old_bid[0], old_bid[1]
                else:
                    continue
                
                # Large order that disappeared
                if size > spoof_size_threshold and price not in new_bid_prices:
                    spoof = SpoofingEvent(
                        price=price,
                        side="BID",
                        size=size,
                        duration_seconds=time_diff,
                        cancelled=True,
                        timestamp=now
                    )
                    detected_spoofs.append(spoof)
                    
                    log.warning(
                        f"[SPOOF] Detected BID spoofing at ${price:.2f}: "
                        f"size {size:.0f} disappeared in {time_diff:.1f}s"
                    )
            
            # Check for disappeared large asks
            for old_ask in old_snap["asks"][:5]:
                if isinstance(old_ask, dict):
                    price, size = old_ask.get("price", 0), old_ask.get("size", 0)
                elif isinstance(old_ask, (list, tuple)) and len(old_ask) >= 2:
                    price, size = old_ask[0], old_ask[1]
                else:
                    continue
                
                # Large order that disappeared
                if size > spoof_size_threshold and price not in new_ask_prices:
                    spoof = SpoofingEvent(
                        price=price,
                        side="ASK",
                        size=size,
                        duration_seconds=time_diff,
                        cancelled=True,
                        timestamp=now
                    )
                    detected_spoofs.append(spoof)
                    
                    log.warning(
                        f"[SPOOF] Detected ASK spoofing at ${price:.2f}: "
                        f"size {size:.0f} disappeared in {time_diff:.1f}s"
                    )
        
        return detected_spoofs

    
    def detect_flash_imbalance(self, symbol: str, current_imbalance: float) -> Optional[FlashImbalance]:
        """
        Detect sudden imbalance change >30% in 10 seconds.
        
        Args:
            symbol: Trading symbol
            current_imbalance: Current imbalance percentage
            
        Returns:
            FlashImbalance if detected, None otherwise
            
        Validates: Requirement 7.4
        """
        # Initialize history for this symbol
        if symbol not in self.imbalance_history:
            self.imbalance_history[symbol] = deque(maxlen=self.max_history_length)
        
        history = self.imbalance_history[symbol]
        now = datetime.utcnow()
        
        # Add current reading
        history.append((now, current_imbalance))
        
        # Need at least 2 readings
        if len(history) < 2:
            return None
        
        # Check for flash imbalance within window
        for timestamp, prev_imbalance in reversed(list(history)[:-1]):
            time_diff = (now - timestamp).total_seconds()
            
            # Check if within flash window
            if time_diff <= self.flash_imbalance_window_sec:
                change_pct = abs(current_imbalance - prev_imbalance)
                
                if change_pct >= self.flash_imbalance_threshold_pct:
                    # Determine direction
                    if current_imbalance > prev_imbalance:
                        direction = "BUY_PRESSURE"
                    else:
                        direction = "SELL_PRESSURE"
                    
                    flash = FlashImbalance(
                        previous_imbalance=prev_imbalance,
                        current_imbalance=current_imbalance,
                        change_pct=change_pct,
                        direction=direction,
                        timestamp=now
                    )
                    
                    log.warning(
                        f"[FLASH] Flash imbalance detected: "
                        f"{prev_imbalance:.1f}% → {current_imbalance:.1f}% "
                        f"({change_pct:.1f}% change in {time_diff:.1f}s) - {direction}"
                    )
                    
                    return flash
            else:
                # Outside window, stop checking
                break
        
        return None

    
    def calculate_pressure_score(self, orderbook: Dict) -> PressureScore:
        """
        Calculate 0-100 pressure score indicating likely price direction.
        
        Score calculation:
        - 0-20: Strong sell pressure
        - 20-40: Moderate sell pressure
        - 40-60: Neutral
        - 60-80: Moderate buy pressure
        - 80-100: Strong buy pressure
        
        Args:
            orderbook: Order book data
            
        Returns:
            PressureScore with score, direction, and confidence
            
        Validates: Requirement 7.5
        """
        imbalance = self.calculate_bid_ask_imbalance(orderbook)
        
        # Convert imbalance_pct (-100 to +100) to pressure score (0 to 100)
        # imbalance_pct: -100 (all asks) to +100 (all bids)
        # pressure_score: 0 (strong sell) to 100 (strong buy)
        pressure_score = (imbalance.imbalance_pct + 100) / 2
        
        # Determine direction and confidence
        if pressure_score >= 80:
            direction = "BUY"
            confidence = 0.85
        elif pressure_score >= 60:
            direction = "BUY"
            confidence = 0.65
        elif pressure_score <= 20:
            direction = "SELL"
            confidence = 0.85
        elif pressure_score <= 40:
            direction = "SELL"
            confidence = 0.65
        else:
            direction = "NEUTRAL"
            confidence = 0.40
        
        return PressureScore(
            score=pressure_score,
            direction=direction,
            confidence=confidence
        )
    
    def detect_absorption(self, symbol: str, orderbook: Dict, recent_trades: List[Dict]) -> Optional[AbsorptionEvent]:
        """
        Detect large orders absorbing opposite side volume.
        
        Absorption occurs when:
        - Large order on one side
        - Significant volume traded against it
        - Order remains (absorbs the volume)
        
        Args:
            symbol: Trading symbol
            orderbook: Current order book
            recent_trades: Recent trades
            
        Returns:
            AbsorptionEvent if detected, None otherwise
            
        Validates: Requirement 7.6
        """
        if not recent_trades:
            return None
        
        # Calculate recent trade volume
        recent_volume = sum(t.get("size", 0) for t in recent_trades[-20:])
        
        # Get top bid and ask
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])
        
        if not bids or not asks:
            return None
        
        # Extract top levels
        if isinstance(bids[0], dict):
            top_bid_price = bids[0].get("price", 0)
            top_bid_size = bids[0].get("size", 0)
        elif isinstance(bids[0], (list, tuple)) and len(bids[0]) >= 2:
            top_bid_price = bids[0][0]
            top_bid_size = bids[0][1]
        else:
            return None
        
        if isinstance(asks[0], dict):
            top_ask_price = asks[0].get("price", 0)
            top_ask_size = asks[0].get("size", 0)
        elif isinstance(asks[0], (list, tuple)) and len(asks[0]) >= 2:
            top_ask_price = asks[0][0]
            top_ask_size = asks[0][1]
        else:
            return None
        
        # Calculate average order size
        all_sizes = []
        for b in bids[:10]:
            if isinstance(b, dict):
                all_sizes.append(b.get("size", 0))
            elif isinstance(b, (list, tuple)) and len(b) >= 2:
                all_sizes.append(b[1])
        
        for a in asks[:10]:
            if isinstance(a, dict):
                all_sizes.append(a.get("size", 0))
            elif isinstance(a, (list, tuple)) and len(a) >= 2:
                all_sizes.append(a[1])
        
        avg_size = sum(all_sizes) / len(all_sizes) if all_sizes else 0
        absorption_threshold = avg_size * self.absorption_volume_multiplier
        
        # Check for bid absorption (large bid absorbing sell volume)
        if top_bid_size > absorption_threshold:
            # Count sell volume near top bid
            sell_volume_near_bid = sum(
                t.get("size", 0) for t in recent_trades[-20:]
                if t.get("side") == "Sell" and abs(t.get("price", 0) - top_bid_price) / top_bid_price < 0.001
            )
            
            if sell_volume_near_bid > top_bid_size * 0.5:  # Absorbed at least 50% of visible size
                absorption = AbsorptionEvent(
                    price=top_bid_price,
                    side="BID",
                    volume_absorbed=sell_volume_near_bid,
                    timestamp=datetime.utcnow(),
                    confidence=min(0.6 + (sell_volume_near_bid / top_bid_size) * 0.2, 0.9)
                )
                
                log.info(
                    f"[ABSORPTION] BID absorption at ${top_bid_price:.2f}: "
                    f"absorbed {sell_volume_near_bid:.0f} sell volume "
                    f"(bid size: {top_bid_size:.0f})"
                )
                
                return absorption
        
        # Check for ask absorption (large ask absorbing buy volume)
        if top_ask_size > absorption_threshold:
            # Count buy volume near top ask
            buy_volume_near_ask = sum(
                t.get("size", 0) for t in recent_trades[-20:]
                if t.get("side") == "Buy" and abs(t.get("price", 0) - top_ask_price) / top_ask_price < 0.001
            )
            
            if buy_volume_near_ask > top_ask_size * 0.5:  # Absorbed at least 50% of visible size
                absorption = AbsorptionEvent(
                    price=top_ask_price,
                    side="ASK",
                    volume_absorbed=buy_volume_near_ask,
                    timestamp=datetime.utcnow(),
                    confidence=min(0.6 + (buy_volume_near_ask / top_ask_size) * 0.2, 0.9)
                )
                
                log.info(
                    f"[ABSORPTION] ASK absorption at ${top_ask_price:.2f}: "
                    f"absorbed {buy_volume_near_ask:.0f} buy volume "
                    f"(ask size: {top_ask_size:.0f})"
                )
                
                return absorption
        
        return None

    
    def analyze_comprehensive(self, symbol: str, orderbook: Dict, recent_trades: List[Dict]) -> Dict:
        """
        Comprehensive order book imbalance analysis.
        
        Combines all detection methods and generates final assessment.
        
        Args:
            symbol: Trading symbol
            orderbook: Current order book
            recent_trades: Recent trades
            
        Returns:
            Dict with comprehensive analysis results
            
        Validates: Requirements 7.1-7.8
        """
        # 1. Calculate bid-ask imbalance
        imbalance = self.calculate_bid_ask_imbalance(orderbook)
        
        # 2. Detect iceberg orders
        icebergs = self.detect_iceberg_orders(symbol, orderbook, recent_trades)
        
        # 3. Detect spoofing
        spoofs = self.detect_spoofing(symbol, orderbook)
        
        # 4. Detect flash imbalance
        flash = self.detect_flash_imbalance(symbol, imbalance.imbalance_pct)
        
        # 5. Calculate pressure score
        pressure = self.calculate_pressure_score(orderbook)
        
        # 6. Detect absorption
        absorption = self.detect_absorption(symbol, orderbook, recent_trades)
        
        # 7. Generate overall assessment
        signals = []
        confidence_scores = []
        
        # Pressure score signal
        if pressure.confidence > 0.6:
            if pressure.direction == "BUY":
                signals.append("LONG")
                confidence_scores.append(pressure.confidence)
            elif pressure.direction == "SELL":
                signals.append("SHORT")
                confidence_scores.append(pressure.confidence)
        
        # Flash imbalance signal
        if flash:
            if flash.direction == "BUY_PRESSURE":
                signals.append("LONG")
                confidence_scores.append(0.75)
            elif flash.direction == "SELL_PRESSURE":
                signals.append("SHORT")
                confidence_scores.append(0.75)
        
        # Absorption signal
        if absorption:
            if absorption.side == "BID":
                signals.append("LONG")
                confidence_scores.append(absorption.confidence)
            elif absorption.side == "ASK":
                signals.append("SHORT")
                confidence_scores.append(absorption.confidence)
        
        # Iceberg signal (institutional accumulation/distribution)
        if icebergs:
            for iceberg in icebergs:
                if iceberg.side == "BID":
                    signals.append("LONG")
                    confidence_scores.append(iceberg.confidence)
                elif iceberg.side == "ASK":
                    signals.append("SHORT")
                    confidence_scores.append(iceberg.confidence)
        
        # Spoofing signal (fade the spoof)
        if spoofs:
            for spoof in spoofs:
                if spoof.side == "BID":
                    signals.append("SHORT")  # Fade fake bid
                    confidence_scores.append(0.60)
                elif spoof.side == "ASK":
                    signals.append("LONG")  # Fade fake ask
                    confidence_scores.append(0.60)
        
        # Determine final signal
        if not signals:
            final_signal = "NEUTRAL"
            final_confidence = 0.0
        else:
            # Majority vote with weighted confidence
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
        
        result = {
            "signal": final_signal,
            "confidence": final_confidence,
            "imbalance": {
                "bid_volume": imbalance.bid_volume,
                "ask_volume": imbalance.ask_volume,
                "ratio": imbalance.ratio,
                "imbalance_pct": imbalance.imbalance_pct
            },
            "pressure_score": {
                "score": pressure.score,
                "direction": pressure.direction,
                "confidence": pressure.confidence
            },
            "icebergs_detected": len(icebergs),
            "icebergs": [
                {
                    "price": ice.price,
                    "side": ice.side,
                    "estimated_total_size": ice.estimated_total_size,
                    "visible_size": ice.visible_size,
                    "refill_count": ice.refill_count,
                    "confidence": ice.confidence
                }
                for ice in icebergs
            ],
            "spoofs_detected": len(spoofs),
            "spoofs": [
                {
                    "price": spoof.price,
                    "side": spoof.side,
                    "size": spoof.size,
                    "duration_seconds": spoof.duration_seconds
                }
                for spoof in spoofs
            ],
            "flash_imbalance": {
                "detected": flash is not None,
                "previous_imbalance": flash.previous_imbalance if flash else None,
                "current_imbalance": flash.current_imbalance if flash else None,
                "change_pct": flash.change_pct if flash else None,
                "direction": flash.direction if flash else None
            } if flash else None,
            "absorption": {
                "detected": absorption is not None,
                "price": absorption.price if absorption else None,
                "side": absorption.side if absorption else None,
                "volume_absorbed": absorption.volume_absorbed if absorption else None,
                "confidence": absorption.confidence if absorption else None
            } if absorption else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        log.info(
            f"[OB_IMBALANCE] {symbol}: {final_signal} "
            f"(conf: {final_confidence:.2%}, "
            f"pressure: {pressure.score:.0f}/100, "
            f"imbalance: {imbalance.imbalance_pct:+.1f}%, "
            f"icebergs: {len(icebergs)}, spoofs: {len(spoofs)})"
        )
        
        return result
