"""
Aggressive Configuration for Advanced Trading Optimization Features

This configuration uses lower thresholds and higher confidence boosts for a more
aggressive trading approach. Suitable for experienced traders in favorable market conditions.

Key Differences from Default:
- Lower detection thresholds (more signals generated)
- Higher confidence boosts (stronger adjustments)
- More lenient risk management limits
- Larger position sizing
- Faster reaction to market changes
"""

# ============================================================================
# 1. Volume Spread Analysis (VSA)
# ============================================================================
VSA_CONFIG = {
    "enabled": True,
    "high_volume_threshold": 1.3,  # 1.3x average volume (lower threshold)
    "narrow_spread_threshold": 0.75,  # 75% of average spread (more lenient)
    "wide_spread_threshold": 1.2,  # 120% of average spread (more lenient)
    "close_top_threshold": 0.75,  # Close in top 75% of range (more lenient)
    "close_bottom_threshold": 0.25,  # Close in bottom 25% of range (more lenient)
    "stopping_volume_multiplier": 1.8,  # 1.8x volume for absorption (lower)
    "lookback_period": 15,  # Fewer candles for average (more responsive)
    "confidence_boost": 15,  # Higher boost (was 10)
}

# ============================================================================
# 2. Wyckoff Method
# ============================================================================
WYCKOFF_CONFIG = {
    "enabled": True,
    "accumulation_volume_decrease": 0.75,  # Volume drops to 75% (more lenient)
    "distribution_volume_increase": 1.2,  # Volume rises to 120% (more lenient)
    "spring_penetration_pct": 0.3,  # Spring penetrates support by 0.3% (lower)
    "spring_reversal_pct": 0.7,  # Must reverse 0.7% above support (lower)
    "upthrust_penetration_pct": 0.3,  # Upthrust penetrates resistance by 0.3% (lower)
    "sos_volume_multiplier": 1.3,  # SOS requires 1.3x volume (lower)
    "phase_min_candles": 15,  # Fewer candles to confirm phase (more responsive)
    "high_confidence_threshold": 75,  # >75% confidence for boost (lower)
    "confidence_boost": 20,  # Higher boost (was 15)
}

# ============================================================================
# 3. Market Profile (TPO)
# ============================================================================
TPO_CONFIG = {
    "enabled": True,
    "period_minutes": 30,
    "value_area_pct": 70,
    "poc_confidence_boost": 18,  # Higher boost (was 12)
    "poor_extreme_min_distance": 3,  # Fewer ticks required (more lenient)
    "profile_lookback_days": 3,  # Fewer days (more responsive)
}

# ============================================================================
# 4. Enhanced Liquidity Engineering
# ============================================================================
LIQUIDITY_CONFIG = {
    "enabled": True,
    "equal_level_tolerance_pct": 0.3,  # Wider tolerance (more lenient)
    "sweep_penetration_pct": 0.2,  # Lower penetration required (was 0.3%)
    "sweep_reversal_candles": 5,  # More candles allowed (more lenient)
    "sweep_volume_multiplier": 1.3,  # Lower volume required (was 1.5x)
    "void_volume_threshold": 0.6,  # <60% average volume = void (more lenient)
    "turtle_soup_lookback": 15,  # 15-day high/low (shorter period)
    "stop_cluster_radius_pct": 0.7,  # Wider clustering (more lenient)
    "confidence_boost": 25,  # Higher boost (was 18)
}

# ============================================================================
# 5. Smart Money Divergence
# ============================================================================
DIVERGENCE_CONFIG = {
    "enabled": True,
    "min_swing_size_pct": 1.5,  # Min 1.5% price swing (lower threshold)
    "lookback_candles": 40,  # Fewer candles to search (more responsive)
    "regular_divergence_boost": 25,  # Higher boost (was 20)
    "hidden_divergence_boost": 15,  # Higher boost (was 10)
    "high_strength_threshold": 70,  # >70% = high strength (more lenient)
}

