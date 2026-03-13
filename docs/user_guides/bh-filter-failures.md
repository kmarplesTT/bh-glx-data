# bh-filter-failures User Guide

A command-line tool for extracting failed test rows from CSV test data files. This tool helps isolate failures for detailed analysis by filtering out passing tests and creating focused failure datasets.

**Version:** 0.3.0
**Purpose:** Extract and analyze test failures from CSV test data with detailed failure breakdown

---

## Quick Start

Get started in 5 minutes:

```bash
# 1. Filter failures from a test data file
bh-filter-failures data_test_results.csv

# 2. View the failure summary output
# Failures written to: data_test_results_failures.csv

# 3. Specify custom output file
bh-filter-failures prbs_test.csv --output my_failures.csv

# 4. Use custom status column if needed
bh-filter-failures test.csv --status-column custom_status
```

---

## Installation

The tool is included in the BH Galaxy Data Analysis Tool package. Follow the installation instructions in the main [README.md](../../README.md).

After installation, the `bh-filter-failures` command will be available in your PATH when the virtual environment is activated:

```bash
source .venv/bin/activate
bh-filter-failures --help
```

---

## Basic Concepts

### What is a Failure?

The tool identifies failures based on the `test_status` column in CSV files:

**Failures** are rows where `test_status` is NOT:
- `ETH_ACTIVE` (passing test, link is active)
- `ETH_UNCONNECTED` (expected condition, port not connected)

**Common failure types**:
- `TRAINING_FAIL` - Link training failed
- `BER_THRESHOLD_EXCEEDED` - Bit error rate too high
- `TIMEOUT` - Test timed out
- `ERROR` - General error condition

### CSV Structure

Expected CSV format:
- Must have a `test_status` column (or custom specified column)
- Can have any number of additional columns
- All columns are preserved in the output file

### Output Format

The tool creates a new CSV file containing:
- Only the failed test rows
- All original columns preserved
- Same column order as input
- Filename: `{original_name}_failures.csv` (or custom name)

---

## Command Reference

### Basic Usage

```bash
bh-filter-failures <input_csv> [OPTIONS]
```

### Arguments

**Required:**

- `input_csv` - Path to input CSV file containing test data

### Options

**Output Control:**

- `--output PATH` - Output CSV file path (default: `{input}_failures.csv`)

**Column Configuration:**

- `--status-column NAME` - Name of status column to check (default: `test_status`)

**Logging:**

- `--verbose, -v` - Enable verbose logging
- `--log-level LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**Help:**

- `--help` - Show help message and exit

---

## Examples

### Example 1: Basic Failure Filtering

Filter failures from a test data file:

```bash
bh-filter-failures data_test_results.csv
```

**Output:**
```
Processing: data_test_results.csv

Total rows read: 12,800
Failures found: 2,426
Failures written to: data_test_results_failures.csv

Failure breakdown by test_status:
  TRAINING_FAIL: 2,426
```

**What happened**:
- Read 12,800 test rows
- Found 2,426 failures
- Created `data_test_results_failures.csv` with only failures
- All 2,426 failures were `TRAINING_FAIL` type

### Example 2: Custom Output File

Specify a custom output filename:

```bash
bh-filter-failures prbs_test_results.csv --output critical_failures.csv
```

**Output:**
```
Processing: prbs_test_results.csv

Total rows read: 8,400
Failures found: 156
Failures written to: critical_failures.csv

Failure breakdown by test_status:
  BER_THRESHOLD_EXCEEDED: 134
  TRAINING_FAIL: 22
```

### Example 3: Multiple Failure Types

When CSV has various failure types:

```bash
bh-filter-failures system_test.csv
```

**Output:**
```
Processing: system_test.csv

Total rows read: 25,600
Failures found: 847
Failures written to: system_test_failures.csv

Failure breakdown by test_status:
  TRAINING_FAIL: 456
  BER_THRESHOLD_EXCEEDED: 312
  TIMEOUT: 56
  ERROR: 23
```

This shows the distribution of different failure modes.

### Example 4: Custom Status Column

If your CSV uses a different column name for status:

```bash
bh-filter-failures test_data.csv --status-column result_status
```

This tells the tool to check the `result_status` column instead of the default `test_status`.

### Example 5: Verbose Output

See detailed processing information:

```bash
bh-filter-failures data_test.csv --verbose
```

**Verbose output shows:**
```
INFO: Reading CSV file: data_test.csv
INFO: Found status column: test_status
INFO: Processing rows...
INFO: Total rows: 12,800
INFO: Passing tests (ETH_ACTIVE): 10,234
INFO: Unconnected ports (ETH_UNCONNECTED): 140
INFO: Failures found: 2,426
INFO: Writing failures to: data_test_failures.csv
INFO: Complete!

Total rows read: 12,800
Failures found: 2,426
Failures written to: data_test_failures.csv

Failure breakdown by test_status:
  TRAINING_FAIL: 2,426
```

### Example 6: Processing Multiple Files

Filter failures from multiple test files:

```bash
# Process each file
bh-filter-failures data/prbs_test_system1.csv
bh-filter-failures data/prbs_test_system2.csv
bh-filter-failures data/data_test_system1.csv

