"""Unit tests for statistics module."""

import pandas as pd
import pytest

from bh_glx_data.system_analysis.statistics import (
    calculate_lane_statistics,
    count_by_status,
    count_by_threshold,
)


class TestCalculateLaneStatistics:
    """Test calculate_lane_statistics function."""

    def test_basic_statistics(self):
        """Test basic statistics calculation."""
        df = pd.DataFrame({
            "acc_ber_lane0": [1e-12, 2e-12, 3e-12],
            "acc_ber_lane1": [1e-11, 2e-11, 3e-11],
        })

        stats = calculate_lane_statistics(df, ["acc_ber_lane0", "acc_ber_lane1"])

        assert "acc_ber_lane0" in stats
        assert "acc_ber_lane1" in stats

        # Check lane0 stats
        assert stats["acc_ber_lane0"]["min"] == 1e-12
        assert stats["acc_ber_lane0"]["max"] == 3e-12
        assert abs(stats["acc_ber_lane0"]["avg"] - 2e-12) < 1e-20
        assert stats["acc_ber_lane0"]["sample_count"] == 3
        assert stats["acc_ber_lane0"]["high_ber_count"] == 0

        # Check lane1 stats
        assert stats["acc_ber_lane1"]["min"] == 1e-11
        assert stats["acc_ber_lane1"]["max"] == 3e-11
        assert abs(stats["acc_ber_lane1"]["avg"] - 2e-11) < 1e-20
        assert stats["acc_ber_lane1"]["sample_count"] == 3
        assert stats["acc_ber_lane1"]["high_ber_count"] == 0

    def test_high_ber_excluded_from_stats(self):
        """Test that high BER values (>= 0.1) are excluded from min/max/avg."""
        df = pd.DataFrame({
            "acc_ber_lane0": [1e-12, 2e-12, 0.5, 0.8],  # Two high BER values
            "acc_ber_lane1": [1e-11, 2e-11, 3e-11, 4e-11],  # No high BER
        })

        stats = calculate_lane_statistics(df, ["acc_ber_lane0", "acc_ber_lane1"])

        # Lane0 should exclude high BER from min/max/avg
        assert stats["acc_ber_lane0"]["min"] == 1e-12
        assert stats["acc_ber_lane0"]["max"] == 2e-12
        assert abs(stats["acc_ber_lane0"]["avg"] - 1.5e-12) < 1e-20
        assert stats["acc_ber_lane0"]["sample_count"] == 4
        assert stats["acc_ber_lane0"]["high_ber_count"] == 2

        # Lane1 should have no high BER
        assert stats["acc_ber_lane1"]["high_ber_count"] == 0

    def test_all_high_ber_values(self):
        """Test when all values are high BER (>= 0.1)."""
        df = pd.DataFrame({
            "acc_ber_lane0": [0.1, 0.5, 0.9],
        })

        stats = calculate_lane_statistics(df, ["acc_ber_lane0"])

        # All values are high BER, so min/max/avg should be None
        assert stats["acc_ber_lane0"]["min"] is None
        assert stats["acc_ber_lane0"]["max"] is None
        assert stats["acc_ber_lane0"]["avg"] is None
        assert stats["acc_ber_lane0"]["sample_count"] == 3
        assert stats["acc_ber_lane0"]["high_ber_count"] == 3

    def test_boundary_value_0_1(self):
        """Test that 0.1 exactly is considered high BER."""
        df = pd.DataFrame({
            "acc_ber_lane0": [0.09, 0.1, 0.11],
        })

        stats = calculate_lane_statistics(df, ["acc_ber_lane0"])

        # Only 0.09 should be in normal stats
        assert stats["acc_ber_lane0"]["min"] == 0.09
        assert stats["acc_ber_lane0"]["max"] == 0.09
        assert stats["acc_ber_lane0"]["avg"] == 0.09
        assert stats["acc_ber_lane0"]["sample_count"] == 3
        assert stats["acc_ber_lane0"]["high_ber_count"] == 2

    def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        df = pd.DataFrame({
            "acc_ber_lane0": [],
        })

        stats = calculate_lane_statistics(df, ["acc_ber_lane0"])

        assert stats["acc_ber_lane0"]["min"] is None
        assert stats["acc_ber_lane0"]["max"] is None
        assert stats["acc_ber_lane0"]["avg"] is None
        assert stats["acc_ber_lane0"]["sample_count"] == 0
        assert stats["acc_ber_lane0"]["high_ber_count"] == 0

    def test_nan_values_excluded(self):
        """Test that NaN values are excluded from statistics."""
        df = pd.DataFrame({
            "acc_ber_lane0": [1e-12, None, 3e-12, float("nan")],
        })

        stats = calculate_lane_statistics(df, ["acc_ber_lane0"])

        assert stats["acc_ber_lane0"]["min"] == 1e-12
        assert stats["acc_ber_lane0"]["max"] == 3e-12
        assert abs(stats["acc_ber_lane0"]["avg"] - 2e-12) < 1e-20
        assert stats["acc_ber_lane0"]["sample_count"] == 2
        assert stats["acc_ber_lane0"]["high_ber_count"] == 0

    def test_missing_lane_column(self):
        """Test handling of missing lane column."""
        df = pd.DataFrame({
            "acc_ber_lane0": [1e-12, 2e-12],
        })

        stats = calculate_lane_statistics(df, ["acc_ber_lane0", "acc_ber_lane99"])

        assert "acc_ber_lane0" in stats
        assert "acc_ber_lane99" not in stats


class TestCountByStatus:
    """Test count_by_status function."""

    def test_count_specific_status(self):
        """Test counting rows with specific status."""
        df = pd.DataFrame({
            "test_status": ["PASS", "TRAINING_FAIL", "PASS", "BER_THRESHOLD_EXCEEDED"],
            "acc_ber_lane0": [1e-12, None, 2e-12, 3e-12],
            "acc_ber_lane1": [1e-11, None, 2e-11, None],
        })

        counts = count_by_status(df, "PASS", ["acc_ber_lane0", "acc_ber_lane1"])

        assert counts["acc_ber_lane0"] == 2  # Two PASS rows with non-null lane0
        assert counts["acc_ber_lane1"] == 2  # Two PASS rows with non-null lane1


class TestCountByThreshold:
    """Test count_by_threshold function."""

    def test_count_exceeding_threshold(self):
        """Test counting values exceeding threshold."""
        df = pd.DataFrame({
            "acc_ber_lane0": [1e-12, 1e-10, 1e-8, 1e-6],
            "acc_ber_lane1": [1e-11, 1e-9, 1e-7, 1e-5],
        })

        counts = count_by_threshold(df, 1e-9, ["acc_ber_lane0", "acc_ber_lane1"])

        assert counts["acc_ber_lane0"] == 2  # 1e-8 and 1e-6 exceed 1e-9
        assert counts["acc_ber_lane1"] == 2  # 1e-7 and 1e-5 exceed 1e-9
