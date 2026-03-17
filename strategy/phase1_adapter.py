"""
Phase 1 Integration for SignalEngine
Connects Phase 1 enhanced analytics to the existing trading system.
"""

from typing import Dict, List, Optional
from collections import deque
from analytics.phase1_integration import Phase1EnhancedAnalytics
from utils.logger import get_logger

log = get_logger("strategy.phase1_adapter")


class Phase1AccuracyTracker:
    """Tracks Phase 1 prediction accuracy for feedback loop."""
    
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.predictions = deque(maxlen=max_history)
        self.conflicts = deque(maxlen=max_history)
        
    def record_prediction(self, phase1_direction: str, actual_direction: str, 
                         phase1_confidence: float, outcome: str):
        """Record a Phase 1 prediction and its outcome.
        
        Args:
            phase1_direction: Phase 1 predicted direction (LONG/SHORT)
            actual_direction: Actual signal direction taken
            phase1_confidence: Phase 1 confidence (0-1)
            outcome: 'correct' if Phase 1 was right, 'incorrect' if wrong, 'rejected' if conflicted
        """
        self.predictions.append({
            'phase1_direction': phase1_direction,
            'actual_direction': actual_direction,
            'confidence': phase1_confidence,
            'outcome': outcome,
            'agreed': phase1_direction == actual_direction
        })
        
    def record_conflict(self, phase1_direction: str, step1_direction: str, 
                       phase1_confidence: float, action: str):
        """Record a directional conflict between Phase 1 and Step 1.
        
        Args:
            phase1_direction: Phase 1 direction
            step1_direction: Step 1 trend direction
            phase1_confidence: Phase 1 confidence
            action: 'rejected' or 'continued'
        """
        self.conflicts.append({
            'phase1_direction': phase1_direction,
            'step1_direction': step1_direction,
            'confidence': phase1_confidence,
            'action': action
        })
        
    def get_accuracy(self) -> float:
        """Calculate Phase 1 accuracy.
        
        Returns:
            Accuracy as percentage (0-100), or 0 if insufficient data
        """
        if not self.predictions:
            return 0.0
            
        correct = sum(1 for p in self.predictions if p['agreed'])
        return (correct / len(self.predictions)) * 100
    
    def get_conflict_rate(self) -> float:
        """Calculate conflict rate.
        
        Returns:
            Conflict rate as percentage (0-100)
        """
        total = len(self.predictions) + len(self.conflicts)
        if total == 0:
            return 0.0
        return (len(self.conflicts) / total) * 100
    
    def should_disable_conflict_detection(self, min_accuracy: float = 50.0, 
                                         min_samples: int = 20) -> bool:
        """Determine if conflict detection should be disabled due to low accuracy.
        
        Args:
            min_accuracy: Minimum accuracy threshold (default: 50%)
            min_samples: Minimum samples required for decision (default: 20)
            
        Returns:
            True if conflict detection should be disabled
        """
        if len(self.predictions) < min_samples:
            return False  # Not enough data yet
            
        accuracy = self.get_accuracy()
        if accuracy < min_accuracy:
            log.warning(
                f"Phase 1 accuracy ({accuracy:.1f}%) below threshold ({min_accuracy:.1f}%). "
                f"Consider disabling conflict detection."
            )
            return True
        return False
    
    def get_stats(self) -> Dict:
        """Get comprehensive Phase 1 statistics.
        
        Returns:
            Dict with accuracy, conflict rate, sample size, etc.
        """
        return {
            'accuracy': self.get_accuracy(),
            'conflict_rate': self.get_conflict_rate(),
            'total_predictions': len(self.predictions),
            'total_conflicts': len(self.conflicts),
            'sample_size': len(self.predictions) + len(self.conflicts)
        }


