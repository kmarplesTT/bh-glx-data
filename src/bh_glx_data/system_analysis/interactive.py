"""Interactive shell module for system analysis.

This module provides a REPL interface for exploratory analysis with
command history and result export capabilities.
"""

import logging
import shlex
from pathlib import Path
from typing import Optional, Union

from bh_glx_data.system_analysis.export import ExcelExporter
from bh_glx_data.system_analysis.query_engine import (
    BERStatistics,
    CustomThresholdCounts,
    LaneSelector,
    QueryEngine,
    ThresholdExceededCounts,
    TrainingFailureCounts,
)
from bh_glx_data.system_analysis.visualization import (
    BER_COLOR_SCHEMES,
    COUNT_COLOR_SCHEMES,
    HeatMapRenderer,
    TableRenderer,
)

logger = logging.getLogger(__name__)


class AnalysisShell:
    """Interactive shell for system analysis.

    This class provides a REPL interface for querying and analyzing
    PRBS test data with command history and Excel export.

    Attributes:
        query_engine: QueryEngine instance
        exporter: ExcelExporter instance
        renderer: TableRenderer instance
        history: List of executed commands
        last_result: Most recent query result
    """

    def __init__(self, query_engine: QueryEngine):
        """Initialize analysis shell.

        Args:
            query_engine: QueryEngine instance
        """
        self.query_engine = query_engine
        self.exporter = ExcelExporter(query_engine.db)
        self.renderer = TableRenderer()
        self.history = []
        self.last_result: Optional[
            Union[BERStatistics, ThresholdExceededCounts, CustomThresholdCounts, TrainingFailureCounts]
        ] = None

    def run(self) -> None:
        """Start interactive shell."""
        print("BH Galaxy System Analysis - Interactive Shell")
        print("Type 'help' for commands, 'exit' to quit\n")

        while True:
            try:
                # Get user input
                command = input("bh-analyze> ").strip()

                if not command:
                    continue

                # Add to history
                self.history.append(command)

                # Handle exit
                if command.lower() in ["exit", "quit", "q"]:
                    print("Exiting...")
                    break

                # Handle command
                self._handle_command(command)

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except EOFError:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
                logger.exception("Shell command error")

    def _handle_command(self, command: str) -> None:
        """Parse and execute shell command.

        Args:
            command: Command string to execute
        """
        # Parse command
        try:
            parts = shlex.split(command)
        except ValueError as e:
            print(f"Parse error: {e}")
            return

        if not parts:
            return

        cmd = parts[0].lower()

        # Route to handler
        if cmd == "help":
            self._handle_help()
        elif cmd == "stats":
            self._handle_stats(parts[1:])
        elif cmd == "threshold":
            self._handle_threshold(parts[1:])
        elif cmd == "custom":
            self._handle_custom(parts[1:])
        elif cmd == "training":
            self._handle_training(parts[1:])
        elif cmd == "histogram":
            self._handle_histogram(parts[1:])
        elif cmd == "advanced-stats":
            self._handle_advanced_stats(parts[1:])
        elif cmd == "systems":
            self._handle_systems()
        elif cmd == "speeds":
            self._handle_speeds()
        elif cmd == "info":
            self._handle_info(parts[1:])
        elif cmd == "history":
            self._handle_history()
        else:
            print(f"Unknown command: {cmd}")
            print("Type 'help' for available commands")

    def _handle_help(self) -> None:
        """Display help message."""
        help_text = """
Available commands:

  stats <lane-spec> [--speed SPEED] [--format FORMAT] [--statistic STAT] [--excel-output FILE] [-u|--by-ubb-position]
                                               - Show BER statistics
  threshold <lane-spec> [--speed SPEED] [--format FORMAT] [--excel-output FILE] [-u|--by-ubb-position]
                                               - Show BER threshold exceeded
  custom <lane-spec> <threshold> [--speed SPEED] [--format FORMAT] [--excel-output FILE] [-u|--by-ubb-position]
                                               - Show custom threshold counts
  training <lane-spec> [--speed SPEED] [--format FORMAT] [--excel-output FILE] [-u|--by-ubb-position]
                                               - Show training failures
  histogram <lane-spec> [--speed SPEED] [--excel-output FILE] [-u|--by-ubb-position]
                                               - Show BER histogram
  advanced-stats <lane-spec> [--speed SPEED] [--excel-output FILE] [-u|--by-ubb-position]
                                               - Show aggregated host statistics
  systems                                      - List all systems
  speeds                                       - List all train speeds
  info [--excel-output FILE]                  - Show database info
  history                                      - Show command history
  help                                         - Show this help
  exit                                         - Exit shell

Format options:
  table         - Table format (default)
  heatmap       - Heatmap format

Statistic options (for heatmap):
  max           - Maximum BER (default)
  avg           - Average BER
  min           - Minimum BER
  high_ber      - High BER count (BER >= 0.1)
  variance      - Average BER with variance indicators

Excel export:
  --excel-output FILE    - Export results to Excel file

UBB normalization:
  --by-ubb-position/-u   - Aggregate by chip position (U1-U8) instead of bus_id
                           Combines data from all 4 UBBs for 4x sample size

Lane specifications:
  all                      - All lanes on all systems
  01:00.0/ETH07           - Specific port (all lanes)
  01:00.0/*               - All ports on bus_id
  system/01:00.0/ETH07    - Specific system and port

UBB mode lane specs (with --by-ubb-position):
  U1/ETH07                - Chip position U1, ETH07 (all UBBs)
  U1/ETH07/4              - Chip position U1, ETH07, lane 4
  U1/*                    - All ports on chip position U1

Examples:
  stats all --speed 200
  stats all --speed 200 --format heatmap --statistic avg
  stats all --excel-output analysis.xlsx
  stats all --by-ubb-position
  stats U1/ETH07 --by-ubb-position --format heatmap
  threshold 01:00.0/ETH07 --format heatmap --excel-output results.xlsx
  custom 01:00.0/* 1e-10 --speed 200
  training all --excel-output failures.xlsx
  histogram 01:00.0/ETH07 --excel-output hist.xlsx
  advanced-stats all --excel-output stats.xlsx
  info --excel-output db_info.xlsx
"""
        print(help_text)

    def _handle_stats(self, args: list) -> None:
        """Handle stats command.

        Args:
            args: Command arguments
        """
        if not args:
            print("Usage: stats <lane-spec> [--speed SPEED] [--format FORMAT] [--statistic STAT] [--excel-output FILE] [--by-ubb-position|-u]")
            return

        lane_spec = args[0]
        speeds = self._parse_speeds(args[1:])
        output_format = self._parse_format(args[1:])
        statistic = self._parse_statistic(args[1:])
        excel_output = self._parse_excel_output(args[1:])
        by_ubb_position = self._parse_by_ubb_position(args[1:])

        try:
            selector = LaneSelector.from_spec(lane_spec, normalize_by_ubb=by_ubb_position)
            result = self.query_engine.query_ber_statistics(selector, train_speeds=speeds)

            self.last_result = result

            # Terminal output (always show unless only exporting)
            if not excel_output or True:  # Always show terminal output in shell
                if output_format == "heatmap":
                    heatmap_renderer = HeatMapRenderer(ber_color_scheme=BER_COLOR_SCHEMES["default"])
                    print(heatmap_renderer.render_ber_heatmap(result, metric=statistic))
                else:
                    print(self.renderer.render_ber_statistics(result))

            # Excel export (if requested)
            if excel_output:
                export_result = self.exporter.export_ber_statistics(
                    result,
                    excel_output,
                    lane_spec=lane_spec,
                    format=output_format,
                    color_scheme=BER_COLOR_SCHEMES["default"],
                )
                print(f"\nExported to: {export_result.output_path}")
                print(f"Worksheet: {export_result.worksheet_name}")
                print(f"Rows written: {export_result.rows_written}")

        except Exception as e:
            print(f"Error: {e}")

    def _handle_threshold(self, args: list) -> None:
        """Handle threshold command.

        Args:
            args: Command arguments
        """
        if not args:
            print("Usage: threshold <lane-spec> [--speed SPEED] [--format FORMAT] [--excel-output FILE] [--by-ubb-position|-u]")
            return

        lane_spec = args[0]
        speeds = self._parse_speeds(args[1:])
        output_format = self._parse_format(args[1:])
        excel_output = self._parse_excel_output(args[1:])
        by_ubb_position = self._parse_by_ubb_position(args[1:])

        try:
            selector = LaneSelector.from_spec(lane_spec, normalize_by_ubb=by_ubb_position)
            result = self.query_engine.query_ber_threshold_exceeded(selector, train_speeds=speeds)

            self.last_result = result

            # Terminal output
            if output_format == "heatmap":
                heatmap_renderer = HeatMapRenderer(count_color_scheme=COUNT_COLOR_SCHEMES["default"])
                print(heatmap_renderer.render_count_heatmap(result))
            else:
                print(self.renderer.render_count_table(result))

            # Excel export (if requested)
            if excel_output:
                export_result = self.exporter.export_count_data(
                    result,
                    excel_output,
                    lane_spec=lane_spec,
                    format=output_format,
                    color_scheme=COUNT_COLOR_SCHEMES["default"],
                )
                print(f"\nExported to: {export_result.output_path}")
                print(f"Worksheet: {export_result.worksheet_name}")
                print(f"Rows written: {export_result.rows_written}")

        except Exception as e:
            print(f"Error: {e}")

    def _handle_custom(self, args: list) -> None:
        """Handle custom command.

        Args:
            args: Command arguments
        """
        if len(args) < 2:
            print("Usage: custom <lane-spec> <threshold> [--speed SPEED] [--format FORMAT] [--excel-output FILE] [--by-ubb-position|-u]")
            return

        lane_spec = args[0]
        try:
            threshold = float(args[1])
        except ValueError:
            print(f"Invalid threshold: {args[1]}")
            return

        speeds = self._parse_speeds(args[2:])
        output_format = self._parse_format(args[2:])
        excel_output = self._parse_excel_output(args[2:])
        by_ubb_position = self._parse_by_ubb_position(args[2:])

        try:
            selector = LaneSelector.from_spec(lane_spec, normalize_by_ubb=by_ubb_position)
            result = self.query_engine.query_custom_ber_threshold(
                selector, threshold, train_speeds=speeds
            )

            self.last_result = result

            # Terminal output
            if output_format == "heatmap":
                heatmap_renderer = HeatMapRenderer(count_color_scheme=COUNT_COLOR_SCHEMES["default"])
                print(heatmap_renderer.render_count_heatmap(result))
            else:
                print(self.renderer.render_count_table(result))

            # Excel export (if requested)
            if excel_output:
                export_result = self.exporter.export_count_data(
                    result,
                    excel_output,
                    lane_spec=lane_spec,
                    format=output_format,
                    color_scheme=COUNT_COLOR_SCHEMES["default"],
                )
                print(f"\nExported to: {export_result.output_path}")
                print(f"Worksheet: {export_result.worksheet_name}")
                print(f"Rows written: {export_result.rows_written}")

        except Exception as e:
            print(f"Error: {e}")

    def _handle_training(self, args: list) -> None:
        """Handle training command.

        Args:
            args: Command arguments
        """
        if not args:
            print("Usage: training <lane-spec> [--speed SPEED] [--format FORMAT] [--excel-output FILE] [--by-ubb-position|-u]")
            return

        lane_spec = args[0]
        speeds = self._parse_speeds(args[1:])
        output_format = self._parse_format(args[1:])
        excel_output = self._parse_excel_output(args[1:])
        by_ubb_position = self._parse_by_ubb_position(args[1:])

        try:
            selector = LaneSelector.from_spec(lane_spec, normalize_by_ubb=by_ubb_position)
            result = self.query_engine.query_training_failures(selector, train_speeds=speeds)

            self.last_result = result

            # Terminal output
            if output_format == "heatmap":
                heatmap_renderer = HeatMapRenderer(count_color_scheme=COUNT_COLOR_SCHEMES["default"])
                print(heatmap_renderer.render_count_heatmap(result))
            else:
                print(self.renderer.render_count_table(result))

            # Excel export (if requested)
            if excel_output:
                export_result = self.exporter.export_count_data(
                    result,
                    excel_output,
                    lane_spec=lane_spec,
                    format=output_format,
                    color_scheme=COUNT_COLOR_SCHEMES["default"],
                )
                print(f"\nExported to: {export_result.output_path}")
                print(f"Worksheet: {export_result.worksheet_name}")
                print(f"Rows written: {export_result.rows_written}")

        except Exception as e:
            print(f"Error: {e}")

    def _handle_histogram(self, args: list) -> None:
        """Handle histogram command.

        Args:
            args: Command arguments
        """
        if not args:
            print("Usage: histogram <lane-spec> [--speed SPEED] [--excel-output FILE] [--by-ubb-position|-u]")
            return

        lane_spec = args[0]
        speeds = self._parse_speeds(args[1:])
        excel_output = self._parse_excel_output(args[1:])
        by_ubb_position = self._parse_by_ubb_position(args[1:])

        try:
            selector = LaneSelector.from_spec(lane_spec, normalize_by_ubb=by_ubb_position)
            result = self.query_engine.query_ber_histogram(selector, train_speeds=speeds)

            self.last_result = result

            # Terminal output
            heatmap_renderer = HeatMapRenderer()
            print(heatmap_renderer.render_ber_histogram(result, max_bar_width=50))

            # Excel export (if requested)
            if excel_output:
                export_result = self.exporter.export_histogram(
                    result,
                    excel_output,
                    lane_spec=lane_spec,
                )
                print(f"\nExported to: {export_result.output_path}")
                print(f"Worksheet: {export_result.worksheet_name}")
                print(f"Rows written: {export_result.rows_written}")

        except Exception as e:
            print(f"Error: {e}")

    def _handle_advanced_stats(self, args: list) -> None:
        """Handle advanced-stats command.

        Args:
            args: Command arguments
        """
        if not args:
            print("Usage: advanced-stats <lane-spec> [--speed SPEED] [--excel-output FILE] [--by-ubb-position|-u]")
            return

        lane_spec = args[0]
        speeds = self._parse_speeds(args[1:])
        excel_output = self._parse_excel_output(args[1:])
        by_ubb_position = self._parse_by_ubb_position(args[1:])

        try:
            selector = LaneSelector.from_spec(lane_spec, normalize_by_ubb=by_ubb_position)
            result = self.query_engine.query_aggregated_host_stats(selector, train_speeds=speeds)

            self.last_result = result

            # Terminal output
            print(self.renderer.render_aggregated_host_stats(result))

            # Excel export (if requested)
            if excel_output:
                export_result = self.exporter.export_advanced_stats(
                    result,
                    excel_output,
                    lane_spec=lane_spec,
                )
                print(f"\nExported to: {export_result.output_path}")
                print(f"Worksheet: {export_result.worksheet_name}")
                print(f"Rows written: {export_result.rows_written}")

        except Exception as e:
            print(f"Error: {e}")

    def _handle_systems(self) -> None:
        """Handle systems command."""
        try:
            hosts = self.query_engine.db.get_unique_hosts()
            print(f"\nUnique systems ({len(hosts)}):")
            for host in hosts:
                print(f"  {host}")
            print()

        except Exception as e:
            print(f"Error: {e}")

    def _handle_speeds(self) -> None:
        """Handle speeds command."""
        try:
            speeds = self.query_engine.db.get_unique_speeds()
            print(f"\nTrain speeds: {', '.join(str(s) for s in speeds)}\n")

        except Exception as e:
            print(f"Error: {e}")

    def _handle_info(self, args: list) -> None:
        """Handle info command.

        Args:
            args: Command arguments
        """
        excel_output = self._parse_excel_output(args)

        try:
            stats = self.query_engine.db.get_database_stats()

            # Terminal output
            print("\nDatabase Information:")
            print(f"  Database: {self.query_engine.db.db_path}")
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
            if excel_output:
                export_result = self.exporter.export_database_info(
                    stats,
                    excel_output,
                )
                print(f"Exported to: {export_result.output_path}")
                print(f"Worksheet: {export_result.worksheet_name}")
                print(f"Rows written: {export_result.rows_written}\n")

        except Exception as e:
            print(f"Error: {e}")


    def _handle_history(self) -> None:
        """Handle history command."""
        if not self.history:
            print("No command history")
            return

        print("\nCommand History:")
        for i, cmd in enumerate(self.history, start=1):
            print(f"  {i}. {cmd}")
        print()

    def _parse_speeds(self, args: list) -> Optional[list]:
        """Parse --speed arguments from command args.

        Args:
            args: Command arguments

        Returns:
            List of speeds or None if no --speed specified
        """
        speeds = []

        i = 0
        while i < len(args):
            if args[i] == "--speed" and i + 1 < len(args):
                try:
                    speed = int(args[i + 1])
                    speeds.append(speed)
                    i += 2
                except ValueError:
                    print(f"Warning: Invalid speed value: {args[i + 1]}")
                    i += 2
            else:
                i += 1

        return speeds if speeds else None

    def _parse_format(self, args: list) -> str:
        """Parse --format argument from command args.

        Args:
            args: Command arguments

        Returns:
            Format string ("table" or "heatmap"), defaults to "table"
        """
        i = 0
        while i < len(args):
            if args[i] == "--format" and i + 1 < len(args):
                return args[i + 1]
            i += 1

        return "table"

    def _parse_statistic(self, args: list) -> str:
        """Parse --statistic argument from command args.

        Args:
            args: Command arguments

        Returns:
            Statistic string ("min", "avg", "max", "high_ber"), defaults to "max"
        """
        i = 0
        while i < len(args):
            if args[i] == "--statistic" and i + 1 < len(args):
                return args[i + 1]
            i += 1

        return "max"

    def _parse_excel_output(self, args: list) -> Optional[Path]:
        """Parse --excel-output argument from command args.

        Args:
            args: Command arguments

        Returns:
            Path to Excel output file, or None if not specified
        """
        i = 0
        while i < len(args):
            if args[i] == "--excel-output" and i + 1 < len(args):
                return Path(args[i + 1])
            i += 1

        return None

    def _parse_by_ubb_position(self, args: list) -> bool:
        """Parse --by-ubb-position/-u flag from command args.

        Args:
            args: Command arguments

        Returns:
            True if flag is present, False otherwise
        """
        return "--by-ubb-position" in args or "-u" in args
