"""Integration tests for end-to-end system analysis workflow."""

import csv
from pathlib import Path

import pytest

from bh_glx_data.system_analysis.database import DatabaseManager
from bh_glx_data.system_analysis.export import ExcelExporter, ExportFilters
from bh_glx_data.system_analysis.ingestion import CSVIngester
from bh_glx_data.system_analysis.interactive import AnalysisShell
from bh_glx_data.system_analysis.query_engine import LaneSelector, QueryEngine
from bh_glx_data.system_analysis.visualization import HeatMapRenderer, TableRenderer


@pytest.fixture
def sample_csv_dir(tmp_path):
    """Create sample CSV files for testing."""
    csv_dir = tmp_path / "csv_data"
    csv_dir.mkdir()

    # Create sample CSV file 1
    csv_file1 = csv_dir / "prbs_test_system1.csv"
    with open(csv_file1, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "host",
                "bus_id",
                "eth_id",
                "date",
                "test_status",
                "train_speed",
                "acc_ber_lane0",
                "acc_ber_lane1",
                "acc_ber_lane2",
                "acc_ber_lane3",
                "acc_ber_lane4",
                "acc_ber_lane5",
                "acc_ber_lane6",
                "acc_ber_lane7",
                "acc_time_elapsed",
            ],
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "host": "bh-glx-c02u02",
                    "bus_id": "01:00.0",
                    "eth_id": "ETH00",
                    "date": "2024-01-01",
                    "test_status": "PASS",
                    "train_speed": 100,
                    "acc_ber_lane0": 1.2e-12,
                    "acc_ber_lane1": 1.5e-12,
                    "acc_ber_lane2": 1.8e-12,
                    "acc_ber_lane3": 2.1e-12,
                    "acc_ber_lane4": "",
                    "acc_ber_lane5": "",
                    "acc_ber_lane6": "",
                    "acc_ber_lane7": "",
                    "acc_time_elapsed": 10.5,
                },
                {
                    "host": "bh-glx-c02u02",
                    "bus_id": "01:00.0",
                    "eth_id": "ETH01",
                    "date": "2024-01-01",
                    "test_status": "BER_THRESHOLD_EXCEEDED",
                    "train_speed": 100,
                    "acc_ber_lane0": 1.2e-10,
                    "acc_ber_lane1": 1.5e-10,
                    "acc_ber_lane2": 1.8e-10,
                    "acc_ber_lane3": 2.1e-10,
                    "acc_ber_lane4": "",
                    "acc_ber_lane5": "",
                    "acc_ber_lane6": "",
                    "acc_ber_lane7": "",
                    "acc_time_elapsed": 12.3,
                },
                {
                    "host": "bh-glx-c02u02",
                    "bus_id": "02:00.0",
                    "eth_id": "ETH00",
                    "date": "2024-01-01",
                    "test_status": "TRAINING_FAIL",
                    "train_speed": 200,
                    "acc_ber_lane0": "",
                    "acc_ber_lane1": "",
                    "acc_ber_lane2": "",
                    "acc_ber_lane3": "",
                    "acc_ber_lane4": "",
                    "acc_ber_lane5": "",
                    "acc_ber_lane6": "",
                    "acc_ber_lane7": "",
                    "acc_time_elapsed": 5.2,
                },
            ]
        )

    # Create sample CSV file 2
    csv_file2 = csv_dir / "prbs_test_system2.csv"
    with open(csv_file2, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "host",
                "bus_id",
                "eth_id",
                "date",
                "test_status",
                "train_speed",
                "acc_ber_lane0",
                "acc_ber_lane1",
                "acc_ber_lane2",
                "acc_ber_lane3",
                "acc_ber_lane4",
                "acc_ber_lane5",
                "acc_ber_lane6",
                "acc_ber_lane7",
                "acc_time_elapsed",
            ],
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "host": "bh-glx-c03u02",
                    "bus_id": "01:00.0",
                    "eth_id": "ETH07",
                    "date": "2024-01-02",
                    "test_status": "PASS",
                    "train_speed": 200,
                    "acc_ber_lane0": 2.2e-12,
                    "acc_ber_lane1": 2.5e-12,
                    "acc_ber_lane2": 2.8e-12,
                    "acc_ber_lane3": 3.1e-12,
                    "acc_ber_lane4": "",
                    "acc_ber_lane5": "",
                    "acc_ber_lane6": "",
                    "acc_ber_lane7": "",
                    "acc_time_elapsed": 15.7,
                },
            ]
        )

    return csv_dir


