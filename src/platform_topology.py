"""
Blackhole Galaxy Platform Topology Mapping

This module defines the ETH port connectivity between chips (PCIe devices) on the platform.
The platform consists of 4 UBBs, each with 8 chips (U1-U8).

Bus ID format: XY:00.0 where:
- X = UBB identifier (0=UBB1, 4=UBB2, c=UBB3, 8=UBB4)
- Y = Chip number (1-8 for U1-U8)

Each chip has 14 ETH ports (ETH00-ETH13):
- ETH05, ETH08: Unused (not physically present) on all chips
- ETH12, ETH13: Unconnected (not used) on all chips
- Cable connector and platform-connected ports vary by chip position (U1-U8)
  See CABLE_CONNECTOR_PORTS_BY_CHIP and PLATFORM_TOPOLOGY for details
"""

from typing import Dict, Tuple, Optional, Set

# Type aliases for clarity
BusId = str  # Format: "XY:00.0"
EthPort = str  # Format: "ETHX"
Connection = Tuple[BusId, EthPort]  # (bus_id, eth_port)

# Port categories
UNUSED_PORTS: Set[str] = {"ETH05", "ETH08"}  # Not physically present
UNCONNECTED_PORTS: Set[str] = {"ETH12", "ETH13"}  # Not used
ALL_VALID_PORTS: Set[str] = {f"ETH{i:02d}" for i in range(14)}  # ETH00-ETH13

# Cable connector ports by chip position (U1-U8)
# These ports connect to external cables, not to other chips on the platform
CABLE_CONNECTOR_PORTS_BY_CHIP: Dict[int, Set[str]] = {
    1: {"ETH00", "ETH01", "ETH02", "ETH03", "ETH10", "ETH11"},
    2: {"ETH00", "ETH01", "ETH10", "ETH11"},
    3: {"ETH00", "ETH01", "ETH10", "ETH11"},
    4: {"ETH00", "ETH01", "ETH10", "ETH11"},
    5: {"ETH02", "ETH03", "ETH10", "ETH11"},
    6: {"ETH10", "ETH11"},
    7: {"ETH10", "ETH11"},
    8: {"ETH10", "ETH11"},
}