class Phase1Adapter:
    """Adapts existing system data for Phase 1 analytics."""
    
    def __init__(self):
        self.phase1 = Phase1EnhancedAnalytics()
        self.accuracy_tracker = Phase1AccuracyTracker()
        log.info("Phase1Adapter initialized with accuracy tracking")
    
    def prepare_market_data(self, symbol: str, candle_mgr, orderbook_mgr, 
                           trade_flow, advanced_of) -> Dict:
        """
        Extract and format data from existing system for Phase 1.
        
        Args:
            symbol: Trading symbol
            candle_mgr: CandleManager instance
            orderbook_mgr: OrderBookManager instance
            trade_flow: TradeFlowAnalyzer instance
            advanced_of: AdvancedOrderFlow instance
            
        Returns:
            Dict with formatted data for Phase 1
        """
        try:
            # Get price data - use existing timeframe constants
            from config import TIMEFRAMES
            
            candles_1m = candle_mgr.get_candles(symbol, TIMEFRAMES.get("confirmation", "5m"), limit=30)
            candles_5m = candle_mgr.get_candles(symbol, TIMEFRAMES.get("confirmation", "5m"), limit=30)
            candles_15m = candle_mgr.get_candles(symbol, TIMEFRAMES.get("zones", "30m"), limit=30)
            
            prices = [c.get("close", 0) for c in candles_1m] if candles_1m else []
            
            # Get CVD data - use simple delta calculation
            cvd_1m = self._extract_simple_cvd(trade_flow, symbol, len(prices))
            cvd_5m = self._extract_simple_cvd(trade_flow, symbol, len(prices))
            cvd_15m = self._extract_simple_cvd(trade_flow, symbol, len(prices))
            
            # Get current orderbook
            try:
                orderbook_mgr.update(symbol)
                orderbook_data = orderbook_mgr.get_orderbook(symbol)
            except:
                orderbook_data = {"bids": [], "asks": []}
            
            # Get recent trades
            try:
                recent_trades = list(trade_flow._trades.get(symbol, []))[-20:]
            except:
                recent_trades = []
            
            market_data = {
                "prices": prices,
                "cvd_1m": cvd_1m,
                "cvd_5m": cvd_5m,
                "cvd_15m": cvd_15m,
                "orderbook": orderbook_data,
                "recent_trades": recent_trades
            }
            
            return market_data
            
        except Exception as e:
            log.error(f"Error preparing Phase 1 data for {symbol}: {e}", exc_info=True)
            return {}
    
    def _extract_simple_cvd(self, trade_flow, symbol: str, length: int) -> List[float]:
        """
        Extract simple CVD values using trade flow delta.
        
        Args:
            trade_flow: TradeFlowAnalyzer instance
            symbol: Trading symbol
            length: Number of values to generate
            
        Returns:
            List of CVD values
        """
        if length == 0:
            return []
        
        try:
            # Get current delta from trade flow
            delta_data = trade_flow.get_delta(symbol, window_minutes=5)
            current_delta = delta_data.get("delta", 0)
            
            # Generate simple CVD history (cumulative)
            # For simplicity, create a linear progression
            cvd_values = []
            step = current_delta / length if length > 0 else 0
            
            for i in range(length):
                cvd_values.append(step * (i + 1))
            
            return cvd_values
            
        except Exception as e:
            log.debug(f"Error extracting CVD for {symbol}: {e}")
            # Return zeros if error
            return [0.0] * length
    
    def analyze(self, symbol: str, candle_mgr, orderbook_mgr, 
                trade_flow, advanced_of) -> Optional[Dict]:
        """
        Run Phase 1 analysis on current market data.
        
        Returns:
            Phase 1 analysis result or None if insufficient data
        """
        market_data = self.prepare_market_data(
            symbol, candle_mgr, orderbook_mgr, trade_flow, advanced_of
        )
        
        if not market_data or not market_data.get("prices"):
            log.debug(f"Insufficient data for Phase 1 analysis on {symbol}")
            return None
        
        # Check minimum data requirements
        if len(market_data.get("prices", [])) < 10:
            log.debug(f"Insufficient price data for Phase 1 on {symbol}")
            return None
        
        try:
            result = self.phase1.analyze_for_prediction(symbol, market_data)
            
            if result and result.get("signal") != "NEUTRAL":
                log.info(
                    f"  >> PHASE 1: {result['signal']} {result['quality']} "
                    f"(confidence: {result['confidence']:.0%})"
                )
            
            return result
            
        except Exception as e:
            log.error(f"Phase 1 analysis error for {symbol}: {e}", exc_info=True)
            return None
    
    def get_confidence_boost(self, phase1_result: Dict, existing_direction: str) -> float:
        """
        Calculate confidence boost/penalty from Phase 1.
        
        Args:
            phase1_result: Phase 1 analysis result
            existing_direction: Current signal direction (LONG/SHORT)
            
        Returns:
            Confidence adjustment percentage (-15 to +15)
        """
        if not phase1_result or phase1_result["signal"] == "NEUTRAL":
            return 0.0
        
        # Agreement: boost confidence
        if phase1_result["signal"] == existing_direction:
            boost = phase1_result["confidence"] * 15  # Up to +15%
            log.info(f"  [OK] Phase 1 confirms {existing_direction}: +{boost:.1f}%")
            return boost
        
        # Disagreement: reduce confidence
        else:
            penalty = -phase1_result["confidence"] * 10  # Up to -10%
            log.warning(f"  [WARNING] Phase 1 conflicts with {existing_direction}: {penalty:.1f}%")
            return penalty
