# Excel Export Feature Implementation Plan

## Overview

This plan describes the implementation of enhanced Excel export capabilities for the `bh-analyze-systems` tool. Instead of exporting the raw database, the tool will export formatted query results (tables and heatmaps) from various commands directly into Excel workbooks.

## Executive Summary

### Current State
- Single `export-excel` command that dumps the entire database into Excel
- Not useful for analyzing specific query results
- No visual formatting applied to Excel output

### Target State
- Remove the current `export-excel` command entirely
- Add `--excel-output` option to all analysis commands (stats, threshold, training, custom, histogram, advanced-stats, info)
- Support both table and heatmap formats in Excel
- Apply color schemes using cell background colors (not font colors)
- If Excel file exists, append a new worksheet; otherwise create new file
- **Include summary/metadata sections** in Excel exports matching terminal output (total samples, systems, speeds, etc.)
- **Use descriptive worksheet names** that include lane_spec (e.g., "Stats - all", "Stats - 01:00.0/ETH07", "Histogram - 01:00.0/*")

### Commands to Update
1. `stats` - Table and heatmap with color schemes
2. `threshold` - Table and heatmap with color schemes
3. `training` - Table and heatmap with color schemes
4. `custom` - Table and heatmap with color schemes
5. `histogram` - Excel chart with bin legend
6. `advanced-stats` - Two tables (per-host stats + aggregated stats)
7. `info` - Single formatted table with database metadata

---

## Architecture Overview

### Design Principles

1. **Unified Interface**: All commands use `--excel-output <path>` option
2. **Separation of Concerns**:
   - CLI layer: Argument parsing and command routing
   - Export layer: Excel file management and formatting
   - Visualization layer: Data formatting and structure
3. **Reusability**: Share code between terminal rendering and Excel export
4. **Incremental Updates**: Append worksheets to existing files without overwriting

### Module Structure

```
system_analysis/
├── cli.py                    # CLI argument parsing (MODIFY)
├── export.py                 # Excel export functionality (MAJOR REFACTOR)
├── visualization.py          # Terminal rendering (MINOR UPDATES)
├── excel_formatters.py       # NEW: Excel-specific formatting
└── query_engine.py           # No changes needed
```

---

## Detailed Implementation Plan

### Phase 1: Remove Current Export Command

#### Files to Modify
1. **`src/bh_glx_data/system_analysis/cli.py`**
   - Remove `export-excel` subcommand parser (lines 248-275)
   - Remove `handle_export_excel()` function (lines 604-654)
   - Remove `export-excel` from command routing in `main()` (lines 753-754)
   - Remove `ExcelExporter` and `ExportFilters` imports from `export` module (line 21)
   - Update epilog examples to remove `export-excel` reference (line 63)
   - Update `initialize_schema()` check to remove `export-excel` from command list (line 722)

2. **`src/bh_glx_data/system_analysis/export.py`**
   - Remove `export_full_database()` method (lines 84-185)
   - Remove `ExportFilters` dataclass (lines 32-45)
   - Remove `ExportResult` dataclass (lines 48-62)
   - Remove `_build_filter_clause()` method (lines 272-312)
   - Remove `_create_summary_sheet()` method (lines 314-383)
   - Remove `_write_dataframe_to_sheet()` method (lines 385-405)
   - Keep class structure and imports for refactoring in Phase 2

3. **`docs/user_guides/bh-analyze-systems.md`**
   - Remove `export-excel` command from Quick Start (line 55-56)
   - Remove `export-excel` command documentation section
   - Add new "Excel Export" section explaining `--excel-output` option

4. **`README.md`**
   - Remove `export-excel` example from System Analysis section
   - Update examples to show new `--excel-output` usage

5. **`CLAUDE.md`**
   - Update System Analysis Module documentation
   - Remove references to `export-excel` command
   - Add documentation for `--excel-output` option

6. **`tests/integration/system_analysis/test_end_to_end.py`**
   - Remove any tests for `export-excel` command if they exist

---

### Phase 2: Create Excel Formatting Infrastructure

#### New File: `src/bh_glx_data/system_analysis/excel_formatters.py`

This new module will handle all Excel-specific formatting logic.

**Key Classes and Functions:**

