"""
Circuit Breaker Pattern Implementation for Error Handling.

Prevents cascading failures by temporarily disabling failing components.
"""

import time
from enum import Enum
from typing import Callable, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# Simple logger for standalone use
class SimpleLogger:
    def __init__(self, name):
        self.name = name
    def info(self, msg): print(f"[INFO] {self.name}: {msg}")
    def warning(self, msg): print(f"[WARN] {self.name}: {msg}")
    def error(self, msg): print(f"[ERROR] {self.name}: {msg}")

log = SimpleLogger("circuit_breaker")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""
    state: CircuitState
    failure_count: int
    success_count: int
    last_failure_time: Optional[float]
    last_success_time: Optional[float]
    total_calls: int
    total_failures: int
    total_successes: int


class CircuitBreaker:
    """
    Circuit Breaker implementation.
    
    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Too many failures, reject calls immediately
    - HALF_OPEN: Testing recovery, allow limited calls
    
    Transitions:
    - CLOSED -> OPEN: After failure_threshold consecutive failures
    - OPEN -> HALF_OPEN: After timeout_seconds
    - HALF_OPEN -> CLOSED: After success_threshold consecutive successes
    - HALF_OPEN -> OPEN: On any failure
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout_seconds: int = 60,
        half_open_max_calls: int = 1,
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name (for logging)
            failure_threshold: Consecutive failures before opening circuit
            success_threshold: Consecutive successes to close circuit from half-open
            timeout_seconds: Seconds to wait before trying again (OPEN -> HALF_OPEN)
            half_open_max_calls: Max concurrent calls in half-open state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.last_success_time: Optional[float] = None
        self.half_open_calls = 0
        
        # Statistics
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
        
        log.info(f"Circuit breaker initialized: {name} (threshold={failure_threshold}, timeout={timeout_seconds}s)")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from function
        """
        self.total_calls += 1
        
        # Check if circuit is open
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Will retry after {self.timeout_seconds}s."
                )
        
        # Check half-open call limit
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is HALF_OPEN with max calls reached."
                )
            self.half_open_calls += 1
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
        finally:
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls -= 1
    
    def _on_success(self):
        """Handle successful call."""
        self.total_successes += 1
        self.last_success_time = time.time()
        self.failure_count = 0
        self.success_count += 1
        
        if self.state == CircuitState.HALF_OPEN:
            if self.success_count >= self.success_threshold:
                self._transition_to_closed()
    
    def _on_failure(self):
        """Handle failed call."""
        self.total_failures += 1
        self.last_failure_time = time.time()
        self.success_count = 0
        self.failure_count += 1
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self._transition_to_open()
        elif self.state == CircuitState.HALF_OPEN:
            self._transition_to_open()
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.timeout_seconds
    
    def _transition_to_open(self):
        """Transition to OPEN state."""
        self.state = CircuitState.OPEN
        log.warning(
            f"Circuit breaker '{self.name}' OPENED after {self.failure_count} failures. "
            f"Will retry in {self.timeout_seconds}s."
        )
    
    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        log.info(f"Circuit breaker '{self.name}' transitioned to HALF_OPEN (testing recovery)")
    
    def _transition_to_closed(self):
        """Transition to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        log.info(f"Circuit breaker '{self.name}' CLOSED (service recovered)")
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        log.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")
    
    def get_stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics."""
        return CircuitBreakerStats(
            state=self.state,
            failure_count=self.failure_count,
            success_count=self.success_count,
            last_failure_time=self.last_failure_time,
            last_success_time=self.last_success_time,
            total_calls=self.total_calls,
            total_failures=self.total_failures,
            total_successes=self.total_successes,
        )


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# ============================================================================
# GLOBAL CIRCUIT BREAKERS
# ============================================================================

# Circuit breakers for each advanced feature
_circuit_breakers = {}


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """
    Get or create a circuit breaker.
    
    Args:
        name: Circuit breaker name
        **kwargs: CircuitBreaker initialization parameters
        
    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, **kwargs)
    return _circuit_breakers[name]


def reset_all_circuit_breakers():
    """Reset all circuit breakers."""
    for cb in _circuit_breakers.values():
        cb.reset()


def get_all_circuit_breaker_stats() -> dict:
    """Get statistics for all circuit breakers."""
    return {name: cb.get_stats() for name, cb in _circuit_breakers.items()}
