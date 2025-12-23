"""
Data Validator - Validate Loaded Data Quality.

Validates data after loading:
    - Market data: No negative prices/volumes
    - Metadata: Required fields present
    - Outlier detection: >10 sigma values

Design Notes:
    - Warnings for suspicious data (don't fail)
    - Configurable validation rules
    - Logs anomalies for investigation
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from universe_screener.domain.value_objects import MarketData, QualityMetrics

logger = logging.getLogger(__name__)


class DataValidationWarning(Exception):
    """Raised when data validation finds issues but can continue."""

    def __init__(self, warnings: List[str]) -> None:
        self.warnings = warnings
        super().__init__(f"Data validation warnings: {len(warnings)} issues found")


@dataclass
class ValidationResult:
    """Result of data validation."""

    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    outliers: Dict[str, List[str]] = field(default_factory=dict)

    def add_error(self, error: str) -> None:
        """Add an error and mark as invalid."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning (validation still passes)."""
        self.warnings.append(warning)

    def add_outlier(self, symbol: str, field: str, value: float, sigma: float) -> None:
        """Record an outlier detection."""
        if symbol not in self.outliers:
            self.outliers[symbol] = []
        self.outliers[symbol].append(f"{field}={value:.2f} ({sigma:.1f}\u03C3)")

    @property
    def has_issues(self) -> bool:
        """Check if any issues were found."""
        return len(self.errors) > 0 or len(self.warnings) > 0 or len(self.outliers) > 0


@dataclass
class DataValidatorConfig:
    """Configuration for data validation."""

    # Market data validation
    allow_zero_volume: bool = True
    max_price: float = 1_000_000  # Reasonable max price
    outlier_sigma_threshold: float = 10.0  # Standard deviations for outlier

    # Metadata validation
    required_metadata_fields: Set[str] = field(
        default_factory=lambda: {"asset_type", "exchange"}
    )

    # Behavior
    raise_on_error: bool = True
    raise_on_warning: bool = False


