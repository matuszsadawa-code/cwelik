"""
Market Profile (TPO - Time Price Opportunity) Module

Builds TPO charts and analyzes market structure through:
- Value Area (VAH/VAL) - 70% of volume
- Point of Control (POC) - highest volume price
- Poor Highs/Lows - single prints as price targets
- Profile shapes - NORMAL, P_SHAPE, B_SHAPE, DOUBLE_DISTRIBUTION
- Trading signals based on price position relative to value area

Market Profile helps identify fair value zones and potential price targets.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict

from analytics.performance_cache import get_cache, CACHE_TTL


@dataclass
class ValueArea:
    """Value Area calculation result"""
    vah: float  # Value Area High
    val: float  # Value Area Low
    poc: float  # Point of Control
    value_area_volume_pct: float  # Should be ~70%


@dataclass
class PoorExtreme:
    """Poor High or Poor Low (single print)"""
    price: float
    extreme_type: str  # POOR_HIGH, POOR_LOW
    tpo_count: int  # Should be 1 for true poor extreme
    distance_from_current: float  # Distance in %


@dataclass
class MarketProfile:
    """Complete Market Profile for a session"""
    date: datetime
    poc: float  # Point of Control
    vah: float  # Value Area High
    val: float  # Value Area Low
    tpo_distribution: Dict[float, int]  # Price -> TPO count
    profile_shape: str  # NORMAL, P_SHAPE, B_SHAPE, DOUBLE_DISTRIBUTION
    poor_highs: List[float]
    poor_lows: List[float]
    volume_distribution: Dict[float, float]  # Price -> Volume
    session_high: float
    session_low: float
    session_range: float


@dataclass
class TPOSignal:
    """Trading signal based on Market Profile"""
    signal_type: str  # BELOW_VALUE, ABOVE_VALUE, AT_POC, NEUTRAL
    confidence: float  # 0-100
    target_price: Optional[float]  # Poor high/low target
    description: str
    poc_distance_pct: float  # Distance from POC in %
    value_area_position: str  # BELOW, INSIDE, ABOVE


class MarketProfileAnalyzer:
    """
    Market Profile (TPO) implementation.
    
    Builds TPO charts from 30-minute periods and analyzes market structure
    to identify value areas, control points, and trading opportunities.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Market Profile analyzer.
        
        Args:
            config: Optional configuration overrides
        """
        self.config = config or {
            "period_minutes": 30,  # TPO period
            "value_area_pct": 70,  # 70% of volume for value area
            "poc_confidence_boost": 12,  # Boost when price at POC
            "poor_extreme_min_distance": 5,  # Min ticks for poor high/low
            "profile_lookback_days": 5,  # Days of profiles to maintain
            "tick_size": 0.01,  # Price tick size for bucketing
        }
        self.profiles: Dict[str, List[MarketProfile]] = {}
    
    def build_profile(self, candles: List[Dict], period_minutes: int = None,
                     symbol: str = "UNKNOWN") -> Optional[MarketProfile]:
        """
        Build TPO chart from candles.
        
        Uses caching to avoid expensive recalculation for same candle data.
        Cache TTL: 30 minutes (configurable via CACHE_TTL)
        
        Args:
            candles: OHLCV data
            period_minutes: TPO period (default from config)
            symbol: Trading symbol for history tracking
            
        Returns:
            MarketProfile with VAH, VAL, POC
        """
        if not candles or len(candles) < 10:
            return None
        
        period_minutes = period_minutes or self.config["period_minutes"]
        
        # Create cache key from candle timestamps (deterministic)
        cache = get_cache()
        candle_timestamps = tuple(c.get('timestamp', 0) for c in candles[:10])  # First 10 for key
        cached_profile = cache.get("market_profile", symbol, period_minutes, candle_timestamps)
        
        if cached_profile is not None:
            return cached_profile
        
        # Build TPO distribution (price -> count of periods)
        tpo_distribution = defaultdict(int)
        volume_distribution = defaultdict(float)
        
        # Group candles into periods
        periods = self._group_into_periods(candles, period_minutes)
        
        if not periods:
            return None
        
        # For each period, mark all prices touched
        for period_candles in periods:
            if not period_candles:
                continue
            
            # Get price range for this period
            period_high = max(c.get('high', 0) for c in period_candles)
            period_low = min(c.get('low', 0) for c in period_candles)
            period_volume = sum(c.get('volume', 0) for c in period_candles)
            
            # Mark all price levels touched in this period
            price_levels = self._get_price_levels(period_low, period_high)
            
            for price in price_levels:
                tpo_distribution[price] += 1
                # Distribute volume across touched prices
                volume_distribution[price] += period_volume / len(price_levels)
        
        if not tpo_distribution:
            return None
        
        # Calculate Value Area (70% of volume)
        value_area = self.calculate_value_area(tpo_distribution, volume_distribution)
        
        # Identify POC (highest volume price)
        poc = self.identify_poc(volume_distribution)
        
        # Detect poor highs/lows (single prints)
        session_high = max(tpo_distribution.keys())
        session_low = min(tpo_distribution.keys())
        poor_extremes = self.detect_poor_highs_lows(tpo_distribution, session_high, session_low)
        
        poor_highs = [p.price for p in poor_extremes if p.extreme_type == "POOR_HIGH"]
        poor_lows = [p.price for p in poor_extremes if p.extreme_type == "POOR_LOW"]
        
        # Classify profile shape
        profile_shape = self.classify_profile_shape(tpo_distribution, poc, value_area)
        
        # Create profile
        profile = MarketProfile(
            date=datetime.utcnow(),
            poc=poc,
            vah=value_area.vah,
            val=value_area.val,
            tpo_distribution=dict(tpo_distribution),
            profile_shape=profile_shape,
            poor_highs=poor_highs,
            poor_lows=poor_lows,
            volume_distribution=dict(volume_distribution),
            session_high=session_high,
            session_low=session_low,
            session_range=session_high - session_low
        )
        
        # Cache the result
        cache.set("market_profile", profile, CACHE_TTL["market_profile"],
                 symbol, period_minutes, candle_timestamps)
        
        # Store in history
        if symbol not in self.profiles:
            self.profiles[symbol] = []
        self.profiles[symbol].append(profile)
        
        # Keep only recent profiles
        max_profiles = self.config["profile_lookback_days"]
        self.profiles[symbol] = self.profiles[symbol][-max_profiles:]
        
        return profile
    
    def calculate_value_area(self, tpo_distribution: Dict[float, int],
                            volume_distribution: Dict[float, float]) -> ValueArea:
        """
        Calculate Value Area (70% of volume).
        
        Algorithm:
        1. Start at POC (highest volume)
        2. Expand up and down, adding price level with more volume
        3. Stop when 70% of total volume is included
        
        Args:
            tpo_distribution: Price -> TPO count
            volume_distribution: Price -> Volume
            
        Returns:
            ValueArea with VAH, VAL, POC
        """
        if not volume_distribution:
            return ValueArea(vah=0, val=0, poc=0, value_area_volume_pct=0)
        
        # Find POC (highest volume price)
        poc = max(volume_distribution.items(), key=lambda x: x[1])[0]
        
        # Calculate total volume
        total_volume = sum(volume_distribution.values())
        target_volume = total_volume * (self.config["value_area_pct"] / 100)
        
        # Sort prices
        sorted_prices = sorted(volume_distribution.keys())
        poc_idx = sorted_prices.index(poc)
        
        # Expand from POC
        value_area_prices = {poc}
        current_volume = volume_distribution[poc]
        
        upper_idx = poc_idx + 1
        lower_idx = poc_idx - 1
        
        while current_volume < target_volume:
            # Check if we can expand
            can_expand_up = upper_idx < len(sorted_prices)
            can_expand_down = lower_idx >= 0
            
            if not can_expand_up and not can_expand_down:
                break
            
            # Get volumes for next expansion
            upper_volume = volume_distribution[sorted_prices[upper_idx]] if can_expand_up else 0
            lower_volume = volume_distribution[sorted_prices[lower_idx]] if can_expand_down else 0
            
            # Expand to side with more volume
            if can_expand_up and (not can_expand_down or upper_volume >= lower_volume):
                value_area_prices.add(sorted_prices[upper_idx])
                current_volume += upper_volume
                upper_idx += 1
            elif can_expand_down:
                value_area_prices.add(sorted_prices[lower_idx])
                current_volume += lower_volume
                lower_idx -= 1
        
        # Calculate VAH and VAL
        vah = max(value_area_prices)
        val = min(value_area_prices)
        value_area_volume_pct = (current_volume / total_volume) * 100
        
        return ValueArea(
            vah=vah,
            val=val,
            poc=poc,
            value_area_volume_pct=value_area_volume_pct
        )
    
    def identify_poc(self, volume_distribution: Dict[float, float]) -> float:
        """
        Identify Point of Control (highest volume price).
        
        Args:
            volume_distribution: Price -> Volume
            
        Returns:
            POC price
        """
        if not volume_distribution:
            return 0.0
        
        return max(volume_distribution.items(), key=lambda x: x[1])[0]
    
    def detect_poor_highs_lows(self, tpo_distribution: Dict[float, int],
                               session_high: float, session_low: float) -> List[PoorExtreme]:
        """
        Detect single prints (poor highs/lows) as price targets.
        
        Poor High: Single TPO at/near session high
        Poor Low: Single TPO at/near session low
        
        Args:
            tpo_distribution: Price -> TPO count
            session_high: Session high price
            session_low: Session low price
            
        Returns:
            List of PoorExtreme objects
        """
        poor_extremes = []
        
        if not tpo_distribution:
            return poor_extremes
        
        sorted_prices = sorted(tpo_distribution.keys())
        
        # Check for poor high (single TPO near session high)
        high_region = [p for p in sorted_prices if p >= session_high * 0.995]  # Top 0.5%
        
        for price in high_region:
            tpo_count = tpo_distribution[price]
            if tpo_count == 1:  # Single print
                poor_extremes.append(PoorExtreme(
                    price=price,
                    extreme_type="POOR_HIGH",
                    tpo_count=tpo_count,
                    distance_from_current=0  # Will be calculated when generating signal
                ))
        
        # Check for poor low (single TPO near session low)
        low_region = [p for p in sorted_prices if p <= session_low * 1.005]  # Bottom 0.5%
        
        for price in low_region:
            tpo_count = tpo_distribution[price]
            if tpo_count == 1:  # Single print
                poor_extremes.append(PoorExtreme(
                    price=price,
                    extreme_type="POOR_LOW",
                    tpo_count=tpo_count,
                    distance_from_current=0
                ))
        
        return poor_extremes
    
    def classify_profile_shape(self, tpo_distribution: Dict[float, int],
                               poc: float, value_area: ValueArea) -> str:
        """
        Classify profile: NORMAL, P_SHAPE, B_SHAPE, DOUBLE_DISTRIBUTION.
        
        - NORMAL: Bell curve, POC in middle
        - P_SHAPE: POC at top (distribution)
        - B_SHAPE: POC at bottom (accumulation)
        - DOUBLE_DISTRIBUTION: Two POCs (bimodal)
        
        Args:
            tpo_distribution: Price -> TPO count
            poc: Point of Control
            value_area: Value Area
            
        Returns:
            Profile shape string
        """
        if not tpo_distribution:
            return "UNKNOWN"
        
        sorted_prices = sorted(tpo_distribution.keys())
        
        if len(sorted_prices) < 5:
            return "UNKNOWN"
        
        # Calculate POC position in range
        price_range = sorted_prices[-1] - sorted_prices[0]
        if price_range == 0:
            return "UNKNOWN"
        
        poc_position = (poc - sorted_prices[0]) / price_range
        
        # Check for double distribution (two peaks)
        peaks = self._find_peaks(tpo_distribution, sorted_prices)
        
        if len(peaks) >= 2:
            # Check if peaks are significant and separated
            peak_values = [tpo_distribution[p] for p in peaks[:2]]
            if min(peak_values) >= max(peak_values) * 0.7:  # Both peaks significant
                return "DOUBLE_DISTRIBUTION"
        
        # Classify based on POC position
        if poc_position > 0.7:
            return "P_SHAPE"  # POC at top (distribution)
        elif poc_position < 0.3:
            return "B_SHAPE"  # POC at bottom (accumulation)
        else:
            return "NORMAL"  # POC in middle (balanced)
    
    def generate_signal(self, current_price: float, profile: MarketProfile) -> TPOSignal:
        """
        Generate trading signal based on price position relative to value area.
        
        Args:
            current_price: Current market price
            profile: Market Profile
            
        Returns:
            TPOSignal with trading recommendation
        """
        if not profile:
            return TPOSignal(
                signal_type="NEUTRAL",
                confidence=0,
                target_price=None,
                description="No profile data",
                poc_distance_pct=0,
                value_area_position="UNKNOWN"
            )
        
        # Calculate position relative to value area
        if current_price < profile.val:
            value_area_position = "BELOW"
            signal_type = "BELOW_VALUE"
            base_confidence = 60
            description = f"Price below value area (${profile.val:.2f}) - potential long opportunity"
            
            # Find nearest poor low as target
            target_price = None
            if profile.poor_lows:
                # Target is to fill the poor low (return to it)
                nearest_poor_low = min(profile.poor_lows, key=lambda p: abs(p - current_price))
                if nearest_poor_low < current_price:
                    target_price = nearest_poor_low
                    description += f" with target at poor low ${target_price:.2f}"
        
        elif current_price > profile.vah:
            value_area_position = "ABOVE"
            signal_type = "ABOVE_VALUE"
            base_confidence = 60
            description = f"Price above value area (${profile.vah:.2f}) - potential short opportunity"
            
            # Find nearest poor high as target
            target_price = None
            if profile.poor_highs:
                # Target is to fill the poor high (return to it)
                nearest_poor_high = min(profile.poor_highs, key=lambda p: abs(p - current_price))
                if nearest_poor_high > current_price:
                    target_price = nearest_poor_high
                    description += f" with target at poor high ${target_price:.2f}"
        
        else:
            value_area_position = "INSIDE"
            signal_type = "NEUTRAL"
            base_confidence = 50
            description = f"Price inside value area (${profile.val:.2f}-${profile.vah:.2f}) - neutral"
            target_price = None
        
        # Calculate distance from POC
        poc_distance_pct = abs(current_price - profile.poc) / profile.poc * 100
        
        # Check if at POC (within 0.5%)
        if poc_distance_pct < 0.5:
            signal_type = "AT_POC"
            base_confidence = 80
            description = f"Price at POC (${profile.poc:.2f}) - high probability reversal zone"
        
        # Adjust confidence based on profile shape
        if profile.profile_shape == "P_SHAPE" and signal_type == "ABOVE_VALUE":
            base_confidence += 10  # Distribution pattern, bearish
        elif profile.profile_shape == "B_SHAPE" and signal_type == "BELOW_VALUE":
            base_confidence += 10  # Accumulation pattern, bullish
        
        return TPOSignal(
            signal_type=signal_type,
            confidence=min(100, base_confidence),
            target_price=target_price,
            description=description,
            poc_distance_pct=poc_distance_pct,
            value_area_position=value_area_position
        )
    
    def _group_into_periods(self, candles: List[Dict], period_minutes: int) -> List[List[Dict]]:
        """
        Group candles into TPO periods.
        
        Args:
            candles: OHLCV data
            period_minutes: Period length in minutes
            
        Returns:
            List of candle groups (one per period)
        """
        if not candles:
            return []
        
        # Assume candles are 5-minute candles (most common for this system)
        candles_per_period = period_minutes // 5
        
        if candles_per_period < 1:
            candles_per_period = 1
        
        periods = []
        for i in range(0, len(candles), candles_per_period):
            period = candles[i:i + candles_per_period]
            if period:
                periods.append(period)
        
        return periods
    
    def _get_price_levels(self, low: float, high: float) -> List[float]:
        """
        Get all price levels between low and high using tick size.
        
        Args:
            low: Low price
            high: High price
            
        Returns:
            List of price levels
        """
        if low >= high:
            return [low]
        
        tick_size = self.config["tick_size"]
        
        # Round to tick size
        low_rounded = round(low / tick_size) * tick_size
        high_rounded = round(high / tick_size) * tick_size
        
        levels = []
        current = low_rounded
        
        # Limit to reasonable number of levels
        max_levels = 1000
        count = 0
        
        while current <= high_rounded and count < max_levels:
            levels.append(round(current, 2))
            current += tick_size
            count += 1
        
        return levels if levels else [low]
    
    def _find_peaks(self, tpo_distribution: Dict[float, int],
                   sorted_prices: List[float]) -> List[float]:
        """
        Find peaks (local maxima) in TPO distribution.
        
        Args:
            tpo_distribution: Price -> TPO count
            sorted_prices: Sorted list of prices
            
        Returns:
            List of peak prices
        """
        if len(sorted_prices) < 3:
            return []
        
        peaks = []
        
        for i in range(1, len(sorted_prices) - 1):
            current = sorted_prices[i]
            prev = sorted_prices[i - 1]
            next_price = sorted_prices[i + 1]
            
            current_tpo = tpo_distribution[current]
            prev_tpo = tpo_distribution[prev]
            next_tpo = tpo_distribution[next_price]
            
            # Peak if higher than neighbors
            if current_tpo > prev_tpo and current_tpo > next_tpo:
                peaks.append(current)
        
        # Sort peaks by TPO count (highest first)
        peaks.sort(key=lambda p: tpo_distribution[p], reverse=True)
        
        return peaks
    
    def get_previous_profile(self, symbol: str) -> Optional[MarketProfile]:
        """
        Get the most recent profile for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Most recent MarketProfile or None
        """
        if symbol not in self.profiles or not self.profiles[symbol]:
            return None
        
        return self.profiles[symbol][-1]
    
    def get_poc_confidence_boost(self, current_price: float, profile: MarketProfile) -> float:
        """
        Calculate confidence boost when price is at POC.
        
        Args:
            current_price: Current market price
            profile: Market Profile
            
        Returns:
            Confidence boost (0 or configured boost value)
        """
        if not profile:
            return 0
        
        # Check if price is within 0.5% of POC
        poc_distance_pct = abs(current_price - profile.poc) / profile.poc * 100
        
        if poc_distance_pct < 0.5:
            return self.config["poc_confidence_boost"]
        
        return 0
