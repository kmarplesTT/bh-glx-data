# System Analysis Utility - Architecture Design

## Executive Summary

This document defines the architecture for a database-driven utility to analyze PRBS test data across multiple systems. The utility provides statistical analysis of Serdes lane performance, identifies systemic issues, and presents results through both tabular and visual interfaces.

**Key Design Decisions:**
- **Database**: SQLite for lightweight, serverless storage with full SQL query capabilities
- **CLI Interface**: Subcommand-based interface integrated with existing `bh-glx-data` toolchain
- **Memory Management**: Chunked CSV processing with configurable batch sizes
- **Visualization**: Terminal-based heat maps using Unicode blocks and ANSI colors

---

## 1. Data Storage Architecture

### 1.1 Database Choice: SQLite

**Rationale:**
- Zero configuration, serverless embedded database
- Full SQL query support for complex statistical aggregations
- Excellent performance for analytical workloads
- Single-file portability
- Native Python support via `sqlite3`
- Handles datasets from MBs to hundreds of GBs

### 1.2 Database Schema

```sql
-- Core test results table (normalized, filtered data)
CREATE TABLE test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- System identification
    host TEXT NOT NULL,
    bus_id TEXT NOT NULL,
    eth_port TEXT NOT NULL,

    -- Test metadata
    test_status TEXT NOT NULL,  -- PASS, BER_THRESHOLD_EXCEEDED, TRAINING_FAIL
    train_speed TEXT,
    train_mode TEXT,

    -- BER data per lane (NULL if training failed)
    acc_ber_lane0 REAL,
    acc_ber_lane1 REAL,
    acc_ber_lane2 REAL,
    acc_ber_lane3 REAL,
    acc_ber_lane4 REAL,
    acc_ber_lane5 REAL,
    acc_ber_lane6 REAL,
    acc_ber_lane7 REAL,

    -- Source tracking
    source_file TEXT NOT NULL,
    import_timestamp INTEGER NOT NULL,

    -- Indexes for query performance
    INDEX idx_port_lookup (bus_id, eth_port),
    INDEX idx_test_status (test_status),
    INDEX idx_train_speed (train_speed),
    INDEX idx_host (host)
);

-- Metadata table for tracking imports
CREATE TABLE import_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    import_timestamp INTEGER NOT NULL,
    rows_imported INTEGER NOT NULL,
    firmware_version TEXT,
    UNIQUE(source_file, import_timestamp)
);

-- Summary statistics cache (optional, for performance)
CREATE TABLE lane_statistics (
    bus_id TEXT NOT NULL,
    eth_port TEXT NOT NULL,
    lane_num INTEGER NOT NULL,
    train_speed TEXT,

    -- Statistics
    min_ber REAL,
    max_ber REAL,
    avg_ber REAL,
    ber_threshold_exceeded_count INTEGER,
    training_fail_count INTEGER,
    total_tests INTEGER,
    unique_systems INTEGER,

    last_updated INTEGER,

    PRIMARY KEY (bus_id, eth_port, lane_num, train_speed)
);
```

### 1.3 Data Filtering During Import

**Included Test Statuses:**
- `PASS`
- `BER_THRESHOLD_EXCEEDED`
- `TRAINING_FAIL`

**Excluded Columns:** (See requirements doc for full list)
- Test configuration parameters (loopback_type, max_packet_size_bytes, etc.)
- Training diagnostics (reinit_count, serdes_train_status, etc.)
- Training BER values (training_ber_lane0-7)
- TX FIR coefficients (serdes_tx_fir_lane0-7)
- Clock settings (aiclk, macclk)
- Histogram data (req_lane_error_cnt_hist, etc.)

**Result:** ~90% reduction in storage requirements

---

## 2. CLI Interface Design

### 2.1 Command Structure

Integrate as a new subcommand in the existing `bh-glx-data` CLI:

```bash
bh-analyze-serdes <command> [options]
```

### 2.2 Subcommands

#### 2.2.1 Database Management

