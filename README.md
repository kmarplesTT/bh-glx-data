# BH Galaxy Data Analysis Tool

A modern Python package for collecting and analyzing test data for BH Galaxy system tests. Includes tools for Jira CSV retrieval, Quanta failure data extraction, Excel report generation, and platform topology queries.

**Version:** 0.2.0 (Alpha)
**Python:** 3.10+
**License:** MIT

---

## Installation

### Option 1: Development Installation (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd bh-glx-data

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with development dependencies
pip install -e ".[dev]"
```

### Option 2: User Installation

```bash
# Install from local directory
pip install .

# Or install from git (future)
pip install git+<repository-url>
```

After installation, all commands will be available in your PATH:

```bash
bh-glx-data --help
bh-jira-retrieve --help
bh-filter-failures --help
# ... etc
```

---

## Quick Start

### 1. Configure Environment

If planning to retrieve data from Jira, copy the example environment file and add your Jira credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
JIRA_SERVER_URL=https://your-jira-instance.atlassian.net
EMAIL=your-email@example.com
API_KEY=your-api-token
```

**Note:** For Jira Cloud, use an [API token](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/) instead of your password.

### 2. Configure Ticket List (Optional)

Edit `config.yaml` to add Jira ticket keys:

```yaml
tickets:
  - SYS-123
  - SYS-456
```

### 3. Run Your First Command

```bash
# Download CSV files from Jira
bh-jira-retrieve --tickets SYS-123 SYS-456

# Filter failures from test data
bh-filter-failures data_test_results.csv

# Generate Excel summary
bh-generate-excel --data-dir csv_data/
```

---

## CLI Reference

### Unified Command Interface

The tool provides a unified `bh-glx-data` command with subcommands:

```bash
bh-glx-data <command> [options]
```

**Global Options:**

- `--verbose, -v` - Enable verbose logging
- `--log-level` - Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--version` - Show version information
- `--help` - Show help message

**Available Commands:**

- `jira-retrieve` - Download CSV attachments from Jira
- `filter-failures` - Filter failed test rows from CSV
- `generate-excel` - Generate Excel summaries
- `extract-quanta` - Extract data from Quanta packages
- `topology` - Query platform topology

**Direct Shortcuts:**

For convenience, each command is also available as a standalone script:

```bash
bh-jira-retrieve     # Same as: bh-glx-data jira-retrieve
bh-filter-failures   # Same as: bh-glx-data filter-failures
bh-generate-excel    # Same as: bh-glx-data generate-excel
bh-extract-quanta    # Same as: bh-glx-data extract-quanta
bh-topology          # Same as: bh-glx-data topology
```

---

## Usage Examples

### Jira CSV Retrieval

Download CSV attachments from Jira tickets:

```bash
# Download from specific tickets
bh-jira-retrieve --tickets SYS-123 SYS-456 SYS-789

# Use tickets from config.yaml
bh-jira-retrieve

# Custom output directory
bh-jira-retrieve --tickets SYS-123 --output-dir my_data/

# View detailed help
bh-jira-retrieve --help
```

**What it does:**

1. Authenticates with Jira using credentials from `.env`
2. Retrieves specified tickets
3. Downloads all CSV attachments
4. Saves to `data/` directory (default)
5. Displays download summary

### Filter Test Failures

Extract only failed test rows from CSV files:

```bash
# Filter failures from test data
bh-filter-failures data_test_results.csv

# Specify custom output file
bh-filter-failures data_test_results.csv --output failures.csv

# Use custom status column
bh-filter-failures test.csv --status-column custom_status

# View help
bh-filter-failures --help
```

**What it does:**

- Identifies rows where `test_status` ≠ `ETH_ACTIVE` or `ETH_UNCONNECTED`
- Creates new CSV with only failures
- Displays failure breakdown by status type

**Example Output:**

```text
Total rows read: 12800
Failures found: 2426
Failures written to: data_test_results_failures.csv

Failure breakdown by test_status:
  TRAINING_FAIL: 2426
```

### Excel Summary Generation

Generate organized Excel reports with pivot tables:

```bash
# Process all systems
bh-generate-excel

