"""Unit tests for visualization module."""

import pytest

from bh_glx_data.system_analysis.query_engine import BERStatistics, LaneBERStats
from bh_glx_data.system_analysis.visualization import (
    BER_COLOR_SCHEMES,
    COUNT_COLOR_SCHEMES,
    ORANGE,
    ColorScheme,
    HeatMapRenderer,
    TableRenderer,
)


class TestColorScheme:
    """Test ColorScheme class."""

    def test_color_schemes_have_orange(self):
        """Test that full-spectrum color schemes include orange."""
        # Check BER color schemes (all should have full 5-step gradient)
        for scheme_name, scheme in BER_COLOR_SCHEMES.items():
            colors = [color for _, color in scheme.thresholds]
            assert ORANGE in colors, f"BER scheme '{scheme_name}' missing orange"

        # Check count color schemes (only default and relaxed have full gradient)
        # "strict" intentionally uses only GREEN, YELLOW, RED
        for scheme_name in ["default", "relaxed"]:
            scheme = COUNT_COLOR_SCHEMES[scheme_name]
            colors = [color for _, color in scheme.thresholds]
            assert ORANGE in colors, f"Count scheme '{scheme_name}' missing orange"

    def test_ber_color_schemes_sorted(self):
        """Test that BER color scheme thresholds are in ascending order."""
        for scheme_name, scheme in BER_COLOR_SCHEMES.items():
            thresholds = [t for t, _ in scheme.thresholds]
            assert thresholds == sorted(thresholds), f"Scheme '{scheme_name}' not sorted"


class TestHeatMapRenderer:
    """Test HeatMapRenderer class."""

    def test_get_color_for_value_threshold_logic(self):
        """Test color selection based on threshold logic.

        Thresholds define upper bounds (exclusive):
        - value <= 1e-12: green
        - 1e-12 < value <= 1e-7: yellow
        - 1e-7 < value <= 1e-6: bright_yellow
        - value > 1e-6: red
        """
        scheme = ColorScheme(
            thresholds=[(1e-12, "green"), (1e-7, "yellow"), (1e-6, "bright_yellow")],
            default_color="red",
        )

        renderer = HeatMapRenderer()

        # Test exact boundaries and ranges
        assert renderer._get_color_for_value(1e-13, scheme) == "green"
        assert renderer._get_color_for_value(1e-12, scheme) == "green"  # Exactly at threshold
        assert renderer._get_color_for_value(5e-12, scheme) == "yellow"
        assert renderer._get_color_for_value(1e-7, scheme) == "yellow"  # Exactly at threshold
        assert renderer._get_color_for_value(5e-7, scheme) == "bright_yellow"
        assert renderer._get_color_for_value(1e-6, scheme) == "bright_yellow"  # Exactly at threshold
        assert renderer._get_color_for_value(2e-6, scheme) == "red"  # Exceeds all thresholds

    def test_get_color_for_value_zero(self):
        """Test color selection for value of zero."""
        scheme = ColorScheme(
            thresholds=[(0, "green"), (1, "yellow"), (10, "red")],
            default_color="bright_red",
        )

        renderer = HeatMapRenderer()

        assert renderer._get_color_for_value(0, scheme) == "green"
        assert renderer._get_color_for_value(0.5, scheme) == "yellow"
        assert renderer._get_color_for_value(1, scheme) == "yellow"
        assert renderer._get_color_for_value(5, scheme) == "red"
        assert renderer._get_color_for_value(10, scheme) == "red"
        assert renderer._get_color_for_value(11, scheme) == "bright_red"

    def test_render_ber_heatmap_with_high_ber(self):
        """Test rendering heatmap with high_ber metric."""
        stats = BERStatistics(
            lane_stats={
                "01:00.0/ETH07/lane0": LaneBERStats(
                    lane_id="01:00.0/ETH07/lane0",
                    min_ber=1e-12,
                    max_ber=5e-10,
                    avg_ber=2e-11,
                    sample_count=100,
                    high_ber_count=5,
                ),
                "01:00.0/ETH07/lane1": LaneBERStats(
                    lane_id="01:00.0/ETH07/lane1",
                    min_ber=1e-11,
                    max_ber=3e-10,
                    avg_ber=1e-10,
                    sample_count=100,
                    high_ber_count=0,
                ),
            },
            num_tests=100,
            num_systems=1,
            train_speeds=[200],
        )

        renderer = HeatMapRenderer()
        output = renderer.render_ber_heatmap(stats, metric="high_ber")

        # Should contain the title
        assert "HIGH_BER Heatmap" in output

        # Should contain counts
        assert "  5  " in output  # high_ber_count for lane0
        assert "  0  " in output  # high_ber_count for lane1

    def test_render_ber_heatmap_metrics(self):
        """Test rendering heatmap with different metrics."""
        stats = BERStatistics(
            lane_stats={
                "01:00.0/ETH07/lane0": LaneBERStats(
                    lane_id="01:00.0/ETH07/lane0",
                    min_ber=1e-12,
                    max_ber=5e-10,
                    avg_ber=2e-11,
                    sample_count=100,
                    high_ber_count=5,
                ),
            },
            num_tests=100,
            num_systems=1,
            train_speeds=[200],
        )

        renderer = HeatMapRenderer()

        # Test each metric
        for metric in ["min", "avg", "max", "high_ber"]:
            output = renderer.render_ber_heatmap(stats, metric=metric)
            assert metric.upper() in output


