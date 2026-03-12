# System Analysis Tool - Architecture Design

## Overview

The System Analysis Tool is a database utility for collecting, storing, and analyzing PRBS test data across multiple systems. It provides an efficient query interface with visualization capabilities for analyzing serdes lane performance patterns.

**Version:** 0.3.0
**Primary Purpose:** Aggregate and query PRBS test data from CSV files with memory-efficient storage and interactive analysis

---

## Design Principles

1. **Memory Efficiency**: Stream CSV processing + SQLite storage for large datasets
2. **Query Performance**: Indexed database for fast aggregations across systems
3. **Extensibility**: Modular design allowing easy addition of new query types
4. **Consistency**: Follows existing package architecture and coding standards
5. **Separation of Concerns**: Clear boundaries between ingestion, storage, querying, and presentation

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLI Interface                                  │
│        (bh-analyze-systems / system_analysis/cli.py)                    │
├──────────────┬──────────────┬──────────────┬──────────────┬─────────────┤
│   Ingest     │    Query     │  Visualize   │    Export    │ Interactive │
│   Command    │   Commands   │   Commands   │   Command    │    Mode     │
└──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┴──────┬──────┘
       │              │              │              │              │
       v              v              v              v              v
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Ingestion  │ │    Query     │ │Visualization │ │    Export    │ │  Interactive │
│   Engine     │ │   Engine     │ │   Engine     │ │   Engine     │ │   Shell      │
│              │ │              │ │              │ │              │ │              │
│              │ │              │ │ + Color      │ │  (Excel)     │ │              │
│              │ │              │ │   Schemes    │ │              │ │              │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────────────┘
       │                │                │                │
       v                v                v                v
┌─────────────────────────────────────────────────────────────────────────┐
│                       Database Manager                                   │
│                (SQLite with indexed schema)                              │
└─────────────────────────────────────────────────────────────────────────┘
       │
       v
┌─────────────────────────────────────────────────────────────────────────┐
│                         Data Store                                       │
│              (~/.local/share/bh-glx-data/analysis.db)                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Module Structure

Following the existing package pattern:

```
src/bh_glx_data/
└── system_analysis/
    ├── __init__.py
    ├── cli.py                  # CLI entry point
    ├── database.py             # Database schema and manager
    ├── ingestion.py            # CSV loading and filtering
    ├── query_engine.py         # Query abstraction layer
    ├── statistics.py           # Statistical calculations
    ├── visualization.py        # Heat maps and tables
    ├── export.py               # Excel export functionality
    └── interactive.py          # Interactive shell mode
```

---

## Database Design

### Storage Technology: SQLite

**Rationale:**

- Zero-configuration embedded database
- Efficient indexing for fast queries
- ACID transactions for data integrity
- Small footprint with excellent performance
- Built-in aggregation functions
- No separate server process needed

### Database Schema

#### Table: `prbs_tests`

Primary table storing filtered test results.

```sql
CREATE TABLE prbs_tests (
    -- Primary identification
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- System identification
    host TEXT NOT NULL,
    bus_id TEXT NOT NULL,
    eth_id TEXT NOT NULL,
    interface_id TEXT,

    -- Test metadata
    date TEXT NOT NULL,
    test_status TEXT NOT NULL,  -- PASS, BER_THRESHOLD_EXCEEDED, TRAINING_FAIL
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
    acc_lane_error_cnt TEXT,  -- Stored as JSON string
    acc_lane_error_cnt_overflow TEXT,  -- Stored as JSON string

    -- Timing
    acc_time_elapsed REAL,

    -- Test parameters
    ber_threshold_used REAL,
    interface_type_used TEXT,

    -- Source tracking
    source_file TEXT NOT NULL,
    ingestion_timestamp TEXT NOT NULL
);

-- Indexes for fast queries
CREATE INDEX idx_host ON prbs_tests(host);
CREATE INDEX idx_bus_id ON prbs_tests(bus_id);
CREATE INDEX idx_eth_id ON prbs_tests(eth_id);
CREATE INDEX idx_test_status ON prbs_tests(test_status);
CREATE INDEX idx_train_speed ON prbs_tests(train_speed);
CREATE INDEX idx_host_speed ON prbs_tests(host, train_speed);
CREATE INDEX idx_bus_eth ON prbs_tests(bus_id, eth_id);
CREATE INDEX idx_status_speed ON prbs_tests(test_status, train_speed);
```

#### Table: `ingestion_metadata`

Track ingestion runs for data provenance.