```python
# Dataclasses for export configuration
@dataclass
class ExcelExportConfig:
    """Configuration for Excel export operations."""
    output_path: Path
    worksheet_name: str
    format_type: str  # "table", "heatmap", "chart"
    color_scheme: Optional[ColorScheme] = None

@dataclass
class ExcelExportResult:
    """Result of an Excel export operation."""
    output_path: Path
    worksheet_name: str
    rows_written: int
    file_existed: bool

# Core formatting functions
def create_or_open_workbook(path: Path) -> tuple[Workbook, bool]:
    """Create new or open existing Excel workbook.
    Returns: (workbook, file_existed)
    """

def generate_unique_worksheet_name(wb: Workbook, base_name: str) -> str:
    """Generate unique worksheet name avoiding collisions.

    Base name should include lane_spec for descriptive names:
    - "Stats - all"
    - "Stats - 01:00.0/ETH07"
    - "Histogram - 01:00.0/*"

    If collision: "Stats - all", "Stats - all (2)", "Stats - all (3)"
    """

def apply_cell_background_color(cell, color: str) -> None:
    """Apply background color to cell (not font color).
    Maps terminal color codes to Excel PatternFill.
    """

def write_table_to_worksheet(
    ws: Worksheet,
    data: Dict[str, List],
    headers: List[str],
    title: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Write tabular data to worksheet with headers.

    Args:
        metadata: Optional summary data to append at bottom (e.g., total samples, systems)
    """

def write_heatmap_to_worksheet(
    ws: Worksheet,
    lane_data: Dict[str, Union[float, int]],
    color_scheme: ColorScheme,
    is_ber_metric: bool,
    title: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Write heatmap data with cell background colors.

    Args:
        metadata: Optional summary data to append at bottom (e.g., total samples, systems)
    """

def write_histogram_to_worksheet(
    ws: Worksheet,
    histogram: BERHistogram,
    title: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Write histogram as Excel column chart with bin legend.

    Args:
        metadata: Optional summary data to append at bottom (e.g., total samples, systems, speeds)
    """

# Color mapping utilities
def map_terminal_color_to_excel(terminal_color: str) -> str:
    """Map Rich terminal color codes to Excel hex colors."""

def get_excel_color_for_value(
    value: Union[float, int],
    color_scheme: ColorScheme,
    is_ber_metric: bool,
) -> str:
    """Get Excel hex color for value based on color scheme."""
```

**Color Mapping:**
```python
TERMINAL_TO_EXCEL_COLOR_MAP = {
    "color(28)": "006400",    # GREEN -> dark green
    "color(106)": "9ACD32",   # YELLOW_GREEN -> yellow-green
    "color(184)": "FFD700",   # YELLOW -> gold
    "color(172)": "FF8C00",   # ORANGE -> dark orange
    "color(124)": "8B0000",   # RED -> dark red
}
```

---

### Phase 3: Refactor Export Module

#### Modified File: `src/bh_glx_data/system_analysis/export.py`

**Remove:**
- All database export functionality (Phase 1)
- Old helper methods

**Keep:**
- `ExcelExporter` class structure
- Database manager reference

**Add/Refactor:**

```python
class ExcelExporter:
    """Export query results to Excel files with formatting."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize exporter with database manager."""
        self.db = db_manager

    def export_ber_statistics(
        self,
        stats: BERStatistics,
        output_path: Path,
        lane_spec: str,
        format: str = "table",
        color_scheme: Optional[ColorScheme] = None,
    ) -> ExcelExportResult:
        """Export BER statistics to Excel (table or heatmap format).

        Args:
            stats: BER statistics result from query
            output_path: Path to Excel file
            lane_spec: Lane specification string for worksheet name (e.g., "all", "01:00.0/ETH07")
            format: "table" or "heatmap"
            color_scheme: Optional color scheme for heatmap

        Returns:
            ExcelExportResult with export details

        Note:
            Includes metadata summary (total samples, systems, speeds) at bottom of worksheet
        """

    def export_count_data(
        self,
        counts: Union[ThresholdExceededCounts, CustomThresholdCounts, TrainingFailureCounts],
        output_path: Path,
        lane_spec: str,
        format: str = "table",
        color_scheme: Optional[ColorScheme] = None,
    ) -> ExcelExportResult:
        """Export count data to Excel (table or heatmap format).

        Note:
            Includes metadata summary (total samples, systems, speeds) at bottom of worksheet
        """

    def export_histogram(
        self,
        histogram: Union[BERHistogram, List[BERHistogram]],
        output_path: Path,
        lane_spec: str,
    ) -> ExcelExportResult:
        """Export histogram(s) to Excel with column chart.

        Note:
            Includes metadata summary (total samples, systems, speeds) at bottom of worksheet
        """

    def export_advanced_stats(
        self,
        stats: Union[AggregatedHostStats, List[AggregatedHostStats]],
        output_path: Path,
        lane_spec: str,
    ) -> ExcelExportResult:
        """Export advanced statistics (two tables per lane).

        Note:
            Includes metadata summary (total samples, systems, speeds) at bottom of worksheet
        """

    def export_database_info(
        self,
        info: DatabaseStats,
        output_path: Path,
    ) -> ExcelExportResult:
        """Export database info to Excel."""
```

