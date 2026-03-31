# bh-analyze-systems v0.7.0 - UBB Normalization Feature Architecture

## 1. Requirements Summary

### Background

Each BH Galaxy system consists of 32 chips (bus_ids) spread across 4 UBBs (8 chips each). The 4 UBBs are identical boards with the same PCB trace paths for high-speed Serdes lanes. Bus IDs follow the pattern:

| UBB | Bus ID Prefix | Example (Chip 1) |
|-----|---------------|------------------|
| UBB1 | `0x:00.0` | `01:00.0` |
| UBB2 | `4x:00.0` | `41:00.0` |
| UBB3 | `cx:00.0` | `c1:00.0` |
| UBB4 | `8x:00.0` | `81:00.0` |

This means bus_ids `01:00.0`, `41:00.0`, `c1:00.0`, and `81:00.0` all represent chip position U1 on their respective UBBs, with identical PCB trace paths.

### Current Behavior (MUST Preserve)

The current implementation analyzes data separately for each `bus_id/eth_id` combination across all systems. A query for `01:00.0/ETH07` returns data only for that specific bus_id on all systems.

### New Feature: UBB-Normalized View

Add an **optional mode** that normalizes bus_ids by chip position (U1-U8), treating all 4 UBBs as equivalent. When enabled:

- Data from `01:00.0`, `41:00.0`, `c1:00.0`, `81:00.0` are aggregated as "U1"
- This effectively 4x's the sample size per chip position
- Enables analysis of patterns related to chip position on the UBB (e.g., PCB trace issues)

### Use Cases

1. **PCB Trace Analysis**: Investigate whether a specific chip position (e.g., U1) shows consistent issues across all UBBs
2. **Manufacturing Quality**: Compare BER patterns across chip positions to detect systematic manufacturing issues
3. **Increased Statistical Power**: 4x sample size for each chip position analysis

---

## 2. Architectural Overview

### Design Philosophy

The feature is implemented as a **query-time transformation** rather than database schema changes:

1. **No Database Changes**: The raw bus_id data remains unchanged in the database
2. **Transparent Aggregation**: UBB normalization happens at the query/result aggregation layer
3. **Clean Separation**: Normalization logic is isolated in dedicated functions
4. **Backward Compatibility**: All existing functionality continues unchanged

### High-Level Data Flow

```
                     ┌─────────────────────────┐
                     │       CLI / Shell       │
                     │  --by-ubb-position flag │
                     └───────────┬─────────────┘
                                 │
                                 v
                     ┌─────────────────────────┐
                     │      Query Engine       │
                     │  normalize_by_ubb=True  │
                     └───────────┬─────────────┘
                                 │
                     ┌───────────┴───────────┐
                     │                       │
                     v                       v
            ┌───────────────┐      ┌───────────────┐
            │  Normal Mode  │      │ UBB Norm Mode │
            │ (bus_id key)  │      │(chip_pos key) │
            └───────┬───────┘      └───────┬───────┘
                    │                      │
                    │                      v
                    │            ┌───────────────────┐
                    │            │ Bus ID Normalizer │
                    │            │  (new module)     │
                    │            └───────┬───────────┘
                    │                    │
                    v                    v
            ┌─────────────────────────────────────┐
            │          Statistics Module          │
            │    (shared aggregation logic)       │
            └───────────────────────────────────┘
                              │
                              v
            ┌─────────────────────────────────────┐
            │     Visualization / Export          │
            │  (displays U1-U8 instead of bus_id) │
            └─────────────────────────────────────┘
```

---

## 3. Component Design

### 3.1 New Module: `ubb_normalization.py`

**Location:** `src/bh_glx_data/system_analysis/ubb_normalization.py`

**Responsibility:** Bus ID to chip position normalization logic

