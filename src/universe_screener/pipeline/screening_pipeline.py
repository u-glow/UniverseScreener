"""
Screening Pipeline - Main Orchestrator.

The ScreeningPipeline coordinates the entire screening workflow.
"""

from __future__ import annotations

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
from universe_screener.pipeline.data_context import DataContext
from universe_screener.config.models import ScreeningConfig


class UniverseProviderProtocol(Protocol):
    """Protocol for universe providers."""

    def get_assets(self, date: datetime, asset_class: AssetClass) -> List[Asset]:
        ...

    def bulk_load_market_data(
        self, assets: List[Asset], start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        ...

    def bulk_load_metadata(
        self, assets: List[Asset], date: datetime
    ) -> Dict[str, Any]:
        ...

    def check_data_availability(
        self, assets: List[Asset], date: datetime, lookback_days: int
    ) -> Dict[str, Any]:
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


class ScreeningPipeline:
    """Main orchestrator for the screening workflow."""

    def __init__(
        self,
        provider: UniverseProviderProtocol,
        filters: List[FilterStageProtocol],
        config: ScreeningConfig,
        audit_logger: AuditLoggerProtocol,
        metrics_collector: MetricsCollectorProtocol,
    ) -> None:
        """
        Initialize pipeline with all dependencies.

        Args:
            provider: Data access provider
            filters: Ordered list of filter stages
            config: Screening configuration
            audit_logger: For audit trail
            metrics_collector: For performance metrics
        """
        self.provider = provider
        self.filters = filters
        self.config = config
        self.audit_logger = audit_logger
        self.metrics_collector = metrics_collector

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
        """
        start_time = time.perf_counter()
        correlation_id = str(uuid.uuid4())
        self.audit_logger.set_correlation_id(correlation_id)

        # 1. Create request
        request = ScreeningRequest(
            date=date,
            asset_class=asset_class,
            config_override=config_override,
            correlation_id=correlation_id,
        )

        # 2. Load data
        context = self._load_data(request)

        # 3. Execute filters
        current_assets = context.assets
        audit_trail: List[StageResult] = []

        for filter_stage in self.filters:
            stage_result, current_assets = self._execute_stage(
                filter_stage, current_assets, date, context
            )
            audit_trail.append(stage_result)

        # 4. Record total time
        total_duration = time.perf_counter() - start_time
        self.metrics_collector.record_timing(
            "screening_total_seconds",
            total_duration,
            {"asset_class": asset_class.value},
        )

        # 5. Build result
        return ScreeningResult(
            request=request,
            input_universe=context.assets,
            output_universe=current_assets,
            audit_trail=audit_trail,
            metrics=self.metrics_collector.get_metrics(),
            metadata=self._build_metadata(correlation_id, total_duration),
        )

    def _load_data(self, request: ScreeningRequest) -> DataContext:
        """Bulk load data into DataContext."""
        load_start = time.perf_counter()

        # Get assets
        assets = self.provider.get_assets(request.date, request.asset_class)

        # Calculate date range
        lookback_days = self.config.global_settings.default_lookback_days
        start_date = request.date - timedelta(days=lookback_days)
        end_date = request.date

        # Bulk load all data
        market_data = self.provider.bulk_load_market_data(assets, start_date, end_date)
        metadata = self.provider.bulk_load_metadata(assets, request.date)
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

    def _build_metadata(self, correlation_id: str, duration: float) -> dict:
        """Build result metadata."""
        return {
            "correlation_id": correlation_id,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "version": "0.1.0",
        }
