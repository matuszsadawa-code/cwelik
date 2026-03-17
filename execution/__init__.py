"""OpenClaw Execution Engine — Autonomous order execution on Bybit Futures."""
try:
    from execution.order_executor import OrderExecutor
    from execution.position_manager import PositionManager
    from execution.portfolio import PortfolioManager
    from execution.dynamic_tp_optimizer import DynamicTPOptimizer, DynamicTP
    from execution.adaptive_sl import AdaptiveSLSystem, SLCalculation, AdaptiveStop
except ModuleNotFoundError:
    # Allow individual module imports when trading_system package not available
    pass
