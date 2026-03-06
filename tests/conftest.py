"""Pytest configuration and shared fixtures for BH Galaxy Data Analysis Tool tests."""

import tempfile
from pathlib import Path
from typing import Dict

import pandas as pd
import pytest

from bh_glx_data.core.config import ConfigManager
from bh_glx_data.core.models import (
    Config,
    DataConfig,
    FailureSignature,
    JiraConfig,
    PortMetadata,
    PortType,
    TestResult,
    TestStatus,
    TestType,
    TrainMode,
)


@pytest.fixture
def tmp_config_dir(tmp_path):
    """Create a temporary configuration directory.

    Args:
        tmp_path: Pytest's temporary path fixture

    Returns:
        Path to temporary config directory
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create temporary data directories.

    Args:
        tmp_path: Pytest's temporary path fixture

    Returns:
        Dictionary with paths to input_dir, output_dir, temp_dir
    """
    input_dir = tmp_path / "csv_data"
    output_dir = tmp_path / "summaries"
    temp_dir = tmp_path / "temp"

    input_dir.mkdir()
    output_dir.mkdir()
    temp_dir.mkdir()

    return {"input_dir": input_dir, "output_dir": output_dir, "temp_dir": temp_dir}


@pytest.fixture
def sample_jira_config():
    """Sample Jira configuration for testing.

    Returns:
        JiraConfig object
    """
    return JiraConfig(
        server_url="https://example.atlassian.net",
        email="test@example.com",
        api_key="test-api-key-12345",
    )


@pytest.fixture
def sample_data_config(tmp_data_dir):
    """Sample data configuration for testing.

    Args:
        tmp_data_dir: Temporary data directory fixture

    Returns:
        DataConfig object
    """
    return DataConfig(
        input_dir=tmp_data_dir["input_dir"],
        output_dir=tmp_data_dir["output_dir"],
        temp_dir=tmp_data_dir["temp_dir"],
    )


@pytest.fixture
def sample_config(sample_jira_config, sample_data_config):
    """Sample complete configuration for testing.

    Args:
        sample_jira_config: Jira configuration fixture
        sample_data_config: Data configuration fixture

    Returns:
        Config object
    """
    return Config(jira=sample_jira_config, data=sample_data_config)


@pytest.fixture
def sample_config_dict():
    """Sample configuration dictionary for testing.

    Returns:
        Dictionary with configuration values
    """
    return {
        "jira": {
            "server_url": "https://example.atlassian.net",
            "email": "test@example.com",
            "api_key": "test-api-key-12345",
        },
        "data": {"input_dir": "csv_data", "output_dir": "summaries", "temp_dir": "temp"},
        "tickets": ["SYS-123", "SYS-456", "SYS-789"],
    }


@pytest.fixture
def sample_config_yaml(tmp_config_dir, sample_config_dict):
    """Create a sample config.yaml file.

    Args:
        tmp_config_dir: Temporary config directory fixture
        sample_config_dict: Sample configuration dictionary

    Returns:
        Path to config.yaml file
    """
    import yaml

    config_file = tmp_config_dir / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(sample_config_dict, f)
    return config_file


@pytest.fixture
def sample_env_file(tmp_config_dir):
    """Create a sample .env file.

    Args:
        tmp_config_dir: Temporary config directory fixture

    Returns:
        Path to .env file
    """
    env_file = tmp_config_dir / ".env"
    env_content = """JIRA_SERVER_URL=https://example.atlassian.net
EMAIL=test@example.com
API_KEY=test-api-key-12345
"""
    env_file.write_text(env_content)
    return env_file


@pytest.fixture
def sample_test_result():
    """Sample TestResult for testing.

    Returns:
        TestResult object
    """
    return TestResult(
        test_id="test_001",
        bus_id="01:00.0",
        eth_port="ETH00",
        test_status=TestStatus.ETH_ACTIVE,
        test_type=TestType.SERDES_PRBS,
        data={
            "interface": "Ethernet0",
            "host": "bh-glx-b02u02",
            "lcpll_lock_fail_cnt": 0,
            "train_status": {"cdr_unlock_cnt": 0, "retry_cnt": 0},
        },
    )


