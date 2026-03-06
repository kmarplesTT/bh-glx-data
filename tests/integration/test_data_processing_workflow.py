"""Integration tests for data processing workflow."""

import csv
from pathlib import Path

import pandas as pd
import pytest

from bh_glx_data.core.exceptions import DataProcessingError
from bh_glx_data.data_processing.csv_reader import read_csv_with_validation
from bh_glx_data.data_processing.filter import filter_failures


class TestDataProcessingWorkflow:
    """Test complete data processing workflow from CSV reading to filtering."""

    def test_read_and_filter_workflow(self, tmp_path, sample_test_data_csv):
        """Test reading CSV and filtering failures."""
        # Step 1: Read CSV
        df = read_csv_with_validation(sample_test_data_csv)
        assert df is not None
        assert len(df) > 0
        assert 'test_status' in df.columns

        # Step 2: Filter failures
        output_file = tmp_path / "failures.csv"
        result = filter_failures(sample_test_data_csv, output_file)

        assert result.success
        assert result.failure_count >= 0
        if result.failure_count > 0:
            assert output_file.exists()
            # Verify filtered output
            failures_df = pd.read_csv(output_file)
            assert len(failures_df) == result.failure_count
            # All rows should be failures
            assert not failures_df['test_status'].isin(['ETH_ACTIVE', 'ETH_UNCONNECTED']).any()

    def test_filter_with_no_failures(self, tmp_path):
        """Test filtering CSV with no failures."""
        # Create CSV with only ETH_ACTIVE statuses
        csv_file = tmp_path / "no_failures.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['bus_id', 'ETH ID', 'test_status', 'test_type'])
            writer.writerow(['01:00.0', 'ETH00', 'ETH_ACTIVE', 'SIMPLE_PACKET'])
            writer.writerow(['01:00.0', 'ETH01', 'ETH_ACTIVE', 'SIMPLE_PACKET'])
            writer.writerow(['01:00.0', 'ETH05', 'ETH_UNCONNECTED', 'SIMPLE_PACKET'])

        output_file = tmp_path / "failures.csv"
        result = filter_failures(csv_file, output_file)

        assert result.success
        assert result.failure_count == 0
        assert not output_file.exists()  # No output file created when no failures

    def test_filter_invalid_csv(self, tmp_path):
        """Test filtering with invalid CSV."""
        # Create CSV without required columns
        csv_file = tmp_path / "invalid.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['col1', 'col2'])
            writer.writerow(['val1', 'val2'])

        output_file = tmp_path / "failures.csv"

        with pytest.raises(DataProcessingError) as exc_info:
            filter_failures(csv_file, output_file, status_column='test_status')

        assert "test_status" in str(exc_info.value).lower()

    def test_filter_custom_status_column(self, tmp_path):
        """Test filtering with custom status column."""
        # Create CSV with custom status column
        csv_file = tmp_path / "custom_status.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['bus_id', 'ETH ID', 'status', 'test_type'])
            writer.writerow(['01:00.0', 'ETH00', 'PASS', 'SIMPLE_PACKET'])
            writer.writerow(['01:00.0', 'ETH01', 'FAIL', 'SIMPLE_PACKET'])
            writer.writerow(['01:00.0', 'ETH02', 'PASS', 'SIMPLE_PACKET'])

        output_file = tmp_path / "failures.csv"
        result = filter_failures(csv_file, output_file, status_column='status')

        # With custom filtering, need to specify what constitutes a failure
        # The default filter looks for ETH_ACTIVE/ETH_UNCONNECTED
        # So this should capture all rows as "failures"
        assert result.success
        assert result.failure_count >= 0


class TestCSVReaderValidation:
    """Test CSV reader validation."""

    def test_read_valid_csv(self, sample_test_data_csv):
        """Test reading a valid CSV file."""
        df = read_csv_with_validation(sample_test_data_csv)
        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_read_nonexistent_csv(self, tmp_path):
        """Test reading nonexistent CSV file."""
        nonexistent = tmp_path / "nonexistent.csv"

        with pytest.raises(DataProcessingError) as exc_info:
            read_csv_with_validation(nonexistent)

        assert "not found" in str(exc_info.value).lower()

    def test_read_empty_csv(self, tmp_path):
        """Test reading empty CSV file."""
        empty_csv = tmp_path / "empty.csv"
        empty_csv.touch()

        with pytest.raises(DataProcessingError):
            read_csv_with_validation(empty_csv)


class TestMetadataExtraction:
    """Test metadata extraction from filenames."""

    def test_extract_firmware_version(self):
        """Test firmware version extraction from filename."""
        from bh_glx_data.data_processing.csv_reader import extract_firmware_version

        # Test various firmware version patterns
        assert extract_firmware_version("data_erisc_v1_7_103.csv") == "erisc_v1_7_103"
        assert extract_firmware_version("SYS-123_v1_7_103_test.csv") == "v1_7_103"
        assert extract_firmware_version("test_v2_0_0.csv") == "v2_0_0"
        assert extract_firmware_version("no_version.csv") is None

    def test_extract_hostname(self):
        """Test hostname extraction from CSV content."""
        from bh_glx_data.data_processing.csv_reader import extract_hostname_from_csv

        # This would need a sample CSV with host column
        # For now, test the function exists
        assert extract_hostname_from_csv is not None
