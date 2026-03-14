"""Unit tests for bh_glx_data.core.config module."""

import os
from pathlib import Path

import pytest
import yaml

from bh_glx_data.core.config import ConfigManager, get_config, load_config
from bh_glx_data.core.exceptions import ConfigurationError, ValidationError
from bh_glx_data.core.models import Config, DataConfig, JiraConfig


@pytest.mark.unit
class TestConfigManagerFindConfigFile:
    """Test cases for ConfigManager._find_config_file method."""

    def test_explicit_config_path_exists(self, tmp_config_dir):
        """Test finding config file with explicit path that exists."""
        config_file = tmp_config_dir / "config.yaml"
        config_file.write_text("test: value")

        result = ConfigManager._find_config_file(config_file)
        assert result == config_file

    def test_explicit_config_path_not_exists(self, tmp_config_dir):
        """Test error when explicit config path doesn't exist."""
        config_file = tmp_config_dir / "nonexistent.yaml"

        with pytest.raises(ConfigurationError, match="Specified config file not found"):
            ConfigManager._find_config_file(config_file)

    def test_env_variable_config_path(self, tmp_config_dir, monkeypatch):
        """Test finding config file from BH_GLX_CONFIG env variable."""
        config_file = tmp_config_dir / "config.yaml"
        config_file.write_text("test: value")

        monkeypatch.setenv("BH_GLX_CONFIG", str(config_file))

        result = ConfigManager._find_config_file()
        assert result == config_file

    def test_env_variable_config_path_not_exists(self, tmp_config_dir, monkeypatch):
        """Test error when env variable points to non-existent file."""
        config_file = tmp_config_dir / "nonexistent.yaml"
        monkeypatch.setenv("BH_GLX_CONFIG", str(config_file))

        with pytest.raises(ConfigurationError, match="Config file from BH_GLX_CONFIG not found"):
            ConfigManager._find_config_file()

    def test_search_default_paths(self, tmp_path, monkeypatch):
        """Test searching default config paths."""
        # Create config in current directory
        config_file = tmp_path / "config.yaml"
        config_file.write_text("test: value")

        # Change to tmp directory
        monkeypatch.chdir(tmp_path)

        result = ConfigManager._find_config_file()
        assert result == config_file

    def test_no_config_file_found(self, tmp_path, monkeypatch):
        """Test when no config file is found."""
        # Change to empty directory
        monkeypatch.chdir(tmp_path)

        result = ConfigManager._find_config_file()
        assert result is None


@pytest.mark.unit
class TestConfigManagerLoadYamlConfig:
    """Test cases for ConfigManager._load_yaml_config method."""

    def test_load_valid_yaml(self, tmp_config_dir):
        """Test loading valid YAML configuration."""
        config_file = tmp_config_dir / "config.yaml"
        config_data = {"tickets": ["SYS-123", "SYS-456"], "data": {"input_dir": "csv_data"}}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        result = ConfigManager._load_yaml_config(config_file)
        assert result == config_data
        assert result["tickets"] == ["SYS-123", "SYS-456"]

    def test_load_empty_yaml(self, tmp_config_dir):
        """Test loading empty YAML file."""
        config_file = tmp_config_dir / "config.yaml"
        config_file.write_text("")

        result = ConfigManager._load_yaml_config(config_file)
        assert result == {}

    def test_load_invalid_yaml(self, tmp_config_dir):
        """Test error when loading invalid YAML."""
        config_file = tmp_config_dir / "config.yaml"
        config_file.write_text("invalid: yaml: content: [")

        with pytest.raises(ConfigurationError, match="Error parsing"):
            ConfigManager._load_yaml_config(config_file)

    def test_load_nonexistent_file(self, tmp_config_dir):
        """Test error when loading non-existent file."""
        config_file = tmp_config_dir / "nonexistent.yaml"

        with pytest.raises(ConfigurationError, match="Error reading"):
            ConfigManager._load_yaml_config(config_file)


