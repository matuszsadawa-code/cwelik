"""
OpenClaw Order Executor — Bybit Futures order placement and management.

Supports two modes:
- DEMO (default): Places orders on Bybit testnet/demo account.
- LIVE: Places real orders via Bybit v5 API (requires API keys).

Order lifecycle: PENDING -> PLACED -> FILLED -> MONITORING -> CLOSED

Features:
- Market & limit order support
- Automatic TP1/TP2/TP3 bracket orders (50%/30%/20% allocation)
- Trailing stop activation after TP1 hit
- Automatic SL placement
- Position leverage configuration
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional, List, Any
from enum import Enum

from config import (
    BYBIT_API_KEY, BYBIT_API_SECRET, BYBIT_DEMO_API_KEY, BYBIT_DEMO_API_SECRET, STRATEGY
)
from utils.logger import get_logger
from data.bybit_client_async import AsyncBybitClient
from execution.tp_calculator import DynamicTPCalculator
from execution.exchange_minimums import ExchangeMinimums

log = get_logger("execution.orders")

BYBIT_REST_URL = "https://api.bybit.com"


class ExecutionMode(Enum):
    PAPER = "paper"  # Pure simulation, no API calls
    DEMO = "demo"    # Bybit testnet
    LIVE = "live"    # Real trading


class OrderStatus(Enum):
    PENDING = "PENDING"
    PLACED = "PLACED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderExecutor:
    """
    Executes trading signals as orders on Bybit Futures.
    
    Default mode is DEMO — orders are placed on Bybit testnet.
    Switch to LIVE mode only when ready for real trading.
    """

    def __init__(self, mode: ExecutionMode = ExecutionMode.PAPER):
        self.mode = mode
        self._recv_window = 5000

        # Initialize async client based on mode
        if self.mode == ExecutionMode.DEMO:
            self.client = AsyncBybitClient(use_demo=True)
        elif self.mode == ExecutionMode.LIVE:
            self.client = AsyncBybitClient(use_demo=False)
        else:
            # Paper mode still needs a client for price lookups sometimes, 
            # but we'll mock its trading calls
            self.client = AsyncBybitClient(use_demo=True) 

        # TP allocation - Single TP only (as per requirements)
        self.tp_allocation = {
            "tp": 1.0,  # Close 100% at single TP
        }

        # Trailing stop config
        self.trailing_stop_pct = 0.5  # 0.5% trailing after TP1
        
        # Pending TP placements (orders waiting for entry fill)
        self.pending_tp_placements = []
        
        # Positions with TP hit - need SL management (BE + trailing)
        self.positions_with_tp_hit = []
        
        # Dynamic TP allocation
        self.tp_calculator = DynamicTPCalculator()
        self.exchange_minimums = ExchangeMinimums(self)

        log.info(f"OrderExecutor initialized — mode: {self.mode.value}")

    # ═══════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════

    async def execute_signal(self, signal: Dict, position_size_qty: float,
                       leverage: int = None) -> Dict:
        """
        Execute a trading signal — the main entry point.

        Args:
            signal: Signal dict from SignalEngine
            position_size_qty: Position size in base asset (e.g., 0.01 BTC)
            leverage: Leverage to use (default from config)

        Returns:
            Execution result dict with order details and status
        """
        symbol = signal["symbol"]
        direction = signal["signal_type"]  # LONG or SHORT
        entry_price = signal["entry_price"]
        sl_price = signal["sl_price"]
        tp1_price = signal.get("tp1_price", signal.get("tp_price"))
        tp2_price = signal.get("tp2_price", signal.get("tp_price"))
        leverage = leverage or STRATEGY.get("default_leverage", 25)

        log.info(f"{'='*50}")
        log.info(f"⚡ EXECUTING: {direction} {symbol}")
        log.info(f"   Mode: {self.mode.value}")
        log.info(f"   Size: {position_size_qty} | Leverage: {leverage}x")
        # Format info with high precision for low-priced assets
        log.info(f"   Entry: ${await self.exchange_minimums.format_price(symbol, entry_price)}")
        
        # Format TP info logging safely if TP2 is missing
        tp_log = f"TP1: ${await self.exchange_minimums.format_price(symbol, tp1_price)}" if tp1_price else "No TP"
        if tp2_price and tp2_price != tp1_price:
            tp_log += f" | TP2: ${await self.exchange_minimums.format_price(symbol, tp2_price)}"
            
        log.info(f"   SL: ${await self.exchange_minimums.format_price(symbol, sl_price)} | {tp_log}")
        log.info(f"{'='*50}")

        import uuid
        execution_id = f"EXEC-{uuid.uuid4().hex[:12].upper()}"
        side = "Buy" if direction == "LONG" else "Sell"
        result = {
            "execution_id": execution_id,
            "signal_id": signal.get("signal_id"),
            "symbol": symbol,
            "side": side,
            "direction": direction,
            "mode": self.mode.value,
            "leverage": leverage,
            "qty": position_size_qty,
            "entry_price": entry_price,
            "sl_price": sl_price,
            "tp1_price": tp1_price,
            "tp2_price": tp2_price,
            "tp_price": tp1_price,  # Backward compatibility
            "status": OrderStatus.PENDING.value,
            "orders": [],
            "created_at": datetime.utcnow().isoformat(),
        }

        try:
            result = await self._execute_live(result)
            log.info(f"[OK] Execution complete: {result['status']}")

        except Exception as e:
            log.error(f"[FAILED] Execution failed: {e}", exc_info=True)
            result["status"] = OrderStatus.REJECTED.value
            result["error"] = str(e)

        return result

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an open order."""
        if self.mode == ExecutionMode.PAPER:
            log.info(f"[PAPER] Cancelled order {order_id}")
            return True

        try:
            resp = await self.client.cancel_order(symbol, order_id)
            return resp.get("orderId") == order_id
        except Exception as e:
            log.error(f"Cancel order failed: {e}")
            return False

    async def close_position(self, symbol: str, side: str, qty: float) -> Dict:
        """Close a position (market order in opposite direction)."""
        close_side = "Sell" if side == "Buy" else "Buy"

        if self.mode == ExecutionMode.PAPER:
            log.info(f"[PAPER] Closed {qty} {symbol} (side: {close_side})")
            return {"status": "FILLED", "mode": "paper"}

        return await self._place_order(
            symbol=symbol,
            side=close_side,
            qty=qty,
            order_type="Market",
            reduce_only=True,
        )

    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for a symbol."""
        if self.mode == ExecutionMode.PAPER:
            log.info(f"[PAPER] Set leverage {symbol}: {leverage}x")
            return True

        try:
            await self.client.set_leverage(symbol, leverage)
            return True
        except Exception as e:
            log.error(f"Set leverage failed: {e}")
            return False

    def get_mode(self) -> str:
        return self.mode.value

    def set_mode(self, mode: str):
        if mode == "live":
            if not BYBIT_API_KEY or not BYBIT_API_SECRET:
                raise ValueError("Cannot switch to LIVE: API keys not configured")
            self.mode = ExecutionMode.LIVE
            self._api_key = BYBIT_API_KEY
            self._api_secret = BYBIT_API_SECRET
            self._rest_url = "https://api.bybit.com"
        elif mode == "demo":
            if not BYBIT_DEMO_API_KEY or not BYBIT_DEMO_API_SECRET:
                raise ValueError("Cannot switch to DEMO: Demo API keys not configured")
            self.mode = ExecutionMode.DEMO
            self._api_key = BYBIT_DEMO_API_KEY
            self._api_secret = BYBIT_DEMO_API_SECRET
            self._rest_url = "https://api-demo.bybit.com"
        else:
            self.mode = ExecutionMode.PAPER
        log.info(f"Execution mode changed to: {self.mode.value}")

    async def _execute_live(self, result: Dict) -> Dict:
        """Execute real orders on Bybit Futures (async)."""
        symbol = result["symbol"]
        side = result["side"]
        qty = result["qty"]
        leverage = result["leverage"]

        # Step 1: Constraint leverage to exchange maximum
        max_allowed_leverage = await self.exchange_minimums.get_max_leverage(symbol)
        if leverage > max_allowed_leverage:
            log.warning(f"[LEVERAGE] Requested leverage {leverage}x exceeds exchange max for {symbol} ({max_allowed_leverage}x). Constraining.")
            leverage = int(max_allowed_leverage)
            result["leverage"] = leverage

        # Step 2: Set leverage (non-fatal if already set)
        leverage_set = await self.set_leverage(symbol, leverage)
        if not leverage_set:
            log.warning(f"Leverage not set for {symbol} (may already be configured)")

        # Step 3: Place LIMIT entry order with ATTACHED stop-loss
        log.info(f"Placing LIMIT entry order at ${await self.exchange_minimums.format_price(symbol, result['entry_price'])} with SL @ ${await self.exchange_minimums.format_price(symbol, result['sl_price'])}...")
        entry_resp = await self._place_order(
            symbol=symbol,
            side=side,
            qty=qty,
            order_type="Limit",
            price=result["entry_price"],
            stop_loss=result["sl_price"],  # Attached SL - activates when order fills
        )

        log.info(f"Order placement response: {entry_resp}")

        # Check if order was placed successfully (orderId present means success)
        if not entry_resp or not entry_resp.get("orderId"):
            # Order failed - entry_resp is either empty or doesn't have orderId
            error_msg = "Entry order placement failed - no orderId returned"
            result["status"] = OrderStatus.REJECTED.value
            result["error"] = error_msg
            log.error(f"Order placement failed: {error_msg}")
            return result

        entry_order_id = entry_resp.get("orderId", "")
        log.info(f"[OK] Entry order placed: {entry_order_id} (LIMIT @ ${await self.exchange_minimums.format_price(symbol, result['entry_price'])}, SL attached)")
        
        result["orders"].append({
            "order_id": entry_order_id,
            "type": "LIMIT_ENTRY_WITH_SL",
            "side": side,
            "qty": qty,
            "price": result["entry_price"],
            "stop_loss": result["sl_price"],
            "status": "PLACED",
        })

        # Step 3: Store order for TP placement monitoring
        close_side = "Sell" if side == "Buy" else "Buy"
        
        # Get exchange minimum for validation
        min_qty = await self.exchange_minimums.get_minimum(symbol)
        
        # PARTIAL TP: Close 50% at TP1, 25% at TP2, keep 25% as moon bag
        tp_allocation = {"tp1": 0.50, "tp2": 0.25}
        
        if qty < min_qty:
            log.warning(f"[WARNING] Position too small for TPs: {qty} < {min_qty} - will require manual TP")
            requires_manual_tp = True
        else:
            requires_manual_tp = False
            log.info(f"[STATS] TP allocation for {symbol}: {tp_allocation} (50% TP1, 25% TP2, 25% moon bag)")
        
        pending_tp = {
            "order_id": entry_order_id,
            "execution_id": result["execution_id"],
            "symbol": symbol,
            "side": close_side,
            "entry_side": side,  # Original entry side (Buy/Sell)
            "direction": result["direction"],  # LONG or SHORT
            "entry_price": result["entry_price"],  # Entry price for BE calculation
            "qty": qty,
            "tp1_price": result.get("tp1_price"),
            "tp2_price": result.get("tp2_price"),
            "tp_allocation": tp_allocation,
            "requires_manual_tp": requires_manual_tp,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        self.pending_tp_placements.append(pending_tp)
        log.info(f"[INFO] Order queued for TP placement after fill (pending: {len(self.pending_tp_placements)})")

        result["status"] = OrderStatus.FILLED.value
        result["filled_at"] = datetime.utcnow().isoformat()
        result["tps_pending"] = True  # Flag indicating TPs will be placed after fill

        return result

    # ═══════════════════════════════════════════════════════════════════
    # BYBIT API HELPERS
    # ═══════════════════════════════════════════════════════════════════

    async def _place_order(self, symbol: str, side: str, qty: float,
                     order_type: str = "Market", price: float = None,
                     reduce_only: bool = False, stop_loss: float = None) -> Dict:
        """Place an order on Bybit v5.
        
        Args:
            symbol: Trading pair
            side: Buy or Sell
            qty: Order quantity
            order_type: Market or Limit
            price: Limit price (required for Limit orders)
            reduce_only: If True, order can only reduce position
            stop_loss: Optional stop loss price to attach to this order
        """
        # Get tick decimals for proper price precision        # Get precision info
        tick_decimals = await self.exchange_minimums.get_tick_decimals(symbol, price=price or stop_loss)
        
        # Round quantity to exchange qty step
        qty = await self.exchange_minimums.round_quantity(symbol, qty)
        
        formatted_price = await self.exchange_minimums.format_price(symbol, price) if price else None
        formatted_qty = await self.exchange_minimums.format_quantity(symbol, qty)
        
        # SL Rounding: Floor for LONG, Ceiling for SHORT
        from decimal import ROUND_FLOOR, ROUND_CEILING
        sl_rounding = ROUND_FLOOR if side == "Buy" else ROUND_CEILING
        formatted_sl = await self.exchange_minimums.format_price(symbol, stop_loss, rounding=sl_rounding) if stop_loss else None

        return await self.client.place_order(
            symbol=symbol,
            side=side,
            qty=formatted_qty,
            order_type=order_type,
            price=formatted_price,
            reduce_only=reduce_only,
            stop_loss=formatted_sl,
        )

    async def _place_stop_order(self, symbol: str, side: str, qty: float,
                          trigger_price: float, order_type: str = "Market") -> Dict:
        """Place a conditional (stop) order."""
        if self.mode == ExecutionMode.PAPER:
            return {"status": "OK", "mode": "paper", "orderId": "paper-stop-" + side}

        formatted_price = await self.exchange_minimums.format_price(symbol, trigger_price)
        formatted_qty = await self.exchange_minimums.format_quantity(symbol, qty)

        return await self.client.place_order(
            symbol=symbol,
            side=side,
            qty=formatted_qty,
            order_type=order_type,
            trigger_price=formatted_price,
            trigger_by="MarkPrice"
        )

    # _signed_request is now handled by the AsyncBybitClient

    async def get_position(self, symbol: str) -> Dict:
        """Get current position for a symbol from Bybit."""
        if self.mode == ExecutionMode.PAPER:
            return {}

        result = await self.client.get_position(symbol)
        if not result:
            return {}
            
        return {
            "symbol": result.get("symbol"),
            "side": result.get("side"),
            "size": float(result.get("size", 0)),
            "entry_price": float(result.get("avgPrice", 0)),
            "mark_price": float(result.get("markPrice", 0)),
            "unrealised_pnl": float(result.get("unrealisedPnl", 0)),
            "leverage": int(result.get("leverage", 1)),
            "liq_price": float(result.get("liqPrice", 0)),
        }

    def _safe_float_convert(self, value) -> float:
        """Safely convert a value to float, treating empty strings as 0.0.
        
        Args:
            value: Value to convert (can be str, int, float, or any type)
            
        Returns:
            float: Converted value, or 0.0 if value is an empty string
        """
        if value == "":
            return 0.0
        return float(value)

    async def get_wallet_balance(self) -> Dict:
        """Get Bybit unified account balance."""
        if self.mode == ExecutionMode.PAPER:
            return {"total_equity": 10000.0, "available": 10000.0, "mode": "paper"}

        result = await self.client.get_wallet_balance()
        if not result or "coin" not in result:
            return {}

        for coin_info in result["coin"]:
            if coin_info.get("coin") == "USDT":
                return {
                    "total_equity": self._safe_float_convert(coin_info.get("equity", 0)),
                    "available": self._safe_float_convert(coin_info.get("availableToWithdraw", 0)),
                    "pnl": self._safe_float_convert(coin_info.get("unrealisedPnl", 0)),
                }
        return {}

    async def get_order_status(self, symbol: str, order_id: str) -> str:
        """Get order status from Bybit.
        
        Returns:
            Order status: "New", "PartiallyFilled", "Filled", "Cancelled", "Rejected", etc.
        """
        if self.mode == ExecutionMode.PAPER:
            return "Filled"  # Simulate immediate fill in paper mode

        try:
            result = await self.client._request("GET", "/v5/order/realtime", {
                "category": "linear",
                "symbol": symbol,
                "orderId": order_id,
            }, auth=True)
            
            orders = result.get("list", [])
            if orders:
                return orders[0].get("orderStatus", "Unknown")
            return "Unknown"
        except Exception as e:
            log.error(f"Failed to get order status for {order_id}: {e}")
            return "Unknown"

    async def check_and_place_tps(self) -> int:
        """Check pending entry orders and place TPs when filled.
        
        Returns:
            Number of TP placements completed
        """
        if not self.pending_tp_placements:
            return 0
        
        placed_count = 0
        
        for pending in list(self.pending_tp_placements):  # Iterate over copy
            order_id = pending["order_id"]
            symbol = pending["symbol"]
            
            # Check if entry order has filled
            status = await self.get_order_status(symbol, order_id)
            
            if status == "Filled":
                log.info(f"[TARGET] Entry order {order_id[:12]}... filled! Placing TPs for {symbol}...")
                
                # Place TP orders and get TP order info
                tp_order_info = await self._place_tp_orders_for_filled_entry(pending)
                
                if tp_order_info:
                    placed_count += 1
                    log.info(f"[OK] TPs placed for {symbol} (execution: {pending['execution_id']})")
                    
                    # Add to positions_with_tp_hit for SL management (BE + trailing)
                    self.positions_with_tp_hit.append(tp_order_info)
                    log.info(f"[TRACKING] Position added for SL management (BE + trailing)")
                else:
                    log.warning(f"[WARNING] TP placement failed for {symbol}")
                
                # Remove from pending list
                self.pending_tp_placements.remove(pending)
            
            elif status in ["Cancelled", "Rejected", "Deactivated"]:
                log.warning(f"[WARNING] Entry order {order_id[:12]}... {status} - removing from pending")
                self.pending_tp_placements.remove(pending)
            elif status in ["New", "Created", "Untriggered", "PartiallyFilled", "Unknown"]:
                # Continue monitoring in next iteration - no automatic cancellation
                pass
        
        return placed_count

    async def check_and_manage_stops(self) -> int:
        """Check positions with TP hit and manage stops (BE + trailing).
        
        Flow:
        1. Check if TP1 order has filled -> Move SL to break-even
        2. Check if TP2 order has filled -> Start trailing stop logic
        """
        if not self.positions_with_tp_hit:
            return 0
        
        updates_count = 0
        
        for pos_info in list(self.positions_with_tp_hit):  # Iterate over copy
            tp1_order_id = pos_info.get("tp1_order_id")
            tp2_order_id = pos_info.get("tp2_order_id")
            symbol = pos_info["symbol"]
            
            # Check TP1 Status
            if tp1_order_id:
                tp1_status = await self.get_order_status(symbol, tp1_order_id)
                if tp1_status == "Filled":
                    if not pos_info["sl_moved_to_be"]:
                        success = await self._move_sl_to_be(pos_info)
                        if success:
                            pos_info["sl_moved_to_be"] = True
                            pos_info["current_sl_price"] = pos_info["entry_price"]
                            updates_count += 1
                            log.info(f"[BE] SL moved to break-even for {symbol} @ ${pos_info['entry_price']:.4f}")
                elif tp1_status in ["Cancelled", "Rejected"]:
                    pos_info["tp1_order_id"] = None
                    
            # Check TP2 Status
            if tp2_order_id:
                tp2_status = await self.get_order_status(symbol, tp2_order_id)
                if tp2_status == "Filled":
                    if not pos_info.get("trailing_active"):
                        pos_info["trailing_active"] = True
                        log.info(f"[TRAILING] TP2 hit for {symbol}, enabling trailing stop.")
                        
                    # Also try updating it immediately
                    success = await self._update_trailing_stop(pos_info)
                    if success:
                        updates_count += 1
                elif tp2_status in ["Cancelled", "Rejected"]:
                    pos_info["tp2_order_id"] = None
                    
            # Check if all targeted TPs are gone and trailing is active
            if not pos_info.get("tp1_order_id") and not pos_info.get("tp2_order_id") and not pos_info.get("trailing_active"):
                self.positions_with_tp_hit.remove(pos_info)
        
        return updates_count

    async def _move_sl_to_be(self, pos_info: Dict) -> bool:
        """Move stop loss to break-even for remaining position.
        
        Args:
            pos_info: Position tracking info
            
        Returns:
            True if SL was successfully moved to BE
        """
        symbol = pos_info["symbol"]
        entry_price = pos_info["entry_price"]
        remaining_qty = pos_info["remaining_qty"]
        side = pos_info["side"]  # Close side (Sell for LONG, Buy for SHORT)
        
        try:
            # Place new SL at break-even price
            sl_resp = await self._place_order(
                symbol=symbol,
                side=side,
                qty=remaining_qty,
                order_type="Limit",
                price=entry_price,
                reduce_only=True,
            )
            
            if sl_resp and sl_resp.get("orderId"):
                log.info(f"  [OK] BE SL placed: {remaining_qty:.6f} @ ${entry_price:.4f} (orderId: {sl_resp['orderId'][:12]}...)")
                return True
            else:
                log.warning(f"  [WARNING] BE SL placement failed - API response: {sl_resp}")
                return False
                
        except Exception as e:
            log.error(f"  [FAILED] BE SL placement error: {e}")
            return False

    async def _update_trailing_stop(self, pos_info: Dict) -> bool:
        """Update trailing stop for remaining position.
        
        Args:
            pos_info: Position tracking info
            
        Returns:
            True if trailing stop was updated
        """
        symbol = pos_info["symbol"]
        direction = pos_info["direction"]
        current_sl_price = pos_info["current_sl_price"]
        remaining_qty = pos_info["remaining_qty"]
        side = pos_info["side"]
        
        # Get current price
        try:
            position = await self.get_position(symbol)
            if not position or position.get("size", 0) == 0:
                log.info(f"[TRAILING] Position closed for {symbol} - removing from tracking")
                self.positions_with_tp_hit.remove(pos_info)
                return False
            
            current_price = position.get("mark_price", 0)
            if current_price == 0:
                return False
            
        except Exception as e:
            log.error(f"[TRAILING] Error getting position for {symbol}: {e}")
            return False
        
        # Calculate new trailing stop level
        trailing_pct = self.trailing_stop_pct / 100  # 0.5% default
        
        if direction == "LONG":
            # For LONG: trail below current price, only move up
            new_sl_price = current_price * (1 - trailing_pct)
            
            # Only update if new SL is higher than current SL (favorable)
            if new_sl_price > current_sl_price:
                try:
                    # Place new trailing SL
                    sl_resp = await self._place_order(
                        symbol=symbol,
                        side=side,
                        qty=remaining_qty,
                        order_type="Limit",
                        price=new_sl_price,
                        reduce_only=True,
                    )
                    
                    if sl_resp and sl_resp.get("orderId"):
                        log.info(f"  [TRAILING] SL updated: ${current_sl_price:.4f} → ${new_sl_price:.4f} (price: ${current_price:.4f})")
                        pos_info["current_sl_price"] = new_sl_price
                        return True
                        
                except Exception as e:
                    log.error(f"  [FAILED] Trailing SL update error: {e}")
                    return False
        
        else:  # SHORT
            # For SHORT: trail above current price, only move down
            new_sl_price = current_price * (1 + trailing_pct)
            
            # Only update if new SL is lower than current SL (favorable)
            if new_sl_price < current_sl_price:
                try:
                    sl_resp = await self._place_order(
                        symbol=symbol,
                        side=side,
                        qty=remaining_qty,
                        order_type="Limit",
                        price=new_sl_price,
                        reduce_only=True,
                    )
                    
                    if sl_resp and sl_resp.get("orderId"):
                        log.info(f"  [TRAILING] SL updated: ${current_sl_price:.4f} → ${new_sl_price:.4f} (price: ${current_price:.4f})")
                        pos_info["current_sl_price"] = new_sl_price
                        return True
                        
                except Exception as e:
                    log.error(f"  [FAILED] Trailing SL update error: {e}")
                    return False
        
        return False

    async def _place_tp_orders_for_filled_entry(self, pending: Dict) -> Optional[Dict]:
        """Place TP orders for a filled entry order.
        
        Args:
            pending: Dict with order details (symbol, side, qty, tp prices, allocation)
            
        Returns:
            Dict with tracking info for SL management (BE + trailing), or None if failed
        """
        symbol = pending["symbol"]
        side = pending["side"]  # This is the close side (opposite of entry)
        qty = pending["qty"]
        entry_price = pending["entry_price"]
        direction = pending["direction"]
        
        # Check if manual TP is required
        if pending.get("requires_manual_tp", False):
            log.warning(f"[WARNING] {symbol} requires manual TP placement (position too small)")
            return None
        
        # Get the calculated allocation
        tp_allocation = pending.get("tp_allocation")
        if not tp_allocation:
            log.error(f"[FAILED] No TP allocation found for {symbol}")
            return None
        
        # Get exchange requirements
        min_qty = await self.exchange_minimums.get_minimum(symbol)
        
        tp_order_ids = {}
        tp_qty_placed = 0
        
        # Place TPs according to calculated allocation (should be {"tp1": 0.50, "tp2": 0.25})
        for tp_name, alloc in tp_allocation.items():
            # Calculate raw quantity
            tp_qty_raw = qty * alloc
            
            # Round to exchange qty step
            tp_qty = await self.exchange_minimums.round_quantity(symbol, tp_qty_raw)
            tp_price = pending.get(f"{tp_name}_price")
            
            # Validate quantity and price
            if not tp_price:
                continue
                
            if tp_qty < min_qty:
                log.warning(f"  [WARNING] {tp_name.upper()}: qty {tp_qty} < minimum {min_qty} - skipping")
                continue
            
            try:
                tp_resp = await self._place_order(
                    symbol=symbol,
                    side=side,
                    qty=tp_qty,
                    order_type="Limit",
                    price=tp_price,
                    reduce_only=True,
                )
                
                if tp_resp and tp_resp.get("orderId"):
                    res_order_id = tp_resp["orderId"]
                    tp_order_ids[tp_name] = res_order_id
                    tp_qty_placed = float(tp_qty_placed) + float(tp_qty)
                    log.info(f"  [OK] {tp_name.upper()}: {tp_qty} @ ${tp_price:.2f} (orderId: {res_order_id[:12]}...)")
                else:
                    log.warning(f"  [WARNING] {tp_name.upper()} failed - API response: {tp_resp}")
            except Exception as e:
                log.error(f"  [FAILED] {tp_name.upper()} error: {e}")
        
        # If any TPs were placed successfully, return tracking info
        if tp_order_ids:
            remaining_qty = float(qty) - float(tp_qty_placed)
            log.info(f"  [INFO] Remaining {remaining_qty:.6f} as moon bag")
            
            tracking_info = {
                "tp1_order_id": tp_order_ids.get("tp1"),
                "tp2_order_id": tp_order_ids.get("tp2"),
                "symbol": symbol,
                "entry_price": entry_price,
                "direction": direction,
                "side": side,  # Close side for remaining position
                "remaining_qty": remaining_qty,
                "original_qty": qty,
                "tp_qty": tp_qty_placed,
                "sl_moved_to_be": False,
                "trailing_active": False,
                "current_sl_price": None,
                "execution_id": pending["execution_id"],
                "created_at": datetime.utcnow().isoformat(),
            }
            
            return tracking_info
        else:
            log.warning(f"  [WARNING] No TP orders placed for {symbol}")
            return None
