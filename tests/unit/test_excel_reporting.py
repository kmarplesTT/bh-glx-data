"""Unit tests for excel_reporting module."""

import csv
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pandas as pd
import pytest

from bh_glx_data.core.exceptions import (
    DataProcessingError,
    ExcelGenerationError,
    TemplateError,
)
from bh_glx_data.excel_reporting.generator import (
    compile_test_data,
    extract_firmware_version,
    extract_system_hostname,
    generate_excel_summary,
    group_csvs_by_system,
    identify_test_type,
    process_all_systems,
    scan_csv_files,
)
from bh_glx_data.excel_reporting.templates import (
    load_template,
    paste_data_to_sheet,
    refresh_pivot_tables,
    save_workbook,
    update_pivot_table_source,
)


class TestExtractFirmwareVersion:
    """Test firmware version extraction."""

    def test_extract_erisc_format(self):
        """Test extracting erisc format version."""
        path = Path("data_erisc_v1_7_103.csv")
        version = extract_firmware_version(path)
        assert version == "erisc_v1_7_103"

    def test_extract_v_format(self):
        """Test extracting v format version."""
        path = Path("test_v2_0_5.csv")
        version = extract_firmware_version(path)
        assert version == "v2_0_5"

    def test_extract_no_version(self):
        """Test extracting when no version present."""
        path = Path("test_data.csv")
        version = extract_firmware_version(path)
        assert version == "unknown"

    def test_extract_erisc_priority(self):
        """Test that erisc format has priority."""
        path = Path("v1_0_0_erisc_v2_0_0.csv")
        version = extract_firmware_version(path)
        assert version == "erisc_v2_0_0"


class TestIdentifyTestType:
    """Test test type identification."""

    def test_identify_prbs_from_column(self, tmp_path):
        """Test identifying PRBS from test_type column."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["test_type", "bus_id"])
            writer.writerow(["TestType.SERDES_PRBS", "01:00.0"])

        test_type = identify_test_type(csv_file)
        assert test_type == "PRBS"

    def test_identify_data_from_column(self, tmp_path):
        """Test identifying DATA from test_type column."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["test_type", "bus_id"])
            writer.writerow(["TestType.SIMPLE_PACKET", "01:00.0"])

        test_type = identify_test_type(csv_file)
        assert test_type == "DATA"

    def test_identify_from_filename_prbs(self, tmp_path):
        """Test identifying PRBS from filename."""
        csv_file = tmp_path / "prbs_test_results.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["bus_id"])
            writer.writerow(["01:00.0"])

        test_type = identify_test_type(csv_file)
        assert test_type == "PRBS"

    def test_identify_from_filename_data(self, tmp_path):
        """Test identifying DATA from filename."""
        csv_file = tmp_path / "data_test_results.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["bus_id"])
            writer.writerow(["01:00.0"])

        test_type = identify_test_type(csv_file)
        assert test_type == "DATA"

    def test_identify_unknown(self, tmp_path):
        """Test identifying unknown test type."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["bus_id"])
            writer.writerow(["01:00.0"])

        test_type = identify_test_type(csv_file)
        assert test_type is None


class TestExtractSystemHostname:
    """Test hostname extraction."""

    def test_extract_hostname_success(self, tmp_path):
        """Test successful hostname extraction."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["host", "bus_id"])
            writer.writerow(["bh-glx-b02u02", "01:00.0"])

        hostname = extract_system_hostname(csv_file)
        assert hostname == "bh-glx-b02u02"

    def test_extract_hostname_no_host_column(self, tmp_path):
        """Test extracting hostname when host column missing."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["bus_id"])
            writer.writerow(["01:00.0"])

        hostname = extract_system_hostname(csv_file)
        assert hostname is None

    def test_extract_hostname_empty(self, tmp_path):
        """Test extracting hostname when empty."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["host", "bus_id"])
            writer.writerow(["", "01:00.0"])

        hostname = extract_system_hostname(csv_file)
        assert hostname is None

    def test_extract_hostname_with_spaces(self, tmp_path):
        """Test extracting hostname with spaces."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["host", "bus_id"])
            writer.writerow(["  bh-glx-b02u02  ", "01:00.0"])

        hostname = extract_system_hostname(csv_file)
        assert hostname == "bh-glx-b02u02"


class TestScanCSVFiles:
    """Test CSV file scanning."""

    def test_scan_csv_files_success(self, tmp_path):
        """Test scanning directory with CSV files."""
        (tmp_path / "test1.csv").touch()
        (tmp_path / "test2.csv").touch()
        (tmp_path / "readme.txt").touch()

        csv_files = scan_csv_files(tmp_path)

        assert len(csv_files) == 2
        assert all(f.suffix == ".csv" for f in csv_files)

    def test_scan_csv_files_empty_directory(self, tmp_path):
        """Test scanning empty directory."""
        csv_files = scan_csv_files(tmp_path)
        assert csv_files == []

    def test_scan_csv_files_nonexistent_directory(self, tmp_path):
        """Test scanning nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(DataProcessingError) as exc_info:
            scan_csv_files(nonexistent)

        assert "does not exist" in str(exc_info.value)


