"""
Error Handler - Resilience Patterns for Fault Tolerance.

Provides:
    - Retry with exponential backoff
    - Circuit breaker pattern
    - Partial failure handling

Design Notes:
    - Configurable retry attempts and backoff
    - Circuit breaker prevents cascading failures
    - Partial success allows degraded operation
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


class RetryExhausted(Exception):
    """Raised when all retry attempts are exhausted."""
    pass


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Failures before opening
    recovery_timeout_seconds: float = 60.0  # Time before half-open
    success_threshold: int = 2  # Successes before closing


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    exponential_base: float = 2.0
    retryable_exceptions: tuple = (Exception,)


@dataclass
class CircuitBreakerState:
    """Mutable state for circuit breaker."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None


@dataclass
class PartialResult(Generic[T]):
    """Result of a partial success operation."""
    successful: List[T] = field(default_factory=list)
    failed: List[tuple[Any, Exception]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0 to 1.0)."""
        total = len(self.successful) + len(self.failed)
        if total == 0:
            return 1.0
        return len(self.successful) / total

    @property
    def has_failures(self) -> bool:
        """Check if any failures occurred."""
        return len(self.failed) > 0

    @property
    def all_failed(self) -> bool:
        """Check if all operations failed."""
        return len(self.successful) == 0 and len(self.failed) > 0


class ErrorHandler:
    """
    Provides resilience patterns for fault tolerance.

    Features:
        - Retry with exponential backoff
        - Circuit breaker pattern
        - Partial failure handling
    """

    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    ) -> None:
        """
        Initialize error handler.

        Args:
            retry_config: Configuration for retry logic
            circuit_breaker_config: Configuration for circuit breaker
        """
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig()
        self._circuit_states: Dict[str, CircuitBreakerState] = {}

    def retry(
        self,
        func: Callable[[], T],
        operation_name: str = "operation",
    ) -> T:
        """
        Execute function with retry and exponential backoff.

        Args:
            func: Function to execute
            operation_name: Name for logging

        Returns:
            Result of successful execution

        Raises:
            RetryExhausted: When all attempts fail
        """
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.retry_config.max_attempts + 1):
            try:
                result = func()
                if attempt > 1:
                    logger.info(
                        f"{operation_name} succeeded on attempt {attempt}"
                    )
                return result

            except self.retry_config.retryable_exceptions as e:
                last_exception = e
                if attempt < self.retry_config.max_attempts:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"{operation_name} failed (attempt {attempt}/{self.retry_config.max_attempts}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"{operation_name} failed after {attempt} attempts: {e}"
                    )

        raise RetryExhausted(
            f"{operation_name} failed after {self.retry_config.max_attempts} attempts"
        ) from last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff."""
        delay = self.retry_config.base_delay_seconds * (
            self.retry_config.exponential_base ** (attempt - 1)
        )
        return min(delay, self.retry_config.max_delay_seconds)

    def with_circuit_breaker(
        self,
        func: Callable[[], T],
        circuit_name: str,
    ) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            circuit_name: Unique name for this circuit

        Returns:
            Result of successful execution

        Raises:
            CircuitBreakerOpen: When circuit is open
        """
        state = self._get_circuit_state(circuit_name)

        # Check if circuit is open
        if state.state == CircuitState.OPEN:
            if self._should_attempt_recovery(state):
                state.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit {circuit_name} entering half-open state")
            else:
                raise CircuitBreakerOpen(
                    f"Circuit {circuit_name} is open, rejecting call"
                )

        try:
            result = func()
            self._record_success(state, circuit_name)
            return result

        except Exception as e:
            self._record_failure(state, circuit_name)
            raise

    def _get_circuit_state(self, circuit_name: str) -> CircuitBreakerState:
        """Get or create circuit breaker state."""
        if circuit_name not in self._circuit_states:
            self._circuit_states[circuit_name] = CircuitBreakerState()
        return self._circuit_states[circuit_name]

    def _should_attempt_recovery(self, state: CircuitBreakerState) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if state.last_failure_time is None:
            return True
        elapsed = datetime.now() - state.last_failure_time
        return elapsed.total_seconds() >= self.circuit_breaker_config.recovery_timeout_seconds

    def _record_success(self, state: CircuitBreakerState, circuit_name: str) -> None:
        """Record successful execution."""
        if state.state == CircuitState.HALF_OPEN:
            state.success_count += 1
            if state.success_count >= self.circuit_breaker_config.success_threshold:
                state.state = CircuitState.CLOSED
                state.failure_count = 0
                state.success_count = 0
                logger.info(f"Circuit {circuit_name} closed after recovery")
        else:
            state.failure_count = 0

    def _record_failure(self, state: CircuitBreakerState, circuit_name: str) -> None:
        """Record failed execution."""
        state.failure_count += 1
        state.last_failure_time = datetime.now()
        state.success_count = 0

        if state.state == CircuitState.HALF_OPEN:
            state.state = CircuitState.OPEN
            logger.warning(f"Circuit {circuit_name} re-opened after failed recovery")
        elif state.failure_count >= self.circuit_breaker_config.failure_threshold:
            state.state = CircuitState.OPEN
            logger.warning(
                f"Circuit {circuit_name} opened after {state.failure_count} failures"
            )

    def handle_partial_failure(
        self,
        items: List[Any],
        processor: Callable[[Any], T],
        min_success_rate: float = 0.5,
        operation_name: str = "batch operation",
    ) -> PartialResult[T]:
        """
        Process items, allowing partial failures.

        Args:
            items: Items to process
            processor: Function to process each item
            min_success_rate: Minimum success rate to continue (0.0-1.0)
            operation_name: Name for logging

        Returns:
            PartialResult with successful and failed items

        Raises:
            RuntimeError: If success rate falls below minimum
        """
        result: PartialResult[T] = PartialResult()

        for item in items:
            try:
                processed = processor(item)
                result.successful.append(processed)
            except Exception as e:
                result.failed.append((item, e))
                logger.warning(f"{operation_name} failed for {item}: {e}")

        if result.success_rate < min_success_rate:
            raise RuntimeError(
                f"{operation_name} success rate {result.success_rate:.1%} "
                f"below minimum {min_success_rate:.1%}"
            )

        if result.has_failures:
            logger.warning(
                f"{operation_name} completed with {len(result.failed)} failures "
                f"({result.success_rate:.1%} success rate)"
            )

        return result

    def reset_circuit(self, circuit_name: str) -> None:
        """Reset a circuit breaker to closed state."""
        if circuit_name in self._circuit_states:
            self._circuit_states[circuit_name] = CircuitBreakerState()
            logger.info(f"Circuit {circuit_name} reset to closed state")

    def get_circuit_state(self, circuit_name: str) -> CircuitState:
        """Get current state of a circuit breaker."""
        return self._get_circuit_state(circuit_name).state

