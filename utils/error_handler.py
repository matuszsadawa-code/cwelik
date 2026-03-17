"""
Error Handler - Retry logic with exponential backoff.
Graceful degradation for API errors.
"""

import time
import logging
from typing import Callable, Any, Optional, Type, Tuple
from functools import wraps

log = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""
    
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


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        config: Retry configuration
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Callback function called on each retry
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                
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
                    
                    time.sleep(delay)
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator


def safe_execute(
    func: Callable,
    default: Any = None,
    log_errors: bool = True,
    error_message: Optional[str] = None
) -> Any:
    """
    Execute function safely, returning default on error.
    
    Args:
        func: Function to execute
        default: Default value to return on error
        log_errors: Whether to log errors
        error_message: Custom error message
        
    Returns:
        Function result or default value
    """
    try:
        return func()
    except Exception as e:
        if log_errors:
            msg = error_message or f"Error in {func.__name__}"
            log.error(f"{msg}: {e}")
        return default


class CircuitBreaker:
    """Circuit breaker pattern for failing services."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
                log.info("Circuit breaker entering half-open state")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        if self.state == "half_open":
            self.state = "closed"
            log.info("Circuit breaker closed")
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            log.warning(f"Circuit breaker opened after {self.failure_count} failures")
