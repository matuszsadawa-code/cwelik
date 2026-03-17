"""
Signal Engine v2 — Full 4-step framework + Advanced Analytics.

Integrates ALL analysis modules:
- 4-step confirmation strategy (trend → zones → volume → order flow)
- Footprint / Volume Profile (POC, VAH, VAL)
- Market Structure (Order Blocks, FVGs, Liquidity Grabs, CHoCH)
- Advanced Order Flow (CVD, DOM, Tape, Market Pulse, Liquidity View)
- Crypto Analytics (Liquidation Zones, Sweeps, Funding, OI, L/S Ratio)
"""

import uuid
from datetime import datetime
from typing import List, Dict, Optional

from data.candle_manager import CandleManager
from data.orderbook import OrderBookManager
from data.trade_flow import TradeFlowAnalyzer
from data.footprint import FootprintAnalyzer
from data.advanced_orderflow import AdvancedOrderFlow
from data.crypto_analytics import CryptoAnalytics
from strategy.step1_trend import identify_trend, _identify_swings
from strategy.step2_zones import find_zones
from strategy.step3_volume import confirm_volume_exhaustion
from strategy.step4_orderflow import confirm_orderflow
from strategy.market_structure import MarketStructureAnalyzer
from strategy.risk_manager import calculate_risk
from strategy.phase1_adapter import Phase1Adapter

# Optional polymarket imports
try:
    from polymarket.whale_tracker import WhaleTracker
    from polymarket.advanced_strategies import AdvancedStrategies
    POLYMARKET_AVAILABLE = True
except ImportError:
    WhaleTracker = None
    AdvancedStrategies = None
    POLYMARKET_AVAILABLE = False

from analytics.vwap_bands import VWAPBands
from analytics.reversal_patterns import ReversalPatterns
from analytics.momentum_indicators import MomentumIndicators
from analytics.ict.killzones import ICTKillzones
from analytics.ict.ote import OptimalTradeEntry
from analytics.ict.premium_discount import PremiumDiscountAnalysis
from analytics.ict.power_of_3 import PowerOf3Analyzer
from analytics.ict.liquidity_pools import LiquidityPoolsAnalyzer
from analytics.vsa_analyzer import VolumeSpreadAnalyzer
from analytics.wyckoff_analyzer import WyckoffAnalyzer
from analytics.market_profile import MarketProfileAnalyzer
from analytics.liquidity_engineer import LiquidityEngineer
from analytics.smart_money_divergence import SmartMoneyDivergenceDetector
from analytics.mtf_confluence import MultiTimeframeAnalyzer
from analytics.orderbook_imbalance import OrderBookImbalanceDetector
from analytics.institutional_flow import InstitutionalFlowDetector
from analytics.seasonality import SeasonalityDetector
from analytics.news_sentiment import NewsSentimentAnalyzer
from strategy.dynamic_weights import DynamicWeightOptimizer
from strategy.volatility_regime import VolatilityRegimeAdapter
from ml.confidence_calibrator import MLConfidenceCalibrator
from storage.database import Database
from config.feature_flags import is_feature_enabled, get_feature_config
from config import STRATEGY, SYMBOLS, TIMEFRAMES
from utils.logger import get_logger

log = get_logger("strategy.engine")

QUALITY_MAP = {"A+": 4, "A": 3, "B": 2, "C": 1}
MIN_QUALITY = STRATEGY["min_quality_for_signal"]


