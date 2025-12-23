"""
Screening Pipeline - Main Orchestrator.

The ScreeningPipeline coordinates the entire screening workflow.
Includes resilience (Phase 1) and observability (Phase 2) layers.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Protocol

from universe_screener.domain.entities import (
    Asset,
    AssetClass,
    ScreeningRequest,
    ScreeningResult,
    StageResult,
)
from universe_screener.domain.value_objects import (
    MarketData,
    MarketDataDict,
    MetadataDict,
    QualityMetrics,
    QualityMetricsDict,
)
from universe_screener.pipeline.data_context import DataContext
from universe_screener.config.models import ScreeningConfig

logger = logging.getLogger(__name__)


class UniverseProviderProtocol(Protocol):
    """Protocol for universe providers."""

    def get_assets(self, date: datetime, asset_class: AssetClass) -> List[Asset]:
        ...

    def bulk_load_market_data(
        self, assets: List[Asset], start_date: datetime, end_date: datetime
    ) -> MarketDataDict:
        ...

    def bulk_load_metadata(
        self, assets: List[Asset], date: datetime
    ) -> MetadataDict:
        ...

    def check_data_availability(
        self, assets: List[Asset], date: datetime, lookback_days: int
    ) -> QualityMetricsDict:
        ...


class FilterStageProtocol(Protocol):
    """Protocol for filter stages."""

    @property
    def name(self) -> str:
        ...

    def apply(
        self, assets: List[Asset], date: datetime, context: DataContext
    ) -> Any:
        ...


class AuditLoggerProtocol(Protocol):
    """Protocol for audit loggers."""

    def set_correlation_id(self, correlation_id: str) -> None:
        ...

    def log_stage_start(
        self, stage_name: str, input_count: int, metadata: Optional[Dict] = None
    ) -> None:
        ...

    def log_stage_end(
        self,
        stage_name: str,
        output_count: int,
        duration_seconds: float,
        metadata: Optional[Dict] = None,
    ) -> None:
        ...

    def log_asset_filtered(self, asset: Asset, stage_name: str, reason: str) -> None:
        ...

    def log_anomaly(
        self, message: str, severity: str, context: Optional[Dict] = None
    ) -> None:
        ...


class MetricsCollectorProtocol(Protocol):
    """Protocol for metrics collectors."""

    def record_timing(
        self, name: str, duration_seconds: float, tags: Optional[Dict] = None
    ) -> None:
        ...

    def record_count(
        self, name: str, value: int, tags: Optional[Dict] = None
    ) -> None:
        ...

    def record_gauge(
        self, name: str, value: float, tags: Optional[Dict] = None
    ) -> None:
        ...

    def get_metrics(self) -> Dict[str, Any]:
        ...


class ErrorHandlerProtocol(Protocol):
    """Protocol for error handlers."""

    def retry(self, func: Any, operation_name: str) -> Any:
        ...

    def with_circuit_breaker(self, func: Any, circuit_name: str) -> Any:
        ...


class RequestValidatorProtocol(Protocol):
    """Protocol for request validators."""

    def validate(self, request: ScreeningRequest, config: ScreeningConfig) -> None:
        ...


class DataValidatorProtocol(Protocol):
    """Protocol for data validators."""

    def validate_all(
        self, market_data: MarketDataDict, metadata: MetadataDict
    ) -> Any:
        ...


class HealthMonitorProtocol(Protocol):
    """Protocol for health monitors (Phase 2)."""

    def check_pre_screening(self) -> Any:
        ...

    def check_post_load(self, context: DataContext) -> Any:
        ...

    def check_post_filtering(self, result: ScreeningResult) -> Any:
        ...


class SnapshotManagerProtocol(Protocol):
    """Protocol for snapshot managers (Phase 2)."""

    def create_snapshot(
        self, screening_date: datetime, asset_class: AssetClass, metadata: Optional[Dict] = None
    ) -> str:
        ...

    def get_current_snapshot_id(self) -> Optional[str]:
        ...


class VersionManagerProtocol(Protocol):
    """Protocol for version managers (Phase 2)."""

    def get_version_metadata(self, config: Optional[Any] = None) -> Any:
        ...

    def register_filters(self, filters: List[Any]) -> None:
        ...


class ScreeningPipeline:
    """Main orchestrator for the screening workflow."""

    def __init__(
        self,
        provider: UniverseProviderProtocol,
        filters: List[FilterStageProtocol],
        config: ScreeningConfig,
        audit_logger: AuditLoggerProtocol,
        metrics_collector: MetricsCollectorProtocol,
        error_handler: Optional[ErrorHandlerProtocol] = None,
        request_validator: Optional[RequestValidatorProtocol] = None,
        data_validator: Optional[DataValidatorProtocol] = None,
        health_monitor: Optional[HealthMonitorProtocol] = None,
        snapshot_manager: Optional[SnapshotManagerProtocol] = None,
        version_manager: Optional[VersionManagerProtocol] = None,
    ) -> None:
        """
        Initialize pipeline with all dependencies.

        Args:
            provider: Data access provider
            filters: Ordered list of filter stages
            config: Screening configuration
            audit_logger: For audit trail
            metrics_collector: For performance metrics
            error_handler: For retry/circuit breaker (optional, Phase 1)
            request_validator: For request validation (optional, Phase 1)
            data_validator: For data validation (optional, Phase 1)
            health_monitor: For health checks (optional, Phase 2)
            snapshot_manager: For point-in-time consistency (optional, Phase 2)
            version_manager: For version tracking (optional, Phase 2)
        """
        self.provider = provider
        self.filters = filters
        self.config = config
        self.audit_logger = audit_logger
        self.metrics_collector = metrics_collector
        self.error_handler = error_handler
        self.request_validator = request_validator
        self.data_validator = data_validator
        self.health_monitor = health_monitor
        self.snapshot_manager = snapshot_manager
        self.version_manager = version_manager

        # Register filter versions if version manager available
        if self.version_manager:
            self.version_manager.register_filters(filters)

    def screen(
        self,
        date: datetime,
        asset_class: AssetClass,
        config_override: Optional[dict] = None,
    ) -> ScreeningResult:
        """
        Execute the screening workflow.

        Args:
            date: Point-in-time for screening
            asset_class: Asset class to screen
            config_override: Optional config overrides

        Returns:
            ScreeningResult with filtered assets and audit trail

        Raises:
            ValidationError: If request validation fails
            RetryExhausted: If data loading fails after retries
            CircuitBreakerOpen: If provider circuit is open
        """
        start_time = time.perf_counter()
        correlation_id = str(uuid.uuid4())
        self.audit_logger.set_correlation_id(correlation_id)

        # Phase 2: Pre-screening health check
        if self.health_monitor:
            pre_health = self.health_monitor.check_pre_screening()
            if not pre_health.is_healthy:
                logger.warning(f"Pre-screening health check failed: {pre_health.summary}")

        # Phase 2: Create snapshot for point-in-time consistency
        # NOTE: Currently for audit trail only. For full point-in-time consistency,
        # the provider would need to receive snapshot_id and query a versioned data store.
        # TODO (STABILIZATION): Extend UniverseProviderProtocol with snapshot_id parameter
        snapshot_id: Optional[str] = None
        if self.snapshot_manager:
            snapshot_id = self.snapshot_manager.create_snapshot(
                screening_date=date,
                asset_class=asset_class,
                metadata={"correlation_id": correlation_id},
            )

        # 1. Create request
        request = ScreeningRequest(
            date=date,
            asset_class=asset_class,
            config_override=config_override,
            correlation_id=correlation_id,
        )

        # 2. Validate request (Phase 1)
        if self.request_validator:
            self.request_validator.validate(request, self.config)
            logger.debug(f"Request validated: {correlation_id}")

        # 3. Load data (with optional error handling)
        context = self._load_data(request)

        # Phase 2: Post-load health check
        if self.health_monitor:
            post_load_health = self.health_monitor.check_post_load(context)
            if not post_load_health.is_healthy:
                logger.warning(f"Post-load health check failed: {post_load_health.summary}")

        # 4. Validate data (Phase 1)
        if self.data_validator:
            validation_result = self.data_validator.validate_all(
                context._market_data, context._metadata
            )
            if validation_result.has_issues:
                self.audit_logger.log_anomaly(
                    f"Data validation: {len(validation_result.warnings)} warnings, "
                    f"{len(validation_result.errors)} errors",
                    severity="WARNING" if validation_result.is_valid else "ERROR",
                    context={"outliers": len(validation_result.outliers)},
                )

        # 5. Execute filters
        current_assets = context.assets
        audit_trail: List[StageResult] = []

        for filter_stage in self.filters:
            stage_result, current_assets = self._execute_stage(
                filter_stage, current_assets, date, context
            )
            audit_trail.append(stage_result)

        # 6. Record total time
        total_duration = time.perf_counter() - start_time
        self.metrics_collector.record_timing(
            "screening_total_seconds",
            total_duration,
            {"asset_class": asset_class.value},
        )

        # 7. Build result
        result = ScreeningResult(
            request=request,
            input_universe=context.assets,
            output_universe=current_assets,
            audit_trail=audit_trail,
            metrics=self.metrics_collector.get_metrics(),
            metadata=self._build_metadata(correlation_id, total_duration, snapshot_id),
        )

        # Phase 2: Post-filtering health check
        if self.health_monitor:
            post_filter_health = self.health_monitor.check_post_filtering(result)
            if not post_filter_health.is_healthy:
                logger.warning(f"Post-filtering health check failed: {post_filter_health.summary}")

        return result

    def _load_data(self, request: ScreeningRequest) -> DataContext:
        """Bulk load data into DataContext."""
        load_start = time.perf_counter()

        # Calculate date range
        lookback_days = self.config.global_settings.default_lookback_days
        start_date = request.date - timedelta(days=lookback_days)
        end_date = request.date

        # Get assets (with optional retry/circuit breaker)
        if self.error_handler:
            assets = self.error_handler.retry(
                lambda: self.provider.get_assets(request.date, request.asset_class),
                operation_name="get_assets",
            )
        else:
            assets = self.provider.get_assets(request.date, request.asset_class)

        # Bulk load market data (with optional retry)
        if self.error_handler:
            market_data = self.error_handler.with_circuit_breaker(
                lambda: self.provider.bulk_load_market_data(assets, start_date, end_date),
                circuit_name="market_data_provider",
            )
        else:
            market_data = self.provider.bulk_load_market_data(assets, start_date, end_date)

        # Bulk load metadata
        if self.error_handler:
            metadata = self.error_handler.retry(
                lambda: self.provider.bulk_load_metadata(assets, request.date),
                operation_name="bulk_load_metadata",
            )
        else:
            metadata = self.provider.bulk_load_metadata(assets, request.date)

        # Check data availability
        quality_metrics = self.provider.check_data_availability(
            assets, request.date, lookback_days
        )

        load_duration = time.perf_counter() - load_start
        self.metrics_collector.record_timing("data_load_seconds", load_duration)
        self.metrics_collector.record_count("input_assets_total", len(assets))

        return DataContext(
            assets=assets,
            market_data=market_data,
            metadata=metadata,
            quality_metrics=quality_metrics,
        )

    def _execute_stage(
        self,
        stage: FilterStageProtocol,
        assets: List[Asset],
        date: datetime,
        context: DataContext,
    ) -> tuple[StageResult, List[Asset]]:
        """Execute a single filter stage."""
        stage_start = time.perf_counter()

        self.audit_logger.log_stage_start(stage.name, len(assets))

        # Apply filter
        filter_result = stage.apply(assets, date, context)

        stage_duration = time.perf_counter() - stage_start

        # Log filtered assets
        for symbol, reason in filter_result.rejection_reasons.items():
            asset = context.get_asset(symbol)
            if asset:
                self.audit_logger.log_asset_filtered(asset, stage.name, reason)

        self.audit_logger.log_stage_end(
            stage.name, filter_result.passed_count, stage_duration
        )

        # Record metrics
        self.metrics_collector.record_timing(
            "stage_duration_seconds",
            stage_duration,
            {"stage": stage.name},
        )
        self.metrics_collector.record_count(
            "assets_filtered_total",
            filter_result.rejected_count,
            {"stage": stage.name},
        )

        # Create stage result
        stage_result = StageResult(
            stage_name=stage.name,
            input_count=len(assets),
            output_count=filter_result.passed_count,
            duration_seconds=stage_duration,
            filtered_assets=filter_result.rejected_assets,
            filter_reasons=filter_result.rejection_reasons,
        )

        # Get assets for next stage
        passed_assets = context.get_assets_by_symbols(filter_result.passed_assets)

        return stage_result, passed_assets

    def _build_metadata(
        self,
        correlation_id: str,
        duration: float,
        snapshot_id: Optional[str] = None,
    ) -> dict:
        """Build result metadata."""
        metadata = {
            "correlation_id": correlation_id,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "version": "0.3.0",  # Phase 2 with observability
        }

        # Add snapshot ID if available
        if snapshot_id:
            metadata["snapshot_id"] = snapshot_id

        # Add version metadata if version manager available
        if self.version_manager:
            version_meta = self.version_manager.get_version_metadata(self.config)
            metadata["code_version"] = version_meta.code_version
            metadata["config_hash"] = version_meta.config_hash
            if version_meta.git_sha:
                metadata["git_sha"] = version_meta.git_sha

        return metadata