class TestGroupCSVsBySystem:
    """Test CSV grouping by system."""

    def test_group_csvs_by_system(self, tmp_path):
        """Test grouping CSV files by system and firmware."""
        # Create test CSV files
        csv1 = tmp_path / "test_erisc_v1_7_103.csv"
        with open(csv1, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["host", "test_type", "bus_id"])
            writer.writerow(["bh-glx-b02u02", "TestType.SERDES_PRBS", "01:00.0"])

        csv2 = tmp_path / "test_erisc_v1_7_103_data.csv"
        with open(csv2, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["host", "test_type", "bus_id"])
            writer.writerow(["bh-glx-b02u02", "TestType.SIMPLE_PACKET", "01:00.0"])

        csv3 = tmp_path / "test_erisc_v2_0_0.csv"
        with open(csv3, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["host", "test_type", "bus_id"])
            writer.writerow(["bh-glx-b03u02", "TestType.SERDES_PRBS", "01:00.0"])

        csv_files = [csv1, csv2, csv3]
        grouped = group_csvs_by_system(csv_files)

        assert len(grouped) == 2
        assert ("bh-glx-b02u02", "erisc_v1_7_103") in grouped
        assert ("bh-glx-b03u02", "erisc_v2_0_0") in grouped

        # Check that files are grouped correctly
        assert len(grouped[("bh-glx-b02u02", "erisc_v1_7_103")]["PRBS"]) == 1
        assert len(grouped[("bh-glx-b02u02", "erisc_v1_7_103")]["DATA"]) == 1
        assert len(grouped[("bh-glx-b03u02", "erisc_v2_0_0")]["PRBS"]) == 1

    def test_group_csvs_skips_invalid(self, tmp_path):
        """Test grouping skips files without hostname or test type."""
        # CSV without hostname
        csv1 = tmp_path / "test1.csv"
        with open(csv1, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["test_type", "bus_id"])
            writer.writerow(["TestType.SERDES_PRBS", "01:00.0"])

        # CSV without test type
        csv2 = tmp_path / "test2.csv"
        with open(csv2, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["host", "bus_id"])
            writer.writerow(["bh-glx-b02u02", "01:00.0"])

        csv_files = [csv1, csv2]
        grouped = group_csvs_by_system(csv_files)

        assert len(grouped) == 0


class TestCompileTestData:
    """Test compiling test data from multiple CSV files."""

    def test_compile_test_data_success(self, tmp_path):
        """Test compiling data from multiple CSV files."""
        csv1 = tmp_path / "test1.csv"
        with open(csv1, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["bus_id", "test_status"])
            writer.writerow(["01:00.0", "ETH_ACTIVE"])

        csv2 = tmp_path / "test2.csv"
        with open(csv2, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["bus_id", "test_status"])
            writer.writerow(["02:00.0", "ETH_ACTIVE"])

        csv_files = [csv1, csv2]
        df = compile_test_data(csv_files, "PRBS")

        assert df is not None
        assert len(df) == 2
        assert "bus_id" in df.columns

    def test_compile_test_data_empty_list(self, tmp_path):
        """Test compiling with empty file list."""
        df = compile_test_data([], "PRBS")
        assert df is None

    def test_compile_test_data_skip_empty_files(self, tmp_path):
        """Test that empty CSV files are skipped."""
        csv1 = tmp_path / "test1.csv"
        with open(csv1, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["bus_id", "test_status"])
            # No data rows

        csv2 = tmp_path / "test2.csv"
        with open(csv2, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["bus_id", "test_status"])
            writer.writerow(["02:00.0", "ETH_ACTIVE"])

        csv_files = [csv1, csv2]
        df = compile_test_data(csv_files, "PRBS")

        assert df is not None
        assert len(df) == 1


class TestLoadTemplate:
    """Test template loading."""

    def test_load_template_success(self, tmp_path):
        """Test successful template loading."""
        template_path = tmp_path / "template.xlsx"

        with patch("openpyxl.load_workbook") as mock_load:
            mock_workbook = MagicMock()
            mock_load.return_value = mock_workbook

            # Create dummy file
            template_path.touch()

            workbook = load_template(template_path)

            assert workbook == mock_workbook
            mock_load.assert_called_once_with(template_path)

    def test_load_template_not_found(self, tmp_path):
        """Test template not found."""
        template_path = tmp_path / "nonexistent.xlsx"

        with pytest.raises(TemplateError) as exc_info:
            load_template(template_path)

        assert "not found" in str(exc_info.value)

    def test_load_template_error(self, tmp_path):
        """Test template loading error."""
        template_path = tmp_path / "template.xlsx"
        template_path.touch()

        with patch("openpyxl.load_workbook") as mock_load:
            mock_load.side_effect = Exception("Load error")

            with pytest.raises(TemplateError) as exc_info:
                load_template(template_path)

            assert "Error loading template" in str(exc_info.value)


