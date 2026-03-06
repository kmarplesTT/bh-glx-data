# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**BH Galaxy Data Analysis Tool** - A modern Python package for collecting and analyzing test data for BH Galaxy systems.

**Version:** 0.1.0 (Alpha)
**Python:** 3.10+
**Architecture:** Modern package with domain-driven design

The tool provides 5 integrated capabilities:

1. **Jira Integration** - Download CSV test data attachments from Jira tickets
2. **Data Processing** - Filter and process test failure data
3. **Excel Reporting** - Generate organized Excel summaries with pivot tables
4. **Quanta Extraction** - Extract test data from Quanta QC3 test packages
5. **Platform Topology** - Query ETH port connectivity between chips

## Package Structure

The codebase follows modern Python packaging best practices:

```
bh-glx-data/
├── src/bh_glx_data/              # Main package (src layout)
│   ├── __init__.py
│   ├── cli.py                    # Unified CLI entry point
│   ├── core/                     # Core abstractions
│   │   ├── config.py             # Multi-source configuration
│   │   ├── models.py             # Data models (dataclasses)
│   │   └── exceptions.py         # Exception hierarchy
│   ├── jira_integration/         # Jira data collection
│   │   ├── client.py             # Jira API wrapper
│   │   ├── retriever.py          # CSV download logic
│   │   └── cli.py
│   ├── data_processing/          # CSV data handling
│   │   ├── csv_reader.py         # CSV utilities
│   │   ├── filter.py             # Failure filtering
│   │   └── cli.py
│   ├── excel_reporting/          # Excel generation
│   │   ├── generator.py          # Excel creation
│   │   ├── templates.py          # Template management
│   │   └── cli.py
│   ├── quanta_extraction/        # Quanta QC3 processing
│   │   ├── extractor.py          # Archive extraction
│   │   ├── analyzer.py           # Excel analysis
│   │   └── cli.py
│   └── hardware/                 # Platform topology
│       ├── platform_topology.py  # Topology data
│       └── cli.py
├── tests/                        # Comprehensive test suite
│   ├── unit/                     # Unit tests (~85% coverage)
│   └── integration/              # Integration tests
├── templates/                    # Excel templates
├── docs/                         # Documentation
└── (old scripts in src/ - deprecated)
```

## Development Setup

### Installation

```bash
# Clone repository
git clone <repository-url>
cd bh-glx-data

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package in development mode
pip install -e ".[dev]"
```

After installation, all CLI commands are available in your PATH.

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=bh_glx_data --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_hardware.py

# Run in parallel (faster)
pytest tests/ -n auto
```

## Common Commands

All tools are now accessed via unified CLI commands:

### Data Collection from Jira

```bash
# Download CSV files from Jira
bh-jira-retrieve --tickets SYS-123 SYS-456

# Or use unified CLI
bh-glx-data jira-retrieve --tickets SYS-123
```

### Filter Test Failures

```bash
# Extract only failed test rows
bh-filter-failures data_test_results.csv

# Specify output file
bh-filter-failures data_test_results.csv --output failures.csv
```

### Excel Summary Generation

```bash
# Generate Excel reports for all systems
bh-generate-excel

# Process specific systems
bh-generate-excel --systems bh-glx-b02u02 bh-glx-b03u02
```

### Quanta Failure Data Extraction

```bash
# Extract from tar.gz archive
bh-extract-quanta QC3_UBB_20260128.tar.gz

# Analyze Excel file for failures
bh-extract-quanta --analyze QC3_S7TK_0128_build_test.xlsx
```

### Platform Topology Queries

```bash
# Query specific connection
bh-topology 01:00.0 ETH07

# Show all connections for device
bh-topology 01:00.0 --all

