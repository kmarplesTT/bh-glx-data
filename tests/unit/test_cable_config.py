"""Unit tests for cable configuration management."""

import pytest
from pathlib import Path
from bh_glx_data.hardware.cable_config import CableConfigManager
from bh_glx_data.core.exceptions import CableConfigError, ValidationError


class TestCableConfigManager:
    """Test cable configuration loading and management."""

    def test_init(self):
        """Test CableConfigManager initialization."""
        manager = CableConfigManager()
        assert not manager.is_loaded()
        assert manager.config_path is None

    def test_load_file_path_config(self, tmp_path):
        """Test loading config from explicit file path."""
        config_content = """
UBB1:
  - QSFP-1 <> QSFP-2
  - QSFP-7 <> QSFP-8
UBB2:
  - QSFP-1 <> QSFP-2
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)

        manager = CableConfigManager()
        manager.load(str(config_file))

        assert manager.is_loaded()
        assert manager.config_path == config_file

        # Test lookups
        assert manager.get_connected_qsfp(1, 1) == (1, 2)
        assert manager.get_connected_qsfp(1, 2) == (1, 1)
        assert manager.get_connected_qsfp(1, 7) == (1, 8)
        assert manager.get_connected_qsfp(2, 1) == (2, 2)

    def test_load_named_config(self, tmp_path, monkeypatch):
        """Test loading named config from search paths."""
        # Create a config in a temporary "cables" directory
        cables_dir = tmp_path / "cables"
        cables_dir.mkdir()
        config_file = cables_dir / "test_qc3.yaml"
        config_file.write_text("""
UBB1:
  - QSFP-1 <> QSFP-2
