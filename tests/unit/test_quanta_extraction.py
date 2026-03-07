"""Unit tests for quanta_extraction module."""

import tarfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pandas as pd
import pytest

from bh_glx_data.core.exceptions import DataProcessingError
from bh_glx_data.core.models import QC3TestResult
from bh_glx_data.quanta_extraction.analyzer import (
    _get_cell_value,
    _get_numeric_value,
    analyze_excel_failures,
    extract_failed_serial_numbers,
    print_failures_summary,
)
from bh_glx_data.quanta_extraction.extractor import extract_csv_from_archive


class TestGetCellValue:
    """Test _get_cell_value helper function."""

    def test_get_cell_value_normal(self):
        """Test getting normal cell value."""
        mock_cell = MagicMock()
        mock_cell.value = "test_value"

        result = _get_cell_value(mock_cell)
        assert result == "test_value"

    def test_get_cell_value_none_cell(self):
        """Test getting value from None cell."""
        result = _get_cell_value(None)
        assert result == ""

    def test_get_cell_value_none_value(self):
        """Test getting None value from cell."""
        mock_cell = MagicMock()
        mock_cell.value = None

        result = _get_cell_value(mock_cell)
        assert result == ""

    def test_get_cell_value_with_whitespace(self):
        """Test getting value with whitespace."""
        mock_cell = MagicMock()
        mock_cell.value = "  test_value  "

        result = _get_cell_value(mock_cell)
        assert result == "test_value"


class TestGetNumericValue:
    """Test _get_numeric_value helper function."""

    def test_get_numeric_value_integer(self):
        """Test getting integer value."""
        mock_cell = MagicMock()
        mock_cell.value = 42

        result = _get_numeric_value(mock_cell)
        assert result == 42

    def test_get_numeric_value_float(self):
        """Test getting float value."""
        mock_cell = MagicMock()
        mock_cell.value = 42.7

        result = _get_numeric_value(mock_cell)
        assert result == 42

    def test_get_numeric_value_string_number(self):
        """Test getting string number value."""
        mock_cell = MagicMock()
        mock_cell.value = "42"

        result = _get_numeric_value(mock_cell)
        assert result == 42

    def test_get_numeric_value_none_cell(self):
        """Test getting value from None cell."""
        result = _get_numeric_value(None)
        assert result == 0

    def test_get_numeric_value_none_value(self):
        """Test getting None value."""
        mock_cell = MagicMock()
        mock_cell.value = None

        result = _get_numeric_value(mock_cell)
        assert result == 0

    def test_get_numeric_value_invalid(self):
        """Test getting invalid numeric value."""
        mock_cell = MagicMock()
        mock_cell.value = "not_a_number"

        result = _get_numeric_value(mock_cell)
        assert result == 0


