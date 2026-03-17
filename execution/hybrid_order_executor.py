"""
Hybrid Order Executor - Intelligent Order Type Selection
Automatically chooses between MARKET and LIMIT orders based on signal quality and market conditions
"""

import time
from typing import Dict, Any, Optional, Literal
from datetime import datetime
import logging

# Setup logging
logger = logging.getLogger(__name__)


class MarketConditionAnalyzer:
    """Analyze market conditions to determine optimal order type"""
    
    def __init__(self, 
                 min_liquidity_ratio: float = 2.0,
                 high_volatility_threshold: float = 0.02):
        """
        Initialize market condition analyzer
        
        Args:
            min_liquidity_ratio: Minimum orderbook liquidity (as multiple of position size)
            high_volatility_threshold: Threshold for high volatility (2% = 0.02)
        """
        self.min_liquidity_ratio = min_liquidity_ratio
        self.high_volatility_threshold = high_volatility_threshold
    
    def analyze(self, symbol: str, position_size: float, 
                orderbook: Dict, recent_candles: list) -> Dict[str, Any]:
        """
        Analyze current market conditions
        
        Args:
            symbol: Trading pair
            position_size: Intended position size
            orderbook: Current orderbook data
            recent_candles: Recent price candles for volatility calculation
        
        Returns:
            Dictionary with market condition analysis
        """
        # Analyze liquidity
        liquidity = self._analyze_liquidity(orderbook, position_size)
        
        # Analyze volatility
        volatility = self._analyze_volatility(recent_candles)
        
        # Analyze spread
        spread = self._analyze_spread(orderbook)
        
        return {
            'liquidity': liquidity,
            'volatility': volatility,
            'spread': spread,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _analyze_liquidity(self, orderbook: Dict, position_size: float) -> Dict[str, Any]:
        """Analyze orderbook liquidity"""
        try:
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            # Calculate total volume in top 5 levels
            bid_volume = sum(float(bid[1]) for bid in bids[:5])
            ask_volume = sum(float(ask[1]) for ask in asks[:5])
            
            # Calculate liquidity ratio
            relevant_volume = min(bid_volume, ask_volume)
            liquidity_ratio = relevant_volume / position_size if position_size > 0 else 0
            
            # Determine liquidity level
            if liquidity_ratio >= self.min_liquidity_ratio * 2:
                level = 'high'
            elif liquidity_ratio >= self.min_liquidity_ratio:
                level = 'medium'
            else:
                level = 'low'
            
            return {
                'level': level,
                'ratio': round(liquidity_ratio, 2),
                'bid_volume': round(bid_volume, 4),
                'ask_volume': round(ask_volume, 4),
                'sufficient': liquidity_ratio >= self.min_liquidity_ratio
            }
        except Exception as e:
            logger.error(f"Error analyzing liquidity: {e}")
            return {'level': 'unknown', 'ratio': 0, 'sufficient': False}
    
    def _analyze_volatility(self, candles: list) -> Dict[str, Any]:
        """Analyze recent price volatility"""
        try:
            if len(candles) < 20:
                return {'level': 'unknown', 'value': 0}
            
            # Calculate ATR-like volatility
            ranges = []
            for candle in candles[-20:]:
                high = float(candle[2])
                low = float(candle[3])
                ranges.append(high - low)
            
            avg_range = sum(ranges) / len(ranges)
            last_close = float(candles[-1][4])
            volatility = avg_range / last_close if last_close > 0 else 0
            
            # Determine volatility level
            if volatility >= self.high_volatility_threshold:
                level = 'high'
            elif volatility >= self.high_volatility_threshold * 0.5:
                level = 'medium'
            else:
                level = 'low'
            
            return {
                'level': level,
                'value': round(volatility, 4),
                'avg_range': round(avg_range, 2)
            }
        except Exception as e:
            logger.error(f"Error analyzing volatility: {e}")
            return {'level': 'unknown', 'value': 0}
    
    def _analyze_spread(self, orderbook: Dict) -> Dict[str, Any]:
        """Analyze bid-ask spread"""
        try:
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return {'value': 0, 'pct': 0, 'level': 'unknown'}
            
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            
            spread = best_ask - best_bid
            spread_pct = (spread / best_bid) * 100 if best_bid > 0 else 0
            
            # Determine spread level
            if spread_pct < 0.05:  # < 0.05%
                level = 'tight'
            elif spread_pct < 0.1:  # < 0.1%
                level = 'normal'
            else:
                level = 'wide'
            
            return {
                'value': round(spread, 2),
                'pct': round(spread_pct, 4),
                'level': level
            }
        except Exception as e:
            logger.error(f"Error analyzing spread: {e}")
            return {'value': 0, 'pct': 0, 'level': 'unknown'}


class HybridOrderExecutor:
    """
    Intelligent order executor that chooses between MARKET and LIMIT orders
    based on signal quality and market conditions
    """
    
    def __init__(self,
                 max_slippage_pct: float = 0.1,
                 limit_timeout_seconds: int = 30,
                 min_liquidity_ratio: float = 2.0):
        """
        Initialize hybrid order executor
        
        Args:
            max_slippage_pct: Maximum acceptable slippage for market orders (0.1 = 0.1%)
            limit_timeout_seconds: Timeout for limit orders before converting to market
            min_liquidity_ratio: Minimum liquidity ratio for market orders
        """
        self.max_slippage_pct = max_slippage_pct
        self.limit_timeout_seconds = limit_timeout_seconds
        self.market_analyzer = MarketConditionAnalyzer(min_liquidity_ratio=min_liquidity_ratio)
        
        logger.info(f"HybridOrderExecutor initialized: max_slippage={max_slippage_pct}%, "
                   f"limit_timeout={limit_timeout_seconds}s")
    
    def execute_entry(self, signal: Dict[str, Any], 
                     orderbook: Dict, 
                     recent_candles: list,
                     exchange_client: Any) -> Dict[str, Any]:
        """
        Execute entry order using optimal order type
        
        Args:
            signal: Trading signal from signal_validator
            orderbook: Current orderbook data
            recent_candles: Recent price candles
            exchange_client: Exchange client (Bybit/Binance)
        
        Returns:
            Execution result with actual entry price, slippage, etc.
        """
        try:
            # 1. Analyze market conditions
            market_conditions = self.market_analyzer.analyze(
                symbol=signal['symbol'],
                position_size=signal.get('position_size', 0),
                orderbook=orderbook,
                recent_candles=recent_candles
            )
            
            logger.info(f"Market conditions for {signal['symbol']}: "
                       f"liquidity={market_conditions['liquidity']['level']}, "
                       f"volatility={market_conditions['volatility']['level']}")
            
            # 2. Decide order type
            order_type = self._decide_order_type(signal, market_conditions)
            
            logger.info(f"Selected order type: {order_type} for {signal['grade']} signal")
            
            # 3. Execute based on order type
            if order_type == 'MARKET':
                result = self._execute_market_order(signal, orderbook, exchange_client)
            elif order_type == 'LIMIT':
                result = self._execute_limit_order(signal, exchange_client)
            elif order_type == 'LIMIT_WITH_TIMEOUT':
                result = self._execute_limit_with_timeout(signal, orderbook, exchange_client)
            else:
                raise ValueError(f"Unknown order type: {order_type}")
            
            # 4. Add metadata
            result['order_type'] = order_type
            result['market_conditions'] = market_conditions
            result['signal_grade'] = signal['grade']
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing entry: {e}")
            return {
                'success': False,
                'error': str(e),
                'order_type': 'FAILED'
            }
    
    def _decide_order_type(self, signal: Dict, market_conditions: Dict) -> Literal['MARKET', 'LIMIT', 'LIMIT_WITH_TIMEOUT']:
        """
        Decide optimal order type based on signal and market conditions
        
        Decision logic:
        - MARKET: A+ signals + high liquidity + high volatility
        - LIMIT: B/C signals OR low liquidity
        - LIMIT_WITH_TIMEOUT: A signals + good conditions
        """
        grade = signal.get('grade', 'C')
        liquidity = market_conditions['liquidity']
        volatility = market_conditions['volatility']
        
        # A+ signals with good conditions -> MARKET
        if (grade == 'A+' and 
            liquidity['level'] in ['high', 'medium'] and
            liquidity['sufficient'] and
            volatility['level'] in ['high', 'medium']):
            return 'MARKET'
        
        # Low liquidity -> always LIMIT
        if not liquidity['sufficient'] or liquidity['level'] == 'low':
            return 'LIMIT'
        
        # B/C signals -> LIMIT
        if grade in ['B', 'C']:
            return 'LIMIT'
        
        # A signals with good conditions -> LIMIT_WITH_TIMEOUT
        if grade == 'A' and liquidity['sufficient']:
            return 'LIMIT_WITH_TIMEOUT'
        
        # Default: LIMIT (safest)
        return 'LIMIT'
    
    def _execute_market_order(self, signal: Dict, orderbook: Dict, 
                             exchange_client: Any) -> Dict[str, Any]:
        """
        Execute market order with slippage protection
        
        Uses IOC (Immediate or Cancel) order with price limit to protect against slippage
        """
        try:
            symbol = signal['symbol']
            direction = signal['direction']
            position_size = signal.get('position_size', 0)
            expected_price = signal['entry']
            
            # Calculate max acceptable price with slippage protection
            if direction == 'long':
                max_price = expected_price * (1 + self.max_slippage_pct / 100)
                side = 'BUY'
            else:
                max_price = expected_price * (1 - self.max_slippage_pct / 100)
                side = 'SELL'
            
            logger.info(f"Executing MARKET order: {side} {position_size} {symbol} "
                       f"@ max {max_price:.2f} (expected: {expected_price:.2f})")
            
            # Place IOC order with price limit
            # Note: This is a placeholder - actual implementation depends on exchange API
            order = exchange_client.place_order(
                symbol=symbol,
                side=side,
                order_type='MARKET',  # or 'IOC' if supported
                quantity=position_size,
                price_limit=max_price  # Slippage protection
            )
            
            # Verify fill
            if order.get('status') != 'FILLED':
                logger.warning(f"Market order not filled: {order.get('status')}")
                return {
                    'success': False,
                    'reason': 'Order not filled - slippage too high',
                    'order': order
                }
            
            # Calculate actual slippage
            actual_price = float(order.get('avg_fill_price', expected_price))
            slippage = actual_price - expected_price
            slippage_pct = (slippage / expected_price) * 100
            
            # Adjust stop loss for actual entry
            adjusted_sl = self._adjust_stop_loss(
                original_sl=signal['stop_loss'],
                expected_entry=expected_price,
                actual_entry=actual_price,
                direction=direction
            )
            
            logger.info(f"Market order filled: {actual_price:.2f} "
                       f"(slippage: {slippage:+.2f} / {slippage_pct:+.3f}%)")
            
            return {
                'success': True,
                'entry_price': actual_price,
                'expected_price': expected_price,
                'slippage': round(slippage, 2),
                'slippage_pct': round(slippage_pct, 3),
                'stop_loss': adjusted_sl,
                'tp1_price': signal.get('tp1_price'),
                'tp2_price': signal.get('tp2_price'),
                'order': order
            }
            
        except Exception as e:
            logger.error(f"Error executing market order: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _execute_limit_order(self, signal: Dict, exchange_client: Any) -> Dict[str, Any]:
        """Execute limit order at specified price"""
        try:
            symbol = signal['symbol']
            direction = signal['direction']
            position_size = signal.get('position_size', 0)
            limit_price = signal['entry']
            
            side = 'BUY' if direction == 'long' else 'SELL'
            
            logger.info(f"Executing LIMIT order: {side} {position_size} {symbol} @ {limit_price:.2f}")
            
            # Place limit order
            order = exchange_client.place_order(
                symbol=symbol,
                side=side,
                order_type='LIMIT',
                quantity=position_size,
                price=limit_price
            )
            
            return {
                'success': True,
                'entry_price': limit_price,
                'expected_price': limit_price,
                'slippage': 0,
                'slippage_pct': 0,
                'stop_loss': signal['stop_loss'],
                'tp1_price': signal.get('tp1_price'),
                'tp2_price': signal.get('tp2_price'),
                'order': order,
                'note': 'Limit order placed - waiting for fill'
            }
            
        except Exception as e:
            logger.error(f"Error executing limit order: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _execute_limit_with_timeout(self, signal: Dict, orderbook: Dict,
                                   exchange_client: Any) -> Dict[str, Any]:
        """
        Execute limit order with timeout - convert to market if not filled
        
        Strategy:
        1. Place limit order
        2. Wait for timeout
        3. If not filled, cancel and execute market order
        """
        try:
            # Place limit order
            limit_result = self._execute_limit_order(signal, exchange_client)
            
            if not limit_result['success']:
                return limit_result
            
            order_id = limit_result['order'].get('order_id')
            
            logger.info(f"Limit order placed, waiting {self.limit_timeout_seconds}s for fill...")
            
            # Wait for timeout
            start_time = time.time()
            while time.time() - start_time < self.limit_timeout_seconds:
                # Check order status
                order_status = exchange_client.get_order_status(
                    symbol=signal['symbol'],
                    order_id=order_id
                )
                
                if order_status.get('status') == 'FILLED':
                    logger.info("Limit order filled!")
                    return {
                        'success': True,
                        'entry_price': float(order_status.get('avg_fill_price')),
                        'expected_price': signal['entry'],
                        'slippage': 0,
                        'slippage_pct': 0,
                        'stop_loss': signal['stop_loss'],
                        'tp1_price': signal.get('tp1_price'),
                        'tp2_price': signal.get('tp2_price'),
                        'order': order_status,
                        'note': 'Limit order filled within timeout'
                    }
                
                time.sleep(1)  # Check every second
            
            # Timeout reached - cancel limit and execute market
            logger.warning(f"Limit order timeout - converting to market order")
            
            # Cancel limit order
            exchange_client.cancel_order(
                symbol=signal['symbol'],
                order_id=order_id
            )
            
            # Execute market order
            market_result = self._execute_market_order(signal, orderbook, exchange_client)
            market_result['note'] = 'Converted from limit to market after timeout'
            
            return market_result
            
        except Exception as e:
            logger.error(f"Error executing limit with timeout: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _adjust_stop_loss(self, original_sl: float, expected_entry: float,
                         actual_entry: float, direction: str) -> float:
        """
        Adjust stop loss to maintain same risk amount after slippage
        
        If entry is worse due to slippage, adjust SL to keep same $ risk
        """
        try:
            # Calculate original risk
            original_risk = abs(expected_entry - original_sl)
            
            # Calculate new stop loss maintaining same risk
            if direction == 'long':
                adjusted_sl = actual_entry - original_risk
            else:
                adjusted_sl = actual_entry + original_risk
            
            logger.info(f"Adjusted SL: {original_sl:.2f} -> {adjusted_sl:.2f} "
                       f"(entry slippage: {actual_entry - expected_entry:+.2f})")
            
            return round(adjusted_sl, 2)
            
        except Exception as e:
            logger.error(f"Error adjusting stop loss: {e}")
            return original_sl


# Example usage and integration
def example_usage():
    """Example of how to use HybridOrderExecutor with signal_validator"""
    
    # Initialize components
    from skills.signal_validator.scripts.validate_signal import SignalValidator
    from skills.risk_calculator.scripts.position_sizer import PositionSizer
    
    validator = SignalValidator()
    sizer = PositionSizer(account_balance=10000, risk_per_trade=0.01)
    executor = HybridOrderExecutor(
        max_slippage_pct=0.1,  # 0.1% max slippage
        limit_timeout_seconds=30,
        min_liquidity_ratio=2.0
    )
    
    # 1. Validate signal
    signal = validator.validate_setup(
        symbol="BTCUSDT",
        direction="long",
        entry_zone={"low": 67200, "high": 67500}
    )
    
    if not signal['should_execute']:
        print(f"Signal rejected: {signal['rejection_reason']}")
        return
    
    # 2. Calculate position size
    position = sizer.calculate_for_signal_grade(
        entry_price=signal['entry'],
        stop_loss=signal['stop_loss'],
        signal_grade=signal['grade'],
        direction=signal['direction']
    )
    
    # 3. Add position size to signal
    signal['position_size'] = position['size']
    
    # 4. Get market data (placeholder - would fetch from exchange)
    orderbook = {
        'bids': [[67300, 10.5], [67299, 8.2], [67298, 15.3]],
        'asks': [[67301, 9.8], [67302, 12.1], [67303, 7.5]]
    }
    recent_candles = []  # Would fetch recent candles
    
    # 5. Execute with hybrid executor
    # exchange_client = BybitClient()  # Would use actual client
    # result = executor.execute_entry(signal, orderbook, recent_candles, exchange_client)
    
    print(f"Signal: {signal['grade']} ({signal['confirmations_met']}/4)")
    print(f"Position: {position['size']:.4f} BTC")
    print(f"Entry: ${signal['entry']:.2f}")
    print(f"Stop: ${signal['stop_loss']:.2f}")
    print(f"TP1: ${signal.get('tp1_price', 0):.2f}")
    if signal.get('tp2_price'):
        print(f"TP2: ${signal['tp2_price']:.2f}")
    # print(f"Execution: {result['order_type']} - {result.get('note', 'Success')}")


if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    example_usage()
