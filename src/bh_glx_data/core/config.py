"""Configuration management for BH Galaxy Data Analysis Tool.

This module provides a flexible configuration system that supports multiple
configuration sources with priority ordering:
1. CLI arguments
2. Environment variables (BH_GLX_CONFIG, BH_GLX_*)
3. User config: ~/.config/bh-glx-data/config.yaml
4. Local config: ./config.yaml
5. Default values
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv

from bh_glx_data.core.exceptions import ConfigurationError, ValidationError
from bh_glx_data.core.models import Config, DataConfig, JiraConfig


class ConfigManager:
    """Manages configuration loading from multiple sources."""

    # Config file search paths (in priority order)
    CONFIG_SEARCH_PATHS = [
        Path.home() / ".config" / "bh-glx-data" / "config.yaml",
        Path("config.yaml"),
    ]

    def __init__(self):
        """Initialize the configuration manager."""
        self._config: Optional[Config] = None

    @staticmethod
    def _load_env_file(env_file: Optional[Path] = None) -> None:
        """Load environment variables from .env file.

        Args:
            env_file: Optional path to .env file (default: .env in current dir)
        """
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()  # Load from .env in current directory

    @staticmethod
    def _find_config_file(config_path: Optional[Path] = None) -> Optional[Path]:
        """Find configuration file using search path.

        Args:
            config_path: Optional explicit config path

        Returns:
            Path to config file, or None if not found
        """
        # If explicit path provided, use it
        if config_path:
            if config_path.exists():
                return config_path
            raise ConfigurationError(f"Specified config file not found: {config_path}")

        # Check environment variable
        env_config = os.getenv("BH_GLX_CONFIG")
        if env_config:
            env_path = Path(env_config)
            if env_path.exists():
                return env_path
            raise ConfigurationError(f"Config file from BH_GLX_CONFIG not found: {env_path}")

        # Search default paths
        for path in ConfigManager.CONFIG_SEARCH_PATHS:
            if path.exists():
                return path.resolve()

        return None

    @staticmethod
    def _load_yaml_config(config_file: Path) -> Dict[str, Any]:
        """Load configuration from YAML file.

        Args:
            config_file: Path to YAML config file

        Returns:
            Dictionary of configuration values

        Raises:
            ConfigurationError: If YAML parsing fails
        """
        try:
            with open(config_file, "r") as f:
                config_data = yaml.safe_load(f)
                if config_data is None:
                    return {}
                return config_data  # type: ignore[no-any-return]
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Error parsing {config_file}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error reading {config_file}: {e}")

    @staticmethod
    def _load_jira_config_from_env() -> JiraConfig:
        """Load Jira configuration from environment variables.

        Returns:
            JiraConfig object

        Raises:
            ValidationError: If required variables are missing
        """
        server_url = os.getenv("JIRA_SERVER_URL")
        email = os.getenv("EMAIL")
        api_key = os.getenv("API_KEY")

        missing = []
        if not server_url:
            missing.append("JIRA_SERVER_URL")
        if not email:
            missing.append("EMAIL")
        if not api_key:
            missing.append("API_KEY")

        if missing:
            raise ValidationError(
                f"Missing required Jira configuration: {', '.join(missing)}. "
                f"Please set these in your .env file (copy from .env.example)."
            )

        return JiraConfig(server_url=server_url, email=email, api_key=api_key)

    @staticmethod
    def _load_data_config(
        config_dict: Dict[str, Any], cli_overrides: Optional[Dict[str, Any]] = None
    ) -> DataConfig:
        """Load data configuration with overrides.

        Args:
            config_dict: Configuration dictionary from YAML
            cli_overrides: Optional CLI argument overrides

        Returns:
            DataConfig object
        """
        # Start with defaults
        input_dir = Path("csv_data")
        output_dir = Path("summaries")
        temp_dir = None

        # Apply YAML config
        data_config = config_dict.get("data", {})
        if "input_dir" in data_config:
            input_dir = Path(data_config["input_dir"])
        if "output_dir" in data_config:
            output_dir = Path(data_config["output_dir"])
        if "temp_dir" in data_config:
            temp_dir = Path(data_config["temp_dir"])

        # Apply CLI overrides
        if cli_overrides:
            if "input_dir" in cli_overrides:
                input_dir = Path(cli_overrides["input_dir"])
            if "output_dir" in cli_overrides:
                output_dir = Path(cli_overrides["output_dir"])
            if "temp_dir" in cli_overrides:
                temp_dir = Path(cli_overrides["temp_dir"])

        return DataConfig(input_dir=input_dir, output_dir=output_dir, temp_dir=temp_dir)

    @staticmethod
    def load_tickets(config_dict: Dict[str, Any]) -> List[str]:
        """Load Jira ticket keys from configuration.

        Args:
            config_dict: Configuration dictionary

        Returns:
            List of ticket keys

        Raises:
            ValidationError: If no tickets found
        """
        if "tickets" not in config_dict:
            raise ValidationError(
                "No 'tickets' section found in config.yaml. "
                "Please add at least one ticket key to the 'tickets' list."
            )

        tickets = config_dict["tickets"]

        if isinstance(tickets, list):
            # Simple list format: ['SYS-123', 'SYS-456']
            ticket_keys = [str(ticket).strip() for ticket in tickets if ticket]
        elif isinstance(tickets, dict):
            # Future dict format: handle if needed
            ticket_keys = []
        else:
            ticket_keys = []

        if not ticket_keys:
            raise ValidationError(
                "No tickets found in config.yaml. "
                "Please add at least one ticket key to the 'tickets' list."
            )

        return ticket_keys

    def load(
        self,
        config_file: Optional[Path] = None,
        env_file: Optional[Path] = None,
        cli_overrides: Optional[Dict[str, Any]] = None,
        load_env: bool = True,
    ) -> Config:
        """Load configuration from all sources.

        Args:
            config_file: Optional explicit path to config file
            env_file: Optional explicit path to .env file
            cli_overrides: Optional dictionary of CLI argument overrides
            load_env: Whether to load .env file (default: True)

        Returns:
            Config object with complete configuration

        Raises:
            ConfigurationError: If configuration loading fails
            ValidationError: If configuration validation fails
        """
        # Load environment variables
        if load_env:
            self._load_env_file(env_file)

        # Find and load config file
        config_path = self._find_config_file(config_file)
        if config_path:
            config_dict = self._load_yaml_config(config_path)
        else:
            # If no config file found, use empty dict (will use env vars)
            config_dict = {}

        # Load Jira config from environment
        jira_config = self._load_jira_config_from_env()

        # Load data config with CLI overrides
        data_config = self._load_data_config(config_dict, cli_overrides)

        # Create Config object
        config = Config(jira=jira_config, data=data_config)

        self._config = config
        return config

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> Config:
        """Create Config from dictionary (useful for testing).

        Args:
            config_dict: Dictionary with config values

        Returns:
            Config object
        """
        jira_dict = config_dict.get("jira", {})
        jira_config = JiraConfig(
            server_url=jira_dict.get("server_url", ""),
            email=jira_dict.get("email", ""),
            api_key=jira_dict.get("api_key", ""),
        )

        data_dict = config_dict.get("data", {})
        data_config = DataConfig(
            input_dir=Path(data_dict.get("input_dir", "csv_data")),
            output_dir=Path(data_dict.get("output_dir", "summaries")),
            temp_dir=Path(data_dict["temp_dir"]) if "temp_dir" in data_dict else None,
        )

        return Config(jira=jira_config, data=data_config)

    def ensure_directories(self):
        """Ensure data directories exist."""
        if self._config:
            self._config.data.input_dir.mkdir(exist_ok=True, parents=True)
            self._config.data.output_dir.mkdir(exist_ok=True, parents=True)
            if self._config.data.temp_dir:
                self._config.data.temp_dir.mkdir(exist_ok=True, parents=True)


# Backwards compatibility: provide module-level functions
_global_config_manager = ConfigManager()


def load_config(
    config_file: Optional[Path] = None,
    env_file: Optional[Path] = None,
    cli_overrides: Optional[Dict[str, Any]] = None,
) -> Config:
    """Load configuration (backwards compatible function).

    Args:
        config_file: Optional explicit path to config file
        env_file: Optional explicit path to .env file
        cli_overrides: Optional dictionary of CLI argument overrides

    Returns:
        Config object
    """
    return _global_config_manager.load(config_file, env_file, cli_overrides)


def get_config() -> Optional[Config]:
    """Get currently loaded configuration.

    Returns:
        Config object if loaded, None otherwise
    """
    return _global_config_manager._config
