# bh-generate-excel User Guide

A command-line tool for generating organized Excel summary reports from test data CSV files. This tool automatically groups data by system and firmware version, creates multi-sheet workbooks, and includes pivot tables for analysis.

**Version:** 0.3.0
**Purpose:** Automated Excel report generation with pivot tables for test data analysis and sharing

---

## Quick Start

Get started in 5 minutes:

```bash
# 1. Ensure you have CSV test data files in data/ directory
ls data/*.csv

# 2. Generate Excel summaries for all systems
bh-generate-excel

# 3. View generated reports
ls summaries/*.xlsx

# 4. Generate for specific systems only
bh-generate-excel --systems bh-glx-b02u02 bh-glx-b03u02
```

---

## Installation

The tool is included in the BH Galaxy Data Analysis Tool package. Follow the installation instructions in the main [README.md](../../README.md).

After installation, the `bh-generate-excel` command will be available in your PATH when the virtual environment is activated:

```bash
source .venv/bin/activate
bh-generate-excel --help
```

---

## Basic Concepts

### Data Grouping

The tool automatically groups CSV files by:
1. **Hostname** - System identifier (extracted from `host` column)
2. **Firmware Version** - Firmware version (extracted from filename)
3. **Test Type** - PRBS vs. Data tests (from `test_type` column or filename)

This creates one Excel file per (hostname, firmware_version) combination.

### Excel Structure

Each generated Excel workbook contains:

**Sheets:**
1. `raw prbs data` - All PRBS test data rows
2. `raw data` - All Data test data rows
3. `PRBS Summary` - Pivot table for PRBS tests
4. `DATA Summary` - Pivot table for Data tests

**Features:**
- Pre-configured pivot tables for instant analysis
- Multiple CSV files combined into single workbook
- Test types automatically separated
- Template-based formatting

### Template System

The tool uses a template file (`system_data_template.xlsx`) that provides:
- Pre-defined sheet structure
- Configured pivot tables
- Formatting and layout
- Column definitions

The template is populated with your data and pivot table sources are updated automatically.

---

## Command Reference

### Basic Usage

```bash
bh-generate-excel [OPTIONS]
```

### Options

**System Selection:**

- `--systems SYSTEM [SYSTEM ...]` - Process only specified systems (by hostname)

**Directory Configuration:**

- `--data-dir PATH` - Directory containing CSV files (default: `data/`)
- `--output-dir PATH` - Directory for Excel output (default: `summaries/`)

**Template:**

- `--template PATH` - Path to Excel template file (default: `templates/system_data_template.xlsx`)

**Configuration:**

- `--config PATH` - Path to configuration file (default: searches standard locations)

**Logging:**

- `--verbose, -v` - Enable verbose logging
- `--log-level LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**Help:**

- `--help` - Show help message and exit

---

## Examples

### Example 1: Generate All System Reports

Process all CSV files and generate Excel summaries for all systems:

```bash
bh-generate-excel
```

**Output:**
```
Generating Excel summaries...

Processing system: bh-glx-b02u02, firmware: erisc_v1_7_103
  Found 4 PRBS CSV files
  Found 2 Data CSV files
  Generated: summaries/bh-glx-b02u02_erisc_v1_7_103.xlsx

Processing system: bh-glx-b03u02, firmware: erisc_v1_7_103
  Found 4 PRBS CSV files
  Found 2 Data CSV files
  Generated: summaries/bh-glx-b03u02_erisc_v1_7_103.xlsx

Summary:
  Systems processed: 2
  Excel files generated: 2
  Output directory: summaries/
```

### Example 2: Generate for Specific Systems

Generate reports for specific systems only:

```bash
bh-generate-excel --systems bh-glx-b02u02 bh-glx-b03u02
```

This processes only the specified systems, ignoring data from other systems in the `data/` directory.

### Example 3: Custom Directories

Use custom input and output directories:

```bash
bh-generate-excel \
  --data-dir test_data/release_2_0/ \
  --output-dir reports/release_2_0/
```

**What this does**:
- Reads CSV files from `test_data/release_2_0/`
- Writes Excel files to `reports/release_2_0/`
- Useful for organizing different test runs or releases

### Example 4: Custom Template

Use a custom Excel template:

```bash
bh-generate-excel --template custom_templates/my_template.xlsx
```

The custom template should have the same sheet structure as the default template:
- `raw prbs data` sheet with data table
- `raw data` sheet with data table
- `PRBS Summary` sheet with pivot table
- `DATA Summary` sheet with pivot table

### Example 5: Verbose Output

See detailed processing information:

```bash
bh-generate-excel --verbose
```

**Verbose output shows:**
```
INFO: Scanning CSV files in: data/
INFO: Found 24 CSV files
INFO: Grouping by hostname and firmware version...
INFO: Groups identified: 2

