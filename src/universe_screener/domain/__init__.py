"""
Domain Layer - Core Business Entities and Value Objects.

This package contains the core domain model for the Universe Screener.
All entities here are pure Python with no external dependencies
(except Pydantic for validation).

Entities:
    - Asset: Represents a tradable asset (stock, crypto, forex)
    - AssetClass: Enum for asset classification
    - ScreeningResult: Complete result of a screening run

Value Objects:
    - FilterResult: Result of a single filter stage
    - StageMetrics: Performance metrics for a filter stage
    - QualityMetrics: Data quality indicators for an asset

Design Principles:
    - Immutable where possible (frozen dataclasses)
    - Rich domain model (behavior with data)
    - No infrastructure dependencies
"""

# TODO: Implement - Export entities after implementation