```sql
CREATE TABLE ingestion_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingestion_timestamp TEXT NOT NULL,
    source_directory TEXT NOT NULL,
    files_processed INTEGER NOT NULL,
    rows_ingested INTEGER NOT NULL,
    rows_filtered INTEGER NOT NULL,
    duration_seconds REAL NOT NULL
);
```

### Memory Management Strategy

1. **Streaming CSV Processing**
   - Process CSV files one at a time
   - Use `pandas.read_csv()` with `chunksize` parameter for large files
   - Filter rows during streaming (before loading into memory)
   - Batch insert into SQLite (e.g., 1000 rows at a time)

2. **Database Optimization**
   - Store only required columns (44 excluded columns saved)
   - Use appropriate data types (INTEGER for speeds, REAL for BER values)
   - Indexed queries for O(log n) lookups
   - SQLite page cache tuned for analytical workloads

3. **Query Result Management**
   - Paginated results for large query responses
   - Lazy evaluation for visualization data
   - Configurable memory limits

---

## Component Details

### 1. Ingestion Engine (`ingestion.py`)

**Responsibility:** Load CSV files, filter data, populate database

**Key Classes:**

```python
class CSVIngester:
    """Handles CSV ingestion with streaming and filtering."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.excluded_columns = [...]  # 44 excluded columns

    def ingest_directory(
        self,
        input_dir: Path,
        status_filter: List[str] = ["PASS", "BER_THRESHOLD_EXCEEDED", "TRAINING_FAIL"]
    ) -> IngestionResult:
        """
        Ingest all CSV files from directory.

        Process:
        1. Discover all CSV files in directory
        2. For each file:
           - Stream read with pandas (chunksize=1000)
           - Filter by test_status
           - Drop excluded columns
           - Batch insert into database
        3. Record metadata in ingestion_metadata table

        Returns:
            IngestionResult with statistics
        """
        pass

    def _process_csv_chunk(self, chunk: pd.DataFrame) -> List[TestRecord]:
        """Filter and transform a chunk of CSV data."""
        pass
```

**Data Models:**

```python
@dataclass
class TestRecord:
    """Represents a single PRBS test record."""
    host: str
    bus_id: str
    eth_id: str
    date: str
    test_status: str
    train_speed: int
    acc_ber_lanes: List[Optional[float]]  # 8 lanes
    # ... other fields

@dataclass
class IngestionResult:
    """Result of an ingestion run."""
    files_processed: int
    rows_ingested: int
    rows_filtered: int
    duration: float
    errors: List[str]
```

---

### 2. Database Manager (`database.py`)

**Responsibility:** Database schema management, connection handling, low-level queries

**Key Classes:**

```python
class DatabaseManager:
    """Manages SQLite database operations."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None

    def initialize_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        pass

    def insert_batch(self, records: List[TestRecord]) -> int:
        """Insert batch of test records efficiently."""
        pass

    def execute_query(self, query: str, params: tuple = ()) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame."""
        pass

    def get_unique_hosts(self) -> List[str]:
        """Get list of all unique hostnames in database."""
        pass

    def get_unique_speeds(self) -> List[int]:
        """Get list of all unique train speeds."""
        pass

    def get_database_stats(self) -> DatabaseStats:
        """Get statistics about the database contents."""
        pass
```

**Database Location:**

- Default: `~/.local/share/bh-glx-data/analysis.db`
- Configurable via config.yaml or CLI argument
- Follows XDG Base Directory specification

---

### 3. Query Engine (`query_engine.py`)

**Responsibility:** High-level query abstraction, serdes lane selection logic

**Key Classes:**

```python
class QueryEngine:
    """High-level query interface for PRBS test data."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def query_ber_statistics(
        self,
        lane_selector: LaneSelector,
        train_speeds: Optional[List[int]] = None,
        exclude_training_failures: bool = True
    ) -> BERStatistics:
        """
        Calculate BER statistics for specified lanes.

        Returns min, max, avg BER for each lane, excluding
        lanes with training failures (no BER data).

        Args:
            lane_selector: Specifies which lanes to analyze
            train_speeds: Filter by specific speeds (None = all)
            exclude_training_failures: Exclude rows with test_status=TRAINING_FAIL

        Returns:
            BERStatistics with per-lane stats and metadata
        """
        pass

    def query_ber_threshold_exceeded(
        self,
        lane_selector: LaneSelector,
        train_speeds: Optional[List[int]] = None
    ) -> ThresholdExceededCounts:
        """
        Count BER_THRESHOLD_EXCEEDED occurrences per lane.

        Returns count of rows where test_status = 'BER_THRESHOLD_EXCEEDED'
        for each specified lane.
        """
        pass

    def query_custom_ber_threshold(
        self,
        lane_selector: LaneSelector,
        threshold: float,
        train_speeds: Optional[List[int]] = None
    ) -> CustomThresholdCounts:
        """
        Count occurrences where acc_ber_lane# > threshold.

        Custom threshold analysis independent of test_status.
        """
        pass

    def query_training_failures(
        self,
        lane_selector: LaneSelector,
        train_speeds: Optional[List[int]] = None
    ) -> TrainingFailureCounts:
        """
        Count TRAINING_FAIL occurrences per lane.

        Returns count of rows where test_status = 'TRAINING_FAIL'
        for each specified lane.
        """
        pass
```

