"""UBB normalization utilities for chip position analysis.

This module provides functions to normalize bus_ids to chip positions (U1-U8),
enabling analysis that aggregates data across all 4 UBBs for each chip position.

Background:
    Each system has 32 chips (bus_ids) across 4 UBBs (8 chips each).
    The 4 UBBs are identical boards with the same PCB traces.
    Bus IDs follow the pattern:
        UBB1: 0x:00.0 (e.g., 01:00.0)
        UBB2: 4x:00.0 (e.g., 41:00.0)
        UBB3: cx:00.0 (e.g., c1:00.0)
        UBB4: 8x:00.0 (e.g., 81:00.0)

    This module enables aggregating data by chip position (U1-U8)
    instead of individual bus_ids, effectively 4x-ing sample sizes.
"""

from typing import Dict, List, Tuple

# UBB prefix mapping: bus_id prefix -> UBB number
UBB_PREFIX_MAP = {
    "0": 1,  # UBB1: 01:00.0 - 08:00.0
    "4": 2,  # UBB2: 41:00.0 - 48:00.0
    "c": 3,  # UBB3: c1:00.0 - c8:00.0
    "8": 4,  # UBB4: 81:00.0 - 88:00.0
}

# Reverse mapping: UBB number -> bus_id prefix
UBB_REVERSE_MAP = {v: k for k, v in UBB_PREFIX_MAP.items()}


def get_chip_position(bus_id: str) -> int:
    """Extract chip position (1-8) from bus_id.

    Args:
        bus_id: Normalized bus ID (e.g., "01:00.0", "c5:00.0")

    Returns:
        Chip position (1-8)

    Raises:
        ValueError: If bus_id format is invalid

    Examples:
        >>> get_chip_position("01:00.0")
        1
        >>> get_chip_position("c5:00.0")
        5
    """
    if len(bus_id) < 2:
        raise ValueError(f"Invalid bus_id format: {bus_id}")

    # Chip number is the second hex digit
    chip_hex = bus_id[1]
    try:
        chip_pos = int(chip_hex, 16)
    except ValueError as e:
        raise ValueError(f"Invalid chip position in bus_id: {bus_id}") from e

    if chip_pos < 1 or chip_pos > 8:
        raise ValueError(f"Chip position must be 1-8, got {chip_pos} from {bus_id}")

    return chip_pos


def get_ubb_number(bus_id: str) -> int:
    """Extract UBB number (1-4) from bus_id.

    Args:
        bus_id: Normalized bus ID (e.g., "01:00.0", "c5:00.0")

    Returns:
        UBB number (1-4)

    Raises:
        ValueError: If bus_id format is invalid

    Examples:
        >>> get_ubb_number("01:00.0")
        1
        >>> get_ubb_number("c5:00.0")
        3
    """
    if len(bus_id) < 1:
        raise ValueError(f"Invalid bus_id format: {bus_id}")

    prefix = bus_id[0].lower()
    ubb = UBB_PREFIX_MAP.get(prefix)
    if ubb is None:
        raise ValueError(f"Unknown UBB prefix: {prefix} in bus_id: {bus_id}")
    return ubb


def normalize_bus_id_to_chip(bus_id: str) -> str:
    """Normalize bus_id to chip position identifier.

    Converts bus_id (e.g., "01:00.0", "41:00.0", "c1:00.0", "81:00.0")
    to chip position identifier "U1".

    Args:
        bus_id: Normalized bus ID

    Returns:
        Chip position identifier (e.g., "U1", "U5")

    Examples:
        >>> normalize_bus_id_to_chip("01:00.0")
        'U1'
        >>> normalize_bus_id_to_chip("41:00.0")
        'U1'
        >>> normalize_bus_id_to_chip("c5:00.0")
        'U5'
    """
    chip_pos = get_chip_position(bus_id)
    return f"U{chip_pos}"


def get_all_bus_ids_for_chip(chip_position: int) -> Tuple[str, str, str, str]:
    """Get all 4 bus_ids that correspond to a chip position.

    Args:
        chip_position: Chip position (1-8)

    Returns:
        Tuple of (ubb1_bus_id, ubb2_bus_id, ubb3_bus_id, ubb4_bus_id)

    Raises:
        ValueError: If chip_position is out of range

    Examples:
        >>> get_all_bus_ids_for_chip(1)
        ('01:00.0', '41:00.0', 'c1:00.0', '81:00.0')
        >>> get_all_bus_ids_for_chip(5)
        ('05:00.0', '45:00.0', 'c5:00.0', '85:00.0')
    """
    if chip_position < 1 or chip_position > 8:
        raise ValueError(f"Chip position must be 1-8, got {chip_position}")

    return (
        f"0{chip_position}:00.0",  # UBB1
        f"4{chip_position}:00.0",  # UBB2
        f"c{chip_position}:00.0",  # UBB3
        f"8{chip_position}:00.0",  # UBB4
    )


def normalize_lane_id(lane_id: str) -> str:
    """Normalize a lane_id to use chip position instead of bus_id.

    Converts "01:00.0/ETH07/lane0" to "U1/ETH07/lane0"

    Args:
        lane_id: Original lane identifier

    Returns:
        Normalized lane identifier with chip position

    Examples:
        >>> normalize_lane_id("01:00.0/ETH07/lane4")
        'U1/ETH07/lane4'
        >>> normalize_lane_id("c5:00.0/ETH10/lane0")
        'U5/ETH10/lane0'
    """
    parts = lane_id.split("/")
    if len(parts) >= 2:
        bus_id = parts[0]
        chip_pos = normalize_bus_id_to_chip(bus_id)
        parts[0] = chip_pos
    return "/".join(parts)


def group_lane_ids_by_chip_position(lane_ids: List[str]) -> Dict[str, List[str]]:
    """Group lane_ids by their chip position.

    Args:
        lane_ids: List of lane identifiers (e.g., ["01:00.0/ETH07/lane0", ...])

    Returns:
        Dictionary mapping normalized lane_id to list of original lane_ids
        e.g., {"U1/ETH07/lane0": ["01:00.0/ETH07/lane0", "41:00.0/ETH07/lane0", ...]}

    Examples:
        >>> lane_ids = ["01:00.0/ETH07/lane0", "41:00.0/ETH07/lane0"]
        >>> group_lane_ids_by_chip_position(lane_ids)
        {'U1/ETH07/lane0': ['01:00.0/ETH07/lane0', '41:00.0/ETH07/lane0']}
    """
    grouped: Dict[str, List[str]] = {}
    for lane_id in lane_ids:
        normalized = normalize_lane_id(lane_id)
        if normalized not in grouped:
            grouped[normalized] = []
        grouped[normalized].append(lane_id)
    return grouped


def parse_chip_position_spec(spec: str) -> int:
    """Parse chip position specification (e.g., 'U1', 'U5') to integer.

    Args:
        spec: Chip position specification (e.g., "U1", "U5")

    Returns:
        Chip position as integer (1-8)

    Raises:
        ValueError: If spec format is invalid or out of range

    Examples:
        >>> parse_chip_position_spec("U1")
        1
        >>> parse_chip_position_spec("U5")
        5
    """
    if not spec.startswith("U"):
        raise ValueError(f"Chip position spec must start with 'U', got: {spec}")

    try:
        chip_pos = int(spec[1:])
    except ValueError as e:
        raise ValueError(f"Invalid chip position format: {spec}") from e

    if chip_pos < 1 or chip_pos > 8:
        raise ValueError(f"Chip position must be 1-8, got: {chip_pos}")

    return chip_pos
