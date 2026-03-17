"""
Conservative Configuration for Advanced Trading Optimization Features

This configuration uses higher thresholds and lower confidence boosts for a more
cautious approach. Suitable for risk-averse traders or volatile market conditions.

Key Differences from Default:
- Higher detection thresholds (require stronger signals)
- Lower confidence boosts (more conservative adjustments)
- Stricter risk management limits
- More conservative position sizing
"""

# ============================================================================
# 1. Volume Spread Analysis (VSA)
# ============================================================================
VSA_CONFIG = {
    "enabled": True,
    "high_volume_threshold": 2.0,  # 2x average volume (higher threshold)
    "narrow_spread_threshold": 0.6,  # 60% of average spread (stricter)
    "wide_spread_threshold": 1.5,  # 150% of average spread (stricter)
    "close_top_threshold": 0.85,  # Close in top 85% of range (stricter)
    "close_bottom_threshold": 0.15,  # Close in bottom 15% of range (stricter)
    "stopping_volume_multiplier": 2.5,  # 2.5x volume for absorption (higher)
    "lookback_period": 30,  # More candles for average (more stable)
    "confidence_boost": 7,  # Lower boost (was 10)
}

# ============================================================================
# 2. Wyckoff Method
# ============================================================================
WYCKOFF_CONFIG = {
    "enabled": True,
    "accumulation_volume_decrease": 0.6,  # Volume drops to 60% (stricter)
    "distribution_volume_increase": 1.5,  # Volume rises to 150% (stricter)
    "spring_penetration_pct": 0.7,  # Spring penetrates support by 0.7% (higher)
    "spring_reversal_pct": 1.5,  # Must reverse 1.5% above support (higher)
    "upthrust_penetration_pct": 0.7,  # Upthrust penetrates resistance by 0.7% (higher)
    "sos_volume_multiplier": 2.0,  # SOS requires 2x volume (higher)
    "phase_min_candles": 30,  # More candles to confirm phase (stricter)
    "high_confidence_threshold": 85,  # >85% confidence for boost (higher)
    "confidence_boost": 10,  # Lower boost (was 15)
}

# ============================================================================
# 3. Market Profile (TPO)
# ============================================================================
TPO_CONFIG = {
    "enabled": True,
    "period_minutes": 30,
    "value_area_pct": 70,
    "poc_confidence_boost": 8,  # Lower boost (was 12)
    "poor_extreme_min_distance": 7,  # More ticks required (stricter)
    "profile_lookback_days": 7,  # More days for stability
}

# ============================================================================
# 4. Enhanced Liquidity Engineering
# ============================================================================
LIQUIDITY_CONFIG = {
    "enabled": True,
    "equal_level_tolerance_pct": 0.15,  # Tighter tolerance (stricter)
    "sweep_penetration_pct": 0.5,  # Higher penetration required (was 0.3%)
    "sweep_reversal_candles": 2,  # Faster reversal required (stricter)
    "sweep_volume_multiplier": 2.0,  # Higher volume required (was 1.5x)
    "void_volume_threshold": 0.4,  # <40% average volume = void (stricter)
    "turtle_soup_lookback": 30,  # 30-day high/low (longer period)
    "stop_cluster_radius_pct": 0.3,  # Tighter clustering (stricter)
    "confidence_boost": 12,  # Lower boost (was 18)
}

# ============================================================================
# 5. Smart Money Divergence
# ============================================================================
DIVERGENCE_CONFIG = {
    "enabled": True,
    "min_swing_size_pct": 3.0,  # Min 3% price swing (higher threshold)
    "lookback_candles": 60,  # More candles to search (more data)
    "regular_divergence_boost": 15,  # Lower boost (was 20)
    "hidden_divergence_boost": 7,  # Lower boost (was 10)
    "high_strength_threshold": 80,  # >80% = high strength (stricter)
}

# ============================================================================
# 6. Multi-Timeframe Confluence
# ============================================================================
MTF_CONFIG = {
    "enabled": True,
    "timeframes": ["1", "5", "15", "60", "240"],
    "level_tolerance_pct": 0.3,  # Tighter tolerance (was 0.5%)
    "min_confluence_timeframes": 4,  # Require 4 TFs (was 3, stricter)
    "full_alignment_boost": 20,  # Lower boost (was 25)
    "divergence_penalty": -20,  # Higher penalty (was -15, more cautious)
}

# ============================================================================
# 7. Advanced Order Book Imbalance
# ============================================================================
ORDERBOOK_IMBALANCE_CONFIG = {
    "enabled": True,
    "flash_imbalance_threshold_pct": 40,  # 40% change required (higher)
    "flash_imbalance_window_sec": 8,  # Shorter window (stricter)
    "iceberg_refill_threshold": 5,  # More refills required (was 3)
    "spoofing_max_duration_sec": 20,  # Shorter duration (stricter)
    "absorption_volume_multiplier": 2.5,  # Higher volume required (was 2.0x)
    "pressure_score_levels": 15,  # More levels for calculation (more data)
    "confidence_boost": 10,  # Lower boost (was 15)
}