```bash
# Initialize new database
bh-analyze-serdes init [--db-path PATH] [--force]

# Import CSV data
bh-analyze-serdes import <csv_files...> [--db-path PATH] [--batch-size N]

# Show database statistics
bh-analyze-serdes info [--db-path PATH]

# Clear database
bh-analyze-serdes clear [--db-path PATH] [--confirm]
```

#### 2.2.2 Statistical Analysis

```bash
# BER statistics for lanes
bh-analyze-serdes ber-stats <bus_id> <eth_port> [options]

Options:
  --lanes LANES              Comma-separated lane numbers (default: all)
  --train-speed SPEED        Filter by train speed (e.g., 50G, 100G)
  --format {table,heatmap}   Output format (default: table)
  --db-path PATH             Database file path
  --json                     Output as JSON

# BER threshold exceeded counts
bh-analyze-serdes ber-failures <bus_id> <eth_port> [options]

Options:
  --lanes LANES              Comma-separated lane numbers (default: all)
  --train-speed SPEED        Filter by train speed
  --format {table,heatmap}   Output format (default: table)
  --db-path PATH             Database file path

# BER exceedance analysis
bh-analyze-serdes ber-exceedance <bus_id> <eth_port> --threshold THRESHOLD [options]

Options:
  --lanes LANES              Comma-separated lane numbers (default: all)
  --train-speed SPEED        Filter by train speed
  --threshold THRESHOLD      BER threshold value (required)
  --format {table,heatmap}   Output format (default: table)
  --db-path PATH             Database file path

# Training failure counts
bh-analyze-serdes training-failures <bus_id> <eth_port> [options]

Options:
  --lanes LANES              Comma-separated lane numbers (default: all)
  --train-speed SPEED        Filter by train speed
  --format {table,heatmap}   Output format (default: table)
  --db-path PATH             Database file path

# Multi-port analysis
bh-analyze-serdes multi-port --ports PORTS [options]

Options:
  --ports PORTS              JSON file or inline JSON with port list
  --lanes LANES              Comma-separated lane numbers (default: all)
  --train-speed SPEED        Filter by train speed
  --metric {ber-stats,ber-failures,ber-exceedance,training-failures}
  --threshold THRESHOLD      BER threshold (for ber-exceedance)
  --format {table,heatmap}   Output format (default: table)
  --db-path PATH             Database file path
```

### 2.3 Configuration File Support

`~/.config/bh-glx-data/config.yaml`:

```yaml
serdes_analysis:
  db_path: ~/.local/share/bh-glx-data/serdes_analysis.db
  default_format: table
  batch_size: 10000
  heatmap:
    color_scheme: viridis
    cell_width: 8
```

---

## 3. Memory Management Strategy

### 3.1 Chunked CSV Processing

**Problem:** Large CSV files (100k+ rows) can exceed available memory

**Solution:** Stream-based processing with configurable batch sizes

```python
def import_csv_chunked(csv_path: str, db_path: str, batch_size: int = 10000):
    """
    Import CSV in chunks to manage memory usage.

    Memory usage: O(batch_size) rather than O(total_rows)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        batch = []

        for row in reader:
            # Filter by test_status
            if row['test_status'] not in ['PASS', 'BER_THRESHOLD_EXCEEDED', 'TRAINING_FAIL']:
                continue

            # Extract only needed columns
            filtered_row = extract_columns(row)
            batch.append(filtered_row)

            # Insert batch when threshold reached
            if len(batch) >= batch_size:
                cursor.executemany(INSERT_QUERY, batch)
                conn.commit()
                batch = []

        # Insert remaining rows
        if batch:
            cursor.executemany(INSERT_QUERY, batch)
            conn.commit()

    conn.close()
```

### 3.2 Database Query Optimization

**Lazy Loading:**
- Load only required lanes/speeds via SQL WHERE clauses
- Use database aggregation functions (MIN, MAX, AVG, COUNT) instead of loading raw data
- Create indexes on frequently queried columns