```python
"""UBB normalization utilities for chip position analysis.

This module provides functions to normalize bus_ids to chip positions (U1-U8),
enabling analysis that aggregates data across all 4 UBBs for each chip position.
"""

from typing import Dict, Optional, Tuple

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
    """
    # Chip number is the second hex digit
    chip_hex = bus_id[1]
    return int(chip_hex, 16)


def get_ubb_number(bus_id: str) -> int:
    """Extract UBB number (1-4) from bus_id.

    Args:
        bus_id: Normalized bus ID (e.g., "01:00.0", "c5:00.0")

    Returns:
        UBB number (1-4)

    Raises:
        ValueError: If bus_id format is invalid
    """
    prefix = bus_id[0].lower()
    ubb = UBB_PREFIX_MAP.get(prefix)
    if ubb is None:
        raise ValueError(f"Unknown UBB prefix: {prefix}")
    return ubb


def normalize_bus_id_to_chip(bus_id: str) -> str:
    """Normalize bus_id to chip position identifier.

    Converts bus_id (e.g., "01:00.0", "41:00.0", "c1:00.0", "81:00.0")
    to chip position identifier "U1".

    Args:
        bus_id: Normalized bus ID

    Returns:
        Chip position identifier (e.g., "U1", "U5")
    """
    chip_pos = get_chip_position(bus_id)
    return f"U{chip_pos}"


def get_all_bus_ids_for_chip(chip_position: int) -> Tuple[str, str, str, str]:
    """Get all 4 bus_ids that correspond to a chip position.

    Args:
        chip_position: Chip position (1-8)

    Returns:
        Tuple of (ubb1_bus_id, ubb2_bus_id, ubb3_bus_id, ubb4_bus_id)
    """
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
    """
    parts = lane_id.split("/")
    if len(parts) >= 2:
        bus_id = parts[0]
        chip_pos = normalize_bus_id_to_chip(bus_id)
        parts[0] = chip_pos
    return "/".join(parts)


def group_lane_ids_by_chip_position(lane_ids: list) -> Dict[str, list]:
    """Group lane_ids by their chip position.

    Args:
        lane_ids: List of lane identifiers (e.g., ["01:00.0/ETH07/lane0", ...])

    Returns:
        Dictionary mapping normalized lane_id to list of original lane_ids
        e.g., {"U1/ETH07/lane0": ["01:00.0/ETH07/lane0", "41:00.0/ETH07/lane0", ...]}
    """
    grouped = {}
    for lane_id in lane_ids:
        normalized = normalize_lane_id(lane_id)
        if normalized not in grouped:
            grouped[normalized] = []
        grouped[normalized].append(lane_id)
    return grouped
```

### 3.2 LaneSelector Modifications

**Location:** `src/bh_glx_data/system_analysis/query_engine.py`

The `LaneSelector` class needs a new attribute to track UBB normalization mode.

```python
class LaneSelector:
    """Specifies which serdes lanes to query.

    ...existing docstring...

    Attributes:
        ...existing attributes...
        normalize_by_ubb: If True, aggregate data by chip position (U1-U8)
    """

    def __init__(
        self,
        host: Optional[str] = None,
        bus_id: Optional[str] = None,
        eth_id: Optional[str] = None,
        lane_num: Optional[int] = None,
        normalize_by_ubb: bool = False,  # NEW
    ):
        """Initialize lane selector.

        Args:
            ...existing args...
            normalize_by_ubb: If True, aggregate by chip position instead of bus_id
        """
        self.host = host
        self.bus_id = bus_id
        self.eth_id = eth_id
        self.lane_num = lane_num
        self.normalize_by_ubb = normalize_by_ubb  # NEW
        self.spec = self._build_spec()

    @classmethod
    def from_spec(cls, spec: str, normalize_by_ubb: bool = False) -> "LaneSelector":
        """Parse lane specification string.

        Args:
            spec: Lane specification string
            normalize_by_ubb: If True, enable UBB normalization mode

        Returns:
            LaneSelector instance
        """
        # ...existing parsing logic...
        # Pass normalize_by_ubb to constructor
        return cls(
            host=host,
            bus_id=normalized_bus_id,
            eth_id=normalized_eth_id,
            lane_num=lane_num,
            normalize_by_ubb=normalize_by_ubb,  # NEW
        )
```

### 3.3 QueryEngine Modifications

**Location:** `src/bh_glx_data/system_analysis/query_engine.py`

Each query method needs to support UBB normalization:

```python
class QueryEngine:
    """High-level query interface for PRBS test data."""

    def query_ber_statistics(
        self,
        lane_selector: LaneSelector,
        train_speeds: Optional[List[int]] = None,
    ) -> BERStatistics:
        """Calculate BER statistics for specified lanes.

        If lane_selector.normalize_by_ubb is True, aggregates data by chip
        position (U1-U8) instead of individual bus_ids.

        ...existing docstring...
        """
        try:
            # Build and execute query (unchanged)
            where_clause, params = lane_selector.to_sql_filter()
            # ... execute query to get df ...

            # NEW: Apply UBB normalization if requested
            if lane_selector.normalize_by_ubb:
                return self._aggregate_ber_stats_by_chip_position(df, lane_selector, train_speeds)

            # Existing logic for non-normalized mode
            # ... existing implementation ...

        except Exception as e:
            raise QueryError(...) from e

    def _aggregate_ber_stats_by_chip_position(
        self,
        df: pd.DataFrame,
        lane_selector: LaneSelector,
        train_speeds: Optional[List[int]],
    ) -> BERStatistics:
        """Aggregate BER statistics by chip position.

        Groups data from all 4 UBBs for each chip position (U1-U8),
        combining samples from equivalent bus_ids.

        Args:
            df: DataFrame with query results
            lane_selector: Lane selector with normalize_by_ubb=True
            train_speeds: Speed filter used

        Returns:
            BERStatistics with chip position identifiers (U1-U8)
        """
        from bh_glx_data.system_analysis.ubb_normalization import (
            normalize_bus_id_to_chip,
        )

        # Add chip_position column
        df = df.copy()
        df["chip_position"] = df["bus_id"].apply(normalize_bus_id_to_chip)

        lane_stats = {}

        for lane_col in self.LANE_COLUMNS:
            lane_num = int(lane_col.replace("acc_ber_lane", ""))

            # Group by chip_position and eth_id instead of bus_id and eth_id
            for (chip_pos, eth_id), group in df.groupby(["chip_position", "eth_id"]):
                lane_id = f"{chip_pos}/{eth_id}/lane{lane_num}"

                lane_values = group[lane_col].dropna()

                if not lane_values.empty:
                    high_ber_mask = lane_values >= 0.1
                    high_ber_count = high_ber_mask.sum()
                    normal_values = lane_values[~high_ber_mask]

                    if normal_values.empty:
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
```

**Similar modifications for other query methods:**
- `query_ber_threshold_exceeded()`
- `query_custom_ber_threshold()`
- `query_training_failures()`
- `query_ber_histogram()`
- `query_aggregated_host_stats()`

Each method follows the same pattern:
1. Execute query normally
2. If `normalize_by_ubb`, call dedicated aggregation helper
3. Helper groups by chip_position instead of bus_id

### 3.4 Result Dataclasses (No Changes Required)

The existing result dataclasses (`BERStatistics`, `LaneBERStats`, `ThresholdExceededCounts`, etc.) work unchanged. The only difference is that `lane_id` values will use chip position identifiers (e.g., "U1/ETH07/lane0") instead of bus_ids.

---

## 4. Data Models

### Lane ID Format Comparison

| Mode | Lane ID Format | Example |
|------|----------------|---------|
| Normal (default) | `{bus_id}/{eth_id}/lane{N}` | `01:00.0/ETH07/lane4` |
| UBB Normalized | `{chip_pos}/{eth_id}/lane{N}` | `U1/ETH07/lane4` |

### Sample Size Comparison

For a fleet of 10 systems with 4 UBBs each:

| Mode | Samples per Lane Entry |
|------|----------------------|
| Normal | 10 (one per system for specific bus_id) |
| UBB Normalized | 40 (all 4 UBBs across all systems) |

---

## 5. API Design

### CLI Interface

**New global flag for all analysis commands:**

```bash
# Existing commands (unchanged)
bh-analyze-systems stats all --speed 200
bh-analyze-systems stats 01:00.0/ETH07 --format heatmap

# New: UBB normalization mode
bh-analyze-systems stats all --speed 200 --by-ubb-position
bh-analyze-systems stats U1/ETH07 --format heatmap --by-ubb-position
bh-analyze-systems threshold all --by-ubb-position
bh-analyze-systems custom all 1e-10 --by-ubb-position
bh-analyze-systems training all --by-ubb-position
bh-analyze-systems histogram U1/ETH07/4 --by-ubb-position
bh-analyze-systems advanced-stats U1/ETH07 --by-ubb-position
```

**Flag semantics:**
- `--by-ubb-position` (or `-u` for short): Enable UBB-normalized aggregation
- When enabled, results show U1-U8 chip positions instead of bus_ids
- Lane specifications can use either bus_id or chip position format

### Lane Specification Enhancements

With `--by-ubb-position` enabled:

| Specification | Meaning |
|--------------|---------|
| `all` | All chip positions (U1-U8), all ETH ports |
| `U1/ETH07` | Chip position U1, ETH07 (combines 01:00.0, 41:00.0, c1:00.0, 81:00.0) |
| `U1/ETH07/4` | Chip position U1, ETH07, lane 4 |
| `*/ETH07` | All chip positions, ETH07 |
| `01:00.0/ETH07` | Interpreted as U1/ETH07 (normalized automatically) |

### Function Signatures

```python
# LaneSelector
@classmethod
def from_spec(
    cls,
    spec: str,
    normalize_by_ubb: bool = False
) -> "LaneSelector":
    """Parse lane specification string.

    Args:
        spec: Lane specification (bus_id or chip position format)
        normalize_by_ubb: If True, aggregate by chip position
    """

# Query methods (signature unchanged, behavior depends on lane_selector)
def query_ber_statistics(
    self,
    lane_selector: LaneSelector,
    train_speeds: Optional[List[int]] = None,
) -> BERStatistics:
    """Calculate BER statistics.

    If lane_selector.normalize_by_ubb is True, aggregates by chip position.
    """
```

---

## 6. Data Flow

### Normal Mode (Current Behavior)

```
Query: stats 01:00.0/ETH07 --speed 200

1. Parse lane_spec -> LaneSelector(bus_id="01:00.0", eth_id="ETH07")
2. SQL: SELECT * FROM prbs_tests WHERE bus_id = '01:00.0' AND eth_id = 'ETH07'
3. Group results by (bus_id, eth_id) -> {"01:00.0/ETH07/lane0": stats, ...}
4. Render table/heatmap
```

### UBB-Normalized Mode (New)

```
Query: stats U1/ETH07 --speed 200 --by-ubb-position

1. Parse lane_spec -> LaneSelector(bus_id=None, eth_id="ETH07", normalize_by_ubb=True)
   - Note: "U1" is parsed but doesn't filter SQL (we want all UBBs)

2. SQL: SELECT * FROM prbs_tests WHERE eth_id = 'ETH07'
   - Returns data for ALL bus_ids with ETH07

3. Post-query: Add chip_position column via normalize_bus_id_to_chip()
   - 01:00.0 -> U1
   - 41:00.0 -> U1
   - c1:00.0 -> U1
   - 81:00.0 -> U1

4. Group results by (chip_position, eth_id) -> {"U1/ETH07/lane0": combined_stats, ...}
   - Samples from all 4 UBBs are combined

5. Render table/heatmap with U1-U8 labels
```

### Query Expansion Logic

When `--by-ubb-position` is set and a specific chip position is requested:

```python
# User specifies: U1/ETH07 --by-ubb-position
#
# This should:
# 1. Query data for ALL 4 corresponding bus_ids: 01:00.0, 41:00.0, c1:00.0, 81:00.0
# 2. Filter by eth_id = ETH07
# 3. Aggregate results under "U1"

# Implementation in LaneSelector.to_sql_filter():
def to_sql_filter(self) -> Tuple[str, tuple]:
    conditions = []
    params = []

    # Host filter (unchanged)
    if self.host and self.host != "*":
        conditions.append("host = ?")
        params.append(self.host)

    # Bus ID filter
    if self.normalize_by_ubb:
        # Don't filter by bus_id - we want all UBBs
        # If specific chip position requested, filter by corresponding bus_ids
        if self.bus_id and self.bus_id.startswith("U"):
            chip_num = int(self.bus_id[1])
            bus_ids = get_all_bus_ids_for_chip(chip_num)
            placeholders = ", ".join(["?" for _ in bus_ids])
            conditions.append(f"bus_id IN ({placeholders})")
            params.extend(bus_ids)
    elif self.bus_id and self.bus_id != "*":
        conditions.append("bus_id = ?")
        params.append(self.bus_id)

    # Eth ID filter (unchanged)
    if self.eth_id and self.eth_id != "*":
        conditions.append("eth_id = ?")
        params.append(self.eth_id)

    # ...rest of method...
```

---

## 7. Error Handling

### New Exception Types

None required. Existing exceptions cover error cases:
- `LaneSelectorError`: Invalid chip position format (e.g., "U9" - out of range)
- `QueryError`: Query execution failures

### Validation Rules

1. **Chip Position Range**: U1-U8 only (raise `LaneSelectorError` for U0, U9, etc.)
2. **Format Detection**: Auto-detect whether input is bus_id or chip position format
3. **Mode Consistency**: If `--by-ubb-position` flag, output always uses chip position format

---

## 8. Configuration