class TestPasteDataToSheet:
    """Test pasting data to Excel sheet."""

    def test_paste_data_to_sheet_success(self):
        """Test successful data pasting."""
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_sheet.max_row = 0
        mock_workbook.__getitem__.return_value = mock_sheet
        mock_workbook.sheetnames = ["test_sheet"]

        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})

        last_row, last_col = paste_data_to_sheet(
            mock_workbook,
            "test_sheet",
            df,
        )

        assert last_row == 4  # 3 data rows + 1 header
        assert last_col == 2
        mock_workbook.__getitem__.assert_called_with("test_sheet")

    def test_paste_data_to_sheet_not_found(self):
        """Test pasting to nonexistent sheet."""
        mock_workbook = MagicMock()
        mock_workbook.sheetnames = ["other_sheet"]

        df = pd.DataFrame({"col1": [1, 2, 3]})

        with pytest.raises(ExcelGenerationError) as exc_info:
            paste_data_to_sheet(mock_workbook, "test_sheet", df)

        assert "not found" in str(exc_info.value)

    def test_paste_data_clears_existing(self):
        """Test that existing data is cleared."""
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_sheet.max_row = 100  # Existing data
        mock_workbook.__getitem__.return_value = mock_sheet
        mock_workbook.sheetnames = ["test_sheet"]

        df = pd.DataFrame({"col1": [1, 2]})

        paste_data_to_sheet(mock_workbook, "test_sheet", df)

        # Should delete existing rows
        mock_sheet.delete_rows.assert_called_once_with(1, 100)


class TestUpdatePivotTableSource:
    """Test updating pivot table source."""

    def test_update_pivot_table_source_success(self):
        """Test successful pivot table source update."""
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.sheetnames = ["pivot_sheet"]
        mock_workbook.__getitem__.return_value = mock_sheet

        # Mock pivot table structure
        mock_pivot = MagicMock()
        mock_cache = MagicMock()
        mock_source = MagicMock()
        mock_ws_source = MagicMock()

        mock_pivot.cache = mock_cache
        mock_cache.cacheSource = mock_source
        mock_source.worksheetSource = mock_ws_source
        mock_cache.refreshOnLoad = False

        mock_sheet._pivots = [mock_pivot]

        result = update_pivot_table_source(
            mock_workbook,
            "pivot_sheet",
            "data_sheet",
            "A1:Z100",
        )

        assert result is True
        assert mock_ws_source.ref == "A1:Z100"
        assert mock_ws_source.sheet == "data_sheet"
        assert mock_cache.refreshOnLoad is True

    def test_update_pivot_table_source_no_sheet(self):
        """Test updating nonexistent sheet."""
        mock_workbook = MagicMock()
        mock_workbook.sheetnames = ["other_sheet"]

        result = update_pivot_table_source(
            mock_workbook,
            "pivot_sheet",
            "data_sheet",
            "A1:Z100",
        )

        assert result is False

    def test_update_pivot_table_source_no_pivots(self):
        """Test updating sheet without pivot tables."""
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.sheetnames = ["pivot_sheet"]
        mock_workbook.__getitem__.return_value = mock_sheet
        mock_sheet._pivots = []

        result = update_pivot_table_source(
            mock_workbook,
            "pivot_sheet",
            "data_sheet",
            "A1:Z100",
        )

        assert result is False


class TestRefreshPivotTables:
    """Test refreshing pivot tables."""

    def test_refresh_pivot_tables_success(self):
        """Test successful pivot table refresh."""
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.sheetnames = ["pivot_sheet"]
        mock_workbook.__getitem__.return_value = mock_sheet

        mock_pivot = MagicMock()
        mock_cache = MagicMock()
        mock_cache.refreshOnLoad = False
        mock_pivot.cache = mock_cache

        mock_sheet._pivots = [mock_pivot]

        result = refresh_pivot_tables(mock_workbook, "pivot_sheet")

        assert result is True
        assert mock_cache.refreshOnLoad is True

    def test_refresh_pivot_tables_no_sheet(self):
        """Test refreshing nonexistent sheet."""
        mock_workbook = MagicMock()
        mock_workbook.sheetnames = ["other_sheet"]

        result = refresh_pivot_tables(mock_workbook, "pivot_sheet")

        assert result is False

    def test_refresh_pivot_tables_no_pivots(self):
        """Test refreshing sheet without pivot tables."""
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.sheetnames = ["pivot_sheet"]
        mock_workbook.__getitem__.return_value = mock_sheet
        mock_sheet._pivots = []

        result = refresh_pivot_tables(mock_workbook, "pivot_sheet")

        assert result is True  # Not an error, just no pivots


