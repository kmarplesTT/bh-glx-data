#!/usr/bin/env python3
"""
Filter test failures from data test CSV files.

This script reads a CSV file containing test data and creates a new CSV file
containing only the rows with failures. Failures are identified when the
test_status column is not equal to ETH_ACTIVE or ETH_UNCONNECTED.
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def filter_failures(input_file: Path, output_file: Path = None) -> None:
    """
    Filter failures from test data CSV.

    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file (default: input_failures.csv)
    """
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)

    # Determine output file name
    if output_file is None:
        output_file = input_file.parent / f"{input_file.stem}_failures.csv"

    logger.info(f"Reading input file: {input_file}")

    try:
        # Read the CSV file
        df = pd.read_csv(input_file)

        logger.info(f"Total rows read: {len(df)}")

        # Check if test_status column exists
        if "test_status" not in df.columns:
            logger.error("Column 'test_status' not found in CSV file")
            logger.info(f"Available columns: {', '.join(df.columns)}")
            sys.exit(1)

        # Filter for failures: test_status NOT in [ETH_ACTIVE, ETH_UNCONNECTED]
        failures_df = df[~df["test_status"].isin(["ETH_ACTIVE", "ETH_UNCONNECTED"])]

        logger.info(f"Failures found: {len(failures_df)}")

        if len(failures_df) == 0:
            logger.info("No failures found - output file not created")
            return

        # Write failures to output file
        failures_df.to_csv(output_file, index=False)
        logger.info(f"Failures written to: {output_file}")

        # Show summary of failure types
        if len(failures_df) > 0:
            logger.info("\nFailure breakdown by test_status:")
            status_counts = failures_df["test_status"].value_counts()
            for status, count in status_counts.items():
                logger.info(f"  {status}: {count}")

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        sys.exit(1)


def main():
    # Deprecation warning
    import warnings

    warnings.warn(
        "\n" + "=" * 80 + "\n"
        "DEPRECATION WARNING: Direct script execution is deprecated.\n"
        "Please use the new command: 'bh-filter-failures'\n"
        "Example: bh-filter-failures data_test_results.csv\n"
        "See documentation for migration guide: docs/migration_guide.md\n"
        "This script will be removed in version 1.0.0\n" + "=" * 80,
        DeprecationWarning,
        stacklevel=2,
    )

    parser = argparse.ArgumentParser(
        description="Filter test failures from data test CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Filter failures from a test file
  python3 filter_failures.py data_test_results.csv

  # Specify custom output file
  python3 filter_failures.py data_test_results.csv --output failures.csv

  # Use the provided test file
  python3 filter_failures.py ~/work/syseng/src/t6ifc/t6py/data_test_results.csv
        """,
    )

    parser.add_argument("input_file", type=Path, help="Path to input CSV file containing test data")

    parser.add_argument(
        "-o", "--output", type=Path, help="Path to output CSV file (default: <input>_failures.csv)"
    )

    args = parser.parse_args()

    filter_failures(args.input_file, args.output)


if __name__ == "__main__":
    main()