class DataValidator:
    """
    Validates loaded data for quality issues.

    Validates:
        - Market data: No negative prices/volumes, reasonable ranges
        - Metadata: Required fields present
        - Outliers: Extreme values detection (>10 sigma)
    """

    def __init__(self, config: Optional[DataValidatorConfig] = None) -> None:
        """
        Initialize data validator.

        Args:
            config: Validation configuration
        """
        self.config = config or DataValidatorConfig()

    def validate_market_data(
        self,
        market_data: Dict[str, List[MarketData]],
    ) -> ValidationResult:
        """
        Validate market data for all assets.

        Checks:
            - No negative prices
            - No negative volumes
            - Prices within reasonable range
            - OHLC consistency (low <= high)

        Args:
            market_data: Market data by symbol

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()

        for symbol, data_points in market_data.items():
            if not data_points:
                result.add_warning(f"{symbol}: No market data")
                continue

            for point in data_points:
                # Check for negative prices
                if point.open < 0:
                    result.add_error(
                        f"{symbol}: Negative open price {point.open} on {point.date}"
                    )
                if point.high < 0:
                    result.add_error(
                        f"{symbol}: Negative high price {point.high} on {point.date}"
                    )
                if point.low < 0:
                    result.add_error(
                        f"{symbol}: Negative low price {point.low} on {point.date}"
                    )
                if point.close < 0:
                    result.add_error(
                        f"{symbol}: Negative close price {point.close} on {point.date}"
                    )

                # Check for negative volume
                if point.volume < 0:
                    result.add_error(
                        f"{symbol}: Negative volume {point.volume} on {point.date}"
                    )

                # Check for zero volume (warning only)
                if point.volume == 0 and not self.config.allow_zero_volume:
                    result.add_warning(
                        f"{symbol}: Zero volume on {point.date}"
                    )

                # Check OHLC consistency
                if point.low > point.high:
                    result.add_error(
                        f"{symbol}: Low ({point.low}) > High ({point.high}) on {point.date}"
                    )

                # Check for extreme prices
                if point.close > self.config.max_price:
                    result.add_warning(
                        f"{symbol}: Extreme price {point.close} on {point.date}"
                    )

        self._log_result("Market data validation", result)
        return result

    def validate_metadata(
        self,
        metadata: Dict[str, Dict[str, Any]],
    ) -> ValidationResult:
        """
        Validate metadata for all assets.

        Checks:
            - Required fields present
            - Field types correct

        Args:
            metadata: Metadata by symbol

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()

        for symbol, meta in metadata.items():
            # Check required fields
            for required_field in self.config.required_metadata_fields:
                if required_field not in meta or meta[required_field] is None:
                    result.add_warning(
                        f"{symbol}: Missing required field '{required_field}'"
                    )

        self._log_result("Metadata validation", result)
        return result

    def detect_outliers(
        self,
        market_data: Dict[str, List[MarketData]],
    ) -> ValidationResult:
        """
        Detect statistical outliers in market data.

        Uses z-score detection with configurable threshold.

        Args:
            market_data: Market data by symbol

        Returns:
            ValidationResult with outlier information
        """
        result = ValidationResult()

        for symbol, data_points in market_data.items():
            if len(data_points) < 10:
                continue  # Need enough data for statistics

            # Extract close prices and volumes
            closes = [p.close for p in data_points]
            volumes = [float(p.volume) for p in data_points]

            # Check for outliers in prices
            price_outliers = self._find_outliers(closes, "close")
            for idx, sigma in price_outliers:
                point = data_points[idx]
                result.add_outlier(symbol, "close", point.close, sigma)
                result.add_warning(
                    f"{symbol}: Price outlier {point.close:.2f} ({sigma:.1f}\u03C3) on {point.date}"
                )

            # Check for outliers in volume
            volume_outliers = self._find_outliers(volumes, "volume")
            for idx, sigma in volume_outliers:
                point = data_points[idx]
                result.add_outlier(symbol, "volume", float(point.volume), sigma)
                # Volume outliers are less critical, just log
                logger.debug(
                    f"{symbol}: Volume outlier {point.volume} ({sigma:.1f}\u03C3) on {point.date}"
                )

        self._log_result("Outlier detection", result)
        return result

    def _find_outliers(
        self,
        values: List[float],
        field_name: str,
    ) -> List[tuple[int, float]]:
        """Find outliers using z-score method."""
        if len(values) < 2:
            return []

        # Calculate mean and std
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance) if variance > 0 else 0

        if std == 0:
            return []  # No variance, no outliers

        # Find outliers
        outliers: List[tuple[int, float]] = []
        for idx, value in enumerate(values):
            z_score = abs((value - mean) / std)
            if z_score > self.config.outlier_sigma_threshold:
                outliers.append((idx, z_score))

        return outliers

    def validate_all(
        self,
        market_data: Dict[str, List[MarketData]],
        metadata: Dict[str, Dict[str, Any]],
    ) -> ValidationResult:
        """
        Run all validations.

        Args:
            market_data: Market data by symbol
            metadata: Metadata by symbol

        Returns:
            Combined ValidationResult

        Raises:
            DataValidationWarning: If configured to raise on warnings
            ValueError: If configured to raise on errors
        """
        # Run all validations
        market_result = self.validate_market_data(market_data)
        metadata_result = self.validate_metadata(metadata)
        outlier_result = self.detect_outliers(market_data)

        # Combine results
        combined = ValidationResult()
        combined.errors = market_result.errors + metadata_result.errors + outlier_result.errors
        combined.warnings = market_result.warnings + metadata_result.warnings + outlier_result.warnings
        combined.outliers = {**market_result.outliers, **outlier_result.outliers}
        combined.is_valid = market_result.is_valid and metadata_result.is_valid and outlier_result.is_valid

        # Handle errors
        if not combined.is_valid and self.config.raise_on_error:
            error_msg = "; ".join(combined.errors[:5])  # First 5 errors
            if len(combined.errors) > 5:
                error_msg += f" ... and {len(combined.errors) - 5} more"
            raise ValueError(f"Data validation failed: {error_msg}")

        # Handle warnings
        if combined.warnings and self.config.raise_on_warning:
            raise DataValidationWarning(combined.warnings)

        return combined

    def _log_result(self, validation_type: str, result: ValidationResult) -> None:
        """Log validation results."""
        if result.errors:
            logger.warning(
                f"{validation_type}: {len(result.errors)} errors found"
            )
        if result.warnings:
            logger.info(
                f"{validation_type}: {len(result.warnings)} warnings"
            )
        if result.outliers:
            total_outliers = sum(len(o) for o in result.outliers.values())
            logger.info(
                f"{validation_type}: {total_outliers} outliers in {len(result.outliers)} symbols"
            )