**Lane Selection Abstraction:**

```python
class LaneSelector:
    """Specifies which serdes lanes to query."""

    @classmethod
    def from_spec(cls, spec: str) -> 'LaneSelector':
        """
        Parse lane specification string.

        Examples:
            "all" -> All lanes on all systems
            "01:00.0/ETH07" -> Specific port
            "01:00.0/*" -> All ports on bus_id
            "bh-glx-c02u02/01:00.0/ETH07" -> Specific system and port
            "bh-glx-c02u02/*" -> All ports on system
            "*/ETH07" -> ETH07 on all systems
        """
        pass

    def to_sql_filter(self) -> Tuple[str, tuple]:
        """Generate SQL WHERE clause for this selector."""
        pass
```

**Result Data Models:**

```python
@dataclass
class BERStatistics:
    """BER statistics result."""
    lane_stats: Dict[str, LaneBERStats]  # lane_id -> stats
    num_tests: int
    num_systems: int
    train_speeds: List[int]

@dataclass
class LaneBERStats:
    """Statistics for a single lane."""
    lane_id: str  # e.g., "01:00.0/ETH07/lane0"
    min_ber: float
    max_ber: float
    avg_ber: float
    sample_count: int

@dataclass
class ThresholdExceededCounts:
    """BER threshold exceeded counts."""
    lane_counts: Dict[str, int]  # lane_id -> count
    num_tests: int
    num_systems: int
    train_speeds: List[int]
```

---

### 4. Statistics Module (`statistics.py`)

**Responsibility:** Statistical calculations and aggregations

**Key Functions:**

```python
def calculate_lane_statistics(
    df: pd.DataFrame,
    lane_columns: List[str]
) -> Dict[str, LaneBERStats]:
    """Calculate min/max/avg for specified BER lane columns."""
    pass

def count_by_status(
    df: pd.DataFrame,
    status: str,
    lane_columns: List[str]
) -> Dict[str, int]:
    """Count occurrences of specific test_status per lane."""
    pass

def count_by_threshold(
    df: pd.DataFrame,
    threshold: float,
    lane_columns: List[str]
) -> Dict[str, int]:
    """Count occurrences where BER exceeds threshold."""
    pass
```

---

### 5. Visualization Engine (`visualization.py`)

**Responsibility:** Render query results as tables or heat maps

**Key Classes:**

```python
class TableRenderer:
    """Render query results as formatted tables."""

    def render_ber_statistics(self, stats: BERStatistics) -> str:
        """
        Render BER statistics as table.

        Example output:
        ┌─────────────────────┬───────────┬───────────┬───────────┬─────────┐
        │ Lane                │ Min BER   │ Max BER   │ Avg BER   │ Samples │
        ├─────────────────────┼───────────┼───────────┼───────────┼─────────┤
        │ 01:00.0/ETH07/lane0 │ 1.23e-12  │ 4.56e-10  │ 2.34e-11  │ 450     │
        │ 01:00.0/ETH07/lane1 │ 8.90e-13  │ 3.21e-10  │ 1.87e-11  │ 450     │
        └─────────────────────┴───────────┴───────────┴───────────┴─────────┘

        Tests: 450  Systems: 12  Speeds: 100, 200
        """
        pass

    def render_count_table(self, counts: Union[ThresholdExceededCounts, TrainingFailureCounts]) -> str:
        """Render counts as table."""
        pass

class HeatMapRenderer:
    """Render query results as heat maps."""

    def __init__(
        self,
        output_format: str = "terminal",
        count_color_scheme: Optional[ColorScheme] = None,
        ber_color_scheme: Optional[ColorScheme] = None
    ):
        """
        Args:
            output_format: "terminal" (ANSI colors) or "html"
            count_color_scheme: Color scheme for count heatmaps (None = use default)
            ber_color_scheme: Color scheme for BER heatmaps (None = use default)
        """
        self.format = output_format
        self.count_colors = count_color_scheme or COUNT_COLOR_SCHEMES["default"]
        self.ber_colors = ber_color_scheme or BER_COLOR_SCHEMES["default"]

    def render_count_heatmap(
        self,
        counts: Union[ThresholdExceededCounts, TrainingFailureCounts],
        color_scale: str = "linear",
        color_scheme: Optional[ColorScheme] = None
    ) -> str:
        """
        Render counts as color-coded heat map.

        Terminal format uses ANSI color codes based on color scheme:
        Default scheme:
        - Green: 0 failures
        - Yellow: 1-10 failures
        - Orange: 11-50 failures
        - Red: 50+ failures

        Args:
            counts: Count data to visualize
            color_scale: "linear" or "log" (for value interpolation)
            color_scheme: Override instance color scheme

        HTML format generates standalone HTML file with interactive features.
        """
        pass

    def render_ber_heatmap(
        self,
        stats: BERStatistics,
        metric: str = "avg",
        color_scheme: Optional[ColorScheme] = None
    ) -> str:
        """
        Render BER statistics as heat map.

        Uses BER-appropriate color thresholds based on color scheme:
        Default scheme:
        - Green: 0
        - Yellow: > 1e-12
        - Orange: > 1e-10
        - Red: > 1e-8

        Args:
            stats: BER statistics to visualize
            metric: "min", "max", or "avg"
            color_scheme: Override instance color scheme
        """
        pass

    def _get_color_for_value(
        self,
        value: float,
        color_scheme: ColorScheme
    ) -> str:
        """
        Determine color for a value based on threshold ranges.

        Returns ANSI color code for terminal or hex color for HTML.
        """
        pass
```

