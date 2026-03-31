"""Tests for UBB normalization module."""

import pytest

from bh_glx_data.system_analysis.ubb_normalization import (
    UBB_PREFIX_MAP,
    UBB_REVERSE_MAP,
    get_all_bus_ids_for_chip,
    get_chip_position,
    get_ubb_number,
    group_lane_ids_by_chip_position,
    normalize_bus_id_to_chip,
    normalize_lane_id,
    parse_chip_position_spec,
)


class TestChipPositionExtraction:
    """Tests for get_chip_position function."""

    def test_get_chip_position_ubb1(self):
        """Test extracting chip position from UBB1 bus_ids."""
        assert get_chip_position("01:00.0") == 1
        assert get_chip_position("02:00.0") == 2
        assert get_chip_position("05:00.0") == 5
        assert get_chip_position("08:00.0") == 8

    def test_get_chip_position_ubb2(self):
        """Test extracting chip position from UBB2 bus_ids."""
        assert get_chip_position("41:00.0") == 1
        assert get_chip_position("42:00.0") == 2
        assert get_chip_position("45:00.0") == 5
        assert get_chip_position("48:00.0") == 8

    def test_get_chip_position_ubb3(self):
        """Test extracting chip position from UBB3 bus_ids."""
        assert get_chip_position("c1:00.0") == 1
        assert get_chip_position("c2:00.0") == 2
        assert get_chip_position("c5:00.0") == 5
        assert get_chip_position("c8:00.0") == 8

    def test_get_chip_position_ubb4(self):
        """Test extracting chip position from UBB4 bus_ids."""
        assert get_chip_position("81:00.0") == 1
        assert get_chip_position("82:00.0") == 2
        assert get_chip_position("85:00.0") == 5
        assert get_chip_position("88:00.0") == 8

    def test_get_chip_position_invalid_format(self):
        """Test error handling for invalid bus_id format."""
        with pytest.raises(ValueError, match="Invalid bus_id format"):
            get_chip_position("")

        with pytest.raises(ValueError, match="Invalid bus_id format"):
            get_chip_position("1")

    def test_get_chip_position_out_of_range(self):
        """Test error handling for out of range chip positions."""
        with pytest.raises(ValueError, match="Chip position must be 1-8"):
            get_chip_position("00:00.0")

        with pytest.raises(ValueError, match="Chip position must be 1-8"):
            get_chip_position("09:00.0")


class TestUBBNumberExtraction:
    """Tests for get_ubb_number function."""

    def test_get_ubb_number_all_ubbs(self):
        """Test extracting UBB number for all UBBs."""
        assert get_ubb_number("01:00.0") == 1
        assert get_ubb_number("41:00.0") == 2
        assert get_ubb_number("c1:00.0") == 3
        assert get_ubb_number("81:00.0") == 4

    def test_get_ubb_number_case_insensitive(self):
        """Test that UBB extraction is case insensitive."""
        assert get_ubb_number("C1:00.0") == 3
        assert get_ubb_number("c1:00.0") == 3

    def test_get_ubb_number_invalid_format(self):
        """Test error handling for invalid bus_id format."""
        with pytest.raises(ValueError, match="Invalid bus_id format"):
            get_ubb_number("")

    def test_get_ubb_number_unknown_prefix(self):
        """Test error handling for unknown UBB prefix."""
        with pytest.raises(ValueError, match="Unknown UBB prefix"):
            get_ubb_number("f1:00.0")

        with pytest.raises(ValueError, match="Unknown UBB prefix"):
            get_ubb_number("11:00.0")


class TestBusIDNormalization:
    """Tests for normalize_bus_id_to_chip function."""

    def test_normalize_bus_id_to_chip_all_ubbs_same_position(self):
        """Test that all UBBs normalize to same chip position."""
        assert normalize_bus_id_to_chip("01:00.0") == "U1"
        assert normalize_bus_id_to_chip("41:00.0") == "U1"
        assert normalize_bus_id_to_chip("c1:00.0") == "U1"
        assert normalize_bus_id_to_chip("81:00.0") == "U1"

    def test_normalize_bus_id_to_chip_different_positions(self):
        """Test normalization for different chip positions."""
        assert normalize_bus_id_to_chip("01:00.0") == "U1"
        assert normalize_bus_id_to_chip("02:00.0") == "U2"
        assert normalize_bus_id_to_chip("03:00.0") == "U3"
        assert normalize_bus_id_to_chip("04:00.0") == "U4"
        assert normalize_bus_id_to_chip("05:00.0") == "U5"
        assert normalize_bus_id_to_chip("06:00.0") == "U6"
        assert normalize_bus_id_to_chip("07:00.0") == "U7"
        assert normalize_bus_id_to_chip("08:00.0") == "U8"

    def test_normalize_bus_id_to_chip_ubb3_example(self):
        """Test normalization for UBB3 examples."""
        assert normalize_bus_id_to_chip("c5:00.0") == "U5"
        assert normalize_bus_id_to_chip("c8:00.0") == "U8"