INFO: Processing group: bh-glx-b02u02 / erisc_v1_7_103
INFO: PRBS files:
  - data/SYS-123_prbs_test_bh-glx-b02u02.csv
  - data/SYS-124_prbs_test_bh-glx-b02u02.csv
  - data/SYS-125_prbs_test_bh-glx-b02u02.csv
  - data/SYS-126_prbs_test_bh-glx-b02u02.csv
INFO: Data files:
  - data/SYS-123_data_test_bh-glx-b02u02.csv
  - data/SYS-124_data_test_bh-glx-b02u02.csv
INFO: Reading template: templates/system_data_template.xlsx
INFO: Compiling PRBS data... (12,800 rows)
INFO: Compiling Data test data... (8,400 rows)
INFO: Updating pivot table sources...
INFO: Saving workbook: summaries/bh-glx-b02u02_erisc_v1_7_103.xlsx
INFO: Complete

Processing system: bh-glx-b02u02, firmware: erisc_v1_7_103
  Found 4 PRBS CSV files
  Found 2 Data CSV files
  Generated: summaries/bh-glx-b02u02_erisc_v1_7_103.xlsx
```

---

## Understanding the Output

### File Naming

Excel files are named: `{hostname}_{firmware_version}.xlsx`

**Examples:**
- `bh-glx-b02u02_erisc_v1_7_103.xlsx`
- `bh-glx-c01u01_v1_7_105.xlsx`

**Why this format?**
- Easy identification of system and firmware
- Groups related test data together
- Sorts naturally in file browsers
- Unique per system/firmware combination

### Sheet Contents

**1. raw prbs data Sheet**

Contains all PRBS test data rows from all CSV files:
- All columns from original CSV files
- Data from multiple tickets combined
- Ready for custom analysis
- Source for PRBS Summary pivot table

**2. raw data Sheet**

Contains all Data test data rows from all CSV files:
- Simple packet test results
- Multiple sources combined
- Source for DATA Summary pivot table

**3. PRBS Summary Sheet**

Pivot table analyzing PRBS tests:
- Automatically configured
- Common metrics pre-calculated
- Filterable and customizable
- Refresh after data changes

**4. DATA Summary Sheet**

Pivot table analyzing Data tests:
- Pre-configured for common views
- Drill-down capability
- Exportable to charts

### Pivot Table Features

**Default Configuration:**
- Rows: System identifiers, test parameters
- Columns: Test metrics
- Values: Counts, pass rates, statistics
- Filters: Test type, speed, status

**Customization:**
- Drag and drop fields to reorganize
- Add calculated fields
- Create custom filters
- Generate charts from pivot data

**Refreshing:**
If you modify raw data sheets, right-click pivot table and select "Refresh".

---

## Common Workflows

### Workflow 1: Standard Reporting

Regular workflow for generating test reports:

```bash
# 1. Download latest test data
bh-jira-retrieve --tickets SYS-200 SYS-201 SYS-202

# 2. Generate Excel summaries
bh-generate-excel

