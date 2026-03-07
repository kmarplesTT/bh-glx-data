"""Unified command-line interface for BH Galaxy Data Analysis Tool."""

import argparse
import logging
import sys
from pathlib import Path

# Import CLI modules
from bh_glx_data.data_processing.cli import main as filter_main
from bh_glx_data.excel_reporting.cli import main as excel_main
from bh_glx_data.hardware.cli import main as topology_main
from bh_glx_data.jira_integration.cli import main as jira_main
from bh_glx_data.quanta_extraction.cli import main as quanta_main

logger = logging.getLogger(__name__)


def create_parser():
    """Create the main argument parser with subcommands.

    Returns:
        argparse.ArgumentParser: Main parser with subcommands
    """
    parser = argparse.ArgumentParser(
        prog="bh-glx-data",
        description="BH Galaxy Data Analysis Tool - Unified CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available Commands:
  jira-retrieve    Download CSV attachments from Jira tickets
  filter-failures  Filter failed test rows from CSV files
  generate-excel   Generate Excel summaries from CSV test data
  extract-quanta   Extract test data from Quanta QC3 packages
  topology         Query platform ETH port connectivity

Examples:
  # Download CSV files from Jira
  bh-glx-data jira-retrieve --tickets SYS-123 SYS-456

  # Filter failures from test data
  bh-glx-data filter-failures data_test_results.csv

  # Generate Excel summaries
  bh-glx-data generate-excel --data-dir csv_data/

  # Extract Quanta failure data
  bh-glx-data extract-quanta QC3_UBB_20260128.tar.gz

  # Query platform topology
  bh-glx-data topology 01:00.0 ETH07

For detailed help on a specific command:
  bh-glx-data <command> --help

Direct Command Shortcuts:
  The following commands are also available as standalone scripts:
  - bh-jira-retrieve (same as: bh-glx-data jira-retrieve)
  - bh-filter-failures (same as: bh-glx-data filter-failures)
  - bh-generate-excel (same as: bh-glx-data generate-excel)
  - bh-extract-quanta (same as: bh-glx-data extract-quanta)
  - bh-topology (same as: bh-glx-data topology)
        """,
    )

    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    # Global options
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set logging level (default: INFO)",
    )

    # Subcommands
    subparsers = parser.add_subparsers(
        dest="command", title="commands", description="Available commands", help="Command to run"
    )

    # Jira Retrieve
    jira_parser = subparsers.add_parser(
        "jira-retrieve",
        help="Download CSV attachments from Jira tickets",
        description="Retrieve CSV test data files from Jira tickets",
    )
    jira_parser.add_argument(
        "--tickets",
        nargs="*",
        help="Jira ticket keys (e.g., SYS-123). If not provided, reads from config.yaml",
    )
    jira_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory for CSV files (default: data/)",
    )
    jira_parser.add_argument("--config", type=Path, help="Path to configuration file")

    # Filter Failures
    filter_parser = subparsers.add_parser(
        "filter-failures",
        help="Filter failed test rows from CSV files",
        description="Extract only failed test cases from CSV test data",
    )
    filter_parser.add_argument("input_file", type=Path, help="Path to input CSV file")
    filter_parser.add_argument(
        "-o", "--output", type=Path, help="Path to output CSV file (default: <input>_failures.csv)"
    )
    filter_parser.add_argument(
        "--status-column",
        default="test_status",
        help="Column name for test status (default: test_status)",
    )

    # Generate Excel
    excel_parser = subparsers.add_parser(
        "generate-excel",
        help="Generate Excel summaries from CSV test data",
        description="Process CSV files and create Excel reports with pivot tables",
    )
    excel_parser.add_argument(
        "--systems",
        nargs="*",
        help="System hostname(s) to process. If not provided, processes all systems",
    )
    excel_parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("csv_data"),
        help="Directory containing CSV files (default: csv_data/)",
    )
    excel_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("summaries"),
        help="Output directory for Excel files (default: summaries/)",
    )
    excel_parser.add_argument(
        "--template",
        type=Path,
        default=Path("templates/system_data_template.xlsx"),
        help="Path to Excel template file",
    )

    # Extract Quanta
    quanta_parser = subparsers.add_parser(
        "extract-quanta",
        help="Extract test data from Quanta QC3 packages",
        description="Extract CSV files from Quanta QC3 test archives or analyze Excel failures",
    )
    quanta_parser.add_argument(
        "archive_file", nargs="?", type=Path, help="Path to QC3 test archive (tar.gz)"
    )
    quanta_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("quanta"),
        help="Output directory for extracted files (default: quanta/)",
    )
    quanta_parser.add_argument(
        "-p", "--prefix", type=str, help="Prefix for output filenames (default: archive basename)"
    )
    quanta_parser.add_argument(
        "--analyze", type=Path, help="Analyze Excel file for failures (e.g., QC3_test.xlsx)"
    )

    # Topology
    topology_parser = subparsers.add_parser(
        "topology",
        help="Query platform ETH port connectivity",
        description="Query Blackhole Galaxy platform topology",
    )
    topology_parser.add_argument("bus_id", help="Bus ID of the device (e.g., '01:00.0' or '01')")
    topology_parser.add_argument(
        "eth_port", nargs="?", help="ETH port to query (e.g., 'ETH07' or '7')"
    )
    topology_parser.add_argument(
        "--all", "-a", action="store_true", help="Show all connections for the device"
    )
    topology_parser.add_argument("--json", "-j", action="store_true", help="Output in JSON format")
    topology_parser.add_argument(
        "--bidirectional", "-b", action="store_true", help="Show reverse connection"
    )

    return parser


def configure_logging(verbose: bool = False, log_level: str = "INFO"):
    """Configure logging for the CLI.

    Args:
        verbose: Enable verbose logging (sets level to DEBUG)
        log_level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    if verbose:
        level = logging.DEBUG
    else:
        level = getattr(logging, log_level)

    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")


def main():
    """Main entry point for the unified CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Configure logging
    configure_logging(verbose=args.verbose, log_level=args.log_level)

    # If no command specified, show help
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to appropriate subcommand
    # We need to reconstruct sys.argv for the subcommand
    # Remove the main command and subcommand name from argv
    original_argv = sys.argv.copy()

    try:
        # Find the index of the subcommand in argv
        if args.command in sys.argv:
            cmd_index = sys.argv.index(args.command)
            # Set argv to include program name + subcommand args
            sys.argv = [f"bh-{args.command}"] + sys.argv[cmd_index + 1 :]

        if args.command == "jira-retrieve":
            jira_main()
        elif args.command == "filter-failures":
            filter_main()
        elif args.command == "generate-excel":
            excel_main()
        elif args.command == "extract-quanta":
            quanta_main()
        elif args.command == "topology":
            topology_main()
        else:
            parser.print_help()
            sys.exit(1)

    finally:
        # Restore original argv
        sys.argv = original_argv


if __name__ == "__main__":
    main()