**Visualization Dependencies:**

- `rich` library for terminal tables and colors
- `matplotlib` or `plotly` for HTML heat maps (optional dependency)

**Color Scheme Configuration:**

The heat map renderers support configurable color schemes through thresholds:

```python
@dataclass
class ColorScheme:
    """Color scheme configuration for heat maps."""
    thresholds: List[Tuple[float, str]]  # (value, color) pairs
    default_color: str

    @classmethod
    def from_config(cls, config: dict) -> 'ColorScheme':
        """Load color scheme from configuration."""
        pass

# Count heatmap color schemes
COUNT_COLOR_SCHEMES = {
    "default": ColorScheme(
        thresholds=[(0, "green"), (1, "yellow"), (11, "orange"), (50, "red")],
        default_color="red"
    ),
    "strict": ColorScheme(
        thresholds=[(0, "green"), (1, "red")],
        default_color="red"
    )
}

# BER heatmap color schemes
BER_COLOR_SCHEMES = {
    "default": ColorScheme(
        thresholds=[(0, "green"), (1e-12, "yellow"), (1e-10, "orange"), (1e-8, "red")],
        default_color="red"
    ),
    "sensitive": ColorScheme(
        thresholds=[(0, "green"), (1e-13, "yellow"), (1e-11, "orange"), (1e-9, "red")],
        default_color="red"
    )
}
```

Color schemes can be:

- Selected from built-in presets
- Defined in config.yaml
- Specified via CLI arguments

---

### 6. Export Module (`export.py`)

**Responsibility:** Export database contents and query results to Excel format

**Key Classes:**

```python
class ExcelExporter:
    """Export database data to Excel files."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def export_full_database(
        self,
        output_path: Path,
        filters: Optional[ExportFilters] = None
    ) -> ExportResult:
        """
        Export entire database (or filtered subset) to Excel.

        Creates Excel workbook with multiple sheets:
        - Summary: Database statistics and metadata
        - PRBS Tests: All PRBS test records
        - Training Failures: Filtered view of training failures
        - BER Exceeded: Filtered view of BER threshold exceeded
        - Metadata: Ingestion history

        Args:
            output_path: Path to output Excel file
            filters: Optional filters (hosts, speeds, date ranges)

        Returns:
            ExportResult with export statistics
        """
        pass

    def export_query_result(
        self,
        result: Union[BERStatistics, ThresholdExceededCounts],
        output_path: Path,
        format: str = "summary"
    ) -> None:
        """
        Export query result to Excel.

        Formats:
        - "summary": Formatted table with statistics
        - "detailed": Include raw data behind the statistics
        - "pivot": Excel pivot table ready format
        """
        pass

    def export_with_heatmap(
        self,
        result: Union[BERStatistics, ThresholdExceededCounts],
        output_path: Path,
        color_scheme: Optional[ColorScheme] = None
    ) -> None:
        """
        Export query result with conditional formatting as heatmap.

        Uses Excel conditional formatting to create color-coded cells.
        """
        pass

@dataclass
class ExportFilters:
    """Filters for database export."""
    hosts: Optional[List[str]] = None
    train_speeds: Optional[List[int]] = None
    test_status: Optional[List[str]] = None
    date_range: Optional[Tuple[str, str]] = None  # (start_date, end_date)

@dataclass
class ExportResult:
    """Result of export operation."""
    rows_exported: int
    sheets_created: int
    file_size_bytes: int
    output_path: Path
```