# ============================================================================
# 6. Multi-Timeframe Confluence
# ============================================================================
MTF_CONFIG = {
    "enabled": True,
    "timeframes": ["1", "5", "15", "60", "240"],
    "level_tolerance_pct": 0.7,  # Wider tolerance (was 0.5%)
    "min_confluence_timeframes": 2,  # Require only 2 TFs (was 3, more lenient)
    "full_alignment_boost": 30,  # Higher boost (was 25)
    "divergence_penalty": -10,  # Lower penalty (was -15, less cautious)
}

# ============================================================================
# 7. Advanced Order Book Imbalance
# ============================================================================
ORDERBOOK_IMBALANCE_CONFIG = {
    "enabled": True,
    "flash_imbalance_threshold_pct": 25,  # 25% change required (lower)
    "flash_imbalance_window_sec": 15,  # Longer window (more lenient)
    "iceberg_refill_threshold": 2,  # Fewer refills required (was 3)
    "spoofing_max_duration_sec": 40,  # Longer duration (more lenient)
    "absorption_volume_multiplier": 1.7,  # Lower volume required (was 2.0x)
    "pressure_score_levels": 8,  # Fewer levels for calculation (faster)
    "confidence_boost": 20,  # Higher boost (was 15)
}

# ============================================================================
# 8. Institutional Order Flow
# ============================================================================
INSTITUTIONAL_FLOW_CONFIG = {
    "enabled": True,
    "iceberg_min_trades": 7,  # Fewer trades required (was 10)
    "iceberg_size_consistency": 0.75,  # Lower consistency required (was 0.8)
    "twap_interval_consistency": 0.65,  # Lower consistency (was 0.7)
    "vwap_price_tolerance_pct": 0.15,  # Wider tolerance (was 0.1%)
    "layering_min_levels": 2,  # Fewer levels required (was 3)
    "sweep_min_levels": 2,  # Fewer levels required (was 3)
    "high_activity_threshold": 75,  # >75 = high activity (more lenient)
    "confidence_boost": 25,  # Higher boost (was 20)
}

# ============================================================================
# 9. Volatility Regime Adaptive System
# ============================================================================
VOLATILITY_REGIME_CONFIG = {
    "enabled": True,
    "low_volatility_threshold": 18,  # <18% = LOW (more lenient)
    "normal_volatility_range": (18, 35),  # Wider range
    "high_volatility_range": (35, 55),  # Wider range
    "extreme_volatility_threshold": 55,  # >55% = EXTREME (higher threshold)
    "compression_duration_days": 3,  # Require only 3 days (was 5, more responsive)
    "compression_percentile": 25,  # Below 25th percentile (more lenient)
    "compression_confidence_boost": 20,  # Higher boost (was 15)
    
    # More aggressive regime adjustments
    "low_regime": {
        "min_quality": "A",  # Accept A (was A+)
        "sl_buffer_multiplier": 0.9,  # Tighter SL
        "leverage_multiplier": 1.2,  # Higher leverage
    },
    "normal_regime": {
        "min_quality": "A",
        "sl_buffer_multiplier": 1.0,
        "leverage_multiplier": 1.1,  # Slightly higher leverage
    },
    "high_regime": {
        "min_quality": "A",
        "sl_buffer_multiplier": 1.3,  # Less widening (was 1.5)
        "leverage_multiplier": 0.85,  # Less reduction (was 0.75)
    },
    "extreme_regime": {
        "min_quality": "A",  # Accept A (was A+)
        "sl_buffer_multiplier": 1.7,  # Less widening (was 2.0)
        "leverage_multiplier": 0.6,  # Less reduction (was 0.5)
    },
}

# ============================================================================
# 10. Machine Learning Confidence Calibration
# ============================================================================
ML_CALIBRATION_CONFIG = {
    "enabled": True,
    "min_samples_for_training": 75,  # Fewer samples required (was 100)
    "retrain_interval_signals": 1200,  # Retrain less frequently (was 1000)
    "calibration_method": "isotonic",
    "confidence_bins": 8,  # Fewer bins (was 10, faster)
    "max_adjustment_pct": 25,  # Higher max adjustment (was 20)
}

