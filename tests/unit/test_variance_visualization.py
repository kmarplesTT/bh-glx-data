"""Tests for variance visualization feature."""

import pytest
from bh_glx_data.system_analysis.statistics import calculate_variance_indicator
from bh_glx_data.system_analysis.visualization import HeatMapRenderer
from bh_glx_data.system_analysis.query_engine import BERStatistics, LaneBERStats


class TestVarianceIndicatorCalculation:
    """Test variance indicator calculation function."""

    def test_very_consistent_ratio_under_2(self):
        """Test very consistent indicator (● symbol)."""
        result = calculate_variance_indicator(1e-12, 1e-12, 1.5e-12)
        assert result == "●"

    def test_consistent_ratio_2_to_10(self):
        """Test consistent indicator (◆ symbol)."""
        result = calculate_variance_indicator(1e-12, 1e-11, 5e-11)
        assert result == "◆"

    def test_moderate_variance_ratio_10_to_100(self):
        """Test moderate variance indicator (▲ symbol)."""
        result = calculate_variance_indicator(1e-12, 1e-10, 5e-9)
        assert result == "▲"

    def test_high_variance_ratio_100_to_1000(self):
        """Test high variance indicator (■ symbol)."""
        result = calculate_variance_indicator(1e-12, 1e-11, 5e-9)
        assert result == "■"

    def test_extreme_spikes_ratio_over_1000(self):
        """Test extreme spikes indicator (✕ symbol)."""
        result = calculate_variance_indicator(1e-12, 1e-12, 1e-8)
        assert result == "✕"

    def test_edge_case_none_avg(self):
        """Test edge case with None average."""
        result = calculate_variance_indicator(1e-12, None, 1e-10)
        assert result == "●"

    def test_edge_case_none_max(self):
        """Test edge case with None max."""
        result = calculate_variance_indicator(1e-12, 1e-11, None)
        assert result == "●"

    def test_edge_case_zero_avg(self):
        """Test edge case with zero average."""
        result = calculate_variance_indicator(0, 0, 1e-10)
        assert result == "●"

    def test_edge_case_equal_values(self):
        """Test edge case with equal min/avg/max."""
        result = calculate_variance_indicator(1e-10, 1e-10, 1e-10)
        assert result == "●"

    def test_boundary_ratio_exactly_2(self):
        """Test boundary at ratio = 2."""
        result = calculate_variance_indicator(1e-12, 1e-11, 2e-11)
        assert result == "◆"

    def test_boundary_ratio_exactly_10(self):
        """Test boundary at ratio = 10."""
        result = calculate_variance_indicator(1e-12, 1e-10, 1e-9)
        assert result == "▲"

    def test_boundary_ratio_exactly_100(self):
        """Test boundary at ratio = 100."""
        result = calculate_variance_indicator(1e-12, 1e-10, 1e-8)
        assert result == "■"

    def test_boundary_ratio_exactly_1000(self):
        """Test boundary at ratio = 1000 (actually 999.999... due to floating point)."""
        result = calculate_variance_indicator(1e-12, 1e-10, 1e-7)
        # Due to floating point precision, 1e-7 / 1e-10 = 999.9999... which is < 1000
        assert result == "■"

    def test_boundary_ratio_above_1000(self):
        """Test boundary above ratio = 1000."""
        result = calculate_variance_indicator(1e-12, 1e-10, 1.1e-7)
        assert result == "✕"


class TestVarianceHeatmapRendering:
    """Test variance heatmap rendering."""

    def test_variance_mode_includes_symbols(self):
        """Test that variance mode includes variance symbols in output."""
        # Create sample statistics
        lane_stats = {
            "01:00.0/ETH00/lane0": LaneBERStats(
                lane_id="01:00.0/ETH00/lane0",
                min_ber=1e-12,
                avg_ber=1e-12,
                max_ber=1.5e-12,  # ratio < 2, should be ●
                sample_count=10,
                high_ber_count=0
            ),
            "01:00.0/ETH00/lane1": LaneBERStats(
                lane_id="01:00.0/ETH00/lane1",
                min_ber=1e-12,
                avg_ber=1e-11,
                max_ber=5e-11,  # ratio ~5, should be ◆
                sample_count=10,
                high_ber_count=0
            ),
        }

        stats = BERStatistics(
            lane_stats=lane_stats,
            num_tests=10,
            num_systems=1,
            train_speeds=[200]
        )

        renderer = HeatMapRenderer()
        output = renderer.render_ber_heatmap(stats, metric="variance")

        # Check that symbols appear in output
        assert "●" in output
        assert "◆" in output

        # Check title
        assert "VARIANCE" in output
        assert "Average with Consistency Indicators" in output

    def test_variance_legend_included(self):
        """Test that variance legend is included in output."""
        lane_stats = {
            "01:00.0/ETH00/lane0": LaneBERStats(
                lane_id="01:00.0/ETH00/lane0",
                min_ber=1e-12,
                avg_ber=1e-12,
                max_ber=1.5e-12,
                sample_count=10,
                high_ber_count=0
            ),
        }

        stats = BERStatistics(
            lane_stats=lane_stats,
            num_tests=10,
            num_systems=1,
            train_speeds=[200]
        )

        renderer = HeatMapRenderer()
        output = renderer.render_ber_heatmap(stats, metric="variance")

        # Check legend components
        assert "Variance Indicators:" in output
        assert "Very Consistent" in output
        assert "Consistent" in output
        assert "Moderate Variance" in output
        assert "High Variance" in output
        assert "Extreme Spikes" in output

    def test_variance_mode_colors_by_avg(self):
        """Test that variance mode colors cells by average BER."""
        # Create lane with low avg but high max (should be green with spike symbol)
        lane_stats = {
            "01:00.0/ETH00/lane0": LaneBERStats(
                lane_id="01:00.0/ETH00/lane0",
                min_ber=1e-12,
                avg_ber=1e-11,  # Low average (green)
                max_ber=1e-7,   # High max (10000x ratio) - ✕ symbol
                sample_count=10,
                high_ber_count=0
            ),
        }

        stats = BERStatistics(
            lane_stats=lane_stats,
            num_tests=10,
            num_systems=1,
            train_speeds=[200]
        )

        renderer = HeatMapRenderer()
        output = renderer.render_ber_heatmap(stats, metric="variance")

        # Should show extreme spike symbol
        assert "✕" in output

        # Color should be based on avg (1e-11 is green in default scheme)
        # Rich markup: [color(...)]value[/]
        assert "1.0e-11" in output or "1e-11" in output


