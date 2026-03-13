# bh-jira-retrieve User Guide

A command-line tool for downloading CSV test data attachments from Jira tickets. This tool automates the retrieval of test data files, making it easy to collect results from multiple tickets for analysis.

**Version:** 0.3.0
**Purpose:** Automated download of CSV attachments from Jira Cloud with parallel processing and progress tracking

---

## Quick Start

Get started in 5 minutes:

```bash
# 1. Configure Jira credentials (one-time setup)
cp .env.example .env
# Edit .env and add your Jira credentials

# 2. Download CSV files from specific tickets
bh-jira-retrieve --tickets SYS-123 SYS-456

# 3. Or configure tickets in config.yaml and run
bh-jira-retrieve

# 4. Files are downloaded to data/ directory
ls data/
```

---

## Installation

The tool is included in the BH Galaxy Data Analysis Tool package. Follow the installation instructions in the main [README.md](../../README.md).

After installation, the `bh-jira-retrieve` command will be available in your PATH when the virtual environment is activated:

```bash
source .venv/bin/activate
bh-jira-retrieve --help
```

---

## Basic Concepts

### Jira Authentication

The tool uses Jira Cloud API authentication with API tokens:

- **Server URL**: Your Jira instance URL (e.g., `https://yourcompany.atlassian.net`)
- **Email**: Your Atlassian account email
- **API Token**: Generated from your Atlassian account settings (not your password)

**Important**: Use API tokens, not passwords. Generate one at [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens).

### CSV Attachments

The tool automatically:
- Identifies CSV attachments on Jira tickets
- Filters for `.csv` files only
- Downloads all CSV attachments from specified tickets
- Saves with descriptive filenames: `{TICKET_KEY}_{original_filename}.csv`

### Parallel Downloads

Multiple attachments are downloaded in parallel for efficiency:
- Uses thread pool for concurrent downloads
- Progress bar shows real-time status
- Automatic retry on transient failures

---

## Command Reference

### Basic Usage

```bash
bh-jira-retrieve [OPTIONS]
```

### Options

**Ticket Specification:**

- `--tickets TICKET [TICKET ...]` - Space-separated list of Jira ticket keys (e.g., SYS-123 SYS-456)

**Output Control:**

- `--output-dir PATH` - Directory to save CSV files (default: `data/`)

**Configuration:**

- `--config PATH` - Path to configuration file (default: searches standard locations)

**Logging:**

- `--verbose, -v` - Enable verbose logging
- `--log-level LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**Help:**

- `--help` - Show help message and exit

---

## Configuration

### Environment Variables (.env)

Create a `.env` file in the project root with your Jira credentials:

```env
# Jira Cloud credentials
JIRA_SERVER_URL=https://yourcompany.atlassian.net
EMAIL=your-email@example.com
API_KEY=your-api-token-here
```

**Security Note**: The `.env` file is gitignored and never committed to version control.

### Configuration File (config.yaml)

You can specify default tickets in `config.yaml`:

```yaml
jira:
  # Optional: Override .env credentials
  server_url: https://yourcompany.atlassian.net
  email: your-email@example.com
  api_key: your-api-token

# Default tickets to retrieve
tickets:
  - SYS-123
  - SYS-456
  - SYS-789
```

**When to use which**:
- `.env` - Credentials (required, never committed)
- `config.yaml` - Default ticket lists (optional, can be committed)

### Configuration Priority

Configuration is loaded in this order (highest priority first):

1. Command-line arguments (`--tickets`)
2. Environment variable `BH_GLX_CONFIG` (for custom config file path)
3. User config: `~/.config/bh-glx-data/config.yaml`
4. Local config: `./config.yaml`

---

## Examples

### Example 1: Download from Specific Tickets

Download CSV files from specific Jira tickets:

```bash
bh-jira-retrieve --tickets SYS-123 SYS-456 SYS-789
```

**Output:**
```
Downloading CSV attachments from Jira...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 12/12 files

Download Summary:
  Tickets processed: 3
  CSV files downloaded: 12
  Total size: 8.4 MB
  Output directory: data/

Downloaded files:
  SYS-123_prbs_test_results.csv
  SYS-123_data_test_results.csv
  SYS-456_prbs_test_results.csv
  SYS-456_data_test_results.csv
  ...
