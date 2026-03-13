# bh-analyze-systems User Guide

A database utility for collecting, storing, and analyzing PRBS test data across multiple systems. This tool provides efficient query capabilities with visualization options for identifying serdes lane performance patterns.

**Version:** 0.3.0
**Purpose:** Aggregate PRBS test data from CSV files with memory-efficient storage and interactive analysis

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

Lanes are specified using a flexible syntax that allows querying specific ports or broad patterns:

- `all` - All lanes on all systems
- `01:00.0/ETH07` - All 8 lanes on specific port
- `01:00.0/*` - All ports on a bus ID
- `bh-glx-c02u02/01:00.0/ETH07` - Specific system and port
- `bh-glx-c02u02/*` - All ports on a system
- `*/ETH07` - ETH07 on all systems

### Query Types

The tool provides several types of queries:

1. **BER Statistics** - Min, max, and average BER values per lane
2. **Threshold Exceeded** - Count of BER_THRESHOLD_EXCEEDED test status occurrences
3. **Custom Threshold** - Count of lanes exceeding a custom BER threshold
4. **Training Failures** - Count of TRAINING_FAIL test status occurrences

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

**What It Does:**

1. Discovers all CSV files in the input directory
2. Streams CSV data in chunks (memory efficient)
3. Filters rows by test_status (includes only specified statuses)
4. Excludes unnecessary columns (44 columns not needed for analysis)
5. Batch inserts data into SQLite database
6. Records ingestion metadata for provenance

**Notes:**

- Ingestion is incremental - you can run it multiple times
- Large files are processed in chunks to avoid memory issues
- Progress bar shows ingestion status

---

### stats

Show BER statistics (min, max, avg) for specified lanes.

```bash
bh-analyze-systems stats <lane_spec> [OPTIONS]
```

**Arguments:**

- `lane_spec` - Lane specification (see Lane Selection Syntax)

**Options:**

- `--speed SPEED` - Filter by train speed (can be specified multiple times)
- `--format {table|heatmap}` - Output format (default: table)
- `--color-scheme SCHEME` - Color scheme for heatmap (default, sensitive, tolerant)
- `--exclude-training-failures` - Exclude training failures from statistics (default: True)

**Example (Table Format):**

```bash
bh-analyze-systems stats "01:00.0/ETH07" --speed 200

# Output:
┌─────────────────────┬───────────┬───────────┬───────────┬─────────┐
│ Lane                │ Min BER   │ Max BER   │ Avg BER   │ Samples │
├─────────────────────┼───────────┼───────────┼───────────┼─────────┤
│ 01:00.0/ETH07/lane0 │ 1.23e-12  │ 4.56e-10  │ 2.34e-11  │ 450     │
│ 01:00.0/ETH07/lane1 │ 8.90e-13  │ 3.21e-10  │ 1.87e-11  │ 450     │
│ 01:00.0/ETH07/lane2 │ 1.45e-12  │ 5.23e-10  │ 2.89e-11  │ 450     │
│ 01:00.0/ETH07/lane3 │ 9.87e-13  │ 3.78e-10  │ 2.12e-11  │ 450     │
└─────────────────────┴───────────┴───────────┴───────────┴─────────┘

Tests: 450  Systems: 12  Speeds: 200
```

**Example (Heatmap Format):**

```bash
bh-analyze-systems stats all --speed 200 --format heatmap
```

Displays a color-coded heatmap with BER values across all systems and lanes.

**Notes:**

- Training failures (no BER data) are excluded by default
- Multiple speeds can be specified: `--speed 100 --speed 200`
- Heatmap colors indicate BER levels (green=low, red=high)

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

- Identify lanes with frequent BER threshold violations
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


| Pattern                | Description                  | Example                       |
| ---------------------- | ---------------------------- | ----------------------------- |
| `all`                  | All lanes on all systems     | `all`                         |
| `BUS_ID/ETH_PORT`      | Specific port, all lanes     | `01:00.0/ETH07`               |
| `BUS_ID/`*             | All ports on bus ID          | `01:00.0/*`                   |
| `HOST/BUS_ID/ETH_PORT` | Specific system and port     | `bh-glx-c02u02/01:00.0/ETH07` |
| `HOST/*`               | All ports on system          | `bh-glx-c02u02/*`             |
| `*/ETH_PORT`           | Specific port on all systems | `*/ETH07`                     |


### Examples

```bash
# Query all lanes everywhere
bh-analyze-systems stats all

# Query specific port (8 lanes)
bh-analyze-systems stats "01:00.0/ETH07"

# Query all ports on a bus ID
bh-analyze-systems stats "01:00.0/*"

# Query specific system
bh-analyze-systems stats "bh-glx-c02u02/*"

# Query same port across all systems
bh-analyze-systems stats "*/ETH07"

# Query with specific system and port
bh-analyze-systems stats "bh-glx-c02u02/01:00.0/ETH07"
```

### Lane Numbering

Each ETH port has 8 serdes lanes numbered 0-7:

- `lane0`, `lane1`, `lane2`, `lane3` - First 4 lanes
- `lane4`, `lane5`, `lane6`, `lane7` - Second 4 lanes

Queries return results for all 8 lanes per port.

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

### Color Schemes

Heatmaps use configurable color schemes to represent values.

#### Count Heatmaps (Threshold, Custom, Training)

**Built-in Schemes:**

1. **default** - Gradual color progression
   - Green: 0 failures
   - Yellow: 1-10 failures
   - Orange: 11-50 failures
   - Red: 50+ failures

2. **strict** - Binary coloring
   - Green: 0 failures
   - Red: 1+ failures

**Usage:**

```bash
# Use default scheme
bh-analyze-systems training all --format heatmap

# Use strict scheme (any failure is red)
bh-analyze-systems training all --format heatmap --color-scheme strict
```

#### BER Heatmaps (Stats)

**Built-in Schemes:**

1. **default** - Standard BER thresholds
   - Green: 0
   - Yellow: > 1e-12
   - Orange: > 1e-10
   - Red: > 1e-8

2. **sensitive** - Stricter thresholds
   - Green: 0
   - Yellow: > 1e-13
   - Orange: > 1e-11
   - Red: > 1e-9

3. **tolerant** - Relaxed thresholds
   - Green: 0
   - Yellow: > 1e-11
   - Orange: > 1e-9
   - Red: > 1e-7

**Usage:**

```bash
# Use default scheme
bh-analyze-systems stats all --format heatmap

# Use sensitive scheme for tighter BER requirements
bh-analyze-systems stats all --format heatmap --color-scheme sensitive

# Use tolerant scheme for more relaxed criteria
bh-analyze-systems stats all --format heatmap --color-scheme tolerant
```

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

- `stats <lane-spec> [--speed SPEED]` - BER statistics
- `threshold <lane-spec> [--speed SPEED]` - Threshold exceeded counts
- `custom <lane-spec> <threshold> [--speed SPEED]` - Custom threshold counts
- `training <lane-spec> [--speed SPEED]` - Training failure counts

**Information Commands:**

- `systems` - List all system hostnames
- `speeds` - List all train speeds
- `info` - Show database information

**Export Commands:**

- `export csv [--output FILE]` - Export last result to CSV
- `export excel [--output FILE]` - Export last result to Excel
- `export excel-db [--output FILE]` - Export full database to Excel

**Utility Commands:**

- `help` - Show available commands
- `exit` - Exit shell

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

# Run queries
bh-analyze> stats 01:00.0/ETH07 --speed 200
bh-analyze> training 01:00.0/* --speed 200
bh-analyze> custom all 1e-10

# Export results
bh-analyze> export excel --output my_analysis.xlsx

# Continue exploring
bh-analyze> stats 05:00.0/ETH00 --speed 200

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

Add system analysis configuration to `config.yaml`:

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
    default_format: table  # or "heatmap"
    heatmap_output: terminal  # or "html" (future)

    # Custom color schemes
    count_heatmap:
      default_scheme: default
      custom_schemes:
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
      default_scheme: default
      custom_schemes:
        custom:
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

### Color Scheme Configuration

Custom color schemes can be defined in `config.yaml` and referenced by name:

```bash
# Use custom "relaxed" scheme defined in config
bh-analyze-systems training all --format heatmap --color-scheme relaxed
```

**Color Values:**

- `green` - Good/passing
- `yellow` - Warning/marginal
- `orange` - Concerning
- `red` - Critical/failing

**Threshold Format:**

- `value` - Numeric threshold
- `color` - Color for values >= threshold
- `default_color` - Color for values above all thresholds

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

# 5. Export for sharing
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

# 2. Compare BER statistics
bh-analyze-systems stats all --speed 100
bh-analyze-systems stats all --speed 200

# 3. Export both speeds for side-by-side comparison
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

### Workflow 5: Interactive Exploration

```bash
# Start interactive shell
bh-analyze-systems shell

# Explore interactively
bh-analyze> info
bh-analyze> systems
bh-analyze> training all --speed 200
bh-analyze> stats 01:00.0/ETH07 --speed 200
bh-analyze> custom 01:00.0/* 1e-10
bh-analyze> export excel --output session_results.xlsx
bh-analyze> exit
```

### Workflow 6: Integration with Jira Data

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

The tool uses streaming ingestion to avoid memory issues, but if problems persist:

1. Reduce chunk size in config:

```yaml
system_analysis:
  ingest:
    chunk_size: 500  # Reduce from default 1000
```

2. Ingest files in smaller batches:

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

4. Update openpyxl package:

```bash
pip install --upgrade openpyxl
```

### Color Scheme Not Found

**Problem:**

```
WARNING: Unknown color scheme: custom-scheme. Using default.
```

**Solution:**

1. Use built-in schemes: `default`, `strict`, `sensitive`, `tolerant`
2. Define custom scheme in `config.yaml` before using
3. Check spelling of scheme name

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

**Last Updated:** 2026-03-12
**Tool Version:** 0.3.0