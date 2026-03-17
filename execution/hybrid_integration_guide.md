# Hybrid Order Executor - Integration Guide

## 📋 Przegląd

Hybrid Order Executor automatycznie wybiera optymalny typ zlecenia (MARKET vs LIMIT) na podstawie:
- Jakości sygnału (A+, A, B, C)
- Warunków rynkowych (płynność, zmienność)
- Wielkości pozycji
- Konfiguracji użytkownika

## 🎯 Logika Decyzyjna

```
A+ Signal + High Liquidity + High Volatility → MARKET ORDER
A+ Signal + Medium Liquidity → LIMIT WITH TIMEOUT (30s)
A Signal + Good Conditions → LIMIT WITH TIMEOUT
B/C Signals → LIMIT ORDER
Low Liquidity (zawsze) → LIMIT ORDER
```

## 🔧 Instalacja i Konfiguracja

### 1. Import Modułów

```python
from trading_system.execution.hybrid_order_executor import (
    HybridOrderExecutor,
    MarketConditionAnalyzer
)
from trading_system.execution import hybrid_config as config
```

### 2. Inicjalizacja

```python
# Podstawowa konfiguracja
executor = HybridOrderExecutor(
    max_slippage_pct=0.1,  # 0.1% max slippage
    limit_timeout_seconds=30,
    min_liquidity_ratio=2.0
)

# Zaawansowana konfiguracja (per-symbol)
def get_executor_for_symbol(symbol):
    settings = config.SYMBOL_SETTINGS.get(
        symbol, 
        config.SYMBOL_SETTINGS['default_altcoin']
    )
    
    return HybridOrderExecutor(
        max_slippage_pct=settings['max_slippage_pct'],
        limit_timeout_seconds=settings['limit_timeout'],
        min_liquidity_ratio=settings['min_liquidity_ratio']
    )
```

## 📊 Kompletny Workflow

### Przykład 1: Podstawowe Użycie

```python
from skills.signal_validator.scripts.validate_signal import SignalValidator
from skills.risk_calculator.scripts.position_sizer import PositionSizer
from skills.risk_calculator.scripts.drawdown_monitor import DrawdownMonitor
from trading_system.execution.hybrid_order_executor import HybridOrderExecutor
from trading_system.data.bybit_client import BybitClient

# 1. Inicjalizacja
validator = SignalValidator()
sizer = PositionSizer(account_balance=10000, risk_per_trade=0.01)
executor = HybridOrderExecutor(max_slippage_pct=0.1)
dd_monitor = DrawdownMonitor(account_balance=10000, daily_limit=0.02)
client = BybitClient()

# 2. Walidacja sygnału
signal = validator.validate_setup(
    symbol="BTCUSDT",
    direction="long",
    entry_zone={"low": 67200, "high": 67500}
)

if not signal['should_execute']:
    print(f"❌ Signal rejected: {signal['rejection_reason']}")
    exit()

print(f"✅ Signal validated: {signal['grade']} ({signal['confirmations_met']}/4)")

# 3. Oblicz wielkość pozycji
position = sizer.calculate_for_signal_grade(
    entry_price=signal['entry'],
    stop_loss=signal['stop_loss'],
    signal_grade=signal['grade'],
    direction=signal['direction']
)

print(f"📊 Position size: {position['size']:.4f} BTC (${position['position_value']:.2f})")
print(f"💰 Risk: ${position['risk_amount']:.2f} ({position['max_loss_pct']:.2%})")

# 4. Sprawdź drawdown limits
can_trade = dd_monitor.can_take_trade(position['risk_amount'])
if not can_trade['allowed']:
    print(f"⚠️ Trade blocked: {can_trade['reason']}")
    exit()

# 5. Pobierz dane rynkowe
orderbook = client.get_orderbook("BTCUSDT", limit=20)
recent_candles = client.get_klines("BTCUSDT", "1h", limit=50)

# 6. Dodaj position size do sygnału
signal['position_size'] = position['size']

# 7. Wykonaj zlecenie z hybrid executor
result = executor.execute_entry(
    signal=signal,
    orderbook=orderbook,
    recent_candles=recent_candles,
    exchange_client=client
)

# 8. Sprawdź wynik
if result['success']:
    print(f"✅ Order executed: {result['order_type']}")
    print(f"   Entry: ${result['entry_price']:.2f}")
    print(f"   Slippage: {result['slippage']:+.2f} ({result['slippage_pct']:+.3f}%)")
    print(f"   Stop Loss: ${result['stop_loss']:.2f}")
    print(f"   Take Profit: ${result['take_profit']:.2f}")
    
    # 9. Zapisz trade do bazy
    # save_trade_to_database(result)
else:
    print(f"❌ Order failed: {result.get('error', 'Unknown error')}")
```