**Excel Export Features:**

- Multi-sheet workbooks with organized data
- Formatted headers and column widths
- Conditional formatting for heatmap visualization
- Pivot-table ready data structure
- Summary statistics sheet
- Metadata preservation

---

### 7. Interactive Shell (`interactive.py`)

**Responsibility:** Interactive REPL for exploratory analysis

**Key Classes:**

```python
class AnalysisShell:
    """Interactive shell for system analysis."""

    def __init__(self, query_engine: QueryEngine, exporter: ExcelExporter):
        self.query_engine = query_engine
        self.exporter = exporter
        self.history = []
        self.last_result = None

    def run(self) -> None:
        """Start interactive shell."""
        pass

    def _handle_command(self, command: str) -> None:
        """Parse and execute shell command."""
        pass
```

**Shell Commands:**

```
bh-analyze> help
Available commands:
  stats <lane-spec> [--speed SPEED]           - Show BER statistics
  threshold <lane-spec> [--speed SPEED]       - Show BER threshold exceeded
  custom <lane-spec> <threshold> [--speed]    - Show custom threshold counts
  training <lane-spec> [--speed SPEED]        - Show training failures
  systems                                      - List all systems
  speeds                                       - List all train speeds
  info                                         - Show database info
  export <format> [--output FILE]              - Export last result or full database
  help                                         - Show this help
  exit                                         - Exit shell

Export formats:
  csv           - Export to CSV
  excel         - Export to Excel with formatting
  excel-db      - Export entire database to Excel

Lane specifications:
  all                      - All lanes on all systems
  01:00.0/ETH07           - Specific port (all lanes)
  01:00.0/*               - All ports on bus_id
  system/01:00.0/ETH07    - Specific system and port
```

---

### 8. CLI Interface (`cli.py`)

**Responsibility:** Command-line entry point

**Command Structure:**

```bash
# Main command
bh-analyze-systems <subcommand> [options]

# Subcommands:
bh-analyze-systems ingest <input-dir> [--db PATH]
bh-analyze-systems stats <lane-spec> [--speed SPEED] [--format table|heatmap] [--color-scheme SCHEME]
bh-analyze-systems threshold <lane-spec> [--speed SPEED] [--format table|heatmap] [--color-scheme SCHEME]
bh-analyze-systems custom <lane-spec> <threshold> [--speed SPEED] [--format table|heatmap] [--color-scheme SCHEME]
bh-analyze-systems training <lane-spec> [--speed SPEED] [--format table|heatmap] [--color-scheme SCHEME]
bh-analyze-systems info [--db PATH]
bh-analyze-systems shell [--db PATH]
bh-analyze-systems export-excel [--output FILE] [--filters ...]

# Shortcut (same as bh-glx-data pattern)
bh-analyze-systems → Main entry point
```

**CLI Implementation:**

```python
def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze PRBS test data across multiple systems"
    )

    # Global options
    parser.add_argument("--db", type=Path, help="Database path")
    parser.add_argument("--verbose", "-v", action="store_true")

    subparsers = parser.add_subparsers(dest="command")

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest")
    ingest_parser.add_argument("input_dir", type=Path)

    # Stats command
    stats_parser = subparsers.add_parser("stats")
    stats_parser.add_argument("lane_spec", type=str)
    stats_parser.add_argument("--speed", type=int, action="append")
    stats_parser.add_argument("--format", choices=["table", "heatmap"], default="table")
    stats_parser.add_argument("--color-scheme", type=str, help="Color scheme name or path to config")

    # Threshold command (similar pattern)
    threshold_parser = subparsers.add_parser("threshold")
    threshold_parser.add_argument("lane_spec", type=str)
    threshold_parser.add_argument("--speed", type=int, action="append")
    threshold_parser.add_argument("--format", choices=["table", "heatmap"], default="table")
    threshold_parser.add_argument("--color-scheme", type=str, help="Color scheme name or path to config")

    # Export command
    export_parser = subparsers.add_parser("export-excel")
    export_parser.add_argument("--output", type=Path, help="Output Excel file path")
    export_parser.add_argument("--hosts", nargs="+", help="Filter by hostnames")
    export_parser.add_argument("--speeds", type=int, nargs="+", help="Filter by train speeds")
    export_parser.add_argument("--status", nargs="+", help="Filter by test status")
    export_parser.add_argument("--date-range", nargs=2, help="Filter by date range (start end)")

    # ... other subparsers

    args = parser.parse_args()

    # Initialize components
    db_path = args.db or get_default_db_path()
    db_manager = DatabaseManager(db_path)
    db_manager.initialize_schema()

    # Route to subcommand handler
    if args.command == "ingest":
        handle_ingest(db_manager, args)
    elif args.command == "stats":
        handle_stats(db_manager, args)
    elif args.command == "export-excel":
        handle_export_excel(db_manager, args)
    # ... other handlers
```

