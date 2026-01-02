# BH Galaxy Data Analysis Tool

A Python tool to collect and analyze csv data from Jira for BH Galaxy system tests

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
python jira_csv_retriever.py --help
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
python excel_summary_generator.py --help
```

Output files are named `{hostname}_{firmware_version}.xlsx` (e.g., `bh-glx-b02u02_erisc_v1_7_103.xlsx`)

## Project Structure

```text
data_collection/
├── .env.example          # Template for environment variables (safe to commit)
├── .env                  # Actual credentials (gitignored - never committed)
├── config.yaml           # Ticket list and configuration (safe to commit)
├── .gitignore           # Ignore virtual env, .env, and downloaded files
├── requirements.txt     # Python dependencies
├── README.md            # Project documentation
├── jira_csv_retriever.py # Main script to retrieve CSV files from Jira
├── excel_summary_generator.py # Script to generate Excel summaries from CSV data
├── system_data_template.xlsx # Excel template with pivot tables
├── data_analyzer.py     # Module for analyzing CSV data and finding patterns
├── report_generator.py  # Module for generating debug reports
├── config.py            # Configuration management
├── data/                # Directory for downloaded CSV files (gitignored)
└── summaries/            # Directory for generated Excel summary files (gitignored)
```

## Security

- Credentials are stored in `.env` file which is gitignored
- Never commit the `.env` file to version control
- `config.yaml` contains only ticket keys (no secrets) and can be safely committed
- Use API tokens instead of passwords for Jira Cloud instances

## Requirements

- Python 3.10+
- Jira account with appropriate permissions to access tickets and attachments
