"""
Feature Flags Configuration for Advanced Trading Optimization.

This file controls the gradual rollout of 20 advanced features across 4 phases.
Set enabled=True to activate a feature.
"""

from typing import Dict, Any


# ============================================================================
# PHASE 1: MARKET DATA ANALYSIS (Features 1-5)
# ============================================================================

PHASE_1_FEATURES = {
    "vsa_analysis": {
        "enabled": False,
        "description": "Volume Spread Analysis - detect market maker manipulation",
        "confidence_boost": 10,  # Max confidence boost when active
        "config": {
            "high_volume_threshold": 1.5,
            "narrow_spread_threshold": 0.7,
            "wide_spread_threshold": 1.3,
            "close_top_threshold": 0.8,
            "close_bottom_threshold": 0.2,
            "stopping_volume_multiplier": 2.0,
            "lookback_period": 20,
        }
    },
    
    "wyckoff_method": {
        "enabled": False,
        "description": "Wyckoff Method - identify accumulation/distribution phases",
        "confidence_boost": 15,
        "config": {
            "accumulation_volume_decrease": 0.7,
            "distribution_volume_increase": 1.3,
            "spring_penetration_pct": 0.5,
            "spring_reversal_pct": 1.0,
            "upthrust_penetration_pct": 0.5,
            "sos_volume_multiplier": 1.5,
            "phase_min_candles": 20,
        }
    },
    
    "market_profile": {
        "enabled": False,
        "description": "Market Profile (TPO) - identify Value Area and POC",
        "confidence_boost": 12,
        "config": {
            "period_minutes": 30,
            "value_area_pct": 70,
            "poc_confidence_boost": 12,
            "poor_extreme_min_distance": 5,
            "profile_lookback_days": 5,
        }
    },
    
    "enhanced_liquidity": {
        "enabled": False,
        "description": "Enhanced Liquidity Engineering - detect sweeps and manipulation",
        "confidence_boost": 18,
        "config": {
            "equal_level_tolerance_pct": 0.2,
            "sweep_penetration_pct": 0.3,
            "sweep_reversal_candles": 3,
            "sweep_volume_multiplier": 1.5,
            "void_volume_threshold": 0.5,
            "turtle_soup_lookback": 20,
            "stop_cluster_radius_pct": 0.5,
        }
    },
    
    "smart_money_divergence": {
        "enabled": False,
        "description": "Smart Money Divergence - detect price vs indicator divergences",
        "confidence_boost": 20,  # For regular divergence >75% strength
        "config": {
            "min_swing_size_pct": 2.0,
            "lookback_candles": 50,
            "regular_divergence_boost": 20,
            "hidden_divergence_boost": 10,
            "high_strength_threshold": 75,
        }
    },
}


# ============================================================================
# PHASE 2: INTELLIGENCE & CONFLUENCE (Features 6-10)
# ============================================================================

