# bh-analyze-systems User Guide

A database utility for collecting, storing, and analyzing PRBS test data across multiple systems. This tool provides efficient query capabilities with visualization options for identifying serdes lane performance patterns.

**Version:** 0.6.0
**Purpose:** Aggregate PRBS test data from CSV files with memory-efficient storage and interactive analysis

---

## What's New in Version 0.6.0

Version 0.6.0 introduces powerful new analysis capabilities and improves variance visualization:

- **Histogram Analysis** - New `histogram` command displays BER distribution across logarithmic bins, helping identify whether failures are clustered at specific BER levels or spread across ranges
- **Advanced Statistics** - New `advanced-stats` command computes per-host BER statistics and then aggregates them fleet-wide, revealing performance consistency across multiple systems
- **Extended Lane Selection** - Lane specifications now support specific lane numbers (e.g., `01:00.0/ETH07/4` for lane 4), enabling targeted single-lane analysis
- **Improved Variance Display** - The `--statistic avg` option now always shows variance indicators by default (replaces the old `variance` option)

**Breaking Change:** The `--statistic variance` option has been renamed to `avg`. Users previously using `--statistic variance` should switch to `--statistic avg`, which now always includes variance indicators.

### Version 0.5.0 Highlights

- **Variance Visualization** - Average BER heatmaps display variance symbols (shape) alongside BER magnitude (color) to show both performance and consistency
- **Five Variance Levels** - Symbols indicate consistency: `●` (very consistent), `◆` (consistent), `▲` (moderate variance), `■` (high variance), `✕` (extreme spikes)
- **Single-Glance Diagnostics** - Quickly identify persistent hardware issues vs. intermittent environmental problems

### Version 0.4.0 Highlights