# Platform topology mapping
# Key: (source_bus_id, source_eth_port)
# Value: (destination_bus_id, destination_eth_port)
PLATFORM_TOPOLOGY: Dict[Connection, Connection] = {
    # UBB1 - U1 (01:00.0)
    ("01:00.0", "ETH04"): ("02:00.0", "ETH02"),
    ("01:00.0", "ETH06"): ("02:00.0", "ETH03"),
    ("01:00.0", "ETH07"): ("05:00.0", "ETH00"),
    ("01:00.0", "ETH09"): ("05:00.0", "ETH01"),
    # UBB1 - U2 (02:00.0)
    ("02:00.0", "ETH02"): ("01:00.0", "ETH04"),
    ("02:00.0", "ETH03"): ("01:00.0", "ETH06"),
    ("02:00.0", "ETH04"): ("03:00.0", "ETH02"),
    ("02:00.0", "ETH06"): ("03:00.0", "ETH03"),
    ("02:00.0", "ETH07"): ("06:00.0", "ETH00"),
    ("02:00.0", "ETH09"): ("06:00.0", "ETH01"),
    # UBB1 - U3 (03:00.0)
    ("03:00.0", "ETH02"): ("02:00.0", "ETH04"),
    ("03:00.0", "ETH03"): ("02:00.0", "ETH06"),
    ("03:00.0", "ETH04"): ("04:00.0", "ETH02"),
    ("03:00.0", "ETH06"): ("04:00.0", "ETH03"),
    ("03:00.0", "ETH07"): ("07:00.0", "ETH00"),
    ("03:00.0", "ETH09"): ("07:00.0", "ETH01"),
    # UBB1 - U4 (04:00.0)
    ("04:00.0", "ETH02"): ("03:00.0", "ETH04"),
    ("04:00.0", "ETH03"): ("03:00.0", "ETH06"),
    ("04:00.0", "ETH04"): ("44:00.0", "ETH04"),
    ("04:00.0", "ETH06"): ("44:00.0", "ETH06"),
    ("04:00.0", "ETH07"): ("08:00.0", "ETH00"),
    ("04:00.0", "ETH09"): ("08:00.0", "ETH01"),
    # UBB1 - U5 (05:00.0)
    ("05:00.0", "ETH00"): ("01:00.0", "ETH07"),
    ("05:00.0", "ETH01"): ("01:00.0", "ETH09"),
    ("05:00.0", "ETH04"): ("06:00.0", "ETH02"),
    ("05:00.0", "ETH06"): ("06:00.0", "ETH03"),
    ("05:00.0", "ETH07"): ("c5:00.0", "ETH07"),
    ("05:00.0", "ETH09"): ("c5:00.0", "ETH09"),
    # UBB1 - U6 (06:00.0)
    ("06:00.0", "ETH00"): ("02:00.0", "ETH07"),
    ("06:00.0", "ETH01"): ("02:00.0", "ETH09"),
    ("06:00.0", "ETH02"): ("05:00.0", "ETH04"),
    ("06:00.0", "ETH03"): ("05:00.0", "ETH06"),
    ("06:00.0", "ETH04"): ("07:00.0", "ETH02"),
    ("06:00.0", "ETH06"): ("07:00.0", "ETH03"),
    ("06:00.0", "ETH07"): ("c6:00.0", "ETH07"),
    ("06:00.0", "ETH09"): ("c6:00.0", "ETH09"),
    # UBB1 - U7 (07:00.0)
    ("07:00.0", "ETH00"): ("03:00.0", "ETH07"),
    ("07:00.0", "ETH01"): ("03:00.0", "ETH09"),
    ("07:00.0", "ETH02"): ("06:00.0", "ETH04"),
    ("07:00.0", "ETH03"): ("06:00.0", "ETH06"),
    ("07:00.0", "ETH04"): ("08:00.0", "ETH02"),
    ("07:00.0", "ETH06"): ("08:00.0", "ETH03"),
    ("07:00.0", "ETH07"): ("c7:00.0", "ETH07"),
    ("07:00.0", "ETH09"): ("c7:00.0", "ETH09"),
    # UBB1 - U8 (08:00.0)
    ("08:00.0", "ETH00"): ("04:00.0", "ETH07"),
    ("08:00.0", "ETH01"): ("04:00.0", "ETH09"),
    ("08:00.0", "ETH02"): ("07:00.0", "ETH04"),
    ("08:00.0", "ETH03"): ("07:00.0", "ETH06"),
    ("08:00.0", "ETH04"): ("48:00.0", "ETH04"),
    ("08:00.0", "ETH06"): ("48:00.0", "ETH06"),
    ("08:00.0", "ETH07"): ("c8:00.0", "ETH07"),
    ("08:00.0", "ETH09"): ("c8:00.0", "ETH09"),
    # UBB2 - U1 (41:00.0)
    ("41:00.0", "ETH04"): ("42:00.0", "ETH02"),
    ("41:00.0", "ETH06"): ("42:00.0", "ETH03"),
    ("41:00.0", "ETH07"): ("45:00.0", "ETH00"),
    ("41:00.0", "ETH09"): ("45:00.0", "ETH01"),
    # UBB2 - U2 (42:00.0)
    ("42:00.0", "ETH02"): ("41:00.0", "ETH04"),
    ("42:00.0", "ETH03"): ("41:00.0", "ETH06"),
    ("42:00.0", "ETH04"): ("43:00.0", "ETH02"),
    ("42:00.0", "ETH06"): ("43:00.0", "ETH03"),
    ("42:00.0", "ETH07"): ("46:00.0", "ETH00"),
    ("42:00.0", "ETH09"): ("46:00.0", "ETH01"),
    # UBB2 - U3 (43:00.0)
    ("43:00.0", "ETH02"): ("42:00.0", "ETH04"),
    ("43:00.0", "ETH03"): ("42:00.0", "ETH06"),
    ("43:00.0", "ETH04"): ("44:00.0", "ETH02"),
    ("43:00.0", "ETH06"): ("44:00.0", "ETH03"),
    ("43:00.0", "ETH07"): ("47:00.0", "ETH00"),
    ("43:00.0", "ETH09"): ("47:00.0", "ETH01"),
    # UBB2 - U4 (44:00.0)
    ("44:00.0", "ETH02"): ("43:00.0", "ETH04"),
    ("44:00.0", "ETH03"): ("43:00.0", "ETH06"),
    ("44:00.0", "ETH04"): ("04:00.0", "ETH04"),
    ("44:00.0", "ETH06"): ("04:00.0", "ETH06"),
    ("44:00.0", "ETH07"): ("48:00.0", "ETH00"),
    ("44:00.0", "ETH09"): ("48:00.0", "ETH01"),
    # UBB2 - U5 (45:00.0)
    ("45:00.0", "ETH00"): ("41:00.0", "ETH07"),
    ("45:00.0", "ETH01"): ("41:00.0", "ETH09"),
    ("45:00.0", "ETH04"): ("46:00.0", "ETH02"),
    ("45:00.0", "ETH06"): ("46:00.0", "ETH03"),
    ("45:00.0", "ETH07"): ("85:00.0", "ETH07"),
    ("45:00.0", "ETH09"): ("85:00.0", "ETH09"),
    # UBB2 - U6 (46:00.0)
    ("46:00.0", "ETH00"): ("42:00.0", "ETH07"),
    ("46:00.0", "ETH01"): ("42:00.0", "ETH09"),
    ("46:00.0", "ETH02"): ("45:00.0", "ETH04"),
    ("46:00.0", "ETH03"): ("45:00.0", "ETH06"),
    ("46:00.0", "ETH04"): ("47:00.0", "ETH02"),
    ("46:00.0", "ETH06"): ("47:00.0", "ETH03"),
    ("46:00.0", "ETH07"): ("86:00.0", "ETH07"),
    ("46:00.0", "ETH09"): ("86:00.0", "ETH09"),
    # UBB2 - U7 (47:00.0)
    ("47:00.0", "ETH00"): ("43:00.0", "ETH07"),
    ("47:00.0", "ETH01"): ("43:00.0", "ETH09"),
    ("47:00.0", "ETH02"): ("46:00.0", "ETH04"),
    ("47:00.0", "ETH03"): ("46:00.0", "ETH06"),
    ("47:00.0", "ETH04"): ("48:00.0", "ETH02"),
    ("47:00.0", "ETH06"): ("48:00.0", "ETH03"),
    ("47:00.0", "ETH07"): ("87:00.0", "ETH07"),
    ("47:00.0", "ETH09"): ("87:00.0", "ETH09"),
    # UBB2 - U8 (48:00.0)
    ("48:00.0", "ETH00"): ("44:00.0", "ETH07"),
    ("48:00.0", "ETH01"): ("44:00.0", "ETH09"),
    ("48:00.0", "ETH02"): ("47:00.0", "ETH04"),
    ("48:00.0", "ETH03"): ("47:00.0", "ETH06"),
    ("48:00.0", "ETH04"): ("08:00.0", "ETH04"),
    ("48:00.0", "ETH06"): ("08:00.0", "ETH06"),
    ("48:00.0", "ETH07"): ("88:00.0", "ETH07"),
    ("48:00.0", "ETH09"): ("88:00.0", "ETH09"),

    # UBB3 - U1 (c1:00.0)
    ("c1:00.0", "ETH04"): ("c2:00.0", "ETH02"),
    ("c1:00.0", "ETH06"): ("c2:00.0", "ETH03"),
    ("c1:00.0", "ETH07"): ("c5:00.0", "ETH00"),
    ("c1:00.0", "ETH09"): ("c5:00.0", "ETH01"),
    # UBB3 - U2 (c2:00.0)
    ("c2:00.0", "ETH02"): ("c1:00.0", "ETH04"),
    ("c2:00.0", "ETH03"): ("c1:00.0", "ETH06"),
    ("c2:00.0", "ETH04"): ("c3:00.0", "ETH02"),
    ("c2:00.0", "ETH06"): ("c3:00.0", "ETH03"),
    ("c2:00.0", "ETH07"): ("c6:00.0", "ETH00"),
    ("c2:00.0", "ETH09"): ("c6:00.0", "ETH01"),
    # UBB3 - U3 (c3:00.0)
    ("c3:00.0", "ETH02"): ("c2:00.0", "ETH04"),
    ("c3:00.0", "ETH03"): ("c2:00.0", "ETH06"),
    ("c3:00.0", "ETH04"): ("c4:00.0", "ETH02"),
    ("c3:00.0", "ETH06"): ("c4:00.0", "ETH03"),
    ("c3:00.0", "ETH07"): ("c7:00.0", "ETH00"),
    ("c3:00.0", "ETH09"): ("c7:00.0", "ETH01"),
    # UBB3 - U4 (c4:00.0)
    ("c4:00.0", "ETH02"): ("c3:00.0", "ETH04"),
    ("c4:00.0", "ETH03"): ("c3:00.0", "ETH06"),
    ("c4:00.0", "ETH04"): ("84:00.0", "ETH04"),
    ("c4:00.0", "ETH06"): ("84:00.0", "ETH06"),
    ("c4:00.0", "ETH07"): ("c8:00.0", "ETH00"),
    ("c4:00.0", "ETH09"): ("c8:00.0", "ETH01"),
    # UBB3 - U5 (c5:00.0)
    ("c5:00.0", "ETH00"): ("c1:00.0", "ETH07"),
    ("c5:00.0", "ETH01"): ("c1:00.0", "ETH09"),
    ("c5:00.0", "ETH04"): ("c6:00.0", "ETH02"),
    ("c5:00.0", "ETH06"): ("c6:00.0", "ETH03"),
    ("c5:00.0", "ETH07"): ("05:00.0", "ETH07"),
    ("c5:00.0", "ETH09"): ("05:00.0", "ETH09"),
    # UBB3 - U6 (c6:00.0)
    ("c6:00.0", "ETH00"): ("c2:00.0", "ETH07"),
    ("c6:00.0", "ETH01"): ("c2:00.0", "ETH09"),
    ("c6:00.0", "ETH02"): ("c5:00.0", "ETH04"),
    ("c6:00.0", "ETH03"): ("c5:00.0", "ETH06"),
    ("c6:00.0", "ETH04"): ("c7:00.0", "ETH02"),
    ("c6:00.0", "ETH06"): ("c7:00.0", "ETH03"),
    ("c6:00.0", "ETH07"): ("06:00.0", "ETH07"),
    ("c6:00.0", "ETH09"): ("06:00.0", "ETH09"),
    # UBB3 - U7 (c7:00.0)
    ("c7:00.0", "ETH00"): ("c3:00.0", "ETH07"),
    ("c7:00.0", "ETH01"): ("c3:00.0", "ETH09"),
    ("c7:00.0", "ETH02"): ("c6:00.0", "ETH04"),
    ("c7:00.0", "ETH03"): ("c6:00.0", "ETH06"),
    ("c7:00.0", "ETH04"): ("c8:00.0", "ETH02"),
    ("c7:00.0", "ETH06"): ("c8:00.0", "ETH03"),
    ("c7:00.0", "ETH07"): ("07:00.0", "ETH07"),
    ("c7:00.0", "ETH09"): ("07:00.0", "ETH09"),
    # UBB3 - U8 (c8:00.0)
    ("c8:00.0", "ETH00"): ("c4:00.0", "ETH07"),
    ("c8:00.0", "ETH01"): ("c4:00.0", "ETH09"),
    ("c8:00.0", "ETH02"): ("c7:00.0", "ETH04"),
    ("c8:00.0", "ETH03"): ("c7:00.0", "ETH06"),
    ("c8:00.0", "ETH04"): ("88:00.0", "ETH04"),
    ("c8:00.0", "ETH06"): ("88:00.0", "ETH06"),
    ("c8:00.0", "ETH07"): ("08:00.0", "ETH07"),
    ("c8:00.0", "ETH09"): ("08:00.0", "ETH09"),

    # UBB4 - U1 (81:00.0)
    ("81:00.0", "ETH04"): ("82:00.0", "ETH02"),
    ("81:00.0", "ETH06"): ("82:00.0", "ETH03"),
    ("81:00.0", "ETH07"): ("85:00.0", "ETH00"),
    ("81:00.0", "ETH09"): ("85:00.0", "ETH01"),
    # UBB4 - U2 (82:00.0)
    ("82:00.0", "ETH02"): ("81:00.0", "ETH04"),
    ("82:00.0", "ETH03"): ("81:00.0", "ETH06"),
    ("82:00.0", "ETH04"): ("83:00.0", "ETH02"),
    ("82:00.0", "ETH06"): ("83:00.0", "ETH03"),
    ("82:00.0", "ETH07"): ("86:00.0", "ETH00"),
    ("82:00.0", "ETH09"): ("86:00.0", "ETH01"),
    # UBB4 - U3 (83:00.0)
    ("83:00.0", "ETH02"): ("82:00.0", "ETH04"),
    ("83:00.0", "ETH03"): ("82:00.0", "ETH06"),
    ("83:00.0", "ETH04"): ("84:00.0", "ETH02"),
    ("83:00.0", "ETH06"): ("84:00.0", "ETH03"),
    ("83:00.0", "ETH07"): ("87:00.0", "ETH00"),
    ("83:00.0", "ETH09"): ("87:00.0", "ETH01"),
    # UBB4 - U4 (84:00.0)
    ("84:00.0", "ETH02"): ("83:00.0", "ETH04"),
    ("84:00.0", "ETH03"): ("83:00.0", "ETH06"),
    ("84:00.0", "ETH04"): ("c4:00.0", "ETH04"),
    ("84:00.0", "ETH06"): ("c4:00.0", "ETH06"),
    ("84:00.0", "ETH07"): ("88:00.0", "ETH00"),
    ("84:00.0", "ETH09"): ("88:00.0", "ETH01"),
    # UBB4 - U5 (85:00.0)
    ("85:00.0", "ETH00"): ("81:00.0", "ETH07"),
    ("85:00.0", "ETH01"): ("81:00.0", "ETH09"),
    ("85:00.0", "ETH04"): ("86:00.0", "ETH02"),
    ("85:00.0", "ETH06"): ("86:00.0", "ETH03"),
    ("85:00.0", "ETH07"): ("45:00.0", "ETH07"),
    ("85:00.0", "ETH09"): ("45:00.0", "ETH09"),
    # UBB4 - U6 (86:00.0)
    ("86:00.0", "ETH00"): ("82:00.0", "ETH07"),
    ("86:00.0", "ETH01"): ("82:00.0", "ETH09"),
    ("86:00.0", "ETH02"): ("85:00.0", "ETH04"),
    ("86:00.0", "ETH03"): ("85:00.0", "ETH06"),
    ("86:00.0", "ETH04"): ("87:00.0", "ETH02"),
    ("86:00.0", "ETH06"): ("87:00.0", "ETH03"),
    ("86:00.0", "ETH07"): ("46:00.0", "ETH07"),
    ("86:00.0", "ETH09"): ("46:00.0", "ETH09"),
    # UBB4 - U7 (87:00.0)
    ("87:00.0", "ETH00"): ("83:00.0", "ETH07"),
    ("87:00.0", "ETH01"): ("83:00.0", "ETH09"),
    ("87:00.0", "ETH02"): ("86:00.0", "ETH04"),
    ("87:00.0", "ETH03"): ("86:00.0", "ETH06"),
    ("87:00.0", "ETH04"): ("88:00.0", "ETH02"),
    ("87:00.0", "ETH06"): ("88:00.0", "ETH03"),
    ("87:00.0", "ETH07"): ("47:00.0", "ETH07"),
    ("87:00.0", "ETH09"): ("47:00.0", "ETH09"),
    # UBB4 - U8 (88:00.0)
    ("88:00.0", "ETH00"): ("84:00.0", "ETH07"),
    ("88:00.0", "ETH01"): ("84:00.0", "ETH09"),
    ("88:00.0", "ETH02"): ("87:00.0", "ETH04"),
    ("88:00.0", "ETH03"): ("87:00.0", "ETH06"),
    ("88:00.0", "ETH04"): ("c8:00.0", "ETH04"),
    ("88:00.0", "ETH06"): ("c8:00.0", "ETH06"),
    ("88:00.0", "ETH07"): ("48:00.0", "ETH07"),
    ("88:00.0", "ETH09"): ("48:00.0", "ETH09"),
}


