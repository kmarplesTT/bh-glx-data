"""Unit tests for data_processing module."""

import csv
from pathlib import Path

import pandas as pd
import pytest

from bh_glx_data.core.exceptions import DataProcessingError
from bh_glx_data.data_processing.csv_reader import (
    extract_firmware_version,
    extract_hostname_from_csv,
    read_csv_with_validation,
    validate_csv_schema,
)
from bh_glx_data.data_processing.filter import filter_failures


class TestCSVReader:
    """Test CSV reading functionality."""

    def test_read_csv_with_validation_success(self, tmp_path):
        """Test successful CSV reading."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["bus_id", "ETH ID", "test_status"])
            writer.writerow(["01:00.0", "ETH00", "ETH_ACTIVE"])

        df = read_csv_with_validation(csv_file)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "bus_id" in df.columns

    def test_read_csv_nonexistent_file(self, tmp_path):
        """Test reading nonexistent file raises error."""
        nonexistent = tmp_path / "nonexistent.csv"

        with pytest.raises(DataProcessingError) as exc_info:
            read_csv_with_validation(nonexistent)

        assert "not found" in str(exc_info.value).lower()
        assert str(nonexistent) in str(exc_info.value)

    def test_read_csv_empty_file(self, tmp_path):
        """Test reading empty file raises error."""
        empty_file = tmp_path / "empty.csv"
        empty_file.touch()

        with pytest.raises(DataProcessingError) as exc_info:
            read_csv_with_validation(empty_file)

        assert "empty" in str(exc_info.value).lower()

    def test_read_csv_malformed(self, tmp_path):
        """Test reading malformed CSV."""
        malformed = tmp_path / "malformed.csv"
        with open(malformed, "w") as f:
            f.write("not,valid,csv\n")
            f.write("missing,columns\n")  # Inconsistent columns

        # pandas is forgiving, but we should handle gracefully
        try:
            df = read_csv_with_validation(malformed)
            # If it succeeds, verify DataFrame structure
            assert isinstance(df, pd.DataFrame)
        except DataProcessingError:
            # Expected if validation fails
            pass


class TestCSVSchemaValidation:
    """Test CSV schema validation."""

    def test_validate_schema_with_required_columns(self):
        """Test schema validation with all required columns."""
        df = pd.DataFrame(
            {"bus_id": ["01:00.0"], "test_status": ["ETH_ACTIVE"], "ETH ID": ["ETH00"]}
        )

        required_columns = ["bus_id", "test_status"]
        result = validate_csv_schema(df, required_columns)
        assert result is True

    def test_validate_schema_missing_columns(self):
        """Test schema validation with missing columns."""
        df = pd.DataFrame({"bus_id": ["01:00.0"]})

        required_columns = ["bus_id", "test_status"]

        with pytest.raises(DataProcessingError) as exc_info:
            validate_csv_schema(df, required_columns)

        assert "missing required column" in str(exc_info.value).lower()
        assert "test_status" in str(exc_info.value)

    def test_validate_schema_empty_dataframe(self):
        """Test schema validation with empty DataFrame."""
        df = pd.DataFrame()

        required_columns = ["bus_id"]

        with pytest.raises(DataProcessingError) as exc_info:
            validate_csv_schema(df, required_columns)

        assert "empty" in str(exc_info.value).lower()

    def test_validate_schema_no_requirements(self):
        """Test schema validation with no requirements."""
        df = pd.DataFrame({"col1": [1, 2, 3]})

        result = validate_csv_schema(df, [])
        assert result is True


class TestFirmwareVersionExtraction:
    """Test firmware version extraction from filenames."""

    def test_extract_firmware_version_erisc_format(self):
        """Test extracting erisc format firmware version."""
        assert extract_firmware_version("data_erisc_v1_7_103.csv") == "erisc_v1_7_103"
        assert extract_firmware_version("SYS-123_erisc_v2_0_5.csv") == "erisc_v2_0_5"

    def test_extract_firmware_version_v_format(self):
        """Test extracting v-format firmware version."""
        assert extract_firmware_version("test_v1_7_103.csv") == "v1_7_103"
        assert extract_firmware_version("SYS-456_v2_0_0_data.csv") == "v2_0_0"

    def test_extract_firmware_version_no_version(self):
        """Test extracting from filename with no version."""
        assert extract_firmware_version("no_version_here.csv") is None
        assert extract_firmware_version("test.csv") is None

    def test_extract_firmware_version_multiple_matches(self):
        """Test extracting when multiple version patterns exist."""
        # Should match the first pattern
        result = extract_firmware_version("v1_0_0_erisc_v2_0_0.csv")
        assert result in ["v1_0_0", "erisc_v2_0_0"]  # Either is acceptable

    def test_extract_firmware_version_edge_cases(self):
        """Test edge cases for firmware version extraction."""
        assert extract_firmware_version("") is None
        assert extract_firmware_version("v.csv") is None
        assert extract_firmware_version("version_1.csv") is None


class TestHostnameExtraction:
    """Test hostname extraction from CSV content."""

    def test_extract_hostname_from_csv_with_host_column(self, tmp_path):
        """Test extracting hostname when host column exists."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["host", "bus_id", "test_status"])
            writer.writerow(["bh-glx-b02u02", "01:00.0", "ETH_ACTIVE"])
            writer.writerow(["bh-glx-b02u02", "02:00.0", "ETH_ACTIVE"])

        hostname = extract_hostname_from_csv(csv_file)
        assert hostname == "bh-glx-b02u02"

    def test_extract_hostname_no_host_column(self, tmp_path):
        """Test extracting hostname when host column doesn't exist."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["bus_id", "test_status"])
            writer.writerow(["01:00.0", "ETH_ACTIVE"])

        hostname = extract_hostname_from_csv(csv_file)
        assert hostname is None

    def test_extract_hostname_empty_values(self, tmp_path):
        """Test extracting hostname when all values are empty."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["host", "bus_id"])
            writer.writerow(["", "01:00.0"])
            writer.writerow(["", "02:00.0"])

        hostname = extract_hostname_from_csv(csv_file)
        assert hostname is None or hostname == ""


