"""CSV ingestion module for system analysis.

This module provides streaming CSV ingestion with filtering and batch insertion
into the database. It excludes unnecessary columns and filters test data by status.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd
from tqdm import tqdm

from bh_glx_data.core.exceptions import IngestionError
from bh_glx_data.system_analysis.database import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class TestRecord:
    """Represents a single PRBS test record.

    Attributes:
        host: System hostname
        bus_id: PCIe bus ID
        eth_id: Ethernet port identifier
        date: Test date/timestamp
        test_status: Test status (PASS, BER_THRESHOLD_EXCEEDED, TRAINING_FAIL)
        train_speed: Training speed in Gbps
        acc_ber_lanes: List of BER values for 8 lanes
        acc_lane_error_cnt: JSON string of error counts
        acc_lane_error_cnt_overflow: JSON string of overflow counts
        acc_time_elapsed: Elapsed time in seconds
        interface_id: Optional interface identifier
        train_type_requested: Optional requested train type
        train_mode: Optional training mode
        port_type: Optional port type
        ber_threshold_used: Optional BER threshold value
        interface_type_used: Optional interface type
        source_file: Source CSV filename
        ingestion_timestamp: When record was ingested
    """

    host: str
    bus_id: str
    eth_id: str
    date: str
    test_status: str
    train_speed: int
    acc_ber_lanes: List[Optional[float]]
    source_file: str
    ingestion_timestamp: str
    interface_id: Optional[str] = None
    train_type_requested: Optional[str] = None
    train_mode: Optional[str] = None
    port_type: Optional[str] = None
    acc_lane_error_cnt: Optional[str] = None
    acc_lane_error_cnt_overflow: Optional[str] = None
    acc_time_elapsed: Optional[float] = None
    ber_threshold_used: Optional[float] = None
    interface_type_used: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert TestRecord to dictionary for database insertion.

        Returns:
            Dictionary with column names as keys
        """
        return {
            "host": self.host,
            "bus_id": self.bus_id,
            "eth_id": self.eth_id,
            "interface_id": self.interface_id,
            "date": self.date,
            "test_status": self.test_status,
            "train_speed": self.train_speed,
            "train_type_requested": self.train_type_requested,
            "train_mode": self.train_mode,
            "port_type": self.port_type,
            "acc_ber_lane0": self.acc_ber_lanes[0] if len(self.acc_ber_lanes) > 0 else None,
            "acc_ber_lane1": self.acc_ber_lanes[1] if len(self.acc_ber_lanes) > 1 else None,
            "acc_ber_lane2": self.acc_ber_lanes[2] if len(self.acc_ber_lanes) > 2 else None,
            "acc_ber_lane3": self.acc_ber_lanes[3] if len(self.acc_ber_lanes) > 3 else None,
            "acc_ber_lane4": self.acc_ber_lanes[4] if len(self.acc_ber_lanes) > 4 else None,
            "acc_ber_lane5": self.acc_ber_lanes[5] if len(self.acc_ber_lanes) > 5 else None,
            "acc_ber_lane6": self.acc_ber_lanes[6] if len(self.acc_ber_lanes) > 6 else None,
            "acc_ber_lane7": self.acc_ber_lanes[7] if len(self.acc_ber_lanes) > 7 else None,
            "acc_lane_error_cnt": self.acc_lane_error_cnt,
            "acc_lane_error_cnt_overflow": self.acc_lane_error_cnt_overflow,
            "acc_time_elapsed": self.acc_time_elapsed,
            "ber_threshold_used": self.ber_threshold_used,
            "interface_type_used": self.interface_type_used,
            "source_file": self.source_file,
            "ingestion_timestamp": self.ingestion_timestamp,
        }


@dataclass
class IngestionResult:
    """Result of an ingestion run.

    Attributes:
        files_processed: Number of CSV files processed
        rows_ingested: Number of rows inserted into database
        rows_filtered: Number of rows filtered out by status
        duration: Duration in seconds
        errors: List of error messages encountered
        success: Whether ingestion completed successfully
    """

    files_processed: int
    rows_ingested: int
    rows_filtered: int
    duration: float
    errors: List[str] = field(default_factory=list)
    success: bool = True