# ============================================================================
# 8. Institutional Order Flow
# ============================================================================
INSTITUTIONAL_FLOW_CONFIG = {
    "enabled": True,
    "iceberg_min_trades": 15,  # More trades required (was 10)
    "iceberg_size_consistency": 0.85,  # Higher consistency required (was 0.8)
    "twap_interval_consistency": 0.75,  # Higher consistency (was 0.7)
    "vwap_price_tolerance_pct": 0.08,  # Tighter tolerance (was 0.1%)
    "layering_min_levels": 4,  # More levels required (was 3)
    "sweep_min_levels": 4,  # More levels required (was 3)
    "high_activity_threshold": 85,  # >85 = high activity (stricter)
    "confidence_boost": 15,  # Lower boost (was 20)
}

# ============================================================================
# 9. Volatility Regime Adaptive System
# ============================================================================
VOLATILITY_REGIME_CONFIG = {
    "enabled": True,
    "low_volatility_threshold": 12,  # <12% = LOW (stricter)
    "normal_volatility_range": (12, 25),  # Narrower range
    "high_volatility_range": (25, 45),  # Narrower range
    "extreme_volatility_threshold": 45,  # >45% = EXTREME (lower threshold)
    "compression_duration_days": 7,  # Require 7 days (was 5, stricter)
    "compression_percentile": 15,  # Below 15th percentile (stricter)
    "compression_confidence_boost": 10,  # Lower boost (was 15)
    
    # More conservative regime adjustments
    "low_regime": {
        "min_quality": "A+",
        "sl_buffer_multiplier": 1.2,  # Wider SL even in low vol
        "leverage_multiplier": 0.9,  # Slightly reduced leverage
    },
    "normal_regime": {
        "min_quality": "A+",  # Require A+ (was A)
        "sl_buffer_multiplier": 1.3,  # Wider SL
        "leverage_multiplier": 0.85,  # Reduced leverage
    },
    "high_regime": {
        "min_quality": "A+",
        "sl_buffer_multiplier": 2.0,  # Much wider SL (was 1.5)
        "leverage_multiplier": 0.6,  # Lower leverage (was 0.75)
    },
    "extreme_regime": {
        "min_quality": "A+",
        "sl_buffer_multiplier": 2.5,  # Much wider SL (was 2.0)
        "leverage_multiplier": 0.4,  # Much lower leverage (was 0.5)
    },
}

# ============================================================================
# 10. Machine Learning Confidence Calibration
# ============================================================================
ML_CALIBRATION_CONFIG = {
    "enabled": True,
    "min_samples_for_training": 200,  # More samples required (was 100)
    "retrain_interval_signals": 800,  # Retrain more frequently (was 1000)
    "calibration_method": "isotonic",
    "confidence_bins": 15,  # More bins for finer calibration (was 10)
    "max_adjustment_pct": 15,  # Lower max adjustment (was 20)
}

# ============================================================================
# 11. Dynamic Take Profit Optimization
# ============================================================================
DYNAMIC_TP_CONFIG = {
    "enabled": True,
    "tp1_atr_multiplier": 2.0,  # Further TP1 (was 1.5, more conservative)
    "tp2_atr_multiplier": 3.5,  # Further TP2 (was 3.0)
    "momentum_rsi_threshold": 75,  # Stronger momentum required (was 70)
    "momentum_tp2_extension_pct": 30,  # Less extension (was 50%)
    "trailing_stop_distance_pct": 1.5,  # Wider trailing (was 1.0%)
    "partial_profit_pct": 60,  # Take more profit at TP1 (was 50%)
    "fibonacci_extensions": [1.618, 2.0, 2.618],
}

# ============================================================================
# 12. Correlation-Based Portfolio Optimization
# ============================================================================
CORRELATION_CONFIG = {
    "enabled": True,
    "lookback_days": 45,  # Longer lookback (was 30, more stable)
    "high_correlation_threshold": 0.75,  # Lower threshold (was 0.8, stricter)
    "min_diversification_score": 50,  # Higher minimum (was 40, stricter)
    "correlation_position_limit": 2,  # Fewer correlated positions (was 3)
    "update_interval_hours": 12,  # Update more frequently (was 24)
}

# ============================================================================
# 13. News Sentiment Integration
# ============================================================================
NEWS_SENTIMENT_CONFIG = {
    "enabled": True,
    "api_provider": "cryptopanic",
    "lookback_hours": 36,  # Longer lookback (was 24)
    "lookahead_hours": 4,  # Longer lookahead (was 2, more cautious)
    "sentiment_shift_threshold": 25,  # Lower threshold (was 30, more sensitive)
    "sentiment_shift_window_hours": 2,  # Longer window (was 1)
    "negative_sentiment_penalty": -25,  # Higher penalty (was -20)
    "positive_sentiment_boost": 7,  # Lower boost (was 10)
    "high_impact_block_duration_hours": 4,  # Block longer (was 2, more cautious)
    "update_interval_minutes": 10,  # Update more frequently (was 15)
}

