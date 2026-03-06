"""Failure filtering logic for test data."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from bh_glx_data.core.exceptions import CSVParseError, DataProcessingError
from bh_glx_data.core.models import FilterResult
from bh_glx_data.data_processing.csv_reader import read_csv, validate_csv_schema

logger = logging.getLogger(__name__)

# Default status values that indicate successful tests
DEFAULT_SUCCESS_STATUSES = ["ETH_ACTIVE", "ETH_UNCONNECTED"]


def get_failure_breakdown(df: pd.DataFrame, status_column: str = "test_status") -> Dict[str, int]:
    """Get breakdown of failures by status.

    Args:
        df: DataFrame with failure rows
        status_column: Name of the status column

    Returns:
        Dictionary mapping status values to counts
    """
    if status_column not in df.columns:
        return {}

    status_counts = df[status_column].value_counts()
    return dict(status_counts)


def filter_failure_rows(
    df: pd.DataFrame,
    status_column: str = "test_status",
    success_statuses: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Filter DataFrame to only failure rows.

    Args:
        df: Input DataFrame with test data
        status_column: Name of the status column
        success_statuses: List of status values that indicate success
                         (default: ['ETH_ACTIVE', 'ETH_UNCONNECTED'])

    Returns:
        DataFrame containing only failure rows

    Raises:
        CSVParseError: If status column doesn't exist
    """
    if status_column not in df.columns:
        raise CSVParseError(
            f"Status column '{status_column}' not found in DataFrame",
        )

    if success_statuses is None:
        success_statuses = DEFAULT_SUCCESS_STATUSES

    # Filter for failures: status NOT in success_statuses
    failures_df = df[~df[status_column].isin(success_statuses)]

    logger.info(f"Filtered {len(failures_df)} failures from {len(df)} total rows")

    return failures_df


def filter_failures(
    input_file: Path,
    output_file: Optional[Path] = None,
    status_column: str = "test_status",
    success_statuses: Optional[List[str]] = None,
) -> FilterResult:
    """Filter failures from a CSV file and write to output.

    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file (default: <input>_failures.csv)
        status_column: Name of the status column (default: 'test_status')
        success_statuses: List of status values indicating success

    Returns:
        FilterResult with summary of filtering operation

    Raises:
        CSVParseError: If input file cannot be read
        DataProcessingError: If filtering fails
    """
    # Determine output file name
    if output_file is None:
        output_file = input_file.parent / f"{input_file.stem}_failures.csv"

    logger.info(f"Filtering failures from: {input_file}")

    try:
        # Read input CSV
        df = read_csv(input_file)
        total_rows = len(df)

        # Validate schema
        validate_csv_schema(df, [status_column], input_file)

        # Filter failures
        failures_df = filter_failure_rows(df, status_column, success_statuses)
        failure_count = len(failures_df)

        # Get failure breakdown
        failure_breakdown = get_failure_breakdown(failures_df, status_column)

        # Write failures to output if any found
        if failure_count == 0:
            logger.info("No failures found - output file not created")
            return FilterResult(
                input_file=input_file,
                output_file=output_file,
                total_rows=total_rows,
                failure_count=0,
                failure_breakdown={},
                success=True,
                error_message="No failures found",
            )

        # Write to output file
        failures_df.to_csv(output_file, index=False)
        logger.info(f"Failures written to: {output_file}")

        # Log breakdown
        logger.info("\nFailure breakdown by test_status:")
        for status, count in failure_breakdown.items():
            logger.info(f"  {status}: {count}")

        return FilterResult(
            input_file=input_file,
            output_file=output_file,
            total_rows=total_rows,
            failure_count=failure_count,
            failure_breakdown=failure_breakdown,
            success=True,
        )

    except CSVParseError:
        # Re-raise CSV parse errors
        raise
    except Exception as e:
        logger.error(f"Error filtering failures: {e}")
        raise DataProcessingError(f"Failed to filter failures: {e}")


def filter_by_criteria(
    df: pd.DataFrame,
    criteria: Dict[str, Any],
) -> pd.DataFrame:
    """Filter DataFrame by multiple criteria.

    Args:
        df: Input DataFrame
        criteria: Dictionary of column: value pairs for filtering

    Returns:
        Filtered DataFrame
    """
    filtered_df = df.copy()

    for column, value in criteria.items():
        if column not in df.columns:
            logger.warning(f"Column '{column}' not found, skipping filter")
            continue

        if isinstance(value, list):
            filtered_df = filtered_df[filtered_df[column].isin(value)]
        else:
            filtered_df = filtered_df[filtered_df[column] == value]

        logger.debug(f"After filtering by {column}={value}: {len(filtered_df)} rows")

    return filtered_df