PHASE_2_FEATURES = {
    "mtf_confluence": {
        "enabled": True,
        "description": "Multi-Timeframe Confluence - cross-timeframe validation",
        "confidence_boost": 25,  # When all timeframes align
        "config": {
            "timeframes": ["1", "5", "15", "60", "240"],
            "level_tolerance_pct": 0.5,
            "min_confluence_timeframes": 3,
            "full_alignment_boost": 25,
            "divergence_penalty": -15,
        }
    },
    
    "orderbook_imbalance": {
        "enabled": False,
        "description": "Advanced Order Book Imbalance - iceberg, spoofing, absorption",
        "confidence_boost": 15,
        "config": {
            "flash_imbalance_threshold_pct": 30,
            "flash_imbalance_window_sec": 10,
            "iceberg_refill_threshold": 3,
            "spoofing_max_duration_sec": 30,
            "absorption_volume_multiplier": 2.0,
            "pressure_score_levels": 10,
        }
    },
    
    "institutional_flow": {
        "enabled": False,
        "description": "Institutional Order Flow Patterns - TWAP, VWAP, layering, sweeps",
        "confidence_boost": 20,
        "config": {
            "iceberg_min_trades": 10,
            "iceberg_size_consistency": 0.8,
            "twap_interval_consistency": 0.7,
            "vwap_price_tolerance_pct": 0.1,
            "layering_min_levels": 3,
            "sweep_min_levels": 3,
            "high_activity_threshold": 80,
        }
    },
    
    "volatility_regime": {
        "enabled": False,
        "description": "Volatility Regime Adaptive System - adjust parameters by regime",
        "confidence_boost": 15,  # For volatility compression
        "config": {
            "low_volatility_threshold": 15,
            "normal_volatility_range": (15, 30),
            "high_volatility_range": (30, 50),
            "extreme_volatility_threshold": 50,
            "compression_duration_days": 5,
            "compression_percentile": 20,
            "regime_adjustments": {
                "LOW": {"min_quality": "A+", "sl_buffer_multiplier": 1.0, "leverage_multiplier": 1.0},
                "NORMAL": {"min_quality": "A", "sl_buffer_multiplier": 1.0, "leverage_multiplier": 1.0},
                "HIGH": {"min_quality": "A", "sl_buffer_multiplier": 1.5, "leverage_multiplier": 0.75},
                "EXTREME": {"min_quality": "A+", "sl_buffer_multiplier": 2.0, "leverage_multiplier": 0.5},
            }
        }
    },
    
    "ml_confidence_calibration": {
        "enabled": True,
        "description": "ML Signal Confidence Calibration - calibrate confidence scores",
        "confidence_boost": 0,  # Adjusts confidence, doesn't boost
        "config": {
            "min_samples_for_training": 100,
            "retrain_interval_signals": 1000,
            "calibration_method": "isotonic",
            "confidence_bins": 10,
            "max_adjustment_pct": 20,
        }
    },
}


# ============================================================================
# PHASE 3: OPTIMIZATION & RISK (Features 11-15)
# ============================================================================

PHASE_3_FEATURES = {
    "dynamic_tp": {
        "enabled": False,
        "description": "Dynamic Take Profit Optimization - ATR-based TP with extensions",
        "confidence_boost": 0,
        "config": {
            "tp1_atr_multiplier": 1.5,
            "tp2_atr_multiplier": 3.0,
            "momentum_rsi_threshold": 70,
            "momentum_tp2_extension_pct": 50,
            "trailing_stop_distance_pct": 1.0,
            "partial_profit_pct": 50,
            "fibonacci_extensions": [1.618, 2.0, 2.618],
        }
    },
    
    "correlation_optimizer": {
        "enabled": False,
        "description": "Correlation-Based Portfolio Optimization - manage correlated positions",
        "confidence_boost": 0,
        "config": {
            "lookback_days": 30,
            "high_correlation_threshold": 0.8,
            "min_diversification_score": 40,
            "correlation_position_limit": 3,
            "update_interval_hours": 24,
        }
    },
    
    "news_sentiment": {
        "enabled": False,
        "description": "News Sentiment Integration - avoid high-impact events",
        "confidence_boost": 10,  # For positive sentiment
        "config": {
            "api_key": "",  # Set via config.json or environment variable
            "api_provider": "cryptopanic",  # cryptopanic or newsapi
            "lookback_hours": 24,
            "lookahead_hours": 2,
            "sentiment_shift_threshold": 30,
            "sentiment_shift_window_hours": 1,
            "negative_sentiment_penalty": -20,
            "positive_sentiment_boost": 10,
            "high_impact_block_duration_hours": 2,
            "update_interval_minutes": 15,
        }
    },
    
    "backtesting_engine": {
        "enabled": False,
        "description": "Backtesting Engine with Walk-Forward Analysis",
        "confidence_boost": 0,
        "config": {
            "walk_forward_train_months": 6,
            "walk_forward_test_months": 2,
            "overfitting_threshold": 0.7,
            "slippage_pct": 0.05,
            "commission_pct": 0.06,
            "initial_capital": 10000,
            "max_concurrent_positions": 5,
        }
    },
    
    "ab_testing": {
        "enabled": False,
        "description": "A/B Testing Framework - test features before deployment",
        "confidence_boost": 0,
        "config": {
            "min_samples_per_variant": 100,
            "significance_level": 0.05,
            "min_improvement_pct": 10,
            "split_ratio": 0.5,
            "max_concurrent_experiments": 3,
        }
    },
}


# ============================================================================
# PHASE 4: ADVANCED RISK & ANALYTICS (Features 16-20)
# ============================================================================

