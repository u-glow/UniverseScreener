"""
Data Quality Filter Implementation.

Filters assets based on data availability and quality:
    - Missing days in lookback window
    - Optional: News article coverage (for sentiment feasibility)
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Tuple

from universe_screener.domain.entities import Asset
from universe_screener.domain.value_objects import FilterResult, QualityMetrics
from universe_screener.config.models import DataQualityFilterConfig

if TYPE_CHECKING:
    from universe_screener.pipeline.data_context import DataContext


class DataQualityFilter:
    """Filter assets by data availability."""

    def __init__(self, config: DataQualityFilterConfig) -> None:
        """
        Initialize with configuration.

        Args:
            config: Data quality filter configuration
        """
        self.config = config

    @property
    def name(self) -> str:
        """Unique name of this filter stage."""
        return "data_quality_filter"

    def apply(
        self,
        assets: List[Asset],
        date: datetime,
        context: "DataContext",
    ) -> FilterResult:
        """
        Apply data quality filtering.

        Checks:
            1. Missing days <= threshold
            2. News coverage >= threshold (if enabled)

        Args:
            assets: Assets to filter
            date: Reference date
            context: Data context with quality metrics

        Returns:
            FilterResult with passed/rejected assets
        """
        if not self.config.enabled:
            return FilterResult(
                passed_assets=[a.symbol for a in assets],
                rejected_assets=[],
                rejection_reasons={},
            )

        passed: List[str] = []
        rejected: List[str] = []
        reasons: Dict[str, str] = {}

        for asset in assets:
            quality = context.get_quality_metrics(asset.symbol)
            if quality is None:
                rejected.append(asset.symbol)
                reasons[asset.symbol] = "no quality metrics available"
                continue

            is_valid, reason = self._check_quality(quality)
            if is_valid:
                passed.append(asset.symbol)
            else:
                rejected.append(asset.symbol)
                reasons[asset.symbol] = reason

        return FilterResult(
            passed_assets=passed,
            rejected_assets=rejected,
            rejection_reasons=reasons,
        )

    def _check_quality(
        self,
        quality: QualityMetrics,
    ) -> Tuple[bool, str]:
        """Check if quality metrics meet requirements."""
        # Check missing days
        if quality.missing_days > self.config.max_missing_days:
            return (
                False,
                f"missing_days={quality.missing_days} > max={self.config.max_missing_days}",
            )

        # Check news coverage (if configured)
        if self.config.min_news_articles is not None:
            if (
                quality.news_article_count is None
                or quality.news_article_count < self.config.min_news_articles
            ):
                news_count = quality.news_article_count or 0
                return (
                    False,
                    f"news_count={news_count} < min={self.config.min_news_articles}",
                )

        return True, ""