class TestGetAllBusIDsForChip:
    """Tests for get_all_bus_ids_for_chip function."""

    def test_get_all_bus_ids_for_chip_1(self):
        """Test getting all bus_ids for chip position 1."""
        bus_ids = get_all_bus_ids_for_chip(1)
        assert bus_ids == ("01:00.0", "41:00.0", "c1:00.0", "81:00.0")

    def test_get_all_bus_ids_for_chip_5(self):
        """Test getting all bus_ids for chip position 5."""
        bus_ids = get_all_bus_ids_for_chip(5)
        assert bus_ids == ("05:00.0", "45:00.0", "c5:00.0", "85:00.0")

    def test_get_all_bus_ids_for_chip_8(self):
        """Test getting all bus_ids for chip position 8."""
        bus_ids = get_all_bus_ids_for_chip(8)
        assert bus_ids == ("08:00.0", "48:00.0", "c8:00.0", "88:00.0")

    def test_get_all_bus_ids_for_chip_all_positions(self):
        """Test getting all bus_ids for all chip positions."""
        for chip_pos in range(1, 9):
            bus_ids = get_all_bus_ids_for_chip(chip_pos)
            assert len(bus_ids) == 4
            assert all(f"{chip_pos}" in bus_id for bus_id in bus_ids)

    def test_get_all_bus_ids_for_chip_out_of_range(self):
        """Test error handling for out of range chip positions."""
        with pytest.raises(ValueError, match="Chip position must be 1-8"):
            get_all_bus_ids_for_chip(0)

        with pytest.raises(ValueError, match="Chip position must be 1-8"):
            get_all_bus_ids_for_chip(9)


class TestNormalizeLaneID:
    """Tests for normalize_lane_id function."""

    def test_normalize_lane_id_full_format(self):
        """Test normalizing lane_id with full format."""
        assert normalize_lane_id("01:00.0/ETH07/lane4") == "U1/ETH07/lane4"
        assert normalize_lane_id("c5:00.0/ETH10/lane0") == "U5/ETH10/lane0"
        assert normalize_lane_id("81:00.0/ETH00/lane7") == "U1/ETH00/lane7"

    def test_normalize_lane_id_port_only(self):
        """Test normalizing lane_id with port only (no lane number)."""
        assert normalize_lane_id("01:00.0/ETH07") == "U1/ETH07"
        assert normalize_lane_id("c5:00.0/ETH10") == "U5/ETH10"

    def test_normalize_lane_id_all_ubbs_same_result(self):
        """Test that all UBBs normalize to same lane_id."""
        assert normalize_lane_id("01:00.0/ETH07/lane4") == "U1/ETH07/lane4"
        assert normalize_lane_id("41:00.0/ETH07/lane4") == "U1/ETH07/lane4"
        assert normalize_lane_id("c1:00.0/ETH07/lane4") == "U1/ETH07/lane4"
        assert normalize_lane_id("81:00.0/ETH07/lane4") == "U1/ETH07/lane4"

    def test_normalize_lane_id_bus_id_only(self):
        """Test normalizing bus_id only (no port specified)."""
        # This case has only 1 part, so it returns unchanged
        assert normalize_lane_id("01:00.0") == "01:00.0"


class TestGroupLaneIDsByChipPosition:
    """Tests for group_lane_ids_by_chip_position function."""

    def test_group_lane_ids_by_chip_position_basic(self):
        """Test basic grouping of lane_ids."""
        lane_ids = [
            "01:00.0/ETH07/lane0",
            "41:00.0/ETH07/lane0",
            "c1:00.0/ETH07/lane0",
            "81:00.0/ETH07/lane0",
        ]
        grouped = group_lane_ids_by_chip_position(lane_ids)

        assert "U1/ETH07/lane0" in grouped
        assert len(grouped["U1/ETH07/lane0"]) == 4
        assert set(grouped["U1/ETH07/lane0"]) == set(lane_ids)

    def test_group_lane_ids_by_chip_position_multiple_positions(self):
        """Test grouping lane_ids from multiple chip positions."""
        lane_ids = [
            "01:00.0/ETH07/lane0",
            "02:00.0/ETH07/lane0",
            "41:00.0/ETH07/lane0",
            "42:00.0/ETH07/lane0",
        ]
        grouped = group_lane_ids_by_chip_position(lane_ids)

        assert len(grouped) == 2
        assert "U1/ETH07/lane0" in grouped
        assert "U2/ETH07/lane0" in grouped
        assert len(grouped["U1/ETH07/lane0"]) == 2
        assert len(grouped["U2/ETH07/lane0"]) == 2

    def test_group_lane_ids_by_chip_position_multiple_ports(self):
        """Test grouping lane_ids from multiple ports."""
        lane_ids = [
            "01:00.0/ETH07/lane0",
            "01:00.0/ETH10/lane0",
            "41:00.0/ETH07/lane0",
            "41:00.0/ETH10/lane0",
        ]
        grouped = group_lane_ids_by_chip_position(lane_ids)

        assert len(grouped) == 2
        assert "U1/ETH07/lane0" in grouped
        assert "U1/ETH10/lane0" in grouped
        assert len(grouped["U1/ETH07/lane0"]) == 2
        assert len(grouped["U1/ETH10/lane0"]) == 2

    def test_group_lane_ids_by_chip_position_empty_list(self):
        """Test grouping empty list."""
        grouped = group_lane_ids_by_chip_position([])
        assert grouped == {}

    def test_group_lane_ids_by_chip_position_single_lane(self):
        """Test grouping single lane_id."""
        lane_ids = ["01:00.0/ETH07/lane0"]
        grouped = group_lane_ids_by_chip_position(lane_ids)

        assert len(grouped) == 1
        assert "U1/ETH07/lane0" in grouped
        assert grouped["U1/ETH07/lane0"] == ["01:00.0/ETH07/lane0"]