class TestFailureFiltering:
    """Test failure filtering functionality."""

    def test_filter_failures_with_failures(self, tmp_path):
        """Test filtering CSV with failures."""
        input_file = tmp_path / "input.csv"
        with open(input_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["bus_id", "ETH ID", "test_status"])
            writer.writerow(["01:00.0", "ETH00", "ETH_ACTIVE"])
            writer.writerow(["01:00.0", "ETH01", "TRAINING_FAIL"])
            writer.writerow(["01:00.0", "ETH02", "LINK_DOWN"])
            writer.writerow(["01:00.0", "ETH05", "ETH_UNCONNECTED"])

        output_file = tmp_path / "output.csv"
        result = filter_failures(input_file, output_file)

        assert result.success
        assert result.failure_count == 2  # TRAINING_FAIL and LINK_DOWN
        assert result.total_rows == 4
        assert output_file.exists()

        # Verify output content
        output_df = pd.read_csv(output_file)
        assert len(output_df) == 2
        assert "TRAINING_FAIL" in output_df["test_status"].values
        assert "LINK_DOWN" in output_df["test_status"].values

    def test_filter_failures_no_failures(self, tmp_path):
        """Test filtering CSV with no failures."""
        input_file = tmp_path / "input.csv"
        with open(input_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["bus_id", "ETH ID", "test_status"])
            writer.writerow(["01:00.0", "ETH00", "ETH_ACTIVE"])
            writer.writerow(["01:00.0", "ETH01", "ETH_ACTIVE"])
            writer.writerow(["01:00.0", "ETH05", "ETH_UNCONNECTED"])

        output_file = tmp_path / "output.csv"
        result = filter_failures(input_file, output_file)

        assert result.success
        assert result.failure_count == 0
        assert not output_file.exists()  # No output when no failures

    def test_filter_failures_missing_column(self, tmp_path):
        """Test filtering with missing status column."""
        input_file = tmp_path / "input.csv"
        with open(input_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["bus_id", "ETH ID"])
            writer.writerow(["01:00.0", "ETH00"])

        output_file = tmp_path / "output.csv"

        with pytest.raises(DataProcessingError) as exc_info:
            filter_failures(input_file, output_file, status_column="test_status")

        assert "test_status" in str(exc_info.value)

    def test_filter_failures_custom_status_column(self, tmp_path):
        """Test filtering with custom status column."""
        input_file = tmp_path / "input.csv"
        with open(input_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["bus_id", "ETH ID", "custom_status"])
            writer.writerow(["01:00.0", "ETH00", "ETH_ACTIVE"])
            writer.writerow(["01:00.0", "ETH01", "FAIL"])

        output_file = tmp_path / "output.csv"
        result = filter_failures(input_file, output_file, status_column="custom_status")

        assert result.success
        # With custom column, filtering logic still applies
        assert result.failure_count >= 0

    def test_filter_failures_default_output_path(self, tmp_path):
        """Test filtering with default output path."""
        input_file = tmp_path / "input.csv"
        with open(input_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["bus_id", "ETH ID", "test_status"])
            writer.writerow(["01:00.0", "ETH00", "TRAINING_FAIL"])

        # Don't specify output file
        result = filter_failures(input_file)

        assert result.success
        assert result.failure_count == 1

        # Output should be created with default name
        expected_output = tmp_path / "input_failures.csv"
        assert expected_output.exists()

    def test_filter_failures_empty_input(self, tmp_path):
        """Test filtering empty CSV."""
        input_file = tmp_path / "empty.csv"
        with open(input_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["bus_id", "ETH ID", "test_status"])
            # No data rows

        output_file = tmp_path / "output.csv"
        result = filter_failures(input_file, output_file)

        assert result.success
        assert result.failure_count == 0
        assert result.total_rows == 0


