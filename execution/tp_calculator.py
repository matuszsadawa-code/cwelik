"""
Dynamic TP Calculator
Calculates optimal TP allocation based on position size and exchange minimums.
"""

import logging
from typing import Dict, Optional

log = logging.getLogger(__name__)


class DynamicTPCalculator:
    """Calculate TP allocation based on position size and minimums."""
    
    def __init__(self):
        # Default allocation (50/30/20)
        self.default_allocation = {
            "tp1": 0.50,
            "tp2": 0.30,
            "tp3": 0.20,
        }
        
        # Fallback allocations for smaller positions
        self.consolidated_allocation = {
            "tp1": 0.70,
            "tp2": 0.30,
        }
        
        self.single_allocation = {
            "tp1": 1.0,
        }
        
        log.info("DynamicTPCalculator initialized")
    
    def calculate_tp_allocation(self, 
                               total_qty: float,
                               min_qty: float,
                               symbol: str = "") -> Optional[Dict]:
        """Calculate valid TP allocation.
        
        Args:
            total_qty: Total position size
            min_qty: Minimum order size for this symbol
            symbol: Symbol name (for logging)
            
        Returns:
            Valid allocation dict or None if position too small
        """
        log.info(f"Calculating TP allocation for {symbol}: qty={total_qty}, min={min_qty}")
        
        # Try default allocation (50/30/20)
        allocation = self._try_allocation(total_qty, min_qty, self.default_allocation, "default (50/30/20)")
        if allocation:
            return allocation
        
        # Try consolidated allocation (70/30)
        allocation = self._try_allocation(total_qty, min_qty, self.consolidated_allocation, "consolidated (70/30)")
        if allocation:
            return allocation
        
        # Try single TP (100%)
        allocation = self._try_allocation(total_qty, min_qty, self.single_allocation, "single (100%)")
        if allocation:
            return allocation
        
        # Position too small for any TP
        log.warning(f"⚠️ Position too small for TPs: {total_qty} < {min_qty}")
        return None
    
    def _try_allocation(self, total_qty: float, min_qty: float, allocation: Dict, name: str) -> Optional[Dict]:
        """Try a specific allocation and check if all quantities meet minimum.
        
        Args:
            total_qty: Total position size
            min_qty: Minimum order size
            allocation: Allocation to try
            name: Name for logging
            
        Returns:
            Allocation dict if valid, None otherwise
        """
        # Calculate quantities for each TP
        quantities = {
            tp_name: round(total_qty * alloc, 6)
            for tp_name, alloc in allocation.items()
        }
        
        # Check if all meet minimum
        all_valid = all(qty >= min_qty for qty in quantities.values())
        
        if all_valid:
            log.info(f"✅ Using {name} allocation: {quantities}")
            return allocation
        else:
            invalid = [f"{name}={qty:.6f}" for name, qty in quantities.items() if qty < min_qty]
            log.debug(f"❌ {name} allocation invalid: {', '.join(invalid)} < {min_qty}")
            return None
    
    def get_tp_quantities(self, total_qty: float, allocation: Dict) -> Dict:
        """Calculate actual TP quantities from allocation.
        
        Args:
            total_qty: Total position size
            allocation: TP allocation dict
            
        Returns:
            Dict of TP name -> quantity
        """
        return {
            tp_name: round(total_qty * alloc, 6)
            for tp_name, alloc in allocation.items()
        }