@pytest.fixture
def sample_failure_result():
    """Sample failed TestResult for testing.

    Returns:
        TestResult object with failure
    """
    return TestResult(
        test_id="test_002",
        bus_id="02:00.0",
        eth_port="ETH01",
        test_status=TestStatus.TRAINING_FAIL,
        test_type=TestType.SIMPLE_PACKET,
        data={
            "interface": "Ethernet1",
            "host": "bh-glx-b02u02",
            "lcpll_lock_fail_cnt": 1,
            "train_status": {"cdr_unlock_cnt": 5, "retry_cnt": 10, "timeout": 1},
        },
    )


@pytest.fixture
def sample_failure_signature():
    """Sample FailureSignature for testing.

    Returns:
        FailureSignature object
    """
    return FailureSignature(
        pattern_name="CDR_UNLOCK_PATTERN",
        indicators={"cdr_unlock_cnt": ">0", "retry_cnt": ">5", "timeout": "1"},
        port_type=PortType.CHIP_TO_QSFPDD,
        train_mode=TrainMode.AW_MANUAL_EQ,
        description="CDR unlock pattern with high retry count",
    )


@pytest.fixture
def sample_port_metadata():
    """Sample PortMetadata for testing.

    Returns:
        PortMetadata object
    """
    return PortMetadata(
        bus_id="01:00.0",
        eth_port="ETH00",
        port_type=PortType.CHIP_TO_CHIP,
        connected_bus_id="02:00.0",
        connected_eth_port="ETH01",
        cable_connector=False,
        serdes_pair="ETH01",
    )


@pytest.fixture
def sample_csv_data():
    """Sample CSV data as pandas DataFrame.

    Returns:
        DataFrame with sample test data
    """
    data = {
        "interface": ["Ethernet0", "Ethernet1", "Ethernet2"],
        "bus_id": ["01:00.0", "01:00.0", "02:00.0"],
        "eth_port": ["ETH00", "ETH01", "ETH00"],
        "test_status": ["ETH_ACTIVE", "TRAINING_FAIL", "ETH_ACTIVE"],
        "test_type": ["SERDES_PRBS", "SIMPLE_PACKET", "SERDES_PRBS"],
        "host": ["bh-glx-b02u02", "bh-glx-b02u02", "bh-glx-b02u02"],
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_csv_file(tmp_data_dir, sample_csv_data):
    """Create a sample CSV file with test data.

    Args:
        tmp_data_dir: Temporary data directory fixture
        sample_csv_data: Sample CSV data DataFrame

    Returns:
        Path to CSV file
    """
    csv_file = tmp_data_dir["input_dir"] / "sample_test_data.csv"
    sample_csv_data.to_csv(csv_file, index=False)
    return csv_file


@pytest.fixture
def sample_failure_csv_data():
    """Sample CSV data with failures as pandas DataFrame.

    Returns:
        DataFrame with failure test data
    """
    data = {
        "interface": ["Ethernet0", "Ethernet1"],
        "bus_id": ["01:00.0", "02:00.0"],
        "eth_port": ["ETH00", "ETH01"],
        "test_status": ["TRAINING_FAIL", "TRAINING_FAIL"],
        "test_type": ["SERDES_PRBS", "SIMPLE_PACKET"],
        "host": ["bh-glx-b02u02", "bh-glx-b02u02"],
        "lcpll_lock_fail_cnt": [0, 1],
        "train_status": [
            "{'cdr_unlock_cnt': 5, 'retry_cnt': 10}",
            "{'cdr_unlock_cnt': 0, 'retry_cnt': 0}",
        ],
    }
    return pd.DataFrame(data)


@pytest.fixture
def config_manager():
    """Create a ConfigManager instance for testing.

    Returns:
        ConfigManager object
    """
    return ConfigManager()


@pytest.fixture
def mock_jira_client(monkeypatch):
    """Mock Jira client for testing (placeholder for future use).

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        Mock Jira client object
    """
    # Placeholder for future Jira client mocking
    pass


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests that don't require external dependencies")
    config.addinivalue_line(
        "markers", "integration: Integration tests that may require external resources"
    )
    config.addinivalue_line("markers", "slow: Slow running tests")
