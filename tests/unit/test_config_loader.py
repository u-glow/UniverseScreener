"""
Unit Tests for ConfigLoader.

Test Aspects Covered:
    ✅ Business Logic: Config loading and merging
    ✅ Error Handling: Invalid YAML, missing files
"""

from __future__ import annotations

from pathlib import Path
import tempfile

import pytest
import yaml

from universe_screener.config.loader import ConfigLoader, load_config
from universe_screener.config.models import ScreeningConfig


class TestConfigLoader:
    """Test cases for ConfigLoader."""

    def test_loads_valid_yaml(self, tmp_path: Path) -> None:
        """
        SCENARIO: Valid YAML configuration file
        EXPECTED: ScreeningConfig object created
        """
        # Arrange
        config_content = """
version: "1.0"
global:
  default_lookback_days: 30
  timezone: "UTC"
structural_filter:
  enabled: true
  allowed_exchanges:
    - NYSE
  min_listing_age_days: 100
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        loader = ConfigLoader(base_path=tmp_path)

        # Act
        config = loader.load("config.yaml")

        # Assert
        assert isinstance(config, ScreeningConfig)
        assert config.global_settings.default_lookback_days == 30
        assert config.structural_filter.min_listing_age_days == 100
        assert "NYSE" in config.structural_filter.allowed_exchanges

    def test_applies_defaults(self) -> None:
        """
        SCENARIO: Minimal config with only required fields
        EXPECTED: Defaults applied for missing fields
        """
        # Arrange
        loader = ConfigLoader()
        config_dict = {"version": "1.0"}

        # Act
        config = loader.load_from_dict(config_dict)

        # Assert
        assert config.global_settings.default_lookback_days == 60  # Default
        assert config.structural_filter.enabled is True  # Default
        assert config.liquidity_filter.stock.min_avg_dollar_volume_usd == 5_000_000

    def test_validates_invalid_config(self, tmp_path: Path) -> None:
        """
        SCENARIO: Config with invalid values
        EXPECTED: ValidationError raised
        """
        # Arrange
        config_content = """
version: "1.0"
global:
  default_lookback_days: -10  # Invalid: must be >= 1
"""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text(config_content)

        loader = ConfigLoader(base_path=tmp_path)

        # Act & Assert
        with pytest.raises(Exception):  # Pydantic ValidationError
            loader.load("invalid.yaml")

    def test_file_not_found(self, tmp_path: Path) -> None:
        """
        SCENARIO: Config path doesn't exist
        EXPECTED: FileNotFoundError raised
        """
        # Arrange
        loader = ConfigLoader(base_path=tmp_path)

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            loader.load("nonexistent.yaml")

    def test_merges_configs(self) -> None:
        """
        SCENARIO: Two configs merged together
        EXPECTED: Overlay values override base values
        """
        # Arrange
        loader = ConfigLoader()
        base = {
            "version": "1.0",
            "structural_filter": {
                "enabled": True,
                "min_listing_age_days": 100,
            },
        }
        overlay = {
            "structural_filter": {
                "min_listing_age_days": 200,  # Override
            },
        }

        # Act
        merged = loader._merge_configs(base, overlay)

        # Assert
        assert merged["structural_filter"]["enabled"] is True  # From base
        assert merged["structural_filter"]["min_listing_age_days"] == 200  # From overlay

    def test_load_from_dict(self) -> None:
        """
        SCENARIO: Load config from dictionary
        EXPECTED: Valid ScreeningConfig created
        """
        # Arrange
        loader = ConfigLoader()
        config_dict = {
            "version": "2.0",
            "global": {
                "default_lookback_days": 90,
            },
        }

        # Act
        config = loader.load_from_dict(config_dict)

        # Assert
        assert config.version == "2.0"
        assert config.global_settings.default_lookback_days == 90