class TestSaveWorkbook:
    """Test saving workbook."""

    def test_save_workbook_success(self, tmp_path):
        """Test successful workbook save."""
        mock_workbook = MagicMock()
        output_path = tmp_path / "output.xlsx"

        save_workbook(mock_workbook, output_path)

        mock_workbook.save.assert_called_once_with(output_path)

    def test_save_workbook_error(self, tmp_path):
        """Test workbook save error."""
        mock_workbook = MagicMock()
        mock_workbook.save.side_effect = Exception("Save error")
        output_path = tmp_path / "output.xlsx"

        with pytest.raises(ExcelGenerationError) as exc_info:
            save_workbook(mock_workbook, output_path)

        assert "Failed to save" in str(exc_info.value)


class TestGenerateExcelSummary:
    """Test Excel summary generation."""

    @patch("bh_glx_data.excel_reporting.generator.load_template")
    @patch("bh_glx_data.excel_reporting.generator.paste_data_to_sheet")
    @patch("bh_glx_data.excel_reporting.generator.update_pivot_table_source")
    @patch("bh_glx_data.excel_reporting.generator.refresh_pivot_tables")
    @patch("bh_glx_data.excel_reporting.generator.save_workbook")
    def test_generate_excel_summary_success(
        self,
        mock_save,
        mock_refresh,
        mock_update,
        mock_paste,
        mock_load,
        tmp_path,
    ):
        """Test successful Excel summary generation."""
        mock_workbook = MagicMock()
        mock_workbook.sheetnames = ["raw prbs data", "raw data", "PRBS Summary", "DATA Summary"]
        mock_load.return_value = mock_workbook
        mock_paste.return_value = (100, 10)

        prbs_df = pd.DataFrame({"col1": [1, 2, 3]})
        data_df = pd.DataFrame({"col1": [4, 5, 6]})

        template_path = tmp_path / "template.xlsx"
        template_path.touch()
        output_dir = tmp_path / "output"

        result = generate_excel_summary(
            "bh-glx-b02u02",
            "erisc_v1_7_103",
            prbs_df,
            data_df,
            template_path,
            output_dir,
        )

        assert result == output_dir / "bh-glx-b02u02_erisc_v1_7_103.xlsx"
        assert output_dir.exists()
        mock_save.assert_called_once()


class TestProcessAllSystems:
    """Test processing all systems."""

    def test_process_all_systems_success(self, tmp_path):
        """Test successful processing of all systems."""
        # Create test CSV files
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        csv1 = data_dir / "test_erisc_v1_7_103.csv"
        with open(csv1, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["host", "test_type", "bus_id"])
            writer.writerow(["bh-glx-b02u02", "TestType.SERDES_PRBS", "01:00.0"])

        template_path = tmp_path / "template.xlsx"
        template_path.touch()
        output_dir = tmp_path / "output"

        with patch("bh_glx_data.excel_reporting.generator.generate_excel_summary") as mock_gen:
            mock_gen.return_value = output_dir / "test.xlsx"

            result = process_all_systems(
                data_dir,
                template_path,
                output_dir,
            )

            assert result["success_count"] > 0
            assert len(result["generated_files"]) > 0

    def test_process_all_systems_no_csv_files(self, tmp_path):
        """Test processing with no CSV files."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        template_path = tmp_path / "template.xlsx"
        output_dir = tmp_path / "output"

        with pytest.raises(DataProcessingError) as exc_info:
            process_all_systems(data_dir, template_path, output_dir)

        assert "No CSV files found" in str(exc_info.value)

    def test_process_all_systems_with_filter(self, tmp_path):
        """Test processing with system filter."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create test CSV for multiple systems
        csv1 = data_dir / "test1_erisc_v1_7_103.csv"
        with open(csv1, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["host", "test_type", "bus_id"])
            writer.writerow(["bh-glx-b02u02", "TestType.SERDES_PRBS", "01:00.0"])

        csv2 = data_dir / "test2_erisc_v1_7_103.csv"
        with open(csv2, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["host", "test_type", "bus_id"])
            writer.writerow(["bh-glx-b03u02", "TestType.SERDES_PRBS", "01:00.0"])

        template_path = tmp_path / "template.xlsx"
        template_path.touch()
        output_dir = tmp_path / "output"

        with patch("bh_glx_data.excel_reporting.generator.generate_excel_summary") as mock_gen:
            mock_gen.return_value = output_dir / "test.xlsx"

            result = process_all_systems(
                data_dir,
                template_path,
                output_dir,
                system_filter=["bh-glx-b02u02"],
            )

            # Should only process one system
            assert result["total_combinations"] == 1
