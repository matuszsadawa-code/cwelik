"""
Enhanced DOM (Depth of Market) Analysis for 5/15min Predictions
Implements imbalance optimization, hidden liquidity detection, and spoofing detection.
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

from utils.logger import get_logger

log = get_logger("analytics.dom_enhanced")


class EnhancedDOMAnalyzer:
    """Advanced DOM analysis for short-term predictions."""
    
    def __init__(self):
        self.strong_imbalance_threshold = 0.70
        self.moderate_imbalance_threshold = 0.60
        self.hidden_liquidity_multiplier = 2.0
        self.iceberg_fill_threshold = 5
        self.spoof_duration_threshold = 5  # seconds
        self.spoof_size_multiplier = 5.0
        
        # Track order book history for spoofing detection
        self.orderbook_history = {}  # symbol -> list of snapshots
        self.max_history_length = 100
        
        log.info("EnhancedDOMAnalyzer initialized")
    
    def calculate_imbalance(self, bids: float, asks: float) -> Dict:
        """Calculate bid/ask imbalance with optimized thresholds.
        
        Args:
            bids: Total bid liquidity (sum of bid sizes)
            asks: Total ask liquidity (sum of ask sizes)
            
        Returns:
            Dict with imbalance ratio, signal, and confidence
        """
        total = bids + asks
        
        if total == 0:
            return {
                "ratio": 0.5,
                "signal": "NEUTRAL",
                "confidence": 0.0,
                "bids": bids,
                "asks": asks
            }
        
        bid_ratio = bids / total
        
        # Classify based on optimized thresholds
        if bid_ratio > self.strong_imbalance_threshold:
            signal = "STRONG_BUY"
            confidence = 0.80
            log.info(f"[+] STRONG BUY imbalance: {bid_ratio:.1%} bids")
        
        elif bid_ratio > self.moderate_imbalance_threshold:
            signal = "MODERATE_BUY"
            confidence = 0.65
            log.info(f"[+] MODERATE BUY imbalance: {bid_ratio:.1%} bids")
        
        elif bid_ratio < (1 - self.strong_imbalance_threshold):
            signal = "STRONG_SELL"
            confidence = 0.80
            log.info(f"[-] STRONG SELL imbalance: {(1-bid_ratio):.1%} asks")
        
        elif bid_ratio < (1 - self.moderate_imbalance_threshold):
            signal = "MODERATE_SELL"
            confidence = 0.65
            log.info(f"[-] MODERATE SELL imbalance: {(1-bid_ratio):.1%} asks")
        
        else:
            signal = "NEUTRAL"
            confidence = 0.40
        
        return {
            "ratio": bid_ratio,
            "signal": signal,
            "confidence": confidence,
            "bids": bids,
            "asks": asks
        }
    
    def detect_hidden_liquidity(self, visible_liquidity: float, executed_volume: float, 
                                recent_trades: List[Dict]) -> Dict:
        """Detect hidden liquidity (iceberg orders, hidden orders).
        
        Args:
            visible_liquidity: Sum of visible orders in the book
            executed_volume: Total volume executed recently
            recent_trades: List of recent trades with price, size, side
            
        Returns:
            Dict with hidden liquidity detection results
        """
        # Check if executed volume significantly exceeds visible liquidity
        if executed_volume > visible_liquidity * self.hidden_liquidity_multiplier:
            # Determine direction
            buy_volume = sum(t['size'] for t in recent_trades if t.get('side') == 'Buy')
            sell_volume = sum(t['size'] for t in recent_trades if t.get('side') == 'Sell')
            
            if buy_volume > sell_volume:
                signal = "HIDDEN_BUYING"
                confidence = 0.70
                log.info(f"[WHALE] HIDDEN BUYING detected (executed: {executed_volume:.0f}, visible: {visible_liquidity:.0f})")
            else:
                signal = "HIDDEN_SELLING"
                confidence = 0.70
                log.info(f"[WHALE] HIDDEN SELLING detected (executed: {executed_volume:.0f}, visible: {visible_liquidity:.0f})")
            
            return {
                "detected": True,
                "signal": signal,
                "confidence": confidence,
                "visible_liquidity": visible_liquidity,
                "executed_volume": executed_volume,
                "ratio": executed_volume / visible_liquidity if visible_liquidity > 0 else 0
            }
        
        # Check for iceberg orders (repeated fills at same price)
        price_fills = {}
        for trade in recent_trades:
            price = trade.get('price')
            if price:
                price_fills[price] = price_fills.get(price, 0) + 1
        
        max_fills = max(price_fills.values()) if price_fills else 0
        
        if max_fills >= self.iceberg_fill_threshold:
            iceberg_price = max(price_fills, key=price_fills.get)
            log.info(f"[ICEBERG] ICEBERG ORDER detected at ${iceberg_price} ({max_fills} fills)")
            
            return {
                "detected": True,
                "signal": "ICEBERG_DETECTED",
                "confidence": 0.65,
                "price": iceberg_price,
                "fill_count": max_fills
            }
        
        return {
            "detected": False,
            "signal": "NO_HIDDEN_LIQUIDITY",
            "confidence": 0.0
        }
    
    def detect_spoofing(self, symbol: str, current_orderbook: Dict) -> Dict:
        """Detect spoofing (fake orders that appear and disappear).
        
        Args:
            symbol: Trading symbol
            current_orderbook: Current order book snapshot
            
        Returns:
            Dict with spoofing detection results
        """
        # Initialize history for this symbol if needed
        if symbol not in self.orderbook_history:
            self.orderbook_history[symbol] = []
        
        # Add current snapshot to history
        snapshot = {
            "timestamp": datetime.utcnow(),
            "bids": current_orderbook.get("bids", []),
            "asks": current_orderbook.get("asks", [])
        }
        self.orderbook_history[symbol].append(snapshot)
        
        # Trim history
        if len(self.orderbook_history[symbol]) > self.max_history_length:
            self.orderbook_history[symbol] = self.orderbook_history[symbol][-self.max_history_length:]
        
        # Need at least 2 snapshots to detect spoofing
        if len(self.orderbook_history[symbol]) < 2:
            return {"detected": False, "signal": "INSUFFICIENT_DATA"}
        
        # Look for large orders that disappeared quickly without filling
        history = self.orderbook_history[symbol]
        
        # Helper to extract price and size from either dict or list
        def get_price_size(item):
            if isinstance(item, dict):
                return item.get("price", 0), item.get("size", 0)
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                return item[0], item[1]
            return 0, 0

        # Calculate average order size
        all_sizes = []
        for snap in history[-10:]:  # Last 10 snapshots
            for b in snap.get("bids", [])[:5]:
                _, size = get_price_size(b)
                all_sizes.append(size)
            for a in snap.get("asks", [])[:5]:
                _, size = get_price_size(a)
                all_sizes.append(size)
        
        avg_size = sum(all_sizes) / len(all_sizes) if all_sizes else 0
        
        # Check for spoofing patterns
        for i in range(len(history) - 1):
            old_snap = history[i]
            new_snap = history[i + 1]
            
            time_diff = (new_snap["timestamp"] - old_snap["timestamp"]).total_seconds()
            
            # Extract new snap prices for fast lookup
            new_bid_prices = {get_price_size(b)[0] for b in new_snap.get("bids", [])}
            new_ask_prices = {get_price_size(a)[0] for a in new_snap.get("asks", [])}
            
            # Check bids
            for old_bid in old_snap.get("bids", [])[:5]:
                price, size = get_price_size(old_bid)
                
                # Large order
                if size > avg_size * self.spoof_size_multiplier and size > 0:
                    # Check if it disappeared
                    found = price in new_bid_prices
                    
                    if not found and time_diff < self.spoof_duration_threshold:
                        log.warning(f"⚠️ SPOOFING detected: Large bid ${price} ({size}) disappeared in {time_diff:.1f}s")
                        return {
                            "detected": True,
                            "signal": "SPOOFING_BID",
                            "confidence": 0.60,
                            "side": "BUY",
                            "price": price,
                            "size": size,
                            "duration": time_diff,
                            "action": "FADE"  # Fade the spoof (go opposite)
                        }
            
            # Check asks
            for old_ask in old_snap.get("asks", [])[:5]:
                price, size = get_price_size(old_ask)
                
                # Large order
                if size > avg_size * self.spoof_size_multiplier and size > 0:
                    # Check if it disappeared
                    found = price in new_ask_prices
                    
                    if not found and time_diff < self.spoof_duration_threshold:
                        log.warning(f"⚠️ SPOOFING detected: Large ask ${price} ({size}) disappeared in {time_diff:.1f}s")
                        return {
                            "detected": True,
                            "signal": "SPOOFING_ASK",
                            "confidence": 0.60,
                            "side": "SELL",
                            "price": price,
                            "size": size,
                            "duration": time_diff,
                            "action": "FADE"  # Fade the spoof (go opposite)
                        }
        
        return {
            "detected": False,
            "signal": "NO_SPOOFING"
        }
    
    def analyze_comprehensive(self, symbol: str, orderbook: Dict, recent_trades: List[Dict]) -> Dict:
        """Comprehensive DOM analysis combining all techniques.
        
        Args:
            symbol: Trading symbol
            orderbook: Current order book with bids and asks
            recent_trades: List of recent trades
            
        Returns:
            Dict with comprehensive analysis and final signal
        """
        # 1. Calculate imbalance - handle both dict and list formats
        bids_data = orderbook.get("bids", [])[:10]
        asks_data = orderbook.get("asks", [])[:10]
        
        # Support both formats: [{"price": X, "size": Y}] and [[price, size]]
        bids_total = 0
        asks_total = 0
        
        for b in bids_data:
            if isinstance(b, dict):
                bids_total += b.get("size", 0)
            elif isinstance(b, (list, tuple)) and len(b) >= 2:
                bids_total += b[1]
        
        for a in asks_data:
            if isinstance(a, dict):
                asks_total += a.get("size", 0)
            elif isinstance(a, (list, tuple)) and len(a) >= 2:
                asks_total += a[1]
        
        imbalance = self.calculate_imbalance(bids_total, asks_total)
        
        # 2. Detect hidden liquidity
        visible_liquidity = bids_total + asks_total
        executed_volume = sum(t.get('size', 0) for t in recent_trades[-20:])
        hidden_liq = self.detect_hidden_liquidity(visible_liquidity, executed_volume, recent_trades)
        
        # 3. Detect spoofing
        spoofing = self.detect_spoofing(symbol, orderbook)
        
        # 4. Combine signals
        signals = []
        confidences = []
        
        # Imbalance signal
        if imbalance["confidence"] > 0.6:
            if "BUY" in imbalance["signal"]:
                signals.append("LONG")
            elif "SELL" in imbalance["signal"]:
                signals.append("SHORT")
            confidences.append(imbalance["confidence"])
        
        # Hidden liquidity signal
        if hidden_liq["detected"]:
            if "BUYING" in hidden_liq["signal"]:
                signals.append("LONG")
            elif "SELLING" in hidden_liq["signal"]:
                signals.append("SHORT")
            confidences.append(hidden_liq["confidence"])
        
        # Spoofing signal (fade the spoof)
        if spoofing.get("detected"):
            if spoofing["side"] == "BUY":
                signals.append("SHORT")  # Fade the fake bid
            elif spoofing["side"] == "SELL":
                signals.append("LONG")  # Fade the fake ask
            confidences.append(spoofing["confidence"])
        
        # 5. Final decision
        if not signals:
            final_signal = "NEUTRAL"
            final_confidence = 0.0
        else:
            # Majority vote
            long_count = signals.count("LONG")
            short_count = signals.count("SHORT")
            
            if long_count > short_count:
                final_signal = "LONG"
                final_confidence = sum(c for s, c in zip(signals, confidences) if s == "LONG") / long_count
            elif short_count > long_count:
                final_signal = "SHORT"
                final_confidence = sum(c for s, c in zip(signals, confidences) if s == "SHORT") / short_count
            else:
                final_signal = "NEUTRAL"
                final_confidence = 0.5
        
        log.info(f"[DOM] DOM Comprehensive Analysis: {final_signal} (confidence: {final_confidence:.2%})")
        
        return {
            "signal": final_signal,
            "confidence": final_confidence,
            "imbalance": imbalance,
            "hidden_liquidity": hidden_liq,
            "spoofing": spoofing,
            "timestamp": datetime.utcnow().isoformat()
        }
