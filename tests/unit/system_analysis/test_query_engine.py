"""Unit tests for query_engine module."""

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from bh_glx_data.system_analysis.database import DatabaseManager
from bh_glx_data.system_analysis.query_engine import (
    LaneBERStats,
    LaneSelector,
    QueryEngine,
)


@pytest.fixture
def test_db(tmp_path):
    """Create a test database with sample data."""
    db_path = tmp_path / "test.db"
    db = DatabaseManager(db_path)
    db.initialize_schema()

    # Insert test data
    test_data = [
        # System 1, Port 1, Speed 200 - PASS with normal BER
        ("sys1", "01:00.0", "ETH07", 200, "PASS", "2026-03-13", "test.csv", "2026-03-13T00:00:00",
         1e-12, 2e-12, 3e-12, 4e-12, 5e-12, 6e-12, 7e-12, 8e-12),
        # System 1, Port 1, Speed 200 - PASS with high BER in lane0
        ("sys1", "01:00.0", "ETH07", 200, "PASS", "2026-03-13", "test.csv", "2026-03-13T00:00:00",
         0.5, 2e-11, 3e-11, 4e-11, 5e-11, 6e-11, 7e-11, 8e-11),
        # System 1, Port 1, Speed 200 - TRAINING_FAIL (no BER data)
        ("sys1", "01:00.0", "ETH07", 200, "TRAINING_FAIL", "2026-03-13", "test.csv", "2026-03-13T00:00:00",
         None, None, None, None, None, None, None, None),
        # System 1, Port 2, Speed 200 - PASS with normal BER
        ("sys1", "05:00.0", "ETH00", 200, "PASS", "2026-03-13", "test.csv", "2026-03-13T00:00:00",
         1e-11, 2e-11, 3e-11, 4e-11, 5e-11, 6e-11, 7e-11, 8e-11),
        # System 2, Port 1, Speed 100 - PASS with normal BER
        ("sys2", "01:00.0", "ETH07", 100, "PASS", "2026-03-13", "test.csv", "2026-03-13T00:00:00",
         1e-10, 2e-10, 3e-10, 4e-10, 5e-10, 6e-10, 7e-10, 8e-10),
    ]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for data in test_data:
        cursor.execute(
            """
            INSERT INTO prbs_tests (
                host, bus_id, eth_id, train_speed, test_status, date, source_file, ingestion_timestamp,
                acc_ber_lane0, acc_ber_lane1, acc_ber_lane2, acc_ber_lane3,
                acc_ber_lane4, acc_ber_lane5, acc_ber_lane6, acc_ber_lane7
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            data,
        )

    conn.commit()
    conn.close()

    return db


class TestQueryEngineHighBER:
    """Test QueryEngine with high BER handling."""

    def test_query_ber_statistics_excludes_training_failures(self, test_db):
        """Test that training failures are always excluded from BER statistics."""
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("01:00.0/ETH07")

        result = engine.query_ber_statistics(selector, train_speeds=[200])

        # Should have 2 tests (PASS), not 3 (excluding TRAINING_FAIL)
        assert result.num_tests == 2

    def test_query_ber_statistics_high_ber_count(self, test_db):
        """Test that high BER values are counted separately."""
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("01:00.0/ETH07")

        result = engine.query_ber_statistics(selector, train_speeds=[200])

        # Lane 0 should have 1 high BER value (0.5)
        lane0_stats = result.lane_stats["01:00.0/ETH07/lane0"]
        assert lane0_stats.high_ber_count == 1

        # Lane 1 should have no high BER values
        lane1_stats = result.lane_stats["01:00.0/ETH07/lane1"]
        assert lane1_stats.high_ber_count == 0

    def test_query_ber_statistics_high_ber_excluded_from_avg(self, test_db):
        """Test that high BER values are excluded from min/max/avg."""
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("01:00.0/ETH07")

        result = engine.query_ber_statistics(selector, train_speeds=[200])

        # Lane 0 has values: 1e-12, 0.5
        # Only 1e-12 should be used for min/max/avg (0.5 is high BER)
        lane0_stats = result.lane_stats["01:00.0/ETH07/lane0"]
        assert lane0_stats.min_ber == 1e-12
        assert lane0_stats.max_ber == 1e-12
        assert lane0_stats.avg_ber == 1e-12
        assert lane0_stats.sample_count == 2  # Total samples including high BER

    def test_query_ber_statistics_all_high_ber(self, test_db):
        """Test handling when all BER values for a lane are high."""
        # Add data where all values are high BER
        conn = sqlite3.connect(test_db.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO prbs_tests (
                host, bus_id, eth_id, train_speed, test_status, date, source_file, ingestion_timestamp,
                acc_ber_lane0, acc_ber_lane1, acc_ber_lane2, acc_ber_lane3,
                acc_ber_lane4, acc_ber_lane5, acc_ber_lane6, acc_ber_lane7
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("sys3", "09:00.0", "ETH01", 200, "PASS", "2026-03-13", "test.csv", "2026-03-13T00:00:00",
             0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0),
        )
        conn.commit()
        conn.close()

        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("09:00.0/ETH01")

        result = engine.query_ber_statistics(selector, train_speeds=[200])

        # All lanes should have None for min/max/avg
        for lane_num in range(8):
            lane_id = f"09:00.0/ETH01/lane{lane_num}"
            lane_stats = result.lane_stats[lane_id]
            assert lane_stats.min_ber is None
            assert lane_stats.max_ber is None
            assert lane_stats.avg_ber is None
            assert lane_stats.high_ber_count == 1
            assert lane_stats.sample_count == 1

    def test_query_ber_statistics_multiple_systems(self, test_db):
        """Test querying statistics across multiple systems."""
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("all")

        result = engine.query_ber_statistics(selector)

        # Should include both systems (excluding training failures)
        assert result.num_systems == 2
        assert result.num_tests == 4  # 2 from sys1 (port 1), 1 from sys1 (port 2), 1 from sys2

    def test_query_ber_statistics_speed_filter(self, test_db):
        """Test filtering by train speed."""
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("all")

        # Filter for speed 200
        result = engine.query_ber_statistics(selector, train_speeds=[200])
        assert result.num_tests == 3  # sys1 port1 (2 tests), sys1 port2 (1 test)

        # Filter for speed 100
        result = engine.query_ber_statistics(selector, train_speeds=[100])
        assert result.num_tests == 1  # sys2 port1 (1 test)


class TestLaneBERStats:
    """Test LaneBERStats dataclass."""

    def test_lane_ber_stats_creation(self):
        """Test creating LaneBERStats with high_ber_count."""
        stats = LaneBERStats(
            lane_id="01:00.0/ETH07/lane0",
            min_ber=1e-12,
            max_ber=5e-10,
            avg_ber=2e-11,
            sample_count=100,
            high_ber_count=5,
        )

        assert stats.lane_id == "01:00.0/ETH07/lane0"
        assert stats.min_ber == 1e-12
        assert stats.max_ber == 5e-10
        assert stats.avg_ber == 2e-11
        assert stats.sample_count == 100
        assert stats.high_ber_count == 5

    def test_lane_ber_stats_with_none_values(self):
        """Test creating LaneBERStats with None values (all high BER)."""
        stats = LaneBERStats(
            lane_id="01:00.0/ETH07/lane0",
            min_ber=None,
            max_ber=None,
            avg_ber=None,
            sample_count=10,
            high_ber_count=10,
        )

        assert stats.min_ber is None
        assert stats.max_ber is None
        assert stats.avg_ber is None
        assert stats.sample_count == 10
        assert stats.high_ber_count == 10
