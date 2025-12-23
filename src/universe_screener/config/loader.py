"""
Configuration Loader - YAML Loading with Validation.

Loads configuration from YAML files and validates using Pydantic models.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

from universe_screener.config.models import ScreeningConfig


class ConfigLoader:
    """Loads and validates configuration from YAML files."""

    def __init__(self, base_path: Optional[Path] = None) -> None:
        """
        Initialize config loader.

        Args:
            base_path: Base path for relative config paths
        """
        self._base_path = base_path or Path(".")

    def load(
        self,
        config_path: Union[str, Path],
        profile: Optional[str] = None,
    ) -> ScreeningConfig:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to YAML config file
            profile: Optional profile name to merge

        Returns:
            Validated ScreeningConfig object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValidationError: If config is invalid
        """
        path = self._resolve_path(config_path)
        config_dict = self._load_yaml(path)

        if profile:
            profile_dict = self._load_profile(profile)
            config_dict = self._merge_configs(config_dict, profile_dict)

        return ScreeningConfig.model_validate(config_dict)

    def load_from_dict(self, config_dict: Dict[str, Any]) -> ScreeningConfig:
        """
        Load configuration from dictionary.

        Args:
            config_dict: Configuration as dictionary

        Returns:
            Validated ScreeningConfig object
        """
        return ScreeningConfig.model_validate(config_dict)

    def _resolve_path(self, path: Union[str, Path]) -> Path:
        """Resolve config path relative to base path."""
        p = Path(path)
        if p.is_absolute():
            return p
        return self._base_path / p

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML file."""
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _load_profile(self, profile: str) -> Dict[str, Any]:
        """Load profile configuration."""
        profile_path = self._base_path / "config" / "profiles" / f"{profile}.yaml"
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile not found: {profile}")
        return self._load_yaml(profile_path)

    def _merge_configs(
        self,
        base: Dict[str, Any],
        overlay: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Deep merge overlay into base config."""
        result = dict(base)
        for key, value in overlay.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result


def load_config(
    config_path: Union[str, Path],
    profile: Optional[str] = None,
    base_path: Optional[Path] = None,
) -> ScreeningConfig:
    """
    Convenience function to load configuration.

    Args:
        config_path: Path to YAML config file
        profile: Optional profile name
        base_path: Base path for resolving relative paths

    Returns:
        Validated ScreeningConfig object
    """
    loader = ConfigLoader(base_path=base_path)
    return loader.load(config_path, profile)
