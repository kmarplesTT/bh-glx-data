"""Query engine module for system analysis.

This module provides high-level query interface with lane selection logic
and result dataclasses for BER statistics and failure counts.
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

from bh_glx_data.core.exceptions import LaneSelectorError, QueryError
from bh_glx_data.system_analysis.database import DatabaseManager
from bh_glx_data.system_analysis.statistics import (
    calculate_lane_statistics,
    count_by_status,
    count_by_threshold,
)

logger = logging.getLogger(__name__)


@dataclass
class LaneBERStats:
    """Statistics for a single lane.

    Attributes:
        lane_id: Lane identifier (e.g., "01:00.0/ETH07/lane0")
        min_ber: Minimum BER value
        max_ber: Maximum BER value
        avg_ber: Average BER value
        sample_count: Number of samples
    """

    lane_id: str
    min_ber: Optional[float]
    max_ber: Optional[float]
    avg_ber: Optional[float]
    sample_count: int


@dataclass
class BERStatistics:
    """BER statistics result.

    Attributes:
        lane_stats: Dictionary mapping lane_id to LaneBERStats
        num_tests: Total number of tests included
        num_systems: Number of unique systems
        train_speeds: List of train speeds included
    """

    lane_stats: Dict[str, LaneBERStats]
    num_tests: int
    num_systems: int
    train_speeds: List[int]


@dataclass
class ThresholdExceededCounts:
    """BER threshold exceeded counts.

    Attributes:
        lane_counts: Dictionary mapping lane_id to count
        num_tests: Total number of tests included
        num_systems: Number of unique systems
        train_speeds: List of train speeds included
    """

    lane_counts: Dict[str, int]
    num_tests: int
    num_systems: int
    train_speeds: List[int]


@dataclass
class CustomThresholdCounts:
    """Custom BER threshold counts.

    Attributes:
        lane_counts: Dictionary mapping lane_id to count
        threshold: Threshold value used
        num_tests: Total number of tests included
        num_systems: Number of unique systems
        train_speeds: List of train speeds included
    """

    lane_counts: Dict[str, int]
    threshold: float
    num_tests: int
    num_systems: int
    train_speeds: List[int]


@dataclass
class TrainingFailureCounts:
    """Training failure counts.

    Attributes:
        lane_counts: Dictionary mapping lane_id to count
        num_tests: Total number of tests included
        num_systems: Number of unique systems
        train_speeds: List of train speeds included
    """

    lane_counts: Dict[str, int]
    num_tests: int
    num_systems: int
    train_speeds: List[int]


class LaneSelector:
    """Specifies which serdes lanes to query.

    The LaneSelector parses lane specification strings and generates
    SQL WHERE clauses for filtering database queries.

    Supported formats:
        - "all" -> All lanes on all systems
        - "01:00.0/ETH07" -> Specific port (all lanes)
        - "01:00.0/*" -> All ports on bus_id
        - "bh-glx-c02u02/01:00.0/ETH07" -> Specific system and port
        - "bh-glx-c02u02/*" -> All ports on system
        - "*/ETH07" -> ETH07 on all systems

    Attributes:
        spec: Original specification string
        host_pattern: Host filter (None = all hosts, "*" = wildcard, specific hostname)
        bus_id_pattern: Bus ID filter (None = all, "*" = wildcard, specific bus_id)
        eth_id_pattern: Ethernet port filter (None = all, "*" = wildcard, specific eth_id)
    """

    def __init__(
        self,
        host_pattern: Optional[str] = None,
        bus_id_pattern: Optional[str] = None,
        eth_id_pattern: Optional[str] = None,
    ):
        """Initialize lane selector.

        Args:
            host_pattern: Host filter pattern
            bus_id_pattern: Bus ID filter pattern
            eth_id_pattern: Ethernet port filter pattern
        """
        self.host_pattern = host_pattern
        self.bus_id_pattern = bus_id_pattern
        self.eth_id_pattern = eth_id_pattern
        self.spec = self._build_spec()

    def _build_spec(self) -> str:
        """Build specification string from patterns."""
        parts = []

        if self.host_pattern and self.host_pattern != "*":
            parts.append(self.host_pattern)

        if self.bus_id_pattern and self.bus_id_pattern != "*":
            parts.append(self.bus_id_pattern)
        elif self.host_pattern or self.bus_id_pattern:
            parts.append("*")

        if self.eth_id_pattern and self.eth_id_pattern != "*":
            parts.append(self.eth_id_pattern)
        elif parts:
            parts.append("*")

        return "/".join(parts) if parts else "all"

    @classmethod
    def from_spec(cls, spec: str) -> "LaneSelector":
        """Parse lane specification string.

        Args:
            spec: Lane specification string

        Returns:
            LaneSelector instance

        Raises:
            LaneSelectorError: If spec format is invalid

        Examples:
            "all" -> All lanes on all systems
            "01:00.0/ETH07" -> Specific port
            "01:00.0/*" -> All ports on bus_id
            "bh-glx-c02u02/01:00.0/ETH07" -> Specific system and port
            "bh-glx-c02u02/*" -> All ports on system
            "*/ETH07" -> ETH07 on all systems
        """
        spec = spec.strip()

        # Handle "all" special case
        if spec.lower() == "all":
            return cls(host_pattern=None, bus_id_pattern=None, eth_id_pattern=None)

        # Split by "/"
        parts = spec.split("/")

        if len(parts) == 1:
            # Could be just host or just bus_id
            part = parts[0]
            if part == "*":
                return cls(host_pattern=None, bus_id_pattern=None, eth_id_pattern=None)

            # Check if it looks like a bus_id (contains ":")
            if ":" in part:
                return cls(host_pattern=None, bus_id_pattern=part, eth_id_pattern=None)
            else:
                # Assume it's a hostname
                return cls(host_pattern=part, bus_id_pattern=None, eth_id_pattern=None)

        elif len(parts) == 2:
            # Could be bus_id/eth_id or host/bus_id
            first, second = parts

            # If first contains ":", it's bus_id/eth_id
            if ":" in first:
                return cls(host_pattern=None, bus_id_pattern=first, eth_id_pattern=second)
            else:
                # Otherwise it's host/bus_id or host/eth_id
                # If second contains ":", it's host/bus_id
                if ":" in second:
                    return cls(host_pattern=first, bus_id_pattern=second, eth_id_pattern=None)
                else:
                    # It's host/eth_id
                    return cls(host_pattern=first, bus_id_pattern=None, eth_id_pattern=second)

        elif len(parts) == 3:
            # host/bus_id/eth_id
            host, bus_id, eth_id = parts
            return cls(host_pattern=host, bus_id_pattern=bus_id, eth_id_pattern=eth_id)

        else:
            raise LaneSelectorError(f"Invalid lane specification format: {spec}", spec=spec)

    def to_sql_filter(self) -> Tuple[str, tuple]:
        """Generate SQL WHERE clause for this selector.

        Returns:
            Tuple of (where_clause, params) for parameterized query

        Example:
            ("bus_id = ? AND eth_id = ?", ("01:00.0", "ETH07"))
        """
        conditions = []
        params = []

        # Host filter
        if self.host_pattern and self.host_pattern != "*":
            conditions.append("host = ?")
            params.append(self.host_pattern)

        # Bus ID filter
        if self.bus_id_pattern and self.bus_id_pattern != "*":
            conditions.append("bus_id = ?")
            params.append(self.bus_id_pattern)

        # Eth ID filter
        if self.eth_id_pattern and self.eth_id_pattern != "*":
            conditions.append("eth_id = ?")
            params.append(self.eth_id_pattern)

        if conditions:
            where_clause = " AND ".join(conditions)
        else:
            where_clause = "1=1"  # Always true (select all)

        return where_clause, tuple(params)

    def __str__(self) -> str:
        """String representation."""
        return self.spec


class QueryEngine:
    """High-level query interface for PRBS test data.

    This class provides methods for querying BER statistics and failure counts
    with flexible lane selection and filtering options.

    Attributes:
        db: DatabaseManager instance
    """

    # Lane column names
    LANE_COLUMNS = [
        "acc_ber_lane0",
        "acc_ber_lane1",
        "acc_ber_lane2",
        "acc_ber_lane3",
        "acc_ber_lane4",
        "acc_ber_lane5",
        "acc_ber_lane6",
        "acc_ber_lane7",
    ]

    def __init__(self, db_manager: DatabaseManager):
        """Initialize query engine.

        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager

    def query_ber_statistics(
        self,
        lane_selector: LaneSelector,
        train_speeds: Optional[List[int]] = None,
        exclude_training_failures: bool = True,
    ) -> BERStatistics:
        """Calculate BER statistics for specified lanes.

        Args:
            lane_selector: Specifies which lanes to analyze
            train_speeds: Filter by specific speeds (None = all)
            exclude_training_failures: Exclude rows with test_status=TRAINING_FAIL

        Returns:
            BERStatistics with per-lane stats and metadata

        Raises:
            QueryError: If query execution fails
        """
        try:
            # Build query
            where_clause, params = lane_selector.to_sql_filter()

            # Add speed filter
            if train_speeds:
                speed_placeholders = ", ".join(["?" for _ in train_speeds])
                where_clause += f" AND train_speed IN ({speed_placeholders})"
                params = params + tuple(train_speeds)

            # Exclude training failures (no BER data)
            if exclude_training_failures:
                where_clause += " AND test_status != 'TRAINING_FAIL'"

            query = f"SELECT * FROM prbs_tests WHERE {where_clause}"

            # Execute query
            df = self.db.execute_query(query, params)

            if df.empty:
                logger.warning(f"No data found for lane selector: {lane_selector}")
                return BERStatistics(
                    lane_stats={},
                    num_tests=0,
                    num_systems=0,
                    train_speeds=train_speeds or [],
                )

            # Calculate statistics per lane
            lane_stats_dict = calculate_lane_statistics(df, self.LANE_COLUMNS)

            # Convert to LaneBERStats objects with full lane IDs
            lane_stats = {}
            for lane_col, stats in lane_stats_dict.items():
                # Extract lane number from column name
                lane_num = int(lane_col.replace("acc_ber_lane", ""))

                # Build lane IDs for each unique bus_id/eth_id combination
                for (bus_id, eth_id), group in df.groupby(["bus_id", "eth_id"]):
                    lane_id = f"{bus_id}/{eth_id}/lane{lane_num}"

                    # Calculate stats for this specific lane
                    lane_values = group[lane_col].dropna()

                    if not lane_values.empty:
                        lane_stats[lane_id] = LaneBERStats(
                            lane_id=lane_id,
                            min_ber=float(lane_values.min()),
                            max_ber=float(lane_values.max()),
                            avg_ber=float(lane_values.mean()),
                            sample_count=len(lane_values),
                        )

            # Metadata
            num_tests = len(df)
            num_systems = df["host"].nunique()
            speeds = sorted(df["train_speed"].unique().tolist())

            return BERStatistics(
                lane_stats=lane_stats,
                num_tests=num_tests,
                num_systems=num_systems,
                train_speeds=speeds,
            )

        except Exception as e:
            raise QueryError(
                f"Failed to query BER statistics: {e}", lane_spec=str(lane_selector)
            ) from e

    def query_ber_threshold_exceeded(
        self,
        lane_selector: LaneSelector,
        train_speeds: Optional[List[int]] = None,
    ) -> ThresholdExceededCounts:
        """Count BER_THRESHOLD_EXCEEDED occurrences per lane.

        Args:
            lane_selector: Specifies which lanes to analyze
            train_speeds: Filter by specific speeds (None = all)

        Returns:
            ThresholdExceededCounts with per-lane counts

        Raises:
            QueryError: If query execution fails
        """
        try:
            # Build query
            where_clause, params = lane_selector.to_sql_filter()

            # Filter by status
            where_clause += " AND test_status = 'BER_THRESHOLD_EXCEEDED'"

            # Add speed filter
            if train_speeds:
                speed_placeholders = ", ".join(["?" for _ in train_speeds])
                where_clause += f" AND train_speed IN ({speed_placeholders})"
                params = params + tuple(train_speeds)

            query = f"SELECT * FROM prbs_tests WHERE {where_clause}"

            # Execute query
            df = self.db.execute_query(query, params)

            if df.empty:
                logger.warning(
                    f"No BER_THRESHOLD_EXCEEDED data found for lane selector: {lane_selector}"
                )
                return ThresholdExceededCounts(
                    lane_counts={},
                    num_tests=0,
                    num_systems=0,
                    train_speeds=train_speeds or [],
                )

            # Count by lane
            lane_counts_dict = count_by_status(df, "BER_THRESHOLD_EXCEEDED", self.LANE_COLUMNS)

            # Build full lane IDs
            lane_counts = {}
            for lane_col, count in lane_counts_dict.items():
                lane_num = int(lane_col.replace("acc_ber_lane", ""))

                # Build lane IDs for each unique bus_id/eth_id
                for (bus_id, eth_id), group in df.groupby(["bus_id", "eth_id"]):
                    lane_id = f"{bus_id}/{eth_id}/lane{lane_num}"

                    # Count non-null values for this specific lane
                    lane_count = group[lane_col].notna().sum()
                    if lane_count > 0:
                        lane_counts[lane_id] = int(lane_count)

            # Metadata
            num_tests = len(df)
            num_systems = df["host"].nunique()
            speeds = sorted(df["train_speed"].unique().tolist())

            return ThresholdExceededCounts(
                lane_counts=lane_counts,
                num_tests=num_tests,
                num_systems=num_systems,
                train_speeds=speeds,
            )

        except Exception as e:
            raise QueryError(
                f"Failed to query BER threshold exceeded: {e}", lane_spec=str(lane_selector)
            ) from e

    def query_custom_ber_threshold(
        self,
        lane_selector: LaneSelector,
        threshold: float,
        train_speeds: Optional[List[int]] = None,
    ) -> CustomThresholdCounts:
        """Count occurrences where acc_ber_lane# > threshold.

        Args:
            lane_selector: Specifies which lanes to analyze
            threshold: BER threshold value
            train_speeds: Filter by specific speeds (None = all)

        Returns:
            CustomThresholdCounts with per-lane counts

        Raises:
            QueryError: If query execution fails
        """
        try:
            # Build query
            where_clause, params = lane_selector.to_sql_filter()

            # Add speed filter
            if train_speeds:
                speed_placeholders = ", ".join(["?" for _ in train_speeds])
                where_clause += f" AND train_speed IN ({speed_placeholders})"
                params = params + tuple(train_speeds)

            # Exclude training failures (no BER data)
            where_clause += " AND test_status != 'TRAINING_FAIL'"

            query = f"SELECT * FROM prbs_tests WHERE {where_clause}"

            # Execute query
            df = self.db.execute_query(query, params)

            if df.empty:
                logger.warning(f"No data found for lane selector: {lane_selector}")
                return CustomThresholdCounts(
                    lane_counts={},
                    threshold=threshold,
                    num_tests=0,
                    num_systems=0,
                    train_speeds=train_speeds or [],
                )

            # Count by threshold
            lane_counts_dict = count_by_threshold(df, threshold, self.LANE_COLUMNS)

            # Build full lane IDs
            lane_counts = {}
            for lane_col, count in lane_counts_dict.items():
                lane_num = int(lane_col.replace("acc_ber_lane", ""))

                # Build lane IDs for each unique bus_id/eth_id
                for (bus_id, eth_id), group in df.groupby(["bus_id", "eth_id"]):
                    lane_id = f"{bus_id}/{eth_id}/lane{lane_num}"

                    # Count values exceeding threshold
                    lane_count = (group[lane_col] > threshold).sum()
                    if lane_count > 0:
                        lane_counts[lane_id] = int(lane_count)

            # Metadata
            num_tests = len(df)
            num_systems = df["host"].nunique()
            speeds = sorted(df["train_speed"].unique().tolist())

            return CustomThresholdCounts(
                lane_counts=lane_counts,
                threshold=threshold,
                num_tests=num_tests,
                num_systems=num_systems,
                train_speeds=speeds,
            )

        except Exception as e:
            raise QueryError(
                f"Failed to query custom threshold: {e}", lane_spec=str(lane_selector)
            ) from e

    def query_training_failures(
        self,
        lane_selector: LaneSelector,
        train_speeds: Optional[List[int]] = None,
    ) -> TrainingFailureCounts:
        """Count TRAINING_FAIL occurrences per lane.

        Args:
            lane_selector: Specifies which lanes to analyze
            train_speeds: Filter by specific speeds (None = all)

        Returns:
            TrainingFailureCounts with per-lane counts

        Raises:
            QueryError: If query execution fails
        """
        try:
            # Build query
            where_clause, params = lane_selector.to_sql_filter()

            # Filter by status
            where_clause += " AND test_status = 'TRAINING_FAIL'"

            # Add speed filter
            if train_speeds:
                speed_placeholders = ", ".join(["?" for _ in train_speeds])
                where_clause += f" AND train_speed IN ({speed_placeholders})"
                params = params + tuple(train_speeds)

            query = f"SELECT * FROM prbs_tests WHERE {where_clause}"

            # Execute query
            df = self.db.execute_query(query, params)

            if df.empty:
                logger.warning(f"No TRAINING_FAIL data found for lane selector: {lane_selector}")
                return TrainingFailureCounts(
                    lane_counts={},
                    num_tests=0,
                    num_systems=0,
                    train_speeds=train_speeds or [],
                )

            # Count by lane
            lane_counts_dict = count_by_status(df, "TRAINING_FAIL", self.LANE_COLUMNS)

            # Build full lane IDs
            lane_counts = {}
            for lane_col, count in lane_counts_dict.items():
                lane_num = int(lane_col.replace("acc_ber_lane", ""))

                # Build lane IDs for each unique bus_id/eth_id
                for (bus_id, eth_id), group in df.groupby(["bus_id", "eth_id"]):
                    lane_id = f"{bus_id}/{eth_id}/lane{lane_num}"

                    # Count non-null values (training failures still have lane markers)
                    # We count all rows since they're already filtered to TRAINING_FAIL
                    lane_count = len(group)
                    if lane_count > 0:
                        lane_counts[lane_id] = int(lane_count)

            # Metadata
            num_tests = len(df)
            num_systems = df["host"].nunique()
            speeds = sorted(df["train_speed"].unique().tolist())

            return TrainingFailureCounts(
                lane_counts=lane_counts,
                num_tests=num_tests,
                num_systems=num_systems,
                train_speeds=speeds,
            )

        except Exception as e:
            raise QueryError(
                f"Failed to query training failures: {e}", lane_spec=str(lane_selector)
            ) from e