### Przykład 2: Automatyczny Trading Loop

```python
import time
from datetime import datetime

def trading_loop():
    """Automatyczny loop tradingowy z hybrid executor"""
    
    # Inicjalizacja
    validator = SignalValidator()
    sizer = PositionSizer(account_balance=10000, risk_per_trade=0.01)
    executor = HybridOrderExecutor(max_slippage_pct=0.1)
    dd_monitor = DrawdownMonitor(account_balance=10000, daily_limit=0.02)
    client = BybitClient()
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    print("🚀 Starting trading loop...")
    
    while True:
        try:
            # Sprawdź każdy symbol
            for symbol in symbols:
                # 1. Znajdź potencjalne entry zones
                zones = validator.find_entry_zones(symbol, "long")
                
                if not zones:
                    continue
                
                # 2. Waliduj najlepszą strefę
                best_zone = zones[0]
                signal = validator.validate_setup(
                    symbol=symbol,
                    direction="long",
                    entry_zone=best_zone
                )
                
                # 3. Tylko A+ i A sygnały
                if not signal['should_execute'] or signal['grade'] not in ['A+', 'A']:
                    continue
                
                print(f"\n🎯 {symbol}: {signal['grade']} signal detected!")
                
                # 4. Oblicz position size
                position = sizer.calculate_for_signal_grade(
                    entry_price=signal['entry'],
                    stop_loss=signal['stop_loss'],
                    signal_grade=signal['grade'],
                    direction=signal['direction']
                )
                
                # 5. Sprawdź drawdown
                if not dd_monitor.can_take_trade(position['risk_amount'])['allowed']:
                    print("⚠️ Drawdown limit - skipping")
                    continue
                
                # 6. Wykonaj zlecenie
                orderbook = client.get_orderbook(symbol, limit=20)
                recent_candles = client.get_klines(symbol, "1h", limit=50)
                signal['position_size'] = position['size']
                
                result = executor.execute_entry(
                    signal=signal,
                    orderbook=orderbook,
                    recent_candles=recent_candles,
                    exchange_client=client
                )
                
                if result['success']:
                    print(f"✅ {result['order_type']} executed @ ${result['entry_price']:.2f}")
                    
                    # Zapisz do bazy i powiadom użytkownika
                    # save_trade(result)
                    # notify_user(f"Trade opened: {symbol} {signal['direction']}")
                else:
                    print(f"❌ Execution failed: {result.get('error')}")
            
            # Czekaj przed następnym skanem
            print(f"\n⏳ Next scan in 60s... ({datetime.now().strftime('%H:%M:%S')})")
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\n🛑 Trading loop stopped by user")
            break
        except Exception as e:
            print(f"❌ Error in trading loop: {e}")
            time.sleep(60)

if __name__ == '__main__':
    trading_loop()
```

### Przykład 3: Backtesting z Hybrid Executor

```python
def backtest_hybrid_executor(historical_signals):
    """Backtest hybrid executor na historycznych sygnałach"""
    
    executor = HybridOrderExecutor(max_slippage_pct=0.1)
    
    results = {
        'total_trades': 0,
        'market_orders': 0,
        'limit_orders': 0,
        'limit_with_timeout': 0,
        'total_slippage': 0,
        'total_fees': 0
    }
    
    for signal in historical_signals:
        # Symuluj market conditions
        market_conditions = {
            'liquidity': {'level': 'high', 'sufficient': True},
            'volatility': {'level': 'medium'},
            'spread': {'level': 'tight'}
        }
        
        # Decyzja o typie zlecenia
        order_type = executor._decide_order_type(signal, market_conditions)
        
        # Symuluj slippage
        if order_type == 'MARKET':
            slippage = signal['entry'] * 0.0005  # 0.05% avg slippage
            fee = signal['entry'] * signal['position_size'] * 0.0006  # Taker fee
        else:
            slippage = 0
            fee = signal['entry'] * signal['position_size'] * -0.0001  # Maker rebate
        
        # Aktualizuj statystyki
        results['total_trades'] += 1
        results[f"{order_type.lower()}_orders"] += 1
        results['total_slippage'] += slippage
        results['total_fees'] += fee
    
    # Podsumowanie
    print(f"\n📊 Backtest Results:")
    print(f"Total trades: {results['total_trades']}")
    print(f"Market orders: {results['market_orders']} ({results['market_orders']/results['total_trades']*100:.1f}%)")
    print(f"Limit orders: {results['limit_orders']} ({results['limit_orders']/results['total_trades']*100:.1f}%)")
    print(f"Limit w/ timeout: {results['limit_with_timeout']} ({results['limit_with_timeout']/results['total_trades']*100:.1f}%)")
    print(f"Total slippage: ${results['total_slippage']:.2f}")
    print(f"Total fees: ${results['total_fees']:.2f}")
    print(f"Net cost: ${results['total_slippage'] + results['total_fees']:.2f}")
    
    return results
```

