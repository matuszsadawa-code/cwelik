"""
OpenClaw Trading System — Main Entry Point v3 (Real-Time)

Autonomous trading signal system with REAL-TIME monitoring:
- Persistent WebSocket connections to ByBit + Binance
- Trade-by-trade processing into all analyzers
- Intelligent signal trigger (volatility, delta, volume thresholds)
- Market regime adaptation (TRENDING/RANGING/VOLATILE/QUIET)
- Full analytics context saved per signal
- Signal lifecycle tracking with MFE/MAE/TP/SL

Usage:
    python -m trading_system.main                  # Real-time continuous
    python -m trading_system.main --once           # Single scan
    python -m trading_system.main --report         # Performance report
    python -m trading_system.main --realtime       # Real-time + periodic hybrid
"""

import sys
import time
import signal as sig
import argparse
import asyncio
from typing import Dict, List
from datetime import datetime, timezone

from config import STRATEGY, SYMBOLS
from data.symbol_manager import SymbolManager
from data.bybit_client import BybitClient, BybitWebSocket
from data.binance_client import BinanceClient, BinanceWebSocket
from data.bybit_client_async import AsyncBybitClient
from data.binance_client_async import AsyncBinanceClient
from data.candle_manager import CandleManager
from data.candle_manager_async import AsyncCandleManager
from data.orderbook import OrderBookManager
from data.trade_flow import TradeFlowAnalyzer
from data.footprint import FootprintAnalyzer
from data.advanced_orderflow import AdvancedOrderFlow
from data.crypto_analytics import CryptoAnalytics
from data.realtime_monitor import RealtimeMonitor
from strategy.signal_engine import SignalEngine
from strategy.market_structure import MarketStructureAnalyzer
from strategy.market_regime import MarketRegimeDetector
from analytics.signal_tracker import SignalTracker
from analytics.performance import PerformanceReporter
from storage.database import Database
from execution.order_executor import OrderExecutor, ExecutionMode
from execution.position_manager import PositionManager
from execution.portfolio import PortfolioManager
from utils.logger import get_logger

log = get_logger("main")

# Polymarket integration
try:
    from polymarket import PolymarketClient, PolymarketExecutor
    from polymarket.config import (
        POLYMARKET_ENABLED, POLYMARKET_API_KEY, POLYMARKET_API_SECRET,
        POLYMARKET_TESTNET, POLYMARKET_BANKROLL, POLYMARKET_MAX_EXPOSURE_PCT,
        POLYMARKET_MAX_BETS_PER_DAY, POLYMARKET_MIN_CONFIDENCE, POLYMARKET_BET_SIZING
    )
    POLYMARKET_AVAILABLE = True
except ImportError:
    POLYMARKET_AVAILABLE = False
    log.warning("Polymarket module not available")