class TestParseChipPositionSpec:
    """Tests for parse_chip_position_spec function."""

    def test_parse_chip_position_spec_valid(self):
        """Test parsing valid chip position specifications."""
        assert parse_chip_position_spec("U1") == 1
        assert parse_chip_position_spec("U2") == 2
        assert parse_chip_position_spec("U5") == 5
        assert parse_chip_position_spec("U8") == 8

    def test_parse_chip_position_spec_invalid_prefix(self):
        """Test error handling for invalid prefix."""
        with pytest.raises(ValueError, match="must start with 'U'"):
            parse_chip_position_spec("1")

        with pytest.raises(ValueError, match="must start with 'U'"):
            parse_chip_position_spec("X1")

    def test_parse_chip_position_spec_invalid_number(self):
        """Test error handling for invalid number format."""
        with pytest.raises(ValueError, match="Invalid chip position format"):
            parse_chip_position_spec("U")

        with pytest.raises(ValueError, match="Invalid chip position format"):
            parse_chip_position_spec("UX")

    def test_parse_chip_position_spec_out_of_range(self):
        """Test error handling for out of range chip positions."""
        with pytest.raises(ValueError, match="Chip position must be 1-8"):
            parse_chip_position_spec("U0")

        with pytest.raises(ValueError, match="Chip position must be 1-8"):
            parse_chip_position_spec("U9")


class TestMappingConstants:
    """Tests for mapping constants."""

    def test_ubb_prefix_map_completeness(self):
        """Test that UBB_PREFIX_MAP contains all expected prefixes."""
        assert len(UBB_PREFIX_MAP) == 4
        assert UBB_PREFIX_MAP["0"] == 1
        assert UBB_PREFIX_MAP["4"] == 2
        assert UBB_PREFIX_MAP["c"] == 3
        assert UBB_PREFIX_MAP["8"] == 4

    def test_ubb_reverse_map_consistency(self):
        """Test that UBB_REVERSE_MAP is consistent with UBB_PREFIX_MAP."""
        assert len(UBB_REVERSE_MAP) == 4
        for prefix, ubb_num in UBB_PREFIX_MAP.items():
            assert UBB_REVERSE_MAP[ubb_num] == prefix

    def test_reverse_mapping_bidirectional(self):
        """Test that forward and reverse mappings are bidirectional."""
        for prefix, ubb_num in UBB_PREFIX_MAP.items():
            assert UBB_REVERSE_MAP[ubb_num] == prefix

        for ubb_num, prefix in UBB_REVERSE_MAP.items():
            assert UBB_PREFIX_MAP[prefix] == ubb_num


class TestIntegrationScenarios:
    """Integration tests for common usage patterns."""

    def test_roundtrip_normalization(self):
        """Test that normalization and expansion work together."""
        # Start with chip position 1
        chip_pos = 1

        # Get all bus_ids for this position
        bus_ids = get_all_bus_ids_for_chip(chip_pos)

        # Normalize each back to chip position
        for bus_id in bus_ids:
            assert normalize_bus_id_to_chip(bus_id) == "U1"
            assert get_chip_position(bus_id) == chip_pos

    def test_full_lane_id_workflow(self):
        """Test complete workflow of lane_id normalization and grouping."""
        # Create lane_ids for same port across all UBBs
        original_lane_ids = [
            "01:00.0/ETH07/lane4",
            "41:00.0/ETH07/lane4",
            "c1:00.0/ETH07/lane4",
            "81:00.0/ETH07/lane4",
        ]

        # Normalize and group
        grouped = group_lane_ids_by_chip_position(original_lane_ids)

        # Should have single entry for U1
        assert len(grouped) == 1
        assert "U1/ETH07/lane4" in grouped

        # Should contain all 4 original lane_ids
        assert len(grouped["U1/ETH07/lane4"]) == 4
        assert set(grouped["U1/ETH07/lane4"]) == set(original_lane_ids)