No configuration changes required. The feature is entirely flag-driven.

Future enhancement (Phase 2): Add config option for default mode:
```yaml
system_analysis:
  default_ubb_normalization: false  # Could be configurable
```

---

## 9. CLI Design

### Argument Parser Additions

**In `cli.py` - Add to each analysis subcommand:**

```python
# Global flag for UBB normalization (add to stats, threshold, custom, training, histogram, advanced-stats)
parser.add_argument(
    "--by-ubb-position",
    "-u",
    action="store_true",
    dest="by_ubb_position",
    help="Aggregate data by UBB chip position (U1-U8) instead of bus_id. "
         "Combines data from equivalent positions across all 4 UBBs.",
)
```

### Command Handler Updates

```python
def handle_stats(db: DatabaseManager, args: argparse.Namespace) -> int:
    """Handle stats command."""
    try:
        # Pass normalize_by_ubb flag to LaneSelector
        selector = LaneSelector.from_spec(
            args.lane_spec,
            normalize_by_ubb=args.by_ubb_position,  # NEW
        )
        engine = QueryEngine(db)

        result = engine.query_ber_statistics(
            selector,
            train_speeds=args.speeds,
        )

        # Rendering unchanged - it uses lane_id which now may be "U1/ETH07/lane0"
        # ...existing rendering logic...
```

### Help Text Update

```
bh-analyze-systems stats --help

Lane Specifications:
  all                      - All lanes on all systems
  01:00.0/ETH07           - Specific port (all lanes)
  01:00.0/*               - All ports on bus_id
  system/01:00.0/ETH07    - Specific system and port

UBB Position Mode (--by-ubb-position):
  U1/ETH07                - Chip position U1, ETH07 (combines all 4 UBBs)
  U1/*                    - All ports on chip position U1
  */ETH07                 - ETH07 on all chip positions

  Note: Bus_ids are automatically normalized to chip positions when
  --by-ubb-position is specified. e.g., "01:00.0" becomes "U1".
```

---

## 10. Testing Strategy

### Unit Tests

**New test file:** `tests/unit/system_analysis/test_ubb_normalization.py`

```python
class TestUBBNormalization:
    """Tests for UBB normalization module."""

    def test_get_chip_position(self):
        assert get_chip_position("01:00.0") == 1
        assert get_chip_position("41:00.0") == 1
        assert get_chip_position("c5:00.0") == 5
        assert get_chip_position("88:00.0") == 8

    def test_get_ubb_number(self):
        assert get_ubb_number("01:00.0") == 1
        assert get_ubb_number("41:00.0") == 2
        assert get_ubb_number("c1:00.0") == 3
        assert get_ubb_number("81:00.0") == 4

    def test_normalize_bus_id_to_chip(self):
        assert normalize_bus_id_to_chip("01:00.0") == "U1"
        assert normalize_bus_id_to_chip("41:00.0") == "U1"
        assert normalize_bus_id_to_chip("c1:00.0") == "U1"
        assert normalize_bus_id_to_chip("81:00.0") == "U1"
        assert normalize_bus_id_to_chip("c5:00.0") == "U5"

    def test_get_all_bus_ids_for_chip(self):
        bus_ids = get_all_bus_ids_for_chip(1)
        assert bus_ids == ("01:00.0", "41:00.0", "c1:00.0", "81:00.0")

    def test_normalize_lane_id(self):
        assert normalize_lane_id("01:00.0/ETH07/lane4") == "U1/ETH07/lane4"
        assert normalize_lane_id("c5:00.0/ETH10/lane0") == "U5/ETH10/lane0"

    def test_group_lane_ids_by_chip_position(self):
        lane_ids = [
            "01:00.0/ETH07/lane0",
            "41:00.0/ETH07/lane0",
            "c1:00.0/ETH07/lane0",
            "81:00.0/ETH07/lane0",
        ]
        grouped = group_lane_ids_by_chip_position(lane_ids)
        assert "U1/ETH07/lane0" in grouped
        assert len(grouped["U1/ETH07/lane0"]) == 4
```

**Additions to existing tests:**

