"""
Real-Time Market Monitor — WebSocket-driven continuous analysis.

The heart of autonomous trading. Instead of polling every 5 minutes,
this module maintains persistent WebSocket connections to both
ByBit and Binance, processing every trade and orderbook update
in real-time.

Architecture:
- Main thread: Orchestrates analysis cycles
- WS thread (ByBit): Receives trades + orderbook
- WS thread (Binance): Receives trades + orderbook
- Analysis triggers: Zone approach, volume exhaustion, OF shift

"The market rewards those who are ready when the moment comes."
"""

import time
import threading
import json
from typing import Dict, List, Optional, Callable
from collections import defaultdict
from datetime import datetime

from data.bybit_client import BybitClient, BybitWebSocket
from data.binance_client import BinanceClient, BinanceWebSocket
from data.candle_manager import CandleManager
from data.orderbook import OrderBookManager
from data.trade_flow import TradeFlowAnalyzer
from data.footprint import FootprintAnalyzer
from data.advanced_orderflow import AdvancedOrderFlow
from data.crypto_analytics import CryptoAnalytics
from strategy.market_structure import MarketStructureAnalyzer
from config import SYMBOLS
import logging as _stdlib_logging

from utils.logger import get_logger

log = get_logger("data.realtime")

# Standard-library logger under the same name so test handlers attached to
# logging.getLogger("data.realtime") receive messages too.
_std_log = _stdlib_logging.getLogger("data.realtime")
_std_log.setLevel(_stdlib_logging.INFO)