class SignalEngine:
    """
    Full strategy engine with advanced analytics integration.

    4-step core + SMC/Order Flow/Crypto intelligence overlay.
    """

    def __init__(self, candle_mgr: CandleManager,
                 orderbook: OrderBookManager,
                 trade_flow: TradeFlowAnalyzer,
                 footprint: FootprintAnalyzer = None,
                 advanced_of: AdvancedOrderFlow = None,
                 crypto: CryptoAnalytics = None,
                 market_structure: MarketStructureAnalyzer = None,
                 db: Database = None,
                 position_manager=None):
        self.candles = candle_mgr
        self.orderbook = orderbook
        self.trade_flow = trade_flow
        self.footprint = footprint or FootprintAnalyzer()
        self.advanced_of = advanced_of or AdvancedOrderFlow()
        self.crypto = crypto
        self.market_struct = market_structure or MarketStructureAnalyzer()
        self.phase1 = Phase1Adapter()
        self.position_manager = position_manager  # Add position manager reference
        self.whale_tracker = WhaleTracker() if POLYMARKET_AVAILABLE else None
        self.advanced_strategies = AdvancedStrategies() if POLYMARKET_AVAILABLE else None
        self.vwap_bands = VWAPBands()
        self.reversal_patterns = ReversalPatterns()
        self.momentum_indicators = MomentumIndicators()
        
        # ICT Analytics (All 5 Components)
        self.ict_killzones = ICTKillzones()
        self.ict_ote = OptimalTradeEntry()
        self.ict_premium_discount = PremiumDiscountAnalysis()
        self.ict_power_of_3 = PowerOf3Analyzer()
        self.ict_liquidity_pools = LiquidityPoolsAnalyzer()
        
        # Phase 1 Features: VSA + Wyckoff + Market Profile + Liquidity Engineering + Smart Money Divergence
        self.vsa_analyzer = VolumeSpreadAnalyzer(config=get_feature_config("vsa_analysis"))
        self.wyckoff_analyzer = WyckoffAnalyzer(config=get_feature_config("wyckoff_method"))
        self.market_profile_analyzer = MarketProfileAnalyzer(config=get_feature_config("market_profile"))
        self.liquidity_engineer = LiquidityEngineer()
        self.smart_money_divergence = SmartMoneyDivergenceDetector(config=get_feature_config("smart_money_divergence"))
        
        # Phase 2 Features: Multi-Timeframe Confluence + Advanced Order Book Imbalance + Institutional Flow
        self.mtf_analyzer = MultiTimeframeAnalyzer(candle_mgr)
        self.orderbook_imbalance = OrderBookImbalanceDetector(config=get_feature_config("orderbook_imbalance"))
        self.institutional_flow = InstitutionalFlowDetector(config=get_feature_config("institutional_flow"))
        
        # Phase 2 Features: Volatility Regime Adaptive System + Seasonality Detection
        self.volatility_regime = VolatilityRegimeAdapter()
        self.seasonality_detector = SeasonalityDetector(config=get_feature_config("seasonality_detection"))
        
        # Phase 4 Features: News Sentiment Integration + Market Microstructure Analysis
        self.news_sentiment = None
        if is_feature_enabled("news_sentiment"):
            news_config = get_feature_config("news_sentiment").copy()
            # Get API key from main config
            from config import CRYPTOPANIC_API_KEY, NEWSAPI_KEY
            api_provider = news_config.get("api_provider", "cryptopanic")
            if api_provider == "cryptopanic":
                news_config["api_key"] = CRYPTOPANIC_API_KEY
            elif api_provider == "newsapi":
                news_config["api_key"] = NEWSAPI_KEY
            self.news_sentiment = NewsSentimentAnalyzer(config=news_config)
        
        self.microstructure_analyzer = None
        if is_feature_enabled("market_microstructure"):
            from analytics.microstructure import MicrostructureAnalyzer
            self.microstructure_analyzer = MicrostructureAnalyzer(config=get_feature_config("market_microstructure"))
        
        # Phase 3 Features: ML Confidence Calibration
        self.ml_calibrator = None
        if db and is_feature_enabled("ml_confidence_calibration"):
            self.ml_calibrator = MLConfidenceCalibrator(db, config=get_feature_config("ml_confidence_calibration"))
            # Auto-train on initialization if needed
            if self.ml_calibrator.should_retrain():
                log.info("Training ML confidence calibrator on initialization...")
                self.ml_calibrator.train_model()
        
        # Dynamic Weights Optimizer
        self.dynamic_weights = DynamicWeightOptimizer()
        
        self._last_signals: Dict[str, Dict] = {}
        log.info("SignalEngine v13 initialized (Dynamic Weights + ICT Killzones + OTE + Premium/Discount + Power of 3 + Liquidity + VWAP + Reversal + Momentum + Phase 1/2/3 + VSA + Wyckoff + Market Profile + Liquidity Engineering + Smart Money Divergence + MTF Confluence + Order Book Imbalance + Institutional Flow + Volatility Regime + Seasonality Detection + News Sentiment + Market Microstructure + ML Confidence Calibration)")

    def analyze_symbol(self, symbol: str, update_data: bool = True) -> Optional[Dict]:
        """
        Run the full 4-step ICT framework on a symbol.
        Returns signal dictionary if quality >= config threshold, else None.
        """
        # DIAGNOSTIC: Log entry point
        log.info(f"[ANALYZE_SYMBOL] Called for {symbol}, update_data={update_data}")
        
        # Check if symbol is excluded due to price mismatch
        if hasattr(self.candles, 'is_symbol_excluded') and self.candles.is_symbol_excluded(symbol):
            log.warning(f"[SKIPPED] {symbol} - excluded due to price mismatch")
            return None
        
        # Check if we already have an open position for this symbol
        if self.position_manager:
            existing_position = self.position_manager.get_position_for_symbol(symbol)
            if existing_position and existing_position.is_open:
                log.info(f"[SKIPPED] {symbol} - already have open {existing_position.direction} position (ID: {existing_position.execution_id})")
                return None
        
        log.info(f"{'='*60}")
        log.info(f"Analyzing {symbol}...")

        steps_confirmed = []
        step_data = {}
        advanced_data = {}

        # ─── STEP 1: Identify 4H Trend ───────────────────────────────
        log.info(f"[ANALYZE_SYMBOL] Fetching 4H candles for {symbol}...")
        candles_4h = self.candles.get_candles(
            symbol, TIMEFRAMES["trend"],
            limit=STRATEGY["trend_candle_count"]
        )
        log.info(f"[ANALYZE_SYMBOL] Got {len(candles_4h) if candles_4h else 0} 4H candles for {symbol}")
        
        trend = identify_trend(candles_4h)
        step_data["step1"] = trend

        if trend and trend["direction"] != "UNCLEAR":
            steps_confirmed.append("STEP1_TREND")
            log.info(f"  [OK] STEP 1: {trend['direction']} ({trend['confidence']}%) — {trend['structure']}")
        else:
            # Guide: UNCLEAR STRUCTURE → AVOID ALL TRADES (hard block)
            log.info(f"  [NO] STEP 1: {'UNCLEAR trend — NO TRADES (guide rule)' if trend else 'No data — skipping'}")
            return None

        # ─── PHASE 1 FEATURE: Wyckoff Method Analysis ─────────────────
        # Analyze Wyckoff phases and events after trend identification
        try:
            if is_feature_enabled("wyckoff_method") and candles_4h:
                # Extract volume from candles
                volume_data = [c.get('volume', 0) for c in candles_4h]
                wyckoff_result = self.wyckoff_analyzer.analyze(candles_4h, volume_data, symbol)
                advanced_data["wyckoff"] = wyckoff_result
                
                if wyckoff_result and wyckoff_result.phase.phase != "UNKNOWN":
                    log.info(
                        f"  >> WYCKOFF: {wyckoff_result.phase.phase} phase "
                        f"(conf: {wyckoff_result.phase.confidence:.0f}%, "
                        f"score: {wyckoff_result.phase_score:.0f}/100, "
                        f"bias: {wyckoff_result.bias})"
                    )
                    
                    # Log high-confidence events (Spring/Upthrust)
                    for event in wyckoff_result.recent_events:
                        if event.event_type in ["SPRING", "UPTHRUST"] and event.confidence > 80:
                            log.info(
                                f"     [!] {event.event_type} detected at ${event.price:.2f} "
                                f"(conf: {event.confidence:.0f}%) - {event.description}"
                            )
                        elif event.event_type in ["SOS", "SOW", "LPS", "LPSY"]:
                            log.info(
                                f"     {event.event_type} at ${event.price:.2f} "
                                f"(conf: {event.confidence:.0f}%)"
                            )
        except Exception as e:
            log.debug(f"  Wyckoff error: {e}")
            advanced_data["wyckoff"] = None

        # ─── PHASE 2 FEATURE: Seasonality and Cyclical Pattern Detection ───
        # Analyze time-based patterns after trend identification
        try:
            if is_feature_enabled("seasonality_detection"):
                # Get daily candles for seasonality analysis (365 days)
                candles_daily = self.candles.get_candles(
                    symbol, "1440",  # Daily timeframe
                    limit=365
                )
                
                # Get intraday candles for time-of-day analysis
                candles_1h = self.candles.get_candles(
                    symbol, "60",  # 1H timeframe
                    limit=168  # 1 week of hourly data
                )
                
                seasonality_result = self.seasonality_detector.analyze_comprehensive(
                    symbol, candles_daily, candles_1h
                )
                advanced_data["seasonality"] = seasonality_result
                
                if seasonality_result and seasonality_result.get("has_seasonal_bias"):
                    bias = seasonality_result["seasonal_bias"]
                    log.info(
                        f"  >> SEASONALITY: {bias['bias']} bias detected "
                        f"({bias['pattern_type']}, accuracy: {bias['accuracy']:.0f}%, "
                        f"boost: +{bias['confidence_boost']:.0f}%) - {bias['description']}"
                    )
                    
                    # Log detected patterns
                    if seasonality_result["day_of_week"]["detected"]:
                        dow = seasonality_result["day_of_week"]
                        log.info(
                            f"     Day-of-Week: Best={dow['best_day']}, "
                            f"Worst={dow['worst_day']}, "
                            f"Strength={dow['pattern_strength']:.0f}/100"
                        )
                    
                    if seasonality_result["time_of_day"]["detected"]:
                        tod = seasonality_result["time_of_day"]
                        log.info(
                            f"     Time-of-Day: Best={tod['best_session']}, "
                            f"Worst={tod['worst_session']}, "
                            f"Strength={tod['pattern_strength']:.0f}/100"
                        )
                    
                    if seasonality_result["cycles"]["detected"]:
                        cycles = seasonality_result["cycles"]
                        cycle_periods = ', '.join([f"{c['period_days']:.1f}d" for c in cycles['cycles'][:3]])
                        log.info(
                            f"     Cyclical: {cycles['count']} cycles detected "
                            f"({cycle_periods})"
                        )
        except Exception as e:
            log.debug(f"  Seasonality error: {e}")
            advanced_data["seasonality"] = None

        # ─── STEP 2: Find 30M Zones ──────────────────────────────────
        current_price = self.candles.get_current_price(symbol)

        if trend and trend["direction"] != "UNCLEAR":
            candles_30m = self.candles.get_candles(
                symbol, TIMEFRAMES["zones"],
                limit=STRATEGY["zone_candle_count"]
            )
            zones = find_zones(candles_30m, trend["direction"], current_price)
            step_data["step2"] = zones

            if zones:
                steps_confirmed.append("STEP2_ZONES")
                log.info(
                    f"  [OK] STEP 2: {zones['zone_type']} zone at "
                    f"${zones['zone_low']:.2f}-${zones['zone_high']:.2f} "
                    f"(strength: {zones['strength']})"
                )
            else:
                log.info(f"  [X] STEP 2: No valid zones near ${current_price:.2f}")
        else:
            zones = None
            step_data["step2"] = None

        # ─── PHASE 1 FEATURE: Market Profile (TPO) Analysis ───────────
        # Build TPO chart and analyze value area after zones are identified
        try:
            if is_feature_enabled("market_profile") and candles_30m:
                market_profile = self.market_profile_analyzer.build_profile(candles_30m, symbol=symbol)
                
                if market_profile:
                    # Generate trading signal based on price position
                    tpo_signal = self.market_profile_analyzer.generate_signal(current_price, market_profile)
                    
                    advanced_data["market_profile"] = {
                        "profile": market_profile,
                        "signal": tpo_signal
                    }
                    
                    log.info(
                        f"  >> MARKET PROFILE: POC=${market_profile.poc:.2f}, "
                        f"VAH=${market_profile.vah:.2f}, VAL=${market_profile.val:.2f}, "
                        f"Shape: {market_profile.profile_shape}"
                    )
                    log.info(
                        f"     Signal: {tpo_signal.signal_type} (conf: {tpo_signal.confidence:.0f}%), "
                        f"Position: {tpo_signal.value_area_position}, "
                        f"POC dist: {tpo_signal.poc_distance_pct:.2f}%"
                    )
                    
                    if tpo_signal.target_price:
                        log.info(f"     Target: ${tpo_signal.target_price:.2f} (poor extreme)")
                    
                    # Log poor highs/lows if present
                    if market_profile.poor_highs:
                        log.info(f"     Poor Highs: {[f'${p:.2f}' for p in market_profile.poor_highs]}")
                    if market_profile.poor_lows:
                        log.info(f"     Poor Lows: {[f'${p:.2f}' for p in market_profile.poor_lows]}")
                else:
                    advanced_data["market_profile"] = None
        except Exception as e:
            log.debug(f"  Market Profile error: {e}")
            advanced_data["market_profile"] = None

        # ─── STEP 3: Volume Confirmation ──────────────────────────────
        candles_5m = self.candles.get_candles(
            symbol, TIMEFRAMES["confirmation"],
            limit=STRATEGY["volume_candle_count"]
        )

        if zones:
            volume = confirm_volume_exhaustion(candles_5m, zones)
            step_data["step3"] = volume

            if volume and volume["exhaustion_confirmed"]:
                steps_confirmed.append("STEP3_VOLUME")
                log.info(f"  [OK] STEP 3: Volume {volume['volume_trend']} (ratio: {volume['volume_ratio']:.2f})")
            else:
                log.info(f"  [X] STEP 3: {volume['volume_trend'] if volume else 'No data'}")
        else:
            volume = None
            step_data["step3"] = None

        # ─── PHASE 1 FEATURE: Volume Spread Analysis (VSA) ────────────
        # Analyze volume-spread relationship for market maker manipulation
        try:
            if is_feature_enabled("vsa_analysis") and candles_5m:
                vsa_result = self.vsa_analyzer.analyze(candles_5m, symbol)
                advanced_data["vsa"] = vsa_result
                
                if vsa_result and vsa_result.vsa_score != 50.0:  # Non-neutral score
                    log.info(
                        f"  >> VSA: {vsa_result.bias} (score: {vsa_result.vsa_score:.0f}/100, "
                        f"{len(vsa_result.signals)} signals)"
                    )
                    if vsa_result.dominant_signal:
                        log.info(
                            f"     Dominant: {vsa_result.dominant_signal.signal_type} "
                            f"(conf: {vsa_result.dominant_signal.confidence:.0f}%)"
                        )
        except Exception as e:
            log.debug(f"  VSA error: {e}")
            advanced_data["vsa"] = None

        # ─── STEP 3.5: 5min Structure Shift (Guide Step 4 Entry) ──────
        # Guide: Wait for HH+HL (long) or LL+LH (short) on 5min before entry
        fivemin_shift = self._detect_5min_structure_shift(candles_5m, zones)
        step_data["step3_5_shift"] = fivemin_shift

        if fivemin_shift and fivemin_shift.get("shift_confirmed"):
            steps_confirmed.append("STEP3_5_STRUCTURE_SHIFT")
            log.info(f"  [OK] STEP 3.5: 5min shift {fivemin_shift['shift_type']} confirmed")
        else:
            log.info(f"  [X] STEP 3.5: No 5min structure shift detected")

        # ─── STEP 4: Order Flow Confirmation ──────────────────────────
        if volume:
            if update_data:
                self.orderbook.update(symbol)
                self.trade_flow.update(symbol)

            of_result = confirm_orderflow(
                symbol, volume["direction"],
                self.orderbook, self.trade_flow
            )
            step_data["step4"] = of_result

            if of_result and of_result["control_shift_confirmed"]:
                steps_confirmed.append("STEP4_ORDERFLOW")
                log.info(f"  [OK] STEP 4: Control shift (score: {of_result['score']}/100)")
            else:
                log.info(f"  [X] STEP 4: No control shift ({of_result['score']}/100)" if of_result else "  [X] STEP 4: No data")
        else:
            of_result = None
            step_data["step4"] = None

        # ─── ADVANCED ANALYTICS (always run, enriches signal) ─────────

        # Volume Profile / Footprint
        try:
            vol_profile = self.footprint.get_volume_profile(symbol)
            fp_imbalance = self.footprint.get_footprint_imbalance(symbol)
            advanced_data["volume_profile"] = vol_profile
            advanced_data["footprint_imbalance"] = fp_imbalance
            if vol_profile.get("poc"):
                log.info(f"  [VP] POC=${vol_profile['poc']:.0f}, VAH=${vol_profile.get('vah', 0):.0f}, VAL=${vol_profile.get('val', 0):.0f}")
        except Exception as e:
            log.debug(f"  Volume profile error: {e}")

        # Market Structure (OB, FVG, Liquidity Grabs)
        try:
            if candles_5m:
                price_delivery = self.market_struct.analyze_price_delivery(candles_5m, current_price)
                advanced_data["price_delivery"] = price_delivery
                obs = price_delivery.get("order_blocks", [])
                fvgs = price_delivery.get("fair_value_gaps", [])
                grabs = price_delivery.get("liquidity_grabs", [])
                log.info(f"  [SMC] {len(obs)} OBs, {len(fvgs)} FVGs, {len(grabs)} liquidity grabs")
        except Exception as e:
            log.debug(f"  Market structure error: {e}")

        # Advanced Order Flow (CVD, DOM, Tape, Pulse)
        try:
            of_complete = self.advanced_of.get_complete_orderflow(symbol, candles_5m)
            advanced_data["advanced_orderflow"] = of_complete
            cvd = of_complete.get("cvd", {})
            pulse = of_complete.get("pulse", {})
            log.info(
                f"  [OF] CVD {cvd.get('trend', '?')} ({cvd.get('acceleration', '?')}), "
                f"Pulse: {pulse.get('score', 0):.0f}/100 ({pulse.get('condition', '?')}), "
                f"Bias: {of_complete.get('overall_bias', '?')}"
            )
        except Exception as e:
            log.debug(f"  Advanced OF error: {e}")

        # ─── PHASE 2 FEATURE: Advanced Order Book Imbalance Detection ────
        # Detect iceberg orders, spoofing, flash imbalance, absorption
        try:
            if is_feature_enabled("orderbook_imbalance"):
                # Get recent trades for analysis
                recent_trades = list(self.trade_flow._trades.get(symbol, []))[-50:]
                
                # Get current orderbook
                self.orderbook.update(symbol)
                current_orderbook = self.orderbook.get_orderbook(symbol)
                
                # Run comprehensive analysis
                ob_imbalance_result = self.orderbook_imbalance.analyze_comprehensive(
                    symbol, current_orderbook, recent_trades
                )
                advanced_data["orderbook_imbalance"] = ob_imbalance_result
                
                if ob_imbalance_result:
                    log.info(
                        f"  >> ORDER BOOK IMBALANCE: {ob_imbalance_result['signal']} "
                        f"(conf: {ob_imbalance_result['confidence']:.0%}, "
                        f"pressure: {ob_imbalance_result['pressure_score']['score']:.0f}/100, "
                        f"imbalance: {ob_imbalance_result['imbalance']['imbalance_pct']:+.1f}%)"
                    )
                    
                    # Log special events
                    if ob_imbalance_result.get('icebergs_detected', 0) > 0:
                        log.info(
                            f"     [ICEBERG] {ob_imbalance_result['icebergs_detected']} iceberg orders detected"
                        )
                    
                    if ob_imbalance_result.get('spoofs_detected', 0) > 0:
                        log.info(
                            f"     [SPOOF] {ob_imbalance_result['spoofs_detected']} spoofing events detected"
                        )
                    
                    if ob_imbalance_result.get('flash_imbalance') and ob_imbalance_result['flash_imbalance'].get('detected'):
                        flash = ob_imbalance_result['flash_imbalance']
                        log.info(
                            f"     [FLASH] Flash imbalance: {flash['change_pct']:.1f}% change - {flash['direction']}"
                        )
                    
                    if ob_imbalance_result.get('absorption') and ob_imbalance_result['absorption'].get('detected'):
                        absorption = ob_imbalance_result['absorption']
                        log.info(
                            f"     [ABSORPTION] {absorption['side']} absorption at ${absorption['price']:.2f}: "
                            f"{absorption['volume_absorbed']:.0f} volume (conf: {absorption['confidence']:.0%})"
                        )
        except Exception as e:
            log.debug(f"  Order Book Imbalance error: {e}")
            advanced_data["orderbook_imbalance"] = None

        # ─── PHASE 2 FEATURE: Institutional Order Flow Patterns ───────
        # Detect institutional execution patterns (TWAP, VWAP, Iceberg, Layering, Sweeps)
        try:
            if is_feature_enabled("institutional_flow"):
                # Get recent trades for analysis
                recent_trades = list(self.trade_flow._trades.get(symbol, []))[-100:]
                
                # Get current orderbook
                self.orderbook.update(symbol)
                current_orderbook = self.orderbook.get_orderbook(symbol)
                
                # Get orderbook snapshots from orderbook_imbalance detector
                orderbook_snapshots = []
                if symbol in self.orderbook_imbalance.orderbook_snapshots:
                    orderbook_snapshots = list(self.orderbook_imbalance.orderbook_snapshots[symbol])
                
                # Run comprehensive analysis
                institutional_result = self.institutional_flow.analyze_comprehensive(
                    symbol, recent_trades, current_orderbook, orderbook_snapshots, candles_5m
                )
                advanced_data["institutional_flow"] = institutional_result
                
                if institutional_result:
                    log.info(
                        f"  >> INSTITUTIONAL FLOW: {institutional_result['signal']} "
                        f"(conf: {institutional_result['confidence']:.0%}, "
                        f"activity score: {institutional_result['institutional_activity_score']:.0f}/100, "
                        f"{institutional_result['patterns_detected']} patterns)"
                    )
                    
                    # Log detected patterns
                    if institutional_result['pattern_types']:
                        log.info(f"     Patterns: {', '.join(institutional_result['pattern_types'])}")
                    
                    # Log iceberg execution
                    if institutional_result['iceberg']['detected']:
                        iceberg = institutional_result['iceberg']
                        log.info(
                            f"     [ICEBERG] {iceberg['side']} execution: "
                            f"{iceberg['trade_count']} trades, vol {iceberg['volume']:.0f}, "
                            f"conf {iceberg['confidence']:.0%}"
                        )
                    
                    # Log algo execution
                    if institutional_result['algo_execution']['detected']:
                        algo = institutional_result['algo_execution']
                        log.info(
                            f"     [{algo['type']}] {algo['side']} algo: "
                            f"vol {algo['volume']:.0f}, participation {algo['participation_rate']:.1f}%, "
                            f"conf {algo['confidence']:.0%}"
                        )
                    
                    # Log layering
                    if institutional_result['layering']['detected']:
                        layering = institutional_result['layering']
                        log.info(
                            f"     [LAYERING] {layering['side']}: "
                            f"{layering['levels']} levels, vol {layering['volume']:.0f}, "
                            f"conf {layering['confidence']:.0%}"
                        )
                    
                    # Log sweep orders
                    if institutional_result['sweep']['detected']:
                        sweep = institutional_result['sweep']
                        log.info(
                            f"     [SWEEP] {sweep['side']} sweep: "
                            f"{sweep['levels_swept']} levels, vol {sweep['volume']:.0f}, "
                            f"conf {sweep['confidence']:.0%}"
                        )
        except Exception as e:
            log.debug(f"  Institutional Flow error: {e}")
            advanced_data["institutional_flow"] = None

        # ─── PHASE 4 FEATURE: Market Microstructure Analysis ──────────
        # Analyze spread dynamics, price impact, and order flow toxicity
        try:
            if is_feature_enabled("market_microstructure") and self.microstructure_analyzer:
                # Get recent trades for analysis
                recent_trades = list(self.trade_flow._trades.get(symbol, []))[-50:]
                
                # Get current orderbook
                self.orderbook.update(symbol)
                current_orderbook = self.orderbook.get_orderbook(symbol)
                
                # Get orderbook updates (if available)
                orderbook_updates = []
                if symbol in self.orderbook_imbalance.orderbook_snapshots:
                    # Convert snapshots to updates format
                    snapshots = list(self.orderbook_imbalance.orderbook_snapshots[symbol])[-10:]
                    orderbook_updates = [{"timestamp": s["timestamp"]} for s in snapshots]
                
                # Run comprehensive analysis
                microstructure_result = self.microstructure_analyzer.analyze_comprehensive(
                    symbol, current_orderbook, recent_trades, orderbook_updates
                )
                advanced_data["microstructure"] = microstructure_result
                
                if microstructure_result and "error" not in microstructure_result:
                    log.info(
                        f"  >> MICROSTRUCTURE: {microstructure_result['signal']} "
                        f"(conf: {microstructure_result['confidence']:.0%}, "
                        f"toxicity: {microstructure_result['order_flow']['toxicity_score']:.0f}/100, "
                        f"flow: {microstructure_result['order_flow']['flow_type']})"
                    )
                    
                    # Log spread information
                    spread_info = microstructure_result['spread']
                    log.info(
                        f"     Spread: bid-ask ${spread_info['bid_ask_spread']:.4f}, "
                        f"effective ${spread_info['effective_spread']:.4f}, "
                        f"mid ${spread_info['mid_price']:.2f}"
                    )
                    
                    # Log spread widening if detected
                    if microstructure_result['spread_widening']['detected']:
                        widening = microstructure_result['spread_widening']
                        log.warning(
                            f"     [SPREAD WIDENING] {widening['ratio']:.1f}x avg "
                            f"for {widening['duration_min']:.1f} min"
                        )
                    
                    # Log order flow characteristics
                    flow = microstructure_result['order_flow']
                    if flow['characteristics']:
                        log.info(f"     Flow characteristics: {', '.join(flow['characteristics'])}")
                    
                    # Log quote stuffing if detected
                    if microstructure_result['quote_stuffing']['detected']:
                        stuffing = microstructure_result['quote_stuffing']
                        log.warning(
                            f"     [QUOTE STUFFING] {stuffing['updates_per_sec']:.0f} updates/sec "
                            f"(cancel rate: {stuffing['cancel_rate']:.0%})"
                        )
                    
                    # Log price impact for key levels
                    if microstructure_result.get('price_impact'):
                        impacts = microstructure_result['price_impact']
                        # Log impact for $10k order
                        if 10000 in impacts:
                            impact_10k = impacts[10000]
                            log.info(
                                f"     Price Impact ($10k): "
                                f"buy {impact_10k['buy']['slippage_pct']:.2f}%, "
                                f"sell {impact_10k['sell']['slippage_pct']:.2f}%"
                            )
        except Exception as e:
            log.debug(f"  Microstructure error: {e}")
            advanced_data["microstructure"] = None

        # Crypto Analytics (Liquidation, Funding, OI, L/S)
        try:
            if self.crypto:
                crypto_data = self.crypto.get_full_analysis(
                    symbol, current_price, candles_5m
                )
                advanced_data["crypto"] = crypto_data
                funding = crypto_data.get("funding", {})
                oi = crypto_data.get("open_interest", {})
                sweeps = crypto_data.get("liquidation_sweeps", [])
                cascade = crypto_data.get("liquidation_cascade", {})
                log.info(
                    f"  [CRYPTO] Funding {funding.get('sentiment', '?')}, "
                    f"OI {oi.get('interpretation', '?')}, "
                    f"{len(sweeps)} liq sweeps, "
                    f"Cascade: {'[ALERT] YES' if cascade.get('cascade_detected') else 'No'}"
                )
        except Exception as e:
            log.debug(f"  Crypto analytics error: {e}")
            crypto_data = None

        # ─── PHASE 1 FEATURE: Smart Money Divergence Detector ─────────
        # Detect divergences between price and smart money indicators (CVD, OI, Funding)
        try:
            if is_feature_enabled("smart_money_divergence") and candles_5m:
                divergence_result = self.smart_money_divergence.analyze(
                    candles_5m, crypto_data, symbol
                )
                advanced_data["smart_money_divergence"] = divergence_result
                
                if divergence_result and divergence_result.divergences:
                    log.info(
                        f"  >> SMART MONEY DIVERGENCE: {divergence_result.bias} "
                        f"(score: {divergence_result.aggregate_score:.0f}/100, "
                        f"{len(divergence_result.divergences)} divergences)"
                    )
                    
                    # Log dominant divergence
                    if divergence_result.dominant_divergence:
                        div = divergence_result.dominant_divergence
                        log.info(
                            f"     Dominant: {div.divergence_class} {div.divergence_type} "
                            f"on {div.indicator} (strength: {div.strength:.0f}%, "
                            f"boost: +{div.confidence_boost:.0f}%)"
                        )
                        
                        # Log price and indicator swings
                        log.info(
                            f"     Price: ${div.price_swing[0]:.2f} → ${div.price_swing[1]:.2f}, "
                            f"{div.indicator}: {div.indicator_swing[0]:.2f} → {div.indicator_swing[1]:.2f}"
                        )
        except Exception as e:
            log.debug(f"  Smart Money Divergence error: {e}")
            advanced_data["smart_money_divergence"] = None

        # ─── PHASE 2 FEATURE: Multi-Timeframe Confluence System ───────
        # Analyze confluence across multiple timeframes (1M, 5M, 15M, 1H, 4H)
        try:
            if is_feature_enabled("mtf_confluence"):
                mtf_result = self.mtf_analyzer.analyze_confluence(symbol, current_price)
                advanced_data["mtf_confluence"] = mtf_result
                
                if mtf_result:
                    log.info(
                        f"  >> MTF CONFLUENCE: Alignment {mtf_result.timeframe_alignment_score:.0f}/100, "
                        f"Trend: {mtf_result.trend_alignment.dominant_trend} "
                        f"({mtf_result.trend_alignment.alignment_pct:.0f}% agreement)"
                    )
                    
                    # Log trend per timeframe
                    if mtf_result.trend_alignment.trends:
                        trends_str = ", ".join([f"{tf}:{t}" for tf, t in mtf_result.trend_alignment.trends.items()])
                        log.info(f"     Trends: {trends_str}")
                    
                    # Log confluence zones
                    if mtf_result.confluence_zones:
                        log.info(f"     {len(mtf_result.confluence_zones)} high confluence zones:")
                        for zone in mtf_result.confluence_zones[:3]:  # Top 3
                            log.info(
                                f"       {zone.zone_type} at ${zone.price_level:.2f} "
                                f"(strength: {zone.strength:.0f}%, TFs: {len(zone.timeframes)})"
                            )
                    
                    # Log timeframe divergence
                    if mtf_result.timeframe_divergence:
                        div = mtf_result.timeframe_divergence
                        log.info(
                            f"     [!] TIMEFRAME DIVERGENCE: Lower TF {div.lower_tf_trend} vs "
                            f"Higher TF {div.higher_tf_trend} (severity: {div.severity:.0f}%, "
                            f"recommendation: {div.recommendation})"
                        )
                    
                    # Log confidence adjustment
                    if mtf_result.confidence_adjustment != 0:
                        log.info(
                            f"     MTF Confidence Adjustment: {mtf_result.confidence_adjustment:+.0f}%"
                        )
        except Exception as e:
            log.debug(f"  MTF Confluence error: {e}")
            advanced_data["mtf_confluence"] = None

        # Phase 1 Enhanced Analytics (CVD + DOM enhancements)
        try:
            phase1_result = self.phase1.analyze(
                symbol, self.candles, self.orderbook, 
                self.trade_flow, self.advanced_of
            )
            advanced_data["phase1"] = phase1_result
            
            # CRITICAL: Check for directional conflict with high-confidence Phase 1
            if phase1_result and trend and trend["direction"] != "UNCLEAR":
                phase1_direction = phase1_result.get("direction")
                phase1_quality = phase1_result.get("quality")
                phase1_confidence = phase1_result.get("confidence", 0)
                
                # If Phase 1 is A+ or A with high confidence (>80%) and conflicts with Step 1
                if phase1_quality in ["A+", "A"] and phase1_confidence >= 80:
                    if phase1_direction != trend["direction"]:
                        # Record conflict for accuracy tracking
                        self.phase1.accuracy_tracker.record_conflict(
                            phase1_direction, 
                            trend["direction"], 
                            phase1_confidence / 100,  # Convert to 0-1
                            action="rejected"
                        )
                        
                        # Check if we should disable conflict detection due to low accuracy
                        if self.phase1.accuracy_tracker.should_disable_conflict_detection():
                            stats = self.phase1.accuracy_tracker.get_stats()
                            log.warning(
                                f"  [PHASE1 ACCURACY] Low accuracy detected: {stats['accuracy']:.1f}% "
                                f"(samples: {stats['sample_size']}). Allowing signal despite conflict."
                            )
                            # Record but don't reject
                            self.phase1.accuracy_tracker.record_prediction(
                                phase1_direction,
                                trend["direction"],
                                phase1_confidence / 100,
                                outcome="conflict_allowed"
                            )
                        else:
                            log.warning(
                                f"  [⚠️ CONFLICT] Step 1: {trend['direction']} vs "
                                f"Phase 1: {phase1_direction} {phase1_quality} ({phase1_confidence:.0f}%)"
                            )
                            log.warning(
                                f"  [REJECTED] Directional conflict with high-confidence Phase 1 analytics"
                            )
                            return None
                    else:
                        # Agreement - record for accuracy tracking
                        self.phase1.accuracy_tracker.record_prediction(
                            phase1_direction,
                            trend["direction"],
                            phase1_confidence / 100,
                            outcome="agreed"
                        )
        except Exception as e:
            log.debug(f"  Phase 1 error: {e}")
            advanced_data["phase1"] = None

        # Phase 2: Whale Tracking
        try:
            # Update whale tracker with current data
            recent_trades = list(self.trade_flow._trades.get(symbol, []))[-100:]
            self.orderbook.update(symbol)
            current_orderbook = self.orderbook.get_orderbook(symbol)
            
            self.whale_tracker.update(recent_trades, current_orderbook)
            
            # Analyze whale activity
            whale_result = self.whale_tracker.analyze_comprehensive(candles_5m)
            advanced_data["phase2_whale"] = whale_result
            
            if whale_result and whale_result.get("whale_signal") != "NEUTRAL":
                log.info(
                    f"  >> PHASE 2 (WHALE): {whale_result['whale_signal']} "
                    f"(confidence: {whale_result['confidence']:.0%})"
                )
        except Exception as e:
            log.debug(f"  Phase 2 error: {e}")
            advanced_data["phase2_whale"] = None

        # Phase 3: Advanced Strategies
        try:
            strategies_result = self.advanced_strategies.analyze_all(candles_5m)
            advanced_data["phase3_strategies"] = strategies_result
            
            if strategies_result and strategies_result.get("signal") != "NEUTRAL":
                log.info(
                    f"  >> PHASE 3 (STRATEGIES): {strategies_result['signal']} "
                    f"(confidence: {strategies_result['confidence']:.0%}, "
                    f"{strategies_result.get('agreement_count', 0)} strategies agree)"
                )
        except Exception as e:
            log.debug(f"  Phase 3 error: {e}")
            advanced_data["phase3_strategies"] = None

        # NEW: VWAP Standard Deviation Bands
        try:
            vwap_result = self.vwap_bands.calculate(candles_5m, period=100)
            advanced_data["vwap_bands"] = vwap_result
            
            if vwap_result:
                log.info(
                    f"  >> VWAP BANDS: Price ${vwap_result['current_price']:.2f}, "
                    f"VWAP ${vwap_result['vwap']:.2f}, "
                    f"Deviation: {vwap_result['deviation_from_vwap']:.2f}σ, "
                    f"Zone: {vwap_result['zone']}, Signal: {vwap_result['signal']}"
                )
        except Exception as e:
            log.debug(f"  VWAP Bands error: {e}")
            advanced_data["vwap_bands"] = None

        # NEW: Reversal Patterns
        try:
            patterns_result = self.reversal_patterns.analyze(candles_5m[-5:])
            advanced_data["reversal_patterns"] = patterns_result
            
            best_pattern = patterns_result.get("best_pattern")
            if best_pattern:
                log.info(
                    f"  >> REVERSAL PATTERN: {best_pattern['type']} "
                    f"({best_pattern['direction']}, confidence: {best_pattern['confidence']:.0f}%) "
                    f"- {best_pattern['description']}"
                )
        except Exception as e:
            log.debug(f"  Reversal Patterns error: {e}")
            advanced_data["reversal_patterns"] = None

        # NEW: Momentum Indicators
        try:
            momentum_result = self.momentum_indicators.calculate_all(candles_5m)
            advanced_data["momentum"] = momentum_result
            
            if momentum_result:
                rsi = momentum_result.get("rsi", {})
                macd = momentum_result.get("macd", {})
                log.info(
                    f"  >> MOMENTUM: Score {momentum_result['momentum_score']:.0f}/100, "
                    f"Signal: {momentum_result['signal']}, "
                    f"RSI: {rsi.get('value', 0):.0f} ({rsi.get('zone', '?')}), "
                    f"MACD: {macd.get('signal', '?')}"
                )
        except Exception as e:
            log.debug(f"  Momentum Indicators error: {e}")
            advanced_data["momentum"] = None

        # ═══ ICT ANALYTICS (5 COMPONENTS) ═══════════════════════════════
        
        # ICT 1: Killzones (time-based)
        try:
            killzone = self.ict_killzones.get_current_killzone()
            silver_bullet = self.ict_killzones.is_silver_bullet_time()
            
            advanced_data["ict_killzone"] = killzone
            advanced_data["ict_silver_bullet"] = silver_bullet
            
            if killzone['active']:
                log.info(f"  >> ICT KILLZONE: {killzone['killzone']} (boost: {killzone['confidence_boost']:+d}%, remaining: {killzone['time_remaining_minutes']}min)")
            
            if silver_bullet['is_silver_bullet']:
                log.info(f"  >> SILVER BULLET: {silver_bullet['type']} (boost: {silver_bullet['confidence_boost']:+d}%)")
        except Exception as e:
            log.debug(f"  ICT Killzone error: {e}")

        # ICT 2+3: OTE + Premium/Discount (use same swing points)
        try:
            swing_points = self.ict_ote.find_swing_points(candles_5m, lookback=50)
            
            if swing_points:
                ote_levels = self.ict_ote.calculate_ote_levels(
                    swing_points['swing_high'],
                    swing_points['swing_low'],
                    swing_points['direction']
                )
                
                ote_entry = self.ict_ote.check_ote_entry(current_price, ote_levels)
                
                advanced_data["ict_ote"] = {
                    'swing_points': swing_points,
                    'ote_levels': ote_levels,
                    'ote_entry': ote_entry,
                }
                
                if ote_entry['at_ote']:
                    log.info(f"  >> ICT OTE: At {ote_entry['ote_level']} (${ote_entry['ote_optimal_price']:.2f}, boost: {ote_entry['confidence_boost']:+d}%)")
                
                # Premium/Discount (same swing points)
                pd_zone = self.ict_premium_discount.classify_zone(
                    current_price,
                    swing_points['swing_high'],
                    swing_points['swing_low']
                )
                
                advanced_data["ict_premium_discount"] = pd_zone
                
                if pd_zone['zone'] != 'EQUILIBRIUM':
                    log.info(f"  >> ICT PREMIUM/DISCOUNT: {pd_zone['zone']} ({pd_zone['position_pct']:.1f}%, boost: {pd_zone['confidence_boost']:+d}%)")
        except Exception as e:
            log.debug(f"  ICT OTE/Premium-Discount error: {e}")

        # ICT 4: Power of 3 (manipulation phases)
        try:
            power_of_3 = self.ict_power_of_3.detect_phase(candles_5m, lookback=20)
            advanced_data["ict_power_of_3"] = power_of_3
            
            if power_of_3['phase'] != 'UNKNOWN':
                log.info(f"  >> ICT POWER OF 3: {power_of_3['phase']} (boost: {power_of_3['confidence_boost']:+d}%) - {power_of_3['description']}")
        except Exception as e:
            log.debug(f"  ICT Power of 3 error: {e}")

        # ICT 5: Liquidity Pools (round numbers)
        try:
            liquidity = self.ict_liquidity_pools.find_nearby_levels(current_price, symbol)
            advanced_data["ict_liquidity_pools"] = liquidity
            
            if liquidity['at_level']:
                closest = liquidity['closest_level']
                log.info(f"  >> ICT LIQUIDITY: At round number ${closest['level']:.0f} (boost: {liquidity['confidence_boost']:+d}%)")
        except Exception as e:
            log.debug(f"  ICT Liquidity Pools error: {e}")

        # ─── PHASE 1 FEATURE: Enhanced Liquidity Engineering ──────────
        # Advanced liquidity manipulation detection alongside ICT Liquidity Pools
        try:
            if is_feature_enabled("enhanced_liquidity") and candles_5m:
                # Get ICT trend for sweep alignment check
                ict_trend = trend.get("direction") if trend else None
                
                liquidity_eng_result = self.liquidity_engineer.analyze(
                    candles_5m, symbol, current_price, ict_trend
                )
                advanced_data["liquidity_engineering"] = liquidity_eng_result
                
                if liquidity_eng_result and liquidity_eng_result.get("analysis_complete"):
                    pools = liquidity_eng_result.get("pools", [])
                    sweeps = liquidity_eng_result.get("sweeps", [])
                    turtle_soup = liquidity_eng_result.get("turtle_soup")
                    unfilled = liquidity_eng_result.get("unfilled_pools", [])
                    
                    log.info(
                        f"  >> LIQUIDITY ENGINEERING: {len(pools)} pools, "
                        f"{len(sweeps)} sweeps, "
                        f"{len(unfilled)} unfilled"
                    )
                    
                    # Log high-confidence sweeps
                    for sweep in sweeps:
                        if sweep.confidence > 70:
                            log.info(
                                f"     [!] {sweep.direction} at ${sweep.sweep_price:.2f} "
                                f"(conf: {sweep.confidence:.0f}%, vol spike: {sweep.volume_spike:.1f}x)"
                            )
                    
                    # Log turtle soup if detected
                    if turtle_soup:
                        log.info(
                            f"     [TURTLE SOUP] {turtle_soup.direction} at ${turtle_soup.breakout_level:.2f} "
                            f"(conf: {turtle_soup.confidence:.0f}%)"
                        )
                    
                    # Log unfilled pools as targets
                    if unfilled:
                        log.info(f"     Unfilled pools: {[f'${p.level:.2f}' for p in unfilled[:3]]}")
        except Exception as e:
            log.debug(f"  Liquidity Engineering error: {e}")
            advanced_data["liquidity_engineering"] = None

        # ─── PHASE 2 FEATURE: Volatility Regime Adaptive System ───────
        # Analyze volatility regime and adjust parameters BEFORE signal generation
        volatility_regime_result = None
        regime_adjustments = None
        try:
            # Use 4H candles for volatility calculation (same as trend)
            volatility_regime_result = self.volatility_regime.analyze(candles_4h, symbol)
            advanced_data["volatility_regime"] = volatility_regime_result
            
            if volatility_regime_result:
                regime = volatility_regime_result["regime"]
                metrics = volatility_regime_result["metrics"]
                compression = volatility_regime_result["compression"]
                regime_adjustments = volatility_regime_result["adjustments"]
                
                log.info(
                    f"  >> VOLATILITY REGIME: {regime} "
                    f"(HV: {metrics.hv:.1f}%, percentile: {metrics.hv_percentile:.0f}%, "
                    f"ATR: ${metrics.atr:.2f})"
                )
                
                # Log regime adjustments
                log.info(
                    f"     Adjustments: min_quality={regime_adjustments.min_quality}, "
                    f"sl_buffer={regime_adjustments.sl_buffer_multiplier:.1f}x, "
                    f"leverage={regime_adjustments.leverage_multiplier:.1f}x"
                )
                
                # Log volatility compression if detected
                if compression.detected:
                    log.info(
                        f"     [!] VOLATILITY COMPRESSION: {compression.duration_days} days, "
                        f"ratio: {compression.compression_ratio:.2f}, "
                        f"breakout prob: {compression.breakout_probability:.0%}, "
                        f"boost: +{compression.confidence_boost:.0f}%"
                    )
        except Exception as e:
            log.debug(f"  Volatility Regime error: {e}")
            advanced_data["volatility_regime"] = None

        # ─── Quality + Signal Decision ────────────────────────────────
        num_confirmed = len(steps_confirmed)
        quality = self._get_quality(num_confirmed)

        # Dynamic confidence adjustment based on statistical performance
        direction = volume["direction"] if volume else (
            "LONG" if zones and zones["zone_type"] == "DEMAND" else "SHORT"
        )
        confidence_adj = self.dynamic_weights.calculate_adjustment(
            advanced_data, steps_confirmed, direction
        )
        
        # ─── PHASE 1 FEATURE: Wyckoff Confidence Boost ────────────────
        # Add +15% confidence boost for Spring/Upthrust with >80% confidence
        wyckoff_boost = 0
        wyckoff_data = advanced_data.get("wyckoff")
        if wyckoff_data and wyckoff_data.recent_events:
            for event in wyckoff_data.recent_events:
                if event.event_type in ["SPRING", "UPTHRUST"] and event.confidence > 80:
                    wyckoff_boost = 15
                    log.info(
                        f"  [WYCKOFF BOOST] +{wyckoff_boost}% for high-confidence "
                        f"{event.event_type} (conf: {event.confidence:.0f}%)"
                    )
                    break  # Only apply boost once
        
        confidence_adj += wyckoff_boost
        
        # ─── PHASE 1 FEATURE: Market Profile Confidence Boost ─────────
        # Add +12% confidence boost when price is at POC
        market_profile_boost = 0
        mp_data = advanced_data.get("market_profile")
        if mp_data and mp_data.get("profile"):
            profile = mp_data["profile"]
            mp_boost = self.market_profile_analyzer.get_poc_confidence_boost(current_price, profile)
            if mp_boost > 0:
                market_profile_boost = mp_boost
                log.info(
                    f"  [MARKET PROFILE BOOST] +{market_profile_boost}% for price at POC "
                    f"(${profile.poc:.2f})"
                )
        
        confidence_adj += market_profile_boost
        
        # ─── PHASE 1 FEATURE: Liquidity Engineering Confidence Boost ──
        # Add +18% confidence boost for liquidity sweep aligned with ICT trend
        liquidity_eng_boost = 0
        liq_eng_data = advanced_data.get("liquidity_engineering")
        if liq_eng_data and liq_eng_data.get("confidence_boost", 0) > 0:
            liquidity_eng_boost = liq_eng_data["confidence_boost"]
            # Boost is already calculated in the analyze method
        
        confidence_adj += liquidity_eng_boost
        
        # ─── PHASE 1 FEATURE: Smart Money Divergence Confidence Boost ─
        # Add +20% confidence for regular divergence with strength >75%
        # Add +10% confidence for hidden divergence
        divergence_boost = 0
        divergence_data = advanced_data.get("smart_money_divergence")
        if divergence_data and divergence_data.dominant_divergence:
            div = divergence_data.dominant_divergence
            divergence_boost = div.confidence_boost
            
            if divergence_boost > 0:
                log.info(
                    f"  [DIVERGENCE BOOST] +{divergence_boost:.0f}% for "
                    f"{div.divergence_class} {div.divergence_type} divergence "
                    f"on {div.indicator} (strength: {div.strength:.0f}%)"
                )
        
        confidence_adj += divergence_boost
        
        # ─── PHASE 2 FEATURE: Multi-Timeframe Confluence Confidence Adjustment ─
        # Add +25% confidence when all timeframes aligned
        # Apply -15% penalty for timeframe divergence
        mtf_boost = 0
        mtf_data = advanced_data.get("mtf_confluence")
        if mtf_data:
            mtf_boost = mtf_data.confidence_adjustment
            
            if mtf_boost != 0:
                log.info(
                    f"  [MTF BOOST] {mtf_boost:+.0f}% for timeframe "
                    f"{'alignment' if mtf_boost > 0 else 'divergence'}"
                )
        
        confidence_adj += mtf_boost
        
        # ─── PHASE 2 FEATURE: Order Book Imbalance Confidence Boost ───
        # Add +15% confidence for absorption aligned with ICT signal
        ob_imbalance_boost = 0
        ob_imbalance_data = advanced_data.get("orderbook_imbalance")
        if ob_imbalance_data:
            absorption = ob_imbalance_data.get("absorption")
            
            # Check if absorption is detected and aligned with signal direction
            if absorption and absorption.get("detected"):
                absorption_side = absorption.get("side")
                
                # BID absorption (buying pressure) aligns with LONG
                # ASK absorption (selling pressure) aligns with SHORT
                if (absorption_side == "BID" and direction == "LONG") or \
                   (absorption_side == "ASK" and direction == "SHORT"):
                    ob_imbalance_boost = 15
                    log.info(
                        f"  [OB IMBALANCE BOOST] +{ob_imbalance_boost}% for {absorption_side} "
                        f"absorption aligned with {direction} signal "
                        f"(conf: {absorption.get('confidence', 0):.0%})"
                    )
        
        confidence_adj += ob_imbalance_boost
        
        # ─── PHASE 2 FEATURE: Institutional Flow Confidence Boost ─────
        # Add +20% confidence when Institutional Activity Score >80%
        institutional_boost = 0
        institutional_data = advanced_data.get("institutional_flow")
        if institutional_data:
            activity_score = institutional_data.get("institutional_activity_score", 0)
            
            # High institutional activity (>80) indicates smart money participation
            if activity_score > 80:
                institutional_boost = 20
                log.info(
                    f"  [INSTITUTIONAL BOOST] +{institutional_boost}% for high institutional activity "
                    f"(score: {activity_score:.0f}/100, {institutional_data['patterns_detected']} patterns)"
                )
        
        confidence_adj += institutional_boost
        
        # ─── PHASE 2 FEATURE: Volatility Compression Confidence Boost ─
        # Add +15% confidence for volatility compression >5 days on breakout signals
        volatility_compression_boost = 0
        if volatility_regime_result:
            compression = volatility_regime_result.get("compression")
            if compression and compression.detected:
                # Check if this is a breakout signal (price breaking out of zone)
                # For simplicity, apply boost to all signals during compression
                volatility_compression_boost = compression.confidence_boost
                log.info(
                    f"  [VOLATILITY COMPRESSION BOOST] +{volatility_compression_boost:.0f}% for "
                    f"{compression.duration_days}-day compression (breakout prob: {compression.breakout_probability:.0%})"
                )
        
        confidence_adj += volatility_compression_boost
        
        # ─── PHASE 2 FEATURE: Seasonality Confidence Boost ────────────
        # Add +8% confidence when seasonal bias aligns with ICT signal
        seasonality_boost = 0
        seasonality_data = advanced_data.get("seasonality")
        if seasonality_data and seasonality_data.get("has_seasonal_bias"):
            seasonal_bias = seasonality_data["seasonal_bias"]
            bias_direction = seasonal_bias.get("bias")
            
            # Check if seasonal bias aligns with signal direction
            if (bias_direction == "BULLISH" and direction == "LONG") or \
               (bias_direction == "BEARISH" and direction == "SHORT"):
                seasonality_boost = seasonal_bias.get("confidence_boost", 8)
                log.info(
                    f"  [SEASONALITY BOOST] +{seasonality_boost:.0f}% for {bias_direction} seasonal bias "
                    f"aligned with {direction} signal ({seasonal_bias['pattern_type']}, "
                    f"accuracy: {seasonal_bias['accuracy']:.0f}%)"
                )
        
        confidence_adj += seasonality_boost
        
        # ─── PHASE 4 FEATURE: News Sentiment Integration ──────────────
        # Check for high-impact events and adjust confidence based on sentiment
        news_sentiment_adj = 0
        news_sentiment_data = None
        
        if self.news_sentiment and is_feature_enabled("news_sentiment"):
            try:
                # Check if signals should be blocked due to high-impact events
                if self.news_sentiment.should_block_signal(symbol):
                    log.warning(
                        f"  [NEWS SENTIMENT] Signal BLOCKED due to high-impact event(s) "
                        f"within {self.news_sentiment.high_impact_block_duration_hours}h"
                    )
                    return None
                
                # Calculate aggregate sentiment
                sentiment_score = self.news_sentiment.calculate_aggregate_sentiment(symbol)
                
                # Detect sentiment shifts
                sentiment_shift = self.news_sentiment.detect_sentiment_shift(symbol)
                
                # Build temporary signal dict for confidence adjustment
                temp_signal = {"direction": direction}
                
                # Get confidence adjustment based on sentiment alignment
                news_sentiment_adj = self.news_sentiment.get_confidence_adjustment(
                    temp_signal, sentiment_score
                )
                
                # Store sentiment data in advanced analytics
                news_sentiment_data = {
                    "sentiment_score": sentiment_score,
                    "sentiment_shift": sentiment_shift,
                    "confidence_adjustment": news_sentiment_adj
                }
                advanced_data["news_sentiment"] = news_sentiment_data
                
                # Log sentiment analysis
                log.info(
                    f"  >> NEWS SENTIMENT: {sentiment_score.sentiment} "
                    f"(score: {sentiment_score.score:+.1f}/100, "
                    f"{sentiment_score.news_count} news items, "
                    f"avg impact: {sentiment_score.avg_impact:.0f}/100)"
                )
                
                if news_sentiment_adj != 0:
                    log.info(
                        f"  [NEWS SENTIMENT ADJ] {news_sentiment_adj:+.0f}% for "
                        f"{sentiment_score.sentiment} sentiment with {direction} signal"
                    )
                
                # Log sentiment shift if detected
                if sentiment_shift:
                    log.warning(
                        f"  [SENTIMENT SHIFT] {sentiment_shift.change:+.1f} points in "
                        f"{sentiment_shift.duration_hours:.1f}h "
                        f"({sentiment_shift.previous_score:.1f} → {sentiment_shift.current_score:.1f})"
                    )
                
            except Exception as e:
                log.error(f"  News Sentiment error: {e}", exc_info=True)
                advanced_data["news_sentiment"] = None
        
        confidence_adj += news_sentiment_adj
        
        # ─── PHASE 4 FEATURE: Market Microstructure Confidence Adjustment ─
        # Add +12% confidence for toxic flow aligned with signal
        # Apply -10% penalty for spread widening
        microstructure_adj = 0
        microstructure_data = advanced_data.get("microstructure")
        
        if microstructure_data and "error" not in microstructure_data:
            # Check for toxic flow aligned with signal direction
            flow_data = microstructure_data.get("order_flow", {})
            if flow_data.get("flow_type") == "TOXIC":
                toxicity_score = flow_data.get("toxicity_score", 0)
                
                # Check if toxic flow aligns with signal direction
                microstructure_signal = microstructure_data.get("signal", "NEUTRAL")
                if microstructure_signal == direction:
                    # Toxic flow aligned with signal: +12% boost
                    microstructure_adj += 12
                    log.info(
                        f"  [MICROSTRUCTURE BOOST] +12% for TOXIC flow aligned with {direction} "
                        f"(toxicity: {toxicity_score:.0f}/100)"
                    )
            
            # Check for spread widening (uncertainty signal)
            if microstructure_data.get("spread_widening", {}).get("detected"):
                widening = microstructure_data["spread_widening"]
                # Spread widening: -10% penalty
                microstructure_adj -= 10
                log.info(
                    f"  [MICROSTRUCTURE PENALTY] -10% for spread widening "
                    f"({widening['ratio']:.1f}x avg for {widening['duration_min']:.1f} min)"
                )
            
            # Check for quote stuffing (manipulation signal)
            if microstructure_data.get("quote_stuffing", {}).get("detected"):
                # Quote stuffing: additional -5% penalty
                microstructure_adj -= 5
                log.info(
                    f"  [MICROSTRUCTURE PENALTY] -5% for quote stuffing detected"
                )
        
        confidence_adj += microstructure_adj
        
        # Log active dynamic weights for transparency
        active_features = self.dynamic_weights.get_feature_info(
            advanced_data, steps_confirmed, direction
        )
        for f in active_features:
            log.info(f"  [WEIGHT] {f['feature']} -> {f['weight']:+.1f} (dynamic: {f['dynamic']})")

        log.info(f"  [SUMMARY] {num_confirmed}/4 steps -> {quality} (adj: {confidence_adj:+.1f}%)")

        # ─── PHASE 2 FEATURE: Apply Volatility Regime Adjustments ─────
        # Adjust min_quality threshold based on volatility regime
        effective_min_quality = MIN_QUALITY
        if regime_adjustments:
            effective_min_quality = regime_adjustments.min_quality
            if effective_min_quality != MIN_QUALITY:
                log.info(
                    f"  [REGIME ADJUSTMENT] Min quality adjusted: {MIN_QUALITY} -> {effective_min_quality} "
                    f"(regime: {volatility_regime_result['regime']})"
                )
        
        if QUALITY_MAP.get(quality, 0) < QUALITY_MAP.get(effective_min_quality, 0):
            log.info(f"  [REJECTED] Quality {quality} < {effective_min_quality}")
            return None

        if not zones:
            log.info(f"  [REJECTED] No zones for entry")
            return None

        # ─── Build Signal ─────────────────────────────────────────────
        direction = volume["direction"] if volume else (
            "LONG" if zones["zone_type"] == "DEMAND" else "SHORT"
        )

        # Get VWAP from Step 3 for TP calculation (guide primary target)
        vwap_price = None
        if volume and volume.get("vwap"):
            vwap_price = volume["vwap"]

        risk = calculate_risk(
            direction=direction,
            zone_info=zones,
            current_price=current_price,
            vwap=vwap_price,
            advanced_data=advanced_data,
            regime_adjustments=regime_adjustments,
        )

        # ─── Guide Golden Rule: R:R ≥ 2:1 HARD CHECK ─────────────────
        if risk["rr_ratio"] < 2.0:
            log.info(f"  [REJECTED] R:R {risk['rr_ratio']:.1f}:1 < 2:1 (guide golden rule)")
            return None

        base_confidence = self._calc_confidence(step_data, num_confirmed)
        final_confidence = max(0, min(100, base_confidence + confidence_adj))
        
        # ─── PHASE 3 FEATURE: ML Confidence Calibration ───────────────
        # Apply ML calibration as final post-processing step
        raw_confidence = final_confidence
        if self.ml_calibrator and is_feature_enabled("ml_confidence_calibration"):
            try:
                # Check if retraining is needed
                if self.ml_calibrator.should_retrain():
                    log.info("  [ML CALIBRATION] Auto-retraining model...")
                    self.ml_calibrator.train_model()
                
                # Apply calibration
                calibrated_confidence = self.ml_calibrator.calibrate_confidence(raw_confidence)
                
                # Log calibration adjustment
                calibration_adjustment = calibrated_confidence - raw_confidence
                if abs(calibration_adjustment) > 0.5:  # Only log significant adjustments
                    log.info(
                        f"  [ML CALIBRATION] Confidence adjusted: {raw_confidence:.1f}% -> "
                        f"{calibrated_confidence:.1f}% (Δ{calibration_adjustment:+.1f}%)"
                    )
                
                final_confidence = calibrated_confidence
                
                # Store calibration info in advanced analytics
                advanced_data["ml_calibration"] = {
                    "raw_confidence": raw_confidence,
                    "calibrated_confidence": calibrated_confidence,
                    "adjustment": calibration_adjustment,
                    "model_stats": self.ml_calibrator.get_calibration_stats()
                }
                
            except Exception as e:
                log.error(f"  [ML CALIBRATION] Error: {e}, using raw confidence")
                advanced_data["ml_calibration"] = {
                    "error": str(e),
                    "raw_confidence": raw_confidence
                }

        signal = {
            "signal_id": f"SIG-{uuid.uuid4().hex[:12].upper()}",
            "symbol": symbol,
            "signal_type": direction,
            "quality": quality,
            "steps_confirmed": num_confirmed,
            "confidence": round(final_confidence, 2),
            "entry_price": current_price,
            "sl_price": risk["sl_price"],
            "tp1_price": risk["tp1_price"],
            "tp2_price": risk["tp2_price"],
            "tp_price": risk["tp1_price"],  # Backward compatibility
            "sl_distance_pct": risk["sl_distance_pct"],
            "rr_ratio": risk["rr_ratio"],
            "vwap_tp_valid": risk.get("vwap_tp_valid", False),
            "reasoning": self._build_reasoning(step_data, advanced_data, quality, steps_confirmed),
            "step1_data": trend,
            "step2_data": zones,
            "step3_data": volume,
            "step3_5_data": fivemin_shift,
            "step4_data": of_result,
            "advanced_analytics": advanced_data,
            "exchange": "cross",
            "created_at": datetime.utcnow().isoformat(),
            "status": "NEW",  # Lifecycle: NEW -> ENTRY_HIT -> TP_HIT/SL_HIT/EXPIRED
        }

        self._last_signals[symbol] = signal

        log.info(
            f"  [SIGNAL] {direction} {symbol} @ ${current_price:.2f} "
            f"(Q:{quality}, Conf:{final_confidence:.0f}%, "
            f"SL:${risk['sl_price']:.2f}, TP1:${risk['tp1_price']:.2f}, TP2:${risk['tp2_price']:.2f}, R:R {risk['rr_ratio']:.1f}:1)"
        )
        log.info(f"{'='*60}")

        return signal

    def analyze_all(self, symbols: List[str] = None) -> List[Dict]:
        """Run full analysis on all symbols."""
        symbols = symbols or SYMBOLS
        signals = []

        log.info(f"Starting analysis for {len(symbols)} symbols...")

        for symbol in symbols:
            try:
                signal = self.analyze_symbol(symbol, update_data=False)
                if signal:
                    signals.append(signal)
            except Exception as e:
                log.error(f"Error analyzing {symbol}: {e}", exc_info=True)

        log.info(f"Analysis complete: {len(signals)} signals from {len(symbols)} symbols")
        return signals

    def _detect_5min_structure_shift(self, candles_5m, zone_info):
        """
        Guide Step 4 Entry: Detect HH+HL (for LONG) or LL+LH (for SHORT) on 5min.

        When price enters a S&D zone on 30min, switch to 5min and wait for:
        - LONG entry: higher high + higher low (bullish structure shift)
        - SHORT entry: lower low + lower high (bearish structure shift)
        """
        if not candles_5m or len(candles_5m) < 10 or not zone_info:
            return {"shift_confirmed": False, "shift_type": "NONE"}

        # Use expanded visibility range (last 40)
        recent = candles_5m[-40:]
        swings = _identify_swings(recent, lookback=2)

        swing_highs = [s for s in swings if s["type"] == "high"]
        swing_lows = [s for s in swings if s["type"] == "low"]

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {"shift_confirmed": False, "shift_type": "INSUFFICIENT_SWINGS"}

        last_2_highs = swing_highs[-2:]
        last_2_lows = swing_lows[-2:]

        # Check for bullish shift (HH + HL) — for LONG entries
        has_hh = last_2_highs[1]["price"] > last_2_highs[0]["price"]
        has_hl = last_2_lows[1]["price"] > last_2_lows[0]["price"]

        # Check for bearish shift (LL + LH) — for SHORT entries
        has_ll = last_2_lows[1]["price"] < last_2_lows[0]["price"]
        has_lh = last_2_highs[1]["price"] < last_2_highs[0]["price"]

        zone_type = zone_info.get("zone_type", "")

        if zone_type == "DEMAND" and has_hh and has_hl:
            return {
                "shift_confirmed": True,
                "shift_type": "BULLISH_SHIFT",
                "hh": True, "hl": True,
                "last_higher_low": last_2_lows[1]["price"],
                "description": "5min HH+HL confirmed — bullish shift at demand zone",
            }
        elif zone_type == "SUPPLY" and has_ll and has_lh:
            return {
                "shift_confirmed": True,
                "shift_type": "BEARISH_SHIFT",
                "ll": True, "lh": True,
                "last_lower_high": last_2_highs[1]["price"],
                "description": "5min LL+LH confirmed — bearish shift at supply zone",
            }

        return {
            "shift_confirmed": False,
            "shift_type": "NO_MATCH",
            "zone_type": zone_type,
            "has_hh": has_hh, "has_hl": has_hl,
            "has_ll": has_ll, "has_lh": has_lh,
        }

    def _get_quality(self, num_confirmed: int) -> str:
        thresholds = STRATEGY["quality_thresholds"]
        for quality, threshold in sorted(thresholds.items(), key=lambda x: -x[1]):
            if num_confirmed >= threshold:
                return quality
        return "REJECT"

    def _calc_confidence(self, step_data: Dict, num_confirmed: int) -> float:
        scores = []
        if step_data.get("step1"):
            scores.append(step_data["step1"].get("confidence", 0))
        if step_data.get("step2"):
            scores.append(step_data["step2"].get("strength", 0))
        if step_data.get("step3") and step_data["step3"].get("exhaustion_confirmed"):
            vol_score = max(0, (1 - step_data["step3"]["volume_ratio"]) * 100 + 50)
            scores.append(min(100, vol_score))
        if step_data.get("step4"):
            scores.append(step_data["step4"].get("score", 0))
        if not scores:
            return 0
        avg = sum(scores) / len(scores)
        quality_mult = {4: 1.0, 3: 0.9, 2: 0.75, 1: 0.6}
        return round(avg * quality_mult.get(num_confirmed, 0.5), 2)



    def _build_reasoning(self, step_data: Dict, advanced_data: Dict,
                          quality: str, steps: List[str]) -> str:
        num_steps = len(steps)
        parts = [f"Quality: {quality} ({num_steps}/5)"]

        s1 = step_data.get("step1")
        if s1:
            parts.append(f"4H:{s1['direction']}")

        s2 = step_data.get("step2")
        if s2:
            parts.append(f"30M:{s2['zone_type']}@${s2['zone_low']:.0f}-${s2['zone_high']:.0f}")

        s3 = step_data.get("step3")
        if s3:
            parts.append(f"Vol:{s3['volume_trend']}({s3['volume_ratio']:.2f})")
            if s3.get("vwap"):
                parts.append(f"VWAP:${s3['vwap']:.0f}")

        s35 = step_data.get("step3_5_shift")
        if s35:
            shift_status = "[+]" if s35.get("shift_confirmed") else "[-]"
            parts.append(f"5minShift:{shift_status}{s35.get('shift_type', '?')}")

        s4 = step_data.get("step4")
        if s4:
            parts.append(f"OF:{s4['score']}/100")

        # Advanced analytics summary
        of = advanced_data.get("advanced_orderflow", {})
        if of.get("overall_bias"):
            parts.append(f"Bias:{of['overall_bias']}")

        pd = advanced_data.get("price_delivery", {})
        if pd.get("total_fresh_obs", 0) > 0:
            parts.append(f"OBs:{pd['total_fresh_obs']}")
        if pd.get("total_unfilled_fvgs", 0) > 0:
            parts.append(f"FVGs:{pd['total_unfilled_fvgs']}")

        crypto = advanced_data.get("crypto", {})
        if crypto.get("crypto_bias"):
            parts.append(f"Crypto:{crypto['crypto_bias']}")

        return " | ".join(parts)