def get_port_status(bus_id: str, eth_port: str) -> str:
    """
    Determine the status/category of an ETH port for a specific device.

    Args:
        bus_id: Device bus ID (e.g., "01:00.0")
        eth_port: ETH port in normalized format (e.g., "ETH07")

    Returns:
        String describing the port status: "unused", "unconnected", "cable_connector",
        "platform_connected", or "invalid"
    """
    if eth_port not in ALL_VALID_PORTS:
        return "invalid"

    if eth_port in UNUSED_PORTS:
        return "unused"

    if eth_port in UNCONNECTED_PORTS:
        return "unconnected"

    # Check if this port is a cable connector for this specific chip
    chip_num = get_chip_from_bus_id(bus_id)
    cable_ports = CABLE_CONNECTOR_PORTS_BY_CHIP.get(chip_num, set())
    if eth_port in cable_ports:
        return "cable_connector"

    return "platform_connected"


def get_connected_port(bus_id: str, eth_port: str) -> Optional[Connection]:
    """
    Get the connected device and port for a given source device and port.

    Args:
        bus_id: Source bus ID (e.g., "01:00.0")
        eth_port: Source ETH port (e.g., "ETH07")

    Returns:
        Tuple of (connected_bus_id, connected_eth_port) or None if not found
    """
    return PLATFORM_TOPOLOGY.get((bus_id, eth_port))


def get_all_connections_for_device(bus_id: str) -> Dict[EthPort, Connection]:
    """
    Get all ETH port connections for a specific device.

    Args:
        bus_id: Device bus ID (e.g., "01:00.0")

    Returns:
        Dictionary mapping source ETH ports to their connected (bus_id, eth_port) tuples
    """
    return {
        src_port: dest
        for (src_bus, src_port), dest in PLATFORM_TOPOLOGY.items()
        if src_bus == bus_id
    }


def get_ubb_from_bus_id(bus_id: str) -> int:
    """
    Extract the UBB number from a bus_id.

    Args:
        bus_id: Bus ID (e.g., "01:00.0")

    Returns:
        UBB number (1-4)
    """
    ubb_digit = bus_id[0].lower()
    ubb_map = {'0': 1, '4': 2, 'c': 3, '8': 4}
    return ubb_map.get(ubb_digit, 0)


def get_chip_from_bus_id(bus_id: str) -> int:
    """
    Extract the chip number (U1-U8) from a bus_id.

    Args:
        bus_id: Bus ID (e.g., "01:00.0")

    Returns:
        Chip number (1-8)
    """
    return int(bus_id[1], 16)


def format_device_info(bus_id: str) -> str:
    """
    Format a bus_id as a human-readable string.

    Args:
        bus_id: Bus ID (e.g., "01:00.0")

    Returns:
        Formatted string (e.g., "UBB1/U1")
    """
    ubb = get_ubb_from_bus_id(bus_id)
    chip = get_chip_from_bus_id(bus_id)
    return f"UBB{ubb}/U{chip}"


def normalize_eth_port(port: str) -> str:
    """
    Normalize ETH port format to ETHXX.

    Args:
        port: ETH port in various formats (e.g., "ETH7", "ETH07", "7", "07")

    Returns:
        Normalized ETH port string (e.g., "ETH07")
    """
    port = port.upper().strip()
    if port.startswith("ETH"):
        # Extract number and reformat
        num_str = port[3:]
        port_num = int(num_str)
    else:
        # Assume it's just a number
        port_num = int(port)

    return f"ETH{port_num:02d}"


def normalize_bus_id(bus_id: str) -> str:
    """
    Normalize bus_id format to XX:00.0.

    Args:
        bus_id: Bus ID in various formats

    Returns:
        Normalized bus ID string
    """
    bus_id = bus_id.lower().strip()
    if ':' not in bus_id:
        # Assume format like "01" and add ":00.0"
        bus_id = f"{bus_id}:00.0"
    return bus_id


# CLI interface
if __name__ == "__main__":
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(
        description="Query Blackhole Galaxy Platform Topology - ETH port connectivity between chips",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query a specific connection
  %(prog)s 01:00.0 ETH07
  %(prog)s 01 7              # Shorthand format

  # Show all connections for a device
  %(prog)s 01:00.0 --all
  %(prog)s 01 --all          # Shorthand format

  # JSON output for programmatic use
  %(prog)s 01:00.0 ETH07 --json

  # Bidirectional lookup
  %(prog)s 05:00.0 ETH00 --bidirectional

ETH Port Categories:
  Each chip has 14 ports (ETH00-ETH13). Port purposes vary by chip position:
  - ETH05, ETH08: Unused (not physically present) on all chips
  - ETH12, ETH13: Unconnected (not used) on all chips
  - Platform connections and cable connectors vary by chip (U1-U8):
    * U1: ETH04,06,07,09 (platform), ETH00,01,02,03,10,11 (cable)
    * U2-U4: ETH02,03,04,06,07,09 (platform), ETH00,01,10,11 (cable)
    * U5: ETH00,01,04,06,07,09 (platform), ETH02,03,10,11 (cable)
    * U6-U8: ETH00,01,02,03,04,06,07,09 (platform), ETH10,11 (cable)
        """
    )

    parser.add_argument(
        "bus_id",
        help="Bus ID of the source device (e.g., '01:00.0' or '01')"
    )
    parser.add_argument(
        "eth_port",
        nargs="?",
        help="ETH port to query (e.g., 'ETH07' or '7'). Omit to use --all"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Show all connections for the device"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output in JSON format"
    )
    parser.add_argument(
        "--bidirectional", "-b",
        action="store_true",
        help="Also show reverse connection (what connects to the result)"
    )

    args = parser.parse_args()

    # Normalize inputs
    try:
        bus_id = normalize_bus_id(args.bus_id)
    except Exception as e:
        print(f"Error: Invalid bus_id format '{args.bus_id}': {e}", file=sys.stderr)
        sys.exit(1)

    # Check if bus_id exists in topology
    device_exists = any(src_bus == bus_id for src_bus, _ in PLATFORM_TOPOLOGY.keys())
    if not device_exists:
        print(f"Error: Device {bus_id} not found in topology", file=sys.stderr)
        sys.exit(1)

    if args.all:
        # Show all connections for device
        connections = get_all_connections_for_device(bus_id)

        if args.json:
            output = {
                "bus_id": bus_id,
                "device": format_device_info(bus_id),
                "connections": {
                    port: {"bus_id": dest_bus, "eth_port": dest_port, "device": format_device_info(dest_bus)}
                    for port, (dest_bus, dest_port) in connections.items()
                }
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"All connections for {format_device_info(bus_id)} ({bus_id}):")
            for src_port, (dest_bus, dest_port) in sorted(connections.items()):
                print(f"  {src_port} -> {format_device_info(dest_bus)} ({dest_bus}) {dest_port}")

    elif args.eth_port:
        # Query specific connection
        try:
            eth_port = normalize_eth_port(args.eth_port)
        except Exception as e:
            print(f"Error: Invalid eth_port format '{args.eth_port}': {e}", file=sys.stderr)
            sys.exit(1)

        connected = get_connected_port(bus_id, eth_port)

        if not connected:
            # Determine why no connection was found and provide informative message
            port_status = get_port_status(bus_id, eth_port)

            if port_status == "invalid":
                print(f"Error: Invalid ETH port '{eth_port}'. Valid ports are ETH00-ETH13.", file=sys.stderr)
            elif port_status == "unused":
                print(f"No connection for {bus_id} {eth_port}: Port is unused (not physically present).", file=sys.stderr)
                print("  Note: ETH05 and ETH08 are not present on the hardware.", file=sys.stderr)
            elif port_status == "unconnected":
                print(f"No connection for {bus_id} {eth_port}: Port is unconnected (not used).", file=sys.stderr)
                print("  Note: ETH12 and ETH13 are not connected on the platform.", file=sys.stderr)
            elif port_status == "cable_connector":
                chip_num = get_chip_from_bus_id(bus_id)
                cable_ports = sorted(CABLE_CONNECTOR_PORTS_BY_CHIP.get(chip_num, set()))
                print(f"No connection for {bus_id} {eth_port}: Port is connected to external cable connector.", file=sys.stderr)
                print(f"  Note: Chip U{chip_num} cable connector ports: {', '.join(cable_ports)}", file=sys.stderr)
            else:
                # Should be in topology but isn't - this is unexpected
                print(f"Error: No connection found for {bus_id} {eth_port}", file=sys.stderr)
                print("  This may indicate missing topology data.", file=sys.stderr)

            sys.exit(1)

        dest_bus, dest_port = connected

        if args.json:
            output = {
                "source": {
                    "bus_id": bus_id,
                    "eth_port": eth_port,
                    "device": format_device_info(bus_id)
                },
                "destination": {
                    "bus_id": dest_bus,
                    "eth_port": dest_port,
                    "device": format_device_info(dest_bus)
                }
            }

            if args.bidirectional:
                # Look up reverse connection
                reverse = get_connected_port(dest_bus, dest_port)
                if reverse:
                    output["reverse"] = {
                        "bus_id": reverse[0],
                        "eth_port": reverse[1],
                        "device": format_device_info(reverse[0])
                    }

            print(json.dumps(output, indent=2))
        else:
            print(f"{format_device_info(bus_id)} ({bus_id}) {eth_port} -> {format_device_info(dest_bus)} ({dest_bus}) {dest_port}")

            if args.bidirectional:
                reverse = get_connected_port(dest_bus, dest_port)
                if reverse:
                    rev_bus, rev_port = reverse
                    print(f"Reverse: {format_device_info(dest_bus)} ({dest_bus}) {dest_port} -> {format_device_info(rev_bus)} ({rev_bus}) {rev_port}")

    else:
        parser.print_help()
        sys.exit(1)