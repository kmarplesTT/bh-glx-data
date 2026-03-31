"""Query engine module for system analysis.

This module provides high-level query interface with lane selection logic
and result dataclasses for BER statistics and failure counts.
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

from bh_glx_data.core.exceptions import LaneSelectorError, QueryError
from bh_glx_data.hardware.platform_topology import normalize_bus_id, normalize_eth_port
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
        min_ber: Minimum BER value (excluding high BER >= 0.1)
        max_ber: Maximum BER value (excluding high BER >= 0.1)
        avg_ber: Average BER value (excluding high BER >= 0.1)
        sample_count: Number of samples
        high_ber_count: Number of samples with BER >= 0.1
    """

    lane_id: str
    min_ber: Optional[float]
    max_ber: Optional[float]
    avg_ber: Optional[float]
    sample_count: int
    high_ber_count: int


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


@dataclass
class BERHistogram:
    """BER histogram result.

    Attributes:
        lane_id: Full lane identifier (e.g., "01:00.0/ETH07/lane4")
        bins: List of (range_label, count) tuples for each bin
        num_tests: Total number of tests included
        num_systems: Number of unique systems
        train_speeds: List of speeds included
    """

    lane_id: str
    bins: List[Tuple[str, int]]
    num_tests: int
    num_systems: int
    train_speeds: List[int]


@dataclass
class HostBERStats:
    """BER statistics for a single host.

    Attributes:
        host: Hostname
        min_ber: Minimum BER across all samples for this host
        avg_ber: Average BER across all samples for this host
        max_ber: Maximum BER across all samples for this host
        sample_count: Number of samples for this host
    """

    host: str
    min_ber: Optional[float]
    avg_ber: Optional[float]
    max_ber: Optional[float]
    sample_count: int


@dataclass
class AggregatedHostStats:
    """Statistics of host statistics.

    Attributes:
        lane_id: Lane identifier
        host_stats: List of per-host statistics
        min_of_mins: Minimum of all host min values
        avg_of_mins: Average of all host min values
        max_of_mins: Maximum of all host min values
        min_of_avgs: Minimum of all host avg values
        avg_of_avgs: Average of all host avg values
        max_of_avgs: Maximum of all host avg values
        min_of_maxs: Minimum of all host max values
        avg_of_maxs: Average of all host max values
        max_of_maxs: Maximum of all host max values
        num_systems: Number of systems included
        train_speeds: List of speeds included
    """

    lane_id: str
    host_stats: List[HostBERStats]
    min_of_mins: Optional[float]
    avg_of_mins: Optional[float]
    max_of_mins: Optional[float]
    min_of_avgs: Optional[float]
    avg_of_avgs: Optional[float]
    max_of_avgs: Optional[float]
    min_of_maxs: Optional[float]
    avg_of_maxs: Optional[float]
    max_of_maxs: Optional[float]
    num_systems: int
    train_speeds: List[int]


@dataclass
class BERPlotPoint:
    """Single BER plot data point.

    Attributes:
        timestamp: Date/time string from test execution
        ber_value: BER value for this lane at this timestamp
    """

    timestamp: str
    ber_value: float


@dataclass
class BERPlot:
    """BER plot data for a single lane over time.

    Attributes:
        lane_id: Full lane identifier (e.g., "system/01:00.0/ETH07/lane4")
        data_points: List of (timestamp, ber_value) tuples ordered by test sequence
        num_systems: Number of systems included (should be 1 for plot)
        train_speeds: List of train speeds included
    """

    lane_id: str
    data_points: List[BERPlotPoint]
    num_systems: int
    train_speeds: List[int]