**Example Optimized Query:**

```sql
-- Efficient: Aggregation in database
SELECT
    lane_num,
    MIN(ber_value) as min_ber,
    MAX(ber_value) as max_ber,
    AVG(ber_value) as avg_ber,
    COUNT(DISTINCT host) as unique_systems,
    COUNT(*) as total_tests
FROM (
    SELECT 0 as lane_num, acc_ber_lane0 as ber_value, host FROM test_results
    WHERE bus_id = ? AND eth_port = ? AND acc_ber_lane0 IS NOT NULL
    UNION ALL
    SELECT 1 as lane_num, acc_ber_lane1 as ber_value, host FROM test_results
    WHERE bus_id = ? AND eth_port = ? AND acc_ber_lane1 IS NOT NULL
    -- ... repeat for lanes 2-7
) lane_data
GROUP BY lane_num;
```

### 3.3 Memory Budget

| Operation | Memory Usage | Strategy |
|-----------|-------------|----------|
| CSV Import | O(batch_size) | Chunked processing, default 10k rows |
| BER Statistics Query | O(lanes × systems) | Database aggregation |
| Heat Map Rendering | O(ports × lanes) | Terminal buffer only |
| Multi-Port Analysis | O(ports × lanes) | Paginated output |

**Maximum Memory Footprint:** < 100 MB for typical workloads

---

## 4. Data Model

### 4.1 Core Domain Models

```python
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

@dataclass
class SerdesLaneIdentifier:
    """Uniquely identifies a Serdes lane."""
    bus_id: str
    eth_port: str
    lane_num: int  # 0-7

    def __str__(self) -> str:
        return f"{self.bus_id}:{self.eth_port}:lane{self.lane_num}"

@dataclass
class BERStatistics:
    """BER statistics for a single lane."""
    lane_id: SerdesLaneIdentifier
    train_speed: Optional[str]

    # Statistics
    min_ber: float
    max_ber: float
    avg_ber: float

    # Context
    total_tests: int
    unique_systems: int

    # Failure counts
    ber_threshold_exceeded_count: int
    training_fail_count: int

@dataclass
class LaneAnalysisResult:
    """Multi-lane analysis result."""
    bus_id: str
    eth_port: str
    train_speed: Optional[str]
    lane_statistics: List[BERStatistics]

    # Metadata
    total_systems_tested: int
    total_tests_conducted: int

class OutputFormat(Enum):
    """Supported output formats."""
    TABLE = "table"
    HEATMAP = "heatmap"
    JSON = "json"

class AnalysisMetric(Enum):
    """Analysis metric types."""
    BER_STATISTICS = "ber-stats"
    BER_FAILURES = "ber-failures"
    BER_EXCEEDANCE = "ber-exceedance"
    TRAINING_FAILURES = "training-failures"
```

### 4.2 Repository Pattern

```python
class SerdesAnalysisRepository:
    """Data access layer for Serdes analysis."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)

    def get_ber_statistics(
        self,
        bus_id: str,
        eth_port: str,
        lanes: Optional[List[int]] = None,
        train_speed: Optional[str] = None
    ) -> LaneAnalysisResult:
        """Retrieve BER statistics for specified lanes."""
        pass

    def get_ber_failure_counts(
        self,
        bus_id: str,
        eth_port: str,
        lanes: Optional[List[int]] = None,
        train_speed: Optional[str] = None
    ) -> Dict[int, int]:
        """Count BER_THRESHOLD_EXCEEDED occurrences per lane."""
        pass

    def get_ber_exceedance_counts(
        self,
        bus_id: str,
        eth_port: str,
        threshold: float,
        lanes: Optional[List[int]] = None,
        train_speed: Optional[str] = None
    ) -> Dict[int, int]:
        """Count tests where BER exceeded threshold."""
        pass

    def get_training_failure_counts(
        self,
        bus_id: str,
        eth_port: str,
        lanes: Optional[List[int]] = None,
        train_speed: Optional[str] = None
    ) -> Dict[int, int]:
        """Count TRAINING_FAIL occurrences per lane."""
        pass
```

