"""
Configuration Validator for Advanced Trading Optimization Features

This module validates configuration parameters to ensure they are within acceptable ranges
and meet all requirements before the system starts.
"""

from typing import Dict, List, Tuple, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass


class ConfigValidator:
    """Validates configuration parameters for all 20 advanced features"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_all(self, config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate all configuration parameters.
        
        Args:
            config: Master configuration dictionary
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        # Validate each feature configuration
        self._validate_vsa(config.get("vsa", {}))
        self._validate_wyckoff(config.get("wyckoff", {}))
        self._validate_market_profile(config.get("market_profile", {}))
        self._validate_liquidity_engineering(config.get("liquidity_engineering", {}))
        self._validate_smart_money_divergence(config.get("smart_money_divergence", {}))
        self._validate_mtf_confluence(config.get("mtf_confluence", {}))
        self._validate_orderbook_imbalance(config.get("orderbook_imbalance", {}))
        self._validate_institutional_flow(config.get("institutional_flow", {}))
        self._validate_volatility_regime(config.get("volatility_regime", {}))
        self._validate_ml_calibration(config.get("ml_calibration", {}))
        self._validate_dynamic_tp(config.get("dynamic_tp", {}))
        self._validate_correlation_optimizer(config.get("correlation_optimizer", {}))
        self._validate_news_sentiment(config.get("news_sentiment", {}))
        self._validate_backtesting(config.get("backtesting", {}))
        self._validate_ab_testing(config.get("ab_testing", {}))
        self._validate_enhanced_risk(config.get("enhanced_risk", {}))
        self._validate_microstructure(config.get("microstructure", {}))
        self._validate_seasonality(config.get("seasonality", {}))
        self._validate_adaptive_sl(config.get("adaptive_sl", {}))
        self._validate_dashboard(config.get("dashboard", {}))
        
        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings
    
    def _validate_range(self, value: float, min_val: float, max_val: float, 
                       param_name: str, feature: str):
        """Validate that a value is within acceptable range"""
        if not (min_val <= value <= max_val):
            self.errors.append(
                f"{feature}.{param_name}: {value} is outside valid range [{min_val}, {max_val}]"
            )
    
    def _validate_positive(self, value: float, param_name: str, feature: str):
        """Validate that a value is positive"""
        if value <= 0:
            self.errors.append(f"{feature}.{param_name}: {value} must be positive")
    
    def _validate_percentage(self, value: float, param_name: str, feature: str):
        """Validate that a value is a valid percentage (0-100)"""
        self._validate_range(value, 0, 100, param_name, feature)
    
    def _validate_vsa(self, config: Dict):
        """Validate VSA configuration"""
        if not config.get("enabled", True):
            return
        
        self._validate_positive(config.get("high_volume_threshold", 1.5), 
                               "high_volume_threshold", "VSA")
        self._validate_range(config.get("narrow_spread_threshold", 0.7), 
                            0.1, 1.0, "narrow_spread_threshold", "VSA")
        self._validate_range(config.get("wide_spread_threshold", 1.3), 
                            1.0, 3.0, "wide_spread_threshold", "VSA")
        self._validate_positive(config.get("lookback_period", 20), 
                               "lookback_period", "VSA")
    
    def _validate_wyckoff(self, config: Dict):
        """Validate Wyckoff configuration"""
        if not config.get("enabled", True):
            return
        
        self._validate_range(config.get("accumulation_volume_decrease", 0.7), 
                            0.3, 0.9, "accumulation_volume_decrease", "Wyckoff")
        self._validate_range(config.get("distribution_volume_increase", 1.3), 
                            1.1, 2.0, "distribution_volume_increase", "Wyckoff")
        self._validate_positive(config.get("phase_min_candles", 20), 
                               "phase_min_candles", "Wyckoff")
    
    def _validate_market_profile(self, config: Dict):
        """Validate Market Profile configuration"""
        if not config.get("enabled", True):
            return
        
        self._validate_positive(config.get("period_minutes", 30), 
                               "period_minutes", "Market Profile")
        self._validate_range(config.get("value_area_pct", 70), 
                            50, 90, "value_area_pct", "Market Profile")
    
    def _validate_liquidity_engineering(self, config: Dict):
        """Validate Liquidity Engineering configuration"""
        if not config.get("enabled", True):
            return
        
        self._validate_range(config.get("equal_level_tolerance_pct", 0.2), 
                            0.05, 1.0, "equal_level_tolerance_pct", "Liquidity Engineering")
        self._validate_range(config.get("sweep_penetration_pct", 0.3), 
                            0.1, 1.0, "sweep_penetration_pct", "Liquidity Engineering")
        self._validate_positive(config.get("sweep_reversal_candles", 3), 
                               "sweep_reversal_candles", "Liquidity Engineering")
    
    def _validate_smart_money_divergence(self, config: Dict):
        """Validate Smart Money Divergence configuration"""
        if not config.get("enabled", True):
            return
        
        self._validate_positive(config.get("min_swing_size_pct", 2.0), 
                               "min_swing_size_pct", "Smart Money Divergence")
        self._validate_positive(config.get("lookback_candles", 50), 
                               "lookback_candles", "Smart Money Divergence")
    
    def _validate_mtf_confluence(self, config: Dict):
        """Validate Multi-Timeframe Confluence configuration"""
        if not config.get("enabled", True):
            return
        
        timeframes = config.get("timeframes", [])
        if len(timeframes) < 2:
            self.errors.append("MTF Confluence: Must have at least 2 timeframes")
        
        min_confluence = config.get("min_confluence_timeframes", 3)
        if min_confluence > len(timeframes):
            self.errors.append(
                f"MTF Confluence: min_confluence_timeframes ({min_confluence}) "
                f"cannot exceed number of timeframes ({len(timeframes)})"
            )
    
    def _validate_orderbook_imbalance(self, config: Dict):
        """Validate Order Book Imbalance configuration"""
        if not config.get("enabled", True):
            return
        
        self._validate_percentage(config.get("flash_imbalance_threshold_pct", 30), 
                                 "flash_imbalance_threshold_pct", "Order Book Imbalance")
        self._validate_positive(config.get("flash_imbalance_window_sec", 10), 
                               "flash_imbalance_window_sec", "Order Book Imbalance")
    
    def _validate_institutional_flow(self, config: Dict):
        """Validate Institutional Flow configuration"""
        if not config.get("enabled", True):
            return
        
        self._validate_positive(config.get("iceberg_min_trades", 10), 
                               "iceberg_min_trades", "Institutional Flow")
        self._validate_range(config.get("iceberg_size_consistency", 0.8), 
                            0.5, 1.0, "iceberg_size_consistency", "Institutional Flow")
    
    def _validate_volatility_regime(self, config: Dict):
        """Validate Volatility Regime configuration"""
        if not config.get("enabled", True):
            return
        
        low_threshold = config.get("low_volatility_threshold", 15)
        normal_range = config.get("normal_volatility_range", (15, 30))
        high_range = config.get("high_volatility_range", (30, 50))
        extreme_threshold = config.get("extreme_volatility_threshold", 50)
        
        if not (low_threshold <= normal_range[0] <= normal_range[1] <= 
                high_range[0] <= high_range[1] <= extreme_threshold):
            self.errors.append(
                "Volatility Regime: Thresholds must be in ascending order: "
                "low < normal_min < normal_max < high_min < high_max < extreme"
            )
    
    def _validate_ml_calibration(self, config: Dict):
        """Validate ML Calibration configuration"""
        if not config.get("enabled", True):
            return
        
        self._validate_positive(config.get("min_samples_for_training", 100), 
                               "min_samples_for_training", "ML Calibration")
        self._validate_positive(config.get("retrain_interval_signals", 1000), 
                               "retrain_interval_signals", "ML Calibration")
        
        method = config.get("calibration_method", "isotonic")
        if method not in ["isotonic", "platt"]:
            self.errors.append(
                f"ML Calibration: calibration_method must be 'isotonic' or 'platt', got '{method}'"
            )
    
    def _validate_dynamic_tp(self, config: Dict):
        """Validate Dynamic TP configuration"""
        if not config.get("enabled", True):
            return
        
        tp1_mult = config.get("tp1_atr_multiplier", 1.5)
        tp2_mult = config.get("tp2_atr_multiplier", 3.0)
        
        if tp2_mult <= tp1_mult:
            self.errors.append(
                f"Dynamic TP: tp2_atr_multiplier ({tp2_mult}) must be greater than "
                f"tp1_atr_multiplier ({tp1_mult})"
            )
        
        self._validate_range(config.get("partial_profit_pct", 50), 
                            10, 90, "partial_profit_pct", "Dynamic TP")
    
    def _validate_correlation_optimizer(self, config: Dict):
        """Validate Correlation Optimizer configuration"""
        if not config.get("enabled", True):
            return
        
        self._validate_positive(config.get("lookback_days", 30), 
                               "lookback_days", "Correlation Optimizer")
        self._validate_range(config.get("high_correlation_threshold", 0.8), 
                            0.5, 1.0, "high_correlation_threshold", "Correlation Optimizer")
    
    def _validate_news_sentiment(self, config: Dict):
        """Validate News Sentiment configuration"""
        if not config.get("enabled", True):
            return
        
        provider = config.get("api_provider", "cryptopanic")
        if provider not in ["cryptopanic", "newsapi"]:
            self.warnings.append(
                f"News Sentiment: Unknown api_provider '{provider}', "
                "expected 'cryptopanic' or 'newsapi'"
            )
        
        self._validate_positive(config.get("lookback_hours", 24), 
                               "lookback_hours", "News Sentiment")
    
    def _validate_backtesting(self, config: Dict):
        """Validate Backtesting configuration"""
        if not config.get("enabled", True):
            return
        
        self._validate_positive(config.get("walk_forward_train_months", 6), 
                               "walk_forward_train_months", "Backtesting")
        self._validate_positive(config.get("walk_forward_test_months", 2), 
                               "walk_forward_test_months", "Backtesting")
        self._validate_range(config.get("overfitting_threshold", 0.7), 
                            0.5, 1.0, "overfitting_threshold", "Backtesting")
    
    def _validate_ab_testing(self, config: Dict):
        """Validate A/B Testing configuration"""
        if not config.get("enabled", True):
            return
        
        self._validate_positive(config.get("min_samples_per_variant", 100), 
                               "min_samples_per_variant", "A/B Testing")
        self._validate_range(config.get("significance_level", 0.05), 
                            0.01, 0.20, "significance_level", "A/B Testing")
    
    def _validate_enhanced_risk(self, config: Dict):
        """Validate Enhanced Risk Management configuration"""
        if not config.get("enabled", True):
            return
        
        base_risk = config.get("base_risk_per_trade_pct", 1.0)
        max_portfolio = config.get("max_portfolio_risk_pct", 5.0)
        max_daily = config.get("max_daily_loss_pct", 3.0)
        
        self._validate_percentage(base_risk, "base_risk_per_trade_pct", "Enhanced Risk")
        self._validate_percentage(max_portfolio, "max_portfolio_risk_pct", "Enhanced Risk")
        self._validate_percentage(max_daily, "max_daily_loss_pct", "Enhanced Risk")
        
        if base_risk > max_portfolio:
            self.warnings.append(
                f"Enhanced Risk: base_risk_per_trade_pct ({base_risk}%) is greater than "
                f"max_portfolio_risk_pct ({max_portfolio}%), which may limit trading"
            )
    
    def _validate_microstructure(self, config: Dict):
        """Validate Microstructure configuration"""
        if not config.get("enabled", True):
            return
        
        self._validate_positive(config.get("spread_widening_threshold", 2.0), 
                               "spread_widening_threshold", "Microstructure")
        self._validate_percentage(config.get("toxic_flow_threshold", 70), 
                                 "toxic_flow_threshold", "Microstructure")
    
    def _validate_seasonality(self, config: Dict):
        """Validate Seasonality configuration"""
        if not config.get("enabled", True):
            return
        
        min_lookback = config.get("min_lookback_days", 365)
        if min_lookback < 180:
            self.warnings.append(
                f"Seasonality: min_lookback_days ({min_lookback}) is less than 180 days, "
                "which may not provide sufficient data for reliable seasonal patterns"
            )
        
        self._validate_percentage(config.get("pattern_accuracy_threshold", 65), 
                                 "pattern_accuracy_threshold", "Seasonality")
    
    def _validate_adaptive_sl(self, config: Dict):
        """Validate Adaptive SL configuration"""
        if not config.get("enabled", True):
            return
        
        atr_multipliers = config.get("atr_multipliers", {})
        required_regimes = ["LOW", "NORMAL", "HIGH", "EXTREME"]
        
        for regime in required_regimes:
            if regime not in atr_multipliers:
                self.errors.append(
                    f"Adaptive SL: Missing ATR multiplier for regime '{regime}'"
                )
            else:
                self._validate_positive(atr_multipliers[regime], 
                                       f"atr_multipliers.{regime}", "Adaptive SL")
        
        # Verify multipliers increase with volatility
        if all(regime in atr_multipliers for regime in required_regimes):
            if not (atr_multipliers["LOW"] <= atr_multipliers["NORMAL"] <= 
                   atr_multipliers["HIGH"] <= atr_multipliers["EXTREME"]):
                self.warnings.append(
                    "Adaptive SL: ATR multipliers should increase with volatility regime "
                    "(LOW < NORMAL < HIGH < EXTREME)"
                )
    
    def _validate_dashboard(self, config: Dict):
        """Validate Dashboard configuration"""
        if not config.get("enabled", True):
            return
        
        self._validate_positive(config.get("update_interval_seconds", 5), 
                               "update_interval_seconds", "Dashboard")
        self._validate_positive(config.get("default_lookback_days", 30), 
                               "default_lookback_days", "Dashboard")
        
        chart_lib = config.get("chart_library", "plotly")
        if chart_lib not in ["plotly", "chartjs"]:
            self.warnings.append(
                f"Dashboard: Unknown chart_library '{chart_lib}', "
                "expected 'plotly' or 'chartjs'"
            )


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate configuration and raise exception if invalid.
    
    Args:
        config: Master configuration dictionary
        
    Raises:
        ConfigValidationError: If configuration is invalid
    """
    validator = ConfigValidator()
    is_valid, errors, warnings = validator.validate_all(config)
    
    # Log warnings
    for warning in warnings:
        logger.warning(f"Configuration warning: {warning}")
    
    # Raise exception if errors found
    if not is_valid:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        logger.error(error_msg)
        raise ConfigValidationError(error_msg)
    
    logger.info("Configuration validation passed successfully")


def load_config(config_type: str = "default") -> Dict[str, Any]:
    """
    Load and validate configuration.
    
    Args:
        config_type: Configuration type - "default", "conservative", or "aggressive"
        
    Returns:
        Validated configuration dictionary
        
    Raises:
        ConfigValidationError: If configuration is invalid
        ValueError: If config_type is unknown
    """
    if config_type == "default":
        from config.advanced_features_default import ADVANCED_FEATURES_CONFIG
    elif config_type == "conservative":
        from config.advanced_features_conservative import ADVANCED_FEATURES_CONFIG
    elif config_type == "aggressive":
        from config.advanced_features_aggressive import ADVANCED_FEATURES_CONFIG
    else:
        raise ValueError(
            f"Unknown config_type '{config_type}'. "
            "Must be 'default', 'conservative', or 'aggressive'"
        )
    
    # Validate configuration
    validate_config(ADVANCED_FEATURES_CONFIG)
    
    return ADVANCED_FEATURES_CONFIG
