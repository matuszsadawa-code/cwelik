"""
Async Error Handler - Retry logic for async functions.
"""

import asyncio
import logging
from typing import Callable, Any, Optional, Type, Tuple
from functools import wraps

log = logging.getLogger(__name__)


class AsyncRetryConfig:
    """Configuration for async retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


def async_retry_with_backoff(
    config: Optional[AsyncRetryConfig] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        config: Retry configuration
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Callback function called on each retry
    """
    if config is None:
        config = AsyncRetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                
                except exceptions as e:
                    last_exception = e
                    
                    if attempt >= config.max_retries:
                        log.error(f"{func.__name__} failed after {config.max_retries} retries: {e}")
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.initial_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        import random
                        delay *= (0.5 + random.random())
                    
                    log.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{config.max_retries + 1}): {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    if on_retry:
                        on_retry(attempt, e, delay)
                    
                    await asyncio.sleep(delay)
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator
