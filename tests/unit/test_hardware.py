"""Unit tests for hardware module."""

import pytest

from bh_glx_data.hardware.platform_topology import (
    CABLE_CONNECTOR_PORTS_BY_CHIP,
    PLATFORM_TOPOLOGY,
    QSFP_PORT_MAPPING,
    UNCONNECTED_PORTS,
    UNUSED_PORTS,
    format_device_info,
    get_all_connections_for_device,
    get_chip_from_bus_id,
    get_connected_port,
    get_port_status,
    get_qsfp_port,
    get_ubb_from_bus_id,
    normalize_bus_id,
    normalize_eth_port,
)


class TestTopologyData:
    """Test topology data structures."""

    def test_unused_ports_defined(self):
        """Test that unused ports are defined."""
        assert len(UNUSED_PORTS) == 2
        assert "ETH05" in UNUSED_PORTS
        assert "ETH08" in UNUSED_PORTS

    def test_unconnected_ports_defined(self):
        """Test that unconnected ports are defined."""
        assert len(UNCONNECTED_PORTS) == 2
        assert "ETH12" in UNCONNECTED_PORTS
        assert "ETH13" in UNCONNECTED_PORTS

    def test_cable_connector_ports_all_chips(self):
        """Test that cable connector ports defined for all 8 chips."""
        assert len(CABLE_CONNECTOR_PORTS_BY_CHIP) == 8
        for chip_num in range(1, 9):
            assert chip_num in CABLE_CONNECTOR_PORTS_BY_CHIP
            assert isinstance(CABLE_CONNECTOR_PORTS_BY_CHIP[chip_num], set)
            assert len(CABLE_CONNECTOR_PORTS_BY_CHIP[chip_num]) > 0

    def test_platform_topology_not_empty(self):
        """Test that platform topology is populated."""
        assert len(PLATFORM_TOPOLOGY) > 0
        # Should have connections for 32 chips with multiple ports each
        assert len(PLATFORM_TOPOLOGY) > 100

    def test_topology_symmetry(self):
        """Test that topology connections are bidirectional."""
        # Sample a few connections and verify reverse exists
        test_cases = [
            (("01:00.0", "ETH04"), ("02:00.0", "ETH02")),
            (("05:00.0", "ETH00"), ("01:00.0", "ETH07")),
            (("c1:00.0", "ETH04"), ("c2:00.0", "ETH02")),
        ]

        for source, expected_dest in test_cases:
            # Forward direction
            assert PLATFORM_TOPOLOGY.get(source) == expected_dest
            # Reverse direction should exist
            assert PLATFORM_TOPOLOGY.get(expected_dest) == source


class TestBusIdParsing:
    """Test bus ID parsing functions."""

    def test_get_ubb_from_bus_id_ubb1(self):
        """Test extracting UBB number for UBB1."""
        assert get_ubb_from_bus_id("01:00.0") == 1
        assert get_ubb_from_bus_id("08:00.0") == 1

    def test_get_ubb_from_bus_id_ubb2(self):
        """Test extracting UBB number for UBB2."""
        assert get_ubb_from_bus_id("41:00.0") == 2
        assert get_ubb_from_bus_id("48:00.0") == 2

    def test_get_ubb_from_bus_id_ubb3(self):
        """Test extracting UBB number for UBB3."""
        assert get_ubb_from_bus_id("c1:00.0") == 3
        assert get_ubb_from_bus_id("c8:00.0") == 3

    def test_get_ubb_from_bus_id_ubb4(self):
        """Test extracting UBB number for UBB4."""
        assert get_ubb_from_bus_id("81:00.0") == 4
        assert get_ubb_from_bus_id("88:00.0") == 4

    def test_get_ubb_from_bus_id_invalid(self):
        """Test extracting UBB from invalid bus ID."""
        assert get_ubb_from_bus_id("99:00.0") == 0

    def test_get_chip_from_bus_id(self):
        """Test extracting chip number from bus ID."""
        assert get_chip_from_bus_id("01:00.0") == 1
        assert get_chip_from_bus_id("02:00.0") == 2
        assert get_chip_from_bus_id("08:00.0") == 8
        assert get_chip_from_bus_id("c5:00.0") == 5

    def test_format_device_info(self):
        """Test formatting device info."""
        assert format_device_info("01:00.0") == "UBB1/U1"
        assert format_device_info("02:00.0") == "UBB1/U2"
        assert format_device_info("41:00.0") == "UBB2/U1"
        assert format_device_info("c1:00.0") == "UBB3/U1"
        assert format_device_info("81:00.0") == "UBB4/U1"


class TestPortNormalization:
    """Test port normalization functions."""

    def test_normalize_eth_port_full_format(self):
        """Test normalizing fully formatted ETH port."""
        assert normalize_eth_port("ETH00") == "ETH00"
        assert normalize_eth_port("ETH07") == "ETH07"
        assert normalize_eth_port("ETH13") == "ETH13"

    def test_normalize_eth_port_short_format(self):
        """Test normalizing short format ETH port."""
        assert normalize_eth_port("ETH0") == "ETH00"
        assert normalize_eth_port("ETH7") == "ETH07"

    def test_normalize_eth_port_numeric_only(self):
        """Test normalizing numeric-only ETH port."""
        assert normalize_eth_port("0") == "ETH00"
        assert normalize_eth_port("7") == "ETH07"
        assert normalize_eth_port("13") == "ETH13"

    def test_normalize_eth_port_lowercase(self):
        """Test normalizing lowercase ETH port."""
        assert normalize_eth_port("eth07") == "ETH07"
        assert normalize_eth_port("eth0") == "ETH00"

    def test_normalize_eth_port_with_spaces(self):
        """Test normalizing ETH port with spaces."""
        assert normalize_eth_port("  ETH07  ") == "ETH07"
        assert normalize_eth_port(" 7 ") == "ETH07"

    def test_normalize_bus_id_full_format(self):
        """Test normalizing fully formatted bus ID."""
        assert normalize_bus_id("01:00.0") == "01:00.0"
        assert normalize_bus_id("c5:00.0") == "c5:00.0"

    def test_normalize_bus_id_short_format(self):
        """Test normalizing short format bus ID."""
        assert normalize_bus_id("01") == "01:00.0"
        assert normalize_bus_id("c5") == "c5:00.0"

    def test_normalize_bus_id_uppercase(self):
        """Test normalizing uppercase bus ID."""
        assert normalize_bus_id("C5:00.0") == "c5:00.0"
        assert normalize_bus_id("C5") == "c5:00.0"

    def test_normalize_bus_id_with_spaces(self):
        """Test normalizing bus ID with spaces."""
        assert normalize_bus_id("  01:00.0  ") == "01:00.0"
        assert normalize_bus_id(" 01 ") == "01:00.0"


class TestPortStatus:
    """Test port status determination."""

    def test_port_status_unused(self):
        """Test unused port status."""
        assert get_port_status("01:00.0", "ETH05") == "unused"
        assert get_port_status("01:00.0", "ETH08") == "unused"

    def test_port_status_unconnected(self):
        """Test unconnected port status."""
        assert get_port_status("01:00.0", "ETH12") == "unconnected"
        assert get_port_status("01:00.0", "ETH13") == "unconnected"

    def test_port_status_cable_connector(self):
        """Test cable connector port status."""
        # U1 has ETH00, ETH01, ETH02, ETH03, ETH10, ETH11 as cable connectors
        assert get_port_status("01:00.0", "ETH00") == "cable_connector"
        assert get_port_status("01:00.0", "ETH01") == "cable_connector"
        assert get_port_status("01:00.0", "ETH02") == "cable_connector"

    def test_port_status_platform_connected(self):
        """Test platform connected port status."""
        # U1 has ETH04, ETH06, ETH07, ETH09 as platform connected
        assert get_port_status("01:00.0", "ETH04") == "platform_connected"
        assert get_port_status("01:00.0", "ETH06") == "platform_connected"
        assert get_port_status("01:00.0", "ETH07") == "platform_connected"

    def test_port_status_invalid(self):
        """Test invalid port status."""
        assert get_port_status("01:00.0", "ETH99") == "invalid"
        assert get_port_status("01:00.0", "INVALID") == "invalid"


class TestConnectivity:
    """Test connectivity query functions."""

    def test_get_connected_port_valid(self):
        """Test getting connected port for valid connection."""
        result = get_connected_port("01:00.0", "ETH04")
        assert result == ("02:00.0", "ETH02")

        result = get_connected_port("05:00.0", "ETH00")
        assert result == ("01:00.0", "ETH07")

    def test_get_connected_port_cable_connector(self):
        """Test getting connected port for cable connector (should be None)."""
        # Cable connector ports don't have platform connections
        result = get_connected_port("01:00.0", "ETH00")
        assert result is None

    def test_get_connected_port_unused(self):
        """Test getting connected port for unused port."""
        result = get_connected_port("01:00.0", "ETH05")
        assert result is None

    def test_get_connected_port_unconnected(self):
        """Test getting connected port for unconnected port."""
        result = get_connected_port("01:00.0", "ETH12")
        assert result is None

    def test_get_all_connections_for_device(self):
        """Test getting all connections for a device."""
        connections = get_all_connections_for_device("01:00.0")

        assert isinstance(connections, dict)
        assert len(connections) > 0

        # U1 should have 4 platform connections
        assert len(connections) == 4
        assert "ETH04" in connections
        assert "ETH06" in connections
        assert "ETH07" in connections
        assert "ETH09" in connections

        # Verify connection targets
        assert connections["ETH04"] == ("02:00.0", "ETH02")
        assert connections["ETH07"] == ("05:00.0", "ETH00")

    def test_get_all_connections_empty_device(self):
        """Test getting connections for device not in topology."""
        connections = get_all_connections_for_device("99:00.0")
        assert connections == {}


class TestTopologyConsistency:
    """Test topology data consistency."""

    def test_all_connections_bidirectional(self):
        """Test that all connections in topology are bidirectional."""
        for source, dest in PLATFORM_TOPOLOGY.items():
            # Each forward connection should have a reverse
            assert dest in PLATFORM_TOPOLOGY, f"Missing reverse connection for {source} -> {dest}"
            # And the reverse should point back to source
            assert (
                PLATFORM_TOPOLOGY[dest] == source
            ), f"Reverse connection mismatch: {dest} does not point back to {source}"

    def test_no_self_connections(self):
        """Test that no port connects to itself."""
        for (src_bus, src_port), (dst_bus, dst_port) in PLATFORM_TOPOLOGY.items():
            assert not (
                src_bus == dst_bus and src_port == dst_port
            ), f"Self-connection found: {src_bus} {src_port}"

    def test_cable_ports_not_in_topology(self):
        """Test that cable connector ports are not in topology."""
        for chip_num, cable_ports in CABLE_CONNECTOR_PORTS_BY_CHIP.items():
            # Get bus IDs for this chip across all UBBs
            bus_prefixes = ["0", "4", "c", "8"]  # UBB1, UBB2, UBB3, UBB4
            for prefix in bus_prefixes:
                bus_id = f"{prefix}{chip_num}:00.0"
                for port in cable_ports:
                    # Cable connector ports should not be in topology
                    assert (
                        bus_id,
                        port,
                    ) not in PLATFORM_TOPOLOGY, (
                        f"Cable connector port {bus_id} {port} should not be in topology"
                    )

    def test_unused_ports_not_in_topology(self):
        """Test that unused ports are not in topology."""
        # Check all devices
        for bus_id in ["01:00.0", "02:00.0", "41:00.0", "c1:00.0", "81:00.0"]:
            for port in UNUSED_PORTS:
                assert (
                    bus_id,
                    port,
                ) not in PLATFORM_TOPOLOGY, f"Unused port {bus_id} {port} should not be in topology"

    def test_unconnected_ports_not_in_topology(self):
        """Test that unconnected ports are not in topology."""
        # Check all devices
        for bus_id in ["01:00.0", "02:00.0", "41:00.0", "c1:00.0", "81:00.0"]:
            for port in UNCONNECTED_PORTS:
                assert (
                    bus_id,
                    port,
                ) not in PLATFORM_TOPOLOGY, (
                    f"Unconnected port {bus_id} {port} should not be in topology"
                )


class TestQSFPPortMapping:
    """Test QSFP port mapping functionality."""

    def test_qsfp_mapping_data_structure(self):
        """Test that QSFP mapping data structure is defined."""
        assert isinstance(QSFP_PORT_MAPPING, dict)
        assert len(QSFP_PORT_MAPPING) > 0
        # Should have 28 entries (14 QSFP ports × 2 ETH ports each)
        assert len(QSFP_PORT_MAPPING) == 28

    def test_qsfp_mapping_all_14_ports(self):
        """Test that all 14 QSFP ports are represented in mapping."""
        qsfp_ports = set(QSFP_PORT_MAPPING.values())
        assert len(qsfp_ports) == 14
        assert qsfp_ports == set(range(1, 15))  # QSFP-1 through QSFP-14

    def test_qsfp_mapping_each_port_has_two_eth(self):
        """Test that each QSFP port maps to exactly 2 ETH ports."""
        from collections import Counter

        qsfp_counts = Counter(QSFP_PORT_MAPPING.values())
        for qsfp_num in range(1, 15):
            assert qsfp_counts[qsfp_num] == 2, f"QSFP-{qsfp_num} should map to exactly 2 ETH ports"

    def test_get_qsfp_port_u1_eth10(self):
        """Test QSFP-7 mapping for U1 ETH10."""
        # From requirements: (U1 ETH10, U2 ETH10) -> QSFP-7
        result = get_qsfp_port("01:00.0", "ETH10")
        assert result == 7

        # Test across different UBBs (U# is independent of UBB)
        result = get_qsfp_port("41:00.0", "ETH10")  # UBB2/U1
        assert result == 7

        result = get_qsfp_port("c1:00.0", "ETH10")  # UBB3/U1
        assert result == 7

        result = get_qsfp_port("81:00.0", "ETH10")  # UBB4/U1
        assert result == 7

    def test_get_qsfp_port_u5_eth02(self):
        """Test QSFP-1 mapping for U5 ETH02."""
        # From requirements: (U5 ETH02, U5 ETH03) -> QSFP-1
        result = get_qsfp_port("05:00.0", "ETH02")
        assert result == 1

        result = get_qsfp_port("05:00.0", "ETH03")
        assert result == 1

    def test_get_qsfp_port_u1_eth00_eth01(self):
        """Test QSFP-3 mapping for U1 ETH00/ETH01."""
        # From requirements: (U1 ETH00, U1 ETH01) -> QSFP-3
        result = get_qsfp_port("01:00.0", "ETH00")
        assert result == 3

        result = get_qsfp_port("01:00.0", "ETH01")
        assert result == 3

    def test_get_qsfp_port_u3_eth10(self):
        """Test QSFP-9 mapping for U3 ETH10."""
        # From requirements: (U3 ETH10, U4 ETH10) -> QSFP-9
        result = get_qsfp_port("03:00.0", "ETH10")
        assert result == 9

        result = get_qsfp_port("43:00.0", "ETH10")  # UBB2/U3
        assert result == 9

    def test_get_qsfp_port_u7_u8_eth11(self):
        """Test QSFP-14 mapping for U7/U8 ETH11."""
        # From requirements: (U7 ETH11, U8 ETH11) -> QSFP-14
        result = get_qsfp_port("07:00.0", "ETH11")
        assert result == 14

        result = get_qsfp_port("08:00.0", "ETH11")
        assert result == 14

    def test_get_qsfp_port_platform_connected(self):
        """Test that platform-connected ports return None."""
        # ETH04 is platform-connected for U1, not a cable connector
        result = get_qsfp_port("01:00.0", "ETH04")
        assert result is None

        result = get_qsfp_port("01:00.0", "ETH07")
        assert result is None

    def test_get_qsfp_port_unused(self):
        """Test that unused ports return None."""
        result = get_qsfp_port("01:00.0", "ETH05")
        assert result is None

        result = get_qsfp_port("01:00.0", "ETH08")
        assert result is None

    def test_get_qsfp_port_unconnected(self):
        """Test that unconnected ports return None."""
        result = get_qsfp_port("01:00.0", "ETH12")
        assert result is None

        result = get_qsfp_port("01:00.0", "ETH13")
        assert result is None

    def test_qsfp_mapping_consistency_with_cable_ports(self):
        """Test that QSFP mapping is consistent with cable connector definitions."""
        # All ports in QSFP_PORT_MAPPING should be cable connector ports
        for (chip_num, eth_port), qsfp_num in QSFP_PORT_MAPPING.items():
            assert (
                chip_num in CABLE_CONNECTOR_PORTS_BY_CHIP
            ), f"Chip U{chip_num} not in cable connector mapping"
            assert (
                eth_port in CABLE_CONNECTOR_PORTS_BY_CHIP[chip_num]
            ), f"U{chip_num} {eth_port} is in QSFP mapping but not in cable connector ports"

    def test_qsfp_mapping_covers_all_cable_ports(self):
        """Test that all cable connector ports have QSFP mappings."""
        # Every cable connector port should have a QSFP mapping
        for chip_num, cable_ports in CABLE_CONNECTOR_PORTS_BY_CHIP.items():
            for port in cable_ports:
                assert (
                    chip_num,
                    port,
                ) in QSFP_PORT_MAPPING, f"Cable port U{chip_num} {port} missing from QSFP mapping"

    def test_all_qsfp_mappings_from_requirements(self):
        """Test all 14 QSFP mappings from requirements document."""
        # All mappings from qsfp_port_mapping_requirements.md
        test_cases = [
            # (bus_id, eth_port, expected_qsfp)
            # QSFP-1: U5 ETH02, ETH03
            ("05:00.0", "ETH02", 1),
            ("05:00.0", "ETH03", 1),
            # QSFP-2: U1 ETH02, ETH03
            ("01:00.0", "ETH02", 2),
            ("01:00.0", "ETH03", 2),
            # QSFP-3: U1 ETH00, ETH01
            ("01:00.0", "ETH00", 3),
            ("01:00.0", "ETH01", 3),
            # QSFP-4: U2 ETH00, ETH01
            ("02:00.0", "ETH00", 4),
            ("02:00.0", "ETH01", 4),
            # QSFP-5: U3 ETH00, ETH01
            ("03:00.0", "ETH00", 5),
            ("03:00.0", "ETH01", 5),
            # QSFP-6: U4 ETH00, ETH01
            ("04:00.0", "ETH00", 6),
            ("04:00.0", "ETH01", 6),
            # QSFP-7: U1 ETH10, U2 ETH10
            ("01:00.0", "ETH10", 7),
            ("02:00.0", "ETH10", 7),
            # QSFP-8: U5 ETH10, U6 ETH10
            ("05:00.0", "ETH10", 8),
            ("06:00.0", "ETH10", 8),
            # QSFP-9: U3 ETH10, U4 ETH10
            ("03:00.0", "ETH10", 9),
            ("04:00.0", "ETH10", 9),
            # QSFP-10: U7 ETH10, U8 ETH10
            ("07:00.0", "ETH10", 10),
            ("08:00.0", "ETH10", 10),
            # QSFP-11: U1 ETH11, U2 ETH11
            ("01:00.0", "ETH11", 11),
            ("02:00.0", "ETH11", 11),
            # QSFP-12: U5 ETH11, U6 ETH11
            ("05:00.0", "ETH11", 12),
            ("06:00.0", "ETH11", 12),
            # QSFP-13: U3 ETH11, U4 ETH11
            ("03:00.0", "ETH11", 13),
            ("04:00.0", "ETH11", 13),
            # QSFP-14: U7 ETH11, U8 ETH11
            ("07:00.0", "ETH11", 14),
            ("08:00.0", "ETH11", 14),
        ]

        for bus_id, eth_port, expected_qsfp in test_cases:
            result = get_qsfp_port(bus_id, eth_port)
            assert (
                result == expected_qsfp
            ), f"Expected {bus_id} {eth_port} -> QSFP-{expected_qsfp}, got {result}"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_normalize_invalid_eth_port(self):
        """Test normalizing invalid ETH port raises error."""
        with pytest.raises((ValueError, IndexError)):
            normalize_eth_port("")

        with pytest.raises((ValueError, IndexError)):
            normalize_eth_port("INVALID")

    def test_normalize_invalid_bus_id(self):
        """Test normalizing invalid bus ID."""
        # These shouldn't raise, just return invalid format
        result = normalize_bus_id("")
        assert result == ":00.0"

    def test_get_chip_from_invalid_bus_id(self):
        """Test getting chip from invalid bus ID."""
        # Should handle gracefully or raise
        try:
            result = get_chip_from_bus_id("invalid")
            # If it doesn't raise, result should indicate invalid
            assert result is not None
        except (ValueError, IndexError):
            # Expected for invalid input
            pass

    def test_format_device_info_edge_cases(self):
        """Test formatting device info for edge cases."""
        # Invalid UBB
        result = format_device_info("99:00.0")
        assert "UBB0" in result  # Invalid UBB maps to 0

    def test_get_all_connections_special_devices(self):
        """Test getting connections for special devices."""
        # Test UBB4 device
        connections = get_all_connections_for_device("81:00.0")
        assert len(connections) > 0

        # Test UBB3 device
        connections = get_all_connections_for_device("c5:00.0")
        assert len(connections) > 0