# 3. Open and review reports
open summaries/*.xlsx

# 4. Share reports with team
# Email or upload Excel files
```

### Workflow 2: Release Validation

Compare systems for a release:

```bash
# 1. Download release test data
bh-jira-retrieve --tickets SYS-300 SYS-301 SYS-302 \
  --output-dir release_3_0/

# 2. Generate reports
bh-generate-excel \
  --data-dir release_3_0/ \
  --output-dir reports/release_3_0/

# 3. Compare pivot tables across systems
# Open all Excel files
# Review PRBS and Data summaries side-by-side
```

### Workflow 3: Failure Analysis

Focus on failures with filtered data:

```bash
# 1. Filter failures from test data
for file in data/*.csv; do
    bh-filter-failures "$file"
done

# 2. Move failure files to separate directory
mkdir -p failures/
mv data/*_failures.csv failures/

# 3. Generate Excel reports from failures only
bh-generate-excel \
  --data-dir failures/ \
  --output-dir failure_reports/

# 4. Review failure patterns in Excel
# Use pivot tables to identify systematic issues
```

### Workflow 4: Multi-Firmware Comparison

Compare different firmware versions:

```bash
# Assuming data directory has CSV files with different firmware versions:
# - Files with v1_7_103 in filename
# - Files with v1_7_105 in filename

# Generate reports (automatically creates separate files per firmware)
bh-generate-excel

# Result:
# summaries/bh-glx-b02u02_v1_7_103.xlsx
# summaries/bh-glx-b02u02_v1_7_105.xlsx

# Open both for side-by-side comparison
```

### Workflow 5: Selective System Reporting

Generate reports for subset of systems:

```bash
# Only process specific systems of interest
bh-generate-excel --systems \
  bh-glx-b02u02 \
  bh-glx-b03u02 \
  bh-glx-c01u01

# Faster than processing all systems
# Useful for focused analysis
```

### Workflow 6: Automated Pipeline

Integrate into automated test reporting:

```bash
#!/bin/bash
# automated_reporting.sh

# Configuration
TICKETS="SYS-400 SYS-401 SYS-402"
DATE=$(date +%Y%m%d)
OUTPUT_DIR="reports/${DATE}"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Download data
bh-jira-retrieve --tickets ${TICKETS}

# Generate Excel reports
bh-generate-excel --output-dir "${OUTPUT_DIR}"

# Archive data
tar -czf "archive/data_${DATE}.tar.gz" data/

# Upload to shared location
# rsync -av "${OUTPUT_DIR}/" /shared/reports/

echo "Reports generated: ${OUTPUT_DIR}"
```

---

## Troubleshooting

### Template Not Found

**Problem:**
```
ERROR: Template file not found: templates/system_data_template.xlsx
```

**Solution:**

1. Verify template exists:
   ```bash
   ls templates/system_data_template.xlsx
   ```

2. If missing, restore from repository:
   ```bash
   git checkout templates/system_data_template.xlsx
   ```

3. Or specify custom template:
   ```bash
   bh-generate-excel --template /path/to/template.xlsx
   ```

### No CSV Files Found

**Problem:**
```
WARNING: No CSV files found in data/
```

**Solution:**

1. Check data directory exists and has CSV files:
   ```bash
   ls data/*.csv
   ```

2. Download test data first:
   ```bash
   bh-jira-retrieve --tickets SYS-123
   ```

3. Use correct data directory:
   ```bash
   bh-generate-excel --data-dir /path/to/csv/files/
   ```

### Missing Required Columns

**Problem:**
```
ERROR: CSV missing required column: host
ERROR: CSV missing required column: test_type
```

**Solution:**

1. Verify CSV has required columns:
   - `host` - System hostname
   - `test_type` - Test type identifier

2. Check CSV headers:
   ```bash
   head -1 data/test_file.csv
   ```

3. Ensure CSV files are from correct source (Jira tickets or Quanta packages)

4. If `test_type` column missing, tool will try to infer from filename (e.g., `prbs_test`, `data_test`)

### Cannot Extract Firmware Version

**Problem:**
```
WARNING: Cannot extract firmware version from filename: test_data.csv
```

**Solution:**

CSV filenames must contain firmware version pattern:
- Format: `v1_7_103` or `erisc_v1_7_103`
- Example: `SYS-123_prbs_test_erisc_v1_7_103.csv`

Rename files to include firmware version or use Jira retrieval which preserves naming.

### Permission Denied on Output

**Problem:**
```
ERROR: Permission denied: summaries/
```

**Solution:**

1. Create output directory:
   ```bash
   mkdir -p summaries/
   ```

2. Check permissions:
   ```bash
   ls -ld summaries/
   chmod u+w summaries/
   ```

3. Use different output directory:
   ```bash
   bh-generate-excel --output-dir ~/reports/
   ```

### Excel File Locked or Corrupted

**Problem:**
```
ERROR: Cannot write to Excel file (file may be open)
```

**Solution:**

1. Close Excel file if open
2. Delete existing file and regenerate:
   ```bash
   rm summaries/bh-glx-b02u02_erisc_v1_7_103.xlsx
   bh-generate-excel
   ```
3. Use different output directory as workaround

### Pivot Table Not Updating

**Problem:**

Pivot table shows old data after regenerating Excel file.

**Solution:**

This shouldn't happen as tool updates pivot table sources. If it does:

1. Manually refresh pivot table:
   - Right-click pivot table
   - Select "Refresh"

2. Verify data is in raw sheets:
   - Check `raw prbs data` and `raw data` sheets
   - Ensure rows are populated

3. Regenerate file with verbose mode:
   ```bash
   rm summaries/problematic_file.xlsx
   bh-generate-excel --verbose
   ```

### Large Files Slow to Generate

**Problem:**

Excel generation takes a long time for large datasets.

**Solution:**

This is normal for large data volumes. The tool is processing:
- Reading multiple CSV files
- Combining data
- Writing Excel sheets
- Updating pivot table sources

**Expected times:**
- Small (1-5 CSV files, <10K rows): 5-15 seconds
- Medium (5-10 CSV files, 10-50K rows): 15-60 seconds
- Large (10+ CSV files, 50K+ rows): 1-5 minutes

Use `--verbose` to see progress.

---

## Tips and Best Practices

### File Organization

- **Consistent naming** - Use Jira retrieval for consistent CSV naming
- **Separate directories** - Use different directories for different test runs
- **Archive old data** - Move old CSV files to archive after Excel generation
- **Backup templates** - Keep original template file safe

### Data Preparation

- **Download first** - Always use `bh-jira-retrieve` to get data
- **Filter if needed** - Use `bh-filter-failures` before Excel generation for failure-focused reports
- **Verify data** - Check CSV files have expected columns
- **Group logically** - Keep related test data in same directory

### Excel Usage

- **Don't modify raw sheets** - Keep original data intact
- **Customize pivot tables** - Drag fields to create custom views
- **Create charts** - Use pivot table data for charts
- **Save variants** - SaveAs different filename for custom analysis
- **Refresh after edits** - Right-click pivot tables and refresh if you edit raw data

### Performance

- **Process subsets** - Use `--systems` to process specific systems
- **Separate runs** - Split large batches into multiple runs
- **SSD recommended** - I/O intensive operation
- **Close Excel** - Ensure Excel files aren't open during generation

### Template Customization

The template can be customized for your needs:

1. Open `templates/system_data_template.xlsx`
2. Modify pivot table configuration:
   - Change fields shown
   - Adjust filters
   - Customize formatting
3. Keep sheet names unchanged:
   - `raw prbs data`
   - `raw data`
   - `PRBS Summary`
   - `DATA Summary`
4. Save and use with `--template` option

### Integration

- **Pipeline component** - Run after data collection, before distribution
- **Automate** - Include in scripts for regular reporting
- **Combine tools** - Use with filter-failures for focused reports
- **Schedule** - Run via cron for periodic report generation
- **Archive** - Keep generated reports for historical comparison

### Quality Checks

- **Verify counts** - Check row counts match expectations
- **Spot check data** - Review a few rows in raw sheets
- **Test pivot tables** - Ensure pivot tables refresh correctly
- **Compare to source** - Verify Excel data matches CSV source
- **Check all systems** - Ensure all expected systems have reports

---

## Advanced Usage

### Custom Pivot Table Views

After generating Excel files, customize pivot tables:

**Example: Failure Rate by Port**
1. Open Excel file
2. Go to PRBS Summary sheet
3. In pivot table:
   - Rows: Add `eth_port`
   - Values: Add count of `test_status`
   - Filter: Show only failures
4. Sort by count descending

**Example: BER Statistics by Speed**
1. Go to PRBS Summary
2. Configure:
   - Rows: `train_speed`
   - Values: Average of BER columns
   - Format: Scientific notation
3. Compare BER across speeds

### Combining Multiple Reports

Compare multiple systems:

1. Generate reports for all systems
2. Open multiple Excel files
3. Create new workbook
4. Copy pivot tables from each file
5. Arrange side-by-side for comparison

Or use Excel's consolidate feature to combine data.

### Exporting Pivot Table Data

To export pivot table results:

1. Right-click pivot table
2. Select "Show Details" to create new sheet with filtered data
3. Save As CSV for further analysis
4. Or copy to other tools

### Creating Charts

Generate charts from pivot tables:

1. Select pivot table
2. Insert → PivotChart
3. Choose chart type (bar, line, etc.)
4. Customize appearance
5. Charts auto-update when pivot table refreshes

---

## Getting Help

### Command Help

```bash
# Show help message
bh-generate-excel --help
```

### Verbose Logging

Enable detailed logging for troubleshooting:

```bash
bh-generate-excel --verbose

# Or set specific log level
bh-generate-excel --log-level DEBUG
```

### Common Questions

**Q: Can I generate PDF instead of Excel?**
A: Not directly. Generate Excel then export to PDF from Excel/LibreOffice.

**Q: Can I modify the pivot table configuration?**
A: Yes, customize the template file or modify generated Excel files.

**Q: Why separate files per system/firmware?**
A: Keeps reports manageable and makes it easy to share specific results.

**Q: Can I combine PRBS and Data tests in one pivot?**
A: They're on separate sheets, but you can create custom pivot combining both.

**Q: How do I add custom calculations?**
A: In Excel, add calculated fields to pivot tables or formulas in new columns.

### Additional Resources

- Main README: [README.md](../../README.md)
- Project overview: [CLAUDE.md](../../CLAUDE.md)
- Jira retrieval: [bh-jira-retrieve.md](bh-jira-retrieve.md)
- Failure filtering: [bh-filter-failures.md](bh-filter-failures.md)
- System analysis: [bh-analyze-systems.md](bh-analyze-systems.md)

---

**Last Updated:** 2026-03-12
**Tool Version:** 0.3.0
