"""
Unit Tests for RequestValidator.

Test Aspects Covered:
    ✅ Business Logic: Date, asset class, config validation
    ✅ Edge Cases: Boundary dates, unsupported asset classes
"""

from __future__ import annotations

from datetime import datetime

import pytest

from universe_screener.domain.entities import AssetClass, ScreeningRequest
from universe_screener.config.models import ScreeningConfig
from universe_screener.validation.request_validator import (
    RequestValidator,
    ValidationError,
)


@pytest.fixture
def validator() -> RequestValidator:
    """Create request validator."""
    return RequestValidator()


@pytest.fixture
def default_config() -> ScreeningConfig:
    """Create default config."""
    return ScreeningConfig()


def create_request(
    date: datetime,
    asset_class: AssetClass = AssetClass.STOCK,
) -> ScreeningRequest:
    """Helper to create screening requests."""
    return ScreeningRequest(
        date=date,
        asset_class=asset_class,
        correlation_id="test-123",
    )


class TestDateValidation:
    """Test cases for date validation."""

    def test_valid_past_date(
        self,
        validator: RequestValidator,
        default_config: ScreeningConfig,
    ) -> None:
        """
        SCENARIO: Date is in the past
        EXPECTED: Validation passes
        """
        # Arrange
        request = create_request(datetime(2024, 1, 15))

        # Act & Assert (no exception)
        validator.validate(request, default_config)

    def test_future_date_rejected(
        self,
        validator: RequestValidator,
        default_config: ScreeningConfig,
    ) -> None:
        """
        SCENARIO: Date is in the future
        EXPECTED: ValidationError raised
        """
        # Arrange
        future_date = datetime(2099, 12, 31)
        request = create_request(future_date)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            validator.validate(request, default_config)

        assert "future" in str(exc_info.value).lower()

    def test_pre_1970_date_rejected(
        self,
        validator: RequestValidator,
        default_config: ScreeningConfig,
    ) -> None:
        """
        SCENARIO: Date is before 1970 (Unix epoch)
        EXPECTED: ValidationError raised
        """
        # Arrange
        old_date = datetime(1960, 1, 1)
        request = create_request(old_date)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            validator.validate(request, default_config)

        assert "before" in str(exc_info.value).lower()

    def test_boundary_date_1970(
        self,
        validator: RequestValidator,
        default_config: ScreeningConfig,
    ) -> None:
        """
        SCENARIO: Date is exactly 1970-01-01
        EXPECTED: Validation passes
        """
        # Arrange
        request = create_request(datetime(1970, 1, 1))

        # Act & Assert (no exception)
        validator.validate(request, default_config)


class TestAssetClassValidation:
    """Test cases for asset class validation."""

    def test_supported_asset_class(
        self,
        default_config: ScreeningConfig,
    ) -> None:
        """
        SCENARIO: Asset class is supported
        EXPECTED: Validation passes
        """
        # Arrange
        validator = RequestValidator(supported_asset_classes={AssetClass.STOCK})
        request = create_request(datetime(2024, 1, 15), AssetClass.STOCK)

        # Act & Assert (no exception)
        validator.validate(request, default_config)

    def test_unsupported_asset_class(
        self,
        default_config: ScreeningConfig,
    ) -> None:
        """
        SCENARIO: Asset class is not supported
        EXPECTED: ValidationError raised
        """
        # Arrange - only support STOCK
        validator = RequestValidator(supported_asset_classes={AssetClass.STOCK})
        request = create_request(datetime(2024, 1, 15), AssetClass.CRYPTO)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            validator.validate(request, default_config)

        assert "CRYPTO" in str(exc_info.value)
        assert "not supported" in str(exc_info.value).lower()


class TestConfigValidation:
    """Test cases for config validation."""

    def test_valid_config(
        self,
        validator: RequestValidator,
    ) -> None:
        """
        SCENARIO: Config is complete and valid
        EXPECTED: Validation passes
        """
        # Arrange
        config = ScreeningConfig()
        request = create_request(datetime(2024, 1, 15))

        # Act & Assert (no exception)
        validator.validate(request, config)

    def test_empty_exchanges_warning(
        self,
        validator: RequestValidator,
    ) -> None:
        """
        SCENARIO: allowed_exchanges is empty
        EXPECTED: ValidationError raised
        """
        # Arrange
        config = ScreeningConfig()
        config.structural_filter.allowed_exchanges = []
        request = create_request(datetime(2024, 1, 15))

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            validator.validate(request, config)

        assert "allowed_exchanges" in str(exc_info.value)


class TestValidateDateOnly:
    """Test cases for validate_date_only utility."""

    def test_valid_date(self) -> None:
        """
        SCENARIO: Valid date
        EXPECTED: No exception
        """
        validator = RequestValidator()
        validator.validate_date_only(datetime(2024, 1, 15))

    def test_invalid_date_raises(self) -> None:
        """
        SCENARIO: Future date
        EXPECTED: ValidationError raised
        """
        validator = RequestValidator()

        with pytest.raises(ValidationError) as exc_info:
            validator.validate_date_only(datetime(2099, 12, 31))

        assert exc_info.value.field == "date"