**Key Implementation Details:**

1. **Workbook Management:**
   - Use `create_or_open_workbook()` from excel_formatters
   - Generate unique worksheet names to avoid collisions
   - Save and close workbook after writing

2. **Data Transformation:**
   - Convert query result dataclasses to Excel-friendly structures
   - Group lane data by bus_id/eth_id for heatmaps
   - Format BER values in scientific notation

3. **Format Selection:**
   - Table format: Write structured rows with headers
   - Heatmap format: Group by port, apply cell background colors
   - Apply color schemes using `get_excel_color_for_value()`

4. **Worksheet Naming:**
   - Include lane_spec in worksheet name for clarity
   - Examples: "Stats - all", "Histogram - 01:00.0/ETH07", "Training - 01:00.0/*"
   - Handle name collisions with incrementing numbers

5. **Metadata:**
   - Add summary section at bottom matching terminal output
   - Include: Total samples, unique systems, train speeds, date ranges
   - Add legends for color schemes
   - Add titles to worksheets

---

### Phase 4: Update CLI Commands

#### Modified File: `src/bh_glx_data/system_analysis/cli.py`

**For Each Command (stats, threshold, custom, training, histogram, advanced-stats, info):**

1. **Add `--excel-output` argument to parser:**

```python
stats_parser.add_argument(
    "--excel-output",
    type=Path,
    metavar="FILE",
    help="Export results to Excel file (creates new file or adds worksheet to existing)",
)
```

2. **Update handler functions to check for `--excel-output`:**

```python
def handle_stats(db: DatabaseManager, args: argparse.Namespace) -> int:
    """Handle stats command with optional Excel export."""
    try:
        selector = LaneSelector.from_spec(args.lane_spec)
        engine = QueryEngine(db)

        # Execute query
        result = engine.query_ber_statistics(
            selector,
            train_speeds=args.speeds,
        )

        # Terminal output (if no Excel export or if verbose)
        if not args.excel_output or args.verbose:
            if args.format == "table":
                renderer = TableRenderer()
                output = renderer.render_ber_statistics(result)
                print(output)
            else:  # heatmap
                color_scheme = _get_color_scheme(args.color_scheme, BER_COLOR_SCHEMES)
                renderer = HeatMapRenderer(ber_color_scheme=color_scheme)
                output = renderer.render_ber_heatmap(result, metric=args.statistic)
                print(output)

        # Excel export (if requested)
        if args.excel_output:
            exporter = ExcelExporter(db)
            color_scheme = _get_color_scheme(args.color_scheme, BER_COLOR_SCHEMES)
            export_result = exporter.export_ber_statistics(
                result,
                args.excel_output,
                lane_spec=args.lane_spec,  # Pass lane_spec for worksheet name
                format=args.format,
                color_scheme=color_scheme,
            )
            logger.info(f"\nExported to: {export_result.output_path}")
            logger.info(f"Worksheet: {export_result.worksheet_name}")
            logger.info(f"Rows written: {export_result.rows_written}")

        return 0

    except LaneSelectorError as e:
        logger.error(f"Invalid lane specification: {e}")
        return 1
    # ... error handling
```

**Handler Function Updates:**

| Command | Export Method | Format Options | Special Handling |
|---------|--------------|----------------|------------------|
| `handle_stats` | `export_ber_statistics()` | table, heatmap | Use `args.statistic` for metric selection |
| `handle_threshold` | `export_count_data()` | table, heatmap | Pass ThresholdExceededCounts |
| `handle_custom` | `export_count_data()` | table, heatmap | Pass CustomThresholdCounts with threshold value |
| `handle_training` | `export_count_data()` | table, heatmap | Pass TrainingFailureCounts |
| `handle_histogram` | `export_histogram()` | chart only | No format option, always chart |
| `handle_advanced_stats` | `export_advanced_stats()` | table only | No format option, always two tables |
| `handle_info` | `export_database_info()` | table only | No format option, database metadata |

