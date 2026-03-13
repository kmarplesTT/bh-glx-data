# bh-extract-quanta User Guide

A command-line tool for extracting test data from Quanta QC3 test packages. This tool navigates complex nested archive structures to extract PRBS and Data test CSV files, and can analyze Excel test reports for failure identification.

**Version:** 0.3.0
**Purpose:** Automated extraction of test data from Quanta QC3 packages with failure analysis capability

---

## Quick Start

Get started in 5 minutes:

```bash
# 1. Extract test data from a Quanta package
bh-extract-quanta QC3_UBB_20260128.tar.gz

# 2. View extracted files
ls quanta/

# 3. Analyze Excel file for failures
bh-extract-quanta --analyze QC3_S7TK_0128_build_test.xlsx

# 4. Extract to custom directory
bh-extract-quanta QC3_UBB_20260128.tar.gz --output-dir test_data/
```

---

## Installation

The tool is included in the BH Galaxy Data Analysis Tool package. Follow the installation instructions in the main [README.md](../../README.md).

After installation, the `bh-extract-quanta` command will be available in your PATH when the virtual environment is activated:

```bash
source .venv/bin/activate
bh-extract-quanta --help
```

---

## Basic Concepts

### Quanta QC3 Package Structure

Quanta QC3 test packages have a deeply nested structure:

```
QC3_UBB_20260128.tar.gz
└── QC3_*.zip
    └── 0130/
        └── {Serial_Numbers}/
            └── QC3_UBB_*.tar.gz
                └── tt_funtest_ubb_*/
                    └── ft_eth_stress_*.tar.gz
                        ├── data_test_*.csv  ← Target files
                        └── prbs_test_*.csv  ← Target files
```

**Challenge**: Manually navigating this structure is tedious and error-prone.

**Solution**: This tool automatically:
- Opens the outer tar.gz archive
- Finds nested zip files
- Navigates to serial number directories
- Extracts inner tar.gz archives
- Locates test CSV files
- Extracts and saves with descriptive names

### Extracted File Naming

CSV files are saved with serial number prefixes:

- Format: `{SN}_{original_filename}.csv`
- Example: `S7TK51203456_prbs_test_results.csv`

This makes it easy to identify which system each file came from.

### Excel Analysis Mode

The tool can also analyze Quanta Excel test reports:

- Reads `QC3_*_test.xlsx` files
- Identifies non-zero failure counts
- Extracts serial numbers of failed systems
- Provides failure summary

This helps quickly identify which systems failed testing.

---

## Command Reference

### Basic Usage

```bash
bh-extract-quanta <archive> [OPTIONS]
```

Or for Excel analysis:

```bash
bh-extract-quanta --analyze <excel_file>
```

### Extraction Mode

**Arguments:**

- `archive` - Path to Quanta QC3 tar.gz package file

**Options:**

- `--output-dir PATH` - Directory for extracted CSV files (default: `quanta/`)
- `--verbose, -v` - Enable verbose logging
- `--log-level LEVEL` - Set logging level
- `--help` - Show help message

### Analysis Mode

**Options:**

- `--analyze FILE` - Analyze Excel file for failures
- `--verbose, -v` - Enable verbose logging
- `--log-level LEVEL` - Set logging level
- `--help` - Show help message

---

## Examples

### Example 1: Basic Extraction

Extract test data from a Quanta package:

```bash
bh-extract-quanta QC3_UBB_20260128.tar.gz
```

**Output:**
```
Extracting test data from Quanta package...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 8/8 systems

Extraction complete:
  Systems processed: 8
  CSV files extracted: 16
    PRBS test files: 8
    Data test files: 8
  Output directory: quanta/

Extracted files:
  quanta/S7TK51203456_prbs_test_results.csv
  quanta/S7TK51203456_data_test_results.csv
  quanta/S7TK51203457_prbs_test_results.csv
  quanta/S7TK51203457_data_test_results.csv
  ...
```

### Example 2: Custom Output Directory

Extract to a specific directory:

```bash
bh-extract-quanta QC3_UBB_20260128.tar.gz --output-dir test_data/january/
```

Files will be saved to `test_data/january/` instead of the default `quanta/` directory.

### Example 3: Verbose Extraction

See detailed extraction process:

```bash
bh-extract-quanta QC3_UBB_20260128.tar.gz --verbose
```

**Verbose output shows:**
```
INFO: Opening archive: QC3_UBB_20260128.tar.gz
INFO: Found nested zip: QC3_S7TK_0128.zip
INFO: Navigating to 0130/ directory
INFO: Found serial number directory: S7TK51203456
INFO: Opening nested archive: QC3_UBB_S7TK51203456.tar.gz
INFO: Searching for test directory: tt_funtest_ubb_*
INFO: Found: tt_funtest_ubb_v2_1/
INFO: Opening stress test archive: ft_eth_stress_*.tar.gz
INFO: Found: ft_eth_stress_results.tar.gz
INFO: Extracting: prbs_test_results.csv
INFO: Saving as: quanta/S7TK51203456_prbs_test_results.csv
INFO: Extracting: data_test_results.csv
INFO: Saving as: quanta/S7TK51203456_data_test_results.csv
INFO: Processing next system...
...
```

