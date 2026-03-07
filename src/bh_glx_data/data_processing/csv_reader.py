"""CSV reading and validation utilities."""

import logging
import re
from pathlib import Path
from typing import List, Optional

import pandas as pd

from bh_glx_data.core.exceptions import CSVParseError, DataProcessingError

logger = logging.getLogger(__name__)


def read_csv_with_validation(file_path: Path) -> pd.DataFrame:
    """Read and validate a CSV file.

    Args:
        file_path: Path to CSV file

    Returns:
        pandas DataFrame with CSV data

    Raises:
        DataProcessingError: If file cannot be read or parsed
    """
    try:
        return read_csv(file_path)
    except CSVParseError as e:
        raise DataProcessingError(str(e)) from e


def read_csv(file_path: Path) -> pd.DataFrame:
    """Read a CSV file into a pandas DataFrame.

    Args:
        file_path: Path to CSV file

    Returns:
        pandas DataFrame with CSV data

    Raises:
        CSVParseError: If file cannot be read or parsed
    """
    if not file_path.exists():
        raise CSVParseError(
            f"CSV file not found: {file_path}",
            file_path=str(file_path),
        )

    try:
        df = pd.read_csv(file_path)
        logger.info(f"Successfully read {len(df)} rows from {file_path}")
        return df
    except pd.errors.EmptyDataError:
        raise CSVParseError(
            "CSV file is empty",
            file_path=str(file_path),
        )
    except pd.errors.ParserError as e:
        raise CSVParseError(
            f"Failed to parse CSV file: {e}",
            file_path=str(file_path),
        )
    except Exception as e:
        raise CSVParseError(
            f"Unexpected error reading CSV file: {e}",
            file_path=str(file_path),
        )


def validate_csv_schema(
    df: pd.DataFrame,
    required_columns: List[str],
    file_path: Optional[Path] = None,
) -> bool:
    """Validate that a DataFrame has required columns.

    Args:
        df: pandas DataFrame to validate
        required_columns: List of required column names
        file_path: Optional path for error messages

    Returns:
        True if validation passes

    Raises:
        DataProcessingError: If DataFrame is empty or columns are missing
    """
    # Check if DataFrame is empty
    if len(df) == 0 and len(df.columns) == 0:
        if required_columns:
            raise DataProcessingError(
                f"CSV file is empty but required columns were specified: {', '.join(required_columns)}"
            )
        return True

    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        error_msg = f"Missing required columns: {', '.join(missing_columns)}"
        if file_path:
            error_msg += f"\nAvailable columns: {', '.join(df.columns)}"

        raise DataProcessingError(error_msg)

    return True


def extract_firmware_version(filename: str) -> Optional[str]:
    """Extract firmware version from filename.

    Supports patterns like:
    - erisc_v1_7_103
    - v1_7_103
    - v2_0_0

    Args:
        filename: Filename to parse

    Returns:
        Firmware version string or None if not found
    """
    if not filename:
        return None

    # Try to match erisc format first (erisc_v#_#_#)
    erisc_match = re.search(r"erisc_v\d+_\d+_\d+", filename)
    if erisc_match:
        return erisc_match.group(0)

    # Try to match v format (v#_#_# or v#_#_#_#)
    v_match = re.search(r"v\d+_\d+_\d+(?:_\d+)?", filename)
    if v_match:
        return v_match.group(0)

    return None


def extract_hostname_from_csv(file_path: Path) -> Optional[str]:
    """Extract hostname from CSV file.

    Looks for a 'host' column and returns the first non-empty value.

    Args:
        file_path: Path to CSV file

    Returns:
        Hostname string or None if not found
    """
    try:
        df = read_csv(file_path)
        if "host" in df.columns:
            # Get first non-empty hostname
            hostnames = df["host"].dropna().unique()
            if len(hostnames) > 0:
                first_hostname = hostnames[0]
                if first_hostname and str(first_hostname).strip():
                    return str(first_hostname)
        return None
    except CSVParseError:
        return None


def get_column_safe(df: pd.DataFrame, column_name: str, default=None) -> pd.Series:
    """Safely get a column from DataFrame with default value.

    Args:
        df: pandas DataFrame
        column_name: Name of column to retrieve
        default: Default value if column doesn't exist

    Returns:
        pandas Series with column data or default values
    """
    if column_name in df.columns:
        return df[column_name]
    else:
        logger.warning(f"Column '{column_name}' not found, using default value")
        return pd.Series([default] * len(df))


def identify_test_type(df: pd.DataFrame) -> str:
    """Identify the test type from DataFrame content.

    Args:
        df: pandas DataFrame with test data

    Returns:
        Test type identifier ('SERDES_PRBS', 'SIMPLE_PACKET', or 'UNKNOWN')
    """
    # Check if test_type column exists
    if "test_type" in df.columns:
        # Get most common test type
        test_types = df["test_type"].value_counts()
        if len(test_types) > 0:
            most_common = test_types.index[0]
            logger.info(f"Identified test type from column: {most_common}")
            return most_common  # type: ignore[no-any-return]

    # Fallback: check filename patterns or column names
    # This can be extended based on specific needs

    logger.warning("Could not identify test type, using UNKNOWN")
    return "UNKNOWN"


def extract_metadata(df: pd.DataFrame, file_path: Optional[Path] = None) -> dict:
    """Extract metadata from DataFrame and filename.

    Args:
        df: pandas DataFrame with test data
        file_path: Optional path to source file

    Returns:
        Dictionary with extracted metadata
    """
    metadata = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns),
    }

    # Extract hostname if present
    if "host" in df.columns:
        hosts = df["host"].unique()
        if len(hosts) > 0:
            metadata["hostname"] = hosts[0]

    # Extract test type
    metadata["test_type"] = identify_test_type(df)

    # Extract firmware version from filename if provided
    if file_path:
        metadata["source_file"] = str(file_path)
        # Pattern matching for firmware version can be added here

    return metadata
