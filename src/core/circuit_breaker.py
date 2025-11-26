"""Circuit Breaker implementation for MCP servers"""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional

import structlog

from src.core.exceptions import CircuitBreakerError

logger = structlog.get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerMetrics:
    """Metrics for circuit breaker"""

    def __init__(self) -> None:
        self.total_requests: int = 0
        self.successful_requests: int = 0
        self.failed_requests: int = 0
        self.rejected_requests: int = 0
        self.last_failure_time: Optional[float] = None
        self.last_success_time: Optional[float] = None
        self.state_changes: int = 0

    def record_success(self) -> None:
        """Record successful request"""
        self.total_requests += 1
        self.successful_requests += 1
        self.last_success_time = time.time()

    def record_failure(self) -> None:
        """Record failed request"""
        self.total_requests += 1
        self.failed_requests += 1
        self.last_failure_time = time.time()

    def record_rejection(self) -> None:
        """Record rejected request"""
        self.rejected_requests += 1

    def record_state_change(self) -> None:
        """Record state change"""
        self.state_changes += 1

    def get_failure_rate(self) -> float:
        """Calculate failure rate"""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    def get_success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "rejected_requests": self.rejected_requests,
            "failure_rate": self.get_failure_rate(),
            "success_rate": self.get_success_rate(),
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "state_changes": self.state_changes,
        }


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance.

    Automatically opens circuit after consecutive failures and
    periodically attempts recovery through half-open state.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        half_open_max_calls: int = 3,
    ) -> None:
        """
        Initialize circuit breaker

        Args:
            name: Identifier for this circuit breaker
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Seconds to wait before attempting recovery
            half_open_max_calls: Max calls allowed in half-open state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
        self.metrics = CircuitBreakerMetrics()

        logger.info(
            "circuit_breaker_initialized",
            name=name,
            failure_threshold=failure_threshold,
            timeout_seconds=timeout_seconds,
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state

    @property
    def is_open(self) -> bool:
        """Check if circuit is open"""
        return self._state == CircuitState.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed"""
        return self._state == CircuitState.CLOSED

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open"""
        return self._state == CircuitState.HALF_OPEN

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute function with circuit breaker protection

        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
        """
        async with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    self.metrics.record_rejection()
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is OPEN",
                        server_name=self.name,
                        state=self._state.value,
                        details={
                            "failure_count": self._failure_count,
                            "time_until_retry": self._time_until_retry(),
                        },
                    )

            # Check if we should reject in HALF_OPEN state
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    self.metrics.record_rejection()
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is HALF_OPEN (max calls reached)",
                        server_name=self.name,
                        state=self._state.value,
                    )
                self._half_open_calls += 1

        # Execute the function
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise e

    async def _on_success(self) -> None:
        """Handle successful call"""
        async with self._lock:
            self.metrics.record_success()

            if self._state == CircuitState.HALF_OPEN:
                # Successful call in half-open, transition to closed
                self._transition_to_closed()
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

            logger.debug(
                "circuit_breaker_success",
                name=self.name,
                state=self._state.value,
            )

    async def _on_failure(self) -> None:
        """Handle failed call"""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            self.metrics.record_failure()

            if self._state == CircuitState.HALF_OPEN:
                # Failed in half-open, go back to open
                self._transition_to_open()
            elif self._state == CircuitState.CLOSED:
                # Check if we should open
                if self._failure_count >= self.failure_threshold:
                    self._transition_to_open()

            logger.warning(
                "circuit_breaker_failure",
                name=self.name,
                state=self._state.value,
                failure_count=self._failure_count,
            )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self._last_failure_time is None:
            return True
        return time.time() - self._last_failure_time >= self.timeout_seconds

    def _time_until_retry(self) -> float:
        """Calculate time until retry attempt"""
        if self._last_failure_time is None:
            return 0.0
        elapsed = time.time() - self._last_failure_time
        return max(0.0, self.timeout_seconds - elapsed)

    def _transition_to_open(self) -> None:
        """Transition to OPEN state"""
        if self._state != CircuitState.OPEN:
            logger.warning(
                "circuit_breaker_opened",
                name=self.name,
                previous_state=self._state.value,
                failure_count=self._failure_count,
            )
            self._state = CircuitState.OPEN
            self.metrics.record_state_change()

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state"""
        if self._state != CircuitState.HALF_OPEN:
            logger.info(
                "circuit_breaker_half_opened",
                name=self.name,
                previous_state=self._state.value,
            )
            self._state = CircuitState.HALF_OPEN
            self._half_open_calls = 0
            self.metrics.record_state_change()

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state"""
        if self._state != CircuitState.CLOSED:
            logger.info(
                "circuit_breaker_closed",
                name=self.name,
                previous_state=self._state.value,
            )
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._half_open_calls = 0
            self.metrics.record_state_change()

    async def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state"""
        async with self._lock:
            self._transition_to_closed()
            self._failure_count = 0
            self._last_failure_time = None
            logger.info("circuit_breaker_reset", name=self.name)

    def get_status(self) -> Dict[str, Any]:
        """Get current status of circuit breaker"""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "timeout_seconds": self.timeout_seconds,
            "time_until_retry": self._time_until_retry() if self.is_open else None,
            "metrics": self.metrics.to_dict(),
        }
