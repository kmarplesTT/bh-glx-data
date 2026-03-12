"""Export module for system analysis.

This module provides Excel export functionality for database contents
and query results with filtering and conditional formatting.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Union

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from bh_glx_data.core.exceptions import ExcelGenerationError
from bh_glx_data.system_analysis.database import DatabaseManager
from bh_glx_data.system_analysis.query_engine import (
    BERStatistics,
    CustomThresholdCounts,
    ThresholdExceededCounts,
    TrainingFailureCounts,
)
from bh_glx_data.system_analysis.visualization import ColorScheme

logger = logging.getLogger(__name__)


@dataclass
class ExportFilters:
    """Filters for database export.

    Attributes:
        hosts: Filter by hostnames
        train_speeds: Filter by train speeds
        test_status: Filter by test status values
        date_range: Filter by date range (start_date, end_date)
    """

    hosts: Optional[List[str]] = None
    train_speeds: Optional[List[int]] = None
    test_status: Optional[List[str]] = None
    date_range: Optional[Tuple[str, str]] = None


@dataclass
class ExportResult:
    """Result of export operation.

    Attributes:
        rows_exported: Number of rows exported
        sheets_created: Number of sheets created
        file_size_bytes: Size of output file in bytes
        output_path: Path to output file
    """

    rows_exported: int
    sheets_created: int
    file_size_bytes: int
    output_path: Path


class ExcelExporter:
    """Export database data to Excel files.

    This class handles exporting full database contents or query results
    to Excel with multiple sheets, formatting, and conditional formatting
    for heatmap visualization.

    Attributes:
        db: DatabaseManager instance
    """

    def __init__(self, db_manager: DatabaseManager):
        """Initialize Excel exporter.

        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager

    def export_full_database(
        self,
        output_path: Path,
        filters: Optional[ExportFilters] = None,
    ) -> ExportResult:
        """Export entire database (or filtered subset) to Excel.

        Creates Excel workbook with multiple sheets:
        - Summary: Database statistics and metadata
        - PRBS Tests: All PRBS test records
        - Training Failures: Filtered view of training failures
        - BER Exceeded: Filtered view of BER threshold exceeded
        - Metadata: Ingestion history

        Args:
            output_path: Path to output Excel file
            filters: Optional filters (hosts, speeds, date ranges)

        Returns:
            ExportResult with export statistics

        Raises:
            ExcelGenerationError: If export fails
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Build filter clause
            where_clause, params = self._build_filter_clause(filters)

            # Create workbook
            wb = Workbook()

            # Remove default sheet
            if "Sheet" in wb.sheetnames:
                wb.remove(wb["Sheet"])

            sheets_created = 0
            total_rows = 0

            # Summary sheet
            self._create_summary_sheet(wb, filters)
            sheets_created += 1

            # PRBS Tests sheet (all data or filtered)
            query = f"SELECT * FROM prbs_tests WHERE {where_clause}"
            df_all = self.db.execute_query(query, params)

            if not df_all.empty:
                ws_all = wb.create_sheet("PRBS Tests")
                self._write_dataframe_to_sheet(ws_all, df_all)
                sheets_created += 1
                total_rows += len(df_all)

            # Training Failures sheet
            training_where = where_clause + " AND test_status = 'TRAINING_FAIL'"
            training_query = f"SELECT * FROM prbs_tests WHERE {training_where}"
            df_training = self.db.execute_query(training_query, params)

            if not df_training.empty:
                ws_training = wb.create_sheet("Training Failures")
                self._write_dataframe_to_sheet(ws_training, df_training)
                sheets_created += 1

            # BER Exceeded sheet
            ber_where = where_clause + " AND test_status = 'BER_THRESHOLD_EXCEEDED'"
            ber_query = f"SELECT * FROM prbs_tests WHERE {ber_where}"
            df_ber = self.db.execute_query(ber_query, params)

            if not df_ber.empty:
                ws_ber = wb.create_sheet("BER Exceeded")
                self._write_dataframe_to_sheet(ws_ber, df_ber)
                sheets_created += 1

            # Ingestion Metadata sheet
            metadata_df = self.db.execute_query("SELECT * FROM ingestion_metadata")
            if not metadata_df.empty:
                ws_metadata = wb.create_sheet("Ingestion Metadata")
                self._write_dataframe_to_sheet(ws_metadata, metadata_df)
                sheets_created += 1

            # Save workbook
            wb.save(output_path)

            # Get file size
            file_size = output_path.stat().st_size

            logger.info(f"Database exported to {output_path} ({total_rows} rows, {sheets_created} sheets)")

            return ExportResult(
                rows_exported=total_rows,
                sheets_created=sheets_created,
                file_size_bytes=file_size,
                output_path=output_path,
            )

        except Exception as e:
            raise ExcelGenerationError(
                f"Failed to export database: {e}",
                output_path=str(output_path),
            ) from e

    def export_query_result(
        self,
        result: Union[BERStatistics, ThresholdExceededCounts, CustomThresholdCounts, TrainingFailureCounts],
        output_path: Path,
        format: str = "summary",
    ) -> None:
        """Export query result to Excel.

        Formats:
        - "summary": Formatted table with statistics
        - "detailed": Include raw data behind the statistics (not implemented in MVP)

        Args:
            result: Query result to export
            output_path: Path to output Excel file
            format: Export format

        Raises:
            ExcelGenerationError: If export fails
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            wb = Workbook()

            # Remove default sheet
            if "Sheet" in wb.sheetnames:
                wb.remove(wb["Sheet"])

            # Create summary sheet based on result type
            if isinstance(result, BERStatistics):
                self._export_ber_statistics(wb, result)
            elif isinstance(result, (ThresholdExceededCounts, CustomThresholdCounts, TrainingFailureCounts)):
                self._export_counts(wb, result)

            # Save workbook
            wb.save(output_path)

            logger.info(f"Query result exported to {output_path}")

        except Exception as e:
            raise ExcelGenerationError(
                f"Failed to export query result: {e}",
                output_path=str(output_path),
            ) from e

    def export_with_heatmap(
        self,
        result: Union[BERStatistics, ThresholdExceededCounts, CustomThresholdCounts, TrainingFailureCounts],
        output_path: Path,
        color_scheme: Optional[ColorScheme] = None,
    ) -> None:
        """Export query result with conditional formatting as heatmap.

        Args:
            result: Query result to export
            output_path: Path to output Excel file
            color_scheme: Color scheme for conditional formatting

        Raises:
            ExcelGenerationError: If export fails
        """
        try:
            # First export normally
            self.export_query_result(result, output_path, format="summary")

            # Then apply conditional formatting
            wb = load_workbook(output_path)

            if isinstance(result, BERStatistics):
                self._apply_ber_heatmap_formatting(wb, result, color_scheme)
            elif isinstance(result, (ThresholdExceededCounts, CustomThresholdCounts, TrainingFailureCounts)):
                self._apply_count_heatmap_formatting(wb, result, color_scheme)

            wb.save(output_path)

            logger.info(f"Heatmap exported to {output_path}")

        except Exception as e:
            raise ExcelGenerationError(
                f"Failed to export heatmap: {e}",
                output_path=str(output_path),
            ) from e

    def _build_filter_clause(self, filters: Optional[ExportFilters]) -> Tuple[str, tuple]:
        """Build SQL WHERE clause from filters.

        Args:
            filters: Export filters

        Returns:
            Tuple of (where_clause, params)
        """
        if filters is None:
            return "1=1", ()

        conditions = []
        params = []

        if filters.hosts:
            placeholders = ", ".join(["?" for _ in filters.hosts])
            conditions.append(f"host IN ({placeholders})")
            params.extend(filters.hosts)

        if filters.train_speeds:
            placeholders = ", ".join(["?" for _ in filters.train_speeds])
            conditions.append(f"train_speed IN ({placeholders})")
            params.extend(filters.train_speeds)

        if filters.test_status:
            placeholders = ", ".join(["?" for _ in filters.test_status])
            conditions.append(f"test_status IN ({placeholders})")
            params.extend(filters.test_status)

        if filters.date_range:
            start_date, end_date = filters.date_range
            conditions.append("date BETWEEN ? AND ?")
            params.extend([start_date, end_date])

        if conditions:
            where_clause = " AND ".join(conditions)
        else:
            where_clause = "1=1"

        return where_clause, tuple(params)

    def _create_summary_sheet(self, wb: Workbook, filters: Optional[ExportFilters]) -> None:
        """Create summary sheet with database statistics.

        Args:
            wb: Workbook to add sheet to
            filters: Filters applied (for display)
        """
        ws = wb.create_sheet("Summary")

        # Get database stats
        stats = self.db.get_database_stats()

        # Write summary data
        row = 1
        ws.cell(row, 1, "Database Summary")
        ws.cell(row, 1).font = Font(bold=True, size=14)
        row += 2

        ws.cell(row, 1, "Export Date:")
        ws.cell(row, 2, datetime.now().isoformat())
        row += 1

        ws.cell(row, 1, "Total Tests:")
        ws.cell(row, 2, stats.total_tests)
        row += 1

        ws.cell(row, 1, "Unique Systems:")
        ws.cell(row, 2, stats.unique_hosts)
        row += 1

        ws.cell(row, 1, "Train Speeds:")
        ws.cell(row, 2, ", ".join(str(s) for s in stats.unique_speeds))
        row += 2

        # Status breakdown
        ws.cell(row, 1, "Status Breakdown:")
        ws.cell(row, 1).font = Font(bold=True)
        row += 1

        for status, count in stats.status_breakdown.items():
            ws.cell(row, 1, f"  {status}:")
            ws.cell(row, 2, count)
            row += 1

        row += 1

        # Filters (if any)
        if filters:
            ws.cell(row, 1, "Filters Applied:")
            ws.cell(row, 1).font = Font(bold=True)
            row += 1

            if filters.hosts:
                ws.cell(row, 1, "  Hosts:")
                ws.cell(row, 2, ", ".join(filters.hosts))
                row += 1

            if filters.train_speeds:
                ws.cell(row, 1, "  Speeds:")
                ws.cell(row, 2, ", ".join(str(s) for s in filters.train_speeds))
                row += 1

            if filters.test_status:
                ws.cell(row, 1, "  Status:")
                ws.cell(row, 2, ", ".join(filters.test_status))
                row += 1

        # Adjust column widths
        ws.column_dimensions["A"].width = 20
        ws.column_dimensions["B"].width = 40

    def _write_dataframe_to_sheet(self, ws, df: pd.DataFrame) -> None:
        """Write DataFrame to worksheet with formatting.

        Args:
            ws: Worksheet to write to
            df: DataFrame to write
        """
        # Write headers
        for col_idx, col_name in enumerate(df.columns, start=1):
            cell = ws.cell(1, col_idx, col_name)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")

        # Write data
        for row_idx, row in enumerate(df.itertuples(index=False), start=2):
            for col_idx, value in enumerate(row, start=1):
                ws.cell(row_idx, col_idx, value)

        # Adjust column widths
        for col_idx in range(1, len(df.columns) + 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = 15

    def _export_ber_statistics(self, wb: Workbook, stats: BERStatistics) -> None:
        """Export BER statistics to workbook.

        Args:
            wb: Workbook to add sheet to
            stats: BER statistics
        """
        ws = wb.create_sheet("BER Statistics")

        # Write headers
        ws.cell(1, 1, "Lane")
        ws.cell(1, 2, "Min BER")
        ws.cell(1, 3, "Max BER")
        ws.cell(1, 4, "Avg BER")
        ws.cell(1, 5, "Samples")

        # Format headers
        for col in range(1, 6):
            ws.cell(1, col).font = Font(bold=True)
            ws.cell(1, col).fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")

        # Write data
        row = 2
        for lane_id in sorted(stats.lane_stats.keys()):
            lane_stat = stats.lane_stats[lane_id]

            ws.cell(row, 1, lane_id)
            ws.cell(row, 2, lane_stat.min_ber)
            ws.cell(row, 3, lane_stat.max_ber)
            ws.cell(row, 4, lane_stat.avg_ber)
            ws.cell(row, 5, lane_stat.sample_count)

            row += 1

        # Adjust column widths
        ws.column_dimensions["A"].width = 25
        for col in ["B", "C", "D"]:
            ws.column_dimensions[col].width = 15
        ws.column_dimensions["E"].width = 10

    def _export_counts(
        self,
        wb: Workbook,
        counts: Union[ThresholdExceededCounts, CustomThresholdCounts, TrainingFailureCounts],
    ) -> None:
        """Export count data to workbook.

        Args:
            wb: Workbook to add sheet to
            counts: Count data
        """
        # Determine sheet name
        if isinstance(counts, ThresholdExceededCounts):
            sheet_name = "BER Threshold Exceeded"
        elif isinstance(counts, CustomThresholdCounts):
            sheet_name = "Custom Threshold Counts"
        elif isinstance(counts, TrainingFailureCounts):
            sheet_name = "Training Failures"
        else:
            sheet_name = "Lane Counts"

        ws = wb.create_sheet(sheet_name)

        # Write headers
        ws.cell(1, 1, "Lane")
        ws.cell(1, 2, "Count")

        # Format headers
        for col in range(1, 3):
            ws.cell(1, col).font = Font(bold=True)
            ws.cell(1, col).fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")

        # Write data
        row = 2
        for lane_id in sorted(counts.lane_counts.keys()):
            count = counts.lane_counts[lane_id]

            ws.cell(row, 1, lane_id)
            ws.cell(row, 2, count)

            row += 1

        # Adjust column widths
        ws.column_dimensions["A"].width = 25
        ws.column_dimensions["B"].width = 10

    def _apply_ber_heatmap_formatting(
        self,
        wb: Workbook,
        stats: BERStatistics,
        color_scheme: Optional[ColorScheme],
    ) -> None:
        """Apply conditional formatting for BER heatmap.

        Args:
            wb: Workbook with BER statistics
            stats: BER statistics
            color_scheme: Color scheme (not used in MVP - placeholder)
        """
        # Placeholder for conditional formatting
        # In MVP, we just apply basic formatting
        # Full implementation would use openpyxl conditional formatting
        logger.debug("BER heatmap formatting applied (basic)")

    def _apply_count_heatmap_formatting(
        self,
        wb: Workbook,
        counts: Union[ThresholdExceededCounts, CustomThresholdCounts, TrainingFailureCounts],
        color_scheme: Optional[ColorScheme],
    ) -> None:
        """Apply conditional formatting for count heatmap.

        Args:
            wb: Workbook with count data
            counts: Count data
            color_scheme: Color scheme (not used in MVP - placeholder)
        """
        # Placeholder for conditional formatting
        logger.debug("Count heatmap formatting applied (basic)")