### Example 4: Analyze Excel File

Analyze a Quanta Excel test report for failures:

```bash
bh-extract-quanta --analyze QC3_S7TK_0128_build_test.xlsx
```

**Output (all passing):**
```
Analyzing Excel file for failures...

Analysis complete:
  Total systems: 8
  Failed systems: 0
  Pass rate: 100%

All systems passed!
```

**Output (with failures):**
```
Analyzing Excel file for failures...

Analysis complete:
  Total systems: 8
  Failed systems: 2
  Pass rate: 75%

Failed system serial numbers:
  S7TK51203458
  S7TK51203461

Failure details:
  S7TK51203458:
    - PRBS test failures: 45
    - Data test failures: 12
  S7TK51203461:
    - PRBS test failures: 23
    - Training failures: 8
```

### Example 5: Multiple Packages

Extract from multiple Quanta packages:

```bash
# Extract each package
bh-extract-quanta QC3_UBB_20260128.tar.gz --output-dir quanta/jan_28/
bh-extract-quanta QC3_UBB_20260205.tar.gz --output-dir quanta/feb_05/
bh-extract-quanta QC3_UBB_20260212.tar.gz --output-dir quanta/feb_12/

# Or use a loop
for package in QC3_UBB_*.tar.gz; do
    date_str=$(echo "$package" | grep -o '[0-9]\{8\}')
    bh-extract-quanta "$package" --output-dir "quanta/${date_str}/"
done
```

---

## Common Workflows

### Workflow 1: Quick Data Extraction

Extract test data for analysis:

```bash
# 1. Extract from Quanta package
bh-extract-quanta QC3_UBB_20260128.tar.gz

# 2. Verify extraction
ls quanta/

# 3. Process extracted data
bh-filter-failures quanta/S7TK51203456_data_test_results.csv
bh-generate-excel --data-dir quanta/
```

### Workflow 2: Failure Investigation

Identify and analyze failed systems:

```bash
# 1. Analyze Excel report to identify failures
bh-extract-quanta --analyze QC3_S7TK_0128_build_test.xlsx

# Output shows failed SNs: S7TK51203458, S7TK51203461

# 2. Extract all data
bh-extract-quanta QC3_UBB_20260128.tar.gz

# 3. Focus on failed systems
bh-filter-failures quanta/S7TK51203458_prbs_test_results.csv
bh-filter-failures quanta/S7TK51203461_prbs_test_results.csv

# 4. Review failure details
# Open failure CSV files for analysis
```

### Workflow 3: Batch Processing

Process multiple Quanta packages:

```bash
# 1. Create organized directory structure
mkdir -p quanta_data/{jan,feb,mar}

# 2. Extract packages by month
bh-extract-quanta QC3_UBB_20260128.tar.gz --output-dir quanta_data/jan/
bh-extract-quanta QC3_UBB_20260205.tar.gz --output-dir quanta_data/feb/
bh-extract-quanta QC3_UBB_20260312.tar.gz --output-dir quanta_data/mar/

# 3. Generate Excel reports for each month
bh-generate-excel --data-dir quanta_data/jan/ --output-dir reports/jan/
bh-generate-excel --data-dir quanta_data/feb/ --output-dir reports/feb/
bh-generate-excel --data-dir quanta_data/mar/ --output-dir reports/mar/

# 4. Compare across months
# Review Excel reports to track quality trends
```

### Workflow 4: Integration with System Analysis

Feed Quanta data into system analysis database:

```bash
# 1. Extract from multiple packages
bh-extract-quanta QC3_UBB_20260128.tar.gz --output-dir quanta/batch1/
bh-extract-quanta QC3_UBB_20260205.tar.gz --output-dir quanta/batch2/

# 2. Ingest into analysis database
bh-analyze-systems ingest quanta/batch1/
bh-analyze-systems ingest quanta/batch2/

# 3. Query across all Quanta systems
bh-analyze-systems stats all --speed 200 --format heatmap
bh-analyze-systems training all --format heatmap

# 4. Export comprehensive analysis
bh-analyze-systems export-excel --output quanta_analysis.xlsx
```

### Workflow 5: Quality Tracking

Track quality metrics over time:

```bash
#!/bin/bash
# quality_tracking.sh

# Configuration
ARCHIVE_DIR="/path/to/quanta/packages"
OUTPUT_BASE="quanta_analysis"
DATE=$(date +%Y%m%d)

# Process latest package
latest_package=$(ls -t ${ARCHIVE_DIR}/QC3_UBB_*.tar.gz | head -1)

# Analyze for failures
echo "Analyzing: ${latest_package}"
bh-extract-quanta --analyze "${latest_package%.tar.gz}_test.xlsx" > \
    "${OUTPUT_BASE}/analysis_${DATE}.txt"

# Extract data
bh-extract-quanta "$latest_package" --output-dir "${OUTPUT_BASE}/${DATE}/"

# Generate failure summary
for csv in "${OUTPUT_BASE}/${DATE}"/*.csv; do
    bh-filter-failures "$csv"
done

# Count failures
failure_count=$(wc -l "${OUTPUT_BASE}/${DATE}"/*_failures.csv | tail -1 | awk '{print $1}')

echo "Date: ${DATE}" >> "${OUTPUT_BASE}/failure_log.txt"
echo "Failures: ${failure_count}" >> "${OUTPUT_BASE}/failure_log.txt"
echo "---" >> "${OUTPUT_BASE}/failure_log.txt"
```

### Workflow 6: Selective Extraction

Extract data for specific systems only:

```bash
# 1. Analyze Excel to identify systems of interest
bh-extract-quanta --analyze QC3_S7TK_0128_build_test.xlsx

# Output shows failed systems: S7TK51203458, S7TK51203461

# 2. Extract all data
bh-extract-quanta QC3_UBB_20260128.tar.gz

# 3. Move only relevant files
mkdir -p focused_analysis/
mv quanta/S7TK51203458_*.csv focused_analysis/
mv quanta/S7TK51203461_*.csv focused_analysis/

# 4. Analyze focused dataset
bh-generate-excel --data-dir focused_analysis/ --output-dir focused_reports/
```

---

## Troubleshooting

### Archive Not Found

**Problem:**
```
ERROR: Archive not found: QC3_UBB_20260128.tar.gz
```

**Solution:**

1. Verify file path:
   ```bash
   ls QC3_UBB_*.tar.gz
   ```

2. Use absolute path:
   ```bash
   bh-extract-quanta /full/path/to/QC3_UBB_20260128.tar.gz
   ```

3. Check filename spelling

### Invalid Archive Format

**Problem:**
```
ERROR: Invalid archive format or corrupted file
```

**Solution:**

1. Verify file is not corrupted:
   ```bash
   tar -tzf QC3_UBB_20260128.tar.gz > /dev/null
   ```

2. Re-download package if corrupted

3. Ensure file is complete (check file size)

4. Try extracting manually to verify structure

### No CSV Files Found

**Problem:**
```
WARNING: No CSV files found in archive
```

**Solution:**

Possible reasons:
1. **Wrong archive type** - Ensure it's a QC3 test package
2. **Different structure** - Package structure may have changed
3. **Empty package** - No test data in package

Verify package contents:
```bash
tar -tzf QC3_UBB_20260128.tar.gz | head -20
```

Check for expected structure (0130/, serial numbers, etc.)

### Excel File Not Found (Analysis Mode)

**Problem:**
```
ERROR: Excel file not found: QC3_S7TK_0128_build_test.xlsx
```

**Solution:**

1. Verify file path:
   ```bash
   ls QC3_*_test.xlsx
   ```

2. Ensure file is Excel format (.xlsx, not .xls)

3. Check filename matches Quanta naming convention

### Permission Denied on Output

**Problem:**
```
ERROR: Permission denied: quanta/
```

**Solution:**

1. Create output directory:
   ```bash
   mkdir -p quanta/
   ```

2. Check permissions:
   ```bash
   ls -ld quanta/
   chmod u+w quanta/
   ```

3. Use different output directory:
   ```bash
   bh-extract-quanta package.tar.gz --output-dir ~/quanta_data/
   ```

### Extraction Incomplete

**Problem:**

Some systems extracted but not all.

**Solution:**

1. Run with verbose mode to see where it stopped:
   ```bash
   bh-extract-quanta package.tar.gz --verbose
   ```

2. Check for disk space:
   ```bash
   df -h
   ```

3. Re-run extraction (tool should skip existing files)

4. If specific system fails, package may have inconsistent structure for that system

### Excel Analysis Fails

**Problem:**
```
ERROR: Cannot read Excel file or unexpected format
```

**Solution:**

1. Verify Excel file opens in Excel/LibreOffice

2. Check file has expected sheets and columns

3. Ensure openpyxl is installed:
   ```bash
   pip install openpyxl
   ```

4. Try opening file manually to verify format

### Large Archive Processing Slow

**Problem:**

Extraction is taking a very long time.

**Solution:**

This is normal for large Quanta packages. The tool is:
- Opening multiple nested archives
- Searching through directory trees
- Extracting and saving multiple CSV files