```

### Example 2: Use Tickets from config.yaml

If you have tickets configured in `config.yaml`, simply run:

```bash
bh-jira-retrieve
```

This will download CSV files from all tickets listed in the configuration file.

### Example 3: Custom Output Directory

Save files to a custom directory:

```bash
bh-jira-retrieve --tickets SYS-123 --output-dir my_data/
```

Files will be saved to `my_data/` instead of the default `data/` directory.

### Example 4: Verbose Output

Enable detailed logging to see what's happening:

```bash
bh-jira-retrieve --tickets SYS-123 --verbose
```

**Verbose output shows:**
- Jira connection details
- Ticket retrieval progress
- Attachment discovery
- Download progress for each file
- Error details if any

### Example 5: Custom Config File

Use a specific configuration file:

```bash
bh-jira-retrieve --config /path/to/custom-config.yaml
```

Or set via environment variable:

```bash
export BH_GLX_CONFIG=/path/to/custom-config.yaml
bh-jira-retrieve
```

---

## Common Workflows

### Workflow 1: One-Time Setup

Initial configuration for first-time users:

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your credentials
# Use your text editor to add:
#   JIRA_SERVER_URL=https://yourcompany.atlassian.net
#   EMAIL=your-email@example.com
#   API_KEY=your-api-token

# 3. Test with a single ticket
bh-jira-retrieve --tickets SYS-123

# 4. If successful, add default tickets to config.yaml
# Edit config.yaml and add ticket list
```

### Workflow 2: Regular Data Collection

Routine workflow for collecting test data:

```bash
# 1. Update config.yaml with new tickets
# Add new ticket keys to the tickets list

# 2. Run retrieval
bh-jira-retrieve

# 3. Verify downloads
ls data/

# 4. Process data with other tools
bh-filter-failures data/SYS-123_data_test_results.csv
bh-generate-excel
```

### Workflow 3: Batch Processing Multiple Tickets

Download data from multiple related tickets:

```bash
# Download test data from all tickets in a release
bh-jira-retrieve --tickets \
  SYS-100 SYS-101 SYS-102 SYS-103 \
  SYS-104 SYS-105 SYS-106 SYS-107

# Or use bash expansion
bh-jira-retrieve --tickets SYS-{100..107}
```

### Workflow 4: Integration with Analysis Pipeline

Complete pipeline from download to analysis:

```bash
# 1. Download latest test data
bh-jira-retrieve --tickets SYS-456

# 2. Filter failures
bh-filter-failures data/SYS-456_data_test_results.csv

# 3. Ingest into analysis database
bh-analyze-systems ingest data/

# 4. Generate reports
bh-generate-excel
bh-analyze-systems export-excel --output analysis.xlsx
```

### Workflow 5: Selective Download

Download from specific tickets with custom organization:

```bash
# Create subdirectory for this test run
mkdir -p test_data/release_2_0/

# Download to custom location
bh-jira-retrieve \
  --tickets SYS-200 SYS-201 SYS-202 \
  --output-dir test_data/release_2_0/

# Files are now organized by release
ls test_data/release_2_0/
```

---

## Troubleshooting

### Authentication Failed

**Problem:**
```
ERROR: Jira authentication failed
ERROR: 401 Client Error: Unauthorized
```

**Solution:**

1. Verify credentials in `.env` file:
   - Check `JIRA_SERVER_URL` is correct
   - Verify `EMAIL` matches your Atlassian account
   - Ensure `API_KEY` is valid

2. Generate a new API token:
   - Visit https://id.atlassian.com/manage-profile/security/api-tokens
   - Create a new token
   - Update `API_KEY` in `.env`

3. Check for typos in credentials (extra spaces, newlines)

4. Verify you're using API token, not password

### Ticket Not Found

**Problem:**
```
ERROR: Ticket not found: SYS-999
```

**Solution:**

1. Verify ticket key is correct (case-sensitive)
2. Check you have permission to view the ticket
3. Ensure ticket exists in your Jira instance
4. Try accessing ticket in web browser first

### No CSV Attachments Found

**Problem:**
```
WARNING: No CSV attachments found on ticket SYS-123
```

**Solution:**

This is informational, not an error. The ticket exists but has no CSV attachments.

- Verify the ticket actually has CSV files attached
- Check if attachments are named differently (must end in `.csv`)
- Ensure attachments are accessible (not restricted)

### Connection Timeout