class TestAnalyzeExcelFailures:
    """Test analyze_excel_failures function."""

    @patch("bh_glx_data.quanta_extraction.analyzer.load_workbook")
    def test_analyze_excel_failures_with_openpyxl(self, mock_load_wb, tmp_path):
        """Test analyzing Excel file with openpyxl."""
        excel_file = tmp_path / "test.xlsx"
        excel_file.touch()

        # Mock workbook and sheet
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.active = mock_sheet
        mock_sheet.max_row = 3  # Header + 2 data rows
        mock_load_wb.return_value = mock_workbook

        # Mock cell values
        def cell_mock(row, column):
            cell = MagicMock()
            # Row 2: failure
            if row == 2:
                if column == 3:  # SN
                    cell.value = "SN123"
                elif column == 10:  # ASIC
                    cell.value = "ASIC1"
                elif column == 11:  # PORT
                    cell.value = "PORT1"
                elif column == 13:  # TYPE
                    cell.value = "DATA"
                elif column == 14:  # Failure Count
                    cell.value = 5
            # Row 3: no failure
            elif row == 3:
                if column == 14:  # Failure Count
                    cell.value = 0
            return cell

        mock_sheet.cell = cell_mock

        failures = analyze_excel_failures(excel_file)

        assert len(failures) == 1
        assert failures[0].serial_number == "SN123"
        assert failures[0].asic == "ASIC1"
        assert failures[0].port == "PORT1"
        assert failures[0].failure_count == 5
        assert failures[0].test_type == "DATA"

    @patch("bh_glx_data.quanta_extraction.analyzer.HAS_OPENPYXL", False)
    @patch("bh_glx_data.quanta_extraction.analyzer.HAS_PANDAS", True)
    @patch("bh_glx_data.quanta_extraction.analyzer.pd.read_excel")
    def test_analyze_excel_failures_with_pandas(self, mock_read_excel, tmp_path):
        """Test analyzing Excel file with pandas."""
        excel_file = tmp_path / "test.xlsx"
        excel_file.touch()

        # Mock DataFrame
        df_data = {
            "col1": ["x", "y"],
            "col2": ["x", "y"],
            "SN": ["SN123", "SN456"],  # Column C (index 2)
            "col4": ["x", "y"],
            "col5": ["x", "y"],
            "col6": ["x", "y"],
            "col7": ["x", "y"],
            "col8": ["x", "y"],
            "col9": ["x", "y"],
            "ASIC": ["ASIC1", "ASIC2"],  # Column J (index 9)
            "PORT": ["PORT1", "PORT2"],  # Column K (index 10)
            "col12": ["x", "y"],
            "TYPE": ["DATA", "PRBS"],  # Column M (index 12)
            "Failure Count": [5, 0],  # Column N (index 13)
        }
        mock_df = pd.DataFrame(df_data)
        mock_read_excel.return_value = mock_df

        failures = analyze_excel_failures(excel_file)

        assert len(failures) == 1
        assert failures[0].serial_number == "SN123"
        assert failures[0].asic == "ASIC1"
        assert failures[0].port == "PORT1"
        assert failures[0].failure_count == 5

    def test_analyze_excel_failures_file_not_found(self, tmp_path):
        """Test analyzing nonexistent Excel file."""
        excel_file = tmp_path / "nonexistent.xlsx"

        with pytest.raises(DataProcessingError) as exc_info:
            analyze_excel_failures(excel_file)

        assert "not found" in str(exc_info.value)

    @patch("bh_glx_data.quanta_extraction.analyzer.HAS_OPENPYXL", False)
    @patch("bh_glx_data.quanta_extraction.analyzer.HAS_PANDAS", False)
    def test_analyze_excel_failures_no_libraries(self, tmp_path):
        """Test analyzing when neither library is available."""
        excel_file = tmp_path / "test.xlsx"
        excel_file.touch()

        with pytest.raises(DataProcessingError) as exc_info:
            analyze_excel_failures(excel_file)

        assert "Neither openpyxl nor pandas" in str(exc_info.value)


class TestPrintFailuresSummary:
    """Test print_failures_summary function."""

    def test_print_failures_summary_with_failures(self, capsys):
        """Test printing failures summary."""
        failures = [
            QC3TestResult(
                serial_number="SN123",
                asic="ASIC1",
                port="PORT1",
                failure_count=5,
                test_type="DATA",
            ),
            QC3TestResult(
                serial_number="SN456",
                asic="ASIC2",
                port="PORT2",
                failure_count=3,
                test_type="PRBS",
            ),
        ]

        print_failures_summary(failures)

        captured = capsys.readouterr()
        assert "SN123" in captured.out
        assert "SN456" in captured.out
        assert "Total failures found: 2" in captured.out

    def test_print_failures_summary_no_failures(self, capsys):
        """Test printing summary with no failures."""
        print_failures_summary([])

        captured = capsys.readouterr()
        assert "No failures found" in captured.out


class TestExtractFailedSerialNumbers:
    """Test extract_failed_serial_numbers function."""

    def test_extract_failed_serial_numbers(self):
        """Test extracting serial numbers from failures."""
        failures = [
            QC3TestResult(
                serial_number="SN123",
                asic="ASIC1",
                port="PORT1",
                failure_count=5,
                test_type="DATA",
            ),
            QC3TestResult(
                serial_number="SN456",
                asic="ASIC2",
                port="PORT2",
                failure_count=3,
                test_type="PRBS",
            ),
            QC3TestResult(
                serial_number="SN123",  # Duplicate
                asic="ASIC3",
                port="PORT3",
                failure_count=1,
                test_type="DATA",
            ),
        ]

        serial_numbers = extract_failed_serial_numbers(failures)

        assert len(serial_numbers) == 2
        assert "SN123" in serial_numbers
        assert "SN456" in serial_numbers

    def test_extract_failed_serial_numbers_empty(self):
        """Test extracting from empty list."""
        serial_numbers = extract_failed_serial_numbers([])
        assert serial_numbers == []

    def test_extract_failed_serial_numbers_sorted(self):
        """Test that serial numbers are sorted."""
        failures = [
            QC3TestResult(
                serial_number="SN999",
                asic="ASIC1",
                port="PORT1",
                failure_count=5,
                test_type="DATA",
            ),
            QC3TestResult(
                serial_number="SN123",
                asic="ASIC2",
                port="PORT2",
                failure_count=3,
                test_type="PRBS",
            ),
        ]

        serial_numbers = extract_failed_serial_numbers(failures)

        assert serial_numbers == ["SN123", "SN999"]