class TradingSystem:
    """Full trading system orchestrator — real-time + periodic hybrid."""

    def __init__(self):
        log.info("=" * 60)
        log.info(">> OpenClaw Trading System v3.0 - Real-Time")
        log.info("   4-Step Confirmation + Advanced Order Flow")
        log.info("   ByBit + Binance | Footprint | SMC | Crypto Intel")
        log.info("   Real-Time WebSocket | Market Regime Adaptation")
        log.info("=" * 60)

        # ─── Core ─────────────────────────────────────────
        self.db = Database()
        self.bybit = BybitClient()
        self.binance = BinanceClient()
        
        # ─── Symbol Manager (Dynamic symbol list) ────────
        self.symbol_manager = SymbolManager(self.bybit)
        log.info(f"Symbol Manager initialized: {len(self.symbol_manager.fixed_symbols)} fixed symbols")
        
        # ─── Async Clients (for parallel processing) ─────
        self.bybit_async = None  # Lazy init
        self.binance_async = None  # Lazy init
        self.candle_mgr_async = None  # Lazy init

        # ─── Data Managers ────────────────────────────────
        self.candle_mgr = CandleManager(self.bybit, self.binance, self.db)
        self.orderbook = OrderBookManager(self.bybit, self.binance)
        self.trade_flow = TradeFlowAnalyzer(self.bybit, self.binance)

        # ─── Advanced Analytics ───────────────────────────
        self.footprint = FootprintAnalyzer()
        self.advanced_of = AdvancedOrderFlow()
        self.crypto = CryptoAnalytics(self.bybit, self.binance)
        self.market_struct = MarketStructureAnalyzer()
        self.regime_detector = MarketRegimeDetector()

        # ─── Execution Engine ─────────────────────────────
        self.executor = OrderExecutor(mode=ExecutionMode.DEMO)
        self.pos_manager = PositionManager()
        self.portfolio = PortfolioManager(
            executor=self.executor,
            pos_manager=self.pos_manager,
        )

        # ─── Strategy Engine ──────────────────────────────
        self.signal_engine = SignalEngine(
            candle_mgr=self.candle_mgr,
            orderbook=self.orderbook,
            trade_flow=self.trade_flow,
            footprint=self.footprint,
            advanced_of=self.advanced_of,
            crypto=self.crypto,
            market_structure=self.market_struct,
            db=self.db,
            position_manager=self.pos_manager,  # Pass position manager to prevent duplicate signals
        )

        # ─── Tracking ────────────────────────────────────
        self.tracker = SignalTracker(self.candle_mgr, self.db)
        self.reporter = PerformanceReporter(self.db)
        
        # ─── Polymarket Integration ───────────────────────
        self.polymarket_executor = None
        if POLYMARKET_AVAILABLE and POLYMARKET_ENABLED:
            try:
                polymarket_client = PolymarketClient(
                    api_key=POLYMARKET_API_KEY,
                    api_secret=POLYMARKET_API_SECRET,
                    testnet=POLYMARKET_TESTNET
                )
                polymarket_config = {
                    "bankroll": POLYMARKET_BANKROLL,
                    "max_exposure_pct": POLYMARKET_MAX_EXPOSURE_PCT,
                    "max_bets_per_day": POLYMARKET_MAX_BETS_PER_DAY,
                    "min_confidence": POLYMARKET_MIN_CONFIDENCE,
                    "bet_sizing": POLYMARKET_BET_SIZING,
                }
                self.polymarket_executor = PolymarketExecutor(polymarket_client, polymarket_config)
                log.info("✅ Polymarket integration enabled")
            except Exception as e:
                log.error(f"❌ Failed to initialize Polymarket: {e}")
                self.polymarket_executor = None

        # ─── Real-Time Monitor ────────────────────────────
        self.realtime = RealtimeMonitor(
            bybit=self.bybit,
            binance=self.binance,
            orderbook=self.orderbook,
            trade_flow=self.trade_flow,
            footprint=self.footprint,
            advanced_of=self.advanced_of,
            crypto=self.crypto,
            market_struct=self.market_struct,
            on_signal_trigger=self._on_realtime_trigger,
        )

        self.realtime.on_price_update = self._on_price_update

        self._running = False
        self._scan_count = 0
        self._realtime_signals = 0

        log.info("All components initialized [OK]")
        log.info(f"Execution mode: {self.executor.mode.value}")
        log.info(f"Symbols: {SYMBOLS}")
        log.info(f"Scan interval: {STRATEGY['scan_interval_seconds']}s")

    # ═══════════════════════════════════════════════════════════════════
    # REAL-TIME TRIGGER
    # ═══════════════════════════════════════════════════════════════════

    def _on_price_update(self, symbol: str, price: float):
        """Called by RealtimeMonitor on every tick — checks SL/TP in real-time."""
        self.tracker.update_price(symbol, price)

    async def _on_realtime_trigger(self, symbol: str):
        """Called by RealtimeMonitor when conditions warrant analysis."""
        try:
            log.info(f"[!] Real-time trigger for {symbol}")
            signal = self.signal_engine.analyze_symbol(symbol)
            if signal:
                # Detect and attach market regime
                candles_4h = self.candle_mgr.get_candles(symbol, "4h", limit=30)
                regime = self.regime_detector.detect_regime(symbol, candles_4h)
                signal["market_regime"] = regime.get("regime", "UNKNOWN")

                # Apply regime adjustments
                adjustments = regime.get("adjustments", {})
                if adjustments:
                    conf_bonus = adjustments.get("confidence_bonus", 0)
                    signal["confidence"] = max(0, min(100, signal["confidence"] + conf_bonus))

                self.db.save_signal(signal)
                self.tracker.track_signal(signal)
                self._print_signal(signal, regime)
                self._realtime_signals += 1

                # ─── EXECUTE SIGNAL ─────────────────────────
                exec_result = await self.portfolio.process_signal(signal)
                if exec_result:
                    self.db.save_execution(exec_result)
                    log.info(f"[AUTO] Executed: {exec_result['execution_id']}")
                
                # ─── POLYMARKET EXECUTION ───────────────────
                if self.polymarket_executor and signal.get("symbol") == "BTCUSDT":
                    try:
                        poly_result = self.polymarket_executor.execute_signal(signal)
                        if poly_result.get("status") == "SUCCESS":
                            log.info(f"[POLYMARKET] Bet placed: {poly_result.get('order_id', 'N/A')}")
                    except Exception as e:
                        log.error(f"[POLYMARKET] Execution failed: {e}")

                # Update position prices
                price = self.candle_mgr.get_current_price(symbol)
                if price:
                    self.pos_manager.update_symbol_price(symbol, price)

        except Exception as e:
            log.error(f"Real-time trigger error {symbol}: {e}", exc_info=True)

    # ═══════════════════════════════════════════════════════════════════
    # SCAN MODES
    # ═══════════════════════════════════════════════════════════════════

    async def run_once(self):
        """Single full analysis scan (all symbols)."""
        log.info(f"\n{'-'*60}")
        log.info(f"[SCAN] #{self._scan_count + 1} at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        log.info(f"{'-'*60}")

        # Get current symbol list (updates dynamically every 60 minutes)
        symbols = self.symbol_manager.get_symbols()
        log.info(f"Monitoring {len(symbols)} symbols (Fixed: {len(self.symbol_manager.fixed_symbols)}, Dynamic: {len(symbols) - len(self.symbol_manager.fixed_symbols)})")

        # Refresh candle data
        self.candle_mgr.refresh_all()

        for symbol in symbols:
            try:
                self.orderbook.update(symbol)
                self.trade_flow.update(symbol)

                current_price = self.candle_mgr.get_current_price(symbol)
                trades = self._get_recent_trades(symbol)

                if trades:
                    self.footprint.process_trades(symbol, trades)
                    self.advanced_of.update_cvd(symbol, trades)
                    self.advanced_of.process_tape(symbol, trades)

                ob_data = self.orderbook.get_orderbook(symbol)
                if ob_data:
                    self.advanced_of.update_dom(symbol, ob_data)
                    self.advanced_of.update_liquidity_view(symbol, ob_data, current_price)
                    self.advanced_of.update_pulse(symbol, ob_data, trades or [], current_price)

                # Detect market regime
                candles_4h = self.candle_mgr.get_candles(symbol, "4h", limit=30)
                regime = self.regime_detector.detect_regime(symbol, candles_4h)
                log.info(f"  [*] {symbol} regime: {regime['regime']} (ADX:{regime['adx']:.0f})")

            except Exception as e:
                log.error(f"Data update error {symbol}: {e}")

        # Run strategy
        signals = self.signal_engine.analyze_all()

        for signal in signals:
            # Attach regime
            regime = self.regime_detector.get_regime(signal["symbol"]) or {}
            signal["market_regime"] = regime.get("regime", "UNKNOWN")
            adjustments = regime.get("adjustments", {})
            if adjustments:
                signal["confidence"] = max(0, min(100, signal["confidence"] + adjustments.get("confidence_bonus", 0)))

            self.db.save_signal(signal)
            self.tracker.track_signal(signal)
            self._print_signal(signal, regime)

            # ─── EXECUTE SIGNAL ─────────────────────────
            exec_result = await self.portfolio.process_signal(signal)
            if exec_result:
                self.db.save_execution(exec_result)
                log.info(f"[AUTO] Executed: {exec_result['execution_id']}")

            # Update position prices
            price = self.candle_mgr.get_current_price(signal["symbol"])
            if price:
                self.pos_manager.update_symbol_price(signal["symbol"], price)

        self.tracker.update_all()
        self._scan_count += 1

        active = self.tracker.get_active_count()
        log.info(f"\n[STATS] Scan done: {len(signals)} new, {active} tracked")
        return signals

    # ═══════════════════════════════════════════════════════════
    # ASYNC METHODS - 16x FASTER PARALLEL PROCESSING
    # ═══════════════════════════════════════════════════════════

    async def _init_async_clients(self):
        """Initialize async clients (lazy initialization)."""
        if self.bybit_async is None:
            self.bybit_async = AsyncBybitClient()
            self.binance_async = AsyncBinanceClient()
            self.candle_mgr_async = AsyncCandleManager(
                self.bybit_async, 
                self.binance_async, 
                self.db
            )
            log.info("Async clients initialized for parallel processing")

    async def _close_async_clients(self):
        """Close async clients."""
        if self.candle_mgr_async:
            await self.candle_mgr_async.close()
            log.info("Async clients closed")

    async def run_once_async(self):
        """Async version of run_once() with PARALLEL processing (16x faster)."""
        await self._init_async_clients()
        
        log.info(f"\n{'-'*60}")
        log.info(f"[SCAN ASYNC] #{self._scan_count + 1} at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        log.info(f"{'-'*60}")

        # Get current symbol list (updates dynamically every 60 minutes)
        symbols = self.symbol_manager.get_symbols()
        log.info(f"Monitoring {len(symbols)} symbols (Fixed: {len(self.symbol_manager.fixed_symbols)}, Dynamic: {len(symbols) - len(self.symbol_manager.fixed_symbols)})")

        # Refresh candle data for ALL symbols in PARALLEL (2-3s instead of 37s!)
        log.info(f"Fetching candle data for {len(symbols)} symbols in parallel...")
        await self.candle_mgr_async.refresh_all(symbols)
        log.info("Candle data refreshed (async parallel)")

        # Process all symbols in PARALLEL
        log.info(f"Processing {len(symbols)} symbols in parallel...")
        await self._process_symbols_parallel(symbols)
        
        # Run strategy
        signals = self.signal_engine.analyze_all()

        # Process signals
        for signal in signals:
            regime = self.regime_detector.get_regime(signal["symbol"]) or {}
            signal["market_regime"] = regime.get("regime", "UNKNOWN")
            adjustments = regime.get("adjustments", {})
            if adjustments:
                signal["confidence"] = max(0, min(100, signal["confidence"] + adjustments.get("confidence_bonus", 0)))

            self.db.save_signal(signal)
            self.tracker.track_signal(signal)
            self._print_signal(signal, regime)

            exec_result = await self.portfolio.process_signal(signal)
            if exec_result:
                self.db.save_execution(exec_result)
                log.info(f"[AUTO] Executed: {exec_result['execution_id']}")

            price = self.candle_mgr.get_current_price(signal["symbol"])
            if price:
                self.pos_manager.update_symbol_price(signal["symbol"], price)

        self.tracker.update_all()
        self._scan_count += 1

        active = self.tracker.get_active_count()
        log.info(f"\n[STATS] Scan done: {len(signals)} new, {active} tracked")
        return signals

    async def _process_symbols_parallel(self, symbols):
        """Process all symbols in PARALLEL (async)."""
        tasks = [self._process_symbol_async(symbol) for symbol in symbols]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_symbol_async(self, symbol):
        """Process a single symbol (async version)."""
        try:
            self.orderbook.update(symbol)
            self.trade_flow.update(symbol)

            current_price = self.candle_mgr.get_current_price(symbol)
            trades = self._get_recent_trades(symbol)

            if trades:
                self.footprint.process_trades(symbol, trades)
                self.advanced_of.update_cvd(symbol, trades)
                self.advanced_of.process_tape(symbol, trades)

            ob_data = self.orderbook.get_orderbook(symbol)
            if ob_data:
                self.advanced_of.update_dom(symbol, ob_data)
                self.advanced_of.update_liquidity_view(symbol, ob_data, current_price)
                self.advanced_of.update_pulse(symbol, ob_data, trades or [], current_price)

            # Detect market regime (use cached candles from async fetch)
            candles_4h = await self.candle_mgr_async.get_candles(symbol, "240", limit=30)
            regime = self.regime_detector.detect_regime(symbol, candles_4h)
            log.info(f"  [*] {symbol} regime: {regime['regime']} (ADX:{regime['adx']:.0f})")

        except Exception as e:
            log.error(f"Data update error {symbol}: {e}")

    # ═══════════════════════════════════════════════════════════

    async def run_continuous(self):
        """Continuous monitoring: real-time WS + periodic full scans."""
        self._running = True
        interval = STRATEGY["scan_interval_seconds"]

        def shutdown(sig_num, frame):
            log.info("\n🛑 Shutdown...")
            self._running = False

        sig.signal(sig.SIGINT, shutdown)
        if hasattr(sig, "SIGTERM"):
            sig.signal(sig.SIGTERM, shutdown)

        # Start real-time WebSocket monitor
        log.info("Starting real-time WebSocket monitor...")
        self.realtime.start()

        log.info(f"Starting periodic scans (every {interval}s)...")
        log.info("Press Ctrl+C to stop\n")

        while self._running:
            try:
                await self.run_once()
            except Exception as e:
                log.error(f"Scan error: {e}", exc_info=True)

            if self._running:
                active = self.tracker.get_active_count()
                rt = self._realtime_signals
                log.info(f"[WAIT] Next in {interval}s (active:{active}, RT signals:{rt})")
                
                # Check for pending TP placements after scan
                tp_placed = await self.executor.check_and_place_tps()
                if tp_placed > 0:
                    log.info(f"✅ Placed TPs for {tp_placed} filled entry orders")
                
                for _ in range(interval):
                    if not self._running:
                        break
                    time.sleep(1)
                    
                    # Check for pending TP placements every 10 seconds during wait
                    if _ % 10 == 0 and _ > 0:
                        tp_placed = await self.executor.check_and_place_tps()
                        if tp_placed > 0:
                            log.info(f"✅ Placed TPs for {tp_placed} filled entry orders")
                    
                    # Update Polymarket positions every 60 seconds
                    if _ % 60 == 0 and _ > 0 and self.polymarket_executor:
                        try:
                            self.polymarket_executor.update_positions()
                        except Exception as e:
                            log.error(f"[POLYMARKET] Update error: {e}")

        self.realtime.stop()
        log.info("🛑 System stopped.")

    def run_realtime_only(self):
        """Real-time only mode (no periodic scans, pure WS-driven)."""
        self._running = True

        def shutdown(sig_num, frame):
            log.info("\n🛑 Shutdown...")
            self._running = False

        sig.signal(sig.SIGINT, shutdown)
        if hasattr(sig, "SIGTERM"):
            sig.signal(sig.SIGTERM, shutdown)

        # Initial data load
        log.info("Loading initial candle data...")
        self.candle_mgr.refresh_all()

        for symbol in SYMBOLS:
            candles_4h = self.candle_mgr.get_candles(symbol, "4h", limit=30)
            regime = self.regime_detector.detect_regime(symbol, candles_4h)
            log.info(f"  {symbol}: {regime['regime']} (ADX:{regime['adx']:.0f})")

        # Start pure real-time
        log.info("[RT] Starting pure real-time mode...")
        self.realtime.start()

        while self._running:
            try:
                # Periodically update slow data (candles, regime) every 5 min
                time.sleep(300)
                if not self._running:
                    break

                self.candle_mgr.refresh_all()
                for symbol in SYMBOLS:
                    candles_4h = self.candle_mgr.get_candles(symbol, "4h", limit=30)
                    self.regime_detector.detect_regime(symbol, candles_4h)

                self.tracker.update_all()
                active = self.tracker.get_active_count()
                log.info(f"[STATS] State: {active} active, {self._realtime_signals} RT signals total")

            except Exception as e:
                log.error(f"Background update error: {e}")

        self.realtime.stop()
        log.info("🛑 System stopped.")

    def print_report(self, days: int = 30):
        """Print performance report."""
        self.reporter.print_summary(days)

    # ═══════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════

    def _get_recent_trades(self, symbol: str, limit: int = 500) -> list:
        trades = []
        try:
            bb = self.bybit.get_trades(symbol, limit=limit)
            if bb:
                for t in bb:
                    trades.append({
                        "price": float(t.get("price", 0)),
                        "size": float(t.get("size", t.get("qty", 0))),
                        "side": t.get("side", "").upper(),
                        "time": int(t.get("time", 0)),
                        "exchange": "bybit",
                    })
        except Exception:
            pass
        try:
            bn = self.binance.get_agg_trades(symbol, limit=limit)
            if bn:
                for t in bn:
                    trades.append({
                        "price": float(t.get("price", t.get("p", 0))),
                        "size": float(t.get("quantity", t.get("q", 0))),
                        "side": "BUY" if t.get("is_buyer_maker") is False else "SELL",
                        "time": int(t.get("timestamp", t.get("T", 0))),
                        "exchange": "binance",
                    })
        except Exception:
            pass
        return sorted(trades, key=lambda t: t["time"])

    def _print_signal(self, signal: Dict, regime: Dict = None):
        d = signal["signal_type"]
        arrow = "^" if d == "LONG" else "v"
        r = regime.get("regime", "?") if regime else "?"

        print("\n" + "=" * 55)
        print(f"{arrow} SIGNAL: {d} {signal['symbol']} [{signal['quality']}]")
        print("=" * 55)
        print(f"  Confidence:  {signal['confidence']:.1f}%")
        print(f"  Entry:       ${signal['entry_price']:.2f}")
        print(f"  Stop Loss:   ${signal['sl_price']:.2f} ({signal.get('sl_distance_pct', 0.0):.2f}%)")
        print(f"  Take Profit: ${signal['tp_price']:.2f}")
        print(f"  R:R:         {signal['rr_ratio']:.1f}:1")
        print(f"  Regime:      {r}")
        print(f"  Reasoning:   {signal['reasoning']}")
        print("=" * 55 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="OpenClaw Trading System v3 — Real-Time Autonomous"
    )
    parser.add_argument("--once", action="store_true", help="Single scan")
    parser.add_argument("--async", dest="use_async", action="store_true", help="Use async parallel processing (16x faster)")
    parser.add_argument("--report", action="store_true", help="Performance report")
    parser.add_argument("--realtime", action="store_true", help="Pure real-time mode")
    parser.add_argument("--days", type=int, default=30, help="Report days")
    parser.add_argument("--symbols", nargs="+", default=None)

    args = parser.parse_args()

    if args.symbols:
        import trading_system.config as cfg
        cfg.SYMBOLS = args.symbols

    system = TradingSystem()

    if args.report:
        system.print_report(args.days)
    elif args.once:
        if args.use_async:
            # Use async parallel processing (16x faster!)
            log.info("[MODE] Async parallel processing enabled")
            asyncio.run(system.run_once_async())
        else:
            # Use sync sequential processing
            asyncio.run(system.run_once())
        system.print_report(7)
    elif args.realtime:
        system.run_realtime_only()
    else:
        asyncio.run(system.run_continuous())


if __name__ == "__main__":
    main()

