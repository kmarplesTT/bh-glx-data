"""Command-line interface for failure filtering."""

import argparse
import logging
import sys
from pathlib import Path

from bh_glx_data.core.exceptions import CSVParseError, DataProcessingError
from bh_glx_data.data_processing.filter import filter_failures

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Filter test failures from data test CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Filter failures from a test file
  %(prog)s data_test_results.csv

  # Specify custom output file
  %(prog)s data_test_results.csv --output failures.csv

  # Custom status column
  %(prog)s data_test_results.csv --status-column my_status

  # Verbose logging
  %(prog)s data_test_results.csv --verbose
        """,
    )

    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to input CSV file containing test data",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Path to output CSV file (default: <input>_failures.csv)",
    )

    parser.add_argument(
        "--status-column",
        type=str,
        default="test_status",
        help="Name of the status column (default: test_status)",
    )

    parser.add_argument(
        "--success-statuses",
        nargs="+",
        default=["ETH_ACTIVE", "ETH_UNCONNECTED"],
        help="Status values indicating success (default: ETH_ACTIVE ETH_UNCONNECTED)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


def print_summary(result):
    """Print filtering summary.

    Args:
        result: FilterResult object
    """
    print("\n" + "=" * 60)
    print("FILTERING SUMMARY")
    print("=" * 60)

    print(f"Input file: {result.input_file}")
    print(f"Total rows: {result.total_rows}")
    print(f"Failures found: {result.failure_count}")
    print(f"Success: {'Yes' if result.success else 'No'}")

    if result.failure_count > 0:
        print(f"\nOutput file: {result.output_file}")

        if result.failure_breakdown:
            print("\nFailure breakdown by status:")
            for status, count in sorted(result.failure_breakdown.items()):
                print(f"  {status}: {count}")
    else:
        print("\nNo failures found - output file not created")

    if result.error_message:
        print(f"\nNote: {result.error_message}")


def main():
    """Main entry point for the failure filtering CLI."""
    args = parse_arguments()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate input file
    if not args.input_file.exists():
        logger.error(f"Input file not found: {args.input_file}")
        sys.exit(1)

    # Filter failures
    try:
        result = filter_failures(
            input_file=args.input_file,
            output_file=args.output,
            status_column=args.status_column,
            success_statuses=args.success_statuses,
        )

        # Print summary
        print_summary(result)

        # Exit with appropriate code
        if not result.success:
            sys.exit(1)

    except CSVParseError as e:
        logger.error(f"CSV parsing error: {e}")
        sys.exit(1)
    except DataProcessingError as e:
        logger.error(f"Data processing error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