# Process specific systems
bh-generate-excel --systems bh-glx-b02u02 bh-glx-b03u02

# Custom directories
bh-generate-excel --data-dir csv_data/ --output-dir summaries/

# Custom template
bh-generate-excel --template my_template.xlsx

# View help
bh-generate-excel --help
```

**What it does:**

1. Scans CSV files in data directory
2. Groups by system hostname and firmware version
3. Separates PRBS and Data test types
4. Compiles data from multiple CSV files
5. Generates Excel files with pivot tables
6. Saves to `summaries/` directory

**Output:** `{hostname}_{firmware_version}.xlsx` (e.g., `bh-glx-b02u02_erisc_v1_7_103.xlsx`)

### Quanta QC3 Data Extraction

Extract test data from Quanta QC3 test packages:

```bash
# Extract from tar.gz archive
bh-extract-quanta QC3_UBB_20260128.tar.gz

# Custom output directory
bh-extract-quanta QC3_UBB_20260128.tar.gz --output-dir quanta_data/

# Analyze Excel file for failures
bh-extract-quanta --analyze QC3_S7TK_0128_build_test.xlsx

# View help
bh-extract-quanta --help
```

**What it does:**

- Opens tar.gz archive
- Extracts nested tar.gz files
- Finds `data_test_*.csv` and `prbs_test_*.csv` files
- Saves with descriptive names to `quanta/` directory

**Analyze Mode:**

- Reads Excel file
- Identifies non-zero failure counts
- Extracts serial numbers of failed systems
- Displays failure summary

### Platform Topology Queries

Query ETH port connectivity between chips and QSFP port mappings:

```bash
# Query specific platform connection
bh-topology 01:00.0 ETH07

# Query QSFP port mapping (for cable connector ports)
bh-topology 01:00.0 ETH10

# Query with cable configuration (NEW)
bh-topology 01:00.0 ETH10 qc3                    # Named config
bh-topology 01:00.0 ETH10 ./cables/custom.yaml   # File path

# Show all connections for a device
bh-topology 01:00.0 --all

# JSON output for scripting
bh-topology 01:00.0 ETH07 --json
bh-topology 01:00.0 ETH10 qc3 --json

# Bidirectional lookup
bh-topology 05:00.0 ETH00 --bidirectional

# View help
bh-topology --help
```

**Cable Configuration Support:**

The topology tool now supports cable configuration files that define how external cables connect QSFP ports. This enables full device-to-device path tracing through cable connections.

Cable configurations can be specified as:

- **Named configs**: Searched in `~/.config/bh-glx-data/cables/` and `./cables/`
- **File paths**: Relative or absolute paths to YAML configuration files

Example cable configuration (`cables/qc3.yaml`):

```yaml
UBB1:
  - QSFP-1 <> QSFP-2
  - QSFP-7 <> QSFP-8
UBB2:
  - QSFP-1 <> QSFP-2
  - QSFP-7 <> QSFP-8
```

**Example Output:**

```
# Platform connection
UBB1/U1 (01:00.0) ETH07 -> UBB1/U5 (05:00.0) ETH00

# QSFP mapping (without cable config)
UBB1/U1 (01:00.0) ETH10 -> UBB1 QSFP-7

# Full cable path (with cable config)
01:00.0 ETH10 -> QSFP-7 <-> QSFP-8 -> 05:00.0 ETH10
```

---

## Configuration

### Multi-Source Configuration

Configuration is loaded from multiple sources in priority order:

1. **Command-line arguments** (highest priority)
2. **Environment variables** (`BH_GLX_CONFIG` for config file path)
3. **User config**: `~/.config/bh-glx-data/config.yaml`
4. **Local config**: `./config.yaml`
5. **Built-in defaults** (lowest priority)

### Configuration File Format

`config.yaml`:

```yaml
jira:
  # These can also be set via .env file
  server_url: https://your-jira.atlassian.net
  email: your-email@example.com
  api_key: your-api-token

tickets:
  - SYS-123
  - SYS-456

data:
  input_dir: csv_data
  output_dir: summaries
