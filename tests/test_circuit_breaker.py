"""Tests for Circuit Breaker"""

import pytest

from src.core.circuit_breaker import CircuitBreaker, CircuitState
from src.core.exceptions import CircuitBreakerError


@pytest.mark.asyncio
class TestCircuitBreaker:
    """Test circuit breaker functionality"""

    async def test_circuit_breaker_initialization(self):
        """Test circuit breaker initializes correctly"""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=3,
            timeout_seconds=30,
            half_open_max_calls=2,
        )

        assert cb.name == "test"
        assert cb.state == CircuitState.CLOSED
        assert cb.is_closed
        assert not cb.is_open
        assert not cb.is_half_open

    async def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures"""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=3,
            timeout_seconds=30,
        )

        async def failing_function():
            raise Exception("Test failure")

        # Execute failing function multiple times
        for _ in range(3):
            with pytest.raises(Exception):
                await cb.call(failing_function)

        # Circuit should be open now
        assert cb.state == CircuitState.OPEN
        assert cb.is_open

        # Next call should be rejected
        with pytest.raises(CircuitBreakerError):
            await cb.call(failing_function)

    async def test_circuit_breaker_success_resets_failures(self):
        """Test successful calls reset failure count"""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=3,
            timeout_seconds=30,
        )

        async def failing_function():
            raise Exception("Test failure")

        async def successful_function():
            return "success"

        # One failure
        with pytest.raises(Exception):
            await cb.call(failing_function)

        assert cb._failure_count == 1

        # Success should reset
        result = await cb.call(successful_function)
        assert result == "success"
        assert cb._failure_count == 0

    async def test_circuit_breaker_metrics(self):
        """Test circuit breaker metrics tracking"""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=5,
        )

        async def successful_function():
            return "success"

        async def failing_function():
            raise Exception("Test failure")

        # Execute some calls
        await cb.call(successful_function)
        await cb.call(successful_function)

        with pytest.raises(Exception):
            await cb.call(failing_function)

        # Check metrics
        status = cb.get_status()
        metrics = status["metrics"]

        assert metrics["total_requests"] == 3
        assert metrics["successful_requests"] == 2
        assert metrics["failed_requests"] == 1
        assert metrics["success_rate"] == pytest.approx(2 / 3)

    async def test_circuit_breaker_reset(self):
        """Test manual circuit breaker reset"""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=2,
        )

        async def failing_function():
            raise Exception("Test failure")

        # Cause failures to open circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_function)

        assert cb.is_open

        # Reset circuit
        await cb.reset()

        assert cb.is_closed
        assert cb._failure_count == 0
