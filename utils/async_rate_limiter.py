"""
Async Rate Limiter - For asyncio-based API clients.
Uses asyncio.Semaphore for non-blocking rate limiting.
"""

import asyncio
import time
from typing import Dict


class AsyncRateLimiter:
    """Async rate limiter using token bucket algorithm."""
    
    def __init__(self, requests_per_second: float = 10, burst: int = 20):
        """
        Initialize async rate limiter.
        
        Args:
            requests_per_second: Maximum sustained request rate
            burst: Maximum burst size (token bucket capacity)
        """
        self.rate = requests_per_second
        self.capacity = burst
        self.tokens = burst
        self.last_update = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1, timeout: float = 10.0) -> bool:
        """
        Acquire tokens for making requests (async).
        
        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum time to wait for tokens
            
        Returns:
            True if tokens acquired, False if timeout
        """
        deadline = time.time() + timeout
        
        while time.time() < deadline:
            async with self.lock:
                self._refill()
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
            
            # Wait a bit before retrying (non-blocking)
            await asyncio.sleep(0.01)
        
        return False
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        
        # Add tokens based on rate
        new_tokens = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_update = now


class AsyncMultiRateLimiter:
    """Manages multiple async rate limiters for different endpoints."""
    
    def __init__(self):
        self.limiters: Dict[str, AsyncRateLimiter] = {}
        self.lock = asyncio.Lock()
    
    async def get_limiter(self, endpoint: str, requests_per_second: float = 10, 
                         burst: int = 20) -> AsyncRateLimiter:
        """Get or create rate limiter for endpoint."""
        async with self.lock:
            if endpoint not in self.limiters:
                self.limiters[endpoint] = AsyncRateLimiter(requests_per_second, burst)
            return self.limiters[endpoint]
    
    async def acquire(self, endpoint: str, tokens: int = 1, timeout: float = 10.0) -> bool:
        """Acquire tokens for endpoint."""
        limiter = await self.get_limiter(endpoint)
        return await limiter.acquire(tokens, timeout)