---

## Usage Examples

### Example 1: Ingest Data

```bash
# Ingest all CSV files from data directory
bh-analyze-systems ingest ./data/

# Output:
# Ingesting PRBS test data...
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 15/15 files
#
# Ingestion complete:
#   Files processed: 15
#   Rows ingested: 12,450
#   Rows filtered: 38,550 (status filter)
#   Duration: 3.2 seconds
#   Database: ~/.local/share/bh-glx-data/analysis.db
```

### Example 2: BER Statistics

```bash
# Get BER stats for all lanes on specific port
bh-analyze-systems stats "01:00.0/ETH07"

# Output:
┌─────────────────────┬───────────┬───────────┬───────────┬─────────┐
│ Lane                │ Min BER   │ Max BER   │ Avg BER   │ Samples │
├─────────────────────┼───────────┼───────────┼───────────┼─────────┤
│ 01:00.0/ETH07/lane0 │ 1.23e-12  │ 4.56e-10  │ 2.34e-11  │ 450     │
│ 01:00.0/ETH07/lane1 │ 8.90e-13  │ 3.21e-10  │ 1.87e-11  │ 450     │
│ 01:00.0/ETH07/lane2 │ 1.45e-12  │ 5.23e-10  │ 2.89e-11  │ 450     │
│ 01:00.0/ETH07/lane3 │ 9.87e-13  │ 3.78e-10  │ 2.12e-11  │ 450     │
└─────────────────────┴───────────┴───────────┴───────────┴─────────┘

Tests: 450  Systems: 12  Speeds: 100, 200
```

### Example 3: Heat Map Visualization

```bash
# Show training failures as heat map for 200G speed
bh-analyze-systems training "all" --speed 200 --format heatmap

# Output (color-coded in terminal):
Training Failures - 200G Train Speed

System: bh-glx-c02u02
  01:00.0  ETH00 [■■■■■■■■] 0  0  0  0  -  -  -  -
           ETH01 [■■■■■■■■] -  -  -  -  0  0  0  0
           ETH02 [■■■■■■■■] 0  0  2  1  -  -  -  -
           ...

System: bh-glx-c02u03
  01:00.0  ETH00 [■■■■■■■■] 0  0  0  0  -  -  -  -
           ...

■ = 0    ▨ = 1-10    ▦ = 11-50    ▧ = 50+

Tests: 1,200  Systems: 24
```

### Example 4: Interactive Shell

```bash
bh-analyze-systems shell

# Interactive session:
bh-analyze> info
Database: ~/.local/share/bh-glx-data/analysis.db
Total tests: 12,450
Unique systems: 24
Train speeds: 100, 200
Status breakdown:
  PASS: 10,234 (82.2%)
  BER_THRESHOLD_EXCEEDED: 1,876 (15.1%)
  TRAINING_FAIL: 340 (2.7%)

bh-analyze> stats 01:00.0/ETH07 --speed 200
[displays table]

bh-analyze> custom 01:00.0/* 1e-10
[displays custom threshold analysis]

bh-analyze> export excel --output my_results.xlsx
Results exported to: my_results.xlsx

bh-analyze> export excel-db --output full_database.xlsx
Database exported to: full_database.xlsx (12,450 rows, 5 sheets)

bh-analyze> exit
```

### Example 5: Custom Color Schemes

```bash
# Use built-in strict color scheme (0=green, 1+=red)
bh-analyze-systems training "all" --speed 200 --format heatmap --color-scheme strict

# Use custom color scheme from config
bh-analyze-systems threshold "01:00.0/*" --format heatmap --color-scheme relaxed

# BER statistics with sensitive color scheme
bh-analyze-systems stats "all" --format heatmap --color-scheme sensitive

# Output:
Training Failures - 200G Train Speed (strict color scheme)

System: bh-glx-c02u02
  01:00.0  ETH00 [████████] 0  0  0  0  -  -  -  -
           ETH01 [████████] -  -  -  -  0  0  0  0
           ETH02 [▓▓▓▓▓▓▓▓] 2  1  0  0  -  -  -  -
           ...

█ = 0 (green)    ▓ = 1+ (red)
```