# Or use a loop
for file in data/*.csv; do
    bh-filter-failures "$file"
done
```

---

## Common Workflows

### Workflow 1: Quick Failure Analysis

Identify and examine failures from a test run:

```bash
# 1. Filter failures
bh-filter-failures data_test_results.csv

# 2. Open failures file in spreadsheet or text editor
# Review: data_test_results_failures.csv

# 3. Look at failure distribution in summary output
# Common patterns suggest systematic issues
```

### Workflow 2: Compare Test Runs

Compare failures across different test runs:

```bash
# Filter failures from each run
bh-filter-failures test_run_1.csv --output failures_run1.csv
bh-filter-failures test_run_2.csv --output failures_run2.csv
bh-filter-failures test_run_3.csv --output failures_run3.csv

# Compare failure counts and types
# Look for consistent vs. intermittent failures
```

### Workflow 3: Integration with Jira Download

Complete pipeline from Jira to failure analysis:

```bash
# 1. Download test data from Jira
bh-jira-retrieve --tickets SYS-123

# 2. Filter failures
bh-filter-failures data/SYS-123_data_test_results.csv
bh-filter-failures data/SYS-123_prbs_test_results.csv

# 3. Review failure files
ls data/*_failures.csv
```

### Workflow 4: Prepare for Excel Reporting

Filter failures before generating Excel summaries:

```bash
# 1. Filter failures from all test files
for file in data/*.csv; do
    bh-filter-failures "$file"
done

# 2. Move failure files to separate directory
mkdir -p failures/
mv data/*_failures.csv failures/

# 3. Generate Excel reports from failures
bh-generate-excel --data-dir failures/ --output-dir failure_reports/
```

### Workflow 5: Database Ingestion Preparation

Prepare failure data for database analysis:

```bash
# 1. Download latest test data
bh-jira-retrieve --tickets SYS-200 SYS-201

# 2. Filter failures
bh-filter-failures data/SYS-200_prbs_test_results.csv
bh-filter-failures data/SYS-201_prbs_test_results.csv

# 3. Ingest failures into analysis database
bh-analyze-systems ingest data/ --status-filter TRAINING_FAIL BER_THRESHOLD_EXCEEDED

# 4. Query failure patterns
bh-analyze-systems training all --format heatmap
```

### Workflow 6: Batch Processing with Organization

Organize failures by test type:

```bash
# Create organized directory structure
mkdir -p failures/prbs
mkdir -p failures/data

# Filter and organize PRBS failures
for file in data/prbs_test*.csv; do
    bh-filter-failures "$file" --output "failures/prbs/$(basename "$file" .csv)_failures.csv"
done

# Filter and organize Data test failures
for file in data/data_test*.csv; do
    bh-filter-failures "$file" --output "failures/data/$(basename "$file" .csv)_failures.csv"
done

# Summary of failures
echo "PRBS failures:"
wc -l failures/prbs/*.csv

echo "Data test failures:"
wc -l failures/data/*.csv
```

---

## Troubleshooting

### File Not Found

**Problem:**
```
ERROR: File not found: data_test_results.csv
```

**Solution:**

1. Check file path is correct
2. Use absolute path if in different directory:
   ```bash
   bh-filter-failures /full/path/to/data_test_results.csv
   ```
3. List files to verify name:
   ```bash
   ls data/*.csv
   ```

### Missing Status Column

**Problem:**
```
ERROR: Status column 'test_status' not found in CSV
```

**Solution:**

1. Check what columns exist:
   ```bash
   head -1 data_test_results.csv
   ```

2. If status column has different name, specify it:
   ```bash
   bh-filter-failures test.csv --status-column result
   ```

3. Verify CSV is properly formatted (has headers)

### No Failures Found

**Problem:**
```
Total rows read: 12,800
Failures found: 0
Failures written to: data_test_results_failures.csv
```

**Solution:**

This is normal if all tests passed. Verify:

1. Check if this is expected (all tests passed)
2. Review test_status values in original file
3. Ensure status column is correct:
   ```bash
   cut -d',' -f<status_column_number> data_test_results.csv | sort | uniq -c
   ```

### Permission Denied on Output

**Problem:**
```
ERROR: Permission denied: data_test_results_failures.csv
```

**Solution:**

1. Check write permissions in directory:
   ```bash
   ls -ld data/
   ```

2. Remove existing read-only file:
   ```bash
   rm data_test_results_failures.csv
   ```

3. Write to different location:
   ```bash
   bh-filter-failures data_test.csv --output ~/failures.csv
   ```

### CSV Parsing Error

**Problem:**
```
ERROR: CSV parsing error at line 145
```

**Solution:**

1. Check for malformed CSV:
   - Unmatched quotes
   - Inconsistent column counts
   - Special characters

2. View problematic line:
   ```bash
   sed -n '145p' data_test_results.csv
   ```

3. Fix CSV formatting or use CSV repair tool

4. Skip problematic file and report to data source

### Empty Output File

**Problem:**

Output file is created but empty (0 failures found).

**Solution:**

This means all tests passed or were unconnected. Verify:

```bash
# Check test_status distribution
cut -d',' -f<column_num> test.csv | sort | uniq -c

# Common statuses:
# ETH_ACTIVE = passing
# ETH_UNCONNECTED = not tested (expected)
# Other values = failures
```

### Large File Processing Slow

**Problem:**

Processing very large CSV files is slow.

**Solution:**

1. Be patient - tool processes entire file
2. Use verbose mode to see progress:
   ```bash
   bh-filter-failures large_file.csv --verbose
   ```
3. For extremely large files, consider splitting first:
   ```bash
   split -l 10000 large_file.csv chunk_
   ```

---

## Tips and Best Practices

### File Organization

- **Keep originals** - Don't overwrite source CSV files
- **Use descriptive names** for custom output files
- **Organize by test type** (PRBS vs. Data tests)
- **Create dated directories** for different test runs
- **Separate failures** from passing tests for easier analysis

### Failure Analysis

- **Review breakdown** - Different failure types indicate different issues
- **Compare across systems** - Consistent failures suggest systematic problems
- **Track over time** - Increasing failures may indicate degradation
- **Cross-reference** - Match failures to hardware topology
- **Document patterns** - Note common failure signatures

### Integration

- **Pipeline position** - Run after download, before reporting
- **Batch processing** - Use loops for multiple files
- **Automate** - Include in test data processing scripts
- **Chain tools** - Feed failures to other analysis tools
- **Preserve provenance** - Keep mapping of failures to original files

### Performance

- **Fast processing** - Tool is efficient even for large files
- **Memory efficient** - Uses pandas streaming for large files
- **Parallel processing** - Run multiple instances for different files
- **SSD recommended** - I/O is the bottleneck for large files

### Output Usage

- **Excel analysis** - Open failure CSV in Excel/LibreOffice
- **Further filtering** - Use grep/awk for additional filtering
- **Database import** - Load failures into SQLite/PostgreSQL
- **Reporting tools** - Feed to `bh-generate-excel` or `bh-analyze-systems`
- **Manual review** - Review in text editor for detailed analysis

### Quality Checks

- **Verify counts** - Failure count should match summary
- **Spot check** - Manually verify a few rows in output
- **Compare totals** - Original rows = passing + unconnected + failures
- **Check status values** - Ensure only failures in output
- **Validate CSV** - Ensure output CSV is well-formed

---

## Understanding Failure Types

### Common Test Status Values

**Passing Conditions** (not included in failure output):
- `ETH_ACTIVE` - Test passed, Ethernet link is active
- `ETH_UNCONNECTED` - Port not connected (expected condition)

**Failure Conditions** (included in failure output):
- `TRAINING_FAIL` - Link training failed to establish
- `BER_THRESHOLD_EXCEEDED` - Bit error rate above threshold
- `TIMEOUT` - Test exceeded time limit
- `ERROR` - General error condition
- `INVALID_CONFIG` - Configuration error
- `HARDWARE_ERROR` - Hardware fault detected

### Interpreting Failure Breakdown

When you see the failure breakdown:

```
Failure breakdown by test_status:
  TRAINING_FAIL: 2,426
  BER_THRESHOLD_EXCEEDED: 134
```

**What this means**:
- Most failures (2,426) are training failures
- Smaller number (134) are BER threshold exceeded
- Training failures prevent link establishment
- BER failures indicate quality issues on established links

**Action items**:
- Training failures → Check physical connections, cable quality
- BER threshold exceeded → Check signal integrity, marginal lanes
- Mix of failures → Multiple issues, prioritize by count

---

## Getting Help

### Command Help

```bash
# Show help message
bh-filter-failures --help
```

### Verbose Logging

Enable detailed logging for troubleshooting:

```bash
bh-filter-failures test.csv --verbose

# Or set specific log level
bh-filter-failures test.csv --log-level DEBUG
```

### Common Questions

**Q: Can I filter passing tests instead of failures?**
A: No, this tool specifically filters failures. Use grep or pandas for other filtering:
```bash
grep "ETH_ACTIVE" test.csv > passing_tests.csv
```

**Q: Can I filter by multiple columns?**
A: No, tool filters by single status column. Use additional tools for complex filtering.

**Q: Does it work with Excel files?**
A: No, only CSV format. Convert Excel to CSV first:
```bash
# In Excel: Save As → CSV
# Or use: libreoffice --convert-to csv file.xlsx
```

**Q: Can it filter by failure count threshold?**
A: No, it extracts all failures. Use additional filtering after:
```bash
# Example: Find lanes with 10+ failures
cut -d',' -f<lane_column> failures.csv | sort | uniq -c | awk '$1 >= 10'
```

### Additional Resources

- Main README: [README.md](../../README.md)
- Project overview: [CLAUDE.md](../../CLAUDE.md)
- System analysis: [bh-analyze-systems.md](bh-analyze-systems.md)
- Excel reporting: [bh-generate-excel.md](bh-generate-excel.md)

---

**Last Updated:** 2026-03-12
**Tool Version:** 0.3.0