@pytest.mark.unit
class TestConfigManagerLoadJiraConfig:
    """Test cases for ConfigManager._load_jira_config_from_env method."""

    def test_load_valid_jira_config(self, monkeypatch):
        """Test loading valid Jira config from environment."""
        monkeypatch.setenv("JIRA_SERVER_URL", "https://example.atlassian.net")
        monkeypatch.setenv("EMAIL", "test@example.com")
        monkeypatch.setenv("API_KEY", "test-api-key")

        result = ConfigManager._load_jira_config_from_env()
        assert isinstance(result, JiraConfig)
        assert result.server_url == "https://example.atlassian.net"
        assert result.email == "test@example.com"
        assert result.api_key == "test-api-key"

    def test_missing_server_url(self, monkeypatch):
        """Test error when JIRA_SERVER_URL is missing."""
        monkeypatch.setenv("EMAIL", "test@example.com")
        monkeypatch.setenv("API_KEY", "test-api-key")
        monkeypatch.delenv("JIRA_SERVER_URL", raising=False)

        with pytest.raises(ValidationError, match="Missing required Jira configuration"):
            ConfigManager._load_jira_config_from_env()

    def test_missing_email(self, monkeypatch):
        """Test error when EMAIL is missing."""
        monkeypatch.setenv("JIRA_SERVER_URL", "https://example.atlassian.net")
        monkeypatch.setenv("API_KEY", "test-api-key")
        monkeypatch.delenv("EMAIL", raising=False)

        with pytest.raises(ValidationError, match="Missing required Jira configuration"):
            ConfigManager._load_jira_config_from_env()

    def test_missing_api_key(self, monkeypatch):
        """Test error when API_KEY is missing."""
        monkeypatch.setenv("JIRA_SERVER_URL", "https://example.atlassian.net")
        monkeypatch.setenv("EMAIL", "test@example.com")
        monkeypatch.delenv("API_KEY", raising=False)

        with pytest.raises(ValidationError, match="Missing required Jira configuration"):
            ConfigManager._load_jira_config_from_env()

    def test_missing_all_vars(self, monkeypatch):
        """Test error when all variables are missing."""
        monkeypatch.delenv("JIRA_SERVER_URL", raising=False)
        monkeypatch.delenv("EMAIL", raising=False)
        monkeypatch.delenv("API_KEY", raising=False)

        with pytest.raises(ValidationError) as exc_info:
            ConfigManager._load_jira_config_from_env()

        assert "JIRA_SERVER_URL" in str(exc_info.value)
        assert "EMAIL" in str(exc_info.value)
        assert "API_KEY" in str(exc_info.value)


@pytest.mark.unit
class TestConfigManagerLoadDataConfig:
    """Test cases for ConfigManager._load_data_config method."""

    def test_load_default_data_config(self):
        """Test loading data config with defaults."""
        result = ConfigManager._load_data_config({})
        assert isinstance(result, DataConfig)
        assert result.input_dir == Path("csv_data")
        assert result.output_dir == Path("summaries")
        assert result.temp_dir is None

    def test_load_data_config_from_yaml(self):
        """Test loading data config from YAML dict."""
        config_dict = {
            "data": {
                "input_dir": "/custom/input",
                "output_dir": "/custom/output",
                "temp_dir": "/custom/temp",
            }
        }
        result = ConfigManager._load_data_config(config_dict)
        assert result.input_dir == Path("/custom/input")
        assert result.output_dir == Path("/custom/output")
        assert result.temp_dir == Path("/custom/temp")

    def test_load_data_config_with_cli_overrides(self):
        """Test loading data config with CLI overrides."""
        config_dict = {"data": {"input_dir": "yaml_input"}}
        cli_overrides = {"output_dir": "cli_output"}

        result = ConfigManager._load_data_config(config_dict, cli_overrides)
        assert result.input_dir == Path("yaml_input")  # From YAML
        assert result.output_dir == Path("cli_output")  # From CLI override

    def test_cli_overrides_take_precedence(self):
        """Test that CLI overrides take precedence over YAML."""
        config_dict = {"data": {"input_dir": "yaml_input", "output_dir": "yaml_output"}}
        cli_overrides = {"input_dir": "cli_input"}

        result = ConfigManager._load_data_config(config_dict, cli_overrides)
        assert result.input_dir == Path("cli_input")  # CLI override
        assert result.output_dir == Path("yaml_output")  # From YAML