@pytest.fixture
def test_db(tmp_path):
    """Create a test database."""
    db_path = tmp_path / "test_analysis.db"
    db = DatabaseManager(db_path)
    db.initialize_schema()
    yield db
    db.close()


class TestEndToEndWorkflow:
    """Test complete workflow from ingestion to visualization."""

    def test_ingest_and_query(self, test_db, sample_csv_dir):
        """Test ingesting CSV data and querying it."""
        # Ingest data
        ingester = CSVIngester(test_db)
        result = ingester.ingest_directory(sample_csv_dir)

        assert result.files_processed == 2
        assert result.rows_ingested == 4
        assert result.rows_filtered == 0

        # Query all data
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("all")
        stats = engine.query_ber_statistics(selector, exclude_training_failures=True)

        assert stats.num_tests > 0
        assert stats.num_systems == 2

    def test_query_specific_port(self, test_db, sample_csv_dir):
        """Test querying specific port."""
        # Ingest data
        ingester = CSVIngester(test_db)
        ingester.ingest_directory(sample_csv_dir)

        # Query specific port
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("01:00.0/ETH00")
        stats = engine.query_ber_statistics(selector)

        # Should have data for ETH00 on bus 01:00.0
        assert len(stats.lane_stats) > 0

    def test_query_with_speed_filter(self, test_db, sample_csv_dir):
        """Test querying with speed filter."""
        # Ingest data
        ingester = CSVIngester(test_db)
        ingester.ingest_directory(sample_csv_dir)

        # Query with speed filter
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("all")
        stats = engine.query_ber_statistics(selector, train_speeds=[200])

        assert 200 in stats.train_speeds
        assert 100 not in stats.train_speeds

    def test_threshold_exceeded_query(self, test_db, sample_csv_dir):
        """Test BER threshold exceeded query."""
        # Ingest data
        ingester = CSVIngester(test_db)
        ingester.ingest_directory(sample_csv_dir)

        # Query threshold exceeded
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("all")
        result = engine.query_ber_threshold_exceeded(selector)

        # Should have at least one threshold exceeded
        assert result.num_tests > 0
        assert len(result.lane_counts) > 0

    def test_training_failures_query(self, test_db, sample_csv_dir):
        """Test training failures query."""
        # Ingest data
        ingester = CSVIngester(test_db)
        ingester.ingest_directory(sample_csv_dir)

        # Query training failures
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("all")
        result = engine.query_training_failures(selector)

        # Should have one training failure
        assert result.num_tests > 0

    def test_custom_threshold_query(self, test_db, sample_csv_dir):
        """Test custom BER threshold query."""
        # Ingest data
        ingester = CSVIngester(test_db)
        ingester.ingest_directory(sample_csv_dir)

        # Query custom threshold
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("all")
        result = engine.query_custom_ber_threshold(selector, threshold=1e-11)

        # Should have lanes exceeding 1e-11
        assert len(result.lane_counts) > 0

    def test_table_rendering(self, test_db, sample_csv_dir):
        """Test rendering query results as table."""
        # Ingest data
        ingester = CSVIngester(test_db)
        ingester.ingest_directory(sample_csv_dir)

        # Query and render
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("01:00.0/ETH00")
        stats = engine.query_ber_statistics(selector)

        renderer = TableRenderer()
        output = renderer.render_ber_statistics(stats)

        assert isinstance(output, str)
        assert len(output) > 0
        assert "Lane" in output

    def test_heatmap_rendering(self, test_db, sample_csv_dir):
        """Test rendering query results as heatmap."""
        # Ingest data
        ingester = CSVIngester(test_db)
        ingester.ingest_directory(sample_csv_dir)

        # Query and render
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("all")
        result = engine.query_training_failures(selector)

        renderer = HeatMapRenderer()
        output = renderer.render_count_heatmap(result)

        assert isinstance(output, str)
        assert len(output) > 0

    def test_excel_export(self, test_db, sample_csv_dir, tmp_path):
        """Test exporting database to Excel."""
        # Ingest data
        ingester = CSVIngester(test_db)
        ingester.ingest_directory(sample_csv_dir)

        # Export to Excel
        exporter = ExcelExporter(test_db)
        output_path = tmp_path / "export.xlsx"
        result = exporter.export_full_database(output_path)

        assert result.output_path.exists()
        assert result.rows_exported > 0
        assert result.sheets_created > 0

    def test_excel_export_with_filters(self, test_db, sample_csv_dir, tmp_path):
        """Test exporting database with filters."""
        # Ingest data
        ingester = CSVIngester(test_db)
        ingester.ingest_directory(sample_csv_dir)

        # Export with filters
        exporter = ExcelExporter(test_db)
        output_path = tmp_path / "filtered_export.xlsx"
        filters = ExportFilters(hosts=["bh-glx-c02u02"], train_speeds=[100])
        result = exporter.export_full_database(output_path, filters=filters)

        assert result.output_path.exists()
        assert result.rows_exported > 0

    def test_database_stats(self, test_db, sample_csv_dir):
        """Test getting database statistics."""
        # Ingest data
        ingester = CSVIngester(test_db)
        ingester.ingest_directory(sample_csv_dir)

        # Get stats
        stats = test_db.get_database_stats()

        assert stats.total_tests == 4
        assert stats.unique_hosts == 2
        assert len(stats.unique_speeds) == 2
        assert "PASS" in stats.status_breakdown
        assert "BER_THRESHOLD_EXCEEDED" in stats.status_breakdown
        assert "TRAINING_FAIL" in stats.status_breakdown

    def test_multiple_ingestions(self, test_db, sample_csv_dir):
        """Test multiple ingestion runs."""
        ingester = CSVIngester(test_db)

        # First ingestion
        result1 = ingester.ingest_directory(sample_csv_dir)
        assert result1.files_processed == 2

        # Second ingestion (should add duplicate data)
        result2 = ingester.ingest_directory(sample_csv_dir)
        assert result2.files_processed == 2

        # Total should be double
        stats = test_db.get_database_stats()
        assert stats.total_tests == 8
        assert stats.total_ingestions == 2


