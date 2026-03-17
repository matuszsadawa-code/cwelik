"""
Phase 1 Integration Module
Integrates enhanced CVD and DOM analyzers with the existing trading system.
"""

from typing import Dict, List, Optional
from datetime import datetime

from analytics.cvd_enhanced import EnhancedCVDAnalyzer
from analytics.dom_enhanced import EnhancedDOMAnalyzer
from utils.logger import get_logger

log = get_logger("analytics.phase1_integration")


class Phase1EnhancedAnalytics:
    """Integrates Phase 1 enhancements into the trading system."""
    
    def __init__(self):
        self.cvd_analyzer = EnhancedCVDAnalyzer()
        self.dom_analyzer = EnhancedDOMAnalyzer()
        
        log.info("[OK] Phase 1 Enhanced Analytics initialized")
    
    def analyze_for_prediction(self, symbol: str, market_data: Dict) -> Dict:
        """Comprehensive analysis for 5/15min predictions.
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            market_data: Dict containing:
                - prices: List of recent prices
                - cvd_1m: CVD data on 1-minute timeframe
                - cvd_5m: CVD data on 5-minute timeframe
                - cvd_15m: CVD data on 15-minute timeframe
                - orderbook: Current order book
                - recent_trades: List of recent trades
                
        Returns:
            Dict with comprehensive analysis and final prediction
        """
        log.info(f"[PHASE1] Running Phase 1 analysis for {symbol}")
        
        # 1. Enhanced CVD Analysis
        cvd_analysis = self.cvd_analyzer.analyze_comprehensive(
            prices=market_data.get("prices", []),
            cvd_1m=market_data.get("cvd_1m", []),
            cvd_5m=market_data.get("cvd_5m", []),
            cvd_15m=market_data.get("cvd_15m", [])
        )
        
        # 2. Enhanced DOM Analysis
        dom_analysis = self.dom_analyzer.analyze_comprehensive(
            symbol=symbol,
            orderbook=market_data.get("orderbook", {}),
            recent_trades=market_data.get("recent_trades", [])
        )
        
        # 3. Combine signals with weighted voting
        signals = []
        weights = []
        
        # CVD signal (weight: 0.6)
        if cvd_analysis["confidence"] > 0.6:
            signals.append(cvd_analysis["signal"])
            weights.append(cvd_analysis["confidence"] * 0.6)
        
        # DOM signal (weight: 0.4)
        if dom_analysis["confidence"] > 0.6:
            signals.append(dom_analysis["signal"])
            weights.append(dom_analysis["confidence"] * 0.4)
        
        # 4. Final decision
        if not signals:
            final_signal = "NEUTRAL"
            final_confidence = 0.0
            quality = "SKIP"
        else:
            # Weighted majority vote
            long_weight = sum(w for s, w in zip(signals, weights) if s == "LONG")
            short_weight = sum(w for s, w in zip(signals, weights) if s == "SHORT")
            
            if long_weight > short_weight:
                final_signal = "LONG"
                final_confidence = long_weight / sum(weights) if weights else 0
            elif short_weight > long_weight:
                final_signal = "SHORT"
                final_confidence = short_weight / sum(weights) if weights else 0
            else:
                final_signal = "NEUTRAL"
                final_confidence = 0.5
            
            # Determine quality based on confidence
            if final_confidence >= 0.85:
                quality = "A+"
            elif final_confidence >= 0.75:
                quality = "A"
            elif final_confidence >= 0.65:
                quality = "B"
            else:
                quality = "C"
        
        # 5. Calculate confidence boost from Phase 1
        base_confidence = final_confidence
        
        # Boost if both CVD and DOM agree
        if (cvd_analysis["signal"] == dom_analysis["signal"] and 
            cvd_analysis["signal"] != "NEUTRAL"):
            confidence_boost = 0.10
            final_confidence = min(0.95, final_confidence + confidence_boost)
            log.info(f"[BOOST] Confidence boost: +{confidence_boost:.0%} (CVD + DOM agreement)")
        
        log.info(f"[PHASE1 FINAL] {final_signal} {quality} (confidence: {final_confidence:.2%})")
        
        return {
            "signal": final_signal,
            "confidence": final_confidence,
            "quality": quality,
            "base_confidence": base_confidence,
            "cvd_analysis": cvd_analysis,
            "dom_analysis": dom_analysis,
            "phase": "PHASE_1_ENHANCED",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_confidence_adjustment(self, existing_signal: Dict, market_data: Dict) -> float:
        """Calculate confidence adjustment for existing signals.
        
        Use this to enhance existing signal confidence with Phase 1 analytics.
        
        Args:
            existing_signal: Existing signal from the strategy engine
            market_data: Market data for Phase 1 analysis
            
        Returns:
            Confidence adjustment (positive or negative)
        """
        symbol = existing_signal.get("symbol")
        existing_direction = existing_signal.get("signal_type")  # LONG or SHORT
        
        # Run Phase 1 analysis
        phase1_result = self.analyze_for_prediction(symbol, market_data)
        
        # Check if Phase 1 agrees with existing signal
        if phase1_result["signal"] == existing_direction:
            # Agreement - boost confidence
            adjustment = phase1_result["confidence"] * 0.15  # Up to +15%
            log.info(f"[OK] Phase 1 confirms {existing_direction}: +{adjustment:.1%} confidence")
            return adjustment
        
        elif phase1_result["signal"] == "NEUTRAL":
            # Neutral - no adjustment
            return 0.0
        
        else:
            # Disagreement - reduce confidence
            adjustment = -phase1_result["confidence"] * 0.10  # Up to -10%
            log.warning(f"⚠️ Phase 1 conflicts with {existing_direction}: {adjustment:.1%} confidence")
            return adjustment
