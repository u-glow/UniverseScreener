"""
Resilience Package - Error Handling and Fault Tolerance.

This package provides resilience patterns for robust operation:
    - ErrorHandler: Retry, circuit breaker, partial failure handling
    - Graceful degradation for transient failures

Design Principles:
    - Fail fast for permanent errors
    - Retry with backoff for transient errors
    - Circuit breaker for persistent failures
    - Continue with partial data when possible
"""

from universe_screener.resilience.error_handler import (
    ErrorHandler,
    CircuitBreakerOpen,
    RetryExhausted,
)

__all__ = ["ErrorHandler", "CircuitBreakerOpen", "RetryExhausted"]