---

### Phase 5: Update Visualization Module

#### Modified File: `src/bh_glx_data/system_analysis/visualization.py`

**Changes:**

1. **Extract data preparation logic into helper methods:**

```python
class TableRenderer:
    # ... existing methods ...

    def prepare_ber_statistics_data(self, stats: BERStatistics) -> Dict[str, List]:
        """Prepare BER statistics data structure for export.

        Returns:
            Dictionary with keys: 'lane_ids', 'min_ber', 'avg_ber', 'max_ber',
            'high_ber', 'samples'
        """

    def prepare_count_data(
        self,
        counts: Union[ThresholdExceededCounts, CustomThresholdCounts, TrainingFailureCounts]
    ) -> Dict[str, List]:
        """Prepare count data structure for export."""

class HeatMapRenderer:
    # ... existing methods ...

    def prepare_heatmap_data(
        self,
        lane_data: Dict[str, Union[float, int]],
    ) -> Dict[Tuple[str, str], Dict[int, Union[float, int]]]:
        """Group lane data by (bus_id, eth_id) for heatmap rendering.

        Returns:
            Nested dict: {(bus_id, eth_id): {lane_num: value}}
        """
```

2. **No changes to terminal rendering logic** - keep all existing functionality intact

3. **Purpose:** These helper methods will be used by both terminal renderers and Excel exporters to ensure consistent data formatting

---

### Phase 6: Implement Special Cases

#### 6.1 Histogram Export (Excel Charts)

**Approach:**
- Create column chart (bar chart) using `openpyxl.chart`
- X-axis: BER bin labels (e.g., "< 1e-12", "1e-12-11", etc.)
- Y-axis: Sample counts
- Apply colors to bars matching terminal color scheme
- Add legend table below chart

**Implementation in `excel_formatters.py`:**

```python
def write_histogram_to_worksheet(
    ws: Worksheet,
    histogram: Union[BERHistogram, List[BERHistogram]],
    title: Optional[str] = None,
) -> None:
    """Write histogram as Excel column chart.

    Creates:
    - Column chart with colored bars
    - Data table with bins and counts
    - Color legend matching terminal output
    """
    from openpyxl.chart import BarChart, Reference
    from openpyxl.chart.series import DataPoint

    # Handle single histogram or list
    histograms = [histogram] if isinstance(histogram, BERHistogram) else histogram

    # Write title
    row = 1
    if title:
        ws.cell(row, 1, title)
        ws.cell(row, 1).font = Font(bold=True, size=14)
        row += 2

    # For multiple histograms (all lanes), create separate charts
    for hist in histograms:
        # Write histogram data table
        ws.cell(row, 1, "BER Range")
        ws.cell(row, 2, "Count")
        row += 1

        start_row = row
        for bin_label, count in hist.bins:
            ws.cell(row, 1, bin_label)
            ws.cell(row, 2, count)
            row += 1

        # Create bar chart
        chart = BarChart()
        chart.type = "col"
        chart.title = f"BER Distribution - {hist.lane_id}"
        chart.x_axis.title = "BER Range"
        chart.y_axis.title = "Count"

        # Add data
        data = Reference(ws, min_col=2, min_row=start_row-1, max_row=row-1)
        cats = Reference(ws, min_col=1, min_row=start_row, max_row=row-1)
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(cats)

        # Apply colors to bars
        series = chart.series[0]
        for i, (bin_label, _) in enumerate(hist.bins):
            terminal_color = _get_histogram_bar_color(bin_label)
            excel_color = map_terminal_color_to_excel(terminal_color)
            point = DataPoint(idx=i)
            point.graphicalProperties.solidFill = excel_color
            series.dPt.append(point)

        # Add chart to worksheet
        ws.add_chart(chart, f"D{start_row}")

        row += 2  # Spacing between charts

    # Add legend at bottom
    row += 1
    ws.cell(row, 1, "Color Legend:")
    ws.cell(row, 1).font = Font(bold=True)
    # ... write color legend ...
```

#### 6.2 Advanced Stats Export (Two Tables)