```python
# tests/unit/system_analysis/test_query_engine.py

class TestLaneSelectorUBBMode:
    """Tests for LaneSelector with UBB normalization."""

    def test_from_spec_with_ubb_normalization(self):
        selector = LaneSelector.from_spec("U1/ETH07", normalize_by_ubb=True)
        assert selector.normalize_by_ubb is True
        assert selector.eth_id == "ETH07"

    def test_from_spec_bus_id_converted_in_ubb_mode(self):
        # When in UBB mode, bus_id spec is treated as chip position
        selector = LaneSelector.from_spec("01:00.0/ETH07", normalize_by_ubb=True)
        assert selector.normalize_by_ubb is True
        # The selector should handle this appropriately

    def test_to_sql_filter_ubb_mode_no_bus_id_filter(self):
        selector = LaneSelector.from_spec("all", normalize_by_ubb=True)
        where, params = selector.to_sql_filter()
        # Should not filter by bus_id
        assert "bus_id" not in where

    def test_to_sql_filter_ubb_mode_specific_chip(self):
        selector = LaneSelector.from_spec("U1/ETH07", normalize_by_ubb=True)
        where, params = selector.to_sql_filter()
        # Should filter by all 4 bus_ids for U1
        assert "bus_id IN" in where
        assert "01:00.0" in params
        assert "41:00.0" in params


class TestQueryEngineUBBMode:
    """Tests for QueryEngine with UBB normalization."""

    def test_query_ber_statistics_ubb_mode(self, populated_db):
        engine = QueryEngine(populated_db)
        selector = LaneSelector.from_spec("all", normalize_by_ubb=True)

        result = engine.query_ber_statistics(selector)

        # Lane IDs should use chip position format
        for lane_id in result.lane_stats.keys():
            assert lane_id.startswith("U")
            assert not ":" in lane_id.split("/")[0]

    def test_ubb_mode_combines_samples(self, populated_db):
        """Verify that UBB mode combines samples from all 4 UBBs."""
        engine = QueryEngine(populated_db)

        # Query in normal mode
        normal_selector = LaneSelector.from_spec("01:00.0/ETH07/4")
        normal_result = engine.query_ber_statistics(normal_selector)
        normal_samples = normal_result.lane_stats["01:00.0/ETH07/lane4"].sample_count

        # Query in UBB mode
        ubb_selector = LaneSelector.from_spec("U1/ETH07/4", normalize_by_ubb=True)
        ubb_result = engine.query_ber_statistics(ubb_selector)
        ubb_samples = ubb_result.lane_stats["U1/ETH07/lane4"].sample_count

        # UBB mode should have ~4x the samples (from all 4 UBBs)
        assert ubb_samples >= normal_samples
```

### Integration Tests

```python
# tests/integration/system_analysis/test_ubb_normalization_e2e.py

class TestUBBNormalizationEndToEnd:
    """End-to-end tests for UBB normalization feature."""

    def test_cli_by_ubb_position_flag(self, populated_db, tmp_path):
        """Test CLI with --by-ubb-position flag."""
        result = subprocess.run([
            "bh-analyze-systems",
            "--db", str(populated_db),
            "stats", "all",
            "--by-ubb-position",
        ], capture_output=True, text=True)

        assert result.returncode == 0
        # Output should show U1-U8 instead of bus_ids
        assert "U1/" in result.stdout or "U1/" in result.stderr
        assert "01:00.0/" not in result.stdout

    def test_excel_export_ubb_mode(self, populated_db, tmp_path):
        """Test Excel export with UBB normalization."""
        output_file = tmp_path / "ubb_stats.xlsx"

        result = subprocess.run([
            "bh-analyze-systems",
            "--db", str(populated_db),
            "stats", "all",
            "--by-ubb-position",
            "--excel-output", str(output_file),
        ], capture_output=True, text=True)

        assert result.returncode == 0
        assert output_file.exists()

        # Verify Excel content uses chip position format
        import openpyxl
        wb = openpyxl.load_workbook(output_file)
        # Check cell values for U1-U8 format
```

---

## 11. Migration Path

### Backward Compatibility

- **No breaking changes**: All existing commands work identically without the `--by-ubb-position` flag
- **No database schema changes**: Existing databases work without modification
- **No configuration changes**: Feature is purely additive

### Rollout Strategy

1. **Phase 1 (v0.7.0)**: Implement core feature with CLI flag
2. **Phase 2 (future)**: Add shell command support
3. **Phase 3 (future)**: Consider config option for default mode

---

## 12. Implementation Phases

### Phase 1: Core Feature (v0.7.0 MVP)

1. **Create `ubb_normalization.py` module**
   - Implement normalization functions
   - Add unit tests
   - ~100 lines of code

