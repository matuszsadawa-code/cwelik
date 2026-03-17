"""
Default Configuration for Advanced Trading Optimization Features

This configuration provides balanced settings suitable for most market conditions.
All 20 features are configured with moderate thresholds and confidence boosts.
"""

# ============================================================================
# 1. Volume Spread Analysis (VSA)
# ============================================================================
VSA_CONFIG = {
    "enabled": True,
    "high_volume_threshold": 1.5,  # 1.5x average volume
    "narrow_spread_threshold": 0.7,  # 70% of average spread
    "wide_spread_threshold": 1.3,  # 130% of average spread
    "close_top_threshold": 0.8,  # Close in top 80% of range
    "close_bottom_threshold": 0.2,  # Close in bottom 20% of range
    "stopping_volume_multiplier": 2.0,  # 2x volume for absorption
    "lookback_period": 20,  # Candles for average calculation
    "confidence_boost": 10,  # Boost for stopping volume detection
}

# ============================================================================
# 2. Wyckoff Method
# ============================================================================
WYCKOFF_CONFIG = {
    "enabled": True,
    "accumulation_volume_decrease": 0.7,  # Volume drops to 70% in accumulation
    "distribution_volume_increase": 1.3,  # Volume rises to 130% in distribution
    "spring_penetration_pct": 0.5,  # Spring penetrates support by 0.5%
    "spring_reversal_pct": 1.0,  # Must reverse 1% above support
    "upthrust_penetration_pct": 0.5,  # Upthrust penetrates resistance by 0.5%
    "sos_volume_multiplier": 1.5,  # SOS requires 1.5x volume
    "phase_min_candles": 20,  # Minimum candles to confirm phase
    "high_confidence_threshold": 80,  # >80% confidence for boost
    "confidence_boost": 15,  # Boost for Spring/Upthrust with high confidence
}

# ============================================================================
# 3. Market Profile (TPO)
# ============================================================================
TPO_CONFIG = {
    "enabled": True,
    "period_minutes": 30,  # TPO period
    "value_area_pct": 70,  # 70% of volume for value area
    "poc_confidence_boost": 12,  # Boost when price at POC
    "poor_extreme_min_distance": 5,  # Min ticks for poor high/low
    "profile_lookback_days": 5,  # Days of profiles to maintain
}

# ============================================================================
# 4. Enhanced Liquidity Engineering
# ============================================================================
LIQUIDITY_CONFIG = {
    "enabled": True,
    "equal_level_tolerance_pct": 0.2,  # 0.2% tolerance for equal highs/lows
    "sweep_penetration_pct": 0.3,  # Min 0.3% penetration for sweep
    "sweep_reversal_candles": 3,  # Max candles for reversal
    "sweep_volume_multiplier": 1.5,  # Volume must be 1.5x average
    "void_volume_threshold": 0.5,  # <50% average volume = void
    "turtle_soup_lookback": 20,  # 20-day high/low for turtle soup
    "stop_cluster_radius_pct": 0.5,  # Cluster stops within 0.5%
    "confidence_boost": 18,  # Boost for liquidity sweep aligned with trend
}

# ============================================================================
# 5. Smart Money Divergence
# ============================================================================
DIVERGENCE_CONFIG = {
    "enabled": True,
    "min_swing_size_pct": 2.0,  # Min 2% price swing for divergence
    "lookback_candles": 50,  # Candles to search for swings
    "regular_divergence_boost": 20,  # Confidence boost for regular
    "hidden_divergence_boost": 10,  # Confidence boost for hidden
    "high_strength_threshold": 75,  # >75% = high strength
}

# ============================================================================
# 6. Multi-Timeframe Confluence
# ============================================================================
MTF_CONFIG = {
    "enabled": True,
    "timeframes": ["1", "5", "15", "60", "240"],  # 1M, 5M, 15M, 1H, 4H
    "level_tolerance_pct": 0.5,  # 0.5% tolerance for level alignment
    "min_confluence_timeframes": 3,  # Min 3 TFs for high confluence
    "full_alignment_boost": 25,  # Boost when all TFs align
    "divergence_penalty": -15,  # Penalty for TF divergence
}

# ============================================================================
# 7. Advanced Order Book Imbalance
# ============================================================================
ORDERBOOK_IMBALANCE_CONFIG = {
    "enabled": True,
    "flash_imbalance_threshold_pct": 30,  # 30% change for flash alert
    "flash_imbalance_window_sec": 10,  # Within 10 seconds
    "iceberg_refill_threshold": 3,  # Min 3 refills to detect iceberg
    "spoofing_max_duration_sec": 30,  # Max 30s before cancel = spoofing
    "absorption_volume_multiplier": 2.0,  # 2x average volume
    "pressure_score_levels": 10,  # Top 10 levels for pressure calculation
    "confidence_boost": 15,  # Boost for absorption aligned with signal
}