### Example 6: Excel Database Export

```bash
# Export entire database to Excel
bh-analyze-systems export-excel --output analysis_full.xlsx

# Output:
Exporting database to Excel...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

Export complete:
  Rows exported: 12,450
  Sheets created: 5
    - Summary (statistics)
    - PRBS Tests (10,234 rows)
    - Training Failures (340 rows)
    - BER Exceeded (1,876 rows)
    - Ingestion Metadata (15 runs)
  File size: 2.3 MB
  Output: analysis_full.xlsx

# Export with filters
bh-analyze-systems export-excel \
  --output filtered_export.xlsx \
  --hosts bh-glx-c02u02 bh-glx-c02u03 \
  --speeds 200 \
  --status TRAINING_FAIL BER_THRESHOLD_EXCEEDED

# Output:
Export complete:
  Rows exported: 856 (filtered from 12,450)
  Filters applied:
    - Hosts: bh-glx-c02u02, bh-glx-c02u03
    - Speeds: 200
    - Status: TRAINING_FAIL, BER_THRESHOLD_EXCEEDED
  File size: 421 KB
  Output: filtered_export.xlsx
```

---

## Configuration

### Config File Addition

Add to `config.yaml`:

```yaml
system_analysis:
  database_path: ~/.local/share/bh-glx-data/analysis.db
  ingest:
    chunk_size: 1000  # Rows per batch
    status_filter:
      - PASS
      - BER_THRESHOLD_EXCEEDED
      - TRAINING_FAIL
  visualization:
    default_format: table
    heatmap_output: terminal  # or "html"

    # Color scheme configuration
    count_heatmap:
      default_scheme: default  # Built-in scheme name
      custom_schemes:
        strict:
          thresholds:
            - value: 0
              color: green
            - value: 1
              color: red
          default_color: red
        relaxed:
          thresholds:
            - value: 0
              color: green
            - value: 5
              color: yellow
            - value: 20
              color: orange
            - value: 100
              color: red
          default_color: red

    ber_heatmap:
      default_scheme: default  # Built-in scheme name
      custom_schemes:
        sensitive:
          thresholds:
            - value: 0
              color: green
            - value: 1e-13
              color: yellow
            - value: 1e-11
              color: orange
            - value: 1e-9
              color: red
          default_color: red
        tolerant:
          thresholds:
            - value: 0
              color: green
            - value: 1e-11
              color: yellow
            - value: 1e-9
              color: orange
            - value: 1e-7
              color: red
          default_color: red

  export:
    default_output_dir: ./exports
    include_metadata: true
    excel_formatting: true
```

---

## Testing Strategy

### Unit Tests

```
tests/unit/system_analysis/
├── test_database.py          # Database schema, CRUD operations
├── test_ingestion.py         # CSV filtering, streaming, column exclusion
├── test_query_engine.py      # Lane selection, query logic
├── test_statistics.py        # Statistical calculations
├── test_visualization.py     # Table and heatmap rendering
└── test_lane_selector.py     # Lane spec parsing
```

### Integration Tests

```
tests/integration/system_analysis/
├── test_end_to_end.py        # Full ingest + query workflow
├── test_multi_file.py        # Multiple CSV ingestion
└── test_interactive.py       # Shell commands
```

### Test Data

- Use `templates/golden_prbs.csv` as primary test fixture
- Create smaller synthetic datasets for unit tests
- Test edge cases: empty files, malformed CSV, missing columns

---

## Performance Considerations

### Expected Performance Targets

**Ingestion:**

- 10,000 rows/second streaming processing
- Target: Ingest 100,000 rows in ~10 seconds

**Queries:**

- Sub-second response for simple statistics (< 100ms)
- 1-2 seconds for complex aggregations across all systems
- Heat map generation: 2-3 seconds

**Memory:**

- Ingestion peak: < 100 MB (streaming + batch buffer)
- Query execution: < 50 MB for typical result sets
- Database file size: ~100-200 bytes per row (compressed indexes)

### Optimization Strategies

1. **Database Level:**
   - CREATE INDEX on frequently queried columns
   - Use INTEGER for categorical data (train_speed)
   - VACUUM regularly to compact database
   - Enable WAL mode for concurrent reads

2. **Query Level:**
   - Use prepared statements
   - Batch operations
   - Push filtering to SQL WHERE clauses
   - Use aggregation functions (MIN, MAX, AVG) in SQL

3. **Application Level:**
   - Connection pooling (for future multi-process support)
   - Lazy loading of visualization data
   - Cache frequently accessed metadata

---

## Error Handling

### Exception Hierarchy