## ⚙️ Konfiguracja

### Dostosowanie Parametrów

```python
# Per-symbol configuration
executor = HybridOrderExecutor(
    max_slippage_pct=0.1,  # BTC: 0.1%, Altcoins: 0.2%
    limit_timeout_seconds=30,  # A+: 15s, A: 30s, B: 60s
    min_liquidity_ratio=2.0  # Large positions: 3.0, Small: 1.5
)

# Dynamic configuration based on signal
def get_executor_config(signal):
    if signal['grade'] == 'A+':
        return {
            'max_slippage_pct': 0.15,  # More aggressive
            'limit_timeout_seconds': 15,  # Faster
            'min_liquidity_ratio': 2.0
        }
    elif signal['grade'] == 'A':
        return {
            'max_slippage_pct': 0.1,
            'limit_timeout_seconds': 30,
            'min_liquidity_ratio': 2.0
        }
    else:  # B/C
        return {
            'max_slippage_pct': 0.05,  # Conservative
            'limit_timeout_seconds': 60,
            'min_liquidity_ratio': 3.0
        }
```

## 📈 Monitoring i Logging

```python
import logging

# Setup detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hybrid_executor.log'),
        logging.StreamHandler()
    ]
)

# Executor automatycznie loguje:
# - Market condition analysis
# - Order type decision reasoning
# - Execution details
# - Slippage and fees
# - Errors and warnings
```

## 🎯 Best Practices

### 1. Zawsze Sprawdzaj Drawdown
```python
if not dd_monitor.can_take_trade(risk_amount)['allowed']:
    # STOP - nie wykonuj zlecenia
    return
```

### 2. Używaj Symbol-Specific Settings
```python
# BTC/ETH: aggressive
# Altcoins: conservative
executor = get_executor_for_symbol(symbol)
```

### 3. Monitoruj Slippage
```python
if result['slippage_pct'] > 0.2:  # > 0.2%
    alert("High slippage detected!")
```

### 4. Track Order Type Distribution
```python
# Idealna dystrybucja:
# A+ signals: 60% MARKET, 40% LIMIT_WITH_TIMEOUT
# A signals: 20% MARKET, 80% LIMIT_WITH_TIMEOUT
# B signals: 100% LIMIT
```

### 5. Adjust Based on Performance
```python
# Jeśli market orders mają gorsze wyniki:
# - Zwiększ min_liquidity_ratio
# - Zmniejsz max_slippage_pct
# - Użyj więcej LIMIT_WITH_TIMEOUT
```

## 🔍 Troubleshooting

### Problem: Zbyt wiele market orders
**Rozwiązanie:** Zwiększ `min_liquidity_ratio` lub zmniejsz `max_slippage_pct`

### Problem: Przegapione wejścia (limit orders nie wypełnione)
**Rozwiązanie:** Zmniejsz `limit_timeout_seconds` lub użyj więcej market orders dla A+ signals

### Problem: Wysoki slippage
**Rozwiązanie:** Zmniejsz `max_slippage_pct` lub użyj IOC orders z price limits

### Problem: Wysokie fees
**Rozwiązanie:** Użyj więcej limit orders (maker rebate) zamiast market orders

## 📊 Oczekiwane Wyniki

**Optymalna dystrybucja order types:**
- A+ signals: 50-70% MARKET
- A signals: 20-40% MARKET, 60-80% LIMIT_WITH_TIMEOUT
- B signals: 100% LIMIT

**Oczekiwany slippage:**
- MARKET orders: 0.03-0.08% avg
- LIMIT orders: 0%
- LIMIT_WITH_TIMEOUT: 0-0.05% avg (jeśli timeout)

**Oczekiwane fees:**
- MARKET: +0.06% (taker)
- LIMIT: -0.01% (maker rebate)
- Net: ~0.02-0.04% per trade

## 🚀 Deployment

### Production Checklist
- [ ] Skonfiguruj symbol-specific settings
- [ ] Ustaw odpowiednie slippage limits
- [ ] Włącz logging
- [ ] Testuj na paper trading
- [ ] Monitoruj pierwsze 10 trades
- [ ] Dostosuj parametry based on performance
- [ ] Setup alerts dla high slippage
- [ ] Backup plan jeśli executor fails

---

**Gotowe do użycia!** Hybrid Order Executor jest w pełni zintegrowany z Twoim trading system i gotowy do produkcji. 🎉