class TestTableRenderer:
    """Test TableRenderer class."""

    def test_render_ber_statistics_column_order(self):
        """Test that BER statistics table has correct column order: Min, Avg, Max."""
        stats = BERStatistics(
            lane_stats={
                "01:00.0/ETH07/lane0": LaneBERStats(
                    lane_id="01:00.0/ETH07/lane0",
                    min_ber=1e-12,
                    max_ber=5e-10,
                    avg_ber=2e-11,
                    sample_count=100,
                    high_ber_count=5,
                ),
            },
            num_tests=100,
            num_systems=1,
            train_speeds=[200],
        )

        renderer = TableRenderer()
        output = renderer.render_ber_statistics(stats)

        # Check that columns appear in output
        assert "Min BER" in output
        assert "Avg BER" in output
        assert "Max BER" in output
        assert "High BER" in output
        assert "Samples" in output

        # Check that Min comes before Avg, and Avg comes before Max
        min_pos = output.index("Min BER")
        avg_pos = output.index("Avg BER")
        max_pos = output.index("Max BER")
        high_pos = output.index("High BER")

        assert min_pos < avg_pos < max_pos < high_pos

    def test_render_ber_statistics_with_high_ber(self):
        """Test that high BER count is displayed correctly."""
        stats = BERStatistics(
            lane_stats={
                "01:00.0/ETH07/lane0": LaneBERStats(
                    lane_id="01:00.0/ETH07/lane0",
                    min_ber=1e-12,
                    max_ber=5e-10,
                    avg_ber=2e-11,
                    sample_count=100,
                    high_ber_count=5,
                ),
                "01:00.0/ETH07/lane1": LaneBERStats(
                    lane_id="01:00.0/ETH07/lane1",
                    min_ber=1e-11,
                    max_ber=3e-10,
                    avg_ber=1e-10,
                    sample_count=100,
                    high_ber_count=0,
                ),
            },
            num_tests=100,
            num_systems=1,
            train_speeds=[200],
        )

        renderer = TableRenderer()
        output = renderer.render_ber_statistics(stats)

        # High BER count should be shown as number or "-"
        lines = output.split("\n")
        # Find lines with lane data (after header)
        data_lines = [line for line in lines if "ETH07" in line]

        assert len(data_lines) == 2
        # One should have "5" and one should have "-"
        assert any("5" in line for line in data_lines)
        assert any("-" in line for line in data_lines)

    def test_render_ber_statistics_all_high_ber(self):
        """Test rendering when all BER values are high (min/max/avg are None)."""
        stats = BERStatistics(
            lane_stats={
                "01:00.0/ETH07/lane0": LaneBERStats(
                    lane_id="01:00.0/ETH07/lane0",
                    min_ber=None,
                    max_ber=None,
                    avg_ber=None,
                    sample_count=100,
                    high_ber_count=100,
                ),
            },
            num_tests=100,
            num_systems=1,
            train_speeds=[200],
        )

        renderer = TableRenderer()
        output = renderer.render_ber_statistics(stats)

        # Should display "-" for None values
        assert "01:00.0/ETH07/lane0" in output
        # Should have dashes for min/avg/max
        lines = output.split("\n")
        data_line = [line for line in lines if "01:00.0/ETH07/lane0" in line][0]
        assert data_line.count("-") >= 3  # At least 3 dashes for min/avg/max