**Expected times:**
- Small packages (1-5 systems): 30-60 seconds
- Medium packages (5-10 systems): 1-3 minutes
- Large packages (10+ systems): 3-10 minutes

Use `--verbose` to see progress.

---

## Tips and Best Practices

### File Organization

- **Organize by date** - Create subdirectories by package date
- **Preserve originals** - Keep original tar.gz packages
- **Consistent naming** - Use consistent directory names for different batches
- **Archive old data** - Move processed packages to archive directory

### Extraction

- **Verify first** - Analyze Excel file before extracting to know what to expect
- **Check structure** - Use verbose mode first time to understand package structure
- **Batch process** - Extract multiple packages in sequence
- **Monitor space** - Ensure sufficient disk space for extraction
- **Keep extracted files** - Don't delete CSV files until after analysis

### Analysis

- **Excel first** - Analyze Excel report to identify failures before extracting
- **Focus on failures** - Extract and focus on failed systems
- **Compare batches** - Track failure rates across multiple packages
- **Document SNs** - Keep list of failed serial numbers for tracking
- **Trend analysis** - Compare failure rates over time

### Integration

- **Part of pipeline** - Use as first step in Quanta data analysis pipeline
- **Combine tools** - Follow with filter-failures and generate-excel
- **Database ingestion** - Feed to bh-analyze-systems for comprehensive analysis
- **Automate** - Script extraction for regular processing
- **Quality gates** - Use analysis mode for pass/fail decisions

### Performance

- **SSD recommended** - Many file operations, benefits from fast I/O
- **Parallel processing** - Extract multiple packages in parallel (different directories)
- **Network shares** - Avoid extracting directly to network shares (slow)
- **Local first** - Extract locally, then move to shared storage

### Quality Checks

- **Verify counts** - Check number of extracted files matches expected
- **Spot check** - Open a few CSV files to verify contents
- **Compare to Excel** - Cross-reference with Excel analysis
- **Check naming** - Ensure serial numbers are correct in filenames
- **Validate data** - Verify CSV structure is compatible with other tools

---

## Understanding Quanta Package Structure

### Typical Package Hierarchy

```
QC3_UBB_20260128.tar.gz                    [Outer archive]
│
└── QC3_S7TK_0128.zip                      [Nested zip]
    │
    └── 0130/                              [Date directory]
        │
        ├── S7TK51203456/                  [Serial number 1]
        │   └── QC3_UBB_S7TK51203456.tar.gz [System package]
        │       └── tt_funtest_ubb_v2_1/   [Test directory]
        │           └── ft_eth_stress_results.tar.gz [Test results]
        │               ├── prbs_test_results.csv  ← Extract this
        │               └── data_test_results.csv  ← Extract this
        │
        ├── S7TK51203457/                  [Serial number 2]
        │   └── QC3_UBB_S7TK51203457.tar.gz
        │       └── ...
        │
        └── ...                            [More serial numbers]
```

### Excel File Structure

Quanta Excel test reports typically contain:

**Sheets:**
- Summary sheet with pass/fail counts
- System-by-system results
- Failure breakdowns by test type

**Key columns:**
- Serial Number
- Test Type
- Pass Count
- Fail Count
- Status

The analysis mode reads these sheets to identify failures.

---

## Getting Help

### Command Help

```bash
# Show help message
bh-extract-quanta --help

# Extraction mode help
bh-extract-quanta --help

# Analysis mode help
bh-extract-quanta --analyze --help
```

### Verbose Logging

Enable detailed logging for troubleshooting:

```bash
# Extraction with verbose output
bh-extract-quanta package.tar.gz --verbose

# Analysis with verbose output
bh-extract-quanta --analyze test.xlsx --verbose

# Debug level logging
bh-extract-quanta package.tar.gz --log-level DEBUG
```

### Common Questions

**Q: Can it extract from zip files instead of tar.gz?**
A: The tool expects tar.gz format. Extract zip manually first if needed.

**Q: What if package structure is different?**
A: Tool may fail. Use verbose mode to see where it stops, and report the issue.

**Q: Can I extract only PRBS or only Data tests?**
A: Not directly. Extract both, then use other tools to filter.

**Q: Does it modify the original package?**
A: No, packages are opened read-only and never modified.

**Q: Can it handle password-protected archives?**
A: No, archives must be unencrypted.

### Additional Resources

- Main README: [README.md](../../README.md)
- Project overview: [CLAUDE.md](../../CLAUDE.md)
- Failure filtering: [bh-filter-failures.md](bh-filter-failures.md)
- Excel generation: [bh-generate-excel.md](bh-generate-excel.md)
- System analysis: [bh-analyze-systems.md](bh-analyze-systems.md)

---

**Last Updated:** 2026-03-12
**Tool Version:** 0.3.0
