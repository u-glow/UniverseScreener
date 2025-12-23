"""
Unit Tests for DataValidator.

Test Aspects Covered:
    ✅ Business Logic: Market data, metadata validation
    ✅ Edge Cases: Empty data, extreme values
    ✅ Data Quality: Outlier detection
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

import pytest

from universe_screener.domain.value_objects import MarketData
from universe_screener.validation.data_validator import (
    DataValidator,
    DataValidatorConfig,
    ValidationResult,
)


def create_market_data(
    days: int = 30,
    base_price: float = 100.0,
    base_volume: int = 1_000_000,
) -> List[MarketData]:
    """Create sample market data."""
    data = []
    base_date = datetime(2024, 12, 15)

    for i in range(days):
        data.append(
            MarketData(
                date=base_date - timedelta(days=i),
                open=base_price,
                high=base_price * 1.02,
                low=base_price * 0.98,
                close=base_price,
                volume=base_volume,
            )
        )

    return data


class TestMarketDataValidation:
    """Test cases for market data validation."""

    def test_valid_market_data(self) -> None:
        """
        SCENARIO: Normal market data
        EXPECTED: Validation passes
        """
        # Arrange
        validator = DataValidator()
        market_data = {"AAPL": create_market_data()}

        # Act
        result = validator.validate_market_data(market_data)

        # Assert
        assert result.is_valid
        assert len(result.errors) == 0

    def test_negative_price_detected(self) -> None:
        """
        SCENARIO: Market data has negative price
        EXPECTED: Error recorded
        """
        # Arrange
        validator = DataValidator()
        bad_data = [
            MarketData(
                date=datetime(2024, 12, 15),
                open=-10.0,  # Negative!
                high=100.0,
                low=95.0,
                close=98.0,
                volume=1000,
            )
        ]

        # Act
        result = validator.validate_market_data({"BAD": bad_data})

        # Assert
        assert not result.is_valid
        assert any("Negative" in e and "open" in e for e in result.errors)

    def test_negative_volume_detected(self) -> None:
        """
        SCENARIO: Market data has negative volume
        EXPECTED: Error recorded
        """
        # Arrange
        validator = DataValidator()
        bad_data = [
            MarketData(
                date=datetime(2024, 12, 15),
                open=100.0,
                high=105.0,
                low=95.0,
                close=98.0,
                volume=-1000,  # Negative!
            )
        ]

        # Act
        result = validator.validate_market_data({"BAD": bad_data})

        # Assert
        assert not result.is_valid
        assert any("volume" in e.lower() for e in result.errors)

    def test_ohlc_inconsistency_detected(self) -> None:
        """
        SCENARIO: Low > High (invalid)
        EXPECTED: Error recorded
        """
        # Arrange
        validator = DataValidator()
        bad_data = [
            MarketData(
                date=datetime(2024, 12, 15),
                open=100.0,
                high=95.0,  # High < Low!
                low=105.0,
                close=98.0,
                volume=1000,
            )
        ]

        # Act
        result = validator.validate_market_data({"BAD": bad_data})

        # Assert
        assert not result.is_valid
        assert any("Low" in e and "High" in e for e in result.errors)

    def test_empty_market_data_warning(self) -> None:
        """
        SCENARIO: No market data for symbol
        EXPECTED: Warning recorded (not error)
        """
        # Arrange
        validator = DataValidator()

        # Act
        result = validator.validate_market_data({"EMPTY": []})

        # Assert
        assert result.is_valid  # Still valid, just a warning
        assert any("No market data" in w for w in result.warnings)


class TestMetadataValidation:
    """Test cases for metadata validation."""

    def test_valid_metadata(self) -> None:
        """
        SCENARIO: Complete metadata
        EXPECTED: Validation passes
        """
        # Arrange
        validator = DataValidator()
        metadata = {
            "AAPL": {
                "asset_type": "COMMON_STOCK",
                "exchange": "NASDAQ",
                "sector": "Technology",
            }
        }

        # Act
        result = validator.validate_metadata(metadata)

        # Assert
        assert result.is_valid
        assert len(result.warnings) == 0

    def test_missing_required_field(self) -> None:
        """
        SCENARIO: Required field missing
        EXPECTED: Warning recorded
        """
        # Arrange
        config = DataValidatorConfig(required_metadata_fields={"exchange", "sector"})
        validator = DataValidator(config)
        metadata = {
            "AAPL": {
                "exchange": "NASDAQ",
                # Missing: sector
            }
        }

        # Act
        result = validator.validate_metadata(metadata)

        # Assert
        assert result.is_valid  # Warnings don't fail validation
        assert any("sector" in w for w in result.warnings)


class TestOutlierDetection:
    """Test cases for outlier detection."""

    def test_no_outliers_in_normal_data(self) -> None:
        """
        SCENARIO: Normal market data with low variance
        EXPECTED: No outliers detected
        """
        # Arrange
        validator = DataValidator()
        market_data = {"AAPL": create_market_data(days=50, base_price=100.0)}

        # Act
        result = validator.detect_outliers(market_data)

        # Assert
        assert len(result.outliers) == 0

    def test_extreme_price_detected(self) -> None:
        """
        SCENARIO: One extreme price in data
        EXPECTED: Outlier detected
        """
        # Arrange
        config = DataValidatorConfig(outlier_sigma_threshold=3.0)
        validator = DataValidator(config)

        # Create normal data with one extreme value
        data = create_market_data(days=50, base_price=100.0)
        # Add extreme outlier
        data.append(
            MarketData(
                date=datetime(2024, 10, 1),
                open=1000.0,  # 10x normal price
                high=1000.0,
                low=1000.0,
                close=1000.0,
                volume=1_000_000,
            )
        )

        # Act
        result = validator.detect_outliers({"OUTLIER": data})

        # Assert
        assert "OUTLIER" in result.outliers
        assert any("close" in o for o in result.outliers["OUTLIER"])

    def test_too_few_data_points(self) -> None:
        """
        SCENARIO: Less than 10 data points
        EXPECTED: Skip outlier detection
        """
        # Arrange
        validator = DataValidator()
        market_data = {"SMALL": create_market_data(days=5)}

        # Act
        result = validator.detect_outliers(market_data)

        # Assert
        assert len(result.outliers) == 0


class TestValidateAll:
    """Test cases for combined validation."""

    def test_validate_all_passes(self) -> None:
        """
        SCENARIO: All data is valid
        EXPECTED: Combined validation passes
        """
        # Arrange
        config = DataValidatorConfig(raise_on_error=False, raise_on_warning=False)
        validator = DataValidator(config)
        market_data = {"AAPL": create_market_data()}
        metadata = {"AAPL": {"asset_type": "STOCK", "exchange": "NASDAQ"}}

        # Act
        result = validator.validate_all(market_data, metadata)

        # Assert
        assert result.is_valid

    def test_validate_all_raises_on_error(self) -> None:
        """
        SCENARIO: Data has errors and raise_on_error=True
        EXPECTED: ValueError raised
        """
        # Arrange
        config = DataValidatorConfig(raise_on_error=True)
        validator = DataValidator(config)
        bad_data = [
            MarketData(
                date=datetime(2024, 12, 15),
                open=-10.0,
                high=100.0,
                low=95.0,
                close=98.0,
                volume=1000,
            )
        ]

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            validator.validate_all({"BAD": bad_data}, {})

        assert "validation failed" in str(exc_info.value).lower()


class TestValidationResult:
    """Test cases for ValidationResult."""

    def test_add_error_marks_invalid(self) -> None:
        """
        SCENARIO: Error added
        EXPECTED: is_valid becomes False
        """
        result = ValidationResult()
        assert result.is_valid

        result.add_error("Something wrong")

        assert not result.is_valid
        assert "Something wrong" in result.errors

    def test_add_warning_stays_valid(self) -> None:
        """
        SCENARIO: Warning added
        EXPECTED: is_valid stays True
        """
        result = ValidationResult()
        result.add_warning("Minor issue")

        assert result.is_valid
        assert "Minor issue" in result.warnings

    def test_has_issues(self) -> None:
        """
        SCENARIO: Various issues
        EXPECTED: has_issues reflects correctly
        """
        result = ValidationResult()
        assert not result.has_issues

        result.add_warning("Warning")
        assert result.has_issues