---

## 5. Visualization System

### 5.1 Table Output

**ASCII Table Format:**

```
BER Statistics for 01:00.0 ETH07 (Train Speed: 50G)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Lane  Min BER      Max BER      Avg BER      Failures  Tests  Systems
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  0   1.23e-12     4.56e-09     2.34e-11        3      1250     45
  1   9.87e-13     3.21e-09     1.89e-11        2      1250     45
  2   1.45e-12     5.67e-09     2.78e-11        5      1250     45
  3   1.11e-12     4.22e-09     2.45e-11        4      1250     45
  4   8.90e-13     2.98e-09     1.67e-11        1      1250     45
  5   1.34e-12     4.89e-09     2.56e-11        4      1250     45
  6   1.56e-12     6.12e-09     3.01e-11        7      1250     45
  7   1.02e-12     3.78e-09     2.12e-11        3      1250     45
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Tests: 10,000 | Systems Tested: 45
```

**Implementation:** `rich` library for formatting

### 5.2 Heat Map Output

**Terminal-Based Heat Map:**

```
BER Failure Heat Map (01:00.0 - 08:00.0, All Lanes)

Port    Lane 0  Lane 1  Lane 2  Lane 3  Lane 4  Lane 5  Lane 6  Lane 7
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
01:00.0   3█      2█      5█      4█      1█      4█      7█      3█
02:00.0   2█      1█      3█      2█      0       2█      4█      1█
03:00.0   4█      3█      6█      5█      2█      5█      8█      4█
04:00.0   1█      1█      2█      1█      0       1█      3█      1█
05:00.0   3█      2█      4█      3█      1█      3█      6█      2█
06:00.0   2█      2█      3█      2█      1█      2█      5█      2█
07:00.0   5█      4█      7█      6█      3█      6█      9█      5█
08:00.0   1█      0       2█      1█      0       1█      2█      1█

Color Scale: █ = 0 failures  █ = 1-3  █ = 4-6  █ = 7+
```

**Features:**
- ANSI color codes for gradient (green → yellow → red)
- Unicode block characters for visual density
- Configurable color schemes (viridis, plasma, grayscale)

**Implementation:** Custom renderer with `colorama` for cross-platform support

### 5.3 JSON Output

```json
{
  "bus_id": "01:00.0",
  "eth_port": "ETH07",
  "train_speed": "50G",
  "total_systems_tested": 45,
  "total_tests_conducted": 10000,
  "lane_statistics": [
    {
      "lane_num": 0,
      "min_ber": 1.23e-12,
      "max_ber": 4.56e-09,
      "avg_ber": 2.34e-11,
      "ber_threshold_exceeded_count": 3,
      "training_fail_count": 0,
      "total_tests": 1250,
      "unique_systems": 45
    }
    // ... lanes 1-7
  ]
}
```

---

## 6. Implementation Modules

### 6.1 Package Structure

```
src/bh_glx_data/
└── serdes_analysis/          # New module
    ├── __init__.py
    ├── cli.py                # CLI entry points
    ├── database.py           # Database schema and initialization
    ├── repository.py         # Data access layer
    ├── importer.py           # CSV import with chunking
    ├── analyzer.py           # Analysis logic
    ├── visualizer.py         # Table and heat map rendering
    └── models.py             # Domain models
```

### 6.2 Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `cli.py` | Argument parsing, command dispatch |
| `database.py` | Schema creation, migrations, DB utilities |
| `repository.py` | SQL queries, data retrieval |
| `importer.py` | CSV chunked import, column filtering |
| `analyzer.py` | Statistical calculations, aggregations |
| `visualizer.py` | Table/heat map rendering, formatting |
| `models.py` | Data classes, enums, type definitions |

---

## 7. Performance Characteristics

### 7.1 Expected Performance

