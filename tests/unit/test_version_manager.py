"""
Unit Tests for VersionManager.

Test Aspects Covered:
    ✅ Business Logic: Version tracking, config hashing
    ✅ Edge Cases: No Git, different config types
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from universe_screener.observability.version_manager import (
    VersionManager,
    VersionMetadata,
)
from universe_screener.config.models import ScreeningConfig


@pytest.fixture
def manager() -> VersionManager:
    """Create version manager."""
    return VersionManager(include_git_info=False)


@pytest.fixture
def default_config() -> ScreeningConfig:
    """Create default config."""
    return ScreeningConfig()


class TestVersionMetadata:
    """Test version metadata retrieval."""

    def test_get_version_metadata(
        self,
        manager: VersionManager,
        default_config: ScreeningConfig,
    ) -> None:
        """
        SCENARIO: Get version metadata
        EXPECTED: Returns VersionMetadata with all fields
        """
        # Act
        metadata = manager.get_version_metadata(default_config)

        # Assert
        assert isinstance(metadata, VersionMetadata)
        assert metadata.code_version is not None
        assert metadata.config_hash is not None
        assert metadata.timestamp is not None

    def test_get_version_without_config(self, manager: VersionManager) -> None:
        """
        SCENARIO: Get version without config
        EXPECTED: Returns metadata with no_config hash
        """
        # Act
        metadata = manager.get_version_metadata()

        # Assert
        assert metadata.config_hash == "no_config"


class TestConfigHashing:
    """Test configuration hashing."""

    def test_compute_config_hash(
        self,
        manager: VersionManager,
        default_config: ScreeningConfig,
    ) -> None:
        """
        SCENARIO: Hash a config
        EXPECTED: Returns 16-char hash
        """
        # Act
        hash_value = manager.compute_config_hash(default_config)

        # Assert
        assert len(hash_value) == 16
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_same_config_same_hash(
        self,
        manager: VersionManager,
    ) -> None:
        """
        SCENARIO: Hash same config twice
        EXPECTED: Same hash value
        """
        # Arrange
        config1 = ScreeningConfig()
        config2 = ScreeningConfig()

        # Act
        hash1 = manager.compute_config_hash(config1)
        hash2 = manager.compute_config_hash(config2)

        # Assert
        assert hash1 == hash2

    def test_different_config_different_hash(
        self,
        manager: VersionManager,
    ) -> None:
        """
        SCENARIO: Hash different configs
        EXPECTED: Different hash values
        """
        # Arrange
        config1 = ScreeningConfig()
        config2 = ScreeningConfig()
        config2.structural_filter.min_listing_age_days = 500

        # Act
        hash1 = manager.compute_config_hash(config1)
        hash2 = manager.compute_config_hash(config2)

        # Assert
        assert hash1 != hash2

    def test_hash_dict_config(self, manager: VersionManager) -> None:
        """
        SCENARIO: Hash a dict config
        EXPECTED: Returns valid hash
        """
        # Arrange
        config = {"key": "value", "nested": {"a": 1}}

        # Act
        hash_value = manager.compute_config_hash(config)

        # Assert
        assert len(hash_value) == 16

    def test_compare_configs(
        self,
        manager: VersionManager,
        default_config: ScreeningConfig,
    ) -> None:
        """
        SCENARIO: Compare two configs
        EXPECTED: Returns True for identical configs
        """
        # Arrange
        config1 = ScreeningConfig()
        config2 = ScreeningConfig()

        # Act & Assert
        assert manager.compare_configs(config1, config2) is True


class TestFilterVersions:
    """Test filter version tracking."""

    def test_register_filter_version(self, manager: VersionManager) -> None:
        """
        SCENARIO: Register a filter version
        EXPECTED: Version stored
        """
        # Act
        manager.register_filter_version("structural_filter", "1.2.0")

        # Assert
        versions = manager.get_filter_versions()
        assert versions["structural_filter"] == "1.2.0"

    def test_register_filters_from_objects(self, manager: VersionManager) -> None:
        """
        SCENARIO: Register filters from objects
        EXPECTED: Versions extracted from objects
        """
        # Arrange
        filter1 = Mock()
        filter1.name = "liquidity_filter"
        filter1.version = "2.0.0"

        filter2 = Mock(spec=["name"])  # Only has 'name', no 'version'
        filter2.name = "data_quality_filter"

        # Act
        manager.register_filters([filter1, filter2])

        # Assert
        versions = manager.get_filter_versions()
        assert versions["liquidity_filter"] == "2.0.0"
        assert versions["data_quality_filter"] == "1.0.0"  # Default


class TestGitInfo:
    """Test Git information retrieval."""

    def test_no_git_info_when_disabled(self) -> None:
        """
        SCENARIO: Git info disabled
        EXPECTED: No Git SHA in metadata
        """
        # Arrange
        manager = VersionManager(include_git_info=False)

        # Act
        metadata = manager.get_version_metadata()

        # Assert
        assert metadata.git_sha is None

    def test_get_code_version_without_git(self) -> None:
        """
        SCENARIO: Get code version without Git
        EXPECTED: Returns package version only
        """
        # Arrange
        manager = VersionManager(include_git_info=False)

        # Act
        version = manager.get_code_version()

        # Assert
        assert "+" not in version  # No Git suffix

    @patch("subprocess.check_output")
    def test_get_git_info_success(self, mock_subprocess: Mock) -> None:
        """
        SCENARIO: Git available and in repo
        EXPECTED: Returns Git SHA and branch
        """
        # Arrange
        mock_subprocess.side_effect = [
            "abc12345678\n",  # SHA
            "main\n",  # Branch
            "",  # Status (clean)
        ]
        manager = VersionManager(include_git_info=True)
        manager._cached_git_info = None  # Clear cache

        # Act
        version = manager.get_code_version()

        # Assert
        assert "+abc12345" in version

    @patch("subprocess.check_output")
    def test_get_git_info_dirty(self, mock_subprocess: Mock) -> None:
        """
        SCENARIO: Git repo has uncommitted changes
        EXPECTED: Version includes -dirty suffix
        """
        # Arrange
        mock_subprocess.side_effect = [
            "abc12345678\n",  # SHA
            "main\n",  # Branch
            "M modified.py\n",  # Status (dirty)
        ]
        manager = VersionManager(include_git_info=True)
        manager._cached_git_info = None  # Clear cache

        # Act
        version = manager.get_code_version()

        # Assert
        assert "-dirty" in version


class TestVersionMetadataClass:
    """Test VersionMetadata dataclass."""

    def test_to_dict(self) -> None:
        """
        SCENARIO: Convert to dict
        EXPECTED: All fields present
        """
        # Arrange
        metadata = VersionMetadata(
            code_version="0.2.0",
            config_hash="abc123",
            filter_versions={"filter1": "1.0"},
            timestamp="2024-12-15T10:00:00",
            git_sha="abc1234",
            git_branch="main",
            git_dirty=False,
        )

        # Act
        data = metadata.to_dict()

        # Assert
        assert data["code_version"] == "0.2.0"
        assert data["config_hash"] == "abc123"
        assert data["git_sha"] == "abc1234"
        assert data["filter_versions"]["filter1"] == "1.0"

