"""Database management module for system analysis.

This module provides SQLite database management with schema creation,
connection handling, and low-level query operations.
"""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

from bh_glx_data.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)


def get_default_db_path() -> Path:
    """Get default database path following XDG Base Directory specification.

    Returns:
        Path to default database location (~/.local/share/bh-glx-data/analysis.db)
    """
    base_dir = Path.home() / ".local" / "share" / "bh-glx-data"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "analysis.db"


@dataclass
class DatabaseStats:
    """Database statistics.

    Attributes:
        total_samples: Total number of individual test records (rows)
        total_tests: Number of unique test runs (unique host+timestamp combinations)
        unique_hosts: Number of unique hostnames
        unique_speeds: List of unique train speeds
        status_breakdown: Dictionary of test counts by status
        date_range: Tuple of (earliest_date, latest_date)
        total_ingestions: Number of ingestion runs recorded
    """

    total_samples: int
    total_tests: int
    unique_hosts: int
    unique_speeds: List[int]
    status_breakdown: dict
    date_range: tuple
    total_ingestions: int


class DatabaseManager:
    """Manages SQLite database operations for system analysis.

    This class handles database schema creation, connection management,
    batch insertions, and query execution.

    Attributes:
        db_path: Path to SQLite database file
        connection: Active database connection (None if not connected)
    """

    # SQL for creating prbs_tests table
    CREATE_PRBS_TESTS_TABLE = """
    CREATE TABLE IF NOT EXISTS prbs_tests (
        -- Primary identification
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        -- System identification
        host TEXT NOT NULL,
        bus_id TEXT NOT NULL,
        eth_id TEXT NOT NULL,
        interface_id TEXT,

        -- Test metadata
        date TEXT NOT NULL,
        test_status TEXT NOT NULL,
        train_speed INTEGER NOT NULL,
        train_type_requested TEXT,
        train_mode TEXT,
        port_type TEXT,

        -- BER data (8 lanes)
        acc_ber_lane0 REAL,
        acc_ber_lane1 REAL,
        acc_ber_lane2 REAL,
        acc_ber_lane3 REAL,
        acc_ber_lane4 REAL,
        acc_ber_lane5 REAL,
        acc_ber_lane6 REAL,
        acc_ber_lane7 REAL,

        -- Error counts
        acc_lane_error_cnt TEXT,
        acc_lane_error_cnt_overflow TEXT,

        -- Timing
        acc_time_elapsed REAL,

        -- Test parameters
        ber_threshold_used REAL,
        interface_type_used TEXT,

        -- Source tracking
        source_file TEXT NOT NULL,
        ingestion_timestamp TEXT NOT NULL
    );
    """

    # SQL for creating indexes
    CREATE_INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_host ON prbs_tests(host);",
        "CREATE INDEX IF NOT EXISTS idx_bus_id ON prbs_tests(bus_id);",
        "CREATE INDEX IF NOT EXISTS idx_eth_id ON prbs_tests(eth_id);",
        "CREATE INDEX IF NOT EXISTS idx_test_status ON prbs_tests(test_status);",
        "CREATE INDEX IF NOT EXISTS idx_train_speed ON prbs_tests(train_speed);",
        "CREATE INDEX IF NOT EXISTS idx_host_speed ON prbs_tests(host, train_speed);",
        "CREATE INDEX IF NOT EXISTS idx_bus_eth ON prbs_tests(bus_id, eth_id);",
        "CREATE INDEX IF NOT EXISTS idx_status_speed ON prbs_tests(test_status, train_speed);",
    ]

    # SQL for creating ingestion_metadata table
    CREATE_METADATA_TABLE = """
    CREATE TABLE IF NOT EXISTS ingestion_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ingestion_timestamp TEXT NOT NULL,
        source_directory TEXT NOT NULL,
        files_processed INTEGER NOT NULL,
        rows_ingested INTEGER NOT NULL,
        rows_filtered INTEGER NOT NULL,
        duration_seconds REAL NOT NULL
    );
    """

    def __init__(self, db_path: Path):
        """Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.connection: Optional[sqlite3.Connection] = None
        self._ensure_parent_dir()

    def _ensure_parent_dir(self) -> None:
        """Ensure parent directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        """Establish database connection.

        Returns:
            SQLite connection object

        Raises:
            DatabaseError: If connection fails
        """
        try:
            if self.connection is None:
                self.connection = sqlite3.connect(str(self.db_path))
                # Enable WAL mode for better concurrent read performance
                self.connection.execute("PRAGMA journal_mode=WAL")
                # Enable foreign keys
                self.connection.execute("PRAGMA foreign_keys=ON")
            return self.connection
        except sqlite3.Error as e:
            raise DatabaseError(
                f"Failed to connect to database: {e}", db_path=str(self.db_path)
            ) from e

    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def initialize_schema(self) -> None:
        """Create tables and indexes if they don't exist.

        Raises:
            DatabaseError: If schema creation fails
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Create tables
            cursor.execute(self.CREATE_PRBS_TESTS_TABLE)
            cursor.execute(self.CREATE_METADATA_TABLE)

            # Create indexes
            for index_sql in self.CREATE_INDEXES:
                cursor.execute(index_sql)

            conn.commit()
            logger.info(f"Database schema initialized: {self.db_path}")

        except sqlite3.Error as e:
            raise DatabaseError(
                f"Failed to initialize schema: {e}", db_path=str(self.db_path)
            ) from e

    def insert_batch(self, records: List[dict]) -> int:
        """Insert batch of test records efficiently.

        Args:
            records: List of test record dictionaries

        Returns:
            Number of records inserted

        Raises:
            DatabaseError: If insertion fails
        """
        if not records:
            return 0

        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Build INSERT statement
            columns = list(records[0].keys())
            placeholders = ", ".join(["?" for _ in columns])
            column_names = ", ".join(columns)

            insert_sql = f"INSERT INTO prbs_tests ({column_names}) VALUES ({placeholders})"

            # Prepare data tuples
            data_tuples = [tuple(record[col] for col in columns) for record in records]

            # Execute batch insert
            cursor.executemany(insert_sql, data_tuples)
            conn.commit()

            inserted_count = cursor.rowcount
            logger.debug(f"Inserted {inserted_count} records into database")

            return inserted_count

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to insert batch: {e}", db_path=str(self.db_path)) from e

    def insert_ingestion_metadata(
        self,
        source_directory: str,
        files_processed: int,
        rows_ingested: int,
        rows_filtered: int,
        duration_seconds: float,
    ) -> None:
        """Insert ingestion metadata record.

        Args:
            source_directory: Directory that was ingested
            files_processed: Number of files processed
            rows_ingested: Number of rows ingested
            rows_filtered: Number of rows filtered out
            duration_seconds: Duration of ingestion

        Raises:
            DatabaseError: If insertion fails
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            timestamp = datetime.now().isoformat()

            cursor.execute(
                """
                INSERT INTO ingestion_metadata
                (ingestion_timestamp, source_directory, files_processed,
                 rows_ingested, rows_filtered, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    source_directory,
                    files_processed,
                    rows_ingested,
                    rows_filtered,
                    duration_seconds,
                ),
            )

            conn.commit()
            logger.debug(f"Inserted ingestion metadata for {source_directory}")

        except sqlite3.Error as e:
            raise DatabaseError(
                f"Failed to insert ingestion metadata: {e}", db_path=str(self.db_path)
            ) from e

    def execute_query(self, query: str, params: tuple = ()) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame.

        Args:
            query: SQL query string
            params: Query parameters (for parameterized queries)

        Returns:
            DataFrame with query results

        Raises:
            DatabaseError: If query execution fails
        """
        try:
            conn = self.connect()
            df = pd.read_sql_query(query, conn, params=params)
            logger.debug(f"Query executed: {query[:100]}... (returned {len(df)} rows)")
            return df

        except (sqlite3.Error, pd.errors.DatabaseError) as e:
            raise DatabaseError(
                f"Failed to execute query: {e}", db_path=str(self.db_path), query=query
            ) from e

    def execute_scalar(self, query: str, params: tuple = ()) -> any:
        """Execute query that returns a single scalar value.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Scalar result value

        Raises:
            DatabaseError: If query execution fails
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result[0] if result else None

        except sqlite3.Error as e:
            raise DatabaseError(
                f"Failed to execute scalar query: {e}", db_path=str(self.db_path), query=query
            ) from e

    def get_unique_hosts(self) -> List[str]:
        """Get list of all unique hostnames in database.

        Returns:
            List of unique hostnames sorted alphabetically
        """
        query = "SELECT DISTINCT host FROM prbs_tests ORDER BY host"
        df = self.execute_query(query)
        return df["host"].tolist()

    def get_unique_speeds(self) -> List[int]:
        """Get list of all unique train speeds.

        Returns:
            List of unique train speeds sorted ascending
        """
        query = "SELECT DISTINCT train_speed FROM prbs_tests ORDER BY train_speed"
        df = self.execute_query(query)
        return df["train_speed"].tolist()

    def get_database_stats(self) -> DatabaseStats:
        """Get statistics about the database contents.

        Returns:
            DatabaseStats object with summary information
        """
        # Total samples (individual records/rows)
        total_samples = self.execute_scalar("SELECT COUNT(*) FROM prbs_tests") or 0

        # Total tests (unique test runs = unique host+timestamp combinations)
        total_tests = self.execute_scalar(
            "SELECT COUNT(DISTINCT host || '|' || date) FROM prbs_tests"
        ) or 0

        # Unique hosts
        unique_hosts = self.execute_scalar("SELECT COUNT(DISTINCT host) FROM prbs_tests") or 0

        # Unique speeds
        speeds = self.get_unique_speeds()

        # Status breakdown
        status_df = self.execute_query(
            """
            SELECT test_status, COUNT(*) as count
            FROM prbs_tests
            GROUP BY test_status
            ORDER BY count DESC
            """
        )
        status_breakdown = dict(zip(status_df["test_status"], status_df["count"]))

        # Date range
        date_query = "SELECT MIN(date) as min_date, MAX(date) as max_date FROM prbs_tests WHERE date IS NOT NULL AND date != ''"
        date_df = self.execute_query(date_query)
        if not date_df.empty and date_df["min_date"].iloc[0] is not None:
            min_date = date_df["min_date"].iloc[0]
            max_date = date_df["max_date"].iloc[0]
            # Handle empty strings
            if min_date and min_date.strip() and max_date and max_date.strip():
                date_range = (min_date, max_date)
            else:
                date_range = ("N/A", "N/A")
        else:
            date_range = ("N/A", "N/A")

        # Total ingestions
        total_ingestions = (
            self.execute_scalar("SELECT COUNT(*) FROM ingestion_metadata") or 0
        )

        return DatabaseStats(
            total_samples=total_samples,
            total_tests=total_tests,
            unique_hosts=unique_hosts,
            unique_speeds=speeds,
            status_breakdown=status_breakdown,
            date_range=date_range,
            total_ingestions=total_ingestions,
        )

    def vacuum(self) -> None:
        """Vacuum database to reclaim space and optimize.

        This operation should be run periodically to compact the database
        and rebuild indexes for better performance.
        """
        try:
            conn = self.connect()
            conn.execute("VACUUM")
            logger.info(f"Database vacuumed: {self.db_path}")

        except sqlite3.Error as e:
            raise DatabaseError(
                f"Failed to vacuum database: {e}", db_path=str(self.db_path)
            ) from e

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
