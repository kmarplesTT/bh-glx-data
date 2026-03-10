# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**BH Galaxy Data Analysis Tool** - A modern Python package for collecting and analyzing test data for BH Galaxy systems.

**Version:** 0.2.0 (Alpha)
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

```text
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
│   ├── unit/                     # Unit tests
│   └── integration/              # Integration tests
├── templates/                    # Excel templates
├── docs/                         # Documentation
└── (old scripts in src/ - deprecated)
```

## Development Setup

### Installation

Refer to the @README.md file for detailed installation instrcutions if needed

All CLI commands are available in your path after installation; however the virtual environment must be activated:

```bash
source .venv/bin/activate
```

### Running Tests

To run all tests, run `pytest` or `pytest -n auto` to run in parallel. Refer to the @README.md for commands to run tests on a subset of the test suite

### Code Quality Tools

Refer to @README.md for available tools to check code quality

## Common Commands

All tools are now accessed via unified CLI commands when the virtual environment is activated.
Refer to the @README.md for example test commands for each tool.

**Note:** Old scripts (`python3 src/*.py`) still work but show deprecation warnings. See `docs/MIGRATION_GUIDE.md` for migration instructions.

## Architecture

### Design Principles

- **Domain-Driven Design**: Code organized by functional domains (5 modules)
- **Separation of Concerns**: Library logic separated from CLI code
- **Type Safety**: Dataclasses for data models, type hints throughout
- **Multi-Source Configuration**: CLI args → env vars → user config → local config → defaults
- **Comprehensive Error Handling**: Custom exception hierarchy
- **Testability**: Comprehensive test suite with unit and integration tests

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
  - Hardware: `TopologyError`, `CableConfigError`

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
  - `QSFP_PORT_MAPPING`: Dictionary mapping (chip_num, eth_port) → QSFP port number (1-14)
  - Platform structure: 4 UBBs × 8 chips × 14 ETH ports
  - Port categories:
    - Unused: `ETH05`, `ETH08`
    - Unconnected: `ETH12`, `ETH13`
    - Cable connector ports (varies by chip, mapped to QSFP ports)
    - Platform connected ports (internal chip-to-chip)
  - QSFP mapping:
    - 14 QSFP ports (QSFP-1 through QSFP-14)
    - Each QSFP port represents 8 serdes lanes (2 ETH ports of 4 lanes each)
    - Cable connector ports map to specific QSFP ports based on chip position (U1-U8)
  - Helper functions:
    - `get_connected_port()`: Query platform connection
    - `get_qsfp_port()`: Get QSFP port number for cable connector ports
    - `get_eth_ports_for_qsfp()`: Reverse lookup - get ETH ports for a QSFP port
    - `get_cable_path()`: Resolve full device-to-device path through cables
    - `get_all_connections_for_device()`: Get all platform connections
    - `get_port_status()`: Determine port category
    - `normalize_bus_id()`, `normalize_eth_port()`: Input normalization
    - `get_ubb_from_bus_id()`, `get_chip_from_bus_id()`: Parse identifiers

- **`cable_config.py`**: Cable configuration management
  - `CableConfigManager`: Load and query cable configuration files
  - Supports named configs (searched in `~/.config/bh-glx-data/cables/` and `./cables/`)
  - Supports explicit file paths (relative or absolute)
  - YAML format defines QSFP-to-QSFP cable connections
  - Bidirectional mapping for cable connections
  - Validation of QSFP port numbers (1-14) and connection format
  - Methods:
    - `load(config_spec)`: Load cable configuration
    - `get_connected_qsfp(ubb_num, qsfp_port)`: Query cable connection
    - `is_loaded()`: Check if configuration is loaded

- **`cli.py`**: CLI entry point for `bh-topology`

**Usage:**

```python
from bh_glx_data.hardware.platform_topology import get_connected_port, get_qsfp_port, get_cable_path
from bh_glx_data.hardware.cable_config import CableConfigManager

# Query platform connection
connection = get_connected_port("01:00.0", "ETH07")
# Returns: ("05:00.0", "ETH00")

# Query QSFP port mapping for cable connector
qsfp = get_qsfp_port("01:00.0", "ETH10")
# Returns: 7  (QSFP-7)

# Query full cable path with configuration
cable_config = CableConfigManager()
cable_config.load("qc3")  # Load named config
path = get_cable_path("01:00.0", "ETH10", cable_config)
# Returns: {
#   "source": {"bus_id": "01:00.0", "eth_port": "ETH10", "qsfp_port": 7, "ubb": 1},
#   "cable": {"source_qsfp": 7, "dest_qsfp": 8, "source_ubb": 1, "dest_ubb": 1},
#   "destination": {"bus_id": "05:00.0", "eth_port": "ETH10", "qsfp_port": 8, "ubb": 1}
# }
```

**Cable Configuration Format** (`cables/qc3.yaml`):

```yaml
UBB1:
  - QSFP-1 <> QSFP-2
  - QSFP-7 <> QSFP-8
UBB2:
  - QSFP-1 <> QSFP-2
  - QSFP-7 <> QSFP-8
```

**Note** The @failure-pattern-analyzer agent is well-versed in the platform topology and understands how to use this tool to analyze failure data and draw conclusions based on Ethernet port mapping

### Data Pipeline Flow

1. **Data Collection** → Jira Integration or Quanta Extraction
2. **Failure Filtering** → Data Processing module
3. **Failure Analysis (optional)** -> @failure-pattern-analyzer agent
4. **Reporting (optional)** → Excel Reporting

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

- **Testing**: Comprehensive test suite
  - Run tests: `pytest tests/`
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
