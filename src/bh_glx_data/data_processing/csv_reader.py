"""CSV reading and validation utilities."""

import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

from bh_glx_data.core.exceptions import CSVParseError

logger = logging.getLogger(__name__)


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
) -> None:
    """Validate that a DataFrame has required columns.

    Args:
        df: pandas DataFrame to validate
        required_columns: List of required column names
        file_path: Optional path for error messages

    Raises:
        CSVParseError: If required columns are missing
    """
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        error_msg = f"Missing required columns: {', '.join(missing_columns)}"
        if file_path:
            error_msg += f"\nAvailable columns: {', '.join(df.columns)}"

        raise CSVParseError(
            error_msg,
            file_path=str(file_path) if file_path else None,
        )


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