class TestExtractCSVFromArchive:
    """Test extract_csv_from_archive function."""

    def test_extract_csv_from_archive_not_found(self, tmp_path):
        """Test extracting from nonexistent archive."""
        archive_path = tmp_path / "nonexistent.tar.gz"
        output_dir = tmp_path / "output"

        with pytest.raises(DataProcessingError) as exc_info:
            extract_csv_from_archive(archive_path, output_dir)

        assert "not found" in str(exc_info.value)

    def test_extract_csv_from_archive_invalid_extension(self, tmp_path):
        """Test extracting from file with invalid extension."""
        archive_path = tmp_path / "test.txt"
        archive_path.touch()
        output_dir = tmp_path / "output"

        with pytest.raises(DataProcessingError) as exc_info:
            extract_csv_from_archive(archive_path, output_dir)

        assert "Expected a .tar.gz file" in str(exc_info.value)

    @patch("tarfile.open")
    def test_extract_csv_from_archive_no_funtest(self, mock_tarfile_open, tmp_path):
        """Test extracting when no funtest archives found."""
        archive_path = tmp_path / "test.tar.gz"
        archive_path.touch()
        output_dir = tmp_path / "output"

        # Mock tar file with no matching members
        mock_tar = MagicMock()
        mock_tar.getmembers.return_value = []
        mock_tarfile_open.return_value.__enter__.return_value = mock_tar

        result = extract_csv_from_archive(archive_path, output_dir)

        assert result.success is False
        assert result.total_files == 0
        assert "ft_eth_stress" in result.error_message or "ft_burnin" in result.error_message

    @patch("tarfile.open")
    @patch("shutil.copy2")
    def test_extract_csv_from_archive_success(self, mock_copy, mock_tarfile_open, tmp_path):
        """Test successful CSV extraction."""
        archive_path = tmp_path / "test.tar.gz"
        archive_path.touch()
        output_dir = tmp_path / "output"

        # Mock outer tar file
        mock_outer_tar = MagicMock()
        mock_member = MagicMock()
        mock_member.name = "tt_funtest_ubb_1/ft_eth_stress_test.tar.gz"
        mock_outer_tar.getmembers.return_value = [mock_member]

        # Mock inner tar file
        mock_inner_tar = MagicMock()
        mock_csv_member = MagicMock()
        mock_csv_member.name = "ft_eth_stress/data_test_results.csv"
        mock_inner_tar.getmembers.return_value = [mock_csv_member]

        # Setup mock context manager behavior
        def mock_tar_context(*args, **kwargs):
            if "ft_eth_stress_test.tar.gz" in str(args[0]):
                return mock_inner_tar
            return mock_outer_tar

        mock_tarfile_open.side_effect = [
            MagicMock(__enter__=lambda self: mock_outer_tar, __exit__=lambda *args: None),
            MagicMock(__enter__=lambda self: mock_inner_tar, __exit__=lambda *args: None),
        ]

        result = extract_csv_from_archive(archive_path, output_dir)

        assert result.success is True
        assert result.total_files == 1
        assert len(result.extracted_files) == 1

    @patch("tarfile.open")
    def test_extract_csv_from_archive_no_csv_files(self, mock_tarfile_open, tmp_path):
        """Test extracting when no CSV files found in archive."""
        archive_path = tmp_path / "test.tar.gz"
        archive_path.touch()
        output_dir = tmp_path / "output"

        # Mock outer tar file with funtest archive
        mock_outer_tar = MagicMock()
        mock_member = MagicMock()
        mock_member.name = "tt_funtest_ubb_1/ft_eth_stress_test.tar.gz"
        mock_outer_tar.getmembers.return_value = [mock_member]

        # Mock inner tar file with no CSV files
        mock_inner_tar = MagicMock()
        mock_inner_tar.getmembers.return_value = []

        mock_tarfile_open.side_effect = [
            MagicMock(__enter__=lambda self: mock_outer_tar, __exit__=lambda *args: None),
            MagicMock(__enter__=lambda self: mock_inner_tar, __exit__=lambda *args: None),
        ]

        result = extract_csv_from_archive(archive_path, output_dir)

        # Should complete but with no files extracted and error message
        assert len(result.extracted_files) == 0
        assert result.success is False
        assert result.error_message is not None

    @patch("tarfile.open")
    def test_extract_csv_from_archive_with_basename(self, mock_tarfile_open, tmp_path):
        """Test extraction with custom basename."""
        archive_path = tmp_path / "test.tar.gz"
        archive_path.touch()
        output_dir = tmp_path / "output"

        # Mock outer tar file
        mock_outer_tar = MagicMock()
        mock_member = MagicMock()
        mock_member.name = "tt_funtest_ubb_1/ft_eth_stress_test.tar.gz"
        mock_outer_tar.getmembers.return_value = [mock_member]

        # Mock inner tar file
        mock_inner_tar = MagicMock()
        mock_csv_member = MagicMock()
        mock_csv_member.name = "ft_eth_stress/data_test_results.csv"
        mock_inner_tar.getmembers.return_value = [mock_csv_member]

        mock_tarfile_open.side_effect = [
            MagicMock(__enter__=lambda self: mock_outer_tar, __exit__=lambda *args: None),
            MagicMock(__enter__=lambda self: mock_inner_tar, __exit__=lambda *args: None),
        ]

        result = extract_csv_from_archive(
            archive_path,
            output_dir,
            archive_basename="custom_name",
        )

        # Check that custom basename was used in filenames
        if result.extracted_files:
            assert "custom_name" in str(result.extracted_files[0])

    @patch("tarfile.open")
    def test_extract_csv_from_archive_tar_error(self, mock_tarfile_open, tmp_path):
        """Test handling tarfile error."""
        archive_path = tmp_path / "test.tar.gz"
        archive_path.touch()
        output_dir = tmp_path / "output"

        mock_tarfile_open.side_effect = tarfile.TarError("Corrupt archive")

        with pytest.raises(DataProcessingError) as exc_info:
            extract_csv_from_archive(archive_path, output_dir)

        assert "Error reading archive" in str(exc_info.value)

    @patch("tarfile.open")
    def test_extract_csv_from_archive_os_error(self, mock_tarfile_open, tmp_path):
        """Test handling OS error."""
        archive_path = tmp_path / "test.tar.gz"
        archive_path.touch()
        output_dir = tmp_path / "output"

        mock_tarfile_open.side_effect = OSError("Permission denied")

        with pytest.raises(DataProcessingError) as exc_info:
            extract_csv_from_archive(archive_path, output_dir)

        assert "OS error" in str(exc_info.value)

    @patch("tarfile.open")
    def test_extract_csv_from_archive_creates_output_dir(self, mock_tarfile_open, tmp_path):
        """Test that output directory is created."""
        archive_path = tmp_path / "test.tar.gz"
        archive_path.touch()
        output_dir = tmp_path / "new_output"

        # Mock tar file with no matching members
        mock_tar = MagicMock()
        mock_tar.getmembers.return_value = []
        mock_tarfile_open.return_value.__enter__.return_value = mock_tar

        extract_csv_from_archive(archive_path, output_dir)

        assert output_dir.exists()

    @patch("tarfile.open")
    @patch("shutil.copy2")
    def test_extract_csv_from_archive_handles_burnin(self, mock_copy, mock_tarfile_open, tmp_path):
        """Test extracting from burnin archives."""
        archive_path = tmp_path / "test.tar.gz"
        archive_path.touch()
        output_dir = tmp_path / "output"

        # Mock outer tar file with burnin archive
        mock_outer_tar = MagicMock()
        mock_member = MagicMock()
        mock_member.name = "tt_funtest_ubb_1/ft_burnin_test.tar.gz"
        mock_outer_tar.getmembers.return_value = [mock_member]

        # Mock inner tar file with CSV from burnin directory
        mock_inner_tar = MagicMock()
        mock_csv_member = MagicMock()
        mock_csv_member.name = "ft_burnin/data_test_results.csv"
        mock_inner_tar.getmembers.return_value = [mock_csv_member]

        mock_tarfile_open.side_effect = [
            MagicMock(__enter__=lambda self: mock_outer_tar, __exit__=lambda *args: None),
            MagicMock(__enter__=lambda self: mock_inner_tar, __exit__=lambda *args: None),
        ]

        result = extract_csv_from_archive(archive_path, output_dir)

        assert result.success is True
        assert result.total_files == 1
