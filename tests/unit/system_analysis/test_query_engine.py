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

class TestQueryBERHistogram:
    """Test query_ber_histogram method."""

    def test_query_histogram_single_lane(self, test_db):
        """Test querying histogram for single lane."""
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("01:00.0/ETH07/0")

        result = engine.query_ber_histogram(selector)

        # Should return single BERHistogram (not a list)
        assert hasattr(result, 'lane_id')
        assert result.lane_id == "01:00.0/ETH07/lane0"
        assert len(result.bins) == 10  # 10 histogram bins
        assert result.num_systems == 2  # sys1 and sys2
        assert 200 in result.train_speeds

    def test_query_histogram_all_lanes(self, test_db):
        """Test querying histogram for all lanes on a port."""
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("01:00.0/ETH07")

        result = engine.query_ber_histogram(selector)

        # Should return list of BERHistogram
        assert isinstance(result, list)
        assert len(result) == 8  # 8 lanes
        assert all(h.num_systems == 2 for h in result)  # sys1 and sys2

    def test_query_histogram_excludes_training_failures(self, test_db):
        """Test that histogram excludes TRAINING_FAIL rows."""
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("01:00.0/ETH07/0")

        result = engine.query_ber_histogram(selector)

        # Training failure row should not contribute to histogram
        # Should have 3 samples (2 PASS rows from sys1 + 1 PASS row from sys2)
        assert result.num_tests == 3

    def test_query_histogram_bin_counts(self, test_db):
        """Test histogram bin counting."""
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("01:00.0/ETH07/0")

        result = engine.query_ber_histogram(selector)

        # Check bins structure
        bin_labels = [label for label, _ in result.bins]
        assert "< 1e-12" in bin_labels
        assert ">= 1e-4" in bin_labels

        # Check that counts sum to total samples
        total_count = sum(count for _, count in result.bins)
        assert total_count == result.num_tests


class TestQueryAggregatedHostStats:
    """Test query_aggregated_host_stats method."""

    def test_query_aggregated_stats_single_lane(self, test_db):
        """Test querying aggregated stats for single lane."""
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("01:00.0/ETH07/0")

        result = engine.query_aggregated_host_stats(selector)

        # Should return single AggregatedHostStats
        assert hasattr(result, 'lane_id')
        assert result.lane_id == "01:00.0/ETH07/lane0"
        assert result.num_systems == 2  # sys1 and sys2

        # Should have stats for both systems
        assert len(result.host_stats) == 2
        hosts = [h.host for h in result.host_stats]
        assert "sys1" in hosts
        assert "sys2" in hosts

    def test_query_aggregated_stats_all_lanes(self, test_db):
        """Test querying aggregated stats for all lanes."""
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("01:00.0/ETH07")

        result = engine.query_aggregated_host_stats(selector)

        # Should return list
        assert isinstance(result, list)
        assert len(result) == 8  # 8 lanes

    def test_aggregated_stats_calculations(self, test_db):
        """Test that aggregated statistics are calculated correctly."""
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("01:00.0/ETH07/0")

        result = engine.query_aggregated_host_stats(selector)

        # Verify structure
        assert result.min_of_mins is not None
        assert result.avg_of_mins is not None
        assert result.max_of_mins is not None
        assert result.min_of_avgs is not None
        assert result.avg_of_avgs is not None
        assert result.max_of_avgs is not None
        assert result.min_of_maxs is not None
        assert result.avg_of_maxs is not None
        assert result.max_of_maxs is not None

        # Check that min <= avg <= max for each statistic
        assert result.min_of_mins <= result.avg_of_mins <= result.max_of_mins
        assert result.min_of_avgs <= result.avg_of_avgs <= result.max_of_avgs
        assert result.min_of_maxs <= result.avg_of_maxs <= result.max_of_maxs

    def test_aggregated_stats_excludes_training_failures(self, test_db):
        """Test that aggregated stats excludes TRAINING_FAIL rows."""
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("01:00.0/ETH07/0")

        result = engine.query_aggregated_host_stats(selector)

        # Check that host_stats have correct sample counts
        # sys1 should have 2 samples (excluding TRAINING_FAIL)
        sys1_stats = next(h for h in result.host_stats if h.host == "sys1")
        assert sys1_stats.sample_count == 2

    def test_aggregated_stats_high_ber_handling(self, test_db):
        """Test that high BER values are excluded from min/avg/max but counted."""
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("01:00.0/ETH07/0")

        result = engine.query_aggregated_host_stats(selector)

        # sys1 has one sample with high BER (0.5)
        # It should be excluded from stats but counted in sample_count
        sys1_stats = next(h for h in result.host_stats if h.host == "sys1")

        # BER stats should be based on the non-high-BER sample (1e-12)
        # Not None because there's one valid sample
        assert sys1_stats.min_ber is not None
        assert sys1_stats.avg_ber is not None
        assert sys1_stats.max_ber is not None

    def test_aggregated_stats_empty_result(self, test_db):
        """Test aggregated stats with no matching data."""
        engine = QueryEngine(test_db)
        # Query for non-existent system
        selector = LaneSelector.from_spec("99:00.0/ETH99/0")

        result = engine.query_aggregated_host_stats(selector)

        # Should return single empty result
        assert hasattr(result, 'lane_id')
        assert len(result.host_stats) == 0
        assert result.num_systems == 0
