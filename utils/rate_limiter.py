"""
Rate Limiter - Token Bucket Algorithm
Prevents API rate limit errors by controlling request frequency.
"""

import time
import threading
from typing import Dict


class RateLimiter:
    """Token bucket rate limiter for API calls."""
    
    def __init__(self, requests_per_second: float = 10, burst: int = 20):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_second: Maximum sustained request rate
            burst: Maximum burst size (token bucket capacity)
        """
        self.rate = requests_per_second
        self.capacity = burst
        self.tokens = burst
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def acquire(self, tokens: int = 1, timeout: float = 10.0) -> bool:
        """
        Acquire tokens for making requests.
        
        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum time to wait for tokens
            
        Returns:
            True if tokens acquired, False if timeout
        """
        deadline = time.time() + timeout
        
        while time.time() < deadline:
            with self.lock:
                self._refill()
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
            
            # Wait a bit before retrying
            time.sleep(0.01)
        
        return False
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        
        # Add tokens based on rate
        new_tokens = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_update = now


class MultiRateLimiter:
    """Manages multiple rate limiters for different endpoints."""
    
    def __init__(self):
        self.limiters: Dict[str, RateLimiter] = {}
        self.lock = threading.Lock()
    
    def get_limiter(self, endpoint: str, requests_per_second: float = 10, 
                    burst: int = 20) -> RateLimiter:
        """Get or create rate limiter for endpoint."""
        with self.lock:
            if endpoint not in self.limiters:
                self.limiters[endpoint] = RateLimiter(requests_per_second, burst)
            return self.limiters[endpoint]
    
    def acquire(self, endpoint: str, tokens: int = 1, timeout: float = 10.0) -> bool:
        """Acquire tokens for endpoint."""
        limiter = self.get_limiter(endpoint)
        return limiter.acquire(tokens, timeout)
