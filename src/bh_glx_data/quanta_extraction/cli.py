"""Command-line interface for Quanta test data extraction."""

import argparse
import logging
import sys
from pathlib import Path

from bh_glx_data.core.exceptions import DataProcessingError
from bh_glx_data.quanta_extraction.analyzer import analyze_excel_failures, print_failures_summary
from bh_glx_data.quanta_extraction.extractor import extract_csv_from_archive

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Extract test CSV files from Quanta QC2/QC3 test archives",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract CSV files from a test archive
  %(prog)s QC2-FRO-QTWS7TKC260700003-0.tar.gz

  # Specify custom output directory
  %(prog)s QC2-FRO-QTWS7TKC260700003-0.tar.gz --output-dir my_data/

  # Specify custom output filename prefix
  %(prog)s QC2-FRO-QTWS7TKC260700003-0.tar.gz --prefix D2K-95

  # Analyze Excel file for failures
  %(prog)s --analyze QC3_S7TK_0128_build_test.xlsx

  # Verbose logging
  %(prog)s QC2-FRO-QTWS7TKC260700003-0.tar.gz --verbose

The tool will:
  1. Open the test archive
  2. Find and extract ft_eth_stress_*.tar.gz or ft_burnin_*.tar.gz archives
  3. Extract data_test_*.csv and prbs_test_*.csv files to output directory
        """,
    )

    parser.add_argument(
        "archive_file",
        nargs="?",
        type=Path,
        help="Path to the QC2/QC3 test archive file (e.g., QC2-FRO-*.tar.gz)",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("quanta"),
        help="Output directory for extracted CSV files (default: quanta/)",
    )

    parser.add_argument(
        "-p",
        "--prefix",
        type=str,
        default=None,
        help="Prefix for output filenames (default: archive basename)",
    )

    parser.add_argument(
        "--analyze",
        type=Path,
        help="Analyze Excel file for failures (e.g., QC3_S7TK_0128_build_test.xlsx)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


def print_extraction_summary(result):
    """Print extraction summary.

    Args:
        result: ExtractionResult object
    """
    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"Total CSV files extracted: {result.total_files}")
    print(f"Success: {'Yes' if result.success else 'No'}")

    if result.extracted_files:
        print(f"\nExtracted files ({len(result.extracted_files)}):")
        for file_path in result.extracted_files:
            print(f"  - {file_path.name}")

    if result.error_message:
        print(f"\nErrors: {result.error_message}")

    if result.extracted_files:
        output_dir = result.extracted_files[0].parent
        print(f"\nOutput directory: {output_dir.absolute()}")

    print("=" * 80)


def main():
    """Main entry point for the Quanta extraction CLI."""
    args = parse_arguments()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check if analyzing Excel file
    if args.analyze:
        logger.info("Analyzing Excel file for failures")
        try:
            failures = analyze_excel_failures(args.analyze)
            print_failures_summary(failures)
            sys.exit(0)
        except DataProcessingError as e:
            logger.error(f"Failed to analyze Excel file: {e}")
            sys.exit(1)

    # Otherwise, extract from archive
    if not args.archive_file:
        logger.error("Error: archive_file is required when not using --analyze")
        print("\nUsage: bh-extract-quanta ARCHIVE_FILE [options]")
        print("   or: bh-extract-quanta --analyze EXCEL_FILE")
        print("\nFor more information, use: bh-extract-quanta --help")
        sys.exit(1)

    # Validate input file
    if not args.archive_file.exists():
        logger.error(f"File not found: {args.archive_file}")
        sys.exit(1)

    if not args.archive_file.name.endswith(".tar.gz"):
        logger.error(f"Expected a .tar.gz file, got: {args.archive_file.name}")
        sys.exit(1)

    logger.info("Starting extraction")
    logger.info(f"Archive: {args.archive_file}")
    logger.info(f"Output directory: {args.output_dir}")

    # Extract CSV files
    try:
        result = extract_csv_from_archive(
            archive_path=args.archive_file,
            output_dir=args.output_dir,
            archive_basename=args.prefix,
        )

        # Print summary
        print_extraction_summary(result)

        # Exit with appropriate code
        if not result.success:
            sys.exit(1)

    except DataProcessingError as e:
        logger.error(f"Extraction failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback

        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
