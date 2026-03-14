# `bh-analyze-systems` Update

This document outlines some desired changes and bug fixes to be done in the next version of `bh-analyze-systems`. The changes are to be carried out by the feature-implementer agent and the user guide is to be updated by the user-guide-writer agent.

Next version : 0.6.0

## Change requests

The features described below are to be implemented in the next version of `bh-analyze-systems`

### Histogram

Add a histogram feature that allows the user to request a histogram visualization of the BER data for a particular bus_id/eth_id/serdes_lane.

#### Extended Lane Selection Syntax

Extend `LaneSelector` class to support lane-specific selection:

**New Syntax Support**:
- `01:00.0/ETH07/4` - Specific lane 4 on a specific port
- `bh-glx-c02u02/01:00.0/ETH07/4` - Specific lane on specific system
- `*/ETH07/4` - Lane 4 on ETH07 across all systems
- `01:00.0/ETH07` - All 8 lanes on specific port (shows 8 histograms)

**Implementation**:
- Add `lane_num: Optional[int]` attribute to `LaneSelector` class
- Extend `from_spec()` parser to handle 4-part specifications
- Add validation to ensure lane_num is 0-7
- Update `to_sql_filter()` to include lane filtering when specified
- Error handling for invalid lane numbers on specific ETH ports

#### Histogram Bins

Use 10 bins based on BER value ranges (logarithmic scale):
```
Bin 1:  BER < 1e-12
Bin 2:  1e-12 ≤ BER < 1e-11
Bin 3:  1e-11 ≤ BER < 1e-10
Bin 4:  1e-10 ≤ BER < 1e-9
Bin 5:  1e-9 ≤ BER < 1e-8
Bin 6:  1e-8 ≤ BER < 1e-7
Bin 7:  1e-7 ≤ BER < 1e-6
Bin 8:  1e-6 ≤ BER < 1e-5
Bin 9:  1e-5 ≤ BER < 1e-4
Bin 10: BER ≥ 1e-4
```

#### Terminal Display Format

Horizontal bar chart with color-coded bins:

**Single Lane Example**:
```
BER Histogram - 01:00.0/ETH07/lane4

  < 1e-12   ████████████████████████████ 145
  1e-12-11  ██████████████ 72
  1e-11-10  ████████ 42
  1e-10-9   ████ 21
  1e-9-8    ██ 12
  1e-8-7    █ 5
  1e-7-6    █ 3
  1e-6-5     1
  1e-5-4     0
  >= 1e-4    0

Total Samples: 301  |  Systems: 5  |  Speeds: 200
```

**Multiple Lanes Example** (when requesting all lanes on a port):
```
BER Histograms - 01:00.0/ETH07 (all lanes)

Lane 0:
  < 1e-12   ████████████████████████████ 145
  1e-12-11  ██████████████ 72
  [... bins ...]

Lane 1:
  < 1e-12   ███████████████████████ 120
  1e-12-11  ████████████ 65
  [... bins ...]

[... lanes 2-7 ...]

Total Samples: 2408  |  Systems: 5  |  Speeds: 200
```

**Visual Elements**:
- Unicode block characters (█) for bar visualization
- Scale bars relative to maximum count in dataset
- Color-code bars using existing BER color scheme (green for low BER, red for high)
- Show exact count next to each bar
- Display bin ranges in scientific notation
- Separate display for each lane when multiple lanes selected

#### Data Structures

**New Dataclass** (in `query_engine.py`):
```python
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
```

#### Query Engine Method

**New Method** (in `QueryEngine` class):
```python
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
```

#### Visualization Method

**New Method** (add to `HeatMapRenderer` or create new `HistogramRenderer` class):
```python
def render_ber_histogram(
    self,
    histogram: Union[BERHistogram, List[BERHistogram]],
    max_bar_width: int = 50,
) -> str:
    """Render BER histogram(s) for terminal.

    Args:
        histogram: Single histogram or list of histograms
        max_bar_width: Maximum width of bars in characters

    Returns:
        Formatted histogram string with ANSI colors
    """
```

#### CLI Integration

**New Subcommand**:
```bash
# Single lane
bh-analyze-systems histogram 01:00.0/ETH07/4 --speed 200

# All lanes on a port (shows 8 histograms)
bh-analyze-systems histogram 01:00.0/ETH07 --speed 200

# Specific system
bh-analyze-systems histogram bh-glx-c02u02/01:00.0/ETH07/4
```

**Arguments**:
- `lane_spec` (required): Lane specification (single lane or port for all lanes)
- `--speed` (optional): Filter by train speeds
- `--max-bar-width` (optional): Max width of bars (default: 50)

#### Implementation Order

1. Extend `LaneSelector` to support lane-specific selection (4-part specs)
2. Add `BERHistogram` dataclass to `query_engine.py`
3. Implement `query_ber_histogram()` in `QueryEngine` class
4. Create histogram rendering method in visualization module
5. Add `histogram` CLI subcommand
6. Write comprehensive unit tests for all components
7. Write integration tests for end-to-end functionality

### Advanced Statistics

Add a mechanism to view advanced BER statistics where per-host statistics are aggregated and analyzed across all systems. This provides a higher-level view of how consistent BER performance is across the fleet.

#### Feature Description

For a given lane selection, compute BER statistics (min/avg/max) per host, then compute statistics of those statistics across all hosts.

**Conceptual Example**:

