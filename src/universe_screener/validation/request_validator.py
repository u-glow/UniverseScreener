"""
Request Validator - Validate Screening Requests.

Validates requests before expensive data loading:
    - Date not in future
    - Date not before 1970
    - AssetClass is supported
    - Config complete for requested AssetClass

Design Notes:
    - Fail-fast principle
    - Clear error messages
    - Configurable supported asset classes
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional, Set

from universe_screener.domain.entities import AssetClass, ScreeningRequest
from universe_screener.config.models import ScreeningConfig

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when request validation fails."""

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


class RequestValidator:
    """
    Validates screening requests before processing.

    Validates:
        - Date is valid (not future, not pre-1970)
        - AssetClass is supported
        - Config is complete for requested AssetClass
    """

    # Minimum valid date (Unix epoch)
    MIN_DATE = datetime(1970, 1, 1)

    def __init__(
        self,
        supported_asset_classes: Optional[Set[AssetClass]] = None,
    ) -> None:
        """
        Initialize request validator.

        Args:
            supported_asset_classes: Set of supported asset classes.
                                     Defaults to all AssetClass values.
        """
        self.supported_asset_classes = supported_asset_classes or set(AssetClass)

    def validate(
        self,
        request: ScreeningRequest,
        config: ScreeningConfig,
    ) -> None:
        """
        Validate a screening request.

        Args:
            request: The screening request to validate
            config: The screening configuration

        Raises:
            ValidationError: If validation fails
        """
        errors: List[str] = []

        # Validate date
        date_error = self._validate_date(request.date)
        if date_error:
            errors.append(date_error)

        # Validate asset class
        asset_class_error = self._validate_asset_class(request.asset_class)
        if asset_class_error:
            errors.append(asset_class_error)

        # Validate config completeness
        config_errors = self._validate_config_for_asset_class(
            request.asset_class, config
        )
        errors.extend(config_errors)

        # Raise if any errors
        if errors:
            error_message = "; ".join(errors)
            logger.error(f"Request validation failed: {error_message}")
            raise ValidationError(error_message)

        logger.debug(
            f"Request validated: date={request.date}, "
            f"asset_class={request.asset_class}"
        )

    def _validate_date(self, date: datetime) -> Optional[str]:
        """Validate the screening date."""
        now = datetime.now()

        if date > now:
            return f"Date {date.isoformat()} is in the future"

        if date < self.MIN_DATE:
            return f"Date {date.isoformat()} is before minimum {self.MIN_DATE.isoformat()}"

        return None

    def _validate_asset_class(self, asset_class: AssetClass) -> Optional[str]:
        """Validate the asset class is supported."""
        if asset_class not in self.supported_asset_classes:
            supported = ", ".join(ac.value for ac in self.supported_asset_classes)
            return f"AssetClass {asset_class.value} not supported. Supported: {supported}"

        return None

    def _validate_config_for_asset_class(
        self,
        asset_class: AssetClass,
        config: ScreeningConfig,
    ) -> List[str]:
        """Validate config is complete for the asset class."""
        errors: List[str] = []

        # Check structural filter config
        if config.structural_filter.enabled:
            if not config.structural_filter.allowed_exchanges:
                errors.append("structural_filter.allowed_exchanges is empty")
            if not config.structural_filter.allowed_asset_types:
                errors.append("structural_filter.allowed_asset_types is empty")

        # Check liquidity filter config based on asset class
        if config.liquidity_filter.enabled:
            if asset_class == AssetClass.STOCK:
                stock_config = config.liquidity_filter.stock
                if stock_config.min_avg_dollar_volume_usd < 0:
                    errors.append(
                        "liquidity_filter.stock.min_avg_dollar_volume_usd must be >= 0"
                    )
                if not (0 <= stock_config.min_trading_days_pct <= 1):
                    errors.append(
                        "liquidity_filter.stock.min_trading_days_pct must be between 0 and 1"
                    )

            elif asset_class == AssetClass.CRYPTO:
                crypto_config = config.liquidity_filter.crypto
                if crypto_config.max_slippage_pct < 0:
                    errors.append(
                        "liquidity_filter.crypto.max_slippage_pct must be >= 0"
                    )

            elif asset_class == AssetClass.FOREX:
                forex_config = config.liquidity_filter.forex
                if forex_config.max_spread_pips < 0:
                    errors.append(
                        "liquidity_filter.forex.max_spread_pips must be >= 0"
                    )

        # Check data quality filter config
        if config.data_quality_filter.enabled:
            if config.data_quality_filter.max_missing_days < 0:
                errors.append("data_quality_filter.max_missing_days must be >= 0")

        return errors

    def validate_date_only(self, date: datetime) -> None:
        """
        Validate just the date (utility method).

        Args:
            date: Date to validate

        Raises:
            ValidationError: If date is invalid
        """
        error = self._validate_date(date)
        if error:
            raise ValidationError(error, field="date")