@pytest.mark.unit
class TestConfigManagerLoadTickets:
    """Test cases for ConfigManager.load_tickets method."""

    def test_load_tickets_list_format(self):
        """Test loading tickets from list format."""
        config_dict = {"tickets": ["SYS-123", "SYS-456", "SYS-789"]}
        result = ConfigManager.load_tickets(config_dict)
        assert result == ["SYS-123", "SYS-456", "SYS-789"]

    def test_load_tickets_with_whitespace(self):
        """Test loading tickets strips whitespace."""
        config_dict = {"tickets": ["  SYS-123  ", "SYS-456 ", " SYS-789"]}
        result = ConfigManager.load_tickets(config_dict)
        assert result == ["SYS-123", "SYS-456", "SYS-789"]

    def test_load_tickets_filters_empty(self):
        """Test loading tickets filters empty values."""
        config_dict = {"tickets": ["SYS-123", "", None, "SYS-456"]}
        result = ConfigManager.load_tickets(config_dict)
        assert result == ["SYS-123", "SYS-456"]

    def test_load_tickets_missing_section(self):
        """Test error when tickets section is missing."""
        config_dict = {}
        with pytest.raises(ValidationError, match="No 'tickets' section found"):
            ConfigManager.load_tickets(config_dict)

    def test_load_tickets_empty_list(self):
        """Test error when tickets list is empty."""
        config_dict = {"tickets": []}
        with pytest.raises(ValidationError, match="No tickets found"):
            ConfigManager.load_tickets(config_dict)


@pytest.mark.unit
class TestConfigManagerLoad:
    """Test cases for ConfigManager.load method."""

    def test_load_from_env_only(self, monkeypatch):
        """Test loading config from environment variables only."""
        monkeypatch.setenv("JIRA_SERVER_URL", "https://example.atlassian.net")
        monkeypatch.setenv("EMAIL", "test@example.com")
        monkeypatch.setenv("API_KEY", "test-api-key")

        manager = ConfigManager()
        config = manager.load(load_env=True)

        assert isinstance(config, Config)
        assert config.jira.server_url == "https://example.atlassian.net"
        assert config.jira.email == "test@example.com"
        assert config.jira.api_key == "test-api-key"
        assert config.data.input_dir == Path("csv_data")

    def test_load_with_config_file(self, sample_config_yaml, sample_env_file, monkeypatch):
        """Test loading config with YAML file."""
        monkeypatch.setenv("JIRA_SERVER_URL", "https://example.atlassian.net")
        monkeypatch.setenv("EMAIL", "test@example.com")
        monkeypatch.setenv("API_KEY", "test-api-key")

        manager = ConfigManager()
        config = manager.load(config_file=sample_config_yaml, load_env=True)

        assert isinstance(config, Config)
        assert config.jira.server_url == "https://example.atlassian.net"

    def test_load_with_cli_overrides(self, sample_config_yaml, monkeypatch):
        """Test loading config with CLI overrides."""
        monkeypatch.setenv("JIRA_SERVER_URL", "https://example.atlassian.net")
        monkeypatch.setenv("EMAIL", "test@example.com")
        monkeypatch.setenv("API_KEY", "test-api-key")

        cli_overrides = {"output_dir": "/cli/override/output"}

        manager = ConfigManager()
        config = manager.load(
            config_file=sample_config_yaml,
            cli_overrides=cli_overrides,
            load_env=True,
        )

        assert config.data.output_dir == Path("/cli/override/output")

    def test_load_without_env_file(self, monkeypatch):
        """Test loading config without loading .env file."""
        # Set env vars directly
        monkeypatch.setenv("JIRA_SERVER_URL", "https://example.atlassian.net")
        monkeypatch.setenv("EMAIL", "test@example.com")
        monkeypatch.setenv("API_KEY", "test-api-key")

        manager = ConfigManager()
        config = manager.load(load_env=False)

        assert isinstance(config, Config)
        assert config.jira.server_url == "https://example.atlassian.net"


