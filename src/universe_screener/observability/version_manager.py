"""
Version Manager - Code and Configuration Versioning.

Tracks versions for reproducibility:
    - Code version (Git SHA or package version)
    - Config hash (SHA256 of configuration)
    - Filter versions

Design Notes:
    - Embeds version metadata in screening results
    - Enables audit trail for regulatory compliance
    - Supports both Git-based and package-based versioning
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from universe_screener import __version__


@dataclass
class VersionMetadata:
    """Version metadata for reproducibility."""
    code_version: str
    config_hash: str
    filter_versions: Dict[str, str]
    timestamp: str
    git_sha: Optional[str] = None
    git_branch: Optional[str] = None
    git_dirty: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "code_version": self.code_version,
            "config_hash": self.config_hash,
            "filter_versions": self.filter_versions,
            "timestamp": self.timestamp,
            "git_sha": self.git_sha,
            "git_branch": self.git_branch,
            "git_dirty": self.git_dirty,
        }


class VersionManager:
    """
    Manages version information for reproducibility.

    Tracks:
        - Package version
        - Git commit SHA (if available)
        - Configuration hash
        - Filter versions
    """

    def __init__(
        self,
        include_git_info: bool = True,
        filter_versions: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Initialize version manager.

        Args:
            include_git_info: Try to get Git SHA and branch
            filter_versions: Manual filter version mapping
        """
        self.include_git_info = include_git_info
        self._filter_versions = filter_versions or {}
        self._cached_git_info: Optional[Dict[str, Any]] = None

    def get_version_metadata(
        self,
        config: Optional[Any] = None,
    ) -> VersionMetadata:
        """
        Get complete version metadata.

        Args:
            config: ScreeningConfig to hash (optional)

        Returns:
            VersionMetadata with all version info
        """
        git_info = self._get_git_info() if self.include_git_info else {}

        return VersionMetadata(
            code_version=__version__,
            config_hash=self.compute_config_hash(config) if config else "no_config",
            filter_versions=self._filter_versions,
            timestamp=datetime.now().isoformat(),
            git_sha=git_info.get("sha"),
            git_branch=git_info.get("branch"),
            git_dirty=git_info.get("dirty", False),
        )

    def compute_config_hash(self, config: Any) -> str:
        """
        Compute SHA256 hash of configuration.

        Args:
            config: Configuration object (Pydantic model or dict)

        Returns:
            SHA256 hash string (first 16 chars)
        """
        try:
            # Handle Pydantic models
            if hasattr(config, "model_dump"):
                config_dict = config.model_dump()
            elif hasattr(config, "dict"):
                config_dict = config.dict()
            elif isinstance(config, dict):
                config_dict = config
            else:
                config_dict = {"raw": str(config)}

            # Sort keys for deterministic hash
            config_json = json.dumps(config_dict, sort_keys=True, default=str)
            hash_bytes = hashlib.sha256(config_json.encode()).hexdigest()

            return hash_bytes[:16]

        except Exception:
            return "hash_error"

    def register_filter_version(self, filter_name: str, version: str) -> None:
        """
        Register a filter's version.

        Args:
            filter_name: Name of the filter
            version: Version string
        """
        self._filter_versions[filter_name] = version

    def register_filters(self, filters: List[Any]) -> None:
        """
        Register versions for a list of filters.

        Args:
            filters: List of filter objects with 'name' and optionally 'version'
        """
        for f in filters:
            name = getattr(f, "name", f.__class__.__name__)
            version = getattr(f, "version", "1.0.0")
            self._filter_versions[name] = version

    def _get_git_info(self) -> Dict[str, Any]:
        """Get Git repository information."""
        if self._cached_git_info is not None:
            return self._cached_git_info

        result: Dict[str, Any] = {}

        try:
            # Get current SHA
            sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            result["sha"] = sha[:8]  # Short SHA

            # Get current branch
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            result["branch"] = branch

            # Check for uncommitted changes
            status = subprocess.check_output(
                ["git", "status", "--porcelain"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            result["dirty"] = len(status) > 0

        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            # Git not available or not in a Git repo
            result = {}

        self._cached_git_info = result
        return result

    def get_code_version(self) -> str:
        """Get code version string."""
        git_info = self._get_git_info() if self.include_git_info else {}

        if git_info.get("sha"):
            dirty_suffix = "-dirty" if git_info.get("dirty") else ""
            return f"{__version__}+{git_info['sha']}{dirty_suffix}"
        else:
            return __version__

    def get_filter_versions(self) -> Dict[str, str]:
        """Get all registered filter versions."""
        return dict(self._filter_versions)

    def compare_configs(
        self,
        config1: Any,
        config2: Any,
    ) -> bool:
        """
        Compare two configurations.

        Args:
            config1: First configuration
            config2: Second configuration

        Returns:
            True if configurations are identical
        """
        return self.compute_config_hash(config1) == self.compute_config_hash(config2)

