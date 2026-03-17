"""
News Sentiment Integration Module

Integrates news sentiment analysis to avoid trading before high-impact events
and leverage sentiment shifts for improved signal confidence.

Validates: Requirements 13.1-13.8
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from utils.logger import get_logger

log = get_logger("analytics.news_sentiment")


@dataclass
class NewsItem:
    """Individual news item with sentiment analysis"""
    title: str
    source: str
    published_at: datetime
    url: str
    sentiment: str  # POSITIVE, NEGATIVE, NEUTRAL
    impact_score: float  # 0-100
    symbols: List[str]


@dataclass
class SentimentScore:
    """Aggregate sentiment score for a symbol"""
    score: float  # -100 to +100
    sentiment: str  # POSITIVE, NEGATIVE, NEUTRAL
    news_count: int
    avg_impact: float
    timestamp: datetime


@dataclass
class SentimentShift:
    """Detected sentiment shift event"""
    previous_score: float
    current_score: float
    change: float
    duration_hours: float
    timestamp: datetime


@dataclass
class HighImpactEvent:
    """High-impact event that should block trading"""
    event_type: str  # FED_ANNOUNCEMENT, HACK, LISTING, REGULATION
    scheduled_time: datetime
    impact_level: str  # HIGH, CRITICAL
    affected_symbols: List[str]


class NewsSentimentAnalyzer:
    """
    News sentiment analyzer for crypto trading signals.
    
    Integrates with news APIs to:
    - Fetch recent news for symbols
    - Analyze sentiment (POSITIVE, NEGATIVE, NEUTRAL)
    - Calculate aggregate sentiment scores
    - Detect sentiment shifts
    - Identify high-impact events
    - Adjust signal confidence based on sentiment
    """
    
    def __init__(self, config: Dict):
        """
        Initialize news sentiment analyzer.
        
        Args:
            config: Configuration dict with API settings
        """
        self.config = config
        self.api_key = config.get("api_key", "")
        self.api_provider = config.get("api_provider", "cryptopanic")
        self.lookback_hours = config.get("lookback_hours", 24)
        self.lookahead_hours = config.get("lookahead_hours", 2)
        self.sentiment_shift_threshold = config.get("sentiment_shift_threshold", 30)
        self.sentiment_shift_window_hours = config.get("sentiment_shift_window_hours", 1)
        self.negative_sentiment_penalty = config.get("negative_sentiment_penalty", -20)
        self.positive_sentiment_boost = config.get("positive_sentiment_boost", 10)
        self.high_impact_block_duration_hours = config.get("high_impact_block_duration_hours", 2)
        self.update_interval_minutes = config.get("update_interval_minutes", 15)
        
        # Cache for news and sentiment
        self.news_cache: Dict[str, List[NewsItem]] = {}
        self.sentiment_history: Dict[str, List[SentimentScore]] = {}
        self.last_update: Dict[str, datetime] = {}
        
        # High-impact event keywords
        self.high_impact_keywords = {
            "FED_ANNOUNCEMENT": ["fed", "federal reserve", "interest rate", "fomc", "powell"],
            "HACK": ["hack", "exploit", "breach", "stolen", "security"],
            "LISTING": ["listing", "binance listing", "coinbase listing", "exchange listing"],
            "REGULATION": ["regulation", "sec", "regulatory", "ban", "legal action"]
        }
        
        log.info(f"NewsSentimentAnalyzer initialized with provider: {self.api_provider}")
    
    def fetch_news(self, symbol: str, lookback_hours: Optional[int] = None) -> List[NewsItem]:
        """
        Fetch news from API (CryptoPanic, NewsAPI, etc.).
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            lookback_hours: Hours of news to fetch (default: config value)
            
        Returns:
            List of news items
        """
        lookback = lookback_hours or self.lookback_hours
        
        # Check cache freshness
        if symbol in self.last_update:
            time_since_update = (datetime.now() - self.last_update[symbol]).total_seconds() / 60
            if time_since_update < self.update_interval_minutes and symbol in self.news_cache:
                log.debug(f"Using cached news for {symbol} (updated {time_since_update:.1f}m ago)")
                return self.news_cache[symbol]
        
        try:
            # Extract base currency (BTC from BTCUSDT)
            base_currency = symbol.replace("USDT", "").replace("BUSD", "").replace("USD", "")
            
            if self.api_provider == "cryptopanic":
                news_items = self._fetch_cryptopanic(base_currency, lookback)
            elif self.api_provider == "newsapi":
                news_items = self._fetch_newsapi(base_currency, lookback)
            else:
                log.warning(f"Unknown API provider: {self.api_provider}, returning empty news")
                news_items = []
            
            # Update cache
            self.news_cache[symbol] = news_items
            self.last_update[symbol] = datetime.now()
            
            log.info(f"Fetched {len(news_items)} news items for {symbol}")
            return news_items
            
        except Exception as e:
            log.error(f"Error fetching news for {symbol}: {e}", exc_info=True)
            return self.news_cache.get(symbol, [])
    
    def _fetch_cryptopanic(self, currency: str, lookback_hours: int) -> List[NewsItem]:
        """Fetch news from CryptoPanic API"""
        if not self.api_key:
            log.warning("CryptoPanic API key not configured")
            return []
        
        url = "https://cryptopanic.com/api/v1/posts/"
        params = {
            "auth_token": self.api_key,
            "currencies": currency,
            "filter": "hot",
            "public": "true"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            news_items = []
            cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
            
            for post in data.get("results", []):
                published_at = datetime.fromisoformat(post["published_at"].replace("Z", "+00:00"))
                
                if published_at < cutoff_time:
                    continue
                
                # Analyze sentiment from votes
                votes = post.get("votes", {})
                sentiment = self._analyze_cryptopanic_sentiment(votes)
                impact_score = self._calculate_impact_score(post)
                
                news_item = NewsItem(
                    title=post["title"],
                    source=post.get("source", {}).get("title", "Unknown"),
                    published_at=published_at,
                    url=post["url"],
                    sentiment=sentiment,
                    impact_score=impact_score,
                    symbols=[currency]
                )
                news_items.append(news_item)
            
            return news_items
            
        except Exception as e:
            log.error(f"Error fetching from CryptoPanic: {e}")
            return []
    
    def _fetch_newsapi(self, currency: str, lookback_hours: int) -> List[NewsItem]:
        """Fetch news from NewsAPI"""
        if not self.api_key:
            log.warning("NewsAPI key not configured")
            return []
        
        url = "https://newsapi.org/v2/everything"
        from_date = (datetime.now() - timedelta(hours=lookback_hours)).isoformat()
        
        params = {
            "apiKey": self.api_key,
            "q": f"{currency} OR cryptocurrency",
            "from": from_date,
            "sortBy": "publishedAt",
            "language": "en"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            news_items = []
            for article in data.get("articles", []):
                published_at = datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00"))
                
                # Simple sentiment analysis based on title/description
                sentiment = self._analyze_text_sentiment(
                    article.get("title", "") + " " + article.get("description", "")
                )
                impact_score = 50.0  # Default impact
                
                news_item = NewsItem(
                    title=article["title"],
                    source=article.get("source", {}).get("name", "Unknown"),
                    published_at=published_at,
                    url=article["url"],
                    sentiment=sentiment,
                    impact_score=impact_score,
                    symbols=[currency]
                )
                news_items.append(news_item)
            
            return news_items
            
        except Exception as e:
            log.error(f"Error fetching from NewsAPI: {e}")
            return []
    
    def _analyze_cryptopanic_sentiment(self, votes: Dict) -> str:
        """Analyze sentiment from CryptoPanic votes"""
        positive = votes.get("positive", 0)
        negative = votes.get("negative", 0)
        
        if positive == 0 and negative == 0:
            return "NEUTRAL"
        
        ratio = positive / (positive + negative) if (positive + negative) > 0 else 0.5
        
        if ratio > 0.6:
            return "POSITIVE"
        elif ratio < 0.4:
            return "NEGATIVE"
        else:
            return "NEUTRAL"
    
    def _analyze_text_sentiment(self, text: str) -> str:
        """Simple keyword-based sentiment analysis"""
        text_lower = text.lower()
        
        positive_keywords = ["bullish", "surge", "rally", "gain", "up", "rise", "growth", "positive", "breakthrough"]
        negative_keywords = ["bearish", "crash", "drop", "fall", "down", "decline", "loss", "negative", "hack", "scam"]
        
        positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)
        negative_count = sum(1 for keyword in negative_keywords if keyword in text_lower)
        
        if positive_count > negative_count:
            return "POSITIVE"
        elif negative_count > positive_count:
            return "NEGATIVE"
        else:
            return "NEUTRAL"
    
    def _calculate_impact_score(self, post: Dict) -> float:
        """Calculate impact score based on votes and metadata"""
        votes = post.get("votes", {})
        total_votes = votes.get("positive", 0) + votes.get("negative", 0) + votes.get("important", 0)
        
        # Base score from votes
        score = min(total_votes * 10, 100)
        
        # Boost for important votes
        if votes.get("important", 0) > 5:
            score = min(score * 1.5, 100)
        
        return score
    
    def analyze_sentiment(self, news_item: NewsItem) -> str:
        """
        Analyze sentiment of news item.
        
        Args:
            news_item: News item to analyze
            
        Returns:
            POSITIVE, NEGATIVE, or NEUTRAL
        """
        # Already analyzed during fetch
        return news_item.sentiment
    
    def calculate_aggregate_sentiment(self, symbol: str) -> SentimentScore:
        """
        Calculate aggregate sentiment score (-100 to +100) for symbol.
        
        Weights recent news more heavily using exponential decay.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            SentimentScore with aggregate metrics
        """
        news_items = self.fetch_news(symbol)
        
        if not news_items:
            return SentimentScore(
                score=0.0,
                sentiment="NEUTRAL",
                news_count=0,
                avg_impact=0.0,
                timestamp=datetime.now()
            )
        
        # Calculate weighted sentiment score
        total_weight = 0.0
        weighted_score = 0.0
        total_impact = 0.0
        
        now = datetime.now()
        
        for news in news_items:
            # Time decay: more recent news has higher weight
            hours_ago = (now - news.published_at).total_seconds() / 3600
            time_weight = 2 ** (-hours_ago / 12)  # Half-life of 12 hours
            
            # Impact weight
            impact_weight = news.impact_score / 100.0
            
            # Combined weight
            weight = time_weight * impact_weight
            
            # Sentiment value: POSITIVE=+1, NEGATIVE=-1, NEUTRAL=0
            sentiment_value = {
                "POSITIVE": 1.0,
                "NEGATIVE": -1.0,
                "NEUTRAL": 0.0
            }.get(news.sentiment, 0.0)
            
            weighted_score += sentiment_value * weight
            total_weight += weight
            total_impact += news.impact_score
        
        # Normalize to -100 to +100 range
        if total_weight > 0:
            aggregate_score = (weighted_score / total_weight) * 100
        else:
            aggregate_score = 0.0
        
        # Classify overall sentiment
        if aggregate_score > 20:
            sentiment = "POSITIVE"
        elif aggregate_score < -20:
            sentiment = "NEGATIVE"
        else:
            sentiment = "NEUTRAL"
        
        avg_impact = total_impact / len(news_items) if news_items else 0.0
        
        sentiment_score = SentimentScore(
            score=aggregate_score,
            sentiment=sentiment,
            news_count=len(news_items),
            avg_impact=avg_impact,
            timestamp=now
        )
        
        # Store in history
        if symbol not in self.sentiment_history:
            self.sentiment_history[symbol] = []
        self.sentiment_history[symbol].append(sentiment_score)
        
        # Keep only last 24 hours of history
        cutoff = now - timedelta(hours=24)
        self.sentiment_history[symbol] = [
            s for s in self.sentiment_history[symbol]
            if s.timestamp > cutoff
        ]
        
        log.debug(f"Aggregate sentiment for {symbol}: {aggregate_score:.1f} ({sentiment})")
        return sentiment_score
    
    def detect_sentiment_shift(self, symbol: str) -> Optional[SentimentShift]:
        """
        Detect significant sentiment shift (>30 points in 1 hour).
        
        Args:
            symbol: Trading symbol
            
        Returns:
            SentimentShift if detected, None otherwise
        """
        if symbol not in self.sentiment_history or len(self.sentiment_history[symbol]) < 2:
            return None
        
        current_sentiment = self.sentiment_history[symbol][-1]
        
        # Look for sentiment from N hours ago
        cutoff = current_sentiment.timestamp - timedelta(hours=self.sentiment_shift_window_hours)
        
        previous_sentiments = [
            s for s in self.sentiment_history[symbol]
            if s.timestamp <= cutoff
        ]
        
        if not previous_sentiments:
            return None
        
        previous_sentiment = previous_sentiments[-1]
        change = current_sentiment.score - previous_sentiment.score
        
        if abs(change) >= self.sentiment_shift_threshold:
            duration_hours = (current_sentiment.timestamp - previous_sentiment.timestamp).total_seconds() / 3600
            
            shift = SentimentShift(
                previous_score=previous_sentiment.score,
                current_score=current_sentiment.score,
                change=change,
                duration_hours=duration_hours,
                timestamp=current_sentiment.timestamp
            )
            
            log.warning(f"Sentiment shift detected for {symbol}: {change:+.1f} points in {duration_hours:.1f}h")
            return shift
        
        return None
    
    def identify_high_impact_events(self, symbol: str, lookahead_hours: Optional[int] = None) -> List[HighImpactEvent]:
        """
        Identify high-impact events in next N hours.
        
        Examples: Fed announcements, major hacks, exchange listings
        
        Args:
            symbol: Trading symbol
            lookahead_hours: Hours to look ahead (default: config value)
            
        Returns:
            List of high-impact events
        """
        lookahead = lookahead_hours or self.lookahead_hours
        news_items = self.fetch_news(symbol, lookback_hours=lookahead)
        
        high_impact_events = []
        now = datetime.now()
        future_cutoff = now + timedelta(hours=lookahead)
        
        for news in news_items:
            # Check if news is in the future (scheduled event)
            if news.published_at > now and news.published_at <= future_cutoff:
                # Check for high-impact keywords
                title_lower = news.title.lower()
                
                for event_type, keywords in self.high_impact_keywords.items():
                    if any(keyword in title_lower for keyword in keywords):
                        impact_level = "CRITICAL" if news.impact_score > 80 else "HIGH"
                        
                        event = HighImpactEvent(
                            event_type=event_type,
                            scheduled_time=news.published_at,
                            impact_level=impact_level,
                            affected_symbols=[symbol]
                        )
                        high_impact_events.append(event)
                        
                        log.warning(f"High-impact event detected: {event_type} for {symbol} at {news.published_at}")
                        break
        
        return high_impact_events
    
    def get_confidence_adjustment(self, signal: Dict, sentiment: SentimentScore) -> float:
        """
        Calculate confidence adjustment based on sentiment alignment.
        
        Args:
            signal: Trading signal dict with 'direction' key
            sentiment: Current sentiment score
            
        Returns:
            Confidence adjustment (+/- percentage)
        """
        signal_direction = signal.get("direction", "").upper()
        
        if signal_direction not in ["LONG", "SHORT"]:
            return 0.0
        
        # LONG signal
        if signal_direction == "LONG":
            if sentiment.sentiment == "NEGATIVE":
                # Negative sentiment conflicts with LONG
                adjustment = self.negative_sentiment_penalty
                log.info(f"LONG signal with NEGATIVE sentiment: {adjustment}% confidence adjustment")
                return adjustment
            elif sentiment.sentiment == "POSITIVE":
                # Positive sentiment supports LONG
                adjustment = self.positive_sentiment_boost
                log.info(f"LONG signal with POSITIVE sentiment: +{adjustment}% confidence adjustment")
                return adjustment
        
        # SHORT signal
        elif signal_direction == "SHORT":
            if sentiment.sentiment == "POSITIVE":
                # Positive sentiment conflicts with SHORT
                adjustment = self.negative_sentiment_penalty
                log.info(f"SHORT signal with POSITIVE sentiment: {adjustment}% confidence adjustment")
                return adjustment
            elif sentiment.sentiment == "NEGATIVE":
                # Negative sentiment supports SHORT
                adjustment = self.positive_sentiment_boost
                log.info(f"SHORT signal with NEGATIVE sentiment: +{adjustment}% confidence adjustment")
                return adjustment
        
        return 0.0
    
    def should_block_signal(self, symbol: str) -> bool:
        """
        Check if signals should be blocked due to high-impact events.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if signals should be blocked
        """
        high_impact_events = self.identify_high_impact_events(symbol, self.high_impact_block_duration_hours)
        
        if high_impact_events:
            log.warning(f"Blocking signals for {symbol} due to {len(high_impact_events)} high-impact event(s)")
            return True
        
        return False