```

### Environment Variables

Create `.env` file:

```env
# Jira credentials
JIRA_SERVER_URL=https://your-jira-instance.atlassian.net
EMAIL=your-email@example.com
API_KEY=your-api-token

# Optional: Custom config file location
BH_GLX_CONFIG=/path/to/config.yaml
```

---

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_hardware.py

# Run integration tests only
pytest tests/integration/

# Run in parallel
pytest -n auto
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
pylint src/bh_glx_data/

# Type check
mypy src/bh_glx_data/
```

---

## Migration from Old Scripts

**Note:** The old Python scripts in `src/` still work but are deprecated. They will show a deprecation warning when run.

### Old → New Command Mapping

| Old Command | New Command |
|-------------|-------------|
| `python3 src/jira_csv_retriever.py` | `bh-jira-retrieve` |
| `python3 src/filter_failures.py` | `bh-filter-failures` |
| `python3 src/excel_summary_generator.py` | `bh-generate-excel` |
| `python3 src/extract_quanta_failures.py` | `bh-extract-quanta` |
| `python3 src/platform_topology.py` | `bh-topology` |

**See [MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md) for detailed migration instructions.**

---

## Troubleshooting

### Installation Issues

**Problem:** `pip install` fails with "requires Python >=3.10"
**Solution:** Upgrade Python or use a Python 3.10+ virtual environment

**Problem:** Entry points not available after install
**Solution:** Ensure you're using `pip install` (not `python setup.py install`)

### Runtime Issues

**Problem:** "Module not found" errors
**Solution:** Ensure package is installed: `pip install -e .`

**Problem:** Jira authentication fails
**Solution:** Verify `.env` file exists with correct credentials and API token (not password)

**Problem:** Template file not found
**Solution:** Ensure `templates/system_data_template.xlsx` exists in project root

### Getting Help

```bash
# View general help
bh-glx-data --help

# View command-specific help
bh-jira-retrieve --help
bh-filter-failures --help
# ... etc

# Enable verbose logging
bh-glx-data --verbose <command> [options]

# Set debug logging
bh-glx-data --log-level DEBUG <command> [options]
```

---

## Changelog

### Version 0.2.0 (2026-03-10)

**New Features**:

- ✨ Cable configuration support for full device-to-device path tracing
  - Added `CableConfigManager` class for loading and managing cable configurations
  - New `get_cable_path()` function to resolve complete signal paths through cables
  - New `get_eth_ports_for_qsfp()` function for reverse QSFP lookups
  - Support for named configurations (searched in standard directories)
  - Support for explicit file paths (relative or absolute)
  - YAML-based configuration format with bidirectional cable mapping
  - Enhanced `bh-topology` CLI with optional cable configuration argument
  - Comprehensive validation (YAML syntax, UBB sections, QSFP port numbers)
  - New documentation: `docs/cable_configuration.md`
  - 22 new unit tests for cable configuration
  - 18 new tests for enhanced topology features
  - 100% backward compatibility maintained

**Example**:
```bash
bh-topology 01:00.0 ETH10 qc3
# Output: 01:00.0 ETH10 -> QSFP-7 <-> QSFP-8 -> 05:00.0 ETH10
```

### Version 0.1.1 (2026-03-09)

**New Features**:

- ✨ QSFP port mapping for cable connector ports
  - Added `get_qsfp_port()` function to query QSFP port numbers
  - Cable connector ports now display QSFP mappings (QSFP-1 through QSFP-14)
  - Updated `bh-topology` CLI to show QSFP port connections
  - Comprehensive test coverage for all 14 QSFP port mappings

### Version 0.1.0 (2026-03-05)

**Initial Release**:

- ✨ Modern Python package with src layout
- ✨ Unified CLI with subcommands
- ✨ 5 domain modules with clear boundaries
- ✨ Comprehensive error handling
- ✨ Data models with type safety
- ✨ Multi-source configuration management
- ✨ Comprehensive test suite
- ⚠️ Backwards compatible with old scripts (deprecated)

---

**Last Updated:** 2026-03-10
**Package Version:** 0.2.0