# ============================================================================
# 14. Backtesting Engine
# ============================================================================
BACKTEST_CONFIG = {
    "enabled": True,
    "walk_forward_train_months": 9,  # Longer training (was 6)
    "walk_forward_test_months": 1,  # Shorter testing (was 2, more rigorous)
    "overfitting_threshold": 0.75,  # Stricter threshold (was 0.7)
    "slippage_pct": 0.08,  # Higher slippage assumption (was 0.05)
    "commission_pct": 0.08,  # Higher commission assumption (was 0.06)
    "initial_capital": 10000,
    "max_concurrent_positions": 3,  # Fewer positions (was 5)
}

# ============================================================================
# 15. A/B Testing Framework
# ============================================================================
AB_TEST_CONFIG = {
    "enabled": True,
    "min_samples_per_variant": 150,  # More samples required (was 100)
    "significance_level": 0.03,  # Stricter significance (was 0.05)
    "min_improvement_pct": 15,  # Higher improvement required (was 10%)
    "split_ratio": 0.5,
    "max_concurrent_experiments": 2,  # Fewer experiments (was 3)
}

# ============================================================================
# 16. Enhanced Risk Management
# ============================================================================
ENHANCED_RISK_CONFIG = {
    "enabled": True,
    "base_risk_per_trade_pct": 0.75,  # Lower risk (was 1.0%)
    "max_portfolio_risk_pct": 3.5,  # Lower max risk (was 5.0%)
    "max_daily_loss_pct": 2.0,  # Lower daily loss limit (was 3.0%)
    "consecutive_loss_threshold": 2,  # Reduce after 2 losses (was 3)
    "consecutive_win_threshold": 7,  # Increase after 7 wins (was 5, stricter)
    "loss_reduction_multiplier": 0.4,  # Reduce more (was 0.5)
    "win_increase_multiplier": 1.15,  # Increase less (was 1.25)
    "max_position_size_multiplier": 1.5,  # Lower max (was 2.0)
    "use_kelly_criterion": True,
    "kelly_fraction": 0.15,  # Use less of Kelly (was 0.25, more conservative)
}

# ============================================================================
# 17. Market Microstructure Analysis
# ============================================================================
MICROSTRUCTURE_CONFIG = {
    "enabled": True,
    "spread_widening_threshold": 2.5,  # Higher threshold (was 2.0)
    "spread_widening_duration_min": 3,  # Shorter duration (more sensitive)
    "toxic_flow_threshold": 75,  # Higher threshold (was 70, stricter)
    "quote_stuffing_threshold": 80,  # Lower threshold (was 100, more sensitive)
    "price_impact_levels": [1000, 5000, 10000, 50000],
    "confidence_boost": 8,  # Lower boost (was 12)
    "spread_widening_penalty": -15,  # Higher penalty (was -10)
}

# ============================================================================
# 18. Seasonality and Cyclical Pattern Detection
# ============================================================================
SEASONALITY_CONFIG = {
    "enabled": True,
    "min_lookback_days": 450,  # More data required (was 365)
    "pattern_accuracy_threshold": 70,  # Higher accuracy required (was 65%)
    "confidence_boost": 5,  # Lower boost (was 8)
    "fft_min_period_days": 10,  # Longer min cycle (was 7)
    "fft_max_period_days": 60,  # Shorter max cycle (was 90)
}

# ============================================================================
# 19. Adaptive Stop Loss System
# ============================================================================
ADAPTIVE_SL_CONFIG = {
    "enabled": True,
    "atr_multipliers": {
        "LOW": 2.0,  # Wider SL (was 1.5)
        "NORMAL": 2.5,  # Wider SL (was 2.0)
        "HIGH": 3.5,  # Wider SL (was 3.0)
        "EXTREME": 5.0,  # Much wider SL (was 4.0)
    },
    "breakeven_trigger_pct": 60,  # Move to BE later (was 50%)
    "profit_lock_trigger": "TP1_HIT",
    "profit_lock_pct": 60,  # Lock more profit (was 50%)
    "chandelier_atr_multiplier": 3.5,  # Wider trailing (was 3.0)
    "structure_buffer_pct": 0.5,  # Larger buffer (was 0.3%)
    "round_number_buffer_pct": 0.3,  # Larger buffer (was 0.2%)
    "stop_hunt_detection_range_pct": 1.5,  # Wider range (was 1.0%)
}

# ============================================================================
# 20. Performance Analytics Dashboard
# ============================================================================
DASHBOARD_CONFIG = {
    "enabled": True,
    "update_interval_seconds": 10,  # Update less frequently (was 5)
    "default_lookback_days": 60,  # Longer lookback (was 30)
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
