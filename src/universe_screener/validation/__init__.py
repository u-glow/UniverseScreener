"""
Validation Package - Input and Data Validation.

This package provides validation for:
    - RequestValidator: Validate screening requests before processing
    - DataValidator: Validate loaded data quality

Design Principles:
    - Fail fast on invalid input
    - Clear, actionable error messages
    - Configurable validation rules
"""

from universe_screener.validation.request_validator import (
    RequestValidator,
    ValidationError,
)
from universe_screener.validation.data_validator import (
    DataValidator,
    DataValidationWarning,
)

__all__ = [
    "RequestValidator",
    "ValidationError",
    "DataValidator",
    "DataValidationWarning",
]

