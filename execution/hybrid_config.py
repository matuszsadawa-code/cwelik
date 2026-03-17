# Hybrid Order Executor Configuration

# Slippage Protection
MAX_SLIPPAGE_PCT = 0.1  # Maximum acceptable slippage for market orders (0.1%)
MAX_SLIPPAGE_AGGRESSIVE = 0.15  # For A+ signals in high volatility (0.15%)
MAX_SLIPPAGE_CONSERVATIVE = 0.05  # For A signals in normal conditions (0.05%)

# Limit Order Timeouts
LIMIT_TIMEOUT_SECONDS = 30  # Default timeout for limit orders
LIMIT_TIMEOUT_FAST = 15  # Fast timeout for A+ signals
LIMIT_TIMEOUT_SLOW = 60  # Slow timeout for B signals

# Liquidity Requirements
MIN_LIQUIDITY_RATIO = 2.0  # Minimum orderbook liquidity (2x position size)
MIN_LIQUIDITY_RATIO_STRICT = 3.0  # Strict requirement for large positions
MIN_LIQUIDITY_RATIO_RELAXED = 1.5  # Relaxed for small positions

# Volatility Thresholds
HIGH_VOLATILITY_THRESHOLD = 0.02  # 2% average range = high volatility
MEDIUM_VOLATILITY_THRESHOLD = 0.01  # 1% average range = medium volatility

# Order Type Decision Rules
ORDER_TYPE_RULES = {
    'A+': {
        'high_liquidity_high_volatility': 'MARKET',
        'high_liquidity_medium_volatility': 'MARKET',
        'medium_liquidity_high_volatility': 'LIMIT_WITH_TIMEOUT',
        'medium_liquidity_medium_volatility': 'LIMIT_WITH_TIMEOUT',
        'low_liquidity': 'LIMIT',
        'default': 'LIMIT_WITH_TIMEOUT'
    },
    'A': {
        'high_liquidity_high_volatility': 'LIMIT_WITH_TIMEOUT',
        'high_liquidity_medium_volatility': 'LIMIT_WITH_TIMEOUT',
        'medium_liquidity': 'LIMIT',
        'low_liquidity': 'LIMIT',
        'default': 'LIMIT'
    },
    'B': {
        'default': 'LIMIT'
    },
    'C': {
        'default': 'LIMIT'
    }
}

# Symbol-Specific Settings
SYMBOL_SETTINGS = {
    'BTCUSDT': {
        'max_slippage_pct': 0.1,
        'min_liquidity_ratio': 2.0,
        'limit_timeout': 30
    },
    'ETHUSDT': {
        'max_slippage_pct': 0.15,
        'min_liquidity_ratio': 2.0,
        'limit_timeout': 30
    },
    # Altcoins - more conservative
    'default_altcoin': {
        'max_slippage_pct': 0.2,
        'min_liquidity_ratio': 3.0,
        'limit_timeout': 60
    }
}

# Position Size Thresholds
LARGE_POSITION_THRESHOLD = 1.0  # BTC - positions larger than this use stricter rules
SMALL_POSITION_THRESHOLD = 0.1  # BTC - positions smaller than this can use relaxed rules

# Retry Settings
MAX_RETRIES = 3  # Maximum retry attempts for failed orders
RETRY_DELAY_SECONDS = 2  # Delay between retries

# Logging
LOG_ALL_ORDERS = True  # Log all order attempts
LOG_MARKET_CONDITIONS = True  # Log market condition analysis
LOG_DECISION_REASONING = True  # Log order type decision reasoning

# Safety Limits
MAX_DAILY_MARKET_ORDERS = 50  # Maximum market orders per day (prevent excessive fees)
MAX_CONSECUTIVE_FAILED_ORDERS = 5  # Halt trading after this many failures

# Fee Considerations
MAKER_FEE_PCT = -0.01  # Bybit maker fee (rebate)
TAKER_FEE_PCT = 0.06  # Bybit taker fee
MIN_RR_RATIO_MARKET = 2.5  # Minimum R:R for market orders (account for fees)
MIN_RR_RATIO_LIMIT = 2.0  # Minimum R:R for limit orders
