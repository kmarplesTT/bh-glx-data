"""Unit tests for LaneSelector class."""

import pytest

from bh_glx_data.core.exceptions import LaneSelectorError
from bh_glx_data.system_analysis.query_engine import LaneSelector


class TestLaneSelector:
    """Test LaneSelector class."""

    def test_from_spec_all(self):
        """Test parsing 'all' specification."""
        selector = LaneSelector.from_spec("all")

        assert selector.host is None
        assert selector.bus_id is None
        assert selector.eth_id is None

    def test_from_spec_bus_eth(self):
        """Test parsing 'bus_id/eth_id' specification."""
        selector = LaneSelector.from_spec("01:00.0/ETH07")

        assert selector.host is None
        assert selector.bus_id == "01:00.0"
        assert selector.eth_id == "ETH07"

    def test_from_spec_bus_wildcard(self):
        """Test parsing 'bus_id/*' specification."""
        selector = LaneSelector.from_spec("01:00.0/*")

        assert selector.host is None
        assert selector.bus_id == "01:00.0"
        assert selector.eth_id is None

    def test_from_spec_host_bus_eth(self):
        """Test parsing 'host/bus_id/eth_id' specification."""
        selector = LaneSelector.from_spec("bh-glx-c02u02/01:00.0/ETH07")

        assert selector.host == "bh-glx-c02u02"
        assert selector.bus_id == "01:00.0"
        assert selector.eth_id == "ETH07"

    def test_from_spec_host_wildcard(self):
        """Test parsing 'host/*' specification."""
        selector = LaneSelector.from_spec("bh-glx-c02u02/*")

        assert selector.host == "bh-glx-c02u02"
        assert selector.bus_id is None
        assert selector.eth_id is None

    def test_from_spec_wildcard_eth(self):
        """Test parsing '*/eth_id' specification."""
        selector = LaneSelector.from_spec("*/ETH07")

        assert selector.host is None
        assert selector.bus_id is None
        assert selector.eth_id == "ETH07"

    def test_from_spec_normalizes_bus_id(self):
        """Test that bus_id is normalized."""
        selector = LaneSelector.from_spec("1/ETH07")

        assert selector.bus_id == "01:00.0"

    def test_from_spec_normalizes_eth_id(self):
        """Test that eth_id is normalized."""
        selector = LaneSelector.from_spec("01:00.0/7")

        assert selector.eth_id == "ETH07"

    def test_from_spec_invalid_format(self):
        """Test that invalid format raises error."""
        with pytest.raises(LaneSelectorError):
            LaneSelector.from_spec("invalid")

    def test_from_spec_too_many_parts(self):
        """Test that too many parts raises error."""
        with pytest.raises(LaneSelectorError):
            LaneSelector.from_spec("host/bus/eth/extra")

    def test_to_sql_filter_all(self):
        """Test SQL filter generation for 'all'."""
        selector = LaneSelector.from_spec("all")
        where_clause, params = selector.to_sql_filter()

        assert where_clause == "1=1"
        assert params == ()

    def test_to_sql_filter_bus_eth(self):
        """Test SQL filter generation for specific bus and eth."""
        selector = LaneSelector.from_spec("01:00.0/ETH07")
        where_clause, params = selector.to_sql_filter()

        assert "bus_id = ?" in where_clause
        assert "eth_id = ?" in where_clause
        assert params == ("01:00.0", "ETH07")

    def test_to_sql_filter_bus_wildcard(self):
        """Test SQL filter generation for bus with wildcard eth."""
        selector = LaneSelector.from_spec("01:00.0/*")
        where_clause, params = selector.to_sql_filter()

        assert "bus_id = ?" in where_clause
        assert "eth_id" not in where_clause
        assert params == ("01:00.0",)

    def test_to_sql_filter_host(self):
        """Test SQL filter generation with host."""
        selector = LaneSelector.from_spec("bh-glx-c02u02/01:00.0/ETH07")
        where_clause, params = selector.to_sql_filter()

        assert "host = ?" in where_clause
        assert "bus_id = ?" in where_clause
        assert "eth_id = ?" in where_clause
        assert params == ("bh-glx-c02u02", "01:00.0", "ETH07")

    def test_str_representation(self):
        """Test string representation of LaneSelector."""
        selector = LaneSelector.from_spec("01:00.0/ETH07")
        str_repr = str(selector)

        assert "01:00.0" in str_repr
        assert "ETH07" in str_repr

    def test_repr_representation(self):
        """Test repr representation of LaneSelector."""
        selector = LaneSelector.from_spec("bh-glx-c02u02/01:00.0/ETH07")
        repr_str = repr(selector)

        assert "LaneSelector" in repr_str
        assert "bh-glx-c02u02" in repr_str
        assert "01:00.0" in repr_str
        assert "ETH07" in repr_str


class TestLaneSelectorEdgeCases:
    """Test edge cases for LaneSelector."""

    def test_empty_spec_raises_error(self):
        """Test that empty specification raises error."""
        with pytest.raises(LaneSelectorError):
            LaneSelector.from_spec("")

    def test_whitespace_spec_raises_error(self):
        """Test that whitespace-only specification raises error."""
        with pytest.raises(LaneSelectorError):
            LaneSelector.from_spec("   ")

    def test_wildcard_only_raises_error(self):
        """Test that wildcard-only specification raises error."""
        with pytest.raises(LaneSelectorError):
            LaneSelector.from_spec("*")

    def test_invalid_bus_id_format(self):
        """Test that invalid bus_id format raises error."""
        with pytest.raises(LaneSelectorError):
            LaneSelector.from_spec("invalid_bus/ETH07")

    def test_invalid_eth_id_format(self):
        """Test that invalid eth_id format raises error."""
        with pytest.raises(LaneSelectorError):
            LaneSelector.from_spec("01:00.0/INVALID")

    def test_case_insensitive_eth(self):
        """Test that ETH ID is case-insensitive."""
        selector1 = LaneSelector.from_spec("01:00.0/eth07")
        selector2 = LaneSelector.from_spec("01:00.0/ETH07")

        assert selector1.eth_id == selector2.eth_id

    def test_spec_with_extra_slashes(self):
        """Test that extra slashes raise error."""
        with pytest.raises(LaneSelectorError):
            LaneSelector.from_spec("01:00.0//ETH07")

    def test_spec_with_leading_slash(self):
        """Test that leading slash raises error."""
        with pytest.raises(LaneSelectorError):
            LaneSelector.from_spec("/01:00.0/ETH07")

    def test_spec_with_trailing_slash(self):
        """Test that trailing slash raises error."""
        with pytest.raises(LaneSelectorError):
            LaneSelector.from_spec("01:00.0/ETH07/")