# ============================================================================
# 11. Dynamic Take Profit Optimization
# ============================================================================
DYNAMIC_TP_CONFIG = {
    "enabled": True,
    "tp1_atr_multiplier": 1.2,  # Closer TP1 (was 1.5, take profit faster)
    "tp2_atr_multiplier": 2.5,  # Closer TP2 (was 3.0)
    "momentum_rsi_threshold": 65,  # Weaker momentum required (was 70)
    "momentum_tp2_extension_pct": 70,  # More extension (was 50%)
    "trailing_stop_distance_pct": 0.7,  # Tighter trailing (was 1.0%)
    "partial_profit_pct": 40,  # Take less profit at TP1 (was 50%, let more run)
    "fibonacci_extensions": [1.618, 2.0, 2.618],
}

# ============================================================================
# 12. Correlation-Based Portfolio Optimization
# ============================================================================
CORRELATION_CONFIG = {
    "enabled": True,
    "lookback_days": 20,  # Shorter lookback (was 30, more responsive)
    "high_correlation_threshold": 0.85,  # Higher threshold (was 0.8, more lenient)
    "min_diversification_score": 30,  # Lower minimum (was 40, more lenient)
    "correlation_position_limit": 5,  # More correlated positions (was 3)
    "update_interval_hours": 48,  # Update less frequently (was 24)
}

# ============================================================================
# 13. News Sentiment Integration
# ============================================================================
NEWS_SENTIMENT_CONFIG = {
    "enabled": True,
    "api_provider": "cryptopanic",
    "lookback_hours": 12,  # Shorter lookback (was 24, more responsive)
    "lookahead_hours": 1,  # Shorter lookahead (was 2, less cautious)
    "sentiment_shift_threshold": 35,  # Higher threshold (was 30, less sensitive)
    "sentiment_shift_window_hours": 0.5,  # Shorter window (was 1, more responsive)
    "negative_sentiment_penalty": -15,  # Lower penalty (was -20)
    "positive_sentiment_boost": 15,  # Higher boost (was 10)
    "high_impact_block_duration_hours": 1,  # Block shorter (was 2, less cautious)
    "update_interval_minutes": 20,  # Update less frequently (was 15)
}

# ============================================================================
# 14. Backtesting Engine
# ============================================================================
BACKTEST_CONFIG = {
    "enabled": True,
    "walk_forward_train_months": 4,  # Shorter training (was 6, more responsive)
    "walk_forward_test_months": 3,  # Longer testing (was 2)
    "overfitting_threshold": 0.65,  # More lenient threshold (was 0.7)
    "slippage_pct": 0.03,  # Lower slippage assumption (was 0.05)
    "commission_pct": 0.05,  # Lower commission assumption (was 0.06)
    "initial_capital": 10000,
    "max_concurrent_positions": 8,  # More positions (was 5)
}

# ============================================================================
# 15. A/B Testing Framework
# ============================================================================
AB_TEST_CONFIG = {
    "enabled": True,
    "min_samples_per_variant": 75,  # Fewer samples required (was 100)
    "significance_level": 0.10,  # More lenient significance (was 0.05)
    "min_improvement_pct": 7,  # Lower improvement required (was 10%)
    "split_ratio": 0.5,
    "max_concurrent_experiments": 5,  # More experiments (was 3)
}

# ============================================================================
# 16. Enhanced Risk Management
# ============================================================================
ENHANCED_RISK_CONFIG = {
    "enabled": True,
    "base_risk_per_trade_pct": 1.5,  # Higher risk (was 1.0%)
    "max_portfolio_risk_pct": 7.0,  # Higher max risk (was 5.0%)
    "max_daily_loss_pct": 4.5,  # Higher daily loss limit (was 3.0%)
    "consecutive_loss_threshold": 4,  # Reduce after 4 losses (was 3)
    "consecutive_win_threshold": 3,  # Increase after 3 wins (was 5, more responsive)
    "loss_reduction_multiplier": 0.6,  # Reduce less (was 0.5)
    "win_increase_multiplier": 1.4,  # Increase more (was 1.25)
    "max_position_size_multiplier": 3.0,  # Higher max (was 2.0)
    "use_kelly_criterion": True,
    "kelly_fraction": 0.35,  # Use more of Kelly (was 0.25, more aggressive)
}