@pytest.mark.unit
class TestConfigManagerFromDict:
    """Test cases for ConfigManager.from_dict method."""

    def test_from_dict_basic(self):
        """Test creating Config from dictionary."""
        config_dict = {
            "jira": {
                "server_url": "https://example.atlassian.net",
                "email": "test@example.com",
                "api_key": "test-api-key",
            },
            "data": {
                "input_dir": "csv_data",
                "output_dir": "summaries",
            },
        }

        config = ConfigManager.from_dict(config_dict)
        assert isinstance(config, Config)
        assert config.jira.server_url == "https://example.atlassian.net"
        assert config.jira.email == "test@example.com"
        assert config.data.input_dir == Path("csv_data")
        assert config.data.output_dir == Path("summaries")

    def test_from_dict_with_temp_dir(self):
        """Test creating Config from dict with temp_dir."""
        config_dict = {
            "jira": {
                "server_url": "https://example.com",
                "email": "test@example.com",
                "api_key": "key",
            },
            "data": {
                "input_dir": "input",
                "output_dir": "output",
                "temp_dir": "temp",
            },
        }

        config = ConfigManager.from_dict(config_dict)
        assert config.data.temp_dir == Path("temp")

    def test_from_dict_with_defaults(self):
        """Test creating Config from dict uses defaults for missing values."""
        config_dict = {
            "jira": {},
            "data": {},
        }

        config = ConfigManager.from_dict(config_dict)
        assert config.jira.server_url == ""
        assert config.jira.email == ""
        assert config.jira.api_key == ""
        assert config.data.input_dir == Path("csv_data")
        assert config.data.output_dir == Path("summaries")
        assert config.data.temp_dir is None


@pytest.mark.unit
class TestConfigManagerEnsureDirectories:
    """Test cases for ConfigManager.ensure_directories method."""

    def test_ensure_directories_creates_dirs(self, tmp_path, monkeypatch):
        """Test that ensure_directories creates directories."""
        monkeypatch.setenv("JIRA_SERVER_URL", "https://example.atlassian.net")
        monkeypatch.setenv("EMAIL", "test@example.com")
        monkeypatch.setenv("API_KEY", "test-api-key")

        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        temp_dir = tmp_path / "temp"

        cli_overrides = {
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "temp_dir": str(temp_dir),
        }

        manager = ConfigManager()
        manager.load(cli_overrides=cli_overrides, load_env=True)
        manager.ensure_directories()

        assert input_dir.exists()
        assert output_dir.exists()
        assert temp_dir.exists()

    def test_ensure_directories_without_temp(self, tmp_path, monkeypatch):
        """Test ensure_directories with no temp_dir."""
        monkeypatch.setenv("JIRA_SERVER_URL", "https://example.atlassian.net")
        monkeypatch.setenv("EMAIL", "test@example.com")
        monkeypatch.setenv("API_KEY", "test-api-key")

        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"

        cli_overrides = {
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
        }

        manager = ConfigManager()
        manager.load(cli_overrides=cli_overrides, load_env=True)
        manager.ensure_directories()

        assert input_dir.exists()
        assert output_dir.exists()


@pytest.mark.unit
class TestModuleLevelFunctions:
    """Test cases for module-level functions."""

    def test_load_config_function(self, monkeypatch):
        """Test module-level load_config function."""
        monkeypatch.setenv("JIRA_SERVER_URL", "https://example.atlassian.net")
        monkeypatch.setenv("EMAIL", "test@example.com")
        monkeypatch.setenv("API_KEY", "test-api-key")

        config = load_config()
        assert isinstance(config, Config)
        assert config.jira.server_url == "https://example.atlassian.net"

    def test_get_config_function(self, monkeypatch):
        """Test module-level get_config function."""
        monkeypatch.setenv("JIRA_SERVER_URL", "https://example.atlassian.net")
        monkeypatch.setenv("EMAIL", "test@example.com")
        monkeypatch.setenv("API_KEY", "test-api-key")

        # Load config first
        load_config()

        # Get config should return the loaded config
        config = get_config()
        assert config is not None
        assert isinstance(config, Config)


