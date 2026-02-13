# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BH Galaxy Data Analysis Tool - A collection of Python tools for analyzing test data for BH Galaxy systems.

The toolset includes:

1. **Data Collection from Jira**: Download CSV test data attachments from Jira tickets
2. **Quanta Failure Data Extraction**: Extract CSV test data for failed systems from Quanta QC3 test packages (received from manufacturing partner)
3. **Report Generation**: Process CSV data and generate Excel summaries organized by system hostname and firmware version

## Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Always activate the virtual environment before running scripts
. .venv/bin/activate
```

## Common Commands

### Data Collection from Jira

Refer to `README.md` for instructions on how to use `jira_csv_analyzer.py`

### Excel Summary Generation

Refer to `README.md` for instructions on how to use `excel_summary_generator.py`

### Quanta Failure Data Extraction

Refer to `README.md` for instructions on how to use `extract_quanta_failures.py`

## Architecture

### Data Pipeline Flow

1. **Jira Retrieval** (`jira_csv_retriever.py`)
   - Authenticates with Jira using credentials from `.env`
   - Reads ticket keys from `config.yaml` (or CLI args)
   - Downloads CSV attachments to `data/` directory
   - Files named as: `{TICKET_KEY}_{ATTACHMENT_NAME}.csv`

2. **Quanta Failure Extraction** (`extract_quanta_failures.py`)
   - Processes QC3 test packages received from Quanta (manufacturing partner)
   - Unzips the package and locates the Excel results file (e.g., `QC3_S7TK_0128_build_test.xlsx`)
   - Uses `analyze_failures.py` to scan Excel for non-zero failure counts
   - Extracts serial numbers of failed systems
   - Navigates nested tar.gz archives to find test data directories
   - Extracts `data_test_*.csv` and `prbs_test_*.csv` for failed systems only
   - Saves to `quanta/` directory with filenames prefixed by system serial numbers
   - File organization: `QC3_*.zip` → `0130/{SNs}/` → `QC3_UBB_*.tar.gz` → `tt_funtest_ubb_*/` → `ft_eth_stress_*.tar.gz` → `ft_eth_stress/` → CSV files

3. **Excel Generation** (`excel_summary_generator.py`)
   - Scans `data/` directory for CSV files
   - Extracts metadata from filenames and CSV content:
     - System hostname from `host` column
     - Firmware version from filename pattern (e.g., `erisc_v1_7_103`)
     - Test type from `test_type` column (`PRBS` vs `DATA`)
   - Groups files by (hostname, firmware_version, test_type)
   - Compiles data for each group by concatenating all matching CSVs
   - Generates Excel files using `system_data_template.xlsx` template
   - Updates pivot table data sources and marks for refresh
   - Saves to `summaries/{hostname}_{firmware_version}.xlsx`

### Key Modules

- **config.py**: Configuration loader
  - Loads Jira credentials from `.env` via python-dotenv
  - Loads ticket list from `config.yaml` via PyYAML
  - Validates required configuration
  - Creates `data/` output directory

- **jira_csv_retriever.py**: Jira data collection
  - Uses `jira` library for API access
  - Downloads only CSV attachments
  - Handles authentication errors and missing tickets gracefully

- **excel_summary_generator.py**: Excel report generator
  - Uses `pandas` for CSV reading and data manipulation
  - Uses `openpyxl` for Excel file operations
  - Handles pivot table source updates via openpyxl's private `_pivots` attribute
  - Template structure:
    - `raw prbs data` sheet: PRBS test data
    - `raw data` sheet: Data test data
    - `PRBS Summary` sheet: Pivot table for PRBS
    - `DATA Summary` sheet: Pivot table for Data tests

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

## Important Notes

- Credentials in `.env` are gitignored and never committed
- `config.yaml` contains only ticket keys (no secrets) and is committed
- `data/` and `summaries/` directories are gitignored
- Python 3.10+ required
- Use `python3` when running Python scripts
- Uses logging at INFO level by default for operational visibility
- Usage documentation can be found in @README.md

### Hardware Information

- The hardware being tested is a platform consisting of 32 chips (PCIe devices) with 14 Ethernet ports on each chip, 4 of which are unused (ETH5, ETH8, ETH12, and ETH13)
- Each Ethernet port (ETH##) is connected to another Ethernet port on the platform
- 2 ETH ports share a Serdes so one will always act as "Lead" and the other "Follower". The pairs are (Lead, Follow): (ETH00, ETH01), (ETH02, ETH03), (ETH04, ETH06), (ETH09, ETH07), (ETH11, ETH10).

### CSV Parsing Guidelines

- The 'bus_id' should be used to identify the PCIe device (chip), not the 'interface'
- For Data tests, successful test ports have `test_status` = `ETH_ACTIVE`
- For PRBS tests, successful test ports have `test_status` = `PASS`
- Use @platform_topology.py to understand Ethernet port connections between chips:
  - Import the module: `from platform_topology import get_connected_port, get_all_connections_for_device, PLATFORM_TOPOLOGY`
  - Query connections programmatically: `get_connected_port("01:00.0", "ETH07")` returns the connected bus_id and ETH port
  - Get all connections for a device: `get_all_connections_for_device("01:00.0")`
  - The topology maps all ETH port connections across the 4 UBBs (32 chips total)
- Ethernet ports that connect to cable connectors are routed to other ports that are connected to cable connectors.
  - Try and infer based on failure data which Ethernet ports match up with each other (e.g., cable connector ports that fail on the same run)
- When asked to analze csv test data, do not parse the provides csv file(s) directly.
  - Run the @src/filter_failures.py script first on the given csv file to extract the failed port data
- When looking for failure patterns on connected ports, focus also on the diagnostic data in the train_status dict
- Refer to `docs/known_failure_signatures.txt` for known failure signatures and store newly found failure signatures in this file for future reference
- A non-zero `lcpll_lock_fail_cnt` is not an issue unless it results in a failure in the corresponding `test_status` but it is good to note in failure reports
- Remote device information (`remote_info` in train_status) is often not relevant to failure analysis:
  - External cable connections show `remote_pcb_type: ORION` with all-zero identifiers when no remote is detected
  - Internal connections show `remote_pcb_type: UBB` with the remote chip's board ID
  - This info provides context (internal vs external connection) but is not a key diagnostic indicator
  - Focus on training metrics (CDR unlock counts, retry counts, timeout values) rather than remote device details
- When documenting failure signatures in `docs/known_failure_signatures.txt`:
  - Always include `port_type` (e.g., CHIP_TO_QSFPDD, CHIP_TO_CHIP) and `train_mode` (e.g., AW_MANUAL_EQ, AW_ANLT_MODE) in diagnostic indicators
  - These values help identify failure patterns and correlations
  - Do NOT document speculative root causes or investigation recommendations
  - Keep descriptions factual - document only what is observed in the data
  - Avoid suggesting firmware changes, timeouts adjustments, or hardware investigations