# ============================================================================
# 8. Institutional Order Flow
# ============================================================================
INSTITUTIONAL_FLOW_CONFIG = {
    "enabled": True,
    "iceberg_min_trades": 10,  # Min trades for iceberg detection
    "iceberg_size_consistency": 0.8,  # 80% size consistency
    "twap_interval_consistency": 0.7,  # 70% time interval consistency
    "vwap_price_tolerance_pct": 0.1,  # Within 0.1% of VWAP
    "layering_min_levels": 3,  # Min 3 levels for layering
    "sweep_min_levels": 3,  # Min 3 levels for sweep
    "high_activity_threshold": 80,  # >80 = high institutional activity
    "confidence_boost": 20,  # Boost when activity score >80%
}

# ============================================================================
# 9. Volatility Regime Adaptive System
# ============================================================================
VOLATILITY_REGIME_CONFIG = {
    "enabled": True,
    "low_volatility_threshold": 15,  # <15% = LOW
    "normal_volatility_range": (15, 30),  # 15-30% = NORMAL
    "high_volatility_range": (30, 50),  # 30-50% = HIGH
    "extreme_volatility_threshold": 50,  # >50% = EXTREME
    "compression_duration_days": 5,  # Min 5 days for compression
    "compression_percentile": 20,  # Below 20th percentile
    "compression_confidence_boost": 15,  # Boost for compression >5 days
    
    # Regime-specific adjustments
    "low_regime": {
        "min_quality": "A+",
        "sl_buffer_multiplier": 1.0,
        "leverage_multiplier": 1.0,
    },
    "normal_regime": {
        "min_quality": "A",
        "sl_buffer_multiplier": 1.0,
        "leverage_multiplier": 1.0,
    },
    "high_regime": {
        "min_quality": "A",
        "sl_buffer_multiplier": 1.5,
        "leverage_multiplier": 0.75,
    },
    "extreme_regime": {
        "min_quality": "A+",
        "sl_buffer_multiplier": 2.0,
        "leverage_multiplier": 0.5,
    },
}

# ============================================================================
# 10. Machine Learning Confidence Calibration
# ============================================================================
ML_CALIBRATION_CONFIG = {
    "enabled": True,
    "min_samples_for_training": 100,  # Min 100 samples to train
    "retrain_interval_signals": 1000,  # Retrain every 1000 signals
    "calibration_method": "isotonic",  # isotonic or platt
    "confidence_bins": 10,  # Number of bins for calibration curve
    "max_adjustment_pct": 20,  # Max ±20% adjustment to confidence
}

# ============================================================================
# 11. Dynamic Take Profit Optimization
# ============================================================================
DYNAMIC_TP_CONFIG = {
    "enabled": True,
    "tp1_atr_multiplier": 1.5,  # TP1 at 1.5x ATR (≈1:1 R:R)
    "tp2_atr_multiplier": 3.0,  # TP2 at 3.0x ATR (≈2:1 R:R)
    "momentum_rsi_threshold": 70,  # RSI >70 or <30 = strong momentum
    "momentum_tp2_extension_pct": 50,  # Extend TP2 by 50% if momentum strong
    "trailing_stop_distance_pct": 1.0,  # Trail by 1% after TP1
    "partial_profit_pct": 50,  # Take 50% profit at TP1
    "fibonacci_extensions": [1.618, 2.0, 2.618],
}

# ============================================================================
# 12. Correlation-Based Portfolio Optimization
# ============================================================================
CORRELATION_CONFIG = {
    "enabled": True,
    "lookback_days": 30,  # 30-day rolling correlation
    "high_correlation_threshold": 0.8,  # >0.8 = highly correlated
    "min_diversification_score": 40,  # Min 40% diversification
    "correlation_position_limit": 3,  # Max 3 positions in correlated assets
    "update_interval_hours": 24,  # Update correlation matrix daily
}

# ============================================================================
# 13. News Sentiment Integration
# ============================================================================
NEWS_SENTIMENT_CONFIG = {
    "enabled": True,
    "api_provider": "cryptopanic",  # cryptopanic, newsapi
    "lookback_hours": 24,  # Fetch last 24h of news
    "lookahead_hours": 2,  # Check for events in next 2h
    "sentiment_shift_threshold": 30,  # >30 point change = shift
    "sentiment_shift_window_hours": 1,  # Within 1 hour
    "negative_sentiment_penalty": -20,  # Penalty for negative sentiment
    "positive_sentiment_boost": 10,  # Boost for positive sentiment
    "high_impact_block_duration_hours": 2,  # Block trading 2h before event
    "update_interval_minutes": 15,  # Update news every 15 min
}