@pytest.mark.unit
class TestConfigIntegration:
    """Integration tests for config loading with multiple sources."""

    def test_priority_cli_over_yaml(self, sample_config_yaml, monkeypatch):
        """Test that CLI args take priority over YAML config."""
        monkeypatch.setenv("JIRA_SERVER_URL", "https://example.atlassian.net")
        monkeypatch.setenv("EMAIL", "test@example.com")
        monkeypatch.setenv("API_KEY", "test-api-key")

        # YAML has output_dir: "summaries"
        # CLI override with different value
        cli_overrides = {"output_dir": "/cli/output"}

        manager = ConfigManager()
        config = manager.load(
            config_file=sample_config_yaml,
            cli_overrides=cli_overrides,
            load_env=True,
        )

        assert config.data.output_dir == Path("/cli/output")

    def test_yaml_over_defaults(self, tmp_config_dir, monkeypatch):
        """Test that YAML config takes priority over defaults."""
        monkeypatch.setenv("JIRA_SERVER_URL", "https://example.atlassian.net")
        monkeypatch.setenv("EMAIL", "test@example.com")
        monkeypatch.setenv("API_KEY", "test-api-key")

        # Create YAML with custom input_dir
        config_file = tmp_config_dir / "config.yaml"
        yaml_content = {
            "tickets": ["SYS-123"],
            "data": {"input_dir": "/yaml/input"},
        }
        with open(config_file, "w") as f:
            yaml.dump(yaml_content, f)

        manager = ConfigManager()
        config = manager.load(config_file=config_file, load_env=True)

        # Should use YAML value, not default "csv_data"
        assert config.data.input_dir == Path("/yaml/input")
        # Should use default for output_dir
        assert config.data.output_dir == Path("summaries")


@pytest.mark.unit
class TestConfigErrorHandling:
    """Test error handling in config loading."""

    def test_error_on_missing_jira_config(self, monkeypatch):
        """Test that missing Jira config raises ValidationError."""
        # Don't set any Jira environment variables
        monkeypatch.delenv("JIRA_SERVER_URL", raising=False)
        monkeypatch.delenv("EMAIL", raising=False)
        monkeypatch.delenv("API_KEY", raising=False)

        manager = ConfigManager()
        with pytest.raises(ValidationError):
            # Don't load .env file since we're testing missing env vars
            manager.load(load_env=False)

    def test_error_on_invalid_yaml_syntax(self, tmp_config_dir, monkeypatch):
        """Test that invalid YAML raises ConfigurationError."""
        monkeypatch.setenv("JIRA_SERVER_URL", "https://example.atlassian.net")
        monkeypatch.setenv("EMAIL", "test@example.com")
        monkeypatch.setenv("API_KEY", "test-api-key")

        config_file = tmp_config_dir / "config.yaml"
        config_file.write_text("invalid: yaml: [[[")

        manager = ConfigManager()
        with pytest.raises(ConfigurationError):
            manager.load(config_file=config_file, load_env=True)

    def test_error_on_nonexistent_explicit_config(self, tmp_config_dir, monkeypatch):
        """Test that non-existent explicit config file raises ConfigurationError."""
        monkeypatch.setenv("JIRA_SERVER_URL", "https://example.atlassian.net")
        monkeypatch.setenv("EMAIL", "test@example.com")
        monkeypatch.setenv("API_KEY", "test-api-key")

        config_file = tmp_config_dir / "nonexistent.yaml"

        manager = ConfigManager()
        with pytest.raises(ConfigurationError, match="Specified config file not found"):
            manager.load(config_file=config_file, load_env=True)