class RealtimeMonitor:
    """
    Continuous real-time market monitor.

    Maintains WebSocket streams to both exchanges and feeds
    every tick into the analysis pipeline. Triggers signal
    evaluation when market conditions change significantly.
    """

    def __init__(self,
                 bybit: BybitClient,
                 binance: BinanceClient,
                 orderbook: OrderBookManager,
                 trade_flow: TradeFlowAnalyzer,
                 footprint: FootprintAnalyzer,
                 advanced_of: AdvancedOrderFlow,
                 crypto: CryptoAnalytics,
                 market_struct: MarketStructureAnalyzer,
                 on_signal_trigger: Callable = None):

        self.bybit = bybit
        self.binance = binance
        self.orderbook = orderbook
        self.trade_flow = trade_flow
        self.footprint = footprint
        self.advanced_of = advanced_of
        self.crypto = crypto
        self.market_struct = market_struct
        self.on_signal_trigger = on_signal_trigger

        # WebSocket clients
        self.bybit_ws = BybitWebSocket()
        self.binance_ws = BinanceWebSocket()

        # Real-time state per symbol
        self._state: Dict[str, Dict] = {}
        self._trade_buffer: Dict[str, List] = defaultdict(list)
        self._ob_buffer: Dict[str, Dict] = {}
        self._last_analysis: Dict[str, float] = {}
        self._last_crypto_update: Dict[str, float] = {}

        # Control
        self._running = False
        self._lock = threading.Lock()
        
        # Reconnection logic
        self._reconnect_delay = 1.0  # Start with 1 second
        self._max_reconnect_delay = 60.0  # Max 60 seconds
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10  # Give up after 10 attempts
        
        # Heartbeat monitoring
        self._last_heartbeat = time.time()
        self._heartbeat_interval = 30  # 30 seconds
        self._heartbeat_thread = None
        self._process_thread = None

        self.on_price_update = None  # callback(symbol, price) — called on every tick

        # Thresholds for triggering re-analysis
        self.MIN_ANALYSIS_INTERVAL = 30   # Min seconds between analyses
        self.TRADE_BUFFER_SIZE = 100      # Trades before flush to analyzers
        self.CRYPTO_UPDATE_INTERVAL = 60  # Seconds between crypto data updates

        for symbol in SYMBOLS:
            self._state[symbol] = {
                "last_price": 0,
                "trade_count": 0,
                "buy_volume": 0,
                "sell_volume": 0,
                "delta": 0,
                "last_ob_update": 0,
                "volatility_1m": 0,
                "prices_1m": [],
            }

        log.info(f"RealtimeMonitor initialized for {len(SYMBOLS)} symbols with reconnection logic")

    # ═══════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════

    def start(self):
        """Start all WebSocket streams and processing with heartbeat monitoring."""
        self._running = True
        log.info("🔴 Starting real-time monitor...")

        # Start WebSocket connections
        self._start_websockets()
        
        # Start heartbeat monitor
        self._start_heartbeat_monitor()

        # Start processing thread (daemon=False so it doesn't terminate when main thread exits)
        self._process_thread = threading.Thread(
            target=self._processing_loop, daemon=False, name="realtime-processing"
        )
        self._process_thread.start()

        log.info("🟢 Real-time monitor active with heartbeat monitoring")
    
    def _start_websockets(self):
        """Start WebSocket connections."""
        try:
            # Subscribe to streams with callbacks
            for symbol in SYMBOLS:
                try:
                    # Convert symbol format: "BTC-USDT" → "BTCUSDT" (remove hyphen)
                    # ByBit and Binance WebSocket APIs expect non-hyphenated format
                    ws_symbol = symbol.replace("-", "")
                    
                    # Use original symbol for internal tracking, ws_symbol for subscriptions
                    sym = symbol  # capture for closure (original format for callbacks)
                    
                    log.info(f"Subscribing to WebSocket streams: {symbol} → {ws_symbol}")
                    
                    self.bybit_ws.subscribe_trades(ws_symbol, callback=lambda d, s=sym: self._on_bybit_trade(s, d))
                    self.bybit_ws.subscribe_orderbook(ws_symbol, callback=lambda d, s=sym: self._on_bybit_orderbook(s, d))
                    self.binance_ws.subscribe_agg_trades(ws_symbol, callback=lambda d, s=sym: self._on_binance_trade(s, d))
                    self.binance_ws.subscribe_orderbook(ws_symbol, callback=lambda d, s=sym: self._on_binance_orderbook(s, d))
                except Exception as e:
                    log.error(f"WS subscribe error for {symbol}: {e}")

            # Start WS connections
            try:
                self.bybit_ws.start()
                log.info("  ByBit WebSocket connected")
            except Exception as e:
                log.warning(f"  ByBit WS warning: {e}")

            try:
                self.binance_ws.start()
                log.info("  Binance WebSocket connected")
            except Exception as e:
                log.warning(f"  Binance WS warning: {e}")
            
            # Reset reconnection state on successful start
            self._reconnect_attempts = 0
            self._reconnect_delay = 1.0
            
        except Exception as e:
            log.error(f"Failed to start WebSockets: {e}")
            self._schedule_reconnect()
    
    def _start_heartbeat_monitor(self):
        """Start heartbeat monitoring thread."""
        def heartbeat_loop():
            while self._running:
                time.sleep(self._heartbeat_interval)
                
                # Check if heartbeat is stale
                time_since_heartbeat = time.time() - self._last_heartbeat
                
                # Log heartbeat status every 30 seconds
                log.info(f"Heartbeat OK - last update {time_since_heartbeat:.1f}s ago")
                
                if time_since_heartbeat > self._heartbeat_interval * 2:
                    log.warning(f"WebSocket heartbeat timeout ({time_since_heartbeat:.0f}s), reconnecting...")
                    self._reconnect()
                
                # Monitor processing thread health
                if self._process_thread is not None and not self._process_thread.is_alive() and self._running:
                    log.warning("Processing thread has died unexpectedly — monitor may be stalled")
        
        self._heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
    
    def _update_heartbeat(self, message_type: str = "unknown", exchange: str = "unknown"):
        """Update heartbeat timestamp (call on every message received)."""
        self._last_heartbeat = time.time()
        log.debug(f"Heartbeat updated on {message_type} from {exchange}")
    
    def _reconnect(self):
        """Reconnect WebSocket with exponential backoff."""
        if not self._running:
            return
        
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            log.error("Max reconnection attempts reached, stopping monitor")
            self._running = False
            return
        
        self._reconnect_attempts += 1
        log.info(f"Attempting reconnection {self._reconnect_attempts}/{self._max_reconnect_attempts}")
        
        try:
            # Stop existing connections without setting _running = False
            try:
                self.bybit_ws.stop()
            except Exception:
                pass
            try:
                self.binance_ws.stop()
            except Exception:
                pass
            
            # Wait with exponential backoff
            time.sleep(self._reconnect_delay)
            
            # Create fresh WS objects to avoid subscription list accumulation
            self.bybit_ws = BybitWebSocket()
            self.binance_ws = BinanceWebSocket()
            
            # Restart WebSockets (keeps _running = True so processing loop continues)
            self._start_websockets()
            
            log.info("Reconnection successful, resuming processing")
            
        except Exception as e:
            log.error(f"Reconnection failed: {e}")
            self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)
            self._schedule_reconnect()
    
    def _schedule_reconnect(self):
        """Schedule reconnection attempt."""
        if not self._running:
            return
        
        log.info(f"Scheduling reconnection in {self._reconnect_delay:.1f}s (attempt {self._reconnect_attempts + 1}/{self._max_reconnect_attempts})")
        
        def delayed_reconnect():
            time.sleep(self._reconnect_delay)
            self._reconnect()
        
        threading.Thread(target=delayed_reconnect, daemon=True).start()

    def stop(self):
        """Stop all streams and processing."""
        self._running = False
        try:
            self.bybit_ws.stop()
        except Exception:
            pass
        try:
            self.binance_ws.stop()
        except Exception:
            pass
        # Gracefully join the processing thread with a timeout
        if self._process_thread is not None and self._process_thread.is_alive():
            log.info("Waiting for processing thread to stop...")
            self._process_thread.join(timeout=10)
            if self._process_thread.is_alive():
                log.warning("Processing thread did not stop within timeout")
            else:
                log.info("Processing thread stopped cleanly")
        log.info("🔴 Real-time monitor stopped")

    # ═══════════════════════════════════════════════════════════════════
    # WEBSOCKET HANDLERS
    # ═══════════════════════════════════════════════════════════════════

    def _on_bybit_trade(self, symbol: str, data: Dict):
        """Handle ByBit trade tick."""
        self._update_heartbeat(message_type="trade", exchange="bybit")  # Update heartbeat on message
        trade = {
            "price": float(data.get("price", data.get("p", 0))),
            "size": float(data.get("size", data.get("v", 0))),
            "side": data.get("side", data.get("S", "")).upper(),
            "time": int(data.get("time", data.get("T", time.time() * 1000))),
            "exchange": "bybit",
        }
        self._process_trade(symbol, trade)

    def _on_binance_trade(self, symbol: str, data: Dict):
        """Handle Binance aggTrade tick."""
        self._update_heartbeat(message_type="trade", exchange="binance")  # Update heartbeat on message
        trade = {
            "price": float(data.get("p", 0)),
            "size": float(data.get("q", 0)),
            "side": "SELL" if data.get("m", False) else "BUY",
            "time": int(data.get("T", time.time() * 1000)),
            "exchange": "binance",
        }
        self._process_trade(symbol, trade)

    def _on_bybit_orderbook(self, symbol: str, data: Dict):
        """Handle ByBit orderbook update."""
        log.debug(f"[bybit] orderbook received for {symbol}")
        self._update_heartbeat(message_type="orderbook", exchange="bybit")  # Update heartbeat on message
        with self._lock:
            self._ob_buffer[f"bybit:{symbol}"] = data
            state = self._state.get(symbol, {})
            state["last_ob_update"] = time.time()

    def _on_binance_orderbook(self, symbol: str, data: Dict):
        """Handle Binance orderbook update."""
        log.debug(f"[binance] orderbook received for {symbol}")
        self._update_heartbeat(message_type="orderbook", exchange="binance")  # Update heartbeat on message
        with self._lock:
            self._ob_buffer[f"binance:{symbol}"] = data
            state = self._state.get(symbol, {})
            state["last_ob_update"] = time.time()

    # ═══════════════════════════════════════════════════════════════════
    # TRADE PROCESSING
    # ═══════════════════════════════════════════════════════════════════

    def _process_trade(self, symbol: str, trade: Dict):
        """Process a single trade tick — update all trackers."""
        with self._lock:
            state = self._state.get(symbol)
            if not state:
                return

            price = trade["price"]
            size = trade["size"]
            state["last_price"] = price
            state["trade_count"] += 1

            if trade["side"] == "BUY":
                state["buy_volume"] += size
                state["delta"] += size
            else:
                state["sell_volume"] += size
                state["delta"] -= size

            # Track 1-minute price for volatility
            now = time.time()
            state["prices_1m"].append((now, price))
            # Prune old (>60s)
            cutoff = now - 60
            state["prices_1m"] = [(t, p) for t, p in state["prices_1m"] if t > cutoff]

            # Calculate 1-min volatility
            if len(state["prices_1m"]) >= 2:
                prices = [p for _, p in state["prices_1m"]]
                min_price = min(prices)
                if min_price > 0:
                    state["volatility_1m"] = (max(prices) - min_price) / min_price * 100
                else:
                    state["volatility_1m"] = 0

            # Buffer trades for batch processing
            self._trade_buffer[symbol].append(trade)

            # Flush buffer when full
            if len(self._trade_buffer[symbol]) >= self.TRADE_BUFFER_SIZE:
                self._flush_trades(symbol)

            # Notify price update listeners (e.g. SignalTracker)
            if self.on_price_update and price > 0:
                self.on_price_update(symbol, price)

    def _flush_trades(self, symbol: str):
        """Flush trade buffer to all analyzers."""
        trades = self._trade_buffer[symbol]
        self._trade_buffer[symbol] = []

        if not trades:
            return

        try:
            # Feed to trade flow analyzer
            self.trade_flow.process_trades_batch(symbol, trades)
        except Exception as e:
            log.debug(f"Trade flow batch error: {e}")

        try:
            # Feed to footprint
            self.footprint.process_trades(symbol, trades)
        except Exception as e:
            log.debug(f"Footprint batch error: {e}")

        try:
            # Feed to advanced OF
            self.advanced_of.update_cvd(symbol, trades)
            self.advanced_of.process_tape(symbol, trades)
        except Exception as e:
            log.debug(f"Advanced OF batch error: {e}")

    # ═══════════════════════════════════════════════════════════════════
    # MAIN PROCESSING LOOP
    # ═══════════════════════════════════════════════════════════════════

    def _processing_loop(self):
        """
        Background loop that periodically:
        1. Flushes remaining trade buffers
        2. Updates DOM / Liquidity View from orderbook
        3. Updates crypto analytics (funding, OI, L/S)
        4. Checks if re-analysis should be triggered
        """
        log.info("Processing loop started")
        _std_log.info("Processing loop started")
        count = 0

        while self._running:
            count += 1
            
            # Collect statistics for this iteration
            total_trades = sum(self._state.get(s, {}).get("trade_count", 0) for s in SYMBOLS)
            symbols_with_trades = sum(1 for s in SYMBOLS if self._state.get(s, {}).get("trade_count", 0) > 0)
            
            msg = f"Processing loop iteration {count} - {len(SYMBOLS)} symbols, {total_trades} total trades, {symbols_with_trades} active"
            log.info(msg)
            _std_log.info(msg)

            try:
                now = time.time()

                for symbol in SYMBOLS:
                    # Flush remaining trades
                    if self._trade_buffer[symbol]:
                        with self._lock:
                            self._flush_trades(symbol)

                    # Update DOM from orderbook
                    try:
                        ob_data = self.orderbook.get_orderbook(symbol)
                        if ob_data:
                            state = self._state.get(symbol, {})
                            price = state.get("last_price", 0)
                            self.advanced_of.update_dom(symbol, ob_data)
                            if price > 0:
                                self.advanced_of.update_liquidity_view(
                                    symbol, ob_data, price
                                )
                    except Exception as e:
                        log.debug(f"DOM update error {symbol}: {e}")

                    # Update crypto analytics periodically
                    last_crypto = self._last_crypto_update.get(symbol, 0)
                    if now - last_crypto > self.CRYPTO_UPDATE_INTERVAL:
                        try:
                            self.crypto.update_funding(symbol)
                            self.crypto.update_open_interest(symbol)
                            self.crypto.update_long_short_ratio(symbol)
                            self._last_crypto_update[symbol] = now
                        except Exception as e:
                            log.debug(f"Crypto update error {symbol}: {e}")

                    # Check if analysis should be triggered
                    last_analysis = self._last_analysis.get(symbol, 0)
                    if now - last_analysis > self.MIN_ANALYSIS_INTERVAL:
                        if self._should_trigger_analysis(symbol):
                            self._trigger_analysis(symbol)
                            self._last_analysis[symbol] = now

                # Periodic alive signal every ~60 seconds (12 iterations * 5s)
                if count % 12 == 0:
                    alive_msg = f"Processing loop alive - iteration {count}"
                    log.info(alive_msg)
                    _std_log.info(alive_msg)
                    # Thread health self-check
                    if self._process_thread is not None and not self._process_thread.is_alive():
                        log.warning("Processing thread reports itself as not alive — unexpected state")

                time.sleep(5)  # Check every 5 seconds

            except Exception as e:
                log.error(f"Processing loop error: {e}", exc_info=True)
                continue

    def _should_trigger_analysis(self, symbol: str) -> bool:
        """
        Decide if we should re-run full analysis for this symbol.

        Triggers on:
        - High volatility (>0.3% in 1 min)
        - Large delta shift
        - Significant trade volume
        - Orderbook change
        """
        state = self._state.get(symbol, {})
        
        # Extract trigger conditions for logging
        volatility = state.get("volatility_1m", 0)
        delta = state.get("delta", 0)
        trade_count = state.get("trade_count", 0)
        buy_volume = state.get("buy_volume", 0)
        sell_volume = state.get("sell_volume", 0)
        total_vol = buy_volume + sell_volume
        delta_pct = abs(delta) / total_vol if total_vol > 0 else 0
        
        log.info(f"[{symbol}] Evaluating trigger: volatility={volatility:.4f}%, delta={delta:.4f} ({delta_pct:.2%}), trades={trade_count}")

        # High short-term volatility
        if volatility > 0.3:
            log.info(f"[{symbol}] ✓ TRIGGER PASSED: High volatility ({volatility:.4f}% > 0.3%)")
            return True

        # Large accumulated delta
        if abs(delta) > 0 and total_vol > 0:
            if delta_pct > 0.3:  # 30% delta skew
                log.info(f"[{symbol}] ✓ TRIGGER PASSED: Large delta skew ({delta_pct:.2%} > 30%, delta={delta:.4f})")
                return True

        # Sufficient trade activity (at least 50 trades in buffer period)
        if trade_count > 50:
            log.info(f"[{symbol}] ✓ TRIGGER PASSED: Sufficient trade activity ({trade_count} trades > 50)")
            # Reset counter
            state["trade_count"] = 0
            state["buy_volume"] = 0
            state["sell_volume"] = 0
            state["delta"] = 0
            return True

        log.info(f"[{symbol}] ✗ TRIGGER FAILED: No conditions met (vol={volatility:.4f}%, delta={delta_pct:.2%}, trades={trade_count})")
        return False

    def _trigger_analysis(self, symbol: str):
        """Trigger a full signal analysis for this symbol."""
        log.info(f"[{symbol}] 🔔 TRIGGERING ANALYSIS - Invoking callback")
        _std_log.info(f"[{symbol}] 🔔 TRIGGERING ANALYSIS - Invoking callback")
        
        if self.on_signal_trigger:
            try:
                # Check if callback is async
                import asyncio
                import inspect
                if inspect.iscoroutinefunction(self.on_signal_trigger):
                    # Schedule async callback as a task in the event loop
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(self.on_signal_trigger(symbol))
                        log.info(f"[{symbol}] ✓ Callback scheduled in event loop")
                    except RuntimeError:
                        # No event loop running, use asyncio.run
                        asyncio.run(self.on_signal_trigger(symbol))
                        log.info(f"[{symbol}] ✓ Callback executed via asyncio.run")
                else:
                    # Synchronous callback
                    self.on_signal_trigger(symbol)
                    log.info(f"[{symbol}] ✓ Synchronous callback executed")
            except Exception as e:
                log.error(f"Signal trigger error for {symbol}: {e}")
        else:
            log.warning(f"[{symbol}] ⚠ No callback registered (on_signal_trigger is None)")

    # ═══════════════════════════════════════════════════════════════════
    # STATE ACCESS
    # ═══════════════════════════════════════════════════════════════════

    def get_state(self, symbol: str) -> Dict:
        """Get current real-time state for a symbol."""
        with self._lock:
            state = self._state.get(symbol, {})
            return {
                "last_price": state.get("last_price", 0),
                "trade_count": state.get("trade_count", 0),
                "buy_volume": round(state.get("buy_volume", 0), 4),
                "sell_volume": round(state.get("sell_volume", 0), 4),
                "delta": round(state.get("delta", 0), 4),
                "volatility_1m": round(state.get("volatility_1m", 0), 4),
                "is_active": self._running,
            }

    def get_all_states(self) -> Dict[str, Dict]:
        """Get real-time state for ALL symbols."""
        return {s: self.get_state(s) for s in SYMBOLS}