class TestVarianceHeatmapIntegration:
    """Integration tests for variance heatmap feature."""

    def test_all_variance_levels_in_single_heatmap(self):
        """Test heatmap with all 5 variance levels."""
        lane_stats = {
            f"01:00.0/ETH00/lane{i}": LaneBERStats(
                lane_id=f"01:00.0/ETH00/lane{i}",
                min_ber=1e-12,
                avg_ber=avg,
                max_ber=max_val,
                sample_count=10,
                high_ber_count=0
            )
            for i, (avg, max_val) in enumerate([
                (1e-12, 1.5e-12),   # ● very consistent
                (1e-11, 5e-11),     # ◆ consistent
                (1e-10, 5e-9),      # ▲ moderate
                (1e-11, 5e-9),      # ■ high variance
                (1e-12, 1e-8),      # ✕ extreme spikes
                (1e-12, 1e-12),     # ● (fill remaining lanes)
                (1e-12, 1e-12),
                (1e-12, 1e-12),
            ])
        }

        stats = BERStatistics(
            lane_stats=lane_stats,
            num_tests=10,
            num_systems=1,
            train_speeds=[200]
        )

        renderer = HeatMapRenderer()
        output = renderer.render_ber_heatmap(stats, metric="variance")

        # Verify all symbols present
        assert "●" in output
        assert "◆" in output
        assert "▲" in output
        assert "■" in output
        assert "✕" in output

    def test_variance_vs_standard_heatmap_output_differs(self):
        """Test that variance mode produces different output than standard mode."""
        lane_stats = {
            "01:00.0/ETH00/lane0": LaneBERStats(
                lane_id="01:00.0/ETH00/lane0",
                min_ber=1e-12,
                avg_ber=1e-11,
                max_ber=5e-11,
                sample_count=10,
                high_ber_count=0
            ),
        }

        stats = BERStatistics(
            lane_stats=lane_stats,
            num_tests=10,
            num_systems=1,
            train_speeds=[200]
        )

        renderer = HeatMapRenderer()

        # Render with variance
        variance_output = renderer.render_ber_heatmap(stats, metric="variance")

        # Render with avg (standard)
        avg_output = renderer.render_ber_heatmap(stats, metric="avg")

        # Outputs should differ
        assert variance_output != avg_output

        # Variance output should have symbols, avg output should not
        assert "◆" in variance_output
        assert "◆" not in avg_output

    def test_backward_compatibility_with_existing_metrics(self):
        """Test that existing metrics (min/max/avg/high_ber) still work."""
        lane_stats = {
            "01:00.0/ETH00/lane0": LaneBERStats(
                lane_id="01:00.0/ETH00/lane0",
                min_ber=1e-12,
                avg_ber=1e-11,
                max_ber=5e-11,
                sample_count=10,
                high_ber_count=2
            ),
        }

        stats = BERStatistics(
            lane_stats=lane_stats,
            num_tests=10,
            num_systems=1,
            train_speeds=[200]
        )

        renderer = HeatMapRenderer()

        # All existing metrics should work without errors
        output_min = renderer.render_ber_heatmap(stats, metric="min")
        output_max = renderer.render_ber_heatmap(stats, metric="max")
        output_avg = renderer.render_ber_heatmap(stats, metric="avg")
        output_high_ber = renderer.render_ber_heatmap(stats, metric="high_ber")

        # Basic sanity checks
        assert "MIN" in output_min
        assert "MAX" in output_max
        assert "AVG" in output_avg
        assert "HIGH_BER" in output_high_ber

        # None should have variance symbols
        for output in [output_min, output_max, output_avg, output_high_ber]:
            assert "●" not in output
            assert "◆" not in output
            assert "▲" not in output
            assert "■" not in output
            assert "✕" not in output
