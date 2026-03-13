"""Command-line interface for system analysis tool.

This module provides the main entry point for the system analysis tool,
supporting subcommands for ingestion, querying, visualization, export, and
interactive analysis.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from bh_glx_data.core.exceptions import (
    DatabaseError,
    IngestionError,
    LaneSelectorError,
    QueryError,
)
from bh_glx_data.system_analysis.database import DatabaseManager, get_default_db_path
from bh_glx_data.system_analysis.export import ExcelExporter, ExportFilters
from bh_glx_data.system_analysis.ingestion import CSVIngester
from bh_glx_data.system_analysis.interactive import AnalysisShell
from bh_glx_data.system_analysis.query_engine import LaneSelector, QueryEngine
from bh_glx_data.system_analysis.visualization import (
    BER_COLOR_SCHEMES,
    COUNT_COLOR_SCHEMES,
    ColorScheme,
    HeatMapRenderer,
    TableRenderer,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Analyze PRBS test data across multiple systems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest CSV data
  %(prog)s ingest ./data/

  # Query BER statistics
  %(prog)s stats all --speed 200
  %(prog)s stats 01:00.0/ETH07

  # Query with heatmap visualization
  %(prog)s threshold all --speed 200 --format heatmap

  # Export database to Excel
  %(prog)s export-excel --output full_db.xlsx

  # Interactive shell
  %(prog)s shell

Lane Specifications:
  all                      - All lanes on all systems
  01:00.0/ETH07           - Specific port (all lanes)
  01:00.0/*               - All ports on bus_id
  system/01:00.0/ETH07    - Specific system and port
        """,
    )

    # Global options
    parser.add_argument(
        "--db",
        type=Path,
        help=f"Database path (default: {get_default_db_path()})",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set logging level (default: INFO)",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest CSV files into database")
    ingest_parser.add_argument("input_dir", type=Path, help="Directory containing CSV files")
    ingest_parser.add_argument(
        "--status-filter",
        nargs="+",
        default=["PASS", "BER_THRESHOLD_EXCEEDED", "TRAINING_FAIL"],
        help="Test status values to include (default: PASS BER_THRESHOLD_EXCEEDED TRAINING_FAIL)",
    )

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show BER statistics")
    stats_parser.add_argument("lane_spec", type=str, help="Lane specification (e.g., 01:00.0/ETH07)")
    stats_parser.add_argument(
        "--speed",
        type=int,
        action="append",
        dest="speeds",
        help="Filter by train speed (can be specified multiple times)",
    )
    stats_parser.add_argument(
        "--format",
        choices=["table", "heatmap"],
        default="table",
        help="Output format (default: table)",
    )
    stats_parser.add_argument(
        "--color-scheme",
        type=str,
        help="Color scheme name for heatmap (default, sensitive, tolerant)",
    )
    stats_parser.add_argument(
        "--statistic",
        choices=["avg", "min", "max", "high_ber", "variance"],
        default="max",
        help="Statistic to display in heatmap (variance shows avg with consistency symbols)",
    )

    # Threshold command
    threshold_parser = subparsers.add_parser(
        "threshold", help="Show BER threshold exceeded counts"
    )
    threshold_parser.add_argument("lane_spec", type=str, help="Lane specification")
    threshold_parser.add_argument(
        "--speed",
        type=int,
        action="append",
        dest="speeds",
        help="Filter by train speed",
    )
    threshold_parser.add_argument(
        "--format",
        choices=["table", "heatmap"],
        default="table",
        help="Output format",
    )
    threshold_parser.add_argument(
        "--color-scheme",
        type=str,
        help="Color scheme name for heatmap",
    )

    # Custom threshold command
    custom_parser = subparsers.add_parser("custom", help="Show custom BER threshold counts")
    custom_parser.add_argument("lane_spec", type=str, help="Lane specification")
    custom_parser.add_argument("threshold", type=float, help="Custom BER threshold (e.g., 1e-10)")
    custom_parser.add_argument(
        "--speed",
        type=int,
        action="append",
        dest="speeds",
        help="Filter by train speed",
    )
    custom_parser.add_argument(
        "--format",
        choices=["table", "heatmap"],
        default="table",
        help="Output format",
    )
    custom_parser.add_argument(
        "--color-scheme",
        type=str,
        help="Color scheme name for heatmap",
    )

    # Training failures command
    training_parser = subparsers.add_parser("training", help="Show training failure counts")
    training_parser.add_argument("lane_spec", type=str, help="Lane specification")
    training_parser.add_argument(
        "--speed",
        type=int,
        action="append",
        dest="speeds",
        help="Filter by train speed",
    )
    training_parser.add_argument(
        "--format",
        choices=["table", "heatmap"],
        default="table",
        help="Output format",
    )
    training_parser.add_argument(
        "--color-scheme",
        type=str,
        help="Color scheme name for heatmap",
    )

    # Info command
    info_parser = subparsers.add_parser("info", help="Show database information")

    # Export command
    export_parser = subparsers.add_parser("export-excel", help="Export database to Excel")
    export_parser.add_argument(
        "--output",
        type=Path,
        help="Output Excel file path (default: database_export.xlsx)",
    )
    export_parser.add_argument(
        "--hosts",
        nargs="+",
        help="Filter by hostnames",
    )
    export_parser.add_argument(
        "--speeds",
        type=int,
        nargs="+",
        help="Filter by train speeds",
    )
    export_parser.add_argument(
        "--status",
        nargs="+",
        help="Filter by test status",
    )
    export_parser.add_argument(
        "--date-range",
        nargs=2,
        metavar=("START", "END"),
        help="Filter by date range (YYYY-MM-DD YYYY-MM-DD)",
    )

    # Shell command
    shell_parser = subparsers.add_parser("shell", help="Start interactive analysis shell")

    return parser.parse_args()