- **High BER Field** - BER values >= 0.1 are now tracked separately in a "High BER" column, providing clearer visibility into severely degraded lanes
- **Column Order Changed** - Statistics now display in [Min, Avg, Max, High BER] order for better readability
- **Training Failures Always Excluded** - Training failures are automatically excluded from BER calculations (they don't produce valid BER data)
- **Heatmap Statistic Selection** - New `--statistic` option allows choosing which statistic to visualize: `avg`, `min`, `max`, or `high_ber` (default: `max`)
- **Fixed Color Scheme Logic** - Thresholds now work correctly as upper bounds, ensuring consistent color mapping
- **Enhanced Color Schemes** - All predefined color schemes now include "orange" between yellow and red for better visual gradation

---

## Quick Start

Get started in 5 minutes:

```bash
# 1. Ingest CSV data into the database
bh-analyze-systems ingest ./data/

# 2. View database summary
bh-analyze-systems info

# 3. Query BER statistics for all systems
bh-analyze-systems stats all --speed 200

# 4. Visualize training failures as a heatmap
bh-analyze-systems training all --speed 200 --format heatmap

# 5. Export results to Excel
bh-analyze-systems export-excel --output my_analysis.xlsx
```

---

## Installation

The tool is included in the BH Galaxy Data Analysis Tool package. Follow the installation instructions in the main [README.md](../../README.md).

After installation, the `bh-analyze-systems` command will be available in your PATH when the virtual environment is activated:

```bash
source .venv/bin/activate
bh-analyze-systems --help
```

---

## Basic Concepts

### Database

The tool uses SQLite to store test data in an efficient, indexed database. By default, the database is stored at:

```
~/.local/share/bh-glx-data/analysis.db
```

You can specify a custom location with the `--db` option:

```bash
bh-analyze-systems --db /path/to/custom.db <command>
```

### Lane Selection

Lanes are specified using a flexible syntax that supports system, bus ID, ETH port, and individual lane selection:

- `all` - All lanes on all systems
- `01:00.0/ETH07` - Specific port, all 8 lanes
- `01:00.0/ETH07/4` - Specific lane 4 on specific port
- `01:00.0/*` - All ports on a bus ID
- `bh-glx-c02u02/01:00.0/ETH07` - Specific system and port
- `bh-glx-c02u02/01:00.0/ETH07/4` - Specific lane on specific system
- `bh-glx-c02u02/*` - All ports on a system
- `*/ETH07` - ETH07 on all systems
- `*/ETH07/4` - Lane 4 on ETH07 across all systems

**New in v0.6.0:** Lane numbers (0-7) can now be specified as a fourth component in the lane specification. This enables targeted analysis of individual serdes lanes.

### Query Types

The tool provides several types of queries:

1. **BER Statistics** - Min, avg, max, and high BER (>= 0.1) counts per lane
2. **Threshold Exceeded** - Count of BER_THRESHOLD_EXCEEDED test status occurrences
3. **Custom Threshold** - Count of lanes exceeding a custom BER threshold
4. **Training Failures** - Count of TRAINING_FAIL test status occurrences

**Note:** Training failures (TRAINING_FAIL status) are always excluded from BER calculations since they don't produce valid BER data. BER values >= 0.1 are counted separately as "high BER" and excluded from min/avg/max calculations in the BER Statistics query.

---

## Command Reference

### Global Options

Available for all commands:

```bash
bh-analyze-systems [OPTIONS] <command> [COMMAND_OPTIONS]
```

**Options:**

- `--db PATH` - Specify database path (default: `~/.local/share/bh-glx-data/analysis.db`)
- `--verbose, -v` - Enable verbose logging
- `--log-level LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--help` - Show help message

---

### ingest

Ingest CSV files into the database. This is typically the first command you run.

```bash
bh-analyze-systems ingest <input_dir> [OPTIONS]
```

**Arguments:**

- `input_dir` - Directory containing PRBS test CSV files

**Options:**

- `--status-filter STATUS [STATUS ...]` - Test status values to include (default: PASS BER_THRESHOLD_EXCEEDED TRAINING_FAIL)

**Example:**

```bash
# Ingest all CSV files from data directory
bh-analyze-systems ingest ./data/

# Output:
# Ingesting PRBS test data from ./data/...
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 15/15 files
#
# Ingestion complete:
#   Files processed: 15
#   Rows ingested: 12,450
#   Rows filtered: 38,550 (status filter)
#   Duration: 3.2 seconds
#   Database: ~/.local/share/bh-glx-data/analysis.db
```

**What it does:**

1. Discovers all CSV files in the input directory
2. Streams CSV data in chunks (memory efficient)
3. Filters rows by test_status (includes only specified statuses)
4. Batch inserts data into SQLite database
5. Records ingestion metadata for provenance

**Notes:**

- Ingestion is incremental - you can run it multiple times
- Large files are processed in chunks to avoid memory issues
- Progress bar shows ingestion status

---

### stats

Show BER statistics (min, avg, max, high BER) for specified lanes.

```bash
bh-analyze-systems stats <lane_spec> [OPTIONS]
```

**Arguments:**

- `lane_spec` - Lane specification (see Lane Selection Syntax)

**Options:**

- `--speed SPEED` - Filter by train speed (can be specified multiple times)
- `--format {table|heatmap}` - Output format (default: table)
- `--statistic {avg|min|max|high_ber}` - Statistic to display in heatmap (default: max; avg includes variance indicators)
- `--color-scheme SCHEME` - Color scheme for heatmap (default, sensitive, tolerant)

**Example (Table Format):**

```bash
bh-analyze-systems stats "01:00.0/ETH07" --speed 200

# Output:
┌─────────────────────┬───────────┬───────────┬───────────┬──────────┬─────────┐
│ Lane                │ Min       │ Avg       │ Max       │ High BER │ Samples │
├─────────────────────┼───────────┼───────────┼───────────┼──────────┼─────────┤
│ 01:00.0/ETH07/lane0 │ 1.23e-12  │ 2.34e-11  │ 4.56e-10  │ 5        │ 450     │
│ 01:00.0/ETH07/lane1 │ 8.90e-13  │ 1.87e-11  │ 3.21e-10  │ -        │ 450     │
│ 01:00.0/ETH07/lane2 │ 1.45e-12  │ 2.89e-11  │ 5.23e-10  │ -        │ 450     │
│ 01:00.0/ETH07/lane3 │ 9.87e-13  │ 2.12e-11  │ 3.78e-10  │ 2        │ 450     │
└─────────────────────┴───────────┴───────────┴───────────┴──────────┴─────────┘

Tests: 450  Systems: 12  Speeds: 200
```

**Column Definitions:**

- **Min** - Minimum BER value (excludes high BER >= 0.1 and training failures)
- **Avg** - Average BER value (excludes high BER >= 0.1 and training failures)
- **Max** - Maximum BER value (excludes high BER >= 0.1 and training failures)
- **High BER** - Count of samples with BER >= 0.1 (shown as "-" if zero)
- **Samples** - Total number of test samples (includes all tests except training failures)

**Example (Heatmap Format):**

```bash
# Display heatmap of maximum BER values (default)
bh-analyze-systems stats all --speed 200 --format heatmap

# Display heatmap of average BER values
bh-analyze-systems stats all --speed 200 --format heatmap --statistic avg

# Display heatmap of minimum BER values
bh-analyze-systems stats all --speed 200 --format heatmap --statistic min

# Display heatmap of high BER counts
bh-analyze-systems stats all --speed 200 --format heatmap --statistic high_ber
```

Displays a color-coded heatmap with BER values across all systems and lanes.

**Heatmap Statistic Options:**

- `max` (default) - Display maximum BER values in heatmap
- `avg` - Display average BER values with variance indicators (symbols show consistency: ●, ◆, ▲, ■, ✕)
- `min` - Display minimum BER values in heatmap
- `high_ber` - Display count of high BER (>= 0.1) occurrences in heatmap

**Notes:**

- Training failures are always excluded from BER calculations (no valid BER data)
- BER values >= 0.1 are counted as "high BER" and excluded from min/avg/max
- Multiple speeds can be specified: `--speed 100 --speed 200`
- Heatmap colors indicate BER levels (green=low, yellow=moderate, orange=elevated, red=high)
- The `--statistic` option only affects heatmap format (table format shows all statistics)

---

### threshold

Show count of BER_THRESHOLD_EXCEEDED occurrences per lane.

```bash
bh-analyze-systems threshold <lane_spec> [OPTIONS]
```

**Arguments:**

- `lane_spec` - Lane specification

**Options:**

- `--speed SPEED` - Filter by train speed
- `--format {table|heatmap}` - Output format (default: table)
- `--color-scheme SCHEME` - Color scheme for heatmap

**Example:**

```bash
bh-analyze-systems threshold "01:00.0/*" --speed 200

# Output:
┌─────────────────────┬───────┐
│ Lane                │ Count │
├─────────────────────┼───────┤
│ 01:00.0/ETH00/lane0 │ 0     │
│ 01:00.0/ETH00/lane1 │ 0     │
│ 01:00.0/ETH01/lane0 │ 2     │
│ 01:00.0/ETH01/lane1 │ 1     │
└─────────────────────┴───────┘

Tests: 1,200  Systems: 24  Speeds: 200
```

**Use Cases:**

- Identify lanes with frequent threshold violations
- Compare failure rates across systems
- Detect patterns in failing lanes

---

### custom

Show count of lanes exceeding a custom BER threshold.

```bash
bh-analyze-systems custom <lane_spec> <threshold> [OPTIONS]
```

**Arguments:**

- `lane_spec` - Lane specification
- `threshold` - Custom BER threshold (e.g., 1e-10)

**Options:**

- `--speed SPEED` - Filter by train speed
- `--format {table|heatmap}` - Output format (default: table)
- `--color-scheme SCHEME` - Color scheme for heatmap

**Example:**

```bash
# Count lanes exceeding 1e-10 BER
bh-analyze-systems custom "all" 1e-10 --speed 200

# Count with more strict threshold
bh-analyze-systems custom "01:00.0/*" 1e-12 --speed 200
```

**Use Cases:**

- Apply stricter BER requirements than test defaults
- Analyze marginal lanes that pass but are close to threshold
- Custom quality control criteria

---

### training

Show count of TRAINING_FAIL occurrences per lane.

```bash
bh-analyze-systems training <lane_spec> [OPTIONS]
```

**Arguments:**

- `lane_spec` - Lane specification

**Options:**

- `--speed SPEED` - Filter by train speed
- `--format {table|heatmap}` - Output format (default: table)
- `--color-scheme SCHEME` - Color scheme for heatmap

**Example:**

```bash
# Show training failures across all systems
bh-analyze-systems training all --speed 200 --format heatmap

# Output (color-coded in terminal):
Training Failures - 200G Train Speed

System: bh-glx-c02u02
  01:00.0  ETH00 [■■■■■■■■] 0  0  0  0  -  -  -  -
           ETH01 [■■■■■■■■] -  -  -  -  0  0  0  0
           ETH02 [■■■■■■■■] 0  0  2  1  -  -  -  -
           ...

■ = 0    ▨ = 1-10    ▦ = 11-50    ▧ = 50+

Tests: 1,200  Systems: 24
```

**Use Cases:**

- Identify lanes with link training issues
- Detect systematic training problems across systems
- Compare training reliability by speed

---

### histogram

Show BER distribution histogram for specific lane(s).

```bash
bh-analyze-systems histogram <lane_spec> [OPTIONS]
```

**Arguments:**

- `lane_spec` - Lane specification (supports single lane or all lanes on a port)

**Options:**

- `--speed SPEED` - Filter by train speed
- `--max-bar-width WIDTH` - Maximum width of histogram bars in characters (default: 50)

**Example (Single Lane):**

```bash
# Show histogram for a specific lane
bh-analyze-systems histogram 01:00.0/ETH07/4 --speed 200

# Output:
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

**Example (All Lanes on Port):**

```bash
# Show histograms for all 8 lanes on a port
bh-analyze-systems histogram 01:00.0/ETH07 --speed 200

# Output:
BER Histograms - 01:00.0/ETH07 (all lanes)

Lane 0:
  < 1e-12   ████████████████████████████ 145
  1e-12-11  ██████████████ 72
  1e-11-10  ████████ 42
  [... additional bins ...]

Lane 1:
  < 1e-12   ███████████████████████ 120
  1e-12-11  ████████████ 65
  1e-11-10  ██████ 38
  [... additional bins ...]

[... lanes 2-7 ...]

Total Samples: 2408  |  Systems: 5  |  Speeds: 200
```

**Histogram Bins:**

The histogram uses 10 logarithmic bins to categorize BER values:

- `< 1e-12` - Excellent performance
- `1e-12 to 1e-11` - Very good
- `1e-11 to 1e-10` - Good
- `1e-10 to 1e-9` - Acceptable
- `1e-9 to 1e-8` - Marginal
- `1e-8 to 1e-7` - Poor
- `1e-7 to 1e-6` - Very poor
- `1e-6 to 1e-5` - Critical
- `1e-5 to 1e-4` - Severe
- `>= 1e-4` - Failed

**Visualization:**

- Bars are color-coded using the BER color scheme (green for low, red for high)
- Bar length is proportional to the count (scaled to max_bar_width)
- Exact count is displayed next to each bar
- Separate histogram displayed for each lane when multiple lanes are queried

**Use Cases:**

- Understand BER distribution patterns for a specific lane
- Identify if failures cluster at specific BER levels or spread across ranges
- Compare BER distributions across different lanes on the same port
- Diagnose whether issues are consistent (single bin) or variable (multiple bins)
- Spot bimodal distributions indicating intermittent problems

**Tips:**

- Single-lane histograms (e.g., `01:00.0/ETH07/4`) are best for detailed analysis
- Port-level histograms (e.g., `01:00.0/ETH07`) show all 8 lanes for comparison
- Use `--speed` to focus on specific training speeds
- Look for unexpected bins - e.g., if most samples are in excellent range but some are critical, investigate intermittent issues

---

### advanced-stats

Show aggregated host statistics with fleet-wide performance consistency analysis.

```bash
bh-analyze-systems advanced-stats <lane_spec> [OPTIONS]
```

**Arguments:**

- `lane_spec` - Lane specification

**Options:**

- `--speed SPEED` - Filter by train speed

**Example:**

```bash
# Show advanced statistics for a specific lane
bh-analyze-systems advanced-stats 01:00.0/ETH07/4 --speed 200

# Output:
Per-Host Statistics - 01:00.0/ETH07/lane4
┌────────────────┬──────────┬──────────┬──────────┬─────────┐
│ Host           │ Min BER  │ Avg BER  │ Max BER  │ Samples │
├────────────────┼──────────┼──────────┼──────────┼─────────┤
│ bh-glx-c02u02  │ 1.00e-12 │ 2.00e-11 │ 3.00e-10 │ 150     │
│ bh-glx-c03u02  │ 5.00e-13 │ 1.00e-11 │ 5.00e-10 │ 151     │
└────────────────┴──────────┴──────────┴──────────┴─────────┘

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

**How It Works:**

The command performs two-level aggregation:

1. **First Level (Per-Host Statistics):**
  - For each system, calculate min/avg/max BER across all test samples for the specified lane
  - Display in the "Per-Host Statistics" table
2. **Second Level (Statistics of Statistics):**
  - Take the per-host min values and calculate min/avg/max of those values
  - Take the per-host avg values and calculate min/avg/max of those values
  - Take the per-host max values and calculate min/avg/max of those values
  - Display in the "Statistics of Host Statistics" table

**Interpreting Results:**

The "Statistics of Host Statistics" table reveals fleet-wide performance patterns:

- **MIN row** - Shows the range of best-case performance across systems
  - Narrow range (min≈max) = Consistent best-case performance
  - Wide range (min<<max) = Some systems perform much better than others at their best
- **AVG row** - Shows the range of typical performance across systems
  - Narrow range = All systems perform similarly on average
  - Wide range = Significant variation in typical performance across fleet
- **MAX row** - Shows the range of worst-case performance across systems
  - Narrow range = Worst-case behavior is consistent
  - Wide range = Some systems experience much worse spikes than others

**Use Cases:**

- Assess performance consistency across a fleet of systems
- Identify outlier systems with consistently better or worse performance
- Determine if BER issues are systemic (all systems) or isolated (specific systems)
- Compare fleet-wide performance across different lanes or speeds
- Prioritize systems for investigation based on worst-case performance

**Example Interpretations:**

**Scenario 1: Consistent Fleet**

```
MIN: min=1e-12, avg=1.1e-12, max=1.2e-12
AVG: min=2e-11, avg=2.1e-11, max=2.2e-11
MAX: min=3e-10, avg=3.2e-10, max=3.5e-10
```

Interpretation: All systems perform very similarly. Narrow ranges in all metrics indicate consistent hardware quality and environmental conditions.

**Scenario 2: Outlier System**

```
MIN: min=5e-13, avg=1e-12, max=5e-12
AVG: min=1e-11, avg=2e-11, max=8e-11
MAX: min=3e-10, avg=4e-10, max=2e-09
```

Interpretation: Wide ranges suggest one or more outlier systems. The system with max=2e-09 should be investigated for hardware or environmental issues.

**Scenario 3: Variable Performance**

```
MIN: min=1e-12, avg=1.1e-12, max=1.2e-12
AVG: min=2e-11, avg=2.2e-11, max=2.4e-11
MAX: min=5e-10, avg=8e-10, max=5e-09
```

Interpretation: Good consistency in typical performance (MIN and AVG), but wide range in MAX suggests some systems experience occasional severe spikes. This could indicate environmental sensitivity (temperature, power, cables).

**Tips:**

- Use this command after identifying problem lanes with standard `stats` command
- Compare results across different speeds to see if consistency changes with speed
- Look at the Per-Host Statistics table to identify specific outlier systems
- Narrow ranges indicate good fleet consistency; wide ranges suggest investigation needed
- Use with `*/ETH07/4` to analyze the same lane across all systems

---

### info

Show database information and statistics.

```bash
bh-analyze-systems info
```

**Example:**

```bash
bh-analyze-systems info

# Output:
Database Information:
  Database: ~/.local/share/bh-glx-data/analysis.db
  Total tests: 12,450
  Unique systems: 24
  Train speeds: 100, 200
  Date range: 2026-01-15 to 2026-03-10

  Status breakdown:
    PASS: 10,234 (82.2%)
    BER_THRESHOLD_EXCEEDED: 1,876 (15.1%)
    TRAINING_FAIL: 340 (2.7%)

  Total ingestions: 15
```

**Use Cases:**

- Verify database contents
- Check data coverage (systems, speeds, dates)
- Understand test result distribution

---

### export-excel

Export database contents to Excel format.

```bash
bh-analyze-systems export-excel [OPTIONS]
```

**Options:**

- `--output PATH` - Output Excel file path (default: database_export.xlsx)
- `--hosts HOST [HOST ...]` - Filter by hostnames
- `--speeds SPEED [SPEED ...]` - Filter by train speeds
- `--status STATUS [STATUS ...]` - Filter by test status
- `--date-range START END` - Filter by date range (YYYY-MM-DD YYYY-MM-DD)

**Example (Full Export):**

```bash
bh-analyze-systems export-excel --output full_analysis.xlsx

# Output:
Exporting database to Excel...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

Export complete:
  Rows exported: 12,450
  Sheets created: 5
  File size: 2.3 MB
  Output: full_analysis.xlsx
```

**Example (Filtered Export):**

```bash
# Export only specific systems and failures
bh-analyze-systems export-excel \
  --output failures.xlsx \
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
  Output: failures.xlsx
```

**Excel Sheets:**

1. **Summary** - Database statistics and metadata
2. **PRBS Tests** - All test records (or filtered subset)
3. **Training Failures** - Filtered view of training failures
4. **BER Exceeded** - Filtered view of BER threshold exceeded
5. **Metadata** - Ingestion history

**Use Cases:**

- Share analysis results with team
- Further analysis in Excel (pivot tables, charts)
- Archive test data snapshots
- Offline analysis

---

### shell

Start interactive analysis shell (REPL mode).

```bash
bh-analyze-systems shell
```

**Example Session:**

```bash
bh-analyze-systems shell

# Interactive prompt:
bh-analyze> help
Available commands:
  stats <lane-spec> [--speed SPEED]           - Show BER statistics
  threshold <lane-spec> [--speed SPEED]       - Show BER threshold exceeded
  custom <lane-spec> <threshold> [--speed]    - Show custom threshold counts
  training <lane-spec> [--speed SPEED]        - Show training failures
  systems                                      - List all systems
  speeds                                       - List all train speeds
  info                                         - Show database info
  export <format> [--output FILE]              - Export last result
  help                                         - Show this help
  exit                                         - Exit shell

bh-analyze> info
Database: ~/.local/share/bh-glx-data/analysis.db
Total tests: 12,450
Unique systems: 24
...

bh-analyze> stats 01:00.0/ETH07 --speed 200
[displays BER statistics table]

bh-analyze> training all --speed 200
[displays training failure counts]

bh-analyze> export excel --output my_results.xlsx
Results exported to: my_results.xlsx

bh-analyze> exit
```

**Shell Commands:**

- `stats` - Same as CLI stats command
- `threshold` - Same as CLI threshold command
- `custom` - Same as CLI custom command
- `training` - Same as CLI training command
- `systems` - List all system hostnames in database
- `speeds` - List all train speeds in database
- `info` - Display database information
- `export <format>` - Export last query result or full database
- `help` - Show available commands
- `exit` - Exit shell

**Export Formats:**

- `csv` - Export to CSV format
- `excel` - Export to Excel with formatting
- `excel-db` - Export entire database to Excel

**Use Cases:**

- Exploratory data analysis
- Multiple queries without reloading database
- Quick iteration on analysis queries
- Interactive troubleshooting sessions

---

## Lane Selection Syntax

The lane selection syntax allows flexible queries across systems, ports, and lanes.

### Syntax Patterns


| Pattern                     | Description                      | Example                         |
| --------------------------- | -------------------------------- | ------------------------------- |
| `all`                       | All lanes on all systems         | `all`                           |
| `BUS_ID/ETH_PORT`           | Specific port, all lanes         | `01:00.0/ETH07`                 |
| `BUS_ID/ETH_PORT/LANE`      | Specific lane on port            | `01:00.0/ETH07/4`               |
| `BUS_ID/`*                  | All ports on bus ID              | `01:00.0/*`                     |
| `HOST/BUS_ID/ETH_PORT`      | Specific system and port         | `bh-glx-c02u02/01:00.0/ETH07`   |
| `HOST/BUS_ID/ETH_PORT/LANE` | Specific lane on system          | `bh-glx-c02u02/01:00.0/ETH07/4` |
| `HOST/*`                    | All ports on system              | `bh-glx-c02u02/*`               |
| `*/ETH_PORT`                | Specific port on all systems     | `*/ETH07`                       |
| `*/ETH_PORT/LANE`           | Specific lane across all systems | `*/ETH07/4`                     |


**New in v0.6.0:** Lane numbers (0-7) can be specified as the fourth component to target individual serdes lanes.

### Examples

```bash
# Query all lanes everywhere
bh-analyze-systems stats all

# Query specific port (8 lanes)
bh-analyze-systems stats "01:00.0/ETH07"

# Query specific lane on port (NEW in v0.6.0)
bh-analyze-systems stats "01:00.0/ETH07/4"

# Query all ports on a bus ID
bh-analyze-systems stats "01:00.0/*"

# Query specific system
bh-analyze-systems stats "bh-glx-c02u02/*"

# Query same port across all systems
bh-analyze-systems stats "*/ETH07"

# Query same lane across all systems (NEW in v0.6.0)
bh-analyze-systems stats "*/ETH07/4"

# Query with specific system and port
bh-analyze-systems stats "bh-glx-c02u02/01:00.0/ETH07"

# Query specific lane on specific system (NEW in v0.6.0)
bh-analyze-systems stats "bh-glx-c02u02/01:00.0/ETH07/4"
```

### Lane Numbering

Each ETH port has 8 serdes lanes numbered 0-7:

- `lane0`, `lane1`, `lane2`, `lane3` - First 4 lanes
- `lane4`, `lane5`, `lane6`, `lane7` - Second 4 lanes

Queries return results for all 8 lanes per port unless a specific lane number is specified.

**New in v0.6.0:** You can target individual lanes by adding a lane number (0-7) to the specification:

```bash
# Query single lane
bh-analyze-systems stats "01:00.0/ETH07/4"
bh-analyze-systems histogram "01:00.0/ETH07/4" --speed 200

# Query same lane across all systems
bh-analyze-systems advanced-stats "*/ETH07/4" --speed 200
```

---

## Visualization Options

### Table Format

Default output format showing data in tabular form.

**Features:**

- Clear column headers
- Aligned numeric values
- Summary statistics at bottom
- Easy to read in terminal

**Best For:**

- Detailed numeric analysis
- Exact values needed
- Small to medium result sets
- Copy-paste into documents

**Example:**

```bash
bh-analyze-systems stats "01:00.0/ETH07" --format table
```

---

### Heatmap Format

Color-coded visualization showing patterns across lanes.

**Features:**

- ANSI color codes in terminal
- Visual pattern recognition
- Quick identification of problem areas
- Compact representation of large datasets

**Best For:**

- Large datasets (many systems/lanes)
- Pattern identification
- Quick visual assessment
- Presentations and reports

**Example:**

```bash
bh-analyze-systems training all --speed 200 --format heatmap
```

---

### Average BER with Variance Indicators

The average BER heatmap combines BER magnitude (color) with consistency indicators (symbols) to show both average performance and variability in a single view. This is now the default behavior when using `--statistic avg`.

**Changed in v0.6.0:** The `--statistic variance` option has been renamed to `avg`. The avg statistic now always includes variance indicators by default.

#### Usage

```bash
# Show average BER with variance indicators for all lanes
bh-analyze-systems stats all --format heatmap --statistic avg

# Filter by speed
bh-analyze-systems stats all --format heatmap --statistic avg --speed 200

# Specific ports
bh-analyze-systems stats 01:00.0/ETH07 --format heatmap --statistic avg

# Use different color schemes
bh-analyze-systems stats all --format heatmap --statistic avg --color-scheme sensitive

# Table format shows all statistics (min, avg, max, high BER)
bh-analyze-systems stats all --format table --speed 200
```

#### Understanding the Average BER Heatmap

Each cell displays:

- **BER value**: Average BER across all test runs
- **Color**: Indicates BER magnitude (green=good, red=bad)
- **Symbol**: Indicates consistency/variance (always shown for avg statistic)

**Variance Symbols:**

- `●` Very Consistent (max/avg < 2) - Stable, predictable performance
- `◆` Consistent (max/avg 2-10) - Minor fluctuations
- `▲` Moderate Variance (max/avg 10-100) - Noticeable spikes
- `■` High Variance (max/avg 100-1000) - Significant intermittent issues
- `✕` Extreme Spikes (max/avg ≥ 1000) - Severe occasional failures

#### Diagnostic Patterns

**Healthy Lanes:**

- Green `●` or `◆` = Excellent and consistent
- Yellow `●` or `◆` = Good and consistent

**Problem Lanes:**

- Orange/Red `●` or `◆` = Persistent hardware issues (consistent failures)
- Green/Yellow `■` or `✕` = Intermittent issues (cable, power, thermal)
- Orange/Red `■` or `✕` = Severe and unstable (critical problem)

**Troubleshooting Tips:**

- `✕` symbol → Investigate environmental factors (cables, power, temperature)
- Consistent `●`/`◆` symbols with high BER → Hardware fault (replace component)
- Pattern on specific lanes → Serdes lane issue
- Pattern on specific ports → Port or connector issue

#### Example

```
01:00.0   ETH07  1.2e-12 ●    1.5e-10 ▲    1.8e-10 ▲    4.5e-10 ✕    1.7e-10 ▲
```

Interpretation:

- Lane 0: Excellent and very consistent (`●`)
- Lanes 1-2: Marginal with moderate spikes (`▲`) - monitor
- Lane 3: Good average BUT extreme spikes (`✕`) - investigate cables/environment
- Lane 4: Marginal with moderate spikes (`▲`) - monitor

---

### Color Schemes

Heatmaps use configurable color schemes to represent values.

#### Count Heatmaps (Threshold, Custom, Training)

**Built-in Schemes:**

1. **default** - Gradual color progression
  - Green: 0 failures
  - Yellow: 1-10 failures
  - Bright Yellow: 11-24 failures
  - Orange: 25-49 failures
  - Red: 50+ failures
2. **strict** - Low tolerance for failures
  - Green: 0 failures
  - Yellow: 1-4 failures
  - Orange: 5-9 failures
  - Red: 10+ failures
3. **tolerant** - Higher tolerance for failures
  - Green: 0 failures
  - Yellow: 1-19 failures
  - Bright Yellow: 20-49 failures
  - Orange: 50-99 failures
  - Red: 100+ failures

**Threshold Logic:** Colors are assigned based on upper bounds. For example, with the default scheme, a count of 10 shows as yellow (count <= 10), while 11 shows as bright yellow (10 < count <= 24).

**Usage:**

```bash
# Use default scheme
bh-analyze-systems training all --format heatmap

# Use strict scheme (low tolerance for failures)
bh-analyze-systems training all --format heatmap --color-scheme strict

# Use tolerant scheme (higher tolerance)
bh-analyze-systems training all --format heatmap --color-scheme tolerant
```

#### BER Heatmaps (Stats)

**Built-in Schemes:**

1. **default** - Standard BER thresholds
  - Green: BER <= 1e-12
  - Yellow: 1e-12 < BER <= 1e-8
  - Bright Yellow: 1e-8 < BER <= 1e-7
  - Orange: 1e-7 < BER <= 5e-7
  - Red: 5e-7 < BER <= 1e-6
  - Bright Red: BER > 1e-6
2. **sensitive** - Stricter thresholds (lower tolerance)
  - Green: BER <= 1e-12
  - Yellow: 1e-12 < BER <= 1e-9
  - Bright Yellow: 1e-9 < BER <= 1e-8
  - Orange: 1e-8 < BER <= 5e-8
  - Red: 5e-8 < BER <= 1e-7
  - Bright Red: BER > 1e-7
3. **tolerant** - Relaxed thresholds (higher tolerance)
  - Green: BER <= 1e-12
  - Yellow: 1e-12 < BER <= 1e-7
  - Bright Yellow: 1e-7 < BER <= 1e-6
  - Orange: 1e-6 < BER <= 5e-6
  - Red: 5e-6 < BER <= 1e-5
  - Bright Red: BER > 1e-5

**Threshold Logic:** Colors are assigned based on upper bounds. For example, with the default scheme, BER of 1e-12 shows as green (BER <= 1e-12), while 5e-12 shows as yellow (1e-12 < BER <= 1e-8).

**Usage:**

```bash
# Use default scheme with maximum BER statistic (default)
bh-analyze-systems stats all --format heatmap

# Display average BER with sensitive scheme
bh-analyze-systems stats all --format heatmap --statistic avg --color-scheme sensitive

# Display minimum BER with tolerant scheme
bh-analyze-systems stats all --format heatmap --statistic min --color-scheme tolerant

# Display high BER counts (uses count color scheme)
bh-analyze-systems stats all --format heatmap --statistic high_ber
```

**Note:** When `--statistic high_ber` is used, the count color scheme is applied instead of the BER color scheme, since high BER values are displayed as counts rather than BER values.

---

## Excel Export

### Full Database Export

Export the entire database to a multi-sheet Excel workbook.

```bash
bh-analyze-systems export-excel --output full_db.xlsx
```

**Sheets Created:**

1. **Summary** - Statistics, system count, test distribution
2. **PRBS Tests** - All test records with full details
3. **Training Failures** - Filtered view of training failures only
4. **BER Exceeded** - Filtered view of BER threshold exceeded only
5. **Ingestion Metadata** - History of data ingestion runs

### Filtered Export

Export a subset of data based on criteria.

**Filter Options:**

- `--hosts` - Include only specific hostnames
- `--speeds` - Include only specific train speeds
- `--status` - Include only specific test status values
- `--date-range` - Include only tests within date range

**Example:**

```bash
# Export only failures for two systems at 200G
bh-analyze-systems export-excel \
  --output failures_200g.xlsx \
  --hosts bh-glx-c02u02 bh-glx-c02u03 \
  --speeds 200 \
  --status TRAINING_FAIL BER_THRESHOLD_EXCEEDED
```

### Excel Features

**Formatting:**

- Formatted headers with bold text
- Auto-sized columns
- Frozen header rows
- Number formatting for BER values

**Multiple Sheets:**

- Organized data by category
- Summary sheet with key statistics
- Metadata for provenance

**Pivot-Ready:**

- Data structured for Excel pivot tables
- Consistent column naming
- No merged cells or formatting that breaks pivots

---

## Interactive Shell

The interactive shell provides a REPL (Read-Eval-Print Loop) for exploratory analysis.

### Starting the Shell

```bash
bh-analyze-systems shell
```

### Available Commands

**Query Commands:**

- `stats <lane-spec> [--speed SPEED] [--format FORMAT] [--statistic STAT]` - BER statistics
- `threshold <lane-spec> [--speed SPEED] [--format FORMAT]` - Threshold exceeded counts
- `custom <lane-spec> <threshold> [--speed SPEED] [--format FORMAT]` - Custom threshold counts
- `training <lane-spec> [--speed SPEED] [--format FORMAT]` - Training failure counts
- `histogram <lane-spec> [--speed SPEED] [--max-bar-width WIDTH]` - BER distribution histogram
- `advanced-stats <lane-spec> [--speed SPEED]` - Aggregated host statistics

**Information Commands:**

- `systems` - List all system hostnames
- `speeds` - List all train speeds
- `info` - Show database information

**Export Commands:**

- `export excel [--output FILE]` - Export last result to Excel
- `export excel-db [--output FILE]` - Export full database to Excel

**Utility Commands:**

- `help` - Show available commands
- `history` - Show command history
- `exit` or `quit` - Exit shell

**Example Usage:**

```bash
bh-analyze> stats all --speed 200
[displays table format with all statistics]

bh-analyze> stats all --speed 200 --format heatmap
[displays heatmap of maximum BER values by default]

bh-analyze> stats all --speed 200 --format heatmap --statistic avg
[displays heatmap with average BER and variance symbols]

bh-analyze> stats all --speed 200 --format heatmap --statistic high_ber
[displays heatmap of high BER counts]

bh-analyze> histogram 01:00.0/ETH07/4 --speed 200
[displays BER distribution histogram for lane 4]

bh-analyze> advanced-stats */ETH07/4 --speed 200
[displays per-host statistics and aggregated statistics for lane 4 across all systems]
```

### Shell Features

**Command History:**

- Up/down arrows navigate command history
- Previous queries are saved during session

**Last Result:**

- Shell remembers the last query result
- Use `export` commands to save last result

**Interactive Exploration:**

- No need to reload database between queries
- Quick iteration on analysis
- Immediate feedback

### Example Workflow

```bash
# Start shell
bh-analyze-systems shell

# Explore database
bh-analyze> info
bh-analyze> systems
bh-analyze> speeds

# Run queries with different statistics
bh-analyze> stats 01:00.0/ETH07 --speed 200
bh-analyze> stats 01:00.0/ETH07 --speed 200 --format heatmap --statistic max
bh-analyze> stats 01:00.0/ETH07 --speed 200 --format heatmap --statistic avg
bh-analyze> training 01:00.0/* --speed 200 --format heatmap
bh-analyze> custom all 1e-10

# Use new v0.6.0 features
bh-analyze> histogram 01:00.0/ETH07/4 --speed 200
bh-analyze> advanced-stats */ETH07/4 --speed 200

# Export results
bh-analyze> export excel --output my_analysis.xlsx

# Continue exploring with high BER focus
bh-analyze> stats all --speed 200 --format heatmap --statistic high_ber

# Exit when done
bh-analyze> exit
```

---

## Configuration

### Database Path

Specify a custom database location:

**Via CLI:**

```bash
bh-analyze-systems --db /path/to/custom.db <command>
```

**Via Environment Variable:**

```bash
export BH_GLX_ANALYSIS_DB=/path/to/custom.db
bh-analyze-systems <command>
```

**Default Location:**

```
~/.local/share/bh-glx-data/analysis.db
```

### Config File

Add system analysis configuration to `config.yaml` (optional):

```yaml
system_analysis:
  database_path: ~/.local/share/bh-glx-data/analysis.db

  ingest:
    chunk_size: 1000
    status_filter:
      - PASS
      - BER_THRESHOLD_EXCEEDED
      - TRAINING_FAIL
```

Most users can use the default settings without a config file.

---

## Common Workflows

### Workflow 1: Initial Data Analysis

```bash
# 1. Ingest data
bh-analyze-systems ingest ./data/

# 2. Check what's in the database
bh-analyze-systems info

# 3. Get overview of training failures
bh-analyze-systems training all --speed 200 --format heatmap

# 4. Analyze BER for specific port
bh-analyze-systems stats "01:00.0/ETH07" --speed 200

# 5. Check for high BER occurrences visually
bh-analyze-systems stats all --speed 200 --format heatmap --statistic high_ber

# 6. Export for sharing
bh-analyze-systems export-excel --output analysis_summary.xlsx
```

### Workflow 2: Failure Investigation

```bash
# 1. Find training failures
bh-analyze-systems training all --format heatmap

# 2. Focus on specific system with failures
bh-analyze-systems training "bh-glx-c02u02/*" --format table

# 3. Check if BER threshold also exceeded
bh-analyze-systems threshold "bh-glx-c02u02/*"

# 4. Export failures for detailed analysis
bh-analyze-systems export-excel \
  --output failures.xlsx \
  --hosts bh-glx-c02u02 \
  --status TRAINING_FAIL BER_THRESHOLD_EXCEEDED
```

### Workflow 3: Speed Comparison

```bash
# 1. Compare training at different speeds
bh-analyze-systems training all --speed 100 --format heatmap
bh-analyze-systems training all --speed 200 --format heatmap

# 2. Compare BER statistics (average values)
bh-analyze-systems stats all --speed 100 --format heatmap --statistic avg
bh-analyze-systems stats all --speed 200 --format heatmap --statistic avg

# 3. Compare high BER occurrences
bh-analyze-systems stats all --speed 100 --format heatmap --statistic high_ber
bh-analyze-systems stats all --speed 200 --format heatmap --statistic high_ber

# 4. Export both speeds for side-by-side comparison
bh-analyze-systems export-excel --output speed_100.xlsx --speeds 100
bh-analyze-systems export-excel --output speed_200.xlsx --speeds 200
```

### Workflow 4: Custom Quality Criteria

```bash
# 1. Apply stricter BER threshold
bh-analyze-systems custom all 1e-12 --speed 200 --format heatmap

# 2. Find lanes that pass test but are marginal
bh-analyze-systems custom all 1e-11 --speed 200 --format table

# 3. Export for quality review
bh-analyze-systems export-excel \
  --output quality_review.xlsx \
  --status PASS
```

### Workflow 5: Variance Analysis for Troubleshooting

```bash
# 1. Start with average BER heatmap with variance indicators to get overall picture
bh-analyze-systems stats all --speed 200 --format heatmap --statistic avg

# 2. Focus on ports with extreme spikes (✕ symbols)
bh-analyze-systems stats 01:00.0/ETH07 --speed 200 --format table

# 3. Compare with maximum BER to confirm spikes
bh-analyze-systems stats 01:00.0/ETH07 --speed 200 --format heatmap --statistic max

# 4. Check if training failures are also present
bh-analyze-systems training 01:00.0/ETH07 --speed 200

# 5. Use sensitive color scheme to identify marginal lanes
bh-analyze-systems stats all --speed 200 --format heatmap --statistic avg --color-scheme sensitive

# 6. Export findings for hardware team
bh-analyze-systems export-excel --output variance_analysis.xlsx
```

### Workflow 6: Interactive Exploration

```bash
# Start interactive shell
bh-analyze-systems shell

# Explore interactively
bh-analyze> info
bh-analyze> systems
bh-analyze> training all --speed 200 --format heatmap
bh-analyze> stats 01:00.0/ETH07 --speed 200
bh-analyze> stats all --speed 200 --format heatmap --statistic avg
bh-analyze> stats all --speed 200 --format heatmap --statistic high_ber
bh-analyze> custom 01:00.0/* 1e-10
bh-analyze> histogram 01:00.0/ETH07/4 --speed 200
bh-analyze> advanced-stats */ETH07/4 --speed 200
bh-analyze> export excel --output session_results.xlsx
bh-analyze> exit
```

### Workflow 7: Lane-Level Deep Dive (NEW in v0.6.0)

```bash
# 1. Start with overall heatmap to identify problem lanes
bh-analyze-systems stats all --speed 200 --format heatmap --statistic avg

# 2. Focus on a specific problematic lane
bh-analyze-systems stats 01:00.0/ETH07/4 --speed 200 --format table

# 3. View BER distribution histogram for the lane
bh-analyze-systems histogram 01:00.0/ETH07/4 --speed 200

# 4. Compare the same lane across all systems
bh-analyze-systems advanced-stats */ETH07/4 --speed 200

# 5. If issue is fleet-wide, check all lanes on that port
bh-analyze-systems histogram 01:00.0/ETH07 --speed 200

# 6. Export detailed findings
bh-analyze-systems export-excel --output lane_analysis.xlsx
```

**Use Case:** This workflow is ideal when you've identified a specific lane with issues and need to understand:

- Is the BER distribution clustered or spread? (histogram)
- Is this lane problematic on all systems or just one? (advanced-stats)
- What's the performance consistency across the fleet? (advanced-stats statistics of statistics)

### Workflow 8: Fleet-Wide Performance Consistency

```bash
# 1. Check performance consistency for critical lanes across fleet
bh-analyze-systems advanced-stats */ETH07/0 --speed 200
bh-analyze-systems advanced-stats */ETH07/1 --speed 200
bh-analyze-systems advanced-stats */ETH07/4 --speed 200

# 2. Identify outlier systems from the per-host statistics
# (Look at the "Per-Host Statistics" table for systems with higher BER)

# 3. Deep dive into outlier system
bh-analyze-systems stats bh-glx-c02u02/* --speed 200 --format heatmap --statistic avg

# 4. Compare histogram of outlier vs typical system
bh-analyze-systems histogram bh-glx-c02u02/01:00.0/ETH07/4 --speed 200
bh-analyze-systems histogram bh-glx-c03u02/01:00.0/ETH07/4 --speed 200

# 5. Export for root cause analysis
bh-analyze-systems export-excel \
  --output fleet_consistency.xlsx \
  --hosts bh-glx-c02u02 bh-glx-c03u02 \
  --speeds 200
```

**Use Case:** This workflow helps you:

- Identify systems performing differently from the fleet average
- Understand if issues are hardware-specific or environmental
- Prioritize which systems need attention first

### Workflow 9: Integration with Jira Data

```bash
# 1. Retrieve data from Jira
bh-jira-retrieve --tickets SYS-123 SYS-456

# 2. Ingest into analysis database
bh-analyze-systems ingest data/

# 3. Analyze
bh-analyze-systems stats all --speed 200 --format heatmap

# 4. Generate report
bh-analyze-systems export-excel --output jira_analysis.xlsx
```

---

## Troubleshooting

### Database Not Found

**Problem:**

```
ERROR: Database not found: ~/.local/share/bh-glx-data/analysis.db
```

**Solution:**

The database doesn't exist yet. Run the ingest command first:

```bash
bh-analyze-systems ingest ./data/
```

### No Data in Query Results

**Problem:**

Query returns empty results or shows 0 tests.

**Solution:**

Check database contents:

```bash
bh-analyze-systems info
```

Verify:

- Database has data (total tests > 0)
- Lane specification matches data in database
- Speed filter matches available speeds
- Data was ingested successfully

### Invalid Lane Specification

**Problem:**

```
ERROR: Invalid lane specification: invalid/format
```

**Solution:**

Use correct lane specification syntax:

```bash
# Correct formats:
bh-analyze-systems stats all
bh-analyze-systems stats "01:00.0/ETH07"
bh-analyze-systems stats "01:00.0/*"
bh-analyze-systems stats "bh-glx-c02u02/*"
```

Note: Use quotes around specifications with wildcards or special characters.

### Memory Issues During Ingestion

**Problem:**

System runs out of memory during large file ingestion.

**Solution:**

The tool uses streaming ingestion to avoid memory issues. If problems persist, ingest files in smaller batches:

```bash
# Split data into subdirectories and ingest separately
bh-analyze-systems ingest ./data/batch1/
bh-analyze-systems ingest ./data/batch2/
```

### Slow Query Performance

**Problem:**

Queries take a long time to complete.

**Solution:**

1. Ensure database has proper indexes (should be automatic)
2. Use more specific lane selectors instead of "all"
3. Filter by speed to reduce data scanned
4. Check database size with `info` command
5. Consider vacuuming database:

```bash
sqlite3 ~/.local/share/bh-glx-data/analysis.db "VACUUM;"
```

### Excel Export Fails

**Problem:**

Excel export command fails or produces corrupt file.

**Solution:**

1. Ensure output directory exists and is writable
2. Check available disk space
3. Try smaller export with filters:

```bash
bh-analyze-systems export-excel \
  --output test.xlsx \
  --hosts single-system
```

1. Update openpyxl package:

```bash
pip install --upgrade openpyxl
```

### Color Scheme Not Found

**Problem:**

```
WARNING: Unknown color scheme: custom-scheme. Using default.
```

**Solution:**

Use built-in schemes: `default`, `strict`, `sensitive`, `tolerant`. Check spelling of scheme name.

### Interactive Shell Doesn't Start

**Problem:**

Shell command fails to start or exits immediately.

**Solution:**

1. Ensure database exists (run `info` first)
2. Check for Python environment issues
3. Verify terminal supports ANSI colors
4. Check logs with verbose flag:

```bash
bh-analyze-systems --verbose shell
```

---

## Tips and Best Practices

### Ingestion

- Ingest data regularly to keep database current
- Use consistent directory structure for CSV files
- Filter by status to keep database size manageable
- Monitor ingestion statistics for data quality

### Querying

- Start broad (`all`), then narrow to specific lanes
- Use heatmaps for large datasets, tables for details
- Filter by speed when analyzing speed-specific issues
- Save frequently-used queries in shell scripts

### Visualization

- Use strict color scheme for binary pass/fail analysis
- Use default scheme for understanding severity
- Export heatmaps as screenshots for presentations
- Combine table and heatmap views for complete picture

### Excel Export

- Export full database periodically for backup
- Use filtered exports for focused analysis
- Include metadata to track data provenance
- Name output files descriptively with dates

### Performance

- Use specific lane selectors when possible
- Filter by speed to reduce data processed
- Limit queries to relevant systems
- Vacuum database periodically if many ingestions

### Analysis Workflow

- Always run `info` first to understand data
- Use interactive shell for exploration
- Export results before trying new queries
- Document findings and export criteria

---

## Getting Help

### Command Help

```bash
# General help
bh-analyze-systems --help

# Command-specific help
bh-analyze-systems ingest --help
bh-analyze-systems stats --help
# ... etc
```

### Verbose Logging

Enable detailed logging for troubleshooting:

```bash
bh-analyze-systems --verbose <command>

# Or set specific log level
bh-analyze-systems --log-level DEBUG <command>
```

### Interactive Shell Help

```bash
bh-analyze-systems shell

bh-analyze> help
[shows available commands]
```

### Additional Resources

- Main README: [README.md](../../README.md)
- Architecture design: [docs/system_analysis_architecture.md](../system_analysis_architecture.md)
- Project overview: [CLAUDE.md](../../CLAUDE.md)
- Bug reports: Contact development team

---

**Last Updated:** 2026-03-13
**Tool Version:** 0.6.0