class TestInteractiveShell:
    """Test interactive shell functionality."""

    def test_shell_initialization(self, test_db, sample_csv_dir):
        """Test shell can be initialized."""
        ingester = CSVIngester(test_db)
        ingester.ingest_directory(sample_csv_dir)

        engine = QueryEngine(test_db)
        exporter = ExcelExporter(test_db)
        shell = AnalysisShell(engine, exporter)

        assert shell.query_engine is not None
        assert shell.exporter is not None
        assert shell.last_result is None
        assert len(shell.history) == 0


class TestErrorHandling:
    """Test error handling in integration scenarios."""

    def test_ingest_nonexistent_directory(self, test_db, tmp_path):
        """Test ingesting from nonexistent directory."""
        from bh_glx_data.core.exceptions import IngestionError

        ingester = CSVIngester(test_db)
        nonexistent_dir = tmp_path / "nonexistent"

        # Should raise IngestionError
        with pytest.raises(IngestionError):
            ingester.ingest_directory(nonexistent_dir)

    def test_query_empty_database(self, test_db):
        """Test querying empty database."""
        engine = QueryEngine(test_db)
        selector = LaneSelector.from_spec("all")

        # Should return empty results, not error
        stats = engine.query_ber_statistics(selector)
        assert stats.num_tests == 0
        assert len(stats.lane_stats) == 0

    def test_export_empty_database(self, test_db, tmp_path):
        """Test exporting empty database."""
        exporter = ExcelExporter(test_db)
        output_path = tmp_path / "empty_export.xlsx"

        # Should create file with empty data
        result = exporter.export_full_database(output_path)
        assert result.output_path.exists()
