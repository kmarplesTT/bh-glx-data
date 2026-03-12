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
from bh_glx_data.system_analysis.visualization import TableRenderer

logger = logging.getLogger(__name__)


class AnalysisShell:
    """Interactive shell for system analysis.

    This class provides a REPL interface for querying and analyzing
    PRBS test data with command history and export capabilities.

    Attributes:
        query_engine: QueryEngine instance
        exporter: ExcelExporter instance
        renderer: TableRenderer instance
        history: List of executed commands
        last_result: Most recent query result
    """

    def __init__(self, query_engine: QueryEngine, exporter: ExcelExporter):
        """Initialize analysis shell.

        Args:
            query_engine: QueryEngine instance
            exporter: ExcelExporter instance
        """
        self.query_engine = query_engine
        self.exporter = exporter
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
        elif cmd == "systems":
            self._handle_systems()
        elif cmd == "speeds":
            self._handle_speeds()
        elif cmd == "info":
            self._handle_info()
        elif cmd == "export":
            self._handle_export(parts[1:])
        elif cmd == "history":
            self._handle_history()
        else:
            print(f"Unknown command: {cmd}")
            print("Type 'help' for available commands")

    def _handle_help(self) -> None:
        """Display help message."""
        help_text = """
Available commands:

  stats <lane-spec> [--speed SPEED]           - Show BER statistics
  threshold <lane-spec> [--speed SPEED]       - Show BER threshold exceeded
  custom <lane-spec> <threshold> [--speed]    - Show custom threshold counts
  training <lane-spec> [--speed SPEED]        - Show training failures
  systems                                      - List all systems
  speeds                                       - List all train speeds
  info                                         - Show database info
  export <format> [--output FILE]              - Export last result or database
  history                                      - Show command history
  help                                         - Show this help
  exit                                         - Exit shell

Export formats:
  excel         - Export last result to Excel
  excel-db      - Export entire database to Excel

Lane specifications:
  all                      - All lanes on all systems
  01:00.0/ETH07           - Specific port (all lanes)
  01:00.0/*               - All ports on bus_id
  system/01:00.0/ETH07    - Specific system and port

Examples:
  stats all --speed 200
  threshold 01:00.0/ETH07
  custom 01:00.0/* 1e-10 --speed 200
  training all
  export excel --output results.xlsx
"""
        print(help_text)

    def _handle_stats(self, args: list) -> None:
        """Handle stats command.

        Args:
            args: Command arguments
        """
        if not args:
            print("Usage: stats <lane-spec> [--speed SPEED]")
            return

        lane_spec = args[0]
        speeds = self._parse_speeds(args[1:])

        try:
            selector = LaneSelector.from_spec(lane_spec)
            result = self.query_engine.query_ber_statistics(selector, train_speeds=speeds)

            self.last_result = result
            print(self.renderer.render_ber_statistics(result))

        except Exception as e:
            print(f"Error: {e}")

    def _handle_threshold(self, args: list) -> None:
        """Handle threshold command.

        Args:
            args: Command arguments
        """
        if not args:
            print("Usage: threshold <lane-spec> [--speed SPEED]")
            return

        lane_spec = args[0]
        speeds = self._parse_speeds(args[1:])

        try:
            selector = LaneSelector.from_spec(lane_spec)
            result = self.query_engine.query_ber_threshold_exceeded(selector, train_speeds=speeds)

            self.last_result = result
            print(self.renderer.render_count_table(result))

        except Exception as e:
            print(f"Error: {e}")

    def _handle_custom(self, args: list) -> None:
        """Handle custom command.

        Args:
            args: Command arguments
        """
        if len(args) < 2:
            print("Usage: custom <lane-spec> <threshold> [--speed SPEED]")
            return

        lane_spec = args[0]
        try:
            threshold = float(args[1])
        except ValueError:
            print(f"Invalid threshold: {args[1]}")
            return

        speeds = self._parse_speeds(args[2:])

        try:
            selector = LaneSelector.from_spec(lane_spec)
            result = self.query_engine.query_custom_ber_threshold(
                selector, threshold, train_speeds=speeds
            )

            self.last_result = result
            print(self.renderer.render_count_table(result))

        except Exception as e:
            print(f"Error: {e}")

    def _handle_training(self, args: list) -> None:
        """Handle training command.

        Args:
            args: Command arguments
        """
        if not args:
            print("Usage: training <lane-spec> [--speed SPEED]")
            return

        lane_spec = args[0]
        speeds = self._parse_speeds(args[1:])

        try:
            selector = LaneSelector.from_spec(lane_spec)
            result = self.query_engine.query_training_failures(selector, train_speeds=speeds)

            self.last_result = result
            print(self.renderer.render_count_table(result))

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

    def _handle_info(self) -> None:
        """Handle info command."""
        try:
            stats = self.query_engine.db.get_database_stats()

            print("\nDatabase Information:")
            print(f"  Database: {self.query_engine.db.db_path}")
            print(f"  Total tests: {stats.total_tests:,}")
            print(f"  Unique systems: {stats.unique_hosts}")
            print(f"  Train speeds: {', '.join(str(s) for s in stats.unique_speeds)}")
            print(f"  Date range: {stats.date_range[0]} to {stats.date_range[1]}")
            print(f"\n  Status breakdown:")
            for status, count in stats.status_breakdown.items():
                percentage = (count / stats.total_tests * 100) if stats.total_tests > 0 else 0
                print(f"    {status}: {count:,} ({percentage:.1f}%)")
            print(f"\n  Total ingestions: {stats.total_ingestions}\n")

        except Exception as e:
            print(f"Error: {e}")

    def _handle_export(self, args: list) -> None:
        """Handle export command.

        Args:
            args: Command arguments
        """
        if not args:
            print("Usage: export <format> [--output FILE]")
            print("Formats: excel, excel-db")
            return

        format_type = args[0].lower()

        # Parse output path
        output_path = None
        for i, arg in enumerate(args):
            if arg == "--output" and i + 1 < len(args):
                output_path = Path(args[i + 1])
                break

        if format_type == "excel":
            if self.last_result is None:
                print("No query result to export. Run a query first.")
                return

            if output_path is None:
                output_path = Path("query_result.xlsx")

            try:
                self.exporter.export_query_result(self.last_result, output_path)
                print(f"Query result exported to: {output_path}")

            except Exception as e:
                print(f"Export failed: {e}")

        elif format_type == "excel-db":
            if output_path is None:
                output_path = Path("database_export.xlsx")

            try:
                result = self.exporter.export_full_database(output_path)
                print(
                    f"Database exported to: {result.output_path} "
                    f"({result.rows_exported:,} rows, {result.sheets_created} sheets)"
                )

            except Exception as e:
                print(f"Export failed: {e}")

        else:
            print(f"Unknown export format: {format_type}")
            print("Available formats: excel, excel-db")

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
