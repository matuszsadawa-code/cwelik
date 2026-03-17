#!/usr/bin/env python3
"""
Real-time System Monitor
Monitoruje działanie systemu tradingowego w czasie rzeczywistym
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).parent))

from storage.database import Database
from config import DATABASE_PATH

def monitor_signals():
    """Monitoruje sygnały w czasie rzeczywistym"""
    db = Database()
    
    print("\n" + "=" * 80)
    print(f"OPENCLAW v3.0 - REAL-TIME MONITOR | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Recent signals
    print("\n📊 RECENT SIGNALS (Last 24h)")
    print("-" * 80)
    try:
        signals = db.get_recent_signals(limit=10)
        if signals:
            for sig in signals:
                timestamp = sig.get('timestamp', 'N/A')
                symbol = sig.get('symbol', 'N/A')
                direction = sig.get('direction', 'N/A')
                quality = sig.get('quality', 'N/A')
                confidence = sig.get('confidence', 0)
                entry = sig.get('entry_price', 0)
                print(f"  {timestamp} | {symbol:12} | {direction:5} | Quality: {quality:2} | "
                      f"Confidence: {confidence:.1f}% | Entry: ${entry:.4f}")
        else:
            print("  No signals in last 24 hours")
    except Exception as e:
        print(f"  Error fetching signals: {e}")
    
    # Performance stats
    print("\n📈 PERFORMANCE STATS (Last 30 days)")
    print("-" * 80)
    try:
        db2 = Database()  # New connection for stats
        stats = db2.get_performance_stats(days=30)
        if stats:
            print(f"  Total Signals: {stats.get('total_signals', 0)}")
            print(f"  Win Rate: {stats.get('win_rate', 0):.1f}%")
            print(f"  Avg R:R: {stats.get('avg_rr', 0):.2f}")
            print(f"  Total PnL: ${stats.get('total_pnl', 0):.2f}")
            print(f"  Profit Factor: {stats.get('profit_factor', 0):.2f}")
        else:
            print("  No performance data available")
    except Exception as e:
        print(f"  Error fetching stats: {e}")
    
    # Signal quality distribution
    print("\n🎯 SIGNAL QUALITY DISTRIBUTION")
    print("-" * 80)
    try:
        db3 = Database()  # New connection for signal stats
        signal_stats = db3.get_signal_stats()
        if signal_stats:
            print(f"  A+ Signals: {signal_stats.get('a_plus', 0)}")
            print(f"  A Signals: {signal_stats.get('a', 0)}")
            print(f"  B Signals: {signal_stats.get('b', 0)}")
            print(f"  C Signals: {signal_stats.get('c', 0)}")
            print(f"  Total: {signal_stats.get('total', 0)}")
    except Exception as e:
        print(f"  Error fetching signal stats: {e}")
    
    # Open positions
    print("\n💼 OPEN POSITIONS")
    print("-" * 80)
    try:
        db4 = Database()  # New connection for open signals
        open_signals = db4.get_open_signals()
        if open_signals:
            for sig in open_signals:
                symbol = sig.get('symbol', 'N/A')
                direction = sig.get('direction', 'N/A')
                entry = sig.get('entry_price', 0)
                sl = sig.get('sl_price', 0)
                tp = sig.get('tp_price', 0)
                print(f"  {symbol:12} | {direction:5} | Entry: ${entry:.4f} | "
                      f"SL: ${sl:.4f} | TP: ${tp:.4f}")
        else:
            print("  No open positions")
    except Exception as e:
        print(f"  Error fetching open positions: {e}")
    
    print("\n" + "=" * 80)

def continuous_monitor(interval=30):
    """Ciągłe monitorowanie z odświeżaniem"""
    try:
        while True:
            monitor_signals()
            print(f"\n⏱️  Refreshing in {interval} seconds... (Ctrl+C to stop)")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\n✓ Monitor stopped")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='OpenClaw System Monitor')
    parser.add_argument('--continuous', '-c', action='store_true', 
                       help='Continuous monitoring mode')
    parser.add_argument('--interval', '-i', type=int, default=30,
                       help='Refresh interval in seconds (default: 30)')
    
    args = parser.parse_args()
    
    if args.continuous:
        continuous_monitor(args.interval)
    else:
        monitor_signals()