**Approach:**
- Create two separate tables on the same worksheet
- First table: Per-host statistics (one row per system)
- Second table: Statistics of statistics (3 rows: MIN, AVG, MAX)
- Apply consistent formatting to both tables

**Implementation:**

```python
def export_advanced_stats(
    self,
    stats: Union[AggregatedHostStats, List[AggregatedHostStats]],
    output_path: Path,
) -> ExcelExportResult:
    """Export advanced statistics (two tables per lane).

    For single lane: One section with two tables
    For multiple lanes: Multiple sections, each with two tables
    """
    wb, file_existed = create_or_open_workbook(output_path)

    # Normalize to list
    stats_list = [stats] if isinstance(stats, AggregatedHostStats) else stats

    # Generate worksheet name with lane_spec
    base_name = f"Advanced Stats - {lane_spec}"
    ws_name = generate_unique_worksheet_name(wb, base_name)
    ws = wb.create_sheet(ws_name)

    row = 1
    rows_written = 0

    for agg_stats in stats_list:
        # Table 1: Per-Host Statistics
        ws.cell(row, 1, f"Per-Host Statistics - {agg_stats.lane_id}")
        ws.cell(row, 1).font = Font(bold=True, size=12)
        row += 1

        # Headers
        headers = ["Host", "Min BER", "Avg BER", "Max BER", "Samples"]
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row, col, header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
        row += 1

        # Data rows
        for host_stat in sorted(agg_stats.host_stats, key=lambda h: h.host):
            ws.cell(row, 1, host_stat.host)
            ws.cell(row, 2, f"{host_stat.min_ber:.2e}" if host_stat.min_ber else "-")
            ws.cell(row, 3, f"{host_stat.avg_ber:.2e}" if host_stat.avg_ber else "-")
            ws.cell(row, 4, f"{host_stat.max_ber:.2e}" if host_stat.max_ber else "-")
            ws.cell(row, 5, host_stat.sample_count)
            row += 1
            rows_written += 1

        row += 2  # Spacing

        # Table 2: Statistics of Host Statistics
        ws.cell(row, 1, "Statistics of Host Statistics")
        ws.cell(row, 1).font = Font(bold=True, size=12)
        row += 1

        # Headers
        headers = ["Metric", "Minimum", "Average", "Maximum"]
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row, col, header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
        row += 1

        # Data rows
        stats_data = [
            ("MIN", agg_stats.min_of_mins, agg_stats.avg_of_mins, agg_stats.max_of_mins),
            ("AVG", agg_stats.min_of_avgs, agg_stats.avg_of_avgs, agg_stats.max_of_avgs),
            ("MAX", agg_stats.min_of_maxs, agg_stats.avg_of_maxs, agg_stats.max_of_maxs),
        ]
        for metric, min_val, avg_val, max_val in stats_data:
            ws.cell(row, 1, metric)
            ws.cell(row, 2, f"{min_val:.2e}" if min_val else "-")
            ws.cell(row, 3, f"{avg_val:.2e}" if avg_val else "-")
            ws.cell(row, 4, f"{max_val:.2e}" if max_val else "-")
            row += 1
            rows_written += 1

        row += 3  # Spacing between lanes

    # Add metadata summary at bottom
    row += 2
    ws.cell(row, 1, "Summary")
    ws.cell(row, 1).font = Font(bold=True, size=12)
    row += 1

    # Extract metadata from stats
    total_samples = sum(hs.sample_count for s in stats_list for hs in s.host_stats)
    unique_systems = len(set(hs.host for s in stats_list for hs in s.host_stats))

    ws.cell(row, 1, "Total Samples:")
    ws.cell(row, 2, total_samples)
    row += 1
    ws.cell(row, 1, "Unique Systems:")
    ws.cell(row, 2, unique_systems)
    row += 1

    # Adjust column widths
    ws.column_dimensions["A"].width = 20
    for col in ["B", "C", "D"]:
        ws.column_dimensions[col].width = 15
    ws.column_dimensions["E"].width = 10

    # Save workbook
    wb.save(output_path)

    return ExcelExportResult(
        output_path=output_path,
        worksheet_name=ws_name,
        rows_written=rows_written,
        file_existed=file_existed,
    )
```

#### 6.3 Info Command Export

**Approach:**
- Single table with database metadata
- Format similar to terminal output but structured as table
- Include all information from `DatabaseStats` dataclass