class LaneSelector:
    """Specifies which serdes lanes to query.

    The LaneSelector parses lane specification strings and generates
    SQL WHERE clauses for filtering database queries.

    Supported formats:
        - "all" -> All lanes on all systems
        - "01:00.0/ETH07" -> Specific port (all lanes)
        - "01:00.0/ETH07/4" -> Specific lane on specific port
        - "01:00.0/*" -> All ports on bus_id
        - "bh-glx-c02u02/01:00.0/ETH07" -> Specific system and port
        - "bh-glx-c02u02/01:00.0/ETH07/4" -> Specific lane on specific system
        - "bh-glx-c02u02/*" -> All ports on system
        - "*/ETH07" -> ETH07 on all systems
        - "*/ETH07/4" -> Lane 4 on ETH07 across all systems

    Attributes:
        spec: Original specification string
        host: Host filter (None = all hosts, "*" = wildcard, specific hostname)
        bus_id: Bus ID filter (None = all, "*" = wildcard, specific bus_id)
        eth_id: Ethernet port filter (None = all, "*" = wildcard, specific eth_id)
        lane_num: Lane number filter (None = all lanes, 0-7 = specific lane)
        normalize_by_ubb: If True, aggregate data by chip position (U1-U8)
    """

    def __init__(
        self,
        host: Optional[str] = None,
        bus_id: Optional[str] = None,
        eth_id: Optional[str] = None,
        lane_num: Optional[int] = None,
        normalize_by_ubb: bool = False,
    ):
        """Initialize lane selector.

        Args:
            host: Host filter pattern
            bus_id: Bus ID filter pattern
            eth_id: Ethernet port filter pattern
            lane_num: Lane number (0-7) or None for all lanes
            normalize_by_ubb: If True, aggregate by chip position instead of bus_id
        """
        self.host = host
        self.bus_id = bus_id
        self.eth_id = eth_id
        self.lane_num = lane_num
        self.normalize_by_ubb = normalize_by_ubb
        self.spec = self._build_spec()

    def _build_spec(self) -> str:
        """Build specification string from patterns."""
        parts = []

        # Handle host if specified
        if self.host and self.host != "*":
            parts.append(self.host)
            # If only host is set (no bus_id, no eth_id), return host/*
            if not self.bus_id and not self.eth_id:
                parts.append("*")
                spec = "/".join(parts)
                if self.lane_num is not None:
                    spec += f"/{self.lane_num}"
                return spec

        # Handle bus_id
        if self.bus_id and self.bus_id != "*":
            parts.append(self.bus_id)
        elif self.bus_id == "*":
            parts.append("*")

        # Handle eth_id
        if self.eth_id and self.eth_id != "*":
            # Special case: */eth_id format (no host, no bus_id)
            if not self.host and not self.bus_id:
                spec = f"*/{self.eth_id}"
                if self.lane_num is not None:
                    spec += f"/{self.lane_num}"
                return spec
            parts.append(self.eth_id)
        elif self.eth_id == "*":
            parts.append("*")
        elif self.bus_id:  # Only add wildcard if bus_id was set
            parts.append("*")

        spec = "/".join(parts) if parts else "all"

        # Add lane number if specified
        if self.lane_num is not None and parts:
            spec += f"/{self.lane_num}"

        return spec

    @classmethod
    def from_spec(cls, spec: str, normalize_by_ubb: bool = False) -> "LaneSelector":
        """Parse lane specification string.

        Args:
            spec: Lane specification string
            normalize_by_ubb: If True, enable UBB normalization mode

        Returns:
            LaneSelector instance

        Raises:
            LaneSelectorError: If spec format is invalid

        Examples:
            "all" -> All lanes on all systems
            "01:00.0/ETH07" -> Specific port
            "01:00.0/ETH07/4" -> Specific lane on specific port
            "01:00.0/*" -> All ports on bus_id
            "bh-glx-c02u02/01:00.0/ETH07" -> Specific system and port
            "bh-glx-c02u02/01:00.0/ETH07/4" -> Specific lane on specific system
            "bh-glx-c02u02/*" -> All ports on system
            "*/ETH07" -> ETH07 on all systems
            "*/ETH07/4" -> Lane 4 on ETH07 across all systems

        UBB Normalization Mode Examples (normalize_by_ubb=True):
            "U1/ETH07" -> Chip position U1, ETH07 (all UBBs)
            "U1/ETH07/4" -> Chip position U1, ETH07, lane 4
            "U1/*" -> All ports on chip position U1
        """
        spec = spec.strip()

        # Validate not empty
        if not spec:
            raise LaneSelectorError("Lane specification cannot be empty", spec=spec)

        # Handle "all" special case
        if spec.lower() == "all":
            return cls(host=None, bus_id=None, eth_id=None, lane_num=None, normalize_by_ubb=normalize_by_ubb)

        # Split by "/" and validate
        parts = spec.split("/")

        # Check for empty parts (e.g., "//", "/foo", "foo/")
        if any(not part for part in parts):
            raise LaneSelectorError(f"Invalid lane specification format: {spec}", spec=spec)

        # Helper function to extract and validate lane number
        def extract_lane_num(part: str) -> Optional[int]:
            """Extract lane number from last part if it's a digit."""
            try:
                lane = int(part)
                if 0 <= lane <= 7:
                    return lane
                else:
                    raise LaneSelectorError(
                        f"Lane number must be 0-7, got {lane}",
                        spec=spec
                    )
            except ValueError:
                return None

        # Check if the last part is a lane number
        # Only extract lane number if we have 3 or 4 parts (not 2)
        # This prevents "01:00.0/7" from being interpreted as lane 7
        lane_num = None
        if len(parts) >= 3:
            potential_lane = extract_lane_num(parts[-1])
            if potential_lane is not None:
                lane_num = potential_lane
                parts = parts[:-1]  # Remove lane number from parts

        if len(parts) == 1:
            # Single part must be a valid bus_id or chip position (not hostname alone)
            part = parts[0]

            # Wildcard-only is invalid
            if part == "*":
                raise LaneSelectorError("Wildcard-only specification is invalid. Use 'all' instead.", spec=spec)

            # In UBB mode, check if it's a chip position spec (U1-U8)
            if normalize_by_ubb and part.startswith("U"):
                from bh_glx_data.system_analysis.ubb_normalization import parse_chip_position_spec
                try:
                    # Validate chip position format
                    parse_chip_position_spec(part)
                    # Store as bus_id for internal use - will be handled in to_sql_filter
                    return cls(host=None, bus_id=part, eth_id=None, lane_num=lane_num, normalize_by_ubb=normalize_by_ubb)
                except ValueError as e:
                    # Not a valid chip position, try as bus_id below
                    pass

            # Try to parse as bus_id
            try:
                normalized_bus_id = normalize_bus_id(part)
                return cls(host=None, bus_id=normalized_bus_id, eth_id=None, lane_num=lane_num, normalize_by_ubb=normalize_by_ubb)
            except ValueError as e:
                # Not a valid bus_id format
                raise LaneSelectorError(
                    f"Invalid lane specification: '{part}'. Single-part specs must be 'all' or a valid bus_id. "
                    f"Use 'host/*' or 'host/bus_id/eth_id' format for hostnames.",
                    spec=spec
                ) from e

        elif len(parts) == 2:
            # Could be bus_id/eth_id, host/bus_id, host/eth_id, or */eth_id
            # In UBB mode: could also be U1/eth_id or U1/*
            first, second = parts

            # Handle */eth_id case
            if first == "*":
                if second == "*":
                    raise LaneSelectorError("Invalid specification: */* is ambiguous. Use 'all' instead.", spec=spec)
                try:
                    normalized_eth_id = normalize_eth_port(second)
                    return cls(host=None, bus_id=None, eth_id=normalized_eth_id, lane_num=lane_num, normalize_by_ubb=normalize_by_ubb)
                except Exception as e:
                    raise LaneSelectorError(f"Invalid eth_id format: {second}", spec=spec) from e

            # In UBB mode, check if first is a chip position (U1-U8)
            if normalize_by_ubb and first.startswith("U"):
                from bh_glx_data.system_analysis.ubb_normalization import parse_chip_position_spec
                try:
                    parse_chip_position_spec(first)
                    # Normalize eth_id if not wildcard
                    if second != "*":
                        try:
                            normalized_eth_id = normalize_eth_port(second)
                        except Exception as e:
                            raise LaneSelectorError(f"Invalid eth_id format: {second}", spec=spec) from e
                    else:
                        normalized_eth_id = None
                    return cls(host=None, bus_id=first, eth_id=normalized_eth_id, lane_num=lane_num, normalize_by_ubb=normalize_by_ubb)
                except ValueError:
                    # Not a valid chip position, continue with normal parsing
                    pass

            # If first contains ":", it's definitely bus_id/eth_id
            if ":" in first:
                try:
                    normalized_bus_id = normalize_bus_id(first)
                except Exception as e:
                    raise LaneSelectorError(f"Invalid bus_id format: {first}", spec=spec) from e

                # Normalize eth_id if not wildcard
                if second != "*":
                    try:
                        normalized_eth_id = normalize_eth_port(second)
                    except Exception as e:
                        raise LaneSelectorError(f"Invalid eth_id format: {second}", spec=spec) from e
                else:
                    normalized_eth_id = None

                return cls(host=None, bus_id=normalized_bus_id, eth_id=normalized_eth_id, lane_num=lane_num, normalize_by_ubb=normalize_by_ubb)

            # If second contains ":", it's host/bus_id
            if ":" in second:
                try:
                    normalized_bus_id = normalize_bus_id(second)
                    return cls(host=first, bus_id=normalized_bus_id, eth_id=None, lane_num=lane_num, normalize_by_ubb=normalize_by_ubb)
                except Exception as e:
                    raise LaneSelectorError(f"Invalid bus_id format: {second}", spec=spec) from e

            # Neither contains ":", could be bus_id/eth_id or host/*
            # If second is a wildcard, first could be bus_id or host
            # If second is a specific eth_id, first must be a valid bus_id
            if second == "*":
                # Could be bus_id/* or host/*
                # Try bus_id first
                try:
                    normalized_bus_id = normalize_bus_id(first)
                    return cls(host=None, bus_id=normalized_bus_id, eth_id=None, lane_num=lane_num, normalize_by_ubb=normalize_by_ubb)
                except ValueError:
                    # Not a valid bus_id, treat as host/*
                    return cls(host=first, bus_id=None, eth_id=None, lane_num=lane_num, normalize_by_ubb=normalize_by_ubb)
            else:
                # second is a specific eth_id, so first must be a valid bus_id
                try:
                    normalized_bus_id = normalize_bus_id(first)
                    normalized_eth_id = normalize_eth_port(second)
                    return cls(host=None, bus_id=normalized_bus_id, eth_id=normalized_eth_id, lane_num=lane_num, normalize_by_ubb=normalize_by_ubb)
                except ValueError as e:
                    raise LaneSelectorError(
                        f"Invalid bus_id format: {first}. For hostname patterns, use 'host/*' format.",
                        spec=spec
                    ) from e
                except Exception as e:
                    raise LaneSelectorError(f"Invalid eth_id format: {second}", spec=spec) from e

        elif len(parts) == 3:
            # host/bus_id/eth_id
            host, bus_id, eth_id = parts

            # Normalize bus_id if not wildcard
            if bus_id != "*":
                try:
                    normalized_bus_id = normalize_bus_id(bus_id)
                except Exception as e:
                    raise LaneSelectorError(f"Invalid bus_id format: {bus_id}", spec=spec) from e
            else:
                normalized_bus_id = None

            # Normalize eth_id if not wildcard
            if eth_id != "*":
                try:
                    normalized_eth_id = normalize_eth_port(eth_id)
                except Exception as e:
                    raise LaneSelectorError(f"Invalid eth_id format: {eth_id}", spec=spec) from e
            else:
                normalized_eth_id = None

            return cls(host=host if host != "*" else None, bus_id=normalized_bus_id, eth_id=normalized_eth_id, lane_num=lane_num, normalize_by_ubb=normalize_by_ubb)

        elif len(parts) == 4:
            # This case is already handled by lane number extraction above
            # Should not reach here
            raise LaneSelectorError(f"Invalid lane specification format: {spec}", spec=spec)

        else:
            raise LaneSelectorError(f"Invalid lane specification format: {spec}", spec=spec)

    def to_sql_filter(self) -> Tuple[str, tuple]:
        """Generate SQL WHERE clause for this selector.

        Note: Lane filtering is NOT included in SQL WHERE clause as it requires
        column-level filtering (selecting specific acc_ber_lane# columns).
        Use get_lane_columns() to determine which columns to query.

        In UBB normalization mode, if a chip position is specified (U1-U8),
        expands to filter by all 4 corresponding bus_ids.

        Returns:
            Tuple of (where_clause, params) for parameterized query

        Example:
            ("bus_id = ? AND eth_id = ?", ("01:00.0", "ETH07"))

        Example (UBB mode with U1):
            ("bus_id IN (?, ?, ?, ?) AND eth_id = ?",
             ("01:00.0", "41:00.0", "c1:00.0", "81:00.0", "ETH07"))
        """
        conditions = []
        params = []

        # Host filter
        if self.host and self.host != "*":
            conditions.append("host = ?")
            params.append(self.host)

        # Bus ID filter
        if self.bus_id and self.bus_id != "*":
            # In UBB mode, check if bus_id is a chip position spec
            if self.normalize_by_ubb and self.bus_id.startswith("U"):
                from bh_glx_data.system_analysis.ubb_normalization import (
                    get_all_bus_ids_for_chip,
                    parse_chip_position_spec,
                )
                try:
                    chip_pos = parse_chip_position_spec(self.bus_id)
                    bus_ids = get_all_bus_ids_for_chip(chip_pos)
                    placeholders = ", ".join(["?" for _ in bus_ids])
                    conditions.append(f"bus_id IN ({placeholders})")
                    params.extend(bus_ids)
                except ValueError:
                    # Not a valid chip position, treat as normal bus_id
                    conditions.append("bus_id = ?")
                    params.append(self.bus_id)
            else:
                conditions.append("bus_id = ?")
                params.append(self.bus_id)

        # Eth ID filter
        if self.eth_id and self.eth_id != "*":
            conditions.append("eth_id = ?")
            params.append(self.eth_id)

        # Note: lane_num filtering happens at column selection level, not WHERE clause

        if conditions:
            where_clause = " AND ".join(conditions)
        else:
            where_clause = "1=1"  # Always true (select all)

        return where_clause, tuple(params)

    def get_lane_columns(self, all_lane_columns: List[str]) -> List[str]:
        """Get list of lane columns to query based on lane_num filter.

        Args:
            all_lane_columns: Full list of lane column names

        Returns:
            Filtered list of lane columns (single column if lane_num specified,
            all columns if lane_num is None)
        """
        if self.lane_num is not None:
            # Return only the specific lane column
            lane_col = f"acc_ber_lane{self.lane_num}"
            return [lane_col] if lane_col in all_lane_columns else []
        else:
            # Return all lane columns
            return all_lane_columns

    def __str__(self) -> str:
        """String representation."""
        return self.spec

    def __repr__(self) -> str:
        """Detailed representation."""
        parts = []
        if self.host:
            parts.append(f"host={self.host}")
        if self.bus_id:
            parts.append(f"bus_id={self.bus_id}")
        if self.eth_id:
            parts.append(f"eth_id={self.eth_id}")
        if self.lane_num is not None:
            parts.append(f"lane_num={self.lane_num}")

        if parts:
            return f"LaneSelector({', '.join(parts)})"
        else:
            return "LaneSelector(all)"


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

    def _aggregate_by_chip_position(
        self, df: pd.DataFrame, lane_col: str
    ) -> Dict[str, pd.Series]:
        """Group DataFrame by chip position instead of bus_id.

        Args:
            df: DataFrame with bus_id, eth_id columns
            lane_col: Lane column name to extract values from

        Returns:
            Dictionary mapping normalized lane_id to series of values
            e.g., {"U1/ETH07/lane0": Series([...]), ...}
        """
        from bh_glx_data.system_analysis.ubb_normalization import normalize_bus_id_to_chip

        # Add chip_position column
        df = df.copy()
        df["chip_position"] = df["bus_id"].apply(normalize_bus_id_to_chip)

        # Group by chip_position and eth_id
        grouped_values = {}
        for (chip_pos, eth_id), group in df.groupby(["chip_position", "eth_id"]):
            lane_num = int(lane_col.replace("acc_ber_lane", ""))
            lane_id = f"{chip_pos}/{eth_id}/lane{lane_num}"
            grouped_values[lane_id] = group[lane_col].dropna()

        return grouped_values

    def query_ber_statistics(
        self,
        lane_selector: LaneSelector,
        train_speeds: Optional[List[int]] = None,
    ) -> BERStatistics:
        """Calculate BER statistics for specified lanes.

        Training failures are always excluded from BER statistics since they
        do not have valid BER data.

        If lane_selector.normalize_by_ubb is True, aggregates data by chip
        position (U1-U8) instead of individual bus_ids.

        Args:
            lane_selector: Specifies which lanes to analyze
            train_speeds: Filter by specific speeds (None = all)

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

            # Always exclude training failures (no BER data)
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
            lane_stats = {}

            for lane_col in self.LANE_COLUMNS:
                lane_num = int(lane_col.replace("acc_ber_lane", ""))

                # Group by chip position or bus_id depending on mode
                if lane_selector.normalize_by_ubb:
                    # UBB normalization mode: group by chip_position
                    grouped_values = self._aggregate_by_chip_position(df, lane_col)
                else:
                    # Normal mode: group by bus_id
                    grouped_values = {}
                    for (bus_id, eth_id), group in df.groupby(["bus_id", "eth_id"]):
                        lane_id = f"{bus_id}/{eth_id}/lane{lane_num}"
                        grouped_values[lane_id] = group[lane_col].dropna()

                # Calculate stats for each grouped lane
                for lane_id, lane_values in grouped_values.items():
                    if not lane_values.empty:
                        # Separate high BER values (>= 0.1) from normal values
                        high_ber_mask = lane_values >= 0.1
                        high_ber_count = high_ber_mask.sum()
                        normal_values = lane_values[~high_ber_mask]

                        if normal_values.empty:
                            # All values are high BER
                            lane_stats[lane_id] = LaneBERStats(
                                lane_id=lane_id,
                                min_ber=None,
                                max_ber=None,
                                avg_ber=None,
                                sample_count=len(lane_values),
                                high_ber_count=int(high_ber_count),
                            )
                        else:
                            lane_stats[lane_id] = LaneBERStats(
                                lane_id=lane_id,
                                min_ber=float(normal_values.min()),
                                max_ber=float(normal_values.max()),
                                avg_ber=float(normal_values.mean()),
                                sample_count=len(lane_values),
                                high_ber_count=int(high_ber_count),
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

        If lane_selector.normalize_by_ubb is True, aggregates counts by chip
        position (U1-U8) instead of individual bus_ids.

        Args:
            lane_selector: Specifies which lanes to analyze
            train_speeds: Filter by specific speeds (None = all)

        Returns:
            ThresholdExceededCounts with per-lane counts

        Raises:
            QueryError: If query execution fails
        """
        try:
            # Build query - get all data (not just threshold exceeded)
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
                logger.warning(
                    f"No data found for lane selector: {lane_selector}"
                )
                return ThresholdExceededCounts(
                    lane_counts={},
                    num_tests=0,
                    num_systems=0,
                    train_speeds=train_speeds or [],
                )

            # Build full lane IDs and count threshold exceeded events
            lane_counts = {}
            for lane_col in self.LANE_COLUMNS:
                lane_num = int(lane_col.replace("acc_ber_lane", ""))

                # Group by chip position or bus_id depending on mode
                if lane_selector.normalize_by_ubb:
                    from bh_glx_data.system_analysis.ubb_normalization import (
                        normalize_bus_id_to_chip,
                    )

                    df_copy = df.copy()
                    df_copy["chip_position"] = df_copy["bus_id"].apply(normalize_bus_id_to_chip)

                    for (chip_pos, eth_id), group in df_copy.groupby(["chip_position", "eth_id"]):
                        lane_id = f"{chip_pos}/{eth_id}/lane{lane_num}"
                        # Count only BER_THRESHOLD_EXCEEDED events, but include all lanes with data
                        lane_data = group[lane_col].dropna()
                        if not lane_data.empty:
                            threshold_exceeded_group = group[group["test_status"] == "BER_THRESHOLD_EXCEEDED"]
                            lane_count = threshold_exceeded_group[lane_col].notna().sum()
                            lane_counts[lane_id] = int(lane_count)
                else:
                    for (bus_id, eth_id), group in df.groupby(["bus_id", "eth_id"]):
                        lane_id = f"{bus_id}/{eth_id}/lane{lane_num}"
                        # Count only BER_THRESHOLD_EXCEEDED events, but include all lanes with data
                        lane_data = group[lane_col].dropna()
                        if not lane_data.empty:
                            threshold_exceeded_group = group[group["test_status"] == "BER_THRESHOLD_EXCEEDED"]
                            lane_count = threshold_exceeded_group[lane_col].notna().sum()
                            lane_counts[lane_id] = int(lane_count)

            # Metadata - count only threshold exceeded tests for backward compatibility
            threshold_exceeded_df = df[df["test_status"] == "BER_THRESHOLD_EXCEEDED"]
            num_tests = len(threshold_exceeded_df)
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

        If lane_selector.normalize_by_ubb is True, aggregates counts by chip
        position (U1-U8) instead of individual bus_ids.

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

            # Build full lane IDs and count
            lane_counts = {}
            for lane_col in self.LANE_COLUMNS:
                lane_num = int(lane_col.replace("acc_ber_lane", ""))

                # Group by chip position or bus_id depending on mode
                if lane_selector.normalize_by_ubb:
                    from bh_glx_data.system_analysis.ubb_normalization import (
                        normalize_bus_id_to_chip,
                    )

                    df_copy = df.copy()
                    df_copy["chip_position"] = df_copy["bus_id"].apply(normalize_bus_id_to_chip)

                    for (chip_pos, eth_id), group in df_copy.groupby(["chip_position", "eth_id"]):
                        lane_id = f"{chip_pos}/{eth_id}/lane{lane_num}"
                        # Count violations and include all lanes with data (even if count is 0)
                        lane_data = group[lane_col].dropna()
                        if not lane_data.empty:
                            lane_count = (lane_data > threshold).sum()
                            lane_counts[lane_id] = int(lane_count)
                else:
                    for (bus_id, eth_id), group in df.groupby(["bus_id", "eth_id"]):
                        lane_id = f"{bus_id}/{eth_id}/lane{lane_num}"
                        # Count violations and include all lanes with data (even if count is 0)
                        lane_data = group[lane_col].dropna()
                        if not lane_data.empty:
                            lane_count = (lane_data > threshold).sum()
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

        If lane_selector.normalize_by_ubb is True, aggregates counts by chip
        position (U1-U8) instead of individual bus_ids.

        Args:
            lane_selector: Specifies which lanes to analyze
            train_speeds: Filter by specific speeds (None = all)

        Returns:
            TrainingFailureCounts with per-lane counts

        Raises:
            QueryError: If query execution fails
        """
        try:
            # Build query - get all data
            where_clause, params = lane_selector.to_sql_filter()

            # Add speed filter
            if train_speeds:
                speed_placeholders = ", ".join(["?" for _ in train_speeds])
                where_clause += f" AND train_speed IN ({speed_placeholders})"
                params = params + tuple(train_speeds)

            query = f"SELECT * FROM prbs_tests WHERE {where_clause}"

            # Execute query
            df = self.db.execute_query(query, params)

            if df.empty:
                logger.warning(f"No data found for lane selector: {lane_selector}")
                return TrainingFailureCounts(
                    lane_counts={},
                    num_tests=0,
                    num_systems=0,
                    train_speeds=train_speeds or [],
                )

            # Build full lane IDs and count training failures
            lane_counts = {}
            for lane_col in self.LANE_COLUMNS:
                lane_num = int(lane_col.replace("acc_ber_lane", ""))

                # Group by chip position or bus_id depending on mode
                if lane_selector.normalize_by_ubb:
                    from bh_glx_data.system_analysis.ubb_normalization import (
                        normalize_bus_id_to_chip,
                    )

                    df_copy = df.copy()
                    df_copy["chip_position"] = df_copy["bus_id"].apply(normalize_bus_id_to_chip)

                    for (chip_pos, eth_id), group in df_copy.groupby(["chip_position", "eth_id"]):
                        lane_id = f"{chip_pos}/{eth_id}/lane{lane_num}"
                        # Count only TRAINING_FAIL events for this port, but include all ports with data
                        if len(group) > 0:
                            training_fail_group = group[group["test_status"] == "TRAINING_FAIL"]
                            lane_count = len(training_fail_group)
                            lane_counts[lane_id] = int(lane_count)
                else:
                    for (bus_id, eth_id), group in df.groupby(["bus_id", "eth_id"]):
                        lane_id = f"{bus_id}/{eth_id}/lane{lane_num}"
                        # Count only TRAINING_FAIL events for this port, but include all ports with data
                        if len(group) > 0:
                            training_fail_group = group[group["test_status"] == "TRAINING_FAIL"]
                            lane_count = len(training_fail_group)
                            lane_counts[lane_id] = int(lane_count)

            # Metadata - count only training failures for backward compatibility
            training_fail_df = df[df["test_status"] == "TRAINING_FAIL"]
            num_tests = len(training_fail_df)
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

    def query_ber_histogram(
        self,
        lane_selector: LaneSelector,
        train_speeds: Optional[List[int]] = None,
    ) -> Union[BERHistogram, List[BERHistogram]]:
        """Generate BER histogram for lane(s).

        Args:
            lane_selector: Lane specification (supports single lane or multiple lanes)
            train_speeds: Filter by speeds (None = all)

        Returns:
            Single BERHistogram if single lane specified,
            List[BERHistogram] if multiple lanes (e.g., all 8 lanes on a port)

        Raises:
            QueryError: If query fails
        """
        try:
            # Build query
            where_clause, params = lane_selector.to_sql_filter()

            # Add speed filter
            if train_speeds:
                speed_placeholders = ", ".join(["?" for _ in train_speeds])
                where_clause += f" AND train_speed IN ({speed_placeholders})"
                params = params + tuple(train_speeds)

            # Always exclude training failures (no BER data)
            where_clause += " AND test_status != 'TRAINING_FAIL'"

            query = f"SELECT * FROM prbs_tests WHERE {where_clause}"

            # Execute query
            df = self.db.execute_query(query, params)

            if df.empty:
                logger.warning(f"No data found for lane selector: {lane_selector}")
                # Return empty histogram(s)
                lane_columns = lane_selector.get_lane_columns(self.LANE_COLUMNS)
                if lane_selector.lane_num is not None:
                    # Single lane requested
                    return BERHistogram(
                        lane_id=f"{lane_selector.spec}",
                        bins=[],
                        num_tests=0,
                        num_systems=0,
                        train_speeds=train_speeds or [],
                    )
                else:
                    # Multiple lanes requested
                    return []

            # Define histogram bins (logarithmic scale)
            bins = [
                ("< 1e-12", 0, 1e-12),
                ("1e-12-11", 1e-12, 1e-11),
                ("1e-11-10", 1e-11, 1e-10),
                ("1e-10-9", 1e-10, 1e-9),
                ("1e-9-8", 1e-9, 1e-8),
                ("1e-8-7", 1e-8, 1e-7),
                ("1e-7-6", 1e-7, 1e-6),
                ("1e-6-5", 1e-6, 1e-5),
                ("1e-5-4", 1e-5, 1e-4),
                (">= 1e-4", 1e-4, float("inf")),
            ]

            # Get lane columns to process
            lane_columns = lane_selector.get_lane_columns(self.LANE_COLUMNS)

            # Metadata
            num_systems = df["host"].nunique()
            speeds = sorted(df["train_speed"].unique().tolist())

            # Build histograms for each lane
            histograms = []

            for lane_col in lane_columns:
                lane_num = int(lane_col.replace("acc_ber_lane", ""))

                # Group by chip position or bus_id depending on mode
                if lane_selector.normalize_by_ubb:
                    from bh_glx_data.system_analysis.ubb_normalization import (
                        normalize_bus_id_to_chip,
                    )

                    df_copy = df.copy()
                    df_copy["chip_position"] = df_copy["bus_id"].apply(normalize_bus_id_to_chip)

                    for (chip_pos, eth_id), group in df_copy.groupby(["chip_position", "eth_id"]):
                        lane_id = f"{chip_pos}/{eth_id}/lane{lane_num}"

                        # Get BER values for this lane
                        lane_values = group[lane_col].dropna()

                        if lane_values.empty:
                            continue

                        # Calculate histogram
                        bin_counts = []
                        for label, low, high in bins:
                            if high == float("inf"):
                                count = (lane_values >= low).sum()
                            else:
                                count = ((lane_values >= low) & (lane_values < high)).sum()
                            bin_counts.append((label, int(count)))

                        num_tests = len(lane_values)

                        histograms.append(
                            BERHistogram(
                                lane_id=lane_id,
                                bins=bin_counts,
                                num_tests=num_tests,
                                num_systems=num_systems,
                                train_speeds=speeds,
                            )
                        )
                else:
                    # Process each unique bus_id/eth_id combination
                    for (bus_id, eth_id), group in df.groupby(["bus_id", "eth_id"]):
                        lane_id = f"{bus_id}/{eth_id}/lane{lane_num}"

                        # Get BER values for this lane
                        lane_values = group[lane_col].dropna()

                        if lane_values.empty:
                            continue

                        # Calculate histogram
                        bin_counts = []
                        for label, low, high in bins:
                            if high == float("inf"):
                                count = (lane_values >= low).sum()
                            else:
                                count = ((lane_values >= low) & (lane_values < high)).sum()
                            bin_counts.append((label, int(count)))

                        num_tests = len(lane_values)

                        histograms.append(
                            BERHistogram(
                                lane_id=lane_id,
                                bins=bin_counts,
                                num_tests=num_tests,
                                num_systems=num_systems,
                                train_speeds=speeds,
                            )
                        )

            # Return single histogram or list based on lane_num specification
            if lane_selector.lane_num is not None and len(histograms) == 1:
                return histograms[0]
            else:
                return histograms

        except Exception as e:
            raise QueryError(
                f"Failed to query BER histogram: {e}", lane_spec=str(lane_selector)
            ) from e

    def query_aggregated_host_stats(
        self,
        lane_selector: LaneSelector,
        train_speeds: Optional[List[int]] = None,
    ) -> Union[AggregatedHostStats, List[AggregatedHostStats]]:
        """Calculate aggregated host statistics.

        First computes per-host BER statistics (min/avg/max), then
        computes statistics of those statistics across all hosts.

        Args:
            lane_selector: Lane specification
            train_speeds: Filter by speeds (None = all)

        Returns:
            Single AggregatedHostStats if single lane specified,
            List[AggregatedHostStats] if multiple lanes

        Raises:
            QueryError: If query fails
        """
        try:
            # Build query
            where_clause, params = lane_selector.to_sql_filter()

            # Add speed filter
            if train_speeds:
                speed_placeholders = ", ".join(["?" for _ in train_speeds])
                where_clause += f" AND train_speed IN ({speed_placeholders})"
                params = params + tuple(train_speeds)

            # Always exclude training failures (no BER data)
            where_clause += " AND test_status != 'TRAINING_FAIL'"

            query = f"SELECT * FROM prbs_tests WHERE {where_clause}"

            # Execute query
            df = self.db.execute_query(query, params)

            if df.empty:
                logger.warning(f"No data found for lane selector: {lane_selector}")
                # Return empty result(s)
                lane_columns = lane_selector.get_lane_columns(self.LANE_COLUMNS)
                if lane_selector.lane_num is not None:
                    return AggregatedHostStats(
                        lane_id=f"{lane_selector.spec}",
                        host_stats=[],
                        min_of_mins=None,
                        avg_of_mins=None,
                        max_of_mins=None,
                        min_of_avgs=None,
                        avg_of_avgs=None,
                        max_of_avgs=None,
                        min_of_maxs=None,
                        avg_of_maxs=None,
                        max_of_maxs=None,
                        num_systems=0,
                        train_speeds=train_speeds or [],
                    )
                else:
                    return []

            # Get lane columns to process
            lane_columns = lane_selector.get_lane_columns(self.LANE_COLUMNS)

            # Metadata
            speeds = sorted(df["train_speed"].unique().tolist())

            # Build aggregated stats for each lane
            aggregated_stats_list = []

            for lane_col in lane_columns:
                lane_num = int(lane_col.replace("acc_ber_lane", ""))

                # Group by chip position or bus_id depending on mode
                if lane_selector.normalize_by_ubb:
                    from bh_glx_data.system_analysis.ubb_normalization import (
                        normalize_bus_id_to_chip,
                    )

                    df_copy = df.copy()
                    df_copy["chip_position"] = df_copy["bus_id"].apply(normalize_bus_id_to_chip)

                    for (chip_pos, eth_id), group in df_copy.groupby(["chip_position", "eth_id"]):
                        lane_id = f"{chip_pos}/{eth_id}/lane{lane_num}"

                        # Calculate per-host statistics
                        host_stats_list = []
                        for host, host_group in group.groupby("host"):
                            # Get BER values for this lane and host
                            lane_values = host_group[lane_col].dropna()

                            if not lane_values.empty:
                                # Separate high BER values (>= 0.1) from normal values
                                high_ber_mask = lane_values >= 0.1
                                normal_values = lane_values[~high_ber_mask]

                                if normal_values.empty:
                                    # All values are high BER
                                    host_stats_list.append(
                                        HostBERStats(
                                            host=host,
                                            min_ber=None,
                                            avg_ber=None,
                                            max_ber=None,
                                            sample_count=len(lane_values),
                                        )
                                    )
                                else:
                                    host_stats_list.append(
                                        HostBERStats(
                                            host=host,
                                            min_ber=float(normal_values.min()),
                                            avg_ber=float(normal_values.mean()),
                                            max_ber=float(normal_values.max()),
                                            sample_count=len(lane_values),
                                        )
                                    )

                        # Calculate statistics of statistics
                        if host_stats_list:
                            # Extract valid min/avg/max values (excluding None)
                            mins = [h.min_ber for h in host_stats_list if h.min_ber is not None]
                            avgs = [h.avg_ber for h in host_stats_list if h.avg_ber is not None]
                            maxs = [h.max_ber for h in host_stats_list if h.max_ber is not None]

                            # Calculate aggregated statistics
                            min_of_mins = float(min(mins)) if mins else None
                            avg_of_mins = float(sum(mins) / len(mins)) if mins else None
                            max_of_mins = float(max(mins)) if mins else None

                            min_of_avgs = float(min(avgs)) if avgs else None
                            avg_of_avgs = float(sum(avgs) / len(avgs)) if avgs else None
                            max_of_avgs = float(max(avgs)) if avgs else None

                            min_of_maxs = float(min(maxs)) if maxs else None
                            avg_of_maxs = float(sum(maxs) / len(maxs)) if maxs else None
                            max_of_maxs = float(max(maxs)) if maxs else None

                            num_systems = len(host_stats_list)
                        else:
                            min_of_mins = avg_of_mins = max_of_mins = None
                            min_of_avgs = avg_of_avgs = max_of_avgs = None
                            min_of_maxs = avg_of_maxs = max_of_maxs = None
                            num_systems = 0

                        aggregated_stats_list.append(
                            AggregatedHostStats(
                                lane_id=lane_id,
                                host_stats=host_stats_list,
                                min_of_mins=min_of_mins,
                                avg_of_mins=avg_of_mins,
                                max_of_mins=max_of_mins,
                                min_of_avgs=min_of_avgs,
                                avg_of_avgs=avg_of_avgs,
                                max_of_avgs=max_of_avgs,
                                min_of_maxs=min_of_maxs,
                                avg_of_maxs=avg_of_maxs,
                                max_of_maxs=max_of_maxs,
                                num_systems=num_systems,
                                train_speeds=speeds,
                            )
                        )
                else:
                    # Normal mode: Process each unique bus_id/eth_id combination
                    for (bus_id, eth_id), group in df.groupby(["bus_id", "eth_id"]):
                        lane_id = f"{bus_id}/{eth_id}/lane{lane_num}"

                        # Calculate per-host statistics
                        host_stats_list = []
                        for host, host_group in group.groupby("host"):
                            # Get BER values for this lane and host
                            lane_values = host_group[lane_col].dropna()

                            if not lane_values.empty:
                                # Separate high BER values (>= 0.1) from normal values
                                high_ber_mask = lane_values >= 0.1
                                normal_values = lane_values[~high_ber_mask]

                                if normal_values.empty:
                                    # All values are high BER
                                    host_stats_list.append(
                                        HostBERStats(
                                            host=host,
                                            min_ber=None,
                                            avg_ber=None,
                                            max_ber=None,
                                            sample_count=len(lane_values),
                                        )
                                    )
                                else:
                                    host_stats_list.append(
                                        HostBERStats(
                                            host=host,
                                            min_ber=float(normal_values.min()),
                                            avg_ber=float(normal_values.mean()),
                                            max_ber=float(normal_values.max()),
                                            sample_count=len(lane_values),
                                        )
                                    )

                    # Calculate statistics of statistics
                    if host_stats_list:
                        # Extract valid min/avg/max values (excluding None)
                        mins = [h.min_ber for h in host_stats_list if h.min_ber is not None]
                        avgs = [h.avg_ber for h in host_stats_list if h.avg_ber is not None]
                        maxs = [h.max_ber for h in host_stats_list if h.max_ber is not None]

                        # Calculate aggregated statistics
                        min_of_mins = float(min(mins)) if mins else None
                        avg_of_mins = float(sum(mins) / len(mins)) if mins else None
                        max_of_mins = float(max(mins)) if mins else None

                        min_of_avgs = float(min(avgs)) if avgs else None
                        avg_of_avgs = float(sum(avgs) / len(avgs)) if avgs else None
                        max_of_avgs = float(max(avgs)) if avgs else None

                        min_of_maxs = float(min(maxs)) if maxs else None
                        avg_of_maxs = float(sum(maxs) / len(maxs)) if maxs else None
                        max_of_maxs = float(max(maxs)) if maxs else None

                        num_systems = len(host_stats_list)
                    else:
                        min_of_mins = avg_of_mins = max_of_mins = None
                        min_of_avgs = avg_of_avgs = max_of_avgs = None
                        min_of_maxs = avg_of_maxs = max_of_maxs = None
                        num_systems = 0

                    aggregated_stats_list.append(
                        AggregatedHostStats(
                            lane_id=lane_id,
                            host_stats=host_stats_list,
                            min_of_mins=min_of_mins,
                            avg_of_mins=avg_of_mins,
                            max_of_mins=max_of_mins,
                            min_of_avgs=min_of_avgs,
                            avg_of_avgs=avg_of_avgs,
                            max_of_avgs=max_of_avgs,
                            min_of_maxs=min_of_maxs,
                            avg_of_maxs=avg_of_maxs,
                            max_of_maxs=max_of_maxs,
                            num_systems=num_systems,
                            train_speeds=speeds,
                        )
                    )

            # Return single result or list based on lane_num specification
            if lane_selector.lane_num is not None and len(aggregated_stats_list) == 1:
                return aggregated_stats_list[0]
            else:
                return aggregated_stats_list

        except Exception as e:
            raise QueryError(
                f"Failed to query aggregated host stats: {e}", lane_spec=str(lane_selector)
            ) from e

    def query_ber_plot(
        self,
        lane_selector: LaneSelector,
        train_speeds: Optional[List[int]] = None,
    ) -> Union[BERPlot, List[BERPlot]]:
        """Query BER values for lane(s) over time.

        Data points are ordered by the 'date' field to show chronological progression.
        The specification requires:
        - System name, bus_id, and eth_id must be specified (no wildcards)
        - Lane number is optional (if not specified, plots for all 8 lanes are returned)

        Plotting BER over time only makes sense for a single system, so the lane
        specification must include a specific system name.

        Args:
            lane_selector: Lane specification (must include system/bus_id/eth_id)
            train_speeds: Filter by speeds (None = all)

        Returns:
            Single BERPlot if single lane specified,
            List[BERPlot] if multiple lanes (all 8 lanes on a port)

        Raises:
            QueryError: If query fails
            LaneSelectorError: If lane selector doesn't include system name or uses wildcards
        """
        try:
            # Validate that we have specific system name (not wildcard, not missing)
            if not lane_selector.host or lane_selector.host == "*":
                raise LaneSelectorError(
                    "BER plot requires specific system name (e.g., 'bh-glx-c02u02/01:00.0/ETH07'). "
                    "Plotting BER over time only makes sense for a single system.",
                    spec=str(lane_selector)
                )

            # Validate that we have specific bus_id and eth_id (not wildcards)
            if not lane_selector.bus_id or lane_selector.bus_id == "*":
                raise LaneSelectorError(
                    "BER plot requires specific bus_id (e.g., 'bh-glx-c02u02/01:00.0/ETH07')",
                    spec=str(lane_selector)
                )
            if not lane_selector.eth_id or lane_selector.eth_id == "*":
                raise LaneSelectorError(
                    "BER plot requires specific eth_id (e.g., 'bh-glx-c02u02/01:00.0/ETH07')",
                    spec=str(lane_selector)
                )

            # Build query
            where_clause, params = lane_selector.to_sql_filter()

            # Add speed filter
            if train_speeds:
                speed_placeholders = ", ".join(["?" for _ in train_speeds])
                where_clause += f" AND train_speed IN ({speed_placeholders})"
                params = params + tuple(train_speeds)

            # Always exclude training failures (no BER data)
            where_clause += " AND test_status != 'TRAINING_FAIL'"

            # Order by date to show chronological progression
            query = f"SELECT * FROM prbs_tests WHERE {where_clause} ORDER BY date ASC"

            # Execute query
            df = self.db.execute_query(query, params)

            if df.empty:
                logger.warning(f"No data found for lane selector: {lane_selector}")
                # Return empty plot(s)
                lane_columns = lane_selector.get_lane_columns(self.LANE_COLUMNS)
                if lane_selector.lane_num is not None:
                    # Single lane requested
                    return BERPlot(
                        lane_id=f"{lane_selector.spec}",
                        data_points=[],
                        num_systems=0,
                        train_speeds=train_speeds or [],
                    )
                else:
                    # Multiple lanes requested
                    return []

            # Get lane columns to process
            lane_columns = lane_selector.get_lane_columns(self.LANE_COLUMNS)

            # Metadata
            num_systems = df["host"].nunique()
            speeds = sorted(df["train_speed"].unique().tolist())

            # Build plots for each lane
            plots = []

            for lane_col in lane_columns:
                lane_num = int(lane_col.replace("acc_ber_lane", ""))

                # Process each unique bus_id/eth_id combination
                for (bus_id, eth_id), group in df.groupby(["bus_id", "eth_id"]):
                    # Build lane ID - include host if specified
                    if lane_selector.host and lane_selector.host != "*":
                        lane_id = f"{lane_selector.host}/{bus_id}/{eth_id}/lane{lane_num}"
                    else:
                        # If host was not specified but there's only one host, include it
                        if num_systems == 1:
                            host = group["host"].iloc[0]
                            lane_id = f"{host}/{bus_id}/{eth_id}/lane{lane_num}"
                        else:
                            lane_id = f"{bus_id}/{eth_id}/lane{lane_num}"

                    # Extract data points (timestamp, ber_value)
                    data_points = []
                    for _, row in group.iterrows():
                        ber_value = row[lane_col]
                        if pd.notna(ber_value):
                            data_points.append(
                                BERPlotPoint(
                                    timestamp=row["date"],
                                    ber_value=float(ber_value),
                                )
                            )

                    if data_points:
                        plots.append(
                            BERPlot(
                                lane_id=lane_id,
                                data_points=data_points,
                                num_systems=num_systems,
                                train_speeds=speeds,
                            )
                        )

            # Return single plot or list based on lane_num specification
            if lane_selector.lane_num is not None and len(plots) == 1:
                return plots[0]
            else:
                return plots

        except LaneSelectorError:
            # Re-raise lane selector errors
            raise
        except Exception as e:
            raise QueryError(
                f"Failed to query BER plot: {e}", lane_spec=str(lane_selector)
            ) from e
