"""
Snapshot Manager - Point-in-Time Data Consistency.

Ensures all filter stages operate on the same data snapshot:
    - Creates immutable snapshots at screening start
    - Provides snapshot ID for data queries
    - Guarantees no read-your-own-writes issues

Design Notes:
    - Can be disabled for simple use cases
    - Snapshot ID propagated through provider calls
    - Enables reproducible backtesting
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from universe_screener.domain.entities import AssetClass


@dataclass
class Snapshot:
    """Immutable data snapshot."""
    snapshot_id: str
    created_at: datetime
    screening_date: datetime
    asset_class: AssetClass
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def age_seconds(self) -> float:
        """Get snapshot age in seconds."""
        return (datetime.now() - self.created_at).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at.isoformat(),
            "screening_date": self.screening_date.isoformat(),
            "asset_class": self.asset_class.value,
            "metadata": self.metadata,
        }


class SnapshotManager:
    """
    Manages point-in-time data snapshots.

    Ensures consistency across filter stages by creating
    an immutable snapshot at screening start.
    """

    def __init__(
        self,
        enabled: bool = True,
        max_snapshot_age_seconds: float = 3600.0,
    ) -> None:
        """
        Initialize snapshot manager.

        Args:
            enabled: Enable snapshot management
            max_snapshot_age_seconds: Max age before snapshot is stale
        """
        self.enabled = enabled
        self.max_snapshot_age_seconds = max_snapshot_age_seconds
        self._snapshots: Dict[str, Snapshot] = {}
        self._current_snapshot_id: Optional[str] = None

    def create_snapshot(
        self,
        screening_date: datetime,
        asset_class: AssetClass,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new data snapshot.

        Args:
            screening_date: Point-in-time for screening
            asset_class: Asset class being screened
            metadata: Additional snapshot metadata

        Returns:
            Unique snapshot ID
        """
        if not self.enabled:
            # Return a deterministic ID when disabled
            return self._generate_deterministic_id(screening_date, asset_class)

        snapshot_id = str(uuid.uuid4())

        snapshot = Snapshot(
            snapshot_id=snapshot_id,
            created_at=datetime.now(),
            screening_date=screening_date,
            asset_class=asset_class,
            metadata=metadata or {},
        )

        self._snapshots[snapshot_id] = snapshot
        self._current_snapshot_id = snapshot_id

        return snapshot_id

    def _generate_deterministic_id(
        self,
        screening_date: datetime,
        asset_class: AssetClass,
    ) -> str:
        """Generate deterministic snapshot ID for disabled mode."""
        key = f"{screening_date.isoformat()}:{asset_class.value}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """
        Get snapshot by ID.

        Args:
            snapshot_id: Snapshot identifier

        Returns:
            Snapshot if found, None otherwise
        """
        return self._snapshots.get(snapshot_id)

    def get_current_snapshot(self) -> Optional[Snapshot]:
        """Get the current active snapshot."""
        if self._current_snapshot_id:
            return self._snapshots.get(self._current_snapshot_id)
        return None

    def get_current_snapshot_id(self) -> Optional[str]:
        """Get current snapshot ID."""
        return self._current_snapshot_id

    def get_snapshot_data(self, snapshot_id: str) -> Dict[str, Any]:
        """
        Get snapshot data for provider queries.

        Args:
            snapshot_id: Snapshot identifier

        Returns:
            Dict with snapshot context for provider
        """
        snapshot = self._snapshots.get(snapshot_id)

        if snapshot is None:
            return {"snapshot_id": snapshot_id, "valid": False}

        return {
            "snapshot_id": snapshot_id,
            "valid": True,
            "screening_date": snapshot.screening_date,
            "asset_class": snapshot.asset_class,
            "created_at": snapshot.created_at,
            "is_stale": snapshot.age_seconds > self.max_snapshot_age_seconds,
        }

    def is_snapshot_valid(self, snapshot_id: str) -> bool:
        """
        Check if snapshot is still valid.

        Args:
            snapshot_id: Snapshot identifier

        Returns:
            True if valid and not stale
        """
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            return False

        return snapshot.age_seconds <= self.max_snapshot_age_seconds

    def invalidate_snapshot(self, snapshot_id: str) -> bool:
        """
        Invalidate and remove a snapshot.

        Args:
            snapshot_id: Snapshot to invalidate

        Returns:
            True if snapshot was found and removed
        """
        if snapshot_id in self._snapshots:
            del self._snapshots[snapshot_id]
            if self._current_snapshot_id == snapshot_id:
                self._current_snapshot_id = None
            return True
        return False

    def cleanup_stale_snapshots(self) -> int:
        """
        Remove all stale snapshots.

        Returns:
            Number of snapshots removed
        """
        stale_ids = [
            sid for sid, snapshot in self._snapshots.items()
            if snapshot.age_seconds > self.max_snapshot_age_seconds
        ]

        for sid in stale_ids:
            self.invalidate_snapshot(sid)

        return len(stale_ids)

    def get_active_snapshot_count(self) -> int:
        """Get number of active snapshots."""
        return len(self._snapshots)

    def clear_all(self) -> None:
        """Clear all snapshots."""
        self._snapshots.clear()
        self._current_snapshot_id = None