```python
class SystemAnalysisError(BHGlxDataError):
    """Base exception for system analysis module."""
    pass

class DatabaseError(SystemAnalysisError):
    """Database operation failed."""
    pass

class IngestionError(SystemAnalysisError):
    """CSV ingestion failed."""
    pass

class QueryError(SystemAnalysisError):
    """Query execution failed."""
    pass

class LaneSelectorError(SystemAnalysisError):
    """Invalid lane specification."""
    pass
```

### Error Recovery

- **Database corruption:** Detect and suggest rebuild from source CSV files
- **Ingestion failures:** Log errors, continue with remaining files, report summary
- **Query failures:** Provide helpful error messages, suggest corrections
- **Missing data:** Handle NULL BER values gracefully (training failures)

---

## Future Enhancements

### Phase 1 (MVP - Current Design)

- SQLite storage
- Basic queries (stats, threshold, training)
- Table and terminal heat map output
- CLI interface
- Excel database export with filtering
- Configurable color schemes for heatmaps
- Count heatmap color customization
- BER heatmap color customization

### Phase 2 (Future)

- HTML heat map export with interactive features
- Comparison mode (compare two lane sets)
- Export to CSV/JSON formats

---

## Integration with Existing Tools

### Data Flow

```
Jira Retrieval → CSV Files → System Analysis DB

or

Quanta Extract → CSV Files → System Analysis DB
```

**Workflow Example:**

```bash
# 1. Retrieve data from Jira
bh-jira-retrieve --tickets SYS-123 SYS-456

# 2. Ingest into analysis database
bh-analyze-systems ingest data/

# 3. Analyze
bh-analyze-systems stats "all" --speed 200 --format heatmap
```

---

## Implementation Checklist

### Core Components

- [ ] Database schema and manager (`database.py`)
- [ ] Ingestion engine with streaming (`ingestion.py`)
- [ ] Query engine with lane selection (`query_engine.py`)
- [ ] Statistics module (`statistics.py`)
- [ ] Table renderer (`visualization.py`)
- [ ] CLI interface (`cli.py`)

### Visualization Features

- [ ] Heat map renderer (terminal)
- [ ] Configurable color schemes for count heatmaps
- [ ] Configurable color schemes for BER heatmaps
- [ ] Color scheme configuration loader
- [ ] Built-in color scheme presets

### Export Features

- [ ] Excel export module (`export.py`)
- [ ] Full database export to Excel
- [ ] Filtered database export (by host, speed, status, date)
- [ ] Query result export to Excel
- [ ] Excel conditional formatting (heatmap style)
- [ ] Multi-sheet Excel workbooks

### Additional Features

- [ ] Interactive shell (`interactive.py`)
- [ ] Configuration integration
- [ ] Export commands in interactive shell

### Testing & Documentation

- [ ] Unit tests (all modules)
- [ ] Integration tests (end-to-end)
- [ ] User documentation
- [ ] API documentation
- [ ] Migration guide from ad-hoc analysis

### Polish

- [ ] Error handling and validation
- [ ] Performance optimization
- [ ] Progress indicators (tqdm)
- [ ] Logging integration
- [ ] Example datasets

---

## Dependencies

### Required

- `sqlite3` (Python stdlib)
- `pandas` (already required)
- `rich` (for table rendering)
- `openpyxl` (for Excel export - already required by excel_reporting module)

### Optional

- `plotly` or `matplotlib` (HTML heat maps - Phase 2)
- `prompt_toolkit` (enhanced interactive shell - Phase 2)
- `xlsxwriter` (alternative Excel library with advanced formatting - Phase 2)

### Development

- `pytest` (already required)
- `pytest-benchmark` (performance testing)

---

## Summary

This architecture provides a robust, memory-efficient system for analyzing PRBS test data across multiple systems. Key strengths:

1. **SQLite Storage:** Efficient, zero-config database with excellent query performance
2. **Streaming Ingestion:** Handles large CSV files without excessive memory usage
3. **Flexible Query Interface:** Lane selection abstraction supports diverse query patterns
4. **Multiple Output Formats:** Tables and heat maps for different analysis needs
5. **Excel Export:** Full database export with filtering and conditional formatting
6. **Configurable Visualization:** Customizable color schemes for both count and BER heatmaps
7. **Interactive Mode:** REPL for exploratory analysis with export capabilities
8. **Consistent Design:** Follows existing package patterns and coding standards
9. **Extensible:** Clear module boundaries enable easy addition of new features

The design balances simplicity (SQLite, streaming CSV) with power (indexed queries, Excel export, configurable visualization) to deliver a practical tool for system analysis workflows.