| Operation | Dataset Size | Time | Memory |
|-----------|-------------|------|--------|
| CSV Import (chunked) | 100k rows | ~5s | <50 MB |
| BER Statistics Query | Single port, all lanes | <100ms | <10 MB |
| Multi-Port Heat Map | 32 ports × 8 lanes | <500ms | <20 MB |
| Database Size | 1M test results | ~200 MB | N/A |

### 7.2 Scalability

- **SQLite limitations:** Up to ~140 TB database size (practical limit ~1 TB)
- **Expected dataset:** 10k-100k rows per system, 100-1000 systems = 1M-100M rows
- **Indexing:** Critical for performance at >10M rows
- **Archival:** Implement data retention policies for very large datasets

---

## 8. Future Enhancements

### 8.1 Phase 2 Features

1. **Web Dashboard:** Flask/FastAPI web UI with interactive charts (Plotly)
2. **Comparative Analysis:** Compare performance across firmware versions
3. **Anomaly Detection:** ML-based identification of outlier lanes
4. **Export Formats:** PDF reports, Excel exports
5. **Time-Series Analysis:** Track BER trends over time
6. **Alerting:** Email/Slack notifications for threshold violations

### 8.2 Advanced Queries

1. **Cross-System Correlation:** Identify lanes with consistent issues
2. **Topology Integration:** Map failures to physical cable connections
3. **Statistical Tests:** Chi-square tests for systematic issues
4. **Regression Analysis:** Predict failure likelihood

---

## 9. Success Criteria

### 9.1 Functional Requirements

- ✓ Import CSV data with 90%+ storage reduction
- ✓ Query BER statistics for any lane/port combination
- ✓ Generate failure counts by category
- ✓ Support train_speed filtering
- ✓ Produce table and heat map visualizations
- ✓ Handle 100k+ row datasets without memory issues

### 9.2 Non-Functional Requirements

- **Performance:** Queries complete in <1 second for typical datasets
- **Usability:** CLI matches existing `bh-glx-data` conventions
- **Reliability:** Data integrity guarantees (ACID transactions)
- **Maintainability:** 80%+ test coverage, type hints, documentation
- **Portability:** Single SQLite file, zero server dependencies

---

## 10. Implementation Plan

### Phase 1: Core Infrastructure (Week 1)
1. Database schema definition
2. CSV importer with chunking
3. Repository pattern implementation
4. Basic CLI framework

### Phase 2: Analysis Engine (Week 2)
1. BER statistics queries
2. Failure count queries
3. Threshold exceedance analysis
4. Train speed filtering

### Phase 3: Visualization (Week 3)
1. Table renderer with `rich`
2. Heat map renderer with ANSI colors
3. JSON output format
4. Multi-port analysis

### Phase 4: Testing & Documentation (Week 4)
1. Unit tests (>80% coverage)
2. Integration tests
3. User documentation
4. Example workflows

---

## Appendix A: Technology Stack

- **Database:** SQLite 3.35+ (JSON support)
- **CLI Framework:** `argparse` (stdlib)
- **Table Rendering:** `rich` library
- **Color Output:** `colorama` for cross-platform
- **Data Processing:** `pandas` for CSV chunking (optional)
- **Testing:** `pytest`, `pytest-cov`
- **Type Checking:** `mypy`

## Appendix B: Database Size Estimation

**Assumptions:**
- 100 systems
- 2 firmware versions each
- 128 ports per system (32 bus_id × 4 eth_port avg)
- 50 test iterations per port
- ~30 columns retained after filtering

**Calculation:**
- Rows: 100 × 2 × 128 × 50 = 1,280,000 rows
- Size per row: ~150 bytes (text + floats)
- Total: ~192 MB database

**With indexes:** ~250 MB total

## Appendix C: SQL Query Examples

See implementation for complete query catalog. Key patterns:

1. **Unpivot lanes for aggregation** (UNION ALL pattern)
2. **Filter NULL BER values** (exclude TRAINING_FAIL)
3. **Use COUNT(DISTINCT host)** for system counts
4. **Index foreign keys** for join performance