2. **Modify `LaneSelector` class**
   - Add `normalize_by_ubb` attribute
   - Update `from_spec()` method
   - Update `to_sql_filter()` for UBB mode
   - ~50 lines of changes

3. **Update `QueryEngine` methods**
   - Add UBB aggregation helpers
   - Modify each query method to check `normalize_by_ubb`
   - ~200 lines of changes across all methods

4. **Update CLI**
   - Add `--by-ubb-position` flag to all analysis commands
   - Update help text
   - ~30 lines per command

5. **Testing**
   - Unit tests for normalization module
   - Unit tests for LaneSelector UBB mode
   - Unit tests for QueryEngine UBB aggregation
   - Integration tests for CLI

### Phase 2: Shell Support (Future)

- Add `--by-ubb-position` flag parsing to interactive shell
- Update shell help text

### Phase 3: Visualization Enhancements (Future)

- Consider grouping U1-U8 visually in heatmaps
- Add "UBB View" label to outputs

---

## 13. Trade-offs and Alternatives

### Alternative 1: Database Schema Change

**Approach**: Add `chip_position` column to `prbs_tests` table during ingestion.

**Pros**:
- Faster queries (no post-processing)
- Pre-computed grouping

**Cons**:
- Requires database migration
- Adds storage overhead
- Less flexible (always computed)

**Decision**: Rejected. Query-time transformation is more flexible and requires no migration.

### Alternative 2: Separate Commands

**Approach**: Create new commands like `bh-analyze-systems ubb-stats`.

**Pros**:
- Clear separation of functionality
- No flag to remember

**Cons**:
- Doubles the number of commands
- Code duplication
- Inconsistent with existing CLI pattern

**Decision**: Rejected. A single flag is cleaner and follows Unix convention.

### Alternative 3: View-based Selection

**Approach**: Use lane spec syntax to indicate mode (e.g., `~U1/ETH07` means UBB mode).

**Pros**:
- No separate flag
- Self-contained specification

**Cons**:
- Non-obvious syntax
- Breaks existing lane spec parsing
- Harder to discover

**Decision**: Rejected. Explicit `--by-ubb-position` flag is clearer and more discoverable.

### Chosen Approach: Query-Time Flag

**Pros**:
- No database changes
- Backward compatible
- Clear semantics with `--by-ubb-position` flag
- Flexible - user chooses per-query
- Simple implementation

**Cons**:
- Slight performance overhead (grouping happens in Python)
- Flag must be specified each time

**Mitigation**: Performance overhead is negligible for typical query sizes. Future config option could set default mode.

---

## 14. Risks and Mitigations

### Risk 1: Confusion Between Modes

**Risk**: Users may not understand when to use UBB mode vs normal mode.

**Mitigation**:
- Clear help text explaining the use case
- Output clearly labeled with mode indicator
- Documentation with examples

### Risk 2: Mixed Output Confusion

**Risk**: Users may mix outputs from different modes and get confused.

**Mitigation**:
- Include mode indicator in output headers
- Different column headers (e.g., "Chip Position" vs "Bus ID")
- Excel worksheet names include mode

### Risk 3: Performance with Large Datasets

**Risk**: Post-query grouping may be slow with very large result sets.

**Mitigation**:
- Pandas groupby is efficient for typical sizes
- If needed, move aggregation to SQL layer in Phase 2
- Monitor performance during testing

---

## 15. Summary

The UBB normalization feature adds a powerful analysis capability by enabling aggregation across equivalent chip positions on all 4 UBBs. The implementation:

1. **Preserves backward compatibility** - existing behavior unchanged
2. **Uses query-time transformation** - no database changes
3. **Provides clear CLI interface** - `--by-ubb-position` flag
4. **Maintains clean architecture** - new module with isolated logic
5. **Enables 4x sample sizes** - for more statistically significant analysis

Key implementation locations:
- **New**: `/Users/kmarples/Blackhole/glx/bh-glx-data/src/bh_glx_data/system_analysis/ubb_normalization.py`
- **Modified**: `/Users/kmarples/Blackhole/glx/bh-glx-data/src/bh_glx_data/system_analysis/query_engine.py`
- **Modified**: `/Users/kmarples/Blackhole/glx/bh-glx-data/src/bh_glx_data/system_analysis/cli.py`
- **New tests**: `/Users/kmarples/Blackhole/glx/bh-glx-data/tests/unit/system_analysis/test_ubb_normalization.py`