**Structure:**
```
Database Information
--------------------
Database Path    | ~/.local/share/bh-glx-data/analysis.db
Total Tests      | 12,450
Unique Systems   | 8
Train Speeds     | 200, 400
Date Range       | 2026-01-15 to 2026-03-10

Status Breakdown
----------------
PASS                      | 10,024 (80.5%)
BER_THRESHOLD_EXCEEDED    | 1,826  (14.7%)
TRAINING_FAIL             | 600    (4.8%)

Ingestion History
-----------------
Total Ingestions | 5
```

---

### Phase 7: Testing Strategy

#### 7.1 Unit Tests

**New Test File: `tests/unit/system_analysis/test_excel_formatters.py`**

Tests for `excel_formatters.py`:
- `test_create_or_open_workbook_new_file()` - Creates new workbook
- `test_create_or_open_workbook_existing_file()` - Opens existing workbook
- `test_generate_unique_worksheet_name()` - Generates unique names
- `test_apply_cell_background_color()` - Applies correct background colors
- `test_map_terminal_color_to_excel()` - Maps all terminal colors correctly
- `test_get_excel_color_for_value_ber()` - BER color scheme mapping
- `test_get_excel_color_for_value_count()` - Count color scheme mapping
- `test_write_table_to_worksheet()` - Writes table correctly
- `test_write_heatmap_to_worksheet()` - Writes heatmap with colors
- `test_write_histogram_to_worksheet()` - Creates chart correctly

**Modified Test File: `tests/unit/system_analysis/test_export.py`** (if exists, otherwise create)

Tests for refactored `ExcelExporter`:
- `test_export_ber_statistics_table()` - Table format
- `test_export_ber_statistics_heatmap()` - Heatmap with colors
- `test_export_count_data_table()` - Count table format
- `test_export_count_data_heatmap()` - Count heatmap with colors
- `test_export_histogram()` - Histogram with chart
- `test_export_advanced_stats()` - Two tables
- `test_export_database_info()` - Info table
- `test_export_to_existing_file()` - Appends worksheet
- `test_export_worksheet_name_collision()` - Handles name conflicts

#### 7.2 Integration Tests

**Modified Test File: `tests/integration/system_analysis/test_end_to_end.py`**

Add Excel export tests:
- `test_stats_command_with_excel_export()` - Verify stats exports correctly
- `test_threshold_command_with_excel_export()` - Verify threshold exports
- `test_histogram_command_with_excel_export()` - Verify histogram chart
- `test_advanced_stats_command_with_excel_export()` - Verify two tables
- `test_multiple_exports_to_same_file()` - Verify worksheet appending
- `test_excel_export_with_color_schemes()` - Verify colors applied

**Modified Test File: `tests/integration/test_cli.py`**

Test CLI integration:
- Verify `--excel-output` argument accepted by all commands
- Verify error handling for invalid paths
- Verify success messages displayed

#### 7.3 Manual Testing

Create manual test plan document with:
1. Test each command with `--excel-output`
2. Verify Excel file structure and formatting
3. Verify color schemes match expectations
4. Verify charts render correctly
5. Verify worksheet names are unique
6. Test appending to existing files

---

### Phase 8: Documentation Updates

#### 8.1 User Guide

**File: `docs/user_guides/bh-analyze-systems.md`**

Add new section "Excel Export" after "Basic Concepts":

```markdown
## Excel Export

All analysis commands support exporting results directly to Excel with the `--excel-output` option. This creates formatted Excel worksheets with the same data and visualizations shown in the terminal.

### Usage

```bash
# Export stats as table
bh-analyze-systems stats all --speed 200 --excel-output analysis.xlsx

# Export threshold analysis as heatmap
bh-analyze-systems threshold all --speed 200 --format heatmap --excel-output analysis.xlsx