# ============================================================================
# 17. Market Microstructure Analysis
# ============================================================================
MICROSTRUCTURE_CONFIG = {
    "enabled": True,
    "spread_widening_threshold": 1.7,  # Lower threshold (was 2.0, more sensitive)
    "spread_widening_duration_min": 7,  # Longer duration (less sensitive)
    "toxic_flow_threshold": 65,  # Lower threshold (was 70, more lenient)
    "quote_stuffing_threshold": 120,  # Higher threshold (was 100, less sensitive)
    "price_impact_levels": [1000, 5000, 10000, 50000],
    "confidence_boost": 18,  # Higher boost (was 12)
    "spread_widening_penalty": -7,  # Lower penalty (was -10)
}

# ============================================================================
# 18. Seasonality and Cyclical Pattern Detection
# ============================================================================
SEASONALITY_CONFIG = {
    "enabled": True,
    "min_lookback_days": 270,  # Less data required (was 365)
    "pattern_accuracy_threshold": 60,  # Lower accuracy required (was 65%)
    "confidence_boost": 12,  # Higher boost (was 8)
    "fft_min_period_days": 5,  # Shorter min cycle (was 7)
    "fft_max_period_days": 120,  # Longer max cycle (was 90)
}

# ============================================================================
# 19. Adaptive Stop Loss System
# ============================================================================
ADAPTIVE_SL_CONFIG = {
    "enabled": True,
    "atr_multipliers": {
        "LOW": 1.2,  # Tighter SL (was 1.5)
        "NORMAL": 1.7,  # Tighter SL (was 2.0)
        "HIGH": 2.5,  # Tighter SL (was 3.0)
        "EXTREME": 3.5,  # Tighter SL (was 4.0)
    },
    "breakeven_trigger_pct": 40,  # Move to BE earlier (was 50%)
    "profit_lock_trigger": "TP1_HIT",
    "profit_lock_pct": 40,  # Lock less profit (was 50%, let more run)
    "chandelier_atr_multiplier": 2.5,  # Tighter trailing (was 3.0)
    "structure_buffer_pct": 0.2,  # Smaller buffer (was 0.3%)
    "round_number_buffer_pct": 0.1,  # Smaller buffer (was 0.2%)
    "stop_hunt_detection_range_pct": 0.7,  # Narrower range (was 1.0%)
}

# ============================================================================
# 20. Performance Analytics Dashboard
# ============================================================================
DASHBOARD_CONFIG = {
    "enabled": True,
    "update_interval_seconds": 3,  # Update more frequently (was 5)
    "default_lookback_days": 14,  # Shorter lookback (was 30, more recent focus)
    "chart_library": "plotly",
    "export_formats": ["pdf", "csv", "json"],
    "port": 8000,
    "host": "localhost",
}

# ============================================================================
# Master Configuration
# ============================================================================
ADVANCED_FEATURES_CONFIG = {
    "vsa": VSA_CONFIG,
    "wyckoff": WYCKOFF_CONFIG,
    "market_profile": TPO_CONFIG,
    "liquidity_engineering": LIQUIDITY_CONFIG,
    "smart_money_divergence": DIVERGENCE_CONFIG,
    "mtf_confluence": MTF_CONFIG,
    "orderbook_imbalance": ORDERBOOK_IMBALANCE_CONFIG,
    "institutional_flow": INSTITUTIONAL_FLOW_CONFIG,
    "volatility_regime": VOLATILITY_REGIME_CONFIG,
    "ml_calibration": ML_CALIBRATION_CONFIG,
    "dynamic_tp": DYNAMIC_TP_CONFIG,
    "correlation_optimizer": CORRELATION_CONFIG,
    "news_sentiment": NEWS_SENTIMENT_CONFIG,
    "backtesting": BACKTEST_CONFIG,
    "ab_testing": AB_TEST_CONFIG,
    "enhanced_risk": ENHANCED_RISK_CONFIG,
    "microstructure": MICROSTRUCTURE_CONFIG,
    "seasonality": SEASONALITY_CONFIG,
    "adaptive_sl": ADAPTIVE_SL_CONFIG,
    "dashboard": DASHBOARD_CONFIG,
}
