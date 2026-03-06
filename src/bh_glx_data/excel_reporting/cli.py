"""Command-line interface for Excel summary generation."""

import argparse
import logging
import sys
from pathlib import Path

from bh_glx_data.core.exceptions import DataProcessingError, ExcelGenerationError, TemplateError
from bh_glx_data.excel_reporting.generator import process_all_systems

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Generate Excel summaries from CSV test data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all systems
  %(prog)s

  # Process specific systems
  %(prog)s --systems bh-glx-b02u02

  # Process multiple systems
  %(prog)s --systems bh-glx-b02u02 bh-glx-b03u02

  # Custom directories
  %(prog)s --data-dir /path/to/csv --output-dir /path/to/output

  # Custom template
  %(prog)s --template /path/to/template.xlsx

  # Verbose logging
  %(prog)s --verbose
        """,
    )

    parser.add_argument(
        "--systems",
        nargs="*",
        help="System hostname(s) to process (e.g., bh-glx-b02u02). If not provided, processes all systems",
    )

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("csv_data"),
        help="Directory containing CSV files (default: csv_data/)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("summaries"),
        help="Output directory for Excel files (default: summaries/)",
    )

    parser.add_argument(
        "--template",
        type=Path,
        default=Path("templates/system_data_template.xlsx"),
        help="Path to Excel template file (default: templates/system_data_template.xlsx)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


def print_summary(result: dict):
    """Print processing summary.

    Args:
        result: Dictionary with processing results
    """
    print("\n" + "=" * 60)
    print("EXCEL GENERATION SUMMARY")
    print("=" * 60)

    print(f"System+firmware combinations found: {result['total_combinations']}")
    print(f"Successfully generated: {result['success_count']}")
    print(f"Errors: {result['error_count']}")

    if result["generated_files"]:
        print(f"\nGenerated files ({len(result['generated_files'])}):")
        for file_path in result["generated_files"]:
            print(f"  - {file_path.name}")

    if result["errors"]:
        print(f"\nErrors encountered ({len(result['errors'])}):")
        for error in result["errors"]:
            print(f"  - {error}")

    if result["generated_files"]:
        # Get output directory from first file
        output_dir = result["generated_files"][0].parent
        print(f"\nOutput directory: {output_dir.absolute()}")


def main():
    """Main entry point for the Excel summary generation CLI."""
    args = parse_arguments()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate directories and template
    if not args.data_dir.exists():
        logger.error(f"Data directory not found: {args.data_dir}")
        sys.exit(1)

    if not args.template.exists():
        logger.error(f"Template file not found: {args.template}")
        logger.info("Please ensure templates/system_data_template.xlsx exists")
        sys.exit(1)

    logger.info("Starting Excel summary generation")
    logger.info(f"Data directory: {args.data_dir}")
    logger.info(f"Template: {args.template}")
    logger.info(f"Output directory: {args.output_dir}")

    if args.systems:
        logger.info(f"Filtering to systems: {', '.join(args.systems)}")

    # Process systems
    try:
        result = process_all_systems(
            data_dir=args.data_dir,
            template_path=args.template,
            output_dir=args.output_dir,
            system_filter=args.systems,
        )

        # Print summary
        print_summary(result)

        # Exit with appropriate code
        if result["error_count"] > 0 and result["success_count"] == 0:
            # All failed
            sys.exit(1)
        elif result["error_count"] > 0:
            # Some failed
            sys.exit(2)
        else:
            # All succeeded
            sys.exit(0)

    except DataProcessingError as e:
        logger.error(f"Data processing error: {e}")
        sys.exit(1)
    except TemplateError as e:
        logger.error(f"Template error: {e}")
        sys.exit(1)
    except ExcelGenerationError as e:
        logger.error(f"Excel generation error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback

        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
