"""Hardware topology module for BH Galaxy platform.

This module provides functionality to:
- Query ETH port connectivity between chips
- Get cable connector and platform connection information
- Format device and port identifiers
- Navigate the platform topology
"""

from bh_glx_data.hardware.platform_topology import (
    CABLE_CONNECTOR_PORTS_BY_CHIP,
    PLATFORM_TOPOLOGY,
    UNCONNECTED_PORTS,
    UNUSED_PORTS,
    format_device_info,
    get_all_connections_for_device,
    get_chip_from_bus_id,
    get_connected_port,
    get_port_status,
    get_ubb_from_bus_id,
    normalize_bus_id,
    normalize_eth_port,
)

__all__ = [
    "PLATFORM_TOPOLOGY",
    "CABLE_CONNECTOR_PORTS_BY_CHIP",
    "UNUSED_PORTS",
    "UNCONNECTED_PORTS",
    "get_connected_port",
    "get_all_connections_for_device",
    "get_port_status",
    "get_ubb_from_bus_id",
    "get_chip_from_bus_id",
    "format_device_info",
    "normalize_eth_port",
    "normalize_bus_id",
]