**Problem:**
```
ERROR: Connection timeout while accessing Jira
```

**Solution:**

1. Check internet connection
2. Verify Jira server URL is accessible
3. Check if firewall is blocking access
4. Try again later (Jira might be temporarily unavailable)
5. Increase timeout in code if needed

### Permission Denied on Output Directory

**Problem:**
```
ERROR: Permission denied: data/
```

**Solution:**

1. Create output directory if it doesn't exist:
   ```bash
   mkdir -p data/
   ```

2. Check write permissions:
   ```bash
   ls -ld data/
   chmod u+w data/
   ```

3. Use different output directory:
   ```bash
   bh-jira-retrieve --output-dir ~/my_data/
   ```

### Incomplete Downloads

**Problem:**

Download stops partway through or some files are missing.

**Solution:**

1. Check available disk space:
   ```bash
   df -h
   ```

2. Run command again (tool will skip existing files)

3. Enable verbose logging to see which file failed:
   ```bash
   bh-jira-retrieve --tickets SYS-123 --verbose
   ```

4. Download problematic ticket separately:
   ```bash
   bh-jira-retrieve --tickets SYS-123
   ```

### Environment File Not Found

**Problem:**
```
WARNING: .env file not found, using environment variables
```

**Solution:**

This warning appears if `.env` doesn't exist. Choose one approach:

**Option 1**: Create `.env` file
```bash
cp .env.example .env
# Edit .env with your credentials
```

**Option 2**: Set environment variables directly
```bash
export JIRA_SERVER_URL="https://yourcompany.atlassian.net"
export EMAIL="your-email@example.com"
export API_KEY="your-api-token"
bh-jira-retrieve --tickets SYS-123
```

### Invalid Ticket Format

**Problem:**
```
ERROR: Invalid ticket key format: sys123
```

**Solution:**

Ticket keys must be in format `PROJECT-NUMBER`:
- Correct: `SYS-123`, `PROJ-456`, `ABC-789`
- Incorrect: `sys123`, `SYS123`, `123`

Fix the ticket key format and try again.

---

## Tips and Best Practices

### Credentials Management

- **Never commit** `.env` file to version control
- **Use API tokens** instead of passwords for better security
- **Rotate tokens** periodically for security
- **Use separate tokens** for different projects/teams

### Organization

- **Use consistent naming** in Jira for CSV attachments
- **Create subdirectories** for different test runs or releases
- **Document ticket lists** in `config.yaml` with comments
- **Archive old data** to keep `data/` directory manageable

### Automation

- **Add to scripts** for automated test data collection
- **Schedule with cron** for periodic downloads
- **Combine with other tools** in data processing pipelines
- **Use config.yaml** for default tickets in automated workflows

### Performance

- **Parallel downloads** are automatic (no tuning needed)
- **Large batches** work fine (tested with 50+ tickets)
- **Network speed** is the main bottleneck
- **Resume capability**: Run again if interrupted (skips existing files)

### Troubleshooting

- **Use --verbose** for detailed output when debugging
- **Test credentials** with a single known ticket first
- **Check Jira web UI** if unsure about ticket access
- **Verify CSV format** of downloaded files before processing

### Integration

- **Download first** in your data pipeline
- **Filter next** with `bh-filter-failures` if needed
- **Then analyze** with `bh-generate-excel` or `bh-analyze-systems`
- **Keep raw data** - don't overwrite original downloads

---

## Getting Help

### Command Help

```bash
# Show help message
bh-jira-retrieve --help
```

### Verbose Logging

Enable detailed logging for troubleshooting:

```bash
bh-jira-retrieve --tickets SYS-123 --verbose

# Or set specific log level
bh-jira-retrieve --tickets SYS-123 --log-level DEBUG
```

### Common Issues

Most problems fall into these categories:
1. **Authentication** - Check credentials in `.env`
2. **Permissions** - Verify Jira access to tickets
3. **Network** - Check connection and firewall
4. **File system** - Check directory permissions and disk space

### Additional Resources

- Main README: [README.md](../../README.md)
- Project overview: [CLAUDE.md](../../CLAUDE.md)
- Migration guide: [docs/MIGRATION_GUIDE.md](../MIGRATION_GUIDE.md)
- API token setup: https://id.atlassian.com/manage-profile/security/api-tokens

---

**Last Updated:** 2026-03-12
**Tool Version:** 0.3.0
