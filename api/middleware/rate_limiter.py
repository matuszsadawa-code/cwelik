"""
Rate Limiting Middleware

Implements role-based rate limiting to prevent API abuse and ensure fair resource allocation.

Rate limits per role (requests per 60 seconds):
- viewer: 100 requests/60s
- trader: 200 requests/60s
- admin: 500 requests/60s

Returns 429 status code when rate limit exceeded with headers:
- X-RateLimit-Limit: Maximum requests allowed
- X-RateLimit-Remaining: Requests remaining in current window
- X-RateLimit-Reset: Unix timestamp when rate limit resets
"""

import time
import logging
from typing import Dict, Tuple
from collections import defaultdict
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from api.auth import User, UserRole

logger = logging.getLogger(__name__)


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded"""
    def __init__(self, limit: int, reset_time: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {limit} requests per 60 seconds. Try again after {reset_time}."
        )
        self.limit = limit
        self.reset_time = reset_time


class RateLimiter:
    """
    Token bucket rate limiter with per-user tracking
    
    Tracks request counts per user within 60-second sliding windows.
    """
    
    # Rate limits per role (requests per 60 seconds)
    RATE_LIMITS = {
        UserRole.VIEWER: 100,
        UserRole.TRADER: 200,
        UserRole.ADMIN: 500
    }
    
    # Window size in seconds
    WINDOW_SIZE = 60
    
    def __init__(self):
        """Initialize rate limiter with empty tracking state"""
        # Track requests per user: {user_id: [(timestamp, count), ...]}
        self.user_requests: Dict[str, list] = defaultdict(list)
        
        # Last cleanup time
        self.last_cleanup = time.time()
        
        # Cleanup interval (remove old entries every 5 minutes)
        self.cleanup_interval = 300
    
    def _cleanup_old_entries(self):
        """Remove expired request entries to prevent memory growth"""
        current_time = time.time()
        
        # Only cleanup every 5 minutes
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        cutoff_time = current_time - self.WINDOW_SIZE
        
        # Remove old entries for each user
        for user_id in list(self.user_requests.keys()):
            # Filter out requests older than window size
            self.user_requests[user_id] = [
                (timestamp, count) for timestamp, count in self.user_requests[user_id]
                if timestamp > cutoff_time
            ]
            
            # Remove user entry if no requests remain
            if not self.user_requests[user_id]:
                del self.user_requests[user_id]
        
        self.last_cleanup = current_time
        logger.debug(f"Rate limiter cleanup completed. Active users: {len(self.user_requests)}")
    
    def _get_request_count(self, user_id: str) -> int:
        """
        Get total request count for user in current window
        
        Args:
            user_id: User identifier
            
        Returns:
            Total request count in current 60-second window
        """
        current_time = time.time()
        cutoff_time = current_time - self.WINDOW_SIZE
        
        # Sum all requests within the window
        total_count = sum(
            count for timestamp, count in self.user_requests[user_id]
            if timestamp > cutoff_time
        )
        
        return total_count
    
    def _get_window_reset_time(self, user_id: str) -> int:
        """
        Get Unix timestamp when the rate limit window resets
        
        Args:
            user_id: User identifier
            
        Returns:
            Unix timestamp (seconds) when oldest request expires
        """
        if not self.user_requests[user_id]:
            return int(time.time() + self.WINDOW_SIZE)
        
        # Find oldest request timestamp
        oldest_timestamp = min(timestamp for timestamp, _ in self.user_requests[user_id])
        
        # Reset time is oldest timestamp + window size
        reset_time = int(oldest_timestamp + self.WINDOW_SIZE)
        
        return reset_time
    
    def check_rate_limit(self, user: User) -> Tuple[int, int, int]:
        """
        Check if user has exceeded rate limit
        
        Args:
            user: Authenticated user
            
        Returns:
            Tuple of (limit, remaining, reset_time)
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        # Periodic cleanup
        self._cleanup_old_entries()
        
        # Get rate limit for user's role
        limit = self.RATE_LIMITS.get(user.role, self.RATE_LIMITS[UserRole.VIEWER])
        
        # Get current request count
        current_count = self._get_request_count(user.user_id)
        
        # Calculate remaining requests
        remaining = max(0, limit - current_count)
        
        # Get reset time
        reset_time = self._get_window_reset_time(user.user_id)
        
        # Check if limit exceeded
        if current_count >= limit:
            logger.warning(
                f"Rate limit exceeded for user {user.username} (role: {user.role}). "
                f"Count: {current_count}/{limit}"
            )
            raise RateLimitExceeded(limit, reset_time)
        
        # Record this request
        current_time = time.time()
        self.user_requests[user.user_id].append((current_time, 1))
        
        # Update remaining count (decremented by 1 for this request)
        remaining = max(0, remaining - 1)
        
        logger.debug(
            f"Rate limit check passed for user {user.username} (role: {user.role}). "
            f"Count: {current_count + 1}/{limit}, Remaining: {remaining}"
        )
        
        return limit, remaining, reset_time


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting
    
    Applies rate limiting to all API endpoints except:
    - Health check endpoints (/health, /)
    - Authentication endpoints (/api/auth/*)
    - WebSocket connections (/ws)
    
    Adds rate limit headers to all responses:
    - X-RateLimit-Limit: Maximum requests allowed
    - X-RateLimit-Remaining: Requests remaining in current window
    - X-RateLimit-Reset: Unix timestamp when rate limit resets
    """
    
    # Paths exempt from rate limiting
    EXEMPT_PATHS = [
        "/",
        "/health",
        "/api/health",
        "/api/auth/login",
        "/api/auth/register",
        "/ws",
        "/docs",
        "/redoc",
        "/openapi.json"
    ]
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting
        
        Args:
            request: FastAPI request
            call_next: Next middleware/endpoint handler
            
        Returns:
            Response with rate limit headers
        """
        # Skip rate limiting for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        # Skip rate limiting for WebSocket upgrade requests
        if request.headers.get("upgrade") == "websocket":
            return await call_next(request)
        
        # Get authenticated user from request state
        # (Set by authentication middleware)
        user = getattr(request.state, "user", None)
        
        # If no user (unauthenticated request), apply default viewer limit
        if not user:
            # For unauthenticated requests, use a default user
            from api.auth import User, UserRole
            user = User(
                user_id="anonymous",
                username="anonymous",
                role=UserRole.VIEWER,
                disabled=False
            )
        
        try:
            # Check rate limit
            limit, remaining, reset_time = rate_limiter.check_rate_limit(user)
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_time)
            
            return response
            
        except RateLimitExceeded as e:
            # Return 429 response with rate limit headers
            logger.warning(
                f"Rate limit exceeded for {user.username} on {request.url.path}"
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": e.detail,
                    "limit": e.limit,
                    "reset_time": e.reset_time
                },
                headers={
                    "X-RateLimit-Limit": str(e.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(e.reset_time),
                    "Retry-After": str(max(0, e.reset_time - int(time.time())))
                }
            )
        
        except Exception as e:
            # Log error but don't block request
            logger.error(f"Rate limiting error: {e}")
            return await call_next(request)


def get_rate_limiter() -> RateLimiter:
    """
    Get global rate limiter instance
    
    Returns:
        RateLimiter instance
    """
    return rate_limiter
