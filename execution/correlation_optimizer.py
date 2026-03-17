"""
Correlation-Based Portfolio Optimization

Optimizes portfolio composition based on asset correlations to reduce risk
and improve diversification. Manages correlation between positions to prevent
over-concentration in correlated assets.

Features:
- Rolling 30-day correlation matrix calculation
- Highly correlated pair identification (correlation >0.8)
- Signal selection logic (choose highest confidence when correlated)
- Portfolio diversification score calculation (0-100)
- Correlation breakdown detection
- Position sizing recommendation based on correlation
- Integration with Portfolio_Manager.process_signal()

**Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8**
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from utils.logger import get_logger
from analytics.performance_cache import get_cache, CACHE_TTL

log = get_logger("execution.correlation_optimizer")


# ═══════════════════════════════════════════════════════════════════
# DEFAULT CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

DEFAULT_CONFIG = {
    "lookback_days": 30,  # 30-day rolling correlation
    "high_correlation_threshold": 0.8,  # >0.8 = highly correlated
    "min_diversification_score": 40,  # Min 40% diversification
    "correlation_position_limit": 3,  # Max 3 positions in correlated assets
    "update_interval_hours": 24,  # Update correlation matrix daily
    "correlation_breakdown_threshold": 0.3,  # >30% drop = breakdown
    "position_size_reduction_pct": 25,  # Reduce size by 25% for correlated assets
}


# ═══════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════

@dataclass
class CorrelatedPair:
    """Represents a pair of correlated assets."""
    symbol1: str
    symbol2: str
    correlation: float  # -1 to 1
    lookback_days: int
    timestamp: datetime


@dataclass
class CorrelationBreakdown:
    """Represents a sudden correlation breakdown."""
    pair: CorrelatedPair
    previous_correlation: float
    current_correlation: float
    change: float
    timestamp: datetime


@dataclass
class PortfolioDiversification:
    """Portfolio diversification metrics."""
    score: float  # 0-100
    avg_correlation: float
    max_correlation: float
    concentrated_sectors: List[str]
    total_positions: int


# ═══════════════════════════════════════════════════════════════════
# CORRELATION OPTIMIZER
# ═══════════════════════════════════════════════════════════════════

class CorrelationOptimizer:
    """
    Optimize portfolio by managing correlation between positions.
    
    Reduces risk and improves diversification by:
    - Tracking correlation between assets
    - Filtering conflicting signals
    - Adjusting position sizing
    - Detecting correlation breakdowns
    """
    
    def __init__(self, candle_manager=None, config: Dict = None):
        """
        Initialize CorrelationOptimizer.
        
        Args:
            candle_manager: CandleManager instance for historical data
            config: Optional configuration overrides
        """
        self.candle_mgr = candle_manager
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        
        # State
        self.correlation_matrix: Optional[pd.DataFrame] = None
        self.last_update: Optional[datetime] = None
        self.correlation_history: Dict[Tuple[str, str], List[float]] = {}
        
        log.info("CorrelationOptimizer initialized")
        log.info(f"  Lookback: {self.config['lookback_days']} days")
        log.info(f"  High correlation threshold: {self.config['high_correlation_threshold']}")
        log.info(f"  Min diversification score: {self.config['min_diversification_score']}%")
    
    # ═══════════════════════════════════════════════════════════════════
    # CORRELATION MATRIX CALCULATION (Requirement 12.1)
    # ═══════════════════════════════════════════════════════════════════
    
    def calculate_correlation_matrix(
        self, 
        symbols: List[str], 
        lookback_days: int = None
    ) -> pd.DataFrame:
        """
        Calculate rolling correlation matrix for all symbols.
        
        Uses caching to avoid expensive recalculation.
        Cache TTL: 1 hour (configurable via CACHE_TTL)
        
        Args:
            symbols: List of trading symbols
            lookback_days: Days of historical data (default: config value)
            
        Returns:
            DataFrame with pairwise correlations
            
        **Validates: Requirement 12.1**
        """
        if lookback_days is None:
            lookback_days = self.config["lookback_days"]
        
        if not symbols or len(symbols) < 2:
            log.warning("Need at least 2 symbols for correlation calculation")
            return pd.DataFrame()
        
        # Check cache first
        cache = get_cache()
        cache_key_symbols = tuple(sorted(symbols))  # Deterministic key
        cached_result = cache.get("correlation_matrix", cache_key_symbols, lookback_days)
        
        if cached_result is not None:
            log.debug(f"Using cached correlation matrix for {len(symbols)} symbols")
            self.correlation_matrix = cached_result
            return cached_result
        
        try:
            # Collect price data for all symbols
            price_data = {}
            
            for symbol in symbols:
                if self.candle_mgr:
                    # Get historical candles
                    candles = self.candle_mgr.get_candles(symbol, "1h", limit=lookback_days * 24)
                    if candles and len(candles) > 0:
                        # Extract close prices
                        prices = [c['close'] for c in candles]
                        price_data[symbol] = prices
                else:
                    # Fallback: generate synthetic data for testing
                    log.warning(f"No candle manager - using synthetic data for {symbol}")
                    price_data[symbol] = self._generate_synthetic_prices(lookback_days * 24)
            
            if len(price_data) < 2:
                log.warning("Insufficient price data for correlation calculation")
                return pd.DataFrame()
            
            # Create DataFrame
            df = pd.DataFrame(price_data)
            
            # Calculate returns (percentage change)
            returns = df.pct_change().dropna()
            
            # Calculate correlation matrix
            corr_matrix = returns.corr()
            
            self.correlation_matrix = corr_matrix
            self.last_update = datetime.utcnow()
            
            # Cache the result
            cache.set("correlation_matrix", corr_matrix, CACHE_TTL["correlation_matrix"], 
                     cache_key_symbols, lookback_days)
            
            log.info(f"Correlation matrix calculated and cached for {len(symbols)} symbols")
            return corr_matrix
            
        except Exception as e:
            log.error(f"Error calculating correlation matrix: {e}")
            return pd.DataFrame()
    
    def _generate_synthetic_prices(self, num_points: int) -> List[float]:
        """Generate synthetic price data for testing."""
        base_price = 50000
        prices = [base_price]
        
        for _ in range(num_points - 1):
            change = np.random.normal(0, 0.01)  # 1% std dev
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)
        
        return prices
    
    def should_update_matrix(self) -> bool:
        """Check if correlation matrix needs updating."""
        if self.last_update is None:
            return True
        
        hours_since_update = (datetime.utcnow() - self.last_update).total_seconds() / 3600
        return hours_since_update >= self.config["update_interval_hours"]
    
    # ═══════════════════════════════════════════════════════════════════
    # CORRELATED PAIR IDENTIFICATION (Requirement 12.2)
    # ═══════════════════════════════════════════════════════════════════
    
    def identify_correlated_pairs(
        self, 
        threshold: float = None
    ) -> List[CorrelatedPair]:
        """
        Identify highly correlated pairs (correlation >0.8).
        
        Args:
            threshold: Correlation threshold (default: config value)
            
        Returns:
            List of correlated pairs
            
        **Validates: Requirement 12.2**
        """
        if threshold is None:
            threshold = self.config["high_correlation_threshold"]
        
        if self.correlation_matrix is None or self.correlation_matrix.empty:
            log.warning("No correlation matrix available")
            return []
        
        correlated_pairs = []
        symbols = self.correlation_matrix.columns.tolist()
        
        # Iterate through upper triangle of correlation matrix
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols):
                if i >= j:  # Skip diagonal and lower triangle
                    continue
                
                correlation = self.correlation_matrix.loc[symbol1, symbol2]
                
                # Check if correlation exceeds threshold
                if abs(correlation) >= threshold:
                    pair = CorrelatedPair(
                        symbol1=symbol1,
                        symbol2=symbol2,
                        correlation=correlation,
                        lookback_days=self.config["lookback_days"],
                        timestamp=datetime.utcnow()
                    )
                    correlated_pairs.append(pair)
                    
                    # Track correlation history
                    pair_key = tuple(sorted([symbol1, symbol2]))
                    if pair_key not in self.correlation_history:
                        self.correlation_history[pair_key] = []
                    self.correlation_history[pair_key].append(correlation)
        
        log.info(f"Identified {len(correlated_pairs)} highly correlated pairs (threshold: {threshold})")
        return correlated_pairs
    
    def get_correlation(self, symbol1: str, symbol2: str) -> Optional[float]:
        """Get correlation between two symbols."""
        if self.correlation_matrix is None or self.correlation_matrix.empty:
            return None
        
        try:
            return self.correlation_matrix.loc[symbol1, symbol2]
        except KeyError:
            return None
    
    # ═══════════════════════════════════════════════════════════════════
    # SIGNAL SELECTION (Requirement 12.3)
    # ═══════════════════════════════════════════════════════════════════
    
    def select_best_signal(self, signals: List[Dict]) -> List[Dict]:
        """
        When multiple signals are correlated, select the one with highest confidence.
        
        Args:
            signals: List of potential signals
            
        Returns:
            Filtered signals with correlation conflicts resolved
            
        **Validates: Requirement 12.3**
        """
        if not signals or len(signals) <= 1:
            return signals
        
        # Update correlation matrix if needed
        symbols = [s["symbol"] for s in signals]
        if self.should_update_matrix():
            self.calculate_correlation_matrix(symbols)
        
        # Identify correlated pairs among signals
        correlated_pairs = self.identify_correlated_pairs()
        
        if not correlated_pairs:
            log.info("No correlated pairs found - all signals approved")
            return signals
        
        # Build conflict groups
        conflict_groups = self._build_conflict_groups(signals, correlated_pairs)
        
        # Select best signal from each conflict group
        selected_signals = []
        rejected_signals = []
        
        for group in conflict_groups:
            # Sort by confidence (descending)
            group_sorted = sorted(group, key=lambda s: s.get("confidence", 0), reverse=True)
            best_signal = group_sorted[0]
            selected_signals.append(best_signal)
            
            # Log rejected signals
            for signal in group_sorted[1:]:
                rejected_signals.append(signal)
                log.info(
                    f"Rejected {signal['symbol']} (conf: {signal.get('confidence', 0):.1f}%) "
                    f"due to correlation with {best_signal['symbol']} "
                    f"(conf: {best_signal.get('confidence', 0):.1f}%)"
                )
        
        log.info(f"Signal selection: {len(selected_signals)} selected, {len(rejected_signals)} rejected")
        return selected_signals
    
    def _build_conflict_groups(
        self, 
        signals: List[Dict], 
        correlated_pairs: List[CorrelatedPair]
    ) -> List[List[Dict]]:
        """Build groups of conflicting (correlated) signals."""
        # Create adjacency map
        adjacency = {s["symbol"]: [] for s in signals}
        
        for pair in correlated_pairs:
            if pair.symbol1 in adjacency and pair.symbol2 in adjacency:
                adjacency[pair.symbol1].append(pair.symbol2)
                adjacency[pair.symbol2].append(pair.symbol1)
        
        # Find connected components (conflict groups)
        visited = set()
        groups = []
        
        for signal in signals:
            symbol = signal["symbol"]
            if symbol in visited:
                continue
            
            # BFS to find all connected symbols
            group = []
            queue = [symbol]
            
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                
                visited.add(current)
                
                # Find signal for this symbol
                signal_obj = next((s for s in signals if s["symbol"] == current), None)
                if signal_obj:
                    group.append(signal_obj)
                
                # Add neighbors
                for neighbor in adjacency.get(current, []):
                    if neighbor not in visited:
                        queue.append(neighbor)
            
            if group:
                groups.append(group)
        
        return groups
    
    # ═══════════════════════════════════════════════════════════════════
    # DIVERSIFICATION SCORE (Requirement 12.4)
    # ═══════════════════════════════════════════════════════════════════
    
    def calculate_diversification_score(
        self, 
        active_positions: List[Dict]
    ) -> PortfolioDiversification:
        """
        Calculate portfolio diversification score (0-100).
        
        Higher score = better diversification
        
        Args:
            active_positions: List of active positions
            
        Returns:
            PortfolioDiversification with score and metrics
            
        **Validates: Requirement 12.4**
        """
        if not active_positions or len(active_positions) == 0:
            return PortfolioDiversification(
                score=100.0,
                avg_correlation=0.0,
                max_correlation=0.0,
                concentrated_sectors=[],
                total_positions=0
            )
        
        symbols = [p.get("symbol", "") for p in active_positions if p.get("symbol")]
        
        if len(symbols) < 2:
            # Single position = perfect diversification (no correlation risk)
            return PortfolioDiversification(
                score=100.0,
                avg_correlation=0.0,
                max_correlation=0.0,
                concentrated_sectors=[],
                total_positions=len(symbols)
            )
        
        # Update correlation matrix if needed
        if self.should_update_matrix():
            self.calculate_correlation_matrix(symbols)
        
        # Calculate average and max correlation
        correlations = []
        
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols):
                if i >= j:
                    continue
                
                corr = self.get_correlation(symbol1, symbol2)
                if corr is not None:
                    correlations.append(abs(corr))
        
        if not correlations:
            avg_correlation = 0.0
            max_correlation = 0.0
        else:
            avg_correlation = np.mean(correlations)
            max_correlation = np.max(correlations)
        
        # Calculate diversification score
        # Score = 100 - (avg_correlation * 100)
        # Perfect diversification (0 correlation) = 100
        # Perfect correlation (1.0) = 0
        score = max(0, 100 - (avg_correlation * 100))
        
        # Identify concentrated sectors (symbols with high correlation)
        concentrated = []
        threshold = self.config["high_correlation_threshold"]
        
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols):
                if i >= j:
                    continue
                
                corr = self.get_correlation(symbol1, symbol2)
                if corr is not None and abs(corr) >= threshold:
                    if symbol1 not in concentrated:
                        concentrated.append(symbol1)
                    if symbol2 not in concentrated:
                        concentrated.append(symbol2)
        
        result = PortfolioDiversification(
            score=round(score, 2),
            avg_correlation=round(avg_correlation, 4),
            max_correlation=round(max_correlation, 4),
            concentrated_sectors=concentrated,
            total_positions=len(symbols)
        )
        
        log.info(
            f"Diversification score: {result.score:.1f}% "
            f"(avg corr: {result.avg_correlation:.3f}, max corr: {result.max_correlation:.3f})"
        )
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════
    # POSITION LIMITING (Requirement 12.5)
    # ═══════════════════════════════════════════════════════════════════
    
    def should_limit_position(
        self, 
        symbol: str, 
        active_positions: List[Dict]
    ) -> bool:
        """
        Check if new position would over-concentrate portfolio in correlated assets.
        
        Args:
            symbol: Symbol for new position
            active_positions: Current active positions
            
        Returns:
            True if position should be limited/rejected
            
        **Validates: Requirement 12.5**
        """
        if not active_positions:
            return False
        
        # Calculate current diversification
        diversification = self.calculate_diversification_score(active_positions)
        
        # Check if diversification is already too low
        min_score = self.config["min_diversification_score"]
        if diversification.score < min_score:
            log.warning(
                f"Portfolio diversification too low ({diversification.score:.1f}% < {min_score}%) "
                f"- limiting new position in {symbol}"
            )
            return True
        
        # Check correlation with existing positions
        active_symbols = [p.get("symbol", "") for p in active_positions if p.get("symbol")]
        
        # Update correlation matrix
        all_symbols = active_symbols + [symbol]
        if self.should_update_matrix():
            self.calculate_correlation_matrix(all_symbols)
        
        # Count highly correlated positions
        correlated_count = 0
        threshold = self.config["high_correlation_threshold"]
        
        for active_symbol in active_symbols:
            corr = self.get_correlation(symbol, active_symbol)
            if corr is not None and abs(corr) >= threshold:
                correlated_count += 1
        
        # Check if exceeds limit
        limit = self.config["correlation_position_limit"]
        if correlated_count >= limit:
            log.warning(
                f"Too many correlated positions ({correlated_count} >= {limit}) "
                f"- limiting new position in {symbol}"
            )
            return True
        
        return False
    
    # ═══════════════════════════════════════════════════════════════════
    # CORRELATION BREAKDOWN DETECTION (Requirement 12.6)
    # ═══════════════════════════════════════════════════════════════════
    
    def detect_correlation_breakdown(
        self, 
        pair: CorrelatedPair
    ) -> Optional[CorrelationBreakdown]:
        """
        Detect sudden correlation breakdown (risk signal).
        
        Args:
            pair: Correlated pair to check
            
        Returns:
            CorrelationBreakdown if detected, None otherwise
            
        **Validates: Requirement 12.6**
        """
        pair_key = tuple(sorted([pair.symbol1, pair.symbol2]))
        
        if pair_key not in self.correlation_history:
            return None
        
        history = self.correlation_history[pair_key]
        
        if len(history) < 2:
            return None
        
        previous_corr = history[-2]
        current_corr = history[-1]
        
        # Calculate change
        change = abs(current_corr - previous_corr)
        threshold = self.config["correlation_breakdown_threshold"]
        
        if change >= threshold:
            breakdown = CorrelationBreakdown(
                pair=pair,
                previous_correlation=previous_corr,
                current_correlation=current_corr,
                change=change,
                timestamp=datetime.utcnow()
            )
            
            log.warning(
                f"Correlation breakdown detected: {pair.symbol1} <-> {pair.symbol2} "
                f"({previous_corr:.3f} -> {current_corr:.3f}, change: {change:.3f})"
            )
            
            return breakdown
        
        return None
    
    # ═══════════════════════════════════════════════════════════════════
    # POSITION SIZING RECOMMENDATION (Requirement 12.7)
    # ═══════════════════════════════════════════════════════════════════
    
    def recommend_position_sizing(
        self, 
        symbol: str, 
        base_size: float, 
        active_positions: List[Dict]
    ) -> float:
        """
        Recommend position size adjustment based on correlation.
        
        Args:
            symbol: Symbol for new position
            base_size: Base position size
            active_positions: Current active positions
            
        Returns:
            Adjusted position size
            
        **Validates: Requirement 12.7**
        """
        if not active_positions or base_size <= 0:
            return base_size
        
        active_symbols = [p.get("symbol", "") for p in active_positions if p.get("symbol")]
        
        # Update correlation matrix
        all_symbols = active_symbols + [symbol]
        if self.should_update_matrix():
            self.calculate_correlation_matrix(all_symbols)
        
        # Find max correlation with existing positions
        max_corr = 0.0
        threshold = self.config["high_correlation_threshold"]
        
        for active_symbol in active_symbols:
            corr = self.get_correlation(symbol, active_symbol)
            if corr is not None:
                max_corr = max(max_corr, abs(corr))
        
        # Reduce size if highly correlated
        if max_corr >= threshold:
            reduction_pct = self.config["position_size_reduction_pct"]
            adjusted_size = base_size * (1 - reduction_pct / 100)
            
            log.info(
                f"Position size reduced for {symbol}: "
                f"${base_size:.2f} -> ${adjusted_size:.2f} "
                f"(max correlation: {max_corr:.3f})"
            )
            
            return adjusted_size
        
        return base_size
    
    # ═══════════════════════════════════════════════════════════════════
    # INTEGRATION WITH PORTFOLIO MANAGER (Requirement 12.8)
    # ═══════════════════════════════════════════════════════════════════
    
    def process_signal_for_portfolio(
        self, 
        signal: Dict, 
        active_positions: List[Dict]
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Process signal through correlation checks before execution.
        
        This is the main integration point with Portfolio_Manager.
        
        Args:
            signal: Trading signal to process
            active_positions: Current active positions
            
        Returns:
            Tuple of (approved, rejection_reason, size_adjustment)
            
        **Validates: Requirement 12.8**
        """
        symbol = signal.get("symbol", "")
        
        # Check if position should be limited
        if self.should_limit_position(symbol, active_positions):
            return False, "Correlation limit exceeded", None
        
        # Calculate diversification score
        diversification = self.calculate_diversification_score(active_positions)
        
        if diversification.score < self.config["min_diversification_score"]:
            return False, f"Low diversification ({diversification.score:.1f}%)", None
        
        # Recommend position sizing adjustment
        base_size = signal.get("position_size", 1.0)
        adjusted_size = self.recommend_position_sizing(symbol, base_size, active_positions)
        
        size_adjustment = adjusted_size / base_size if base_size > 0 else 1.0
        
        log.info(
            f"Signal approved for {symbol} "
            f"(diversification: {diversification.score:.1f}%, "
            f"size adjustment: {size_adjustment:.2%})"
        )
        
        return True, None, size_adjustment
    
    # ═══════════════════════════════════════════════════════════════════
    # STATUS & REPORTING
    # ═══════════════════════════════════════════════════════════════════
    
    def get_status(self) -> Dict:
        """Get correlation optimizer status."""
        return {
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "matrix_size": len(self.correlation_matrix) if self.correlation_matrix is not None else 0,
            "tracked_pairs": len(self.correlation_history),
            "config": self.config,
        }

