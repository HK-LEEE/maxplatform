"""
Circuit Breaker Pattern Implementation - Wave 2
Provides resilience against database timeouts and connection failures
"""

import asyncio
import time
import logging
from enum import Enum
from typing import Any, Callable, Optional, Dict
from functools import wraps
import statistics
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation - requests flow through
    OPEN = "open"          # Circuit is open - requests fail fast
    HALF_OPEN = "half_open"  # Testing if service is back - limited requests

class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open"""
    pass

class CircuitBreaker:
    """
    Circuit Breaker implementation for database operations
    
    Features:
    - Automatic failure detection and recovery
    - Configurable thresholds and timeouts
    - Metrics collection for monitoring
    - Thread-safe operation
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,          # Number of failures to open circuit
        recovery_timeout: int = 60,          # Seconds to wait before trying again
        expected_exception: type = Exception, # Exception type that triggers circuit
        success_threshold: int = 3,          # Successes needed to close circuit
        timeout: int = 30,                   # Request timeout in seconds
        monitor_window: int = 300            # Monitoring window in seconds
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.monitor_window = monitor_window
        
        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.next_attempt_time = 0
        
        # Metrics
        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0
        self.total_timeouts = 0
        self.response_times: list = []
        self.last_reset_time = time.time()
        
        # Thread safety
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker
        """
        async with self._lock:
            await self._update_state()
            
            # Check if circuit is open
            if self.state == CircuitState.OPEN:
                logger.warning(f"Circuit breaker {self.name} is OPEN - failing fast")
                raise CircuitBreakerError(
                    f"Circuit breaker {self.name} is open. Service unavailable."
                )
            
            # In HALF_OPEN state, only allow limited requests
            if self.state == CircuitState.HALF_OPEN and self.success_count > 0:
                logger.warning(f"Circuit breaker {self.name} is HALF_OPEN - limiting requests")
                raise CircuitBreakerError(
                    f"Circuit breaker {self.name} is half-open. Limited requests allowed."
                )
        
        # Execute the function with timeout
        start_time = time.time()
        self.total_requests += 1
        
        try:
            # Apply timeout
            result = await asyncio.wait_for(
                self._execute_async(func, *args, **kwargs),
                timeout=self.timeout
            )
            
            # Success
            response_time = time.time() - start_time
            await self._record_success(response_time)
            return result
            
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            await self._record_timeout(response_time)
            raise CircuitBreakerError(
                f"Circuit breaker {self.name} - request timeout after {self.timeout}s"
            )
            
        except self.expected_exception as e:
            response_time = time.time() - start_time
            await self._record_failure(response_time, e)
            raise
        
        except Exception as e:
            # Unexpected exceptions don't affect circuit breaker
            response_time = time.time() - start_time
            self.response_times.append(response_time)
            logger.error(f"Unexpected error in circuit breaker {self.name}: {e}")
            raise
    
    async def _execute_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function, handling both sync and async functions"""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, func, *args, **kwargs)
    
    async def _record_success(self, response_time: float):
        """Record successful execution"""
        async with self._lock:
            self.total_successes += 1
            self.response_times.append(response_time)
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self._close_circuit()
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0
    
    async def _record_failure(self, response_time: float, exception: Exception):
        """Record failed execution"""
        async with self._lock:
            self.total_failures += 1
            self.failure_count += 1
            self.last_failure_time = time.time()
            self.response_times.append(response_time)
            
            logger.warning(
                f"Circuit breaker {self.name} - failure {self.failure_count}/{self.failure_threshold}: {exception}"
            )
            
            if self.failure_count >= self.failure_threshold:
                self._open_circuit()
    
    async def _record_timeout(self, response_time: float):
        """Record timeout"""
        async with self._lock:
            self.total_timeouts += 1
            self.failure_count += 1
            self.last_failure_time = time.time()
            self.response_times.append(response_time)
            
            logger.warning(
                f"Circuit breaker {self.name} - timeout {self.failure_count}/{self.failure_threshold}"
            )
            
            if self.failure_count >= self.failure_threshold:
                self._open_circuit()
    
    async def _update_state(self):
        """Update circuit breaker state based on time and conditions"""
        current_time = time.time()
        
        if (self.state == CircuitState.OPEN and 
            current_time >= self.next_attempt_time):
            self._half_open_circuit()
    
    def _open_circuit(self):
        """Open the circuit breaker"""
        self.state = CircuitState.OPEN
        self.next_attempt_time = time.time() + self.recovery_timeout
        self.success_count = 0
        
        logger.error(
            f"Circuit breaker {self.name} OPENED - "
            f"failure threshold reached ({self.failure_count} failures)"
        )
    
    def _half_open_circuit(self):
        """Set circuit breaker to half-open state"""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        
        logger.info(f"Circuit breaker {self.name} HALF-OPEN - testing service recovery")
    
    def _close_circuit(self):
        """Close the circuit breaker"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        
        logger.info(f"Circuit breaker {self.name} CLOSED - service recovered")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        current_time = time.time()
        recent_response_times = [
            rt for rt in self.response_times 
            if current_time - self.last_reset_time <= self.monitor_window
        ]
        
        # Clean old response times
        self.response_times = recent_response_times
        
        return {
            "name": self.name,
            "state": self.state.value,
            "total_requests": self.total_requests,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "total_timeouts": self.total_timeouts,
            "failure_count": self.failure_count,
            "success_rate": (
                self.total_successes / max(self.total_requests, 1) * 100
            ),
            "avg_response_time": (
                statistics.mean(recent_response_times) 
                if recent_response_times else 0
            ),
            "median_response_time": (
                statistics.median(recent_response_times)
                if recent_response_times else 0
            ),
            "last_failure_time": (
                datetime.fromtimestamp(self.last_failure_time).isoformat()
                if self.last_failure_time else None
            ),
            "next_attempt_time": (
                datetime.fromtimestamp(self.next_attempt_time).isoformat()
                if self.state == CircuitState.OPEN else None
            )
        }
    
    def reset(self):
        """Reset circuit breaker to initial state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.next_attempt_time = 0
        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0
        self.total_timeouts = 0
        self.response_times = []
        self.last_reset_time = time.time()
        
        logger.info(f"Circuit breaker {self.name} RESET")

# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}

def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception,
    success_threshold: int = 3,
    timeout: int = 30
) -> CircuitBreaker:
    """Get or create a circuit breaker"""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            success_threshold=success_threshold,
            timeout=timeout
        )
    return _circuit_breakers[name]

def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception,
    success_threshold: int = 3,
    timeout: int = 30
):
    """Decorator for circuit breaker functionality"""
    def decorator(func: Callable):
        cb = get_circuit_breaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            success_threshold=success_threshold,
            timeout=timeout
        )
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await cb.call(func, *args, **kwargs)
        
        return wrapper
    return decorator

def get_all_circuit_breaker_metrics() -> Dict[str, Dict[str, Any]]:
    """Get metrics for all circuit breakers"""
    return {name: cb.get_metrics() for name, cb in _circuit_breakers.items()}

def reset_all_circuit_breakers():
    """Reset all circuit breakers"""
    for cb in _circuit_breakers.values():
        cb.reset()