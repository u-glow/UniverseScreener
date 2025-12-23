"""
Unit Tests for ErrorHandler.

Test Aspects Covered:
    ✅ Business Logic: Retry, circuit breaker, partial failure handling
    ✅ Edge Cases: Immediate success, all failures
"""

from __future__ import annotations

import time
from unittest.mock import Mock

import pytest

from universe_screener.resilience.error_handler import (
    ErrorHandler,
    RetryConfig,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerOpen,
    RetryExhausted,
    PartialResult,
)


class TestRetry:
    """Test cases for retry logic."""

    def test_succeeds_on_first_attempt(self) -> None:
        """
        SCENARIO: Function succeeds on first attempt
        EXPECTED: Result returned, no retries
        """
        # Arrange
        handler = ErrorHandler()
        mock_func = Mock(return_value="success")

        # Act
        result = handler.retry(mock_func, "test_op")

        # Assert
        assert result == "success"
        assert mock_func.call_count == 1

    def test_succeeds_after_retries(self) -> None:
        """
        SCENARIO: Function fails twice, succeeds on third attempt
        EXPECTED: Result returned after retries
        """
        # Arrange
        config = RetryConfig(max_attempts=3, base_delay_seconds=0.01)
        handler = ErrorHandler(retry_config=config)

        call_count = 0

        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Transient error")
            return "success"

        # Act
        result = handler.retry(flaky_func, "flaky_op")

        # Assert
        assert result == "success"
        assert call_count == 3

    def test_raises_after_max_attempts(self) -> None:
        """
        SCENARIO: Function fails all attempts
        EXPECTED: RetryExhausted raised
        """
        # Arrange
        config = RetryConfig(max_attempts=3, base_delay_seconds=0.01)
        handler = ErrorHandler(retry_config=config)
        mock_func = Mock(side_effect=ValueError("Permanent error"))

        # Act & Assert
        with pytest.raises(RetryExhausted) as exc_info:
            handler.retry(mock_func, "failing_op")

        assert "failed after 3 attempts" in str(exc_info.value)
        assert mock_func.call_count == 3

    def test_exponential_backoff(self) -> None:
        """
        SCENARIO: Multiple retries
        EXPECTED: Delay increases exponentially
        """
        # Arrange
        config = RetryConfig(
            max_attempts=3,
            base_delay_seconds=0.1,
            exponential_base=2.0,
        )
        handler = ErrorHandler(retry_config=config)

        # Act
        delay1 = handler._calculate_delay(1)
        delay2 = handler._calculate_delay(2)
        delay3 = handler._calculate_delay(3)

        # Assert
        assert delay1 == pytest.approx(0.1, rel=0.01)
        assert delay2 == pytest.approx(0.2, rel=0.01)
        assert delay3 == pytest.approx(0.4, rel=0.01)

    def test_max_delay_cap(self) -> None:
        """
        SCENARIO: Calculated delay exceeds max
        EXPECTED: Delay capped at max_delay_seconds
        """
        # Arrange
        config = RetryConfig(
            max_attempts=10,
            base_delay_seconds=1.0,
            max_delay_seconds=5.0,
            exponential_base=2.0,
        )
        handler = ErrorHandler(retry_config=config)

        # Act
        delay = handler._calculate_delay(10)  # Would be 512s without cap

        # Assert
        assert delay == 5.0


class TestCircuitBreaker:
    """Test cases for circuit breaker."""

    def test_closed_allows_calls(self) -> None:
        """
        SCENARIO: Circuit is closed (normal operation)
        EXPECTED: Calls pass through
        """
        # Arrange
        handler = ErrorHandler()
        mock_func = Mock(return_value="success")

        # Act
        result = handler.with_circuit_breaker(mock_func, "test_circuit")

        # Assert
        assert result == "success"
        assert handler.get_circuit_state("test_circuit") == CircuitState.CLOSED

    def test_opens_after_failures(self) -> None:
        """
        SCENARIO: Multiple consecutive failures
        EXPECTED: Circuit opens after threshold
        """
        # Arrange
        config = CircuitBreakerConfig(failure_threshold=3)
        handler = ErrorHandler(circuit_breaker_config=config)

        def failing_func():
            raise ValueError("Error")

        # Act - trigger failures
        for _ in range(3):
            try:
                handler.with_circuit_breaker(failing_func, "test_circuit")
            except ValueError:
                pass

        # Assert
        assert handler.get_circuit_state("test_circuit") == CircuitState.OPEN

    def test_open_rejects_calls(self) -> None:
        """
        SCENARIO: Circuit is open
        EXPECTED: Calls rejected with CircuitBreakerOpen
        """
        # Arrange
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout_seconds=60)
        handler = ErrorHandler(circuit_breaker_config=config)

        # Open the circuit
        try:
            handler.with_circuit_breaker(
                Mock(side_effect=ValueError()), "test_circuit"
            )
        except ValueError:
            pass

        # Act & Assert
        with pytest.raises(CircuitBreakerOpen):
            handler.with_circuit_breaker(Mock(), "test_circuit")

    def test_reset_circuit(self) -> None:
        """
        SCENARIO: Circuit is reset
        EXPECTED: Circuit returns to closed state
        """
        # Arrange
        config = CircuitBreakerConfig(failure_threshold=1)
        handler = ErrorHandler(circuit_breaker_config=config)

        # Open the circuit
        try:
            handler.with_circuit_breaker(
                Mock(side_effect=ValueError()), "test_circuit"
            )
        except ValueError:
            pass

        assert handler.get_circuit_state("test_circuit") == CircuitState.OPEN

        # Act
        handler.reset_circuit("test_circuit")

        # Assert
        assert handler.get_circuit_state("test_circuit") == CircuitState.CLOSED


class TestPartialFailure:
    """Test cases for partial failure handling."""

    def test_all_succeed(self) -> None:
        """
        SCENARIO: All items process successfully
        EXPECTED: Full success, no failures
        """
        # Arrange
        handler = ErrorHandler()
        items = [1, 2, 3, 4, 5]
        processor = lambda x: x * 2

        # Act
        result = handler.handle_partial_failure(items, processor)

        # Assert
        assert result.successful == [2, 4, 6, 8, 10]
        assert result.failed == []
        assert result.success_rate == 1.0

    def test_partial_success(self) -> None:
        """
        SCENARIO: Some items fail
        EXPECTED: Continues with successful items
        """
        # Arrange
        handler = ErrorHandler()
        items = [1, 2, 0, 4, 5]  # 0 will cause division error

        def processor(x):
            return 10 // x  # Will fail for x=0

        # Act
        result = handler.handle_partial_failure(
            items, processor, min_success_rate=0.5
        )

        # Assert
        assert len(result.successful) == 4
        assert len(result.failed) == 1
        assert result.success_rate == 0.8

    def test_below_min_success_rate(self) -> None:
        """
        SCENARIO: Success rate below minimum
        EXPECTED: RuntimeError raised
        """
        # Arrange
        handler = ErrorHandler()
        items = [1, 2, 3]
        processor = Mock(side_effect=ValueError("Error"))

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            handler.handle_partial_failure(
                items, processor, min_success_rate=0.5
            )

        assert "success rate 0.0%" in str(exc_info.value)


class TestPartialResult:
    """Test cases for PartialResult."""

    def test_success_rate_calculation(self) -> None:
        """
        SCENARIO: Mixed results
        EXPECTED: Correct success rate
        """
        result = PartialResult(
            successful=[1, 2, 3],
            failed=[(4, ValueError()), (5, ValueError())],
        )

        assert result.success_rate == 0.6

    def test_empty_result(self) -> None:
        """
        SCENARIO: No items processed
        EXPECTED: Success rate is 1.0
        """
        result = PartialResult()

        assert result.success_rate == 1.0
        assert not result.has_failures
        assert not result.all_failed

