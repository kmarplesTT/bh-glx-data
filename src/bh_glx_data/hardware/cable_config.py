"""Cable configuration management for QSFP port mappings.

This module provides the CableConfigManager class for loading and querying cable
configuration files that map QSFP port connections between UBBs. Cable configurations
define how external cables connect QSFP ports across the platform.

Cable Configuration Format (YAML):
    UBB1:
      - QSFP-1 <> QSFP-2
      - QSFP-3 <> QSFP-5
      - QSFP-7 <> QSFP-8
    UBB2:
      - QSFP-1 <> QSFP-2
      ...

The module supports:
- Named configurations (searched in standard directories)
- Explicit file paths (relative or absolute)
- Bidirectional cable mappings
- Validation of QSFP port numbers (1-14)
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from bh_glx_data.core.exceptions import CableConfigError, ValidationError

# Type alias for cable mapping
# Key: (ubb_num, qsfp_port) -> Value: (dest_ubb, dest_qsfp_port)
CableMapping = Dict[Tuple[int, int], Tuple[int, int]]


class CableConfigManager:
    """Manages cable configuration loading and querying.

    This class handles loading cable configuration files from various sources
    (named configs or file paths), parsing YAML content, validating structure,
    and providing fast lookups for QSFP-to-QSFP connections.

    Attributes:
        CONFIG_SEARCH_PATHS: Default search paths for named configurations

    Example:
        >>> manager = CableConfigManager()
        >>> manager.load("QC3")  # Load named config
        >>> dest = manager.get_connected_qsfp(1, 7)  # Query UBB1 QSFP-7
        >>> print(dest)  # (1, 8) - connects to UBB1 QSFP-8
    """

    # Search paths for named configurations
    CONFIG_SEARCH_PATHS: List[Path] = [
        Path.home() / ".config" / "bh-glx-data" / "cables",
        Path("cables"),
    ]

    def __init__(self):
        """Initialize the cable config manager."""
        self._config: Optional[CableMapping] = None
        self._config_path: Optional[Path] = None

    def load(self, config_spec: str) -> None:
        """Load cable configuration from named config or file path.

        This method finds the configuration file (either by searching standard
        directories for named configs or using an explicit path), parses the
        YAML content, validates the structure, and builds the internal mapping.

        Args:
            config_spec: Either a named config (e.g., "QC3") or file path
                        (e.g., "./custom-cables.yaml" or "/path/to/config.yaml")

        Raises:
            CableConfigError: If config file not found or loading fails
            ValidationError: If config structure or data is invalid
        """
        try:
            config_file = self._find_config_file(config_spec)
            config_dict = self._parse_yaml_config(config_file)
            self._config = self._build_cable_mapping(config_dict)
            self._config_path = config_file
        except (CableConfigError, ValidationError):
            raise
        except Exception as e:
            raise CableConfigError(
                f"Unexpected error loading cable configuration: {e}", config_spec
            ) from e

    def _find_config_file(self, config_spec: str) -> Path:
        """Find config file from named config or explicit path.

        Strategy:
        1. If config_spec contains "/" or ends with ".yaml", treat as file path
        2. Otherwise, search named configs in CONFIG_SEARCH_PATHS:
           - ~/.config/bh-glx-data/cables/{config_spec}.yaml
           - ./cables/{config_spec}.yaml

        Args:
            config_spec: Config name or file path

        Returns:
            Path to config file

        Raises:
            CableConfigError: If file not found
        """
        # Check if it looks like a file path
        if "/" in config_spec or config_spec.endswith(".yaml"):
            path = Path(config_spec)
            if path.exists() and path.is_file():
                return path
            raise CableConfigError(
                f"Cable config file not found: {config_spec}", config_spec
            )

        # Search for named config in standard directories
        for search_dir in self.CONFIG_SEARCH_PATHS:
            config_file = search_dir / f"{config_spec}.yaml"
            if config_file.exists() and config_file.is_file():
                return config_file

        # Not found in any location
        search_paths_str = ", ".join(str(p) for p in self.CONFIG_SEARCH_PATHS)
        raise CableConfigError(
            f"Named cable config '{config_spec}' not found in: {search_paths_str}",
            config_spec,
        )

    def _parse_yaml_config(self, config_file: Path) -> Dict[str, Any]:
        """Parse YAML config file and validate structure.

        Validates:
        - File is valid YAML
        - Has at least one UBB section (UBB1, UBB2, UBB3, or UBB4)
        - Each UBB section contains a list of connections

        Args:
            config_file: Path to YAML config file

        Returns:
            Parsed YAML as dictionary

        Raises:
            CableConfigError: If parsing fails
            ValidationError: If structure validation fails
        """
        try:
            with open(config_file, "r") as f:
                config_dict = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise CableConfigError(
                f"Error parsing YAML file '{config_file}': {e}", str(config_file)
            ) from e
        except Exception as e:
            raise CableConfigError(
                f"Error reading config file '{config_file}': {e}", str(config_file)
            ) from e

        # Validate structure
        if not isinstance(config_dict, dict):
            raise ValidationError(f"Config file must contain a YAML dictionary")

        # Check for at least one UBB section
        valid_ubbs = {"UBB1", "UBB2", "UBB3", "UBB4"}
        found_ubbs = set(config_dict.keys()) & valid_ubbs
        if not found_ubbs:
            raise ValidationError(
                f"Config file must contain at least one UBB section (UBB1-UBB4)"
            )

        # Validate each UBB section is a list
        for ubb_name in found_ubbs:
            if config_dict[ubb_name] is not None and not isinstance(
                config_dict[ubb_name], list
            ):
                raise ValidationError(f"{ubb_name} section must be a list of connections")

        return config_dict

    def _build_cable_mapping(self, config_dict: Dict[str, Any]) -> CableMapping:
        """Build bidirectional cable mapping from parsed YAML.

        Parses connection strings in the format "QSFP-X <> QSFP-Y" and builds
        a bidirectional mapping:
        - Input: "UBB1: [QSFP-1 <> QSFP-2]"
        - Output: {(1, 1): (1, 2), (1, 2): (1, 1)}

        Args:
            config_dict: Parsed YAML config dictionary

        Returns:
            Cable mapping structure ready for lookup

        Raises:
            ValidationError: If connection format invalid or QSFP port out of range
        """
        mapping: CableMapping = {}

        # Pattern to match "QSFP-X <> QSFP-Y"
        connection_pattern = re.compile(r"QSFP-(\d+)\s*<>\s*QSFP-(\d+)", re.IGNORECASE)

        # Process each UBB
        for ubb_name, connections in config_dict.items():
            # Extract UBB number (UBB1 -> 1, etc.)
            if not ubb_name.startswith("UBB"):
                continue

            try:
                ubb_num = int(ubb_name[3:])
            except (ValueError, IndexError):
                raise ValidationError(f"Invalid UBB name: {ubb_name}")

            if not (1 <= ubb_num <= 4):
                raise ValidationError(f"UBB number must be 1-4, got: {ubb_num}")

            # Skip if no connections for this UBB
            if connections is None:
                continue

            # Parse each connection
            for connection in connections:
                if not isinstance(connection, str):
                    raise ValidationError(
                        f"Connection must be a string, got: {type(connection)}"
                    )

                match = connection_pattern.match(connection.strip())
                if not match:
                    raise ValidationError(
                        f"Invalid connection format: '{connection}'. "
                        f"Expected format: 'QSFP-X <> QSFP-Y'"
                    )

                qsfp_a = int(match.group(1))
                qsfp_b = int(match.group(2))

                # Validate QSFP port numbers (1-14)
                for qsfp_port in [qsfp_a, qsfp_b]:
                    if not (1 <= qsfp_port <= 14):
                        raise ValidationError(
                            f"Invalid QSFP port: {qsfp_port}. Must be 1-14"
                        )

                # Add bidirectional mapping
                # (ubb, qsfp_a) -> (ubb, qsfp_b)
                # (ubb, qsfp_b) -> (ubb, qsfp_a)
                mapping[(ubb_num, qsfp_a)] = (ubb_num, qsfp_b)
                mapping[(ubb_num, qsfp_b)] = (ubb_num, qsfp_a)

        return mapping

    def get_connected_qsfp(
        self, ubb_num: int, qsfp_port: int
    ) -> Optional[Tuple[int, int]]:
        """Get the connected QSFP port for a given QSFP.

        Args:
            ubb_num: UBB number (1-4)
            qsfp_port: QSFP port number (1-14)

        Returns:
            Tuple of (dest_ubb, dest_qsfp_port) or None if not connected

        Example:
            >>> manager.get_connected_qsfp(1, 7)
            (1, 8)  # UBB1 QSFP-7 connects to UBB1 QSFP-8
        """
        if not self._config:
            return None
        return self._config.get((ubb_num, qsfp_port))

    def is_loaded(self) -> bool:
        """Check if configuration is loaded.

        Returns:
            True if config loaded, False otherwise
        """
        return self._config is not None

    @property
    def config_path(self) -> Optional[Path]:
        """Return the path to the loaded config file.

        Returns:
            Path to loaded config file or None if not loaded
        """
        return self._config_path
