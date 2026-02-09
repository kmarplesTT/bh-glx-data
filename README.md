# BH Galaxy Data Analysis Tool

A collection of Python tools to collect and analyze test data for BH Galaxy system tests, including Jira CSV retrieval, Quanta failure data extraction, and Excel report generation

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your Jira credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your Jira credentials:

```env
JIRA_SERVER_URL=https://your-jira-instance.atlassian.net
EMAIL=your-email@example.com
API_KEY=your-api-token
```

**Note**: For Jira Cloud, you'll need to use an [API token](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/) instead of your password.

### 3. Configure Ticket List

Edit `config.yaml` and add your Jira ticket keys to the `tickets` list

## Usage

### Basic Usage

The script will:

1. Authenticate with Jira using credentials from your `.env` file
2. Retrieve each ticket specified in `config.yaml`
3. Find all CSV attachments on each ticket
4. Download CSV files to the `data/` directory
5. Display a summary of results

View help for usage instructions

```bash
python3 src/jira_csv_retriever.py --help
```

### Excel Summary Generation

After downloading CSV files, use the Excel summary generator to create organized Excel files with pivot tables:

The script will:

1. Scan all CSV files in the `data/` directory
2. Group files by system hostname and firmware version
3. Separate PRBS and Data test types
4. Compile data from multiple CSV files for each system+firmware combination
5. Generate Excel files using the `system_data_template.xlsx` template
6. Update pivot table data sources automatically
7. Save output files to the `summaries/` directory
View help for usage instructions:

```bash
python3 src/excel_summary_generator.py --help
```

Output files are named `{hostname}_{firmware_version}.xlsx` (e.g., `bh-glx-b02u02_erisc_v1_7_103.xlsx`)

### Platform Topology Utility

Query the ETH port connectivity between chips (PCIe devices) on the BH Galaxy platform. The platform consists of 4 UBBs with 8 chips each (U1-U8), where each chip has 14 ETH ports.

```bash
# Query a specific connection
python3 src/platform_topology.py 01:00.0 ETH07

# Show all connections for a device
python3 src/platform_topology.py 01:00.0 --all

# View detailed help and examples
python3 src/platform_topology.py --help
```

The utility can be used as a CLI tool or imported as a Python module for programmatic access to the topology data.

### Quanta Failure Data Extraction

Extract test data (CSV files) for failed systems from Quanta QC3 test packages. Quanta is the manufacturing partner that provides QC3 test results in zip file packages. This tool automates the process of:

1. Unzipping QC3 test packages
2. Analyzing Excel results to identify systems with failures
3. Extracting test CSV files from nested tar.gz archives
4. Organizing output by system serial number

```bash
# Extract failure data from a QC3 test package
python3 src/extract_quanta_failures.py QC3_UBB_20260128_build.zip

# Specify custom output directory
python3 src/extract_quanta_failures.py QC3_UBB_20260128_build.zip --output-dir my_failures/

# View help
python3 src/extract_quanta_failures.py --help
```

The tool will:

- Scan the Excel file (e.g., `QC3_S7TK_0128_build_test.xlsx`) for non-zero failure counts
- Find directories matching the failed serial numbers
- Extract `data_test_*.csv` and `prbs_test_*.csv` files from nested archives
- Save files to `quanta/` directory (default) with descriptive names

**File Organization:**

```
QC3_*.zip
├── QC3_*_test.xlsx                   (analyzed for failures)
└── 0130/{SN1}_{SN2}_{SN3}_{SN4}/
    └── QC3_UBB_*.tar.gz
        └── tt_funtest_ubb_*/
            └── ft_eth_stress_*.tar.gz
                └── ft_eth_stress/
                    ├── data_test_*.csv  (extracted)
                    └── prbs_test_*.csv  (extracted)
```

### Filter Test Failures

Filter and extract only the failed test rows from CSV test data files. This utility helps isolate problematic test cases for detailed analysis by identifying rows where the `test_status` column indicates a failure (any value other than `ETH_ACTIVE` or `ETH_UNCONNECTED`).

```bash
# Filter failures from a test data CSV file
python3 src/filter_failures.py data_test_results.csv

# Specify custom output file location
python3 src/filter_failures.py data_test_results.csv --output failures.csv

# View help
python3 src/filter_failures.py --help
```

The tool will:

- Read the input CSV file containing test data
- Identify all rows where `test_status` is not `ETH_ACTIVE` or `ETH_UNCONNECTED`
- Write failures to a new CSV file (default: `<input>_failures.csv`)
- Display a summary breakdown of failure types

**Example output:**

```
INFO - Total rows read: 12800
INFO - Failures found: 2426
INFO - Failures written to: data_test_results_failures.csv

Failure breakdown by test_status:
  TRAINING_FAIL: 2426
```

## Project Structure

```text
bh-glx-data/
├── src/                          # Source code
│   ├── __init__.py
│   ├── config.py                 # Configuration management
│   ├── jira_csv_retriever.py    # Script to retrieve CSV files from Jira
│   ├── excel_summary_generator.py # Script to generate Excel summaries
│   ├── extract_quanta_failures.py # Script to extract failure data from QC3 packages
│   ├── filter_failures.py        # Filter failed test rows from CSV files
│   ├── analyze_failures.py       # Analyze Excel files for failures
│   ├── platform_topology.py      # Platform connectivity mapping
│   └── validate_topology.py      # Topology validation utility
├── templates/                    # Excel templates
│   └── system_data_template.xlsx # Template with pivot tables
├── docs/                         # Documentation and diagrams
├── data/                         # Downloaded CSV files from Jira (gitignored)
├── summaries/                    # Generated Excel reports (gitignored)
├── quanta/                       # Extracted Quanta failure CSV files (gitignored)
├── .env.example                  # Template for environment variables
├── .env                          # Actual credentials (gitignored)
├── config.yaml                   # Ticket list configuration
├── requirements.txt              # Python dependencies
├── README.md                     # Project documentation
├── CLAUDE.md                     # Instructions for Claude Code
└── .gitignore                    # Git ignore rules
```

## Security

- Credentials are stored in `.env` file which is gitignored
- Never commit the `.env` file to version control
- `config.yaml` contains only ticket keys (no secrets) and can be safely committed
- Use API tokens instead of passwords for Jira Cloud instances

## Requirements

- Python 3.10+
- Jira account with appropriate permissions to access tickets and attachments