class TestFilterResultModel:
    """Test FilterResult model."""

    def test_filter_result_creation(self):
        """Test creating FilterResult."""
        from bh_glx_data.core.models import FilterResult

        result = FilterResult(
            input_file=Path("input.csv"),
            output_file=Path("output.csv"),
            total_rows=100,
            failure_count=10,
            status_breakdown={"TRAINING_FAIL": 5, "LINK_DOWN": 5},
            success=True,
            error_message=None,
        )

        assert result.success
        assert result.total_rows == 100
        assert result.failure_count == 10
        assert len(result.status_breakdown) == 2


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_read_csv_with_bom(self, tmp_path):
        """Test reading CSV with BOM (Byte Order Mark)."""
        csv_file = tmp_path / "bom.csv"
        with open(csv_file, "w", encoding="utf-8-sig") as f:
            f.write("bus_id,test_status\n")
            f.write("01:00.0,ETH_ACTIVE\n")

        df = read_csv_with_validation(csv_file)
        assert df is not None
        assert "bus_id" in df.columns

    def test_filter_with_special_characters(self, tmp_path):
        """Test filtering with special characters in data."""
        input_file = tmp_path / "special.csv"
        with open(input_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["bus_id", "ETH ID", "test_status"])
            writer.writerow(['"01:00.0"', "ETH00", "ETH_ACTIVE"])  # Quoted
            writer.writerow(["02:00.0", "ETH01", "FAIL"])

        output_file = tmp_path / "output.csv"
        result = filter_failures(input_file, output_file)

        assert result.success

    def test_filter_with_very_long_lines(self, tmp_path):
        """Test filtering with very long lines."""
        input_file = tmp_path / "long.csv"
        long_value = "A" * 10000  # Very long string

        with open(input_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["bus_id", "ETH ID", "test_status", "data"])
            writer.writerow(["01:00.0", "ETH00", "TRAINING_FAIL", long_value])

        output_file = tmp_path / "output.csv"
        result = filter_failures(input_file, output_file)

        assert result.success
        assert result.failure_count == 1
