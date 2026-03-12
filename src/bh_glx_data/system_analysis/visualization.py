"""Visualization module for system analysis.

This module provides table and heatmap rendering with configurable color schemes
for displaying query results.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

from rich.console import Console
from rich.table import Table

from bh_glx_data.system_analysis.query_engine import (
    BERStatistics,
    CustomThresholdCounts,
    ThresholdExceededCounts,
    TrainingFailureCounts,
)

logger = logging.getLogger(__name__)


@dataclass
class ColorScheme:
    """Color scheme configuration for heat maps.

    Attributes:
        thresholds: List of (value, color) tuples defining color ranges
        default_color: Color to use when value exceeds all thresholds
    """

    thresholds: List[Tuple[float, str]]
    default_color: str

    @classmethod
    def from_config(cls, config: dict) -> "ColorScheme":
        """Load color scheme from configuration.

        Args:
            config: Dictionary with "thresholds" and "default_color" keys

        Returns:
            ColorScheme instance
        """
        thresholds = [(t["value"], t["color"]) for t in config.get("thresholds", [])]
        default_color = config.get("default_color", "red")
        return cls(thresholds=thresholds, default_color=default_color)


# Built-in count heatmap color schemes
COUNT_COLOR_SCHEMES = {
    "default": ColorScheme(
        thresholds=[(0, "green"), (1, "yellow"), (11, "bright_yellow"), (50, "red")],
        default_color="bright_red",
    ),
    "strict": ColorScheme(
        thresholds=[(0, "green"), (1, "red")],
        default_color="red",
    ),
    "relaxed": ColorScheme(
        thresholds=[(0, "green"), (5, "yellow"), (20, "bright_yellow"), (100, "red")],
        default_color="bright_red",
    ),
}

# Built-in BER heatmap color schemes
BER_COLOR_SCHEMES = {
    "default": ColorScheme(
        thresholds=[(0, "green"), (1e-12, "yellow"), (1e-10, "bright_yellow"), (1e-8, "red")],
        default_color="bright_red",
    ),
    "sensitive": ColorScheme(
        thresholds=[(0, "green"), (1e-13, "yellow"), (1e-11, "bright_yellow"), (1e-9, "red")],
        default_color="bright_red",
    ),
    "tolerant": ColorScheme(
        thresholds=[(0, "green"), (1e-11, "yellow"), (1e-9, "bright_yellow"), (1e-7, "red")],
        default_color="bright_red",
    ),
}


class TableRenderer:
    """Render query results as formatted tables using Rich library."""

    def __init__(self):
        """Initialize table renderer."""
        self.console = Console()

    def render_ber_statistics(self, stats: BERStatistics) -> str:
        """Render BER statistics as table.

        Args:
            stats: BER statistics to render

        Returns:
            Formatted table string
        """
        table = Table(title="BER Statistics", show_header=True, header_style="bold cyan")

        table.add_column("Lane", style="dim")
        table.add_column("Min BER", justify="right")
        table.add_column("Max BER", justify="right")
        table.add_column("Avg BER", justify="right")
        table.add_column("Samples", justify="right", style="green")

        # Sort lane IDs for consistent output
        for lane_id in sorted(stats.lane_stats.keys()):
            lane_stat = stats.lane_stats[lane_id]

            min_ber_str = self._format_ber(lane_stat.min_ber)
            max_ber_str = self._format_ber(lane_stat.max_ber)
            avg_ber_str = self._format_ber(lane_stat.avg_ber)

            table.add_row(
                lane_id,
                min_ber_str,
                max_ber_str,
                avg_ber_str,
                str(lane_stat.sample_count),
            )

        # Add footer with metadata
        speeds_str = ", ".join(str(s) for s in stats.train_speeds) if stats.train_speeds else "all"
        footer = (
            f"Tests: {stats.num_tests}  |  "
            f"Systems: {stats.num_systems}  |  "
            f"Speeds: {speeds_str}"
        )

        # Render to string
        with self.console.capture() as capture:
            self.console.print(table)
            self.console.print(footer, style="dim")

        return capture.get()

    def render_count_table(
        self,
        counts: Union[ThresholdExceededCounts, CustomThresholdCounts, TrainingFailureCounts],
    ) -> str:
        """Render counts as table.

        Args:
            counts: Count data to render

        Returns:
            Formatted table string
        """
        # Determine table title based on type
        if isinstance(counts, ThresholdExceededCounts):
            title = "BER Threshold Exceeded Counts"
        elif isinstance(counts, CustomThresholdCounts):
            title = f"Custom Threshold Counts (threshold={counts.threshold:.2e})"
        elif isinstance(counts, TrainingFailureCounts):
            title = "Training Failure Counts"
        else:
            title = "Lane Counts"

        table = Table(title=title, show_header=True, header_style="bold cyan")

        table.add_column("Lane", style="dim")
        table.add_column("Count", justify="right", style="yellow")

        # Sort lane IDs
        for lane_id in sorted(counts.lane_counts.keys()):
            count = counts.lane_counts[lane_id]
            table.add_row(lane_id, str(count))

        # Add footer
        speeds_str = ", ".join(str(s) for s in counts.train_speeds) if counts.train_speeds else "all"
        footer = (
            f"Tests: {counts.num_tests}  |  "
            f"Systems: {counts.num_systems}  |  "
            f"Speeds: {speeds_str}"
        )

        # Render to string
        with self.console.capture() as capture:
            self.console.print(table)
            self.console.print(footer, style="dim")

        return capture.get()

    def _format_ber(self, value: Optional[float]) -> str:
        """Format BER value for display.

        Args:
            value: BER value

        Returns:
            Formatted string (scientific notation or "-" for None)
        """
        if value is None:
            return "-"
        return f"{value:.2e}"


class HeatMapRenderer:
    """Render query results as heat maps with configurable color schemes."""

    def __init__(
        self,
        output_format: str = "terminal",
        count_color_scheme: Optional[ColorScheme] = None,
        ber_color_scheme: Optional[ColorScheme] = None,
    ):
        """Initialize heatmap renderer.

        Args:
            output_format: "terminal" (ANSI colors) or "html"
            count_color_scheme: Color scheme for count heatmaps (None = use default)
            ber_color_scheme: Color scheme for BER heatmaps (None = use default)
        """
        self.format = output_format
        self.count_colors = count_color_scheme or COUNT_COLOR_SCHEMES["default"]
        self.ber_colors = ber_color_scheme or BER_COLOR_SCHEMES["default"]
        self.console = Console()

    def render_count_heatmap(
        self,
        counts: Union[ThresholdExceededCounts, TrainingFailureCounts, CustomThresholdCounts],
        color_scale: str = "linear",
        color_scheme: Optional[ColorScheme] = None,
    ) -> str:
        """Render counts as color-coded heat map.

        Args:
            counts: Count data to visualize
            color_scale: "linear" or "log" (for value interpolation)
            color_scheme: Override instance color scheme

        Returns:
            Formatted heatmap string
        """
        scheme = color_scheme or self.count_colors

        if self.format == "terminal":
            return self._render_terminal_count_heatmap(counts, scheme)
        else:
            raise NotImplementedError(f"Output format '{self.format}' not yet implemented")

    def render_ber_heatmap(
        self,
        stats: BERStatistics,
        metric: str = "avg",
        color_scheme: Optional[ColorScheme] = None,
    ) -> str:
        """Render BER statistics as heat map.

        Args:
            stats: BER statistics to visualize
            metric: "min", "max", or "avg"
            color_scheme: Override instance color scheme

        Returns:
            Formatted heatmap string
        """
        scheme = color_scheme or self.ber_colors

        if self.format == "terminal":
            return self._render_terminal_ber_heatmap(stats, metric, scheme)
        else:
            raise NotImplementedError(f"Output format '{self.format}' not yet implemented")

    def _render_terminal_count_heatmap(
        self,
        counts: Union[ThresholdExceededCounts, TrainingFailureCounts, CustomThresholdCounts],
        scheme: ColorScheme,
    ) -> str:
        """Render count heatmap for terminal with ANSI colors.

        Args:
            counts: Count data
            scheme: Color scheme to use

        Returns:
            Formatted string with ANSI colors
        """
        # Group by bus_id/eth_id
        grouped = {}
        for lane_id, count in counts.lane_counts.items():
            parts = lane_id.split("/")
            if len(parts) >= 3:
                bus_id = parts[0]
                eth_id = parts[1]
                lane_num = int(parts[2].replace("lane", ""))

                key = (bus_id, eth_id)
                if key not in grouped:
                    grouped[key] = {}
                grouped[key][lane_num] = count

        # Determine title
        if isinstance(counts, ThresholdExceededCounts):
            title = "BER Threshold Exceeded - Count Heatmap"
        elif isinstance(counts, CustomThresholdCounts):
            title = f"Custom Threshold Count Heatmap (threshold={counts.threshold:.2e})"
        elif isinstance(counts, TrainingFailureCounts):
            title = "Training Failures - Count Heatmap"
        else:
            title = "Count Heatmap"

        lines = [title, ""]

        # Render each port
        for (bus_id, eth_id), lane_counts in sorted(grouped.items()):
            port_line = f"{bus_id}/{eth_id}  "

            # Render 8 lanes
            for lane_num in range(8):
                count = lane_counts.get(lane_num, 0)
                color = self._get_color_for_value(count, scheme)

                # Format count value
                count_str = f"{count:3d}" if count < 1000 else "999+"

                # Add colored value
                port_line += f"[{color}]{count_str}[/]  "

            lines.append(port_line)

        # Add legend
        lines.append("")
        lines.append(self._format_count_legend(scheme))

        # Add metadata
        speeds_str = ", ".join(str(s) for s in counts.train_speeds) if counts.train_speeds else "all"
        lines.append("")
        lines.append(f"Tests: {counts.num_tests}  |  Systems: {counts.num_systems}  |  Speeds: {speeds_str}")

        # Render with Rich console
        with self.console.capture() as capture:
            for line in lines:
                self.console.print(line)

        return capture.get()

    def _render_terminal_ber_heatmap(
        self,
        stats: BERStatistics,
        metric: str,
        scheme: ColorScheme,
    ) -> str:
        """Render BER heatmap for terminal with ANSI colors.

        Args:
            stats: BER statistics
            metric: "min", "max", or "avg"
            scheme: Color scheme to use

        Returns:
            Formatted string with ANSI colors
        """
        # Group by bus_id/eth_id
        grouped = {}
        for lane_id, lane_stat in stats.lane_stats.items():
            parts = lane_id.split("/")
            if len(parts) >= 3:
                bus_id = parts[0]
                eth_id = parts[1]
                lane_num = int(parts[2].replace("lane", ""))

                # Get metric value
                if metric == "min":
                    value = lane_stat.min_ber
                elif metric == "max":
                    value = lane_stat.max_ber
                else:  # avg
                    value = lane_stat.avg_ber

                key = (bus_id, eth_id)
                if key not in grouped:
                    grouped[key] = {}
                grouped[key][lane_num] = value

        title = f"BER Statistics - {metric.upper()} Heatmap"
        lines = [title, ""]

        # Render each port
        for (bus_id, eth_id), lane_values in sorted(grouped.items()):
            port_line = f"{bus_id}/{eth_id}  "

            # Render 8 lanes
            for lane_num in range(8):
                value = lane_values.get(lane_num)

                if value is None:
                    value_str = "  -  "
                    color = "dim"
                else:
                    value_str = f"{value:.1e}"
                    color = self._get_color_for_value(value, scheme)

                port_line += f"[{color}]{value_str}[/]  "

            lines.append(port_line)

        # Add legend
        lines.append("")
        lines.append(self._format_ber_legend(scheme))

        # Add metadata
        speeds_str = ", ".join(str(s) for s in stats.train_speeds) if stats.train_speeds else "all"
        lines.append("")
        lines.append(f"Tests: {stats.num_tests}  |  Systems: {stats.num_systems}  |  Speeds: {speeds_str}")

        # Render with Rich console
        with self.console.capture() as capture:
            for line in lines:
                self.console.print(line)

        return capture.get()

    def _get_color_for_value(
        self,
        value: float,
        color_scheme: ColorScheme,
    ) -> str:
        """Determine color for a value based on threshold ranges.

        Args:
            value: Value to color
            color_scheme: Color scheme with thresholds

        Returns:
            Rich color name
        """
        # Find appropriate color based on thresholds
        color = color_scheme.default_color

        for threshold, threshold_color in sorted(color_scheme.thresholds, reverse=True):
            if value >= threshold:
                color = threshold_color
                break

        return color

    def _format_count_legend(self, scheme: ColorScheme) -> str:
        """Format legend for count heatmap.

        Args:
            scheme: Color scheme

        Returns:
            Legend string
        """
        legend_parts = []

        # Sort thresholds
        sorted_thresholds = sorted(scheme.thresholds)

        for i, (threshold, color) in enumerate(sorted_thresholds):
            if i == 0:
                legend_parts.append(f"[{color}]= {threshold}[/]")
            else:
                prev_threshold = sorted_thresholds[i - 1][0]
                legend_parts.append(f"[{color}]{prev_threshold + 1}-{threshold}[/]")

        # Add final range
        if sorted_thresholds:
            last_threshold = sorted_thresholds[-1][0]
            legend_parts.append(f"[{scheme.default_color}]> {last_threshold}[/]")

        return "  ".join(legend_parts)

    def _format_ber_legend(self, scheme: ColorScheme) -> str:
        """Format legend for BER heatmap.

        Args:
            scheme: Color scheme

        Returns:
            Legend string
        """
        legend_parts = []

        # Sort thresholds
        sorted_thresholds = sorted(scheme.thresholds)

        for threshold, color in sorted_thresholds:
            if threshold == 0:
                legend_parts.append(f"[{color}]= 0[/]")
            else:
                legend_parts.append(f"[{color}]> {threshold:.0e}[/]")

        return "  ".join(legend_parts)
