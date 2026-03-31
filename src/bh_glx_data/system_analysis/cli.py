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
from bh_glx_data.system_analysis.export import ExcelExporter
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
        choices=["avg", "min", "max", "high_ber"],
        default="max",
        help="Statistic to display in heatmap (avg includes variance indicators)",
    )
    stats_parser.add_argument(
        "--excel-output",
        type=Path,
        metavar="FILE",
        help="Export results to Excel file (creates new file or adds worksheet to existing)",
    )
    stats_parser.add_argument(
        "--by-ubb-position",
        "-u",
        action="store_true",
        dest="by_ubb_position",
        help="Aggregate data by UBB chip position (U1-U8) instead of bus_id. "
             "Combines data from equivalent positions across all 4 UBBs.",
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
    threshold_parser.add_argument(
        "--excel-output",
        type=Path,
        metavar="FILE",
        help="Export results to Excel file (creates new file or adds worksheet to existing)",
    )
    threshold_parser.add_argument(
        "--by-ubb-position",
        "-u",
        action="store_true",
        dest="by_ubb_position",
        help="Aggregate data by UBB chip position (U1-U8) instead of bus_id. "
             "Combines data from equivalent positions across all 4 UBBs.",
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
    custom_parser.add_argument(
        "--excel-output",
        type=Path,
        metavar="FILE",
        help="Export results to Excel file (creates new file or adds worksheet to existing)",
    )
    custom_parser.add_argument(
        "--by-ubb-position",
        "-u",
        action="store_true",
        dest="by_ubb_position",
        help="Aggregate data by UBB chip position (U1-U8) instead of bus_id. "
             "Combines data from equivalent positions across all 4 UBBs.",
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
    training_parser.add_argument(
        "--excel-output",
        type=Path,
        metavar="FILE",
        help="Export results to Excel file (creates new file or adds worksheet to existing)",
    )
    training_parser.add_argument(
        "--by-ubb-position",
        "-u",
        action="store_true",
        dest="by_ubb_position",
        help="Aggregate data by UBB chip position (U1-U8) instead of bus_id. "
             "Combines data from equivalent positions across all 4 UBBs.",
    )

    # Histogram command
    histogram_parser = subparsers.add_parser("histogram", help="Show BER histogram for lane(s)")
    histogram_parser.add_argument(
        "lane_spec",
        type=str,
        help="Lane specification (e.g., 01:00.0/ETH07/4 for single lane, 01:00.0/ETH07 for all lanes)",
    )
    histogram_parser.add_argument(
        "--speed",
        type=int,
        action="append",
        dest="speeds",
        help="Filter by train speed",
    )
    histogram_parser.add_argument(
        "--max-bar-width",
        type=int,
        default=50,
        help="Maximum width of histogram bars in characters (default: 50)",
    )
    histogram_parser.add_argument(
        "--excel-output",
        type=Path,
        metavar="FILE",
        help="Export results to Excel file (creates new file or adds worksheet to existing)",
    )
    histogram_parser.add_argument(
        "--by-ubb-position",
        "-u",
        action="store_true",
        dest="by_ubb_position",
        help="Aggregate data by UBB chip position (U1-U8) instead of bus_id. "
             "Combines data from equivalent positions across all 4 UBBs.",
    )

    # Advanced stats command
    advanced_stats_parser = subparsers.add_parser(
        "advanced-stats",
        help="Show aggregated host statistics (per-host BER stats + statistics of those stats)",
    )
    advanced_stats_parser.add_argument(
        "lane_spec",
        type=str,
        help="Lane specification",
    )
    advanced_stats_parser.add_argument(
        "--speed",
        type=int,
        action="append",
        dest="speeds",
        help="Filter by train speed",
    )
    advanced_stats_parser.add_argument(
        "--color-scheme",
        type=str,
        help="Color scheme name for Excel export (default, sensitive, tolerant)",
    )
    advanced_stats_parser.add_argument(
        "--excel-output",
        type=Path,
        metavar="FILE",
        help="Export results to Excel file (creates new file or adds worksheet to existing)",
    )
    advanced_stats_parser.add_argument(
        "--by-ubb-position",
        "-u",
        action="store_true",
        dest="by_ubb_position",
        help="Aggregate data by UBB chip position (U1-U8) instead of bus_id. "
             "Combines data from equivalent positions across all 4 UBBs.",
    )

    # Plot command
    plot_parser = subparsers.add_parser(
        "plot",
        help="Plot BER values for a lane over time",
    )
    plot_parser.add_argument(
        "lane_spec",
        type=str,
        help="Lane specification (requires system/bus_id/eth_id, e.g., 'bh-glx-c02u02/01:00.0/ETH07' or 'bh-glx-c02u02/01:00.0/ETH07/4')",
    )
    plot_parser.add_argument(
        "--speed",
        type=int,
        action="append",
        dest="speeds",
        help="Filter by train speed",
    )
    plot_parser.add_argument(
        "--excel-output",
        type=Path,
        metavar="FILE",
        help="Export results to Excel file with line chart (creates new file or adds worksheet to existing)",
    )

    # Info command
    info_parser = subparsers.add_parser("info", help="Show database information")
    info_parser.add_argument(
        "--excel-output",
        type=Path,
        metavar="FILE",
        help="Export results to Excel file (creates new file or adds worksheet to existing)",
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
        by_ubb_position = getattr(args, "by_ubb_position", False)
        selector = LaneSelector.from_spec(args.lane_spec, normalize_by_ubb=by_ubb_position)
        engine = QueryEngine(db)

        result = engine.query_ber_statistics(
            selector,
            train_speeds=args.speeds,
        )

        # Terminal output (if no Excel export or if verbose)
        if not args.excel_output or args.verbose:
            if args.format == "table":
                renderer = TableRenderer()
                output = renderer.render_ber_statistics(result)
                print(output)
            else:  # heatmap
                color_scheme = _get_color_scheme(args.color_scheme, BER_COLOR_SCHEMES)
                renderer = HeatMapRenderer(ber_color_scheme=color_scheme)
                output = renderer.render_ber_heatmap(result, metric=args.statistic)
                print(output)

        # Excel export (if requested)
        if args.excel_output:
            exporter = ExcelExporter(db)
            color_scheme = _get_color_scheme(args.color_scheme, BER_COLOR_SCHEMES)
            export_result = exporter.export_ber_statistics(
                result,
                args.excel_output,
                lane_spec=args.lane_spec,
                format=args.format,
                color_scheme=color_scheme,
                statistic=args.statistic,
            )
            logger.info(f"\nExported to: {export_result.output_path}")
            logger.info(f"Worksheet: {export_result.worksheet_name}")
            logger.info(f"Rows written: {export_result.rows_written}")

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
        by_ubb_position = getattr(args, "by_ubb_position", False)
        selector = LaneSelector.from_spec(args.lane_spec, normalize_by_ubb=by_ubb_position)
        engine = QueryEngine(db)

        result = engine.query_ber_threshold_exceeded(selector, train_speeds=args.speeds)

        # Terminal output (if no Excel export or if verbose)
        if not args.excel_output or args.verbose:
            if args.format == "table":
                renderer = TableRenderer()
                output = renderer.render_count_table(result)
                print(output)
            else:  # heatmap
                color_scheme = _get_color_scheme(args.color_scheme, COUNT_COLOR_SCHEMES)
                renderer = HeatMapRenderer(count_color_scheme=color_scheme)
                output = renderer.render_count_heatmap(result)
                print(output)

        # Excel export (if requested)
        if args.excel_output:
            exporter = ExcelExporter(db)
            color_scheme = _get_color_scheme(args.color_scheme, COUNT_COLOR_SCHEMES)
            export_result = exporter.export_count_data(
                result,
                args.excel_output,
                lane_spec=args.lane_spec,
                format=args.format,
                color_scheme=color_scheme,
            )
            logger.info(f"\nExported to: {export_result.output_path}")
            logger.info(f"Worksheet: {export_result.worksheet_name}")
            logger.info(f"Rows written: {export_result.rows_written}")

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
        by_ubb_position = getattr(args, "by_ubb_position", False)
        selector = LaneSelector.from_spec(args.lane_spec, normalize_by_ubb=by_ubb_position)
        engine = QueryEngine(db)

        result = engine.query_custom_ber_threshold(
            selector,
            args.threshold,
            train_speeds=args.speeds,
        )

        # Terminal output (if no Excel export or if verbose)
        if not args.excel_output or args.verbose:
            if args.format == "table":
                renderer = TableRenderer()
                output = renderer.render_count_table(result)
                print(output)
            else:  # heatmap
                color_scheme = _get_color_scheme(args.color_scheme, COUNT_COLOR_SCHEMES)
                renderer = HeatMapRenderer(count_color_scheme=color_scheme)
                output = renderer.render_count_heatmap(result)
                print(output)

        # Excel export (if requested)
        if args.excel_output:
            exporter = ExcelExporter(db)
            color_scheme = _get_color_scheme(args.color_scheme, COUNT_COLOR_SCHEMES)
            export_result = exporter.export_count_data(
                result,
                args.excel_output,
                lane_spec=args.lane_spec,
                format=args.format,
                color_scheme=color_scheme,
            )
            logger.info(f"\nExported to: {export_result.output_path}")
            logger.info(f"Worksheet: {export_result.worksheet_name}")
            logger.info(f"Rows written: {export_result.rows_written}")

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
        by_ubb_position = getattr(args, "by_ubb_position", False)
        selector = LaneSelector.from_spec(args.lane_spec, normalize_by_ubb=by_ubb_position)
        engine = QueryEngine(db)

        result = engine.query_training_failures(selector, train_speeds=args.speeds)

        # Terminal output (if no Excel export or if verbose)
        if not args.excel_output or args.verbose:
            if args.format == "table":
                renderer = TableRenderer()
                output = renderer.render_count_table(result)
                print(output)
            else:  # heatmap
                color_scheme = _get_color_scheme(args.color_scheme, COUNT_COLOR_SCHEMES)
                renderer = HeatMapRenderer(count_color_scheme=color_scheme)
                output = renderer.render_count_heatmap(result)
                print(output)

        # Excel export (if requested)
        if args.excel_output:
            exporter = ExcelExporter(db)
            color_scheme = _get_color_scheme(args.color_scheme, COUNT_COLOR_SCHEMES)
            export_result = exporter.export_count_data(
                result,
                args.excel_output,
                lane_spec=args.lane_spec,
                format=args.format,
                color_scheme=color_scheme,
            )
            logger.info(f"\nExported to: {export_result.output_path}")
            logger.info(f"Worksheet: {export_result.worksheet_name}")
            logger.info(f"Rows written: {export_result.rows_written}")

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


def handle_histogram(db: DatabaseManager, args: argparse.Namespace) -> int:
    """Handle histogram command.

    Args:
        db: DatabaseManager instance
        args: Parsed arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        by_ubb_position = getattr(args, "by_ubb_position", False)
        selector = LaneSelector.from_spec(args.lane_spec, normalize_by_ubb=by_ubb_position)
        engine = QueryEngine(db)

        result = engine.query_ber_histogram(selector, train_speeds=args.speeds)

        # Terminal output (if no Excel export or if verbose)
        if not args.excel_output or args.verbose:
            renderer = HeatMapRenderer()
            output = renderer.render_ber_histogram(result, max_bar_width=args.max_bar_width)
            print(output)

        # Excel export (if requested)
        if args.excel_output:
            exporter = ExcelExporter(db)
            export_result = exporter.export_histogram(
                result,
                args.excel_output,
                lane_spec=args.lane_spec,
            )
            logger.info(f"\nExported to: {export_result.output_path}")
            logger.info(f"Worksheet: {export_result.worksheet_name}")
            logger.info(f"Rows written: {export_result.rows_written}")

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


def handle_advanced_stats(db: DatabaseManager, args: argparse.Namespace) -> int:
    """Handle advanced-stats command.

    Args:
        db: DatabaseManager instance
        args: Parsed arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        by_ubb_position = getattr(args, "by_ubb_position", False)
        selector = LaneSelector.from_spec(args.lane_spec, normalize_by_ubb=by_ubb_position)
        engine = QueryEngine(db)

        result = engine.query_aggregated_host_stats(selector, train_speeds=args.speeds)

        # Terminal output (if no Excel export or if verbose)
        if not args.excel_output or args.verbose:
            renderer = TableRenderer()
            output = renderer.render_aggregated_host_stats(result)
            print(output)

        # Excel export (if requested)
        if args.excel_output:
            exporter = ExcelExporter(db)
            color_scheme = _get_color_scheme(args.color_scheme, BER_COLOR_SCHEMES)
            export_result = exporter.export_advanced_stats(
                result,
                args.excel_output,
                lane_spec=args.lane_spec,
                color_scheme=color_scheme,
            )
            logger.info(f"\nExported to: {export_result.output_path}")
            logger.info(f"Worksheet: {export_result.worksheet_name}")
            logger.info(f"Rows written: {export_result.rows_written}")

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


def handle_plot(db: DatabaseManager, args: argparse.Namespace) -> int:
    """Handle plot command.

    Args:
        db: DatabaseManager instance
        args: Parsed arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        selector = LaneSelector.from_spec(args.lane_spec)
        engine = QueryEngine(db)

        result = engine.query_ber_plot(selector, train_speeds=args.speeds)

        # Terminal output (if no Excel export or if verbose)
        if not args.excel_output or args.verbose:
            renderer = TableRenderer()
            output = renderer.render_ber_plot(result)
            print(output)

        # Excel export (if requested)
        if args.excel_output:
            exporter = ExcelExporter(db)
            export_result = exporter.export_ber_plot(
                result,
                args.excel_output,
                lane_spec=args.lane_spec,
            )
            logger.info(f"\nExported to: {export_result.output_path}")
            logger.info(f"Worksheet: {export_result.worksheet_name}")
            logger.info(f"Rows written: {export_result.rows_written}")

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

        # Terminal output (if no Excel export or if verbose)
        if not args.excel_output or args.verbose:
            print("\nDatabase Information:")
            print(f"  Database: {db.db_path}")
            print(f"  Total samples: {stats.total_samples:,}")
            print(f"  Total tests: {stats.total_tests:,}")
            print(f"  Unique systems: {stats.unique_hosts}")
            print(f"  Train speeds: {', '.join(str(s) for s in stats.unique_speeds)}")
            print(f"  Date range: {stats.date_range[0]} to {stats.date_range[1]}")
            print(f"\n  Status breakdown:")
            for status, count in stats.status_breakdown.items():
                percentage = (count / stats.total_samples * 100) if stats.total_samples > 0 else 0
                print(f"    {status}: {count:,} ({percentage:.1f}%)")
            print(f"\n  Total ingestions: {stats.total_ingestions}\n")

        # Excel export (if requested)
        if args.excel_output:
            exporter = ExcelExporter(db)
            export_result = exporter.export_database_info(
                stats,
                args.excel_output,
            )
            logger.info(f"\nExported to: {export_result.output_path}")
            logger.info(f"Worksheet: {export_result.worksheet_name}")
            logger.info(f"Rows written: {export_result.rows_written}")

        return 0

    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
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
        shell = AnalysisShell(engine)

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
        if args.command in ["ingest", "stats", "threshold", "custom", "training", "histogram", "advanced-stats", "plot"]:
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
    elif args.command == "histogram":
        return handle_histogram(db, args)
    elif args.command == "advanced-stats":
        return handle_advanced_stats(db, args)
    elif args.command == "plot":
        return handle_plot(db, args)
    elif args.command == "info":
        return handle_info(db, args)
    elif args.command == "shell":
        return handle_shell(db, args)
    else:
        logger.error("No command specified. Use --help for usage information.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