Given two systems with the following per-host BER statistics for a lane:
- bh-glx-c02u02: min=1e-12, avg=2e-11, max=3e-10
- bh-glx-c03u02: min=5e-13, avg=1e-11, max=5e-10

The aggregated statistics would be:
- **MIN statistic across hosts**: min=5e-13, avg=7.5e-13, max=1e-12
- **AVG statistic across hosts**: min=1e-11, avg=1.5e-11, max=2e-11
- **MAX statistic across hosts**: min=3e-10, avg=4e-10, max=5e-10

This shows the range and distribution of BER performance across the fleet. See the Visualization section below for the actual table output format.

#### Data Structures

**New Dataclass** (in `query_engine.py`):
```python
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
```

#### Query Engine Method

**New Method** (in `QueryEngine` class):
```python
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
```

#### Visualization

Display two separate tables using Rich library:

**Table 1: Per-Host Statistics** (shown first)
```
Per-Host Statistics - 01:00.0/ETH07/lane4
┌────────────────┬──────────┬──────────┬──────────┬─────────┐
│ Host           │ Min BER  │ Avg BER  │ Max BER  │ Samples │
├────────────────┼──────────┼──────────┼──────────┼─────────┤
│ bh-glx-c02u02  │ 1.00e-12 │ 2.00e-11 │ 3.00e-10 │ 150     │
│ bh-glx-c03u02  │ 5.00e-13 │ 1.00e-11 │ 5.00e-10 │ 151     │
└────────────────┴──────────┴──────────┴──────────┴─────────┘
```

**Table 2: Statistics of Host Statistics** (shown below Table 1)
```
Statistics of Host Statistics
┌───────────┬──────────┬──────────┬──────────┐
│ Metric    │ Minimum  │ Average  │ Maximum  │
├───────────┼──────────┼──────────┼──────────┤
│ MIN       │ 5.00e-13 │ 7.50e-13 │ 1.00e-12 │
│ AVG       │ 1.00e-11 │ 1.50e-11 │ 2.00e-11 │
│ MAX       │ 3.00e-10 │ 4.00e-10 │ 5.00e-10 │
└───────────┴──────────┴──────────┴──────────┘

Systems: 2  |  Total Samples: 301  |  Speeds: 200
```

**Implementation Notes**:
- Use `TableRenderer` class to create both tables
- Render Table 1 with per-host statistics first
- Add spacing between tables
- Render Table 2 with aggregated statistics below
- Add metadata footer after both tables

#### CLI Integration

**New Subcommand**:
```bash
# Single lane
bh-analyze-systems advanced-stats 01:00.0/ETH07/4 --speed 200

# All lanes on a port
bh-analyze-systems advanced-stats 01:00.0/ETH07 --speed 200

# All ports on all systems
bh-analyze-systems advanced-stats all --speed 200
```

**Arguments**:
- `lane_spec` (required): Lane specification
- `--speed` (optional): Filter by train speeds
- `--format` (optional): Output format (table only for now)

#### Implementation Order

1. Add `HostBERStats` and `AggregatedHostStats` dataclasses
2. Implement `query_aggregated_host_stats()` in `QueryEngine`
3. Add statistics calculation helper functions
4. Create table rendering method in `TableRenderer`
5. Add `advanced-stats` CLI subcommand
6. Write comprehensive unit tests
7. Write integration tests

### Rename Variance Statistic to Avg

The current `--statistic variance` option provides average BER with variance indicators, which is more useful than the plain `avg` option. Consolidate these by renaming `variance` to `avg` and removing the original `avg` option.

#### Current State

The `stats` command supports:
- `--statistic min` - Show minimum BER
- `--statistic avg` - Show average BER (plain, no variance indicators)
- `--statistic max` - Show maximum BER
- `--statistic high_ber` - Show count of high BER samples
- `--statistic variance` - Show average BER with variance indicators (●, ◆, ▲, ■, ✕)

#### Desired State

After this change:
- `--statistic min` - Show minimum BER (unchanged)
- `--statistic avg` - Show average BER with variance indicators (replaces current variance)
- `--statistic max` - Show maximum BER (unchanged)
- `--statistic high_ber` - Show count of high BER samples (unchanged)
- `--statistic variance` - REMOVED (functionality moved to avg)

#### Implementation Changes

**File: `cli.py`**
- Update `--statistic` choices from `["avg", "min", "max", "high_ber", "variance"]` to `["avg", "min", "max", "high_ber"]`
- Update help text to indicate that `avg` includes variance indicators

**File: `visualization.py`**
- In `_render_terminal_ber_heatmap()` method:
  - Change condition from `if metric == "variance":` to `if metric == "avg":`
  - Update title from "VARIANCE Heatmap" to "AVG Heatmap (with Variance Indicators)"
  - Ensure variance indicators (symbols) are always shown for avg metric

**Backwards Compatibility**:
- This is a breaking change for users using `--statistic variance`
- They will need to switch to `--statistic avg`
- Document this change clearly in release notes

#### Testing Updates

Update tests that reference `variance` statistic:
- Change test cases using `statistic="variance"` to `statistic="avg"`
- Verify that `avg` now shows variance indicators
- Ensure old `variance` option is no longer accepted

## Bug Fixes

None

## Post Implementation Actions

1. Write tests and make sure they pass
2. User the user-guide-writer agent to update the user guide to reflect changes if necessary
3. Commit the changes and notify me to push them