""")

        # Temporarily override search paths
        manager = CableConfigManager()
        manager.CONFIG_SEARCH_PATHS = [cables_dir]

        manager.load("test_qc3")

        assert manager.is_loaded()
        assert manager.config_path == config_file

    def test_config_file_not_found_explicit_path(self):
        """Test error when explicit config file path not found."""
        manager = CableConfigManager()

        with pytest.raises(CableConfigError) as exc_info:
            manager.load("/nonexistent/path/config.yaml")

        assert "not found" in str(exc_info.value).lower()

    def test_config_file_not_found_named(self, tmp_path, monkeypatch):
        """Test error when named config not found."""
        # Use empty search path
        manager = CableConfigManager()
        manager.CONFIG_SEARCH_PATHS = [tmp_path / "empty"]

        with pytest.raises(CableConfigError) as exc_info:
            manager.load("nonexistent_config")

        assert "not found" in str(exc_info.value).lower()

    def test_invalid_yaml_format(self, tmp_path):
        """Test error on invalid YAML."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [unclosed")

        manager = CableConfigManager()

        with pytest.raises(CableConfigError) as exc_info:
            manager.load(str(config_file))

        assert "parsing" in str(exc_info.value).lower() or "yaml" in str(exc_info.value).lower()

    def test_missing_ubb_section(self, tmp_path):
        """Test error when UBB section missing."""
        config_file = tmp_path / "no_ubb.yaml"
        config_file.write_text("""
other_section:
  - some data
""")

        manager = CableConfigManager()

        with pytest.raises(ValidationError) as exc_info:
            manager.load(str(config_file))

        assert "ubb" in str(exc_info.value).lower()

    def test_invalid_connection_format(self, tmp_path):
        """Test error on invalid connection format."""
        config_file = tmp_path / "bad_format.yaml"
        config_file.write_text("""
UBB1:
  - QSFP-1 -> QSFP-2
""")

        manager = CableConfigManager()

        with pytest.raises(ValidationError) as exc_info:
            manager.load(str(config_file))

        assert "format" in str(exc_info.value).lower()

    def test_invalid_qsfp_port_number(self, tmp_path):
        """Test error on invalid QSFP port number (>14)."""
        config_file = tmp_path / "bad_port.yaml"
        config_file.write_text("""
UBB1:
  - QSFP-1 <> QSFP-15
""")

        manager = CableConfigManager()

        with pytest.raises(ValidationError) as exc_info:
            manager.load(str(config_file))

        assert "1-14" in str(exc_info.value) or "invalid" in str(exc_info.value).lower()

    def test_parse_yaml_config_valid(self, tmp_path):
        """Test parsing valid YAML config."""
        config_content = """
UBB1:
  - QSFP-1 <> QSFP-2
  - QSFP-3 <> QSFP-5
UBB2:
  - QSFP-7 <> QSFP-8
UBB3:
UBB4:
  - QSFP-9 <> QSFP-10
"""
        config_file = tmp_path / "valid.yaml"
        config_file.write_text(config_content)

        manager = CableConfigManager()
        manager.load(str(config_file))

        assert manager.is_loaded()
        assert manager.get_connected_qsfp(1, 1) == (1, 2)
        assert manager.get_connected_qsfp(1, 3) == (1, 5)
        assert manager.get_connected_qsfp(2, 7) == (2, 8)
        assert manager.get_connected_qsfp(4, 9) == (4, 10)

    def test_build_cable_mapping_bidirectional(self, tmp_path):
        """Test that cable mapping is bidirectional."""
        config_content = """
UBB1:
  - QSFP-1 <> QSFP-2
"""
        config_file = tmp_path / "bidir.yaml"
        config_file.write_text(config_content)

        manager = CableConfigManager()
        manager.load(str(config_file))

        # Both directions should work
        assert manager.get_connected_qsfp(1, 1) == (1, 2)
        assert manager.get_connected_qsfp(1, 2) == (1, 1)

    def test_get_connected_qsfp_valid(self, tmp_path):
        """Test getting connected QSFP port."""
        config_content = """
UBB1:
  - QSFP-7 <> QSFP-8
"""
        config_file = tmp_path / "test.yaml"
        config_file.write_text(config_content)

        manager = CableConfigManager()
        manager.load(str(config_file))

        result = manager.get_connected_qsfp(1, 7)
        assert result == (1, 8)

    def test_get_connected_qsfp_not_connected(self, tmp_path):
        """Test getting QSFP port not in config."""
        config_content = """
UBB1:
  - QSFP-1 <> QSFP-2
"""
        config_file = tmp_path / "test.yaml"
        config_file.write_text(config_content)

        manager = CableConfigManager()
        manager.load(str(config_file))

        result = manager.get_connected_qsfp(1, 7)
        assert result is None

    def test_get_connected_qsfp_not_loaded(self):
        """Test getting QSFP port when config not loaded."""
        manager = CableConfigManager()
        result = manager.get_connected_qsfp(1, 7)
        assert result is None

    def test_is_loaded(self, tmp_path):
        """Test is_loaded check."""
        config_content = """
UBB1:
  - QSFP-1 <> QSFP-2
"""
        config_file = tmp_path / "test.yaml"
        config_file.write_text(config_content)

        manager = CableConfigManager()
        assert not manager.is_loaded()

        manager.load(str(config_file))
        assert manager.is_loaded()

    def test_config_path_property(self, tmp_path):
        """Test config_path property."""
        config_content = """
UBB1:
  - QSFP-1 <> QSFP-2
"""
        config_file = tmp_path / "test.yaml"
        config_file.write_text(config_content)

        manager = CableConfigManager()
        assert manager.config_path is None

        manager.load(str(config_file))
        assert manager.config_path == config_file

    def test_case_insensitive_qsfp_format(self, tmp_path):
        """Test that QSFP format is case insensitive."""
        config_content = """
UBB1:
  - qsfp-1 <> Qsfp-2
"""
        config_file = tmp_path / "case.yaml"
        config_file.write_text(config_content)

        manager = CableConfigManager()
        manager.load(str(config_file))

        assert manager.get_connected_qsfp(1, 1) == (1, 2)

    def test_whitespace_handling(self, tmp_path):
        """Test that whitespace in connections is handled properly."""
        config_content = """
UBB1:
  -   QSFP-1   <>   QSFP-2
  - QSFP-3<>QSFP-4
"""
        config_file = tmp_path / "whitespace.yaml"
        config_file.write_text(config_content)

        manager = CableConfigManager()
        manager.load(str(config_file))

        assert manager.get_connected_qsfp(1, 1) == (1, 2)
        assert manager.get_connected_qsfp(1, 3) == (1, 4)

    def test_multiple_ubbs(self, tmp_path):
        """Test configuration with multiple UBBs."""
        config_content = """
UBB1:
  - QSFP-1 <> QSFP-2
UBB2:
  - QSFP-1 <> QSFP-3
UBB3:
  - QSFP-1 <> QSFP-4
UBB4:
  - QSFP-1 <> QSFP-5
"""
        config_file = tmp_path / "multi_ubb.yaml"
        config_file.write_text(config_content)

        manager = CableConfigManager()
        manager.load(str(config_file))

        assert manager.get_connected_qsfp(1, 1) == (1, 2)
        assert manager.get_connected_qsfp(2, 1) == (2, 3)
        assert manager.get_connected_qsfp(3, 1) == (3, 4)
        assert manager.get_connected_qsfp(4, 1) == (4, 5)

    def test_empty_ubb_section(self, tmp_path):
        """Test that empty UBB sections are handled gracefully."""
        config_content = """
UBB1:
  - QSFP-1 <> QSFP-2
UBB2:
UBB3:
UBB4:
  - QSFP-3 <> QSFP-4
"""
        config_file = tmp_path / "empty_ubb.yaml"
        config_file.write_text(config_content)

        manager = CableConfigManager()
        manager.load(str(config_file))

        assert manager.get_connected_qsfp(1, 1) == (1, 2)
        assert manager.get_connected_qsfp(2, 1) is None
        assert manager.get_connected_qsfp(4, 3) == (4, 4)

    def test_non_dict_yaml(self, tmp_path):
        """Test error when YAML is not a dictionary."""
        config_file = tmp_path / "list.yaml"
        config_file.write_text("- item1\n- item2")

        manager = CableConfigManager()

        with pytest.raises(ValidationError) as exc_info:
            manager.load(str(config_file))

        assert "dictionary" in str(exc_info.value).lower()

    def test_non_list_ubb_section(self, tmp_path):
        """Test error when UBB section is not a list."""
        config_file = tmp_path / "bad_ubb.yaml"
        config_file.write_text("""
UBB1: "string instead of list"
""")

        manager = CableConfigManager()

        with pytest.raises(ValidationError) as exc_info:
            manager.load(str(config_file))

        assert "list" in str(exc_info.value).lower()