class CSVIngester:
    """Handles CSV ingestion with streaming and filtering.

    This class processes CSV files in chunks to minimize memory usage,
    filters rows by test status, excludes unnecessary columns, and
    batch inserts data into the database.

    Attributes:
        db: DatabaseManager instance
        chunk_size: Number of rows to process per chunk
        excluded_columns: List of column names to exclude from ingestion
    """

    # Columns to exclude (44 columns from the spec)
    EXCLUDED_COLUMNS = [
        "interface_type_requested",
        "prbs_polynomial_type",
        "loopback_mode",
        "fec_type",
        "data_pkt_size_bytes",
        "num_lanes",
        "num_data_bytes_per_lane",
        "num_acc_bits_per_lane",
        "num_data_pkts_per_lane",
        "num_data_pkts_per_sec",
        "acc_lane_ber_cnt",
        "acc_lane_ber_cnt_overflow",
        "lock_cdr_lane",
        "lock_sig_detect_lane",
        "lock_block_lock_lane",
        "lock_am_lock_lane",
        "lock_pcs_status_lane",
        "ber_threshold_exceeded_lane",
        "interface_state",
        "train_state",
        "train_complete",
        "train_done_sent",
        "train_failed",
        "train_tx_preset_index",
        "train_tx_ffe_pre2",
        "train_tx_ffe_pre",
        "train_tx_ffe_main",
        "train_tx_ffe_post",
        "train_rx_preset_index",
        "train_rx_ffe_tap_values",
        "tune_tx_ffe_step",
        "tune_tx_ffe_pre2",
        "tune_tx_ffe_pre",
        "tune_tx_ffe_main",
        "tune_tx_ffe_post",
        "tune_rx_ffe_step",
        "tune_rx_ffe_tap_values",
        "tx_param_values_initial",
        "tx_param_values_current",
        "tx_param_values_best",
        "rx_param_values_initial",
        "rx_param_values_current",
        "rx_param_values_best",
        "chip_type",
    ]

    # Default status filter
    DEFAULT_STATUS_FILTER = ["PASS", "BER_THRESHOLD_EXCEEDED", "TRAINING_FAIL"]

    def __init__(self, db_manager: DatabaseManager, chunk_size: int = 1000):
        """Initialize CSV ingester.

        Args:
            db_manager: DatabaseManager instance
            chunk_size: Number of rows to process per chunk
        """
        self.db = db_manager
        self.chunk_size = chunk_size
        self.excluded_columns = self.EXCLUDED_COLUMNS

    def ingest_directory(
        self,
        input_dir: Path,
        status_filter: Optional[List[str]] = None,
    ) -> IngestionResult:
        """Ingest all CSV files from directory.

        Args:
            input_dir: Directory containing CSV files
            status_filter: List of status values to include (None = use default)

        Returns:
            IngestionResult with statistics

        Raises:
            IngestionError: If ingestion fails
        """
        if status_filter is None:
            status_filter = self.DEFAULT_STATUS_FILTER

        input_path = Path(input_dir)
        if not input_path.exists():
            raise IngestionError(f"Input directory does not exist: {input_path}")

        if not input_path.is_dir():
            raise IngestionError(f"Input path is not a directory: {input_path}")

        # Find all CSV files
        csv_files = list(input_path.glob("*.csv"))
        if not csv_files:
            logger.warning(f"No CSV files found in {input_path}")
            return IngestionResult(
                files_processed=0,
                rows_ingested=0,
                rows_filtered=0,
                duration=0.0,
                errors=[],
                success=True,
            )

        start_time = time.time()
        total_rows_ingested = 0
        total_rows_filtered = 0
        errors = []

        logger.info(f"Starting ingestion of {len(csv_files)} CSV files from {input_path}")

        # Process each CSV file with progress bar
        for csv_file in tqdm(csv_files, desc="Ingesting CSV files", unit="file"):
            try:
                rows_ingested, rows_filtered = self._ingest_file(csv_file, status_filter)
                total_rows_ingested += rows_ingested
                total_rows_filtered += rows_filtered

            except Exception as e:
                error_msg = f"Failed to ingest {csv_file.name}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        duration = time.time() - start_time

        # Record metadata
        try:
            self.db.insert_ingestion_metadata(
                source_directory=str(input_path),
                files_processed=len(csv_files) - len(errors),
                rows_ingested=total_rows_ingested,
                rows_filtered=total_rows_filtered,
                duration_seconds=duration,
            )
        except Exception as e:
            logger.error(f"Failed to record ingestion metadata: {e}")

        logger.info(
            f"Ingestion complete: {total_rows_ingested} rows ingested, "
            f"{total_rows_filtered} rows filtered, {len(errors)} errors"
        )

        return IngestionResult(
            files_processed=len(csv_files) - len(errors),
            rows_ingested=total_rows_ingested,
            rows_filtered=total_rows_filtered,
            duration=duration,
            errors=errors,
            success=len(errors) == 0,
        )

    def _ingest_file(self, csv_file: Path, status_filter: List[str]) -> tuple:
        """Ingest a single CSV file.

        Args:
            csv_file: Path to CSV file
            status_filter: List of status values to include

        Returns:
            Tuple of (rows_ingested, rows_filtered)

        Raises:
            IngestionError: If file processing fails
        """
        logger.debug(f"Processing file: {csv_file.name}")

        ingestion_timestamp = datetime.now().isoformat()
        rows_ingested = 0
        rows_filtered = 0

        try:
            # Read CSV in chunks
            for chunk in pd.read_csv(csv_file, chunksize=self.chunk_size):
                # Normalize column names: lowercase and replace spaces with underscores
                chunk.columns = chunk.columns.str.lower().str.replace(' ', '_')

                # Filter by status
                filtered_chunk = chunk[chunk["test_status"].isin(status_filter)]
                rows_filtered += len(chunk) - len(filtered_chunk)

                if filtered_chunk.empty:
                    continue

                # Transform chunk to TestRecords
                records = self._process_csv_chunk(
                    filtered_chunk, csv_file.name, ingestion_timestamp
                )

                # Batch insert
                if records:
                    record_dicts = [record.to_dict() for record in records]
                    inserted = self.db.insert_batch(record_dicts)
                    rows_ingested += inserted

        except pd.errors.EmptyDataError:
            logger.warning(f"Empty CSV file: {csv_file.name}")
            return 0, 0

        except KeyError as e:
            raise IngestionError(
                f"Required column missing in CSV: {e}", file_path=str(csv_file)
            ) from e

        except Exception as e:
            raise IngestionError(
                f"Error processing CSV file: {e}", file_path=str(csv_file)
            ) from e

        logger.debug(
            f"File processed: {csv_file.name} ({rows_ingested} ingested, {rows_filtered} filtered)"
        )

        return rows_ingested, rows_filtered

    def _process_csv_chunk(
        self, chunk: pd.DataFrame, source_file: str, ingestion_timestamp: str
    ) -> List[TestRecord]:
        """Filter and transform a chunk of CSV data.

        Args:
            chunk: DataFrame chunk from CSV
            source_file: Name of source CSV file
            ingestion_timestamp: ISO timestamp of ingestion

        Returns:
            List of TestRecord objects
        """
        records = []

        for _, row in chunk.iterrows():
            try:
                # Extract BER lane values (8 lanes)
                ber_lanes = []
                for i in range(8):
                    col_name = f"acc_ber_lane{i}"
                    if col_name in row:
                        val = row[col_name]
                        ber_lanes.append(None if pd.isna(val) else float(val))
                    else:
                        ber_lanes.append(None)

                # Convert error count arrays to JSON strings
                error_cnt = None
                if "acc_lane_error_cnt" in row and not pd.isna(row["acc_lane_error_cnt"]):
                    # Handle array-like values
                    val = row["acc_lane_error_cnt"]
                    if isinstance(val, str):
                        error_cnt = val
                    else:
                        error_cnt = json.dumps(val)

                error_cnt_overflow = None
                if "acc_lane_error_cnt_overflow" in row and not pd.isna(
                    row["acc_lane_error_cnt_overflow"]
                ):
                    val = row["acc_lane_error_cnt_overflow"]
                    if isinstance(val, str):
                        error_cnt_overflow = val
                    else:
                        error_cnt_overflow = json.dumps(val)

                # Create TestRecord
                record = TestRecord(
                    host=str(row["host"]).strip('"') if "host" in row else "",
                    bus_id=str(row["bus_id"]).strip('"') if "bus_id" in row else "",
                    eth_id=str(row["eth_id"]).strip('"') if "eth_id" in row else "",
                    date=str(row["date"]).strip('"') if "date" in row else "",
                    test_status=str(row["test_status"]).strip('"'),
                    train_speed=int(row["train_speed"]) if "train_speed" in row else 0,
                    acc_ber_lanes=ber_lanes,
                    interface_id=str(row["interface_id"]).strip('"')
                    if "interface_id" in row and not pd.isna(row["interface_id"])
                    else None,
                    train_type_requested=str(row["train_type_requested"]).strip('"')
                    if "train_type_requested" in row and not pd.isna(row["train_type_requested"])
                    else None,
                    train_mode=str(row["train_mode"]).strip('"')
                    if "train_mode" in row and not pd.isna(row["train_mode"])
                    else None,
                    port_type=str(row["port_type"]).strip('"')
                    if "port_type" in row and not pd.isna(row["port_type"])
                    else None,
                    acc_lane_error_cnt=error_cnt,
                    acc_lane_error_cnt_overflow=error_cnt_overflow,
                    acc_time_elapsed=float(row["acc_time_elapsed"])
                    if "acc_time_elapsed" in row and not pd.isna(row["acc_time_elapsed"])
                    else None,
                    ber_threshold_used=float(row["ber_threshold_used"])
                    if "ber_threshold_used" in row and not pd.isna(row["ber_threshold_used"])
                    else None,
                    interface_type_used=str(row["interface_type_used"]).strip('"')
                    if "interface_type_used" in row and not pd.isna(row["interface_type_used"])
                    else None,
                    source_file=source_file,
                    ingestion_timestamp=ingestion_timestamp,
                )

                records.append(record)

            except Exception as e:
                logger.warning(f"Failed to process row in {source_file}: {e}")
                continue

        return records