# JSON output
bh-topology 01:00.0 ETH07 --json
```

**Note:** Old scripts (`python3 src/*.py`) still work but show deprecation warnings. See `docs/MIGRATION_GUIDE.md` for migration instructions.

## Architecture

### Design Principles

- **Domain-Driven Design**: Code organized by functional domains (5 modules)
- **Separation of Concerns**: Library logic separated from CLI code
- **Type Safety**: Dataclasses for data models, type hints throughout
- **Multi-Source Configuration**: CLI args → env vars → user config → local config → defaults
- **Comprehensive Error Handling**: Custom exception hierarchy
- **Testability**: >80% test coverage target, >85% for library code

### Module Responsibilities

#### Core Module (`core/`)

Provides foundational abstractions used across the package.

- **`config.py`**: Multi-source configuration management
  - `ConfigManager` class with config search path
  - Loads from: CLI args → `BH_GLX_CONFIG` env → `~/.config/bh-glx-data/config.yaml` → `./config.yaml` → defaults
  - Type-safe configuration with validation

- **`models.py`**: Data models (dataclasses)
  - `TestResult`: Test execution result
  - `FailureRecord`: Failure with signature
  - `FilterResult`: Failure filtering result
  - `SystemConfig`: System metadata (hostname, firmware)
  - `Connection`: Port connectivity tuple
  - Enums: `TestType`, `TestStatus`, `PortType`, `TrainMode`

- **`exceptions.py`**: Custom exception hierarchy
  - Base: `BHGlxDataError`
  - Config: `ConfigurationError`, `ValidationError`
  - Data: `DataProcessingError`, `CSVParseError`
  - Jira: `JiraConnectionError`, `JiraAuthenticationError`
  - Excel: `ExcelGenerationError`, `TemplateError`
  - Hardware: `TopologyError`

#### Jira Integration Module (`jira_integration/`)

Handles Jira API interaction and CSV download.

- **`client.py`**: `JiraClient` wrapper around `jira` library
  - Authentication with API tokens
  - Ticket retrieval with error handling
  - Attachment listing and filtering

- **`retriever.py`**: `JiraCSVRetriever` for downloading CSVs
  - Parallel downloads with `ThreadPoolExecutor`
  - Progress tracking with `tqdm`
  - Returns `RetrievalResult` with statistics

- **`cli.py`**: CLI entry point for `bh-jira-retrieve`

**Usage:**
```python
from bh_glx_data.jira_integration.client import JiraClient
from bh_glx_data.jira_integration.retriever import JiraCSVRetriever

client = JiraClient(server_url, email, api_key)
retriever = JiraCSVRetriever(client)
result = retriever.download_ticket_csvs(ticket_key, output_dir)
```

#### Data Processing Module (`data_processing/`)

CSV reading, validation, and failure filtering.

- **`csv_reader.py`**: CSV utilities
  - `read_csv_with_validation()`: Read with schema validation
  - `validate_csv_schema()`: Check required columns
  - `extract_firmware_version()`: Parse from filename
  - `extract_hostname_from_csv()`: Extract from CSV content

- **`filter.py`**: Failure filtering
  - `filter_failures()`: Extract only failed rows
  - Identifies failures: `test_status` NOT IN [`ETH_ACTIVE`, `ETH_UNCONNECTED`]
  - Returns `FilterResult` with breakdown

- **`cli.py`**: CLI entry point for `bh-filter-failures`

**Usage:**
```python
from bh_glx_data.data_processing.filter import filter_failures

result = filter_failures(input_csv, output_csv)
print(f"Found {result.failure_count} failures")
```

#### Excel Reporting Module (`excel_reporting/`)

Excel report generation with pivot tables.

- **`generator.py`**: `ExcelReportGenerator` class
  - Reads `system_data_template.xlsx` template
  - Groups CSV data by (hostname, firmware_version, test_type)
  - Compiles data into Excel sheets
  - Updates pivot table sources via `openpyxl`
  - Template structure:
    - `raw prbs data`: PRBS test data
    - `raw data`: Data test data
    - `PRBS Summary`: Pivot table for PRBS
    - `DATA Summary`: Pivot table for Data tests

- **`templates.py`**: Template management utilities
  - Template validation
  - Sheet verification

- **`cli.py`**: CLI entry point for `bh-generate-excel`

**Output format:** `{hostname}_{firmware_version}.xlsx`

#### Quanta Extraction Module (`quanta_extraction/`)

Extract test data from Quanta QC3 test packages.

- **`extractor.py`**: `QuantaExtractor` class
  - Opens tar.gz archives directly (no temporary extraction)
  - Navigates nested archives: `QC3_*.zip` → `0130/{SNs}/` → `QC3_UBB_*.tar.gz` → `tt_funtest_ubb_*/` → `ft_eth_stress_*.tar.gz`
  - Extracts `data_test_*.csv` and `prbs_test_*.csv`
  - Progress tracking with `tqdm`

- **`analyzer.py`**: Excel failure analyzer
  - Scans `QC3_*_test.xlsx` for non-zero failure counts
  - Extracts serial numbers of failed systems
  - Returns list of failed SNs

- **`cli.py`**: CLI entry point for `bh-extract-quanta`

**File organization:** CSV files saved to `quanta/` directory with SN prefix

#### Hardware Module (`hardware/`)

Platform topology data and queries.

- **`platform_topology.py`**: Topology mapping
  - `PLATFORM_TOPOLOGY`: Dictionary mapping (bus_id, eth_port) → (bus_id, eth_port)
  - Platform structure: 4 UBBs × 8 chips × 14 ETH ports
  - Port categories:
    - Unused: `ETH05`, `ETH08`
    - Unconnected: `ETH12`, `ETH13`
    - Cable connector ports (varies by chip)
    - Platform connected ports (internal chip-to-chip)
  - Helper functions:
    - `get_connected_port()`: Query connection
    - `get_all_connections_for_device()`: Get all connections
    - `get_port_status()`: Determine port category
    - `normalize_bus_id()`, `normalize_eth_port()`: Input normalization
    - `get_ubb_from_bus_id()`, `get_chip_from_bus_id()`: Parse identifiers

- **`cli.py`**: CLI entry point for `bh-topology`

**Usage:**
```python
from bh_glx_data.hardware.platform_topology import get_connected_port