def handle_ingest(db: DatabaseManager, args: argparse.Namespace) -> int:
    """Handle ingest command.

    Args:
        db: DatabaseManager instance
        args: Parsed arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        input_dir = args.input_dir
        if not input_dir.exists():
            logger.error(f"Input directory not found: {input_dir}")
            return 1

        if not input_dir.is_dir():
            logger.error(f"Input path is not a directory: {input_dir}")
            return 1

        logger.info(f"Ingesting PRBS test data from {input_dir}...")
        logger.info("")

        ingester = CSVIngester(db)
        result = ingester.ingest_directory(input_dir, status_filter=args.status_filter)

        logger.info("")
        logger.info("Ingestion complete:")
        logger.info(f"  Files processed: {result.files_processed}")
        logger.info(f"  Rows ingested: {result.rows_ingested:,}")
        logger.info(f"  Rows filtered: {result.rows_filtered:,} (status filter)")
        logger.info(f"  Duration: {result.duration:.1f} seconds")
        logger.info(f"  Database: {db.db_path}")

        if result.errors:
            logger.warning(f"\nErrors encountered ({len(result.errors)}):")
            for error in result.errors:
                logger.warning(f"  {error}")

        return 0

    except IngestionError as e:
        logger.error(f"Ingestion failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during ingestion: {e}")
        logger.debug("", exc_info=True)
        return 1


def handle_stats(db: DatabaseManager, args: argparse.Namespace) -> int:
    """Handle stats command.

    Args:
        db: DatabaseManager instance
        args: Parsed arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        selector = LaneSelector.from_spec(args.lane_spec)
        engine = QueryEngine(db)

        result = engine.query_ber_statistics(
            selector,
            train_speeds=args.speeds,
        )

        if args.format == "table":
            renderer = TableRenderer()
            output = renderer.render_ber_statistics(result)
            print(output)
        else:  # heatmap
            color_scheme = _get_color_scheme(args.color_scheme, BER_COLOR_SCHEMES)
            renderer = HeatMapRenderer(ber_color_scheme=color_scheme)
            output = renderer.render_ber_heatmap(result, metric=args.statistic)
            print(output)

        return 0

    except LaneSelectorError as e:
        logger.error(f"Invalid lane specification: {e}")
        return 1
    except QueryError as e:
        logger.error(f"Query failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug("", exc_info=True)
        return 1


def handle_threshold(db: DatabaseManager, args: argparse.Namespace) -> int:
    """Handle threshold command.

    Args:
        db: DatabaseManager instance
        args: Parsed arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        selector = LaneSelector.from_spec(args.lane_spec)
        engine = QueryEngine(db)

        result = engine.query_ber_threshold_exceeded(selector, train_speeds=args.speeds)

        if args.format == "table":
            renderer = TableRenderer()
            output = renderer.render_count_table(result)
            print(output)
        else:  # heatmap
            color_scheme = _get_color_scheme(args.color_scheme, COUNT_COLOR_SCHEMES)
            renderer = HeatMapRenderer(count_color_scheme=color_scheme)
            output = renderer.render_count_heatmap(result)
            print(output)

        return 0

    except LaneSelectorError as e:
        logger.error(f"Invalid lane specification: {e}")
        return 1
    except QueryError as e:
        logger.error(f"Query failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug("", exc_info=True)
        return 1


def handle_custom(db: DatabaseManager, args: argparse.Namespace) -> int:
    """Handle custom threshold command.

    Args:
        db: DatabaseManager instance
        args: Parsed arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        selector = LaneSelector.from_spec(args.lane_spec)
        engine = QueryEngine(db)

        result = engine.query_custom_ber_threshold(
            selector,
            args.threshold,
            train_speeds=args.speeds,
        )

        if args.format == "table":
            renderer = TableRenderer()
            output = renderer.render_count_table(result)
            print(output)
        else:  # heatmap
            color_scheme = _get_color_scheme(args.color_scheme, COUNT_COLOR_SCHEMES)
            renderer = HeatMapRenderer(count_color_scheme=color_scheme)
            output = renderer.render_count_heatmap(result)
            print(output)

        return 0

    except LaneSelectorError as e:
        logger.error(f"Invalid lane specification: {e}")
        return 1
    except QueryError as e:
        logger.error(f"Query failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug("", exc_info=True)
        return 1


def handle_training(db: DatabaseManager, args: argparse.Namespace) -> int:
    """Handle training failures command.

    Args:
        db: DatabaseManager instance
        args: Parsed arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        selector = LaneSelector.from_spec(args.lane_spec)
        engine = QueryEngine(db)

        result = engine.query_training_failures(selector, train_speeds=args.speeds)

        if args.format == "table":
            renderer = TableRenderer()
            output = renderer.render_count_table(result)
            print(output)
        else:  # heatmap
            color_scheme = _get_color_scheme(args.color_scheme, COUNT_COLOR_SCHEMES)
            renderer = HeatMapRenderer(count_color_scheme=color_scheme)
            output = renderer.render_count_heatmap(result)
            print(output)

        return 0

    except LaneSelectorError as e:
        logger.error(f"Invalid lane specification: {e}")
        return 1
    except QueryError as e:
        logger.error(f"Query failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug("", exc_info=True)
        return 1


def handle_info(db: DatabaseManager, args: argparse.Namespace) -> int:
    """Handle info command.

    Args:
        db: DatabaseManager instance
        args: Parsed arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        stats = db.get_database_stats()

        print("\nDatabase Information:")
        print(f"  Database: {db.db_path}")
        print(f"  Total tests: {stats.total_tests:,}")
        print(f"  Unique systems: {stats.unique_hosts}")
        print(f"  Train speeds: {', '.join(str(s) for s in stats.unique_speeds)}")
        print(f"  Date range: {stats.date_range[0]} to {stats.date_range[1]}")
        print(f"\n  Status breakdown:")
        for status, count in stats.status_breakdown.items():
            percentage = (count / stats.total_tests * 100) if stats.total_tests > 0 else 0
            print(f"    {status}: {count:,} ({percentage:.1f}%)")
        print(f"\n  Total ingestions: {stats.total_ingestions}\n")

        return 0

    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug("", exc_info=True)
        return 1


def handle_export_excel(db: DatabaseManager, args: argparse.Namespace) -> int:
    """Handle export-excel command.

    Args:
        db: DatabaseManager instance
        args: Parsed arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        output_path = args.output or Path("database_export.xlsx")

        # Build filters
        filters = None
        if any([args.hosts, args.speeds, args.status, args.date_range]):
            filters = ExportFilters(
                hosts=args.hosts,
                train_speeds=args.speeds,
                test_status=args.status,
                date_range=tuple(args.date_range) if args.date_range else None,
            )

        logger.info("Exporting database to Excel...")

        exporter = ExcelExporter(db)
        result = exporter.export_full_database(output_path, filters=filters)

        logger.info("\nExport complete:")
        logger.info(f"  Rows exported: {result.rows_exported:,}")
        logger.info(f"  Sheets created: {result.sheets_created}")
        logger.info(f"  File size: {result.file_size_bytes / (1024 * 1024):.1f} MB")
        logger.info(f"  Output: {result.output_path}")

        if filters:
            logger.info(f"\n  Filters applied:")
            if filters.hosts:
                logger.info(f"    - Hosts: {', '.join(filters.hosts)}")
            if filters.train_speeds:
                logger.info(f"    - Speeds: {', '.join(str(s) for s in filters.train_speeds)}")
            if filters.test_status:
                logger.info(f"    - Status: {', '.join(filters.test_status)}")
            if filters.date_range:
                logger.info(f"    - Date range: {filters.date_range[0]} to {filters.date_range[1]}")

        return 0

    except Exception as e:
        logger.error(f"Export failed: {e}")
        logger.debug("", exc_info=True)
        return 1


def handle_shell(db: DatabaseManager, args: argparse.Namespace) -> int:
    """Handle shell command.

    Args:
        db: DatabaseManager instance
        args: Parsed arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        engine = QueryEngine(db)
        exporter = ExcelExporter(db)
        shell = AnalysisShell(engine, exporter)

        shell.run()
        return 0

    except Exception as e:
        logger.error(f"Shell error: {e}")
        logger.debug("", exc_info=True)
        return 1


def _get_color_scheme(
    scheme_name: Optional[str],
    scheme_dict: dict,
) -> Optional[ColorScheme]:
    """Get color scheme from name.

    Args:
        scheme_name: Color scheme name
        scheme_dict: Dictionary of available schemes

    Returns:
        ColorScheme or None if not found
    """
    if scheme_name is None:
        return None

    if scheme_name in scheme_dict:
        return scheme_dict[scheme_name]

    logger.warning(f"Unknown color scheme: {scheme_name}. Using default.")
    return None


def main():
    """Main entry point for system analysis CLI."""
    args = parse_arguments()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Get database path
    db_path = args.db or get_default_db_path()

    # Initialize database
    try:
        db = DatabaseManager(db_path)

        # Initialize schema if this is a new database or command is not info/shell
        if args.command in ["ingest", "stats", "threshold", "custom", "training", "export-excel"]:
            db.initialize_schema()
        elif args.command in ["info", "shell"]:
            # For info and shell, only initialize if database doesn't exist
            if not db_path.exists():
                logger.error(f"Database not found: {db_path}")
                logger.error("Run 'ingest' command first to create the database.")
                return 1
            db.initialize_schema()  # Safe to call even if already initialized

    except DatabaseError as e:
        logger.error(f"Database initialization failed: {e}")
        return 1

    # Handle commands
    if args.command == "ingest":
        return handle_ingest(db, args)
    elif args.command == "stats":
        return handle_stats(db, args)
    elif args.command == "threshold":
        return handle_threshold(db, args)
    elif args.command == "custom":
        return handle_custom(db, args)
    elif args.command == "training":
        return handle_training(db, args)
    elif args.command == "info":
        return handle_info(db, args)
    elif args.command == "export-excel":
        return handle_export_excel(db, args)
    elif args.command == "shell":
        return handle_shell(db, args)
    else:
        logger.error("No command specified. Use --help for usage information.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