PHASE_4_FEATURES = {
    "enhanced_risk": {
        "enabled": False,
        "description": "Enhanced Risk Management - Kelly Criterion, dynamic sizing",
        "confidence_boost": 0,
        "config": {
            "base_risk_per_trade_pct": 1.0,
            "max_portfolio_risk_pct": 5.0,
            "max_daily_loss_pct": 3.0,
            "consecutive_loss_threshold": 3,
            "consecutive_win_threshold": 5,
            "loss_reduction_multiplier": 0.5,
            "win_increase_multiplier": 1.25,
            "max_position_size_multiplier": 2.0,
            "kelly_fraction": 0.25,
        }
    },
    
    "market_microstructure": {
        "enabled": False,
        "description": "Market Microstructure Analysis - spread, price impact, toxicity",
        "confidence_boost": 12,
        "config": {
            "spread_widening_threshold": 2.0,
            "spread_widening_duration_min": 5,
            "toxic_flow_threshold": 70,
            "quote_stuffing_threshold": 100,
            "price_impact_levels": [1000, 5000, 10000, 50000],
        }
    },
    
    "seasonality_detection": {
        "enabled": False,
        "description": "Seasonality and Cyclical Pattern Detection - time-based patterns",
        "confidence_boost": 8,
        "config": {
            "min_lookback_days": 365,
            "pattern_accuracy_threshold": 65,
            "confidence_boost": 8,
            "fft_min_period_days": 7,
            "fft_max_period_days": 90,
        }
    },
    
    "adaptive_sl": {
        "enabled": False,
        "description": "Adaptive Stop Loss System - ATR-based with regime adjustment",
        "confidence_boost": 0,
        "config": {
            "base_atr_multiplier": 2.0,
            "low_volatility_multiplier": 1.5,
            "normal_volatility_multiplier": 2.0,
            "high_volatility_multiplier": 3.0,
            "breakeven_threshold_pct": 50,
            "profit_lock_threshold_pct": 100,
            "chandelier_enabled": True,
        }
    },
    
    "performance_dashboard": {
        "enabled": False,
        "description": "Performance Analytics Dashboard - real-time metrics",
        "confidence_boost": 0,
        "config": {
            "update_interval_seconds": 60,
            "equity_curve_points": 720,
            "performance_lookback_days": 30,
            "export_formats": ["pdf", "csv"],
        }
    },
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_all_features() -> Dict[str, Dict[str, Any]]:
    """Get all features across all phases."""
    return {
        **PHASE_1_FEATURES,
        **PHASE_2_FEATURES,
        **PHASE_3_FEATURES,
        **PHASE_4_FEATURES,
    }


def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature is enabled."""
    all_features = get_all_features()
    return all_features.get(feature_name, {}).get("enabled", False)


def get_feature_config(feature_name: str) -> Dict[str, Any]:
    """Get configuration for a specific feature."""
    all_features = get_all_features()
    return all_features.get(feature_name, {}).get("config", {})


def get_enabled_features() -> Dict[str, Dict[str, Any]]:
    """Get all currently enabled features."""
    all_features = get_all_features()
    return {name: config for name, config in all_features.items() if config.get("enabled", False)}


def enable_phase(phase: int):
    """Enable all features in a specific phase (1-4)."""
    phase_map = {
        1: PHASE_1_FEATURES,
        2: PHASE_2_FEATURES,
        3: PHASE_3_FEATURES,
        4: PHASE_4_FEATURES,
    }
    
    if phase not in phase_map:
        raise ValueError(f"Invalid phase: {phase}. Must be 1-4.")
    
    for feature_name, feature_config in phase_map[phase].items():
        feature_config["enabled"] = True


def disable_all_features():
    """Disable all features (rollback to baseline)."""
    for features in [PHASE_1_FEATURES, PHASE_2_FEATURES, PHASE_3_FEATURES, PHASE_4_FEATURES]:
        for feature_config in features.values():
            feature_config["enabled"] = False


# ============================================================================
# CIRCUIT BREAKER CONFIGURATION
# ============================================================================

CIRCUIT_BREAKER_CONFIG = {
    "enabled": True,
    "failure_threshold": 5,  # Open circuit after 5 failures
    "success_threshold": 3,  # Close circuit after 3 successes
    "timeout_seconds": 60,  # Try again after 60 seconds
    "half_open_max_calls": 1,  # Allow 1 call in half-open state
}
