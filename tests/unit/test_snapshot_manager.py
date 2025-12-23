"""
Unit Tests for SnapshotManager.

Test Aspects Covered:
    ✅ Business Logic: Snapshot creation, retrieval
    ✅ Edge Cases: Disabled mode, stale snapshots
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from universe_screener.domain.entities import AssetClass
from universe_screener.observability.snapshot_manager import (
    SnapshotManager,
    Snapshot,
)


@pytest.fixture
def manager() -> SnapshotManager:
    """Create snapshot manager."""
    return SnapshotManager(enabled=True)


class TestSnapshotCreation:
    """Test snapshot creation."""

    def test_create_snapshot_returns_id(self, manager: SnapshotManager) -> None:
        """
        SCENARIO: Create a snapshot
        EXPECTED: Returns unique snapshot ID
        """
        # Act
        snapshot_id = manager.create_snapshot(
            screening_date=datetime(2024, 12, 15),
            asset_class=AssetClass.STOCK,
        )

        # Assert
        assert snapshot_id is not None
        assert len(snapshot_id) == 36  # UUID format

    def test_create_snapshot_with_metadata(self, manager: SnapshotManager) -> None:
        """
        SCENARIO: Create snapshot with metadata
        EXPECTED: Metadata stored
        """
        # Act
        snapshot_id = manager.create_snapshot(
            screening_date=datetime(2024, 12, 15),
            asset_class=AssetClass.STOCK,
            metadata={"correlation_id": "test-123"},
        )

        # Assert
        snapshot = manager.get_snapshot(snapshot_id)
        assert snapshot is not None
        assert snapshot.metadata["correlation_id"] == "test-123"

    def test_disabled_returns_deterministic_id(self) -> None:
        """
        SCENARIO: Manager is disabled
        EXPECTED: Returns deterministic ID
        """
        # Arrange
        manager = SnapshotManager(enabled=False)

        # Act
        id1 = manager.create_snapshot(
            screening_date=datetime(2024, 12, 15),
            asset_class=AssetClass.STOCK,
        )
        id2 = manager.create_snapshot(
            screening_date=datetime(2024, 12, 15),
            asset_class=AssetClass.STOCK,
        )

        # Assert
        assert id1 == id2  # Deterministic

    def test_current_snapshot_id_set(self, manager: SnapshotManager) -> None:
        """
        SCENARIO: Create snapshot
        EXPECTED: Current snapshot ID updated
        """
        # Act
        snapshot_id = manager.create_snapshot(
            screening_date=datetime(2024, 12, 15),
            asset_class=AssetClass.STOCK,
        )

        # Assert
        assert manager.get_current_snapshot_id() == snapshot_id


class TestSnapshotRetrieval:
    """Test snapshot retrieval."""

    def test_get_snapshot_by_id(self, manager: SnapshotManager) -> None:
        """
        SCENARIO: Get snapshot by ID
        EXPECTED: Returns correct snapshot
        """
        # Arrange
        snapshot_id = manager.create_snapshot(
            screening_date=datetime(2024, 12, 15),
            asset_class=AssetClass.STOCK,
        )

        # Act
        snapshot = manager.get_snapshot(snapshot_id)

        # Assert
        assert snapshot is not None
        assert snapshot.snapshot_id == snapshot_id
        assert snapshot.asset_class == AssetClass.STOCK

    def test_get_nonexistent_snapshot(self, manager: SnapshotManager) -> None:
        """
        SCENARIO: Get non-existent snapshot
        EXPECTED: Returns None
        """
        # Act
        snapshot = manager.get_snapshot("nonexistent-id")

        # Assert
        assert snapshot is None

    def test_get_current_snapshot(self, manager: SnapshotManager) -> None:
        """
        SCENARIO: Get current snapshot
        EXPECTED: Returns most recent snapshot
        """
        # Arrange
        manager.create_snapshot(
            screening_date=datetime(2024, 12, 14),
            asset_class=AssetClass.STOCK,
        )
        latest_id = manager.create_snapshot(
            screening_date=datetime(2024, 12, 15),
            asset_class=AssetClass.STOCK,
        )

        # Act
        current = manager.get_current_snapshot()

        # Assert
        assert current is not None
        assert current.snapshot_id == latest_id

    def test_get_snapshot_data(self, manager: SnapshotManager) -> None:
        """
        SCENARIO: Get snapshot data for provider
        EXPECTED: Returns context dict
        """
        # Arrange
        snapshot_id = manager.create_snapshot(
            screening_date=datetime(2024, 12, 15),
            asset_class=AssetClass.STOCK,
        )

        # Act
        data = manager.get_snapshot_data(snapshot_id)

        # Assert
        assert data["valid"] is True
        assert data["asset_class"] == AssetClass.STOCK
        assert "is_stale" in data


class TestSnapshotValidation:
    """Test snapshot validation."""

    def test_is_valid_for_fresh_snapshot(self, manager: SnapshotManager) -> None:
        """
        SCENARIO: Check fresh snapshot
        EXPECTED: Returns True
        """
        # Arrange
        snapshot_id = manager.create_snapshot(
            screening_date=datetime(2024, 12, 15),
            asset_class=AssetClass.STOCK,
        )

        # Act
        is_valid = manager.is_snapshot_valid(snapshot_id)

        # Assert
        assert is_valid is True

    def test_is_valid_for_nonexistent(self, manager: SnapshotManager) -> None:
        """
        SCENARIO: Check non-existent snapshot
        EXPECTED: Returns False
        """
        # Act
        is_valid = manager.is_snapshot_valid("nonexistent")

        # Assert
        assert is_valid is False


class TestSnapshotInvalidation:
    """Test snapshot invalidation."""

    def test_invalidate_snapshot(self, manager: SnapshotManager) -> None:
        """
        SCENARIO: Invalidate a snapshot
        EXPECTED: Snapshot removed
        """
        # Arrange
        snapshot_id = manager.create_snapshot(
            screening_date=datetime(2024, 12, 15),
            asset_class=AssetClass.STOCK,
        )

        # Act
        result = manager.invalidate_snapshot(snapshot_id)

        # Assert
        assert result is True
        assert manager.get_snapshot(snapshot_id) is None

    def test_invalidate_nonexistent(self, manager: SnapshotManager) -> None:
        """
        SCENARIO: Invalidate non-existent snapshot
        EXPECTED: Returns False
        """
        # Act
        result = manager.invalidate_snapshot("nonexistent")

        # Assert
        assert result is False

    def test_clear_all(self, manager: SnapshotManager) -> None:
        """
        SCENARIO: Clear all snapshots
        EXPECTED: All snapshots removed
        """
        # Arrange
        manager.create_snapshot(
            screening_date=datetime(2024, 12, 15),
            asset_class=AssetClass.STOCK,
        )
        manager.create_snapshot(
            screening_date=datetime(2024, 12, 14),
            asset_class=AssetClass.CRYPTO,
        )

        # Act
        manager.clear_all()

        # Assert
        assert manager.get_active_snapshot_count() == 0


class TestSnapshot:
    """Test Snapshot dataclass."""

    def test_age_seconds(self) -> None:
        """
        SCENARIO: Check snapshot age
        EXPECTED: Returns correct age
        """
        # Arrange
        snapshot = Snapshot(
            snapshot_id="test",
            created_at=datetime.now() - timedelta(seconds=10),
            screening_date=datetime(2024, 12, 15),
            asset_class=AssetClass.STOCK,
        )

        # Act
        age = snapshot.age_seconds

        # Assert
        assert age >= 10

    def test_to_dict(self) -> None:
        """
        SCENARIO: Convert snapshot to dict
        EXPECTED: All fields present
        """
        # Arrange
        snapshot = Snapshot(
            snapshot_id="test-123",
            created_at=datetime(2024, 12, 15, 10, 0, 0),
            screening_date=datetime(2024, 12, 15),
            asset_class=AssetClass.STOCK,
        )

        # Act
        data = snapshot.to_dict()

        # Assert
        assert data["snapshot_id"] == "test-123"
        assert data["asset_class"] == "STOCK"