connection = get_connected_port("01:00.0", "ETH07")
# Returns: ("05:00.0", "ETH00")
```

### Data Pipeline Flow

1. **Data Collection** → Jira Integration or Quanta Extraction
2. **Failure Filtering** → Data Processing module
3. **Reporting** → Excel Reporting

### Test Type Identification

The system recognizes two test types based on the `test_type` column:

- `TestType.SERDES_PRBS` → PRBS tests
- `TestType.SIMPLE_PACKET` → Data tests

Fallback: If `test_type` column is missing, uses filename patterns (`prbs_test`, `data_test`).

### File Naming Conventions

**Input CSV files** (from Jira):

- Format: `{TICKET_KEY}_{original_filename}.csv`
- Must contain firmware version pattern in filename (e.g., `erisc_v1_7_103` or `v1_7_103`)
- Must have `host` column with system hostname
- Must have `test_type` column with test type identifier

**Output Excel files**:

- Format: `{hostname}_{firmware_version}.xlsx`
- Example: `bh-glx-b02u02_erisc_v1_7_103.xlsx`

## Important Development Notes

### Package and Dependencies

- **Python Version**: 3.10+ required (uses modern type hints and dataclasses)
- **Package Structure**: src layout with proper `pyproject.toml` configuration
- **Installation**: Always use `pip install -e ".[dev]"` for development
- **Virtual Environment**: Always activate `.venv` before development

### Security

- Credentials in `.env` are gitignored and never committed
- `config.yaml` contains only ticket keys (no secrets) and is committed
- `data/`, `summaries/`, `quanta/`, `failures/`, and `reports/` directories are gitignored
- Use API tokens (not passwords) for Jira Cloud authentication

### Code Quality

- **Testing**: >80% overall coverage target, >85% for library code
  - Run tests: `pytest tests/`
  - Run with coverage: `pytest tests/ --cov=bh_glx_data --cov-report=term-missing`
  - Integration tests in `tests/integration/`
  - Unit tests in `tests/unit/`
- **Type Hints**: All public APIs should have type hints
- **Docstrings**: All public functions/classes require docstrings
- **Error Handling**: Use custom exceptions from `core.exceptions`
- **Logging**: Use INFO level by default for operational visibility

### CLI Development

- Each module has its own CLI entry point in `<module>/cli.py`
- Unified CLI in `src/bh_glx_data/cli.py` routes to module CLIs
- Entry points defined in `pyproject.toml` under `[project.scripts]`
- Old scripts in `src/*.py` are deprecated but functional (with warnings)

### Working with the Codebase

- **Module Imports**: Use `from bh_glx_data.module.submodule import ...`
- **Data Models**: Import from `bh_glx_data.core.models`
- **Exceptions**: Import from `bh_glx_data.core.exceptions`
- **Configuration**: Use `ConfigManager.load()` from `bh_glx_data.core.config`
- **Failure Filtering**: Use `bh-filter-failures` command or `filter_failures()` from `data_processing.filter`
- **Documentation**: Keep README.md, CLAUDE.md, and migration guide in sync

### Testing Guidelines

When writing tests:
- Use fixtures from `tests/conftest.py`
- Mock external dependencies (Jira API, filesystem where appropriate)
- Test both success and error paths
- Use `tmp_path` fixture for file operations
- Test edge cases (empty files, missing columns, invalid data)
- Verify data model field types and values

### Hardware Information

- The hardware being tested is a platform consisting of 32 chips (PCIe devices) with 14 Ethernet ports on each chip, 4 of which are unused (ETH5, ETH8, ETH12, and ETH13)
- Each Ethernet port (ETH##) is connected to another Ethernet port on the platform
- 2 ETH ports share a Serdes so one will always act as "Lead" and the other "Follower". The pairs are (Lead, Follow): (ETH00, ETH01), (ETH02, ETH03), (ETH04, ETH06), (ETH09, ETH07), (ETH11, ETH10).

### CSV Parsing and Analysis Guidelines

#### Understanding Test Data

- **Device Identification**: Use `bus_id` to identify PCIe device (chip), not `interface`
- **Test Success Criteria**:
  - Data tests: `test_status` = `ETH_ACTIVE`
  - PRBS tests: `test_status` = `PASS`
  - Unconnected ports: `test_status` = `ETH_UNCONNECTED` (not a failure)
- **Test Types**: Defined in `TestType` enum (`core/models.py`):
  - `SERDES_PRBS`: PRBS tests
  - `SIMPLE_PACKET`: Data tests

#### Topology and Connectivity

- Use the `hardware.platform_topology` module to understand port connections:
  ```python
  from bh_glx_data.hardware.platform_topology import get_connected_port

  # Find connected port
  connection = get_connected_port("01:00.0", "ETH07")
  # Returns: ("05:00.0", "ETH00")
  ```
- Use this to identify connected ports failing together
- Cable connector ports route to other cable connector ports
- Infer cable port pairings from failure patterns

#### Failure Analysis Workflow

1. **Filter Failures First**:
   ```bash
   # Use CLI command
   bh-filter-failures data_test_results.csv

   # Or programmatically
   from bh_glx_data.data_processing.filter import filter_failures
   result = filter_failures(input_csv, output_csv)
   ```

2. **Focus on Diagnostic Data**:
   - The `train_status` dictionary contains crucial diagnostic info
   - Key metrics in `train_status`:
     - `eth_status.port_status`: Port state
     - `eth_status.train_status`: Training result
     - `eth_status.postcode`: Firmware diagnostic code
     - `serdes_training.cdr_unlocked_cnt`: CDR unlock count
     - `serdes_training.cdr_unlock_transitions`: CDR unlock transitions
     - `serdes_training.man_eq_retry_cnt`: Manual EQ retry count
     - `serdes_training.training_times`: Timeout values
     - `macpcs_training.macpcs_retry_cnt`: MAC/PCS retry count

#### Failure Signature Documentation

When documenting failure signatures:

**Required Fields**:
- `port_type` (e.g., `CHIP_TO_QSFPDD`, `CHIP_TO_CHIP`)
- `train_mode` (e.g., `AW_MANUAL_EQ`, `AW_ANLT_MODE`)
- Diagnostic indicators (CDR counts, retry counts, timeouts)

**Keep Factual**:
- Document ONLY what is observed in the data
- Do NOT include speculative root causes
- Do NOT suggest firmware changes or investigations
- Do NOT recommend timeout adjustments
- Focus on patterns, not interpretations

**Example Good Documentation**:
```
Pattern: MANUAL_EQ_TRAINING_TIMEOUT
Indicators:
  - test_status: TRAINING_FAIL
  - train_status: LINK_TRAIN_TIMEOUT_MANUAL_EQ
  - port_type: CHIP_TO_QSFPDD
  - train_mode: AW_MANUAL_EQ
  - sigdet_time_ms: 20000+ (high)
  - rx_eq_assert_time_ms: varies
```

#### Diagnostic Data Interpretation

**CDR Unlock Counts**:
- `cdr_unlocked_cnt`: Number of CDR unlock events
- Non-zero count is NOT an issue unless `test_status` shows failure
- Include in reports for context but don't over-emphasize

**LCPLL Lock Failures**:
- `lcpll_lock_fail_cnt`: LCPLL lock failure count
- Only relevant if results in `test_status` failure
- Note in reports but don't flag as primary issue

**Remote Device Info**:
- `remote_info` in `train_status` provides context but is rarely diagnostic
- External connections: `remote_pcb_type: ORION` (cable, no remote)
- Internal connections: `remote_pcb_type: UBB` (chip-to-chip)
- Focus on training metrics, not remote info

**Priority Metrics** (most diagnostic value):
1. CDR unlock counts and transitions
2. Retry counts (manual EQ, ANLT, MAC/PCS)
3. Training timeout values
4. Postcode values (firmware diagnostics)
5. Port status and training status

#### Programmatic API

```python
# Complete workflow example
from bh_glx_data.data_processing.filter import filter_failures
from bh_glx_data.hardware.platform_topology import get_connected_port

# 1. Filter failures
result = filter_failures('data_test.csv', 'failures.csv')
print(f"Found {result.failure_count} failures")

# 2. Check topology for connected failures
# Read failure CSV and analyze port connections
import csv
with open('failures.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        bus_id = row['bus_id']
        eth_id = row['eth_id']
        connected = get_connected_port(bus_id, eth_id)
        if connected:
            print(f"{bus_id} {eth_id} connects to {connected}")
```
