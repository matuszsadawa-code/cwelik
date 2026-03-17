"""
Seasonality and Cyclical Pattern Detection

Implements detection of recurring time-based patterns:
- Day-of-week effect analysis (365-day lookback)
- Time-of-day pattern analysis (Asian, London, NY sessions)
- Monthly pattern analysis (end-of-month flows)
- Cycle detection using FFT (Fast Fourier Transform)
- Seasonal bias generation (>65% accuracy threshold)

Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7, 18.8
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import statistics
import numpy as np

try:
    from utils.logger import get_logger
    log = get_logger("analytics.seasonality")
except ImportError:
    # Fallback for standalone testing
    import logging
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("analytics.seasonality")


@dataclass
class DayOfWeekPattern:
    """Day-of-week pattern analysis."""
    performance_by_day: Dict[str, float]  # day -> avg return %
    best_day: str
    worst_day: str
    pattern_strength: float  # 0-100
    sample_counts: Dict[str, int]  # day -> number of samples


@dataclass
class TimeOfDayPattern:
    """Time-of-day pattern analysis."""
    performance_by_session: Dict[str, float]  # session -> avg return %
    best_session: str
    worst_session: str
    pattern_strength: float  # 0-100
    sample_counts: Dict[str, int]  # session -> number of samples


@dataclass
class MonthlyPattern:
    """Monthly pattern analysis."""
    performance_by_month: Dict[int, float]  # month -> avg return %
    performance_by_week: Dict[int, float]  # week of month -> avg return %
    pattern_strength: float  # 0-100
    sample_counts: Dict[str, int]  # period -> number of samples


@dataclass
class CyclicalPattern:
    """Cyclical pattern detected via FFT."""
    period_days: float
    amplitude: float
    phase: float
    strength: float  # 0-100
    next_peak: datetime
    next_trough: datetime


@dataclass
class SeasonalBias:
    """Seasonal bias signal."""
    bias: str  # BULLISH, BEARISH
    pattern_type: str  # DAY_OF_WEEK, TIME_OF_DAY, MONTHLY, CYCLICAL
    accuracy: float  # Historical accuracy %
    confidence_boost: float
    description: str


@dataclass
class SeasonalPatterns:
    """Complete seasonal analysis."""
    day_of_week: Optional[DayOfWeekPattern]
    time_of_day: Optional[TimeOfDayPattern]
    monthly: Optional[MonthlyPattern]
    cycles: List[CyclicalPattern]


class SeasonalityDetector:
    """Detect seasonality and cyclical patterns in market behavior."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize detector with configuration."""
        self.config = config or {}
        
        # Configuration parameters
        self.min_lookback_days = self.config.get("min_lookback_days", 365)
        self.pattern_accuracy_threshold = self.config.get("pattern_accuracy_threshold", 65)
        self.confidence_boost = self.config.get("confidence_boost", 8)
        self.fft_min_period_days = self.config.get("fft_min_period_days", 7)
        self.fft_max_period_days = self.config.get("fft_max_period_days", 90)
        
        # Trading sessions (UTC times)
        self.sessions = {
            "ASIAN": (0, 8),    # 00:00-08:00 UTC
            "LONDON": (8, 16),  # 08:00-16:00 UTC
            "NY": (13, 21),     # 13:00-21:00 UTC (overlaps with London)
        }
        
        # Pattern cache
        self.patterns: Dict[str, SeasonalPatterns] = {}
        
        log.info(
            f"SeasonalityDetector initialized "
            f"(min_lookback={self.min_lookback_days} days, "
            f"accuracy_threshold={self.pattern_accuracy_threshold}%)"
        )

    
    def analyze_day_of_week_effect(self, symbol: str, candles: List[Dict], 
                                   lookback_days: int = 365) -> Optional[DayOfWeekPattern]:
        """
        Analyze day-of-week patterns.
        
        Example: Monday dip, Friday rally
        
        Args:
            symbol: Trading symbol
            candles: Historical candle data (daily)
            lookback_days: Days to analyze (default 365)
            
        Returns:
            DayOfWeekPattern with performance by day
            
        Validates: Requirement 18.2
        """
        if len(candles) < lookback_days:
            log.debug(f"Insufficient data for day-of-week analysis: {len(candles)} < {lookback_days}")
            return None
        
        # Use most recent data
        recent_candles = candles[-lookback_days:]
        
        # Group returns by day of week
        day_returns: Dict[str, List[float]] = {
            "Monday": [], "Tuesday": [], "Wednesday": [], 
            "Thursday": [], "Friday": [], "Saturday": [], "Sunday": []
        }
        
        for candle in recent_candles:
            # Get timestamp
            timestamp = candle.get("time", 0)
            if timestamp == 0:
                continue
            
            # Convert to datetime
            if timestamp > 1e12:  # Milliseconds
                dt = datetime.utcfromtimestamp(timestamp / 1000)
            else:  # Seconds
                dt = datetime.utcfromtimestamp(timestamp)
            
            # Get day name
            day_name = dt.strftime("%A")
            
            # Calculate return
            open_price = candle.get("open", 0)
            close_price = candle.get("close", 0)
            
            if open_price > 0:
                return_pct = ((close_price - open_price) / open_price) * 100
                day_returns[day_name].append(return_pct)
        
        # Calculate average returns by day
        performance_by_day = {}
        sample_counts = {}
        
        for day, returns in day_returns.items():
            if returns:
                performance_by_day[day] = statistics.mean(returns)
                sample_counts[day] = len(returns)
            else:
                performance_by_day[day] = 0.0
                sample_counts[day] = 0
        
        # Find best and worst days
        if not performance_by_day:
            return None
        
        best_day = max(performance_by_day, key=performance_by_day.get)
        worst_day = min(performance_by_day, key=performance_by_day.get)
        
        # Calculate pattern strength (0-100)
        # Based on consistency and magnitude of differences
        returns_list = [r for r in performance_by_day.values() if r != 0]
        if not returns_list:
            pattern_strength = 0.0
        else:
            # Range of returns
            return_range = max(returns_list) - min(returns_list)
            # Standard deviation (lower = more consistent)
            std_dev = statistics.stdev(returns_list) if len(returns_list) > 1 else 0
            
            # Strength based on range and consistency
            range_score = min(100, return_range * 10)  # Normalize
            consistency_score = max(0, 100 - std_dev * 20)  # Lower std = higher score
            
            pattern_strength = (range_score * 0.6 + consistency_score * 0.4)
        
        pattern = DayOfWeekPattern(
            performance_by_day=performance_by_day,
            best_day=best_day,
            worst_day=worst_day,
            pattern_strength=pattern_strength,
            sample_counts=sample_counts
        )
        
        log.info(
            f"[DAY-OF-WEEK] {symbol}: Best={best_day} ({performance_by_day[best_day]:+.2f}%), "
            f"Worst={worst_day} ({performance_by_day[worst_day]:+.2f}%), "
            f"Strength={pattern_strength:.0f}/100"
        )
        
        return pattern

    
    def analyze_time_of_day_patterns(self, symbol: str, candles: List[Dict]) -> Optional[TimeOfDayPattern]:
        """
        Analyze time-of-day patterns.
        
        Sessions:
        - Asian (00:00-08:00 UTC)
        - London (08:00-16:00 UTC)
        - New York (13:00-21:00 UTC)
        
        Args:
            symbol: Trading symbol
            candles: Historical candle data (intraday, e.g., 1H or 4H)
            
        Returns:
            TimeOfDayPattern with performance by session
            
        Validates: Requirement 18.3
        """
        if len(candles) < 100:  # Need sufficient intraday data
            log.debug(f"Insufficient data for time-of-day analysis: {len(candles)}")
            return None
        
        # Group returns by session
        session_returns: Dict[str, List[float]] = {
            "ASIAN": [], "LONDON": [], "NY": []
        }
        
        for candle in candles:
            # Get timestamp
            timestamp = candle.get("time", 0)
            if timestamp == 0:
                continue
            
            # Convert to datetime
            if timestamp > 1e12:  # Milliseconds
                dt = datetime.utcfromtimestamp(timestamp / 1000)
            else:  # Seconds
                dt = datetime.utcfromtimestamp(timestamp)
            
            # Get hour (UTC)
            hour = dt.hour
            
            # Determine session
            session = None
            for session_name, (start_hour, end_hour) in self.sessions.items():
                if start_hour <= hour < end_hour:
                    session = session_name
                    break
            
            if not session:
                continue
            
            # Calculate return
            open_price = candle.get("open", 0)
            close_price = candle.get("close", 0)
            
            if open_price > 0:
                return_pct = ((close_price - open_price) / open_price) * 100
                session_returns[session].append(return_pct)
        
        # Calculate average returns by session
        performance_by_session = {}
        sample_counts = {}
        
        for session, returns in session_returns.items():
            if returns:
                performance_by_session[session] = statistics.mean(returns)
                sample_counts[session] = len(returns)
            else:
                performance_by_session[session] = 0.0
                sample_counts[session] = 0
        
        # Find best and worst sessions
        if not performance_by_session:
            return None
        
        best_session = max(performance_by_session, key=performance_by_session.get)
        worst_session = min(performance_by_session, key=performance_by_session.get)
        
        # Calculate pattern strength
        returns_list = [r for r in performance_by_session.values() if r != 0]
        if not returns_list:
            pattern_strength = 0.0
        else:
            return_range = max(returns_list) - min(returns_list)
            std_dev = statistics.stdev(returns_list) if len(returns_list) > 1 else 0
            
            range_score = min(100, return_range * 10)
            consistency_score = max(0, 100 - std_dev * 20)
            
            pattern_strength = (range_score * 0.6 + consistency_score * 0.4)
        
        pattern = TimeOfDayPattern(
            performance_by_session=performance_by_session,
            best_session=best_session,
            worst_session=worst_session,
            pattern_strength=pattern_strength,
            sample_counts=sample_counts
        )
        
        log.info(
            f"[TIME-OF-DAY] {symbol}: Best={best_session} ({performance_by_session[best_session]:+.2f}%), "
            f"Worst={worst_session} ({performance_by_session[worst_session]:+.2f}%), "
            f"Strength={pattern_strength:.0f}/100"
        )
        
        return pattern

    
    def analyze_monthly_patterns(self, symbol: str, candles: List[Dict]) -> Optional[MonthlyPattern]:
        """
        Analyze monthly patterns.
        
        Example: End-of-month flows, options expiry effects
        
        Args:
            symbol: Trading symbol
            candles: Historical candle data (daily)
            
        Returns:
            MonthlyPattern with performance by month/week
            
        Validates: Requirement 18.4
        """
        if len(candles) < 365:  # Need at least 1 year
            log.debug(f"Insufficient data for monthly analysis: {len(candles)}")
            return None
        
        # Group returns by month and week of month
        month_returns: Dict[int, List[float]] = {i: [] for i in range(1, 13)}
        week_returns: Dict[int, List[float]] = {i: [] for i in range(1, 6)}  # 1-5 weeks
        
        for candle in candles:
            # Get timestamp
            timestamp = candle.get("time", 0)
            if timestamp == 0:
                continue
            
            # Convert to datetime
            if timestamp > 1e12:  # Milliseconds
                dt = datetime.utcfromtimestamp(timestamp / 1000)
            else:  # Seconds
                dt = datetime.utcfromtimestamp(timestamp)
            
            # Get month (1-12)
            month = dt.month
            
            # Get week of month (1-5)
            day_of_month = dt.day
            week_of_month = min(5, (day_of_month - 1) // 7 + 1)
            
            # Calculate return
            open_price = candle.get("open", 0)
            close_price = candle.get("close", 0)
            
            if open_price > 0:
                return_pct = ((close_price - open_price) / open_price) * 100
                month_returns[month].append(return_pct)
                week_returns[week_of_month].append(return_pct)
        
        # Calculate average returns
        performance_by_month = {}
        performance_by_week = {}
        sample_counts = {}
        
        for month, returns in month_returns.items():
            if returns:
                performance_by_month[month] = statistics.mean(returns)
                sample_counts[f"month_{month}"] = len(returns)
            else:
                performance_by_month[month] = 0.0
                sample_counts[f"month_{month}"] = 0
        
        for week, returns in week_returns.items():
            if returns:
                performance_by_week[week] = statistics.mean(returns)
                sample_counts[f"week_{week}"] = len(returns)
            else:
                performance_by_week[week] = 0.0
                sample_counts[f"week_{week}"] = 0
        
        # Calculate pattern strength
        all_returns = list(performance_by_month.values()) + list(performance_by_week.values())
        returns_list = [r for r in all_returns if r != 0]
        
        if not returns_list:
            pattern_strength = 0.0
        else:
            return_range = max(returns_list) - min(returns_list)
            std_dev = statistics.stdev(returns_list) if len(returns_list) > 1 else 0
            
            range_score = min(100, return_range * 10)
            consistency_score = max(0, 100 - std_dev * 20)
            
            pattern_strength = (range_score * 0.6 + consistency_score * 0.4)
        
        pattern = MonthlyPattern(
            performance_by_month=performance_by_month,
            performance_by_week=performance_by_week,
            pattern_strength=pattern_strength,
            sample_counts=sample_counts
        )
        
        # Find best/worst months and weeks
        best_month = max(performance_by_month, key=performance_by_month.get)
        worst_month = min(performance_by_month, key=performance_by_month.get)
        best_week = max(performance_by_week, key=performance_by_week.get)
        
        log.info(
            f"[MONTHLY] {symbol}: Best month={best_month} ({performance_by_month[best_month]:+.2f}%), "
            f"Worst month={worst_month} ({performance_by_month[worst_month]:+.2f}%), "
            f"Best week={best_week} ({performance_by_week[best_week]:+.2f}%), "
            f"Strength={pattern_strength:.0f}/100"
        )
        
        return pattern

    
    def detect_cycles(self, candles: List[Dict]) -> List[CyclicalPattern]:
        """
        Detect cyclical patterns using FFT (Fast Fourier Transform).
        
        Args:
            candles: Historical candle data
            
        Returns:
            List of detected cycles with periods and strengths
            
        Validates: Requirement 18.7
        """
        if len(candles) < 100:  # Need sufficient data for FFT
            log.debug(f"Insufficient data for cycle detection: {len(candles)}")
            return []
        
        # Extract close prices
        prices = [candle.get("close", 0) for candle in candles]
        prices = [p for p in prices if p > 0]
        
        if len(prices) < 100:
            return []
        
        # Detrend the data (remove linear trend)
        x = np.arange(len(prices))
        coeffs = np.polyfit(x, prices, 1)
        trend = np.polyval(coeffs, x)
        detrended = np.array(prices) - trend
        
        # Apply FFT
        fft_result = np.fft.fft(detrended)
        frequencies = np.fft.fftfreq(len(detrended))
        
        # Get power spectrum (magnitude)
        power = np.abs(fft_result) ** 2
        
        # Only consider positive frequencies
        positive_freq_idx = frequencies > 0
        frequencies = frequencies[positive_freq_idx]
        power = power[positive_freq_idx]
        
        # Convert frequencies to periods (in days)
        periods = 1 / frequencies
        
        # Filter periods within our range
        valid_idx = (periods >= self.fft_min_period_days) & (periods <= self.fft_max_period_days)
        periods = periods[valid_idx]
        power = power[valid_idx]
        
        if len(periods) == 0:
            return []
        
        # Find top cycles by power
        top_n = 5
        top_indices = np.argsort(power)[-top_n:][::-1]
        
        cycles = []
        now = datetime.utcnow()
        
        for idx in top_indices:
            period = periods[idx]
            amplitude = np.sqrt(power[idx])
            
            # Calculate strength (0-100) based on relative power
            max_power = np.max(power)
            strength = (power[idx] / max_power * 100) if max_power > 0 else 0
            
            # Only include significant cycles
            if strength < 20:
                continue
            
            # Estimate phase (simplified)
            phase = np.angle(fft_result[positive_freq_idx][valid_idx][idx])
            
            # Estimate next peak and trough
            # This is a simplified calculation
            days_into_cycle = (len(candles) % period)
            days_to_peak = (period / 4 - days_into_cycle) % period
            days_to_trough = (3 * period / 4 - days_into_cycle) % period
            
            next_peak = now + timedelta(days=float(days_to_peak))
            next_trough = now + timedelta(days=float(days_to_trough))
            
            cycle = CyclicalPattern(
                period_days=float(period),
                amplitude=float(amplitude),
                phase=float(phase),
                strength=float(strength),
                next_peak=next_peak,
                next_trough=next_trough
            )
            cycles.append(cycle)
        
        if cycles:
            log.info(
                f"[CYCLES] Detected {len(cycles)} cyclical patterns: "
                f"{', '.join([f'{c.period_days:.1f}d (strength {c.strength:.0f})' for c in cycles])}"
            )
        
        return cycles

    
    def generate_seasonal_bias(self, symbol: str, current_time: datetime,
                              patterns: SeasonalPatterns) -> Optional[SeasonalBias]:
        """
        Generate seasonal bias signal if strong pattern exists.
        
        Criteria:
        - Pattern accuracy >65%
        - Minimum 1 year of data
        
        Args:
            symbol: Trading symbol
            current_time: Current datetime
            patterns: Seasonal patterns for the symbol
            
        Returns:
            SeasonalBias if pattern is strong
            
        Validates: Requirements 18.5, 18.6
        """
        if not patterns:
            return None
        
        biases = []
        
        # Check day-of-week pattern
        if patterns.day_of_week and patterns.day_of_week.pattern_strength >= self.pattern_accuracy_threshold:
            day_name = current_time.strftime("%A")
            day_performance = patterns.day_of_week.performance_by_day.get(day_name, 0)
            
            if abs(day_performance) > 0.1:  # Significant bias
                bias = "BULLISH" if day_performance > 0 else "BEARISH"
                biases.append(SeasonalBias(
                    bias=bias,
                    pattern_type="DAY_OF_WEEK",
                    accuracy=patterns.day_of_week.pattern_strength,
                    confidence_boost=self.confidence_boost,
                    description=f"{day_name} typically {bias.lower()} ({day_performance:+.2f}%)"
                ))
        
        # Check time-of-day pattern
        if patterns.time_of_day and patterns.time_of_day.pattern_strength >= self.pattern_accuracy_threshold:
            hour = current_time.hour
            
            # Determine current session
            current_session = None
            for session_name, (start_hour, end_hour) in self.sessions.items():
                if start_hour <= hour < end_hour:
                    current_session = session_name
                    break
            
            if current_session:
                session_performance = patterns.time_of_day.performance_by_session.get(current_session, 0)
                
                if abs(session_performance) > 0.1:
                    bias = "BULLISH" if session_performance > 0 else "BEARISH"
                    biases.append(SeasonalBias(
                        bias=bias,
                        pattern_type="TIME_OF_DAY",
                        accuracy=patterns.time_of_day.pattern_strength,
                        confidence_boost=self.confidence_boost,
                        description=f"{current_session} session typically {bias.lower()} ({session_performance:+.2f}%)"
                    ))
        
        # Check monthly pattern
        if patterns.monthly and patterns.monthly.pattern_strength >= self.pattern_accuracy_threshold:
            month = current_time.month
            day_of_month = current_time.day
            week_of_month = min(5, (day_of_month - 1) // 7 + 1)
            
            month_performance = patterns.monthly.performance_by_month.get(month, 0)
            week_performance = patterns.monthly.performance_by_week.get(week_of_month, 0)
            
            # Use week performance if more significant
            if abs(week_performance) > abs(month_performance) and abs(week_performance) > 0.1:
                bias = "BULLISH" if week_performance > 0 else "BEARISH"
                biases.append(SeasonalBias(
                    bias=bias,
                    pattern_type="MONTHLY",
                    accuracy=patterns.monthly.pattern_strength,
                    confidence_boost=self.confidence_boost,
                    description=f"Week {week_of_month} of month typically {bias.lower()} ({week_performance:+.2f}%)"
                ))
        
        # Check cyclical patterns
        if patterns.cycles:
            for cycle in patterns.cycles:
                if cycle.strength >= self.pattern_accuracy_threshold:
                    # Determine if we're near peak or trough
                    days_to_peak = (cycle.next_peak - current_time).days
                    days_to_trough = (cycle.next_trough - current_time).days
                    
                    # If within 20% of cycle period from peak/trough
                    threshold_days = cycle.period_days * 0.2
                    
                    if abs(days_to_peak) < threshold_days:
                        biases.append(SeasonalBias(
                            bias="BULLISH",
                            pattern_type="CYCLICAL",
                            accuracy=cycle.strength,
                            confidence_boost=self.confidence_boost,
                            description=f"{cycle.period_days:.1f}-day cycle approaching peak in {days_to_peak} days"
                        ))
                    elif abs(days_to_trough) < threshold_days:
                        biases.append(SeasonalBias(
                            bias="BEARISH",
                            pattern_type="CYCLICAL",
                            accuracy=cycle.strength,
                            confidence_boost=self.confidence_boost,
                            description=f"{cycle.period_days:.1f}-day cycle approaching trough in {days_to_trough} days"
                        ))
        
        # Return strongest bias
        if not biases:
            return None
        
        # Sort by accuracy
        biases.sort(key=lambda b: b.accuracy, reverse=True)
        strongest_bias = biases[0]
        
        log.info(
            f"[SEASONAL BIAS] {symbol}: {strongest_bias.bias} "
            f"({strongest_bias.pattern_type}, accuracy {strongest_bias.accuracy:.0f}%) - "
            f"{strongest_bias.description}"
        )
        
        return strongest_bias

    
    def analyze_comprehensive(self, symbol: str, candles_daily: List[Dict],
                            candles_intraday: Optional[List[Dict]] = None) -> Dict:
        """
        Comprehensive seasonality analysis.
        
        Args:
            symbol: Trading symbol
            candles_daily: Daily candle data (min 365 days)
            candles_intraday: Intraday candle data for time-of-day analysis (optional)
            
        Returns:
            Dict with comprehensive seasonality analysis
            
        Validates: Requirements 18.1-18.8
        """
        # Analyze patterns
        day_of_week = self.analyze_day_of_week_effect(symbol, candles_daily, self.min_lookback_days)
        time_of_day = self.analyze_time_of_day_patterns(symbol, candles_intraday) if candles_intraday else None
        monthly = self.analyze_monthly_patterns(symbol, candles_daily)
        cycles = self.detect_cycles(candles_daily)
        
        # Create patterns object
        patterns = SeasonalPatterns(
            day_of_week=day_of_week,
            time_of_day=time_of_day,
            monthly=monthly,
            cycles=cycles
        )
        
        # Cache patterns
        self.patterns[symbol] = patterns
        
        # Generate seasonal bias
        current_time = datetime.utcnow()
        seasonal_bias = self.generate_seasonal_bias(symbol, current_time, patterns)
        
        # Build result
        result = {
            "has_seasonal_bias": seasonal_bias is not None,
            "seasonal_bias": {
                "bias": seasonal_bias.bias if seasonal_bias else None,
                "pattern_type": seasonal_bias.pattern_type if seasonal_bias else None,
                "accuracy": seasonal_bias.accuracy if seasonal_bias else 0,
                "confidence_boost": seasonal_bias.confidence_boost if seasonal_bias else 0,
                "description": seasonal_bias.description if seasonal_bias else None,
            },
            "day_of_week": {
                "detected": day_of_week is not None,
                "best_day": day_of_week.best_day if day_of_week else None,
                "worst_day": day_of_week.worst_day if day_of_week else None,
                "pattern_strength": day_of_week.pattern_strength if day_of_week else 0,
                "performance": day_of_week.performance_by_day if day_of_week else {},
            },
            "time_of_day": {
                "detected": time_of_day is not None,
                "best_session": time_of_day.best_session if time_of_day else None,
                "worst_session": time_of_day.worst_session if time_of_day else None,
                "pattern_strength": time_of_day.pattern_strength if time_of_day else 0,
                "performance": time_of_day.performance_by_session if time_of_day else {},
            },
            "monthly": {
                "detected": monthly is not None,
                "pattern_strength": monthly.pattern_strength if monthly else 0,
                "performance_by_month": monthly.performance_by_month if monthly else {},
                "performance_by_week": monthly.performance_by_week if monthly else {},
            },
            "cycles": {
                "detected": len(cycles) > 0,
                "count": len(cycles),
                "cycles": [
                    {
                        "period_days": c.period_days,
                        "strength": c.strength,
                        "next_peak": c.next_peak.isoformat(),
                        "next_trough": c.next_trough.isoformat(),
                    }
                    for c in cycles
                ],
            },
        }
        
        return result