# Export histogram
bh-analyze-systems histogram 01:00.0/ETH07 --excel-output analysis.xlsx
```

### Behavior

- **New File**: If the Excel file doesn't exist, it will be created
- **Existing File**: If the Excel file exists, a new worksheet will be added
- **Worksheet Names**: Automatically generated to avoid collisions (e.g., "Stats", "Stats (2)", "Stats (3)")
- **Color Schemes**: Applied using cell background colors (not font colors)
- **Formatting**: Matches terminal output with Excel-appropriate formatting

### Supported Formats

| Command | Table | Heatmap | Chart | Notes |
|---------|-------|---------|-------|-------|
| `stats` | ✓ | ✓ | - | Use `--format` option |
| `threshold` | ✓ | ✓ | - | Use `--format` option |
| `custom` | ✓ | ✓ | - | Use `--format` option |
| `training` | ✓ | ✓ | - | Use `--format` option |
| `histogram` | - | - | ✓ | Always chart format |
| `advanced-stats` | ✓ | - | - | Two tables per lane |
| `info` | ✓ | - | - | Database metadata |
```

Update each command section to include `--excel-output` examples.

#### 8.2 README.md

**File: `README.md`**

Update System Analysis section:
- Remove `export-excel` command
- Add examples with `--excel-output`
- Update Quick Start section

#### 8.3 CLAUDE.md

**File: `CLAUDE.md`**

Update System Analysis Module section:
- Remove `export.py` old functionality
- Document new Excel export architecture
- Add examples of using `--excel-output`
- Document `excel_formatters.py` module

---

## Implementation Order

### Step-by-Step Execution

1. **Phase 1**: Remove current export command
   - Remove CLI command and handler
   - Remove old export methods
   - Update documentation (remove references)
   - Verify no breaking changes to other code
   - Run existing tests to ensure nothing broke

2. **Phase 2**: Create excel_formatters module
   - Implement all formatting functions
   - Create color mapping utilities
   - Write unit tests for formatters
   - Verify color mapping is correct

3. **Phase 3**: Refactor export.py
   - Implement new export methods
   - Use excel_formatters module
   - Handle workbook creation/opening
   - Write unit tests for export methods

4. **Phase 4**: Update CLI for one command (stats)
   - Add `--excel-output` argument
   - Update handler function
   - Test thoroughly with both formats
   - Once working, replicate pattern to other commands

5. **Phase 5**: Update remaining CLI commands
   - threshold, custom, training (similar to stats)
   - histogram (chart-specific)
   - advanced-stats (two-table format)
   - info (database metadata)

6. **Phase 6**: Update visualization.py
   - Add data preparation helper methods
   - Ensure no regression in terminal rendering

7. **Phase 7**: Comprehensive testing
   - Write all unit tests
   - Write integration tests
   - Manual testing with real data

8. **Phase 8**: Documentation
   - Update all documentation files
   - Add usage examples
   - Update CLAUDE.md with new patterns

---

## Shared Code and Reusability

### Reusable Components

1. **Color Scheme Mapping** (`excel_formatters.py`)
   - Used by all heatmap exports
   - Single source of truth for terminal → Excel color mapping

2. **Workbook Management** (`excel_formatters.py`)
   - `create_or_open_workbook()` - Used by all export methods
   - `generate_unique_worksheet_name()` - Used by all export methods

3. **Data Preparation** (`visualization.py`)
   - Extract from rendering logic
   - Shared between terminal and Excel rendering
   - Ensures consistency

4. **Export Pattern** (`cli.py`)
   - Consistent pattern across all handler functions
   - Check for `args.excel_output`
   - Call appropriate exporter method
   - Display success message

### Code Duplication to Avoid

- Don't duplicate color threshold logic (use ColorScheme dataclass)
- Don't duplicate lane grouping logic (extract to shared function)
- Don't duplicate BER formatting logic (create shared formatter)
- Don't duplicate worksheet creation boilerplate (use helper functions)

---

## Testing Requirements

### Test Coverage Goals

- **Unit Tests**: 90%+ coverage for new modules
  - `excel_formatters.py`: 100% coverage (all utility functions)
  - `export.py`: 90%+ coverage (all export methods)

- **Integration Tests**: Cover all commands
  - Each command with `--excel-output` option
  - Multiple exports to same file
  - Color scheme variations

### Test Data

- Use existing test fixtures from `tests/conftest.py`
- Create sample query results for each result type
- Create minimal Excel files for testing appending

### Assertions

For each test:
1. Verify Excel file created/updated
2. Verify worksheet exists with expected name
3. Verify data integrity (row count, values)
4. Verify formatting applied (colors, fonts, widths)
5. Verify charts created (for histogram)
6. Verify no data loss or corruption

---

## Risk Assessment and Mitigation

### Risks

1. **Breaking Changes**: Removing export-excel command could break user scripts
   - **Mitigation**: Clear communication in release notes, provide migration guide

