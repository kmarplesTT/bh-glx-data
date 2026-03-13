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


# ANSI 8-bit color codes for heatmap visualization
# 5-step color scale: Green → Yellow-Green → Yellow → Orange → Red
GREEN = "color(46)"           # #00FF00 - Step 1: Excellent/No issues
YELLOW_GREEN = "color(154)"   # #ADFF2F - Step 2: Good/Minor issues
YELLOW = "color(226)"         # #FFFF00 - Step 3: Caution/Moderate issues
ORANGE = "color(214)"         # #FFA500 - Step 4: Warning/Significant issues
RED = "color(196)"            # #FF0000 - Step 5: Critical/Severe issues


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
        thresholds=[(0, GREEN), (1, YELLOW_GREEN), (11, YELLOW), (25, ORANGE), (50, RED)],
        default_color=RED,
    ),
    "strict": ColorScheme(
        thresholds=[(0, GREEN), (1, YELLOW), (5, RED)],
        default_color=RED,
    ),
    "relaxed": ColorScheme(
        thresholds=[(0, GREEN), (5, YELLOW_GREEN), (20, YELLOW), (50, ORANGE), (100, RED)],
        default_color=RED,
    ),
}

# Built-in BER heatmap color schemes
BER_COLOR_SCHEMES = {
    "default": ColorScheme(
        thresholds=[(1e-8, GREEN), (5e-8, YELLOW_GREEN), (1e-7, YELLOW), (5e-7, ORANGE), (1e-6, RED)],
        default_color=RED,
    ),
    "sensitive": ColorScheme(
        thresholds=[(1e-9, GREEN), (5e-9, YELLOW_GREEN), (1e-8, YELLOW), (5e-8, ORANGE), (1e-7, RED)],
        default_color=RED,
    ),
    "tolerant": ColorScheme(
        thresholds=[(1e-6, GREEN), (5e-6, YELLOW_GREEN), (1e-5, YELLOW), (5e-5, ORANGE), (1e-4, RED)],
        default_color=RED,
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
        table.add_column("Avg BER", justify="right")
        table.add_column("Max BER", justify="right")
        table.add_column("High BER", justify="right", style="red")
        table.add_column("Samples", justify="right", style="green")

        # Group lanes by bus_id and eth_id for proper sectioning
        grouped_lanes = self._group_lanes_by_bus_and_eth(stats.lane_stats.keys())

        prev_bus_id = None
        for bus_id in sorted(grouped_lanes.keys()):
            # Add thick separator (double line) between different bus_ids
            if prev_bus_id is not None:
                # Add an empty row styled as a separator for thick line effect
                table.add_row("", "", "", "", "", "", end_section=True)

            prev_eth_id = None
            for eth_id in sorted(grouped_lanes[bus_id].keys()):
                # Add thin separator between different eth_ids within same bus_id
                if prev_eth_id is not None:
                    # Mark end of previous eth_id section with a line
                    pass  # The previous row already has end_section=True

                # Add all lanes for this eth_id
                lane_ids = sorted(grouped_lanes[bus_id][eth_id])
                for i, lane_id in enumerate(lane_ids):
                    lane_stat = stats.lane_stats[lane_id]

                    min_ber_str = self._format_ber(lane_stat.min_ber)
                    avg_ber_str = self._format_ber(lane_stat.avg_ber)
                    max_ber_str = self._format_ber(lane_stat.max_ber)
                    high_ber_str = str(lane_stat.high_ber_count) if lane_stat.high_ber_count > 0 else "-"

                    # Add separator line after last lane of each eth_id group
                    is_last_in_eth = (i == len(lane_ids) - 1)

                    table.add_row(
                        lane_id,
                        min_ber_str,
                        avg_ber_str,
                        max_ber_str,
                        high_ber_str,
                        str(lane_stat.sample_count),
                        end_section=is_last_in_eth,
                    )

                prev_eth_id = eth_id

            prev_bus_id = bus_id

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

        # Group lanes by bus_id and eth_id for proper sectioning
        grouped_lanes = self._group_lanes_by_bus_and_eth(counts.lane_counts.keys())

        prev_bus_id = None
        for bus_id in sorted(grouped_lanes.keys()):
            # Add thick separator (double line) between different bus_ids
            if prev_bus_id is not None:
                # Add an empty row styled as a separator for thick line effect
                table.add_row("", "", end_section=True)

            prev_eth_id = None
            for eth_id in sorted(grouped_lanes[bus_id].keys()):
                # Add thin separator between different eth_ids within same bus_id
                if prev_eth_id is not None:
                    # Mark end of previous eth_id section with a line
                    pass  # The previous row already has end_section=True

                # Add all lanes for this eth_id
                lane_ids = sorted(grouped_lanes[bus_id][eth_id])
                for i, lane_id in enumerate(lane_ids):
                    count = counts.lane_counts[lane_id]

                    # Add separator line after last lane of each eth_id group
                    is_last_in_eth = (i == len(lane_ids) - 1)

                    table.add_row(lane_id, str(count), end_section=is_last_in_eth)

                prev_eth_id = eth_id

            prev_bus_id = bus_id

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

    def _group_lanes_by_bus_and_eth(self, lane_ids) -> dict:
        """Group lane IDs by bus_id and eth_id.

        Args:
            lane_ids: Iterable of lane ID strings (format: "bus_id/eth_id/laneN")

        Returns:
            Nested dict: {bus_id: {eth_id: [lane_ids]}}
        """
        grouped = {}
        for lane_id in lane_ids:
            parts = lane_id.split("/")
            if len(parts) >= 3:
                bus_id = parts[0]
                eth_id = parts[1]

                if bus_id not in grouped:
                    grouped[bus_id] = {}
                if eth_id not in grouped[bus_id]:
                    grouped[bus_id][eth_id] = []

                grouped[bus_id][eth_id].append(lane_id)

        return grouped

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
        metric: str = "max",
        color_scheme: Optional[ColorScheme] = None,
    ) -> str:
        """Render BER statistics as heat map.

        Args:
            stats: BER statistics to visualize
            metric: "min", "max", "avg", or "high_ber"
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
                count_str = f"{count:4d}" if count < 1000 else "999+"

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
            metric: "min", "max", "avg", or "high_ber"
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
                elif metric == "avg":
                    value = lane_stat.avg_ber
                else:  # high_ber
                    value = lane_stat.high_ber_count

                key = (bus_id, eth_id)
                if key not in grouped:
                    grouped[key] = {}
                grouped[key][lane_num] = value

        title = f"BER Statistics - {metric.upper()} Heatmap"
        lines = [title, ""]

        # Determine if we're showing counts or BER values
        is_count_metric = (metric == "high_ber")

        # Render each port
        for (bus_id, eth_id), lane_values in sorted(grouped.items()):
            port_line = f"{bus_id}/{eth_id}  "

            # Render 8 lanes
            for lane_num in range(8):
                value = lane_values.get(lane_num)

                if value is None:
                    if is_count_metric:
                        # Treat None as 0 for count metrics and use same color scheme
                        value_str = "   0"
                        color = self._get_color_for_value(0, self.count_colors)
                        style = color
                    else:
                        # For BER metrics, show as missing data
                        value_str = "  -  "
                        style = "dim"
                elif is_count_metric:
                    # For high_ber counts, use count color scheme
                    value_str = f"{int(value):4d}" if value < 1000 else "999+"
                    color = self._get_color_for_value(value, scheme)
                    style = color
                else:
                    # For BER values
                    value_str = f"{value:.1e}"
                    color = self._get_color_for_value(value, scheme)
                    style = color

                # Apply style to output
                port_line += f"[{style}]{value_str}[/]  "

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

        Thresholds define upper bounds (exclusive). For example:
        thresholds=[(1e-12, "green"), (1e-7, "yellow"), (1e-6, "bright_yellow")]
        means:
        - value <= 1e-12: green
        - 1e-12 < value <= 1e-7: yellow
        - 1e-7 < value <= 1e-6: bright_yellow
        - value > 1e-6: default_color

        Args:
            value: Value to color
            color_scheme: Color scheme with thresholds

        Returns:
            Rich color name
        """
        # Sort thresholds in ascending order
        sorted_thresholds = sorted(color_scheme.thresholds)

        # Find appropriate color based on thresholds
        for threshold, threshold_color in sorted_thresholds:
            if value <= threshold:
                return threshold_color

        # Value exceeds all thresholds
        return color_scheme.default_color

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

        legend_str = "  ".join(legend_parts)
        return legend_str

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

        legend_str = "  ".join(legend_parts)
        return legend_str
