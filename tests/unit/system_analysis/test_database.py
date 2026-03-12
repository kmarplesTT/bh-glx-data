"""Unit tests for database module."""

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from bh_glx_data.core.exceptions import DatabaseError
from bh_glx_data.system_analysis.database import DatabaseManager, get_default_db_path


class TestGetDefaultDbPath:
    """Test get_default_db_path function."""

    def test_returns_path_object(self):
        """Test that function returns a Path object."""
        result = get_default_db_path()
        assert isinstance(result, Path)

    def test_uses_xdg_data_home(self):
        """Test that path uses XDG_DATA_HOME directory."""
        result = get_default_db_path()
        assert "bh-glx-data" in str(result)
        assert "analysis.db" in str(result)


class TestDatabaseManager:
    """Test DatabaseManager class."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary database for testing."""
        db_path = tmp_path / "test.db"
        db = DatabaseManager(db_path)
        db.initialize_schema()
        yield db
        db.close()

    def test_init(self, tmp_path):
        """Test DatabaseManager initialization."""
        db_path = tmp_path / "test.db"
        db = DatabaseManager(db_path)

        assert db.db_path == db_path
        assert db.connection is None

    def test_initialize_schema_creates_tables(self, tmp_path):
        """Test that initialize_schema creates all required tables."""
        db_path = tmp_path / "test.db"
        db = DatabaseManager(db_path)
        db.initialize_schema()

        # Check that tables exist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check prbs_tests table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='prbs_tests'"
        )
        assert cursor.fetchone() is not None

        # Check ingestion_metadata table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ingestion_metadata'"
        )
        assert cursor.fetchone() is not None

        conn.close()
        db.close()

    def test_initialize_schema_creates_indexes(self, tmp_path):
        """Test that initialize_schema creates all required indexes."""
        db_path = tmp_path / "test.db"
        db = DatabaseManager(db_path)
        db.initialize_schema()

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check for some expected indexes
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_host'"
        )
        assert cursor.fetchone() is not None

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_bus_id'"
        )
        assert cursor.fetchone() is not None

        conn.close()
        db.close()

    def test_initialize_schema_idempotent(self, tmp_path):
        """Test that initialize_schema can be called multiple times safely."""
        db_path = tmp_path / "test.db"
        db = DatabaseManager(db_path)

        # Call multiple times
        db.initialize_schema()
        db.initialize_schema()
        db.initialize_schema()

        # Should not raise an error
        db.close()

    def test_insert_batch(self, temp_db, tmp_path):
        """Test batch insertion of test records."""
        from bh_glx_data.system_analysis.ingestion import TestRecord

        # Create test records
        records = [
            TestRecord(
                host="test-host-01",
                bus_id="01:00.0",
                eth_id="ETH00",
                date="2024-01-01",
                test_status="PASS",
                train_speed=100,
                acc_ber_lanes=[1e-12, 2e-12, 3e-12, 4e-12, None, None, None, None],
                acc_time_elapsed=10.0,
                source_file="test.csv",
                ingestion_timestamp="2024-01-01T12:00:00",
            ),
            TestRecord(
                host="test-host-02",
                bus_id="02:00.0",
                eth_id="ETH01",
                date="2024-01-01",
                test_status="BER_THRESHOLD_EXCEEDED",
                train_speed=200,
                acc_ber_lanes=[1e-10, 2e-10, 3e-10, 4e-10, None, None, None, None],
                acc_time_elapsed=15.0,
                source_file="test.csv",
                ingestion_timestamp="2024-01-01T12:00:00",
            ),
        ]

        # Insert records (convert to dicts)
        count = temp_db.insert_batch([r.to_dict() for r in records])

        assert count == 2

        # Verify records were inserted
        df = temp_db.execute_query("SELECT * FROM prbs_tests")
        assert len(df) == 2
        assert df["host"].tolist() == ["test-host-01", "test-host-02"]

    def test_execute_query(self, temp_db):
        """Test query execution."""
        from bh_glx_data.system_analysis.ingestion import TestRecord

        # Insert test data
        records = [
            TestRecord(
                host="test-host",
                bus_id="01:00.0",
                eth_id="ETH00",
                date="2024-01-01",
                test_status="PASS",
                train_speed=100,
                acc_ber_lanes=[1e-12] * 8,
                acc_time_elapsed=10.0,
                source_file="test.csv",
                ingestion_timestamp="2024-01-01T12:00:00",
            )
        ]
        temp_db.insert_batch([r.to_dict() for r in records])

        # Query data
        df = temp_db.execute_query("SELECT * FROM prbs_tests WHERE host = ?", ("test-host",))

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df.iloc[0]["host"] == "test-host"

    def test_get_unique_hosts(self, temp_db):
        """Test getting unique hosts."""
        from bh_glx_data.system_analysis.ingestion import TestRecord

        # Insert test data with multiple hosts
        records = [
            TestRecord(
                host="host-a",
                bus_id="01:00.0",
                eth_id="ETH00",
                date="2024-01-01",
                test_status="PASS",
                train_speed=100,
                acc_ber_lanes=[1e-12] * 8,
                acc_time_elapsed=10.0,
                source_file="test.csv",
                ingestion_timestamp="2024-01-01T12:00:00",
            ),
            TestRecord(
                host="host-b",
                bus_id="02:00.0",
                eth_id="ETH01",
                date="2024-01-01",
                test_status="PASS",
                train_speed=100,
                acc_ber_lanes=[1e-12] * 8,
                acc_time_elapsed=10.0,
                source_file="test.csv",
                ingestion_timestamp="2024-01-01T12:00:00",
            ),
            TestRecord(
                host="host-a",
                bus_id="01:00.0",
                eth_id="ETH02",
                date="2024-01-01",
                test_status="PASS",
                train_speed=100,
                acc_ber_lanes=[1e-12] * 8,
                acc_time_elapsed=10.0,
                source_file="test.csv",
                ingestion_timestamp="2024-01-01T12:00:00",
            ),
        ]
        temp_db.insert_batch([r.to_dict() for r in records])

        hosts = temp_db.get_unique_hosts()

        assert len(hosts) == 2
        assert "host-a" in hosts
        assert "host-b" in hosts

    def test_get_unique_speeds(self, temp_db):
        """Test getting unique train speeds."""
        from bh_glx_data.system_analysis.ingestion import TestRecord

        # Insert test data with multiple speeds
        records = [
            TestRecord(
                host="host-a",
                bus_id="01:00.0",
                eth_id="ETH00",
                date="2024-01-01",
                test_status="PASS",
                train_speed=100,
                acc_ber_lanes=[1e-12] * 8,
                acc_time_elapsed=10.0,
                source_file="test.csv",
                ingestion_timestamp="2024-01-01T12:00:00",
            ),
            TestRecord(
                host="host-a",
                bus_id="01:00.0",
                eth_id="ETH01",
                date="2024-01-01",
                test_status="PASS",
                train_speed=200,
                acc_ber_lanes=[1e-12] * 8,
                acc_time_elapsed=10.0,
                source_file="test.csv",
                ingestion_timestamp="2024-01-01T12:00:00",
            ),
        ]
        temp_db.insert_batch([r.to_dict() for r in records])

        speeds = temp_db.get_unique_speeds()

        assert len(speeds) == 2
        assert 100 in speeds
        assert 200 in speeds

    def test_get_database_stats(self, temp_db):
        """Test getting database statistics."""
        from bh_glx_data.system_analysis.ingestion import TestRecord

        # Insert test data
        records = [
            TestRecord(
                host="host-a",
                bus_id="01:00.0",
                eth_id="ETH00",
                date="2024-01-01",
                test_status="PASS",
                train_speed=100,
                acc_ber_lanes=[1e-12] * 8,
                acc_time_elapsed=10.0,
                source_file="test.csv",
                ingestion_timestamp="2024-01-01T12:00:00",
            ),
            TestRecord(
                host="host-b",
                bus_id="02:00.0",
                eth_id="ETH01",
                date="2024-01-02",
                test_status="TRAINING_FAIL",
                train_speed=200,
                acc_ber_lanes=[None] * 8,
                acc_time_elapsed=5.0,
                source_file="test.csv",
                ingestion_timestamp="2024-01-01T12:00:00",
            ),
        ]
        temp_db.insert_batch([r.to_dict() for r in records])

        stats = temp_db.get_database_stats()

        assert stats.total_tests == 2
        assert stats.unique_hosts == 2
        assert stats.unique_speeds == [100, 200]
        assert "PASS" in stats.status_breakdown
        assert "TRAINING_FAIL" in stats.status_breakdown
        assert stats.status_breakdown["PASS"] == 1
        assert stats.status_breakdown["TRAINING_FAIL"] == 1

    def test_close(self, tmp_path):
        """Test closing database connection."""
        db_path = tmp_path / "test.db"
        db = DatabaseManager(db_path)
        db.initialize_schema()

        # Connection should be established
        assert db.connection is not None

        db.close()

        # Connection should be None
        assert db.connection is None

    def test_context_manager(self, tmp_path):
        """Test using DatabaseManager as context manager."""
        db_path = tmp_path / "test.db"

        with DatabaseManager(db_path) as db:
            db.initialize_schema()
            assert db.connection is not None

        # Connection should be closed after exiting context
        assert db.connection is None


class TestDatabaseErrors:
    """Test database error handling."""

    def test_invalid_query_raises_error(self, tmp_path):
        """Test that invalid queries raise DatabaseError."""
        db_path = tmp_path / "test.db"
        db = DatabaseManager(db_path)
        db.initialize_schema()

        with pytest.raises(DatabaseError):
            db.execute_query("SELECT * FROM nonexistent_table")

        db.close()
