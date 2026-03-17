-- Migration: Advanced Trading Optimization Infrastructure
-- Date: 2025-01-XX
-- Description: Add tables and columns for 20 advanced trading features

-- ============================================================================
-- NEW TABLES FOR ADVANCED ANALYTICS
-- ============================================================================

-- VSA (Volume Spread Analysis) Signals
CREATE TABLE IF NOT EXISTS vsa_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL,  -- NO_DEMAND, NO_SUPPLY, BUYING_CLIMAX, SELLING_CLIMAX, STOPPING_VOLUME
    confidence REAL NOT NULL,
    volume_ratio REAL NOT NULL,
    spread_ratio REAL NOT NULL,
    close_position REAL NOT NULL,  -- 0-1 position of close in candle range
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_vsa_symbol ON vsa_signals(symbol, timestamp);

-- Wyckoff Phases and Events
CREATE TABLE IF NOT EXISTS wyckoff_phases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    phase TEXT NOT NULL,  -- ACCUMULATION, MARKUP, DISTRIBUTION, MARKDOWN
    confidence REAL NOT NULL,
    duration_candles INTEGER NOT NULL,
    volume_profile TEXT NOT NULL,  -- INCREASING, DECREASING, STABLE
    events_json TEXT,  -- JSON array of WyckoffEvent objects
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_wyckoff_symbol ON wyckoff_phases(symbol, timestamp);

-- Market Profile (TPO) Data
CREATE TABLE IF NOT EXISTS market_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    poc REAL NOT NULL,  -- Point of Control
    vah REAL NOT NULL,  -- Value Area High
    val REAL NOT NULL,  -- Value Area Low
    profile_shape TEXT NOT NULL,  -- NORMAL, P_SHAPE, B_SHAPE, DOUBLE_DISTRIBUTION
    poor_highs_json TEXT,  -- JSON array of poor high prices
    poor_lows_json TEXT,  -- JSON array of poor low prices
    tpo_distribution_json TEXT,  -- JSON object: price -> TPO count
    volume_distribution_json TEXT,  -- JSON object: price -> volume
    created_at TEXT NOT NULL,
    UNIQUE(symbol, date)
);

CREATE INDEX IF NOT EXISTS idx_profile_symbol ON market_profiles(symbol, date);

-- Liquidity Sweeps
CREATE TABLE IF NOT EXISTS liquidity_sweeps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    pool_level REAL NOT NULL,
    pool_type TEXT NOT NULL,  -- EQUAL_HIGHS, EQUAL_LOWS, STOP_CLUSTER
    sweep_price REAL NOT NULL,
    reversal_price REAL NOT NULL,
    volume_spike REAL NOT NULL,
    confidence REAL NOT NULL,
    direction TEXT NOT NULL,  -- BULLISH_SWEEP, BEARISH_SWEEP
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sweeps_symbol ON liquidity_sweeps(symbol, timestamp);

-- Smart Money Divergences
CREATE TABLE IF NOT EXISTS divergences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    divergence_type TEXT NOT NULL,  -- BULLISH, BEARISH
    divergence_class TEXT NOT NULL,  -- REGULAR, HIDDEN
    indicator TEXT NOT NULL,  -- CVD, OPEN_INTEREST, FUNDING_RATE
    strength REAL NOT NULL,
    price_swing_start REAL NOT NULL,
    price_swing_end REAL NOT NULL,
    indicator_swing_start REAL NOT NULL,
    indicator_swing_end REAL NOT NULL,
    confidence_boost REAL NOT NULL,
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_divergence_symbol ON divergences(symbol, timestamp);

-- News Items and Sentiment
CREATE TABLE IF NOT EXISTS news_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    published_at TEXT NOT NULL,
    url TEXT NOT NULL,
    sentiment TEXT NOT NULL,  -- POSITIVE, NEGATIVE, NEUTRAL
    impact_score REAL NOT NULL,
    symbols_json TEXT NOT NULL,  -- JSON array of affected symbols
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_news_published ON news_items(published_at);

CREATE TABLE IF NOT EXISTS sentiment_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    score REAL NOT NULL,  -- -100 to +100
    sentiment TEXT NOT NULL,  -- POSITIVE, NEGATIVE, NEUTRAL
    news_count INTEGER NOT NULL,
    avg_impact REAL NOT NULL,
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sentiment_symbol ON sentiment_scores(symbol, timestamp);

-- ============================================================================
-- ML CALIBRATION TABLES
-- ============================================================================

-- Calibration Training Samples
CREATE TABLE IF NOT EXISTS calibration_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT NOT NULL,
    predicted_confidence REAL NOT NULL,
    actual_outcome INTEGER NOT NULL,  -- 1 for TP hit, 0 for SL hit
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_calibration_signal ON calibration_samples(signal_id);
CREATE INDEX IF NOT EXISTS idx_calibration_timestamp ON calibration_samples(timestamp);

-- ============================================================================
-- A/B TESTING FRAMEWORK TABLES
-- ============================================================================

-- Experiments
CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    variants_json TEXT NOT NULL,  -- JSON array of variant names
    start_date TEXT NOT NULL,
    end_date TEXT DEFAULT NULL,
    status TEXT NOT NULL,  -- ACTIVE, COMPLETED, CANCELLED
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_experiment_status ON experiments(status);

-- Experiment Assignments
CREATE TABLE IF NOT EXISTS experiment_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT NOT NULL,
    signal_id TEXT NOT NULL,
    variant TEXT NOT NULL,
    signal_data_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_assignment_experiment ON experiment_assignments(experiment_id);
CREATE INDEX IF NOT EXISTS idx_assignment_signal ON experiment_assignments(signal_id);

-- Experiment Outcomes
CREATE TABLE IF NOT EXISTS experiment_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT NOT NULL,
    outcome TEXT NOT NULL,  -- WIN, LOSS
    pnl REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_outcome_signal ON experiment_outcomes(signal_id);

-- ============================================================================
-- SEASONALITY AND PATTERNS
-- ============================================================================

-- Seasonal Patterns
CREATE TABLE IF NOT EXISTS seasonal_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    pattern_type TEXT NOT NULL,  -- DAY_OF_WEEK, TIME_OF_DAY, MONTHLY
    pattern_value TEXT NOT NULL,  -- e.g., "MONDAY", "ASIAN_SESSION", "END_OF_MONTH"
    direction TEXT NOT NULL,  -- BULLISH, BEARISH, NEUTRAL
    accuracy REAL NOT NULL,  -- Historical accuracy %
    sample_size INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(symbol, pattern_type, pattern_value)
);

CREATE INDEX IF NOT EXISTS idx_seasonal_symbol ON seasonal_patterns(symbol);