2. **Excel Compatibility**: Different Excel versions may render differently
   - **Mitigation**: Test with Excel 2016, 2019, 2021, and Office 365

3. **Large Datasets**: Excel has row limits (1,048,576 rows)
   - **Mitigation**: Warn users if dataset exceeds limits, suggest filtering

4. **File Locking**: Excel files may be locked if open in Excel
   - **Mitigation**: Catch permission errors and provide clear error message

5. **Color Scheme Accuracy**: Terminal colors may not map perfectly to Excel
   - **Mitigation**: Manual testing and adjustment of color mapping

### Validation

- Compare Excel output to terminal output visually
- Verify color schemes match expectations
- Test with large datasets
- Test with multiple concurrent exports

---

## Success Criteria

### Definition of Done

1. ✅ Current `export-excel` command removed completely
2. ✅ All 7 commands support `--excel-output` option
3. ✅ Excel files created with correct formatting
4. ✅ Color schemes applied using cell background colors
5. ✅ Histogram creates Excel chart
6. ✅ Advanced stats creates two tables
7. ✅ Worksheet appending works correctly
8. ✅ All unit tests pass (90%+ coverage)
9. ✅ All integration tests pass
10. ✅ Documentation updated completely
11. ✅ Manual testing completed successfully

### User Acceptance Criteria

- Users can export any analysis command result to Excel
- Excel output is visually similar to terminal output
- Color coding is clear and intuitive
- Worksheets are well-formatted and professional
- Multiple exports to same file work seamlessly
- Error messages are clear and actionable

---

## Estimated Effort

| Phase | Estimated Time | Complexity |
|-------|---------------|------------|
| Phase 1: Remove old code | 2 hours | Low |
| Phase 2: Excel formatters | 8 hours | Medium |
| Phase 3: Refactor export.py | 6 hours | Medium |
| Phase 4: Update CLI (stats) | 4 hours | Medium |
| Phase 5: Update CLI (remaining) | 8 hours | Medium |
| Phase 6: Visualization updates | 3 hours | Low |
| Phase 7: Testing | 10 hours | High |
| Phase 8: Documentation | 4 hours | Low |
| **Total** | **45 hours** | **Medium** |

---

## Dependencies

### External Libraries

- `openpyxl>=3.0.0` - Already in requirements
- `pandas>=1.3.0` - Already in requirements
- `rich>=10.0.0` - Already in requirements

### Internal Dependencies

- `core.exceptions` - For error handling
- `system_analysis.query_engine` - Query result dataclasses
- `system_analysis.visualization` - ColorScheme dataclass
- `hardware.platform_topology` - For lane parsing (no changes)

---

## Open Questions

1. **Worksheet Naming Convention**: Should we include timestamp in worksheet names?
   - Proposed: No, keep names simple. Use incrementing numbers for duplicates.

2. **Maximum Worksheets**: Should we limit the number of worksheets in one file?
   - Proposed: No hard limit, but warn if exceeding 50 worksheets.

3. **Chart Style**: Should histogram charts be customizable (color, style)?
   - Proposed: Use sensible defaults, defer customization to future enhancement.

4. **File Size Warnings**: Should we warn users about large Excel files?
   - Proposed: Yes, log warning if file size exceeds 50MB.

5. **Concurrent Access**: How to handle concurrent writes to same Excel file?
   - Proposed: File locking detection with clear error message.

---

## Future Enhancements (Out of Scope)

1. Excel conditional formatting (color scales) instead of fixed cell colors
2. Interactive Excel charts with drill-down
3. Excel pivot tables for advanced analysis
4. Multi-sheet dashboards with summary page
5. Customizable color schemes via config file
6. Export to other formats (CSV, JSON, PDF)
7. Batch export (all commands to one file)
8. Template-based Excel export with pre-defined layouts

---

## Conclusion

This implementation plan provides a comprehensive roadmap for replacing the current database export functionality with command-specific Excel export capabilities. The modular approach ensures code reusability, maintainability, and testability. The phased implementation allows for incremental progress and early validation of the architecture.

**Next Steps:**
1. Review this plan with stakeholders
2. Confirm approach and priorities
3. Begin Phase 1 implementation
4. Iterate based on feedback

---

**Document Version:** 1.0
**Date:** 2026-03-16
**Author:** Claude Code
**Status:** Ready for Review