# ============================================================================
# 14. Backtesting Engine
# ============================================================================
BACKTEST_CONFIG = {
    "enabled": True,
    "walk_forward_train_months": 6,  # Train on 6 months
    "walk_forward_test_months": 2,  # Test on 2 months
    "overfitting_threshold": 0.7,  # Out-sample must be >70% in-sample
    "slippage_pct": 0.05,  # 0.05% slippage per trade
    "commission_pct": 0.06,  # 0.06% commission (maker+taker)
    "initial_capital": 10000,  # $10k starting capital
    "max_concurrent_positions": 5,
}

# ============================================================================
# 15. A/B Testing Framework
# ============================================================================
AB_TEST_CONFIG = {
    "enabled": True,
    "min_samples_per_variant": 100,  # Min 100 samples to conclude
    "significance_level": 0.05,  # p < 0.05 for significance
    "min_improvement_pct": 10,  # Treatment must be >10% better
    "split_ratio": 0.5,  # 50/50 split
    "max_concurrent_experiments": 3,  # Max 3 experiments at once
}

# ============================================================================
# 16. Enhanced Risk Management
# ============================================================================
ENHANCED_RISK_CONFIG = {
    "enabled": True,
    "base_risk_per_trade_pct": 1.0,  # 1% risk per trade
    "max_portfolio_risk_pct": 5.0,  # Max 5% portfolio risk
    "max_daily_loss_pct": 3.0,  # Max 3% daily loss
    "consecutive_loss_threshold": 3,  # Reduce after 3 losses
    "consecutive_win_threshold": 5,  # Increase after 5 wins
    "loss_reduction_multiplier": 0.5,  # Reduce to 50%
    "win_increase_multiplier": 1.25,  # Increase to 125%
    "max_position_size_multiplier": 2.0,  # Max 2x base size
    "use_kelly_criterion": True,  # Enable Kelly Criterion
    "kelly_fraction": 0.25,  # Use 25% of Kelly recommendation
}

# ============================================================================
# 17. Market Microstructure Analysis
# ============================================================================
MICROSTRUCTURE_CONFIG = {
    "enabled": True,
    "spread_widening_threshold": 2.0,  # 2x average spread
    "spread_widening_duration_min": 5,  # Min 5 minutes
    "toxic_flow_threshold": 70,  # >70 = toxic flow
    "quote_stuffing_threshold": 100,  # >100 updates/sec
    "price_impact_levels": [1000, 5000, 10000, 50000],  # $ sizes to test
    "confidence_boost": 12,  # Boost for toxic flow aligned with signal
    "spread_widening_penalty": -10,  # Penalty for spread widening
}

# ============================================================================
# 18. Seasonality and Cyclical Pattern Detection
# ============================================================================
SEASONALITY_CONFIG = {
    "enabled": True,
    "min_lookback_days": 365,  # Min 1 year of data
    "pattern_accuracy_threshold": 65,  # >65% accuracy to use
    "confidence_boost": 8,  # +8% for aligned seasonal bias
    "fft_min_period_days": 7,  # Min 7-day cycle
    "fft_max_period_days": 90,  # Max 90-day cycle
}

# ============================================================================
# 19. Adaptive Stop Loss System
# ============================================================================
ADAPTIVE_SL_CONFIG = {
    "enabled": True,
    "atr_multipliers": {
        "LOW": 1.5,
        "NORMAL": 2.0,
        "HIGH": 3.0,
        "EXTREME": 4.0,
    },
    "breakeven_trigger_pct": 50,  # Move to BE at 50% to TP1
    "profit_lock_trigger": "TP1_HIT",  # Lock profit when TP1 hits
    "profit_lock_pct": 50,  # Lock in 50% of profit
    "chandelier_atr_multiplier": 3.0,  # 3x ATR for trailing
    "structure_buffer_pct": 0.3,  # 0.3% buffer beyond structure
    "round_number_buffer_pct": 0.2,  # 0.2% buffer beyond round numbers
    "stop_hunt_detection_range_pct": 1.0,  # Check 1% range for stop hunts
}

# ============================================================================
# 20. Performance Analytics Dashboard
# ============================================================================
DASHBOARD_CONFIG = {
    "enabled": True,
    "update_interval_seconds": 5,  # Update every 5 seconds
    "default_lookback_days": 30,  # Default 30-day view
    "chart_library": "plotly",  # plotly or chartjs
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
