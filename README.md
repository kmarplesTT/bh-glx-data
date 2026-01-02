# Jira CSV Data Analysis Tool

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
JIRA_USERNAME=your-email@example.com
JIRA_PASSWORD=your-api-token-or-password
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

**Process all tickets listed under `tickets` in `config.yaml`**

```bash
python jira_csv_retriever.py
```

**Process a single ticket:**

```bash
python jira_csv_retriever.py SYS-2826
```

**Process multiple tickets:**

```bash
python jira_csv_retriever.py SYS-2826 SYS-2827 SYS-2828
```

**View help:**

```bash
python jira_csv_retriever.py --help
```

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
├── data_analyzer.py     # Module for analyzing CSV data and finding patterns
├── report_generator.py  # Module for generating debug reports
├── config.py            # Configuration management
└── data/                # Directory for downloaded CSV files (gitignored)
```

## Security

- Credentials are stored in `.env` file which is gitignored
- Never commit the `.env` file to version control
- `config.yaml` contains only ticket keys (no secrets) and can be safely committed
- Use API tokens instead of passwords for Jira Cloud instances

## Requirements

- Python 3.7+
- Jira account with appropriate permissions to access tickets and attachments
