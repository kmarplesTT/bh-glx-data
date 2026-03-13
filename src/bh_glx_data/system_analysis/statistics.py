"""Statistical calculations module for system analysis.

This module provides functions for calculating BER statistics and counting
failures by status or threshold values.
"""

import logging
from typing import Dict, List

import pandas as pd

logger = logging.getLogger(__name__)


def calculate_lane_statistics(
    df: pd.DataFrame,
    lane_columns: List[str],
) -> Dict[str, Dict[str, float]]:
    """Calculate min/max/avg for specified BER lane columns.

    BER values >= 0.1 are counted separately as "high_ber" and excluded from
    min/max/avg calculations.

    Args:
        df: DataFrame with BER data
        lane_columns: List of lane column names (e.g., ["acc_ber_lane0", ...])

    Returns:
        Dictionary mapping lane column name to dict with "min", "max", "avg",
        "sample_count", "high_ber_count" keys. NaN/None values are excluded from calculations.

    Example:
        {
            "acc_ber_lane0": {
                "min": 1.23e-12,
                "max": 4.56e-10,
                "avg": 2.34e-11,
                "sample_count": 450,
                "high_ber_count": 5
            },
            ...
        }
    """
    stats = {}

    for lane in lane_columns:
        if lane not in df.columns:
            logger.warning(f"Lane column {lane} not found in DataFrame")
            continue

        # Get non-null values
        values = df[lane].dropna()

        if values.empty:
            stats[lane] = {
                "min": None,
                "max": None,
                "avg": None,
                "sample_count": 0,
                "high_ber_count": 0,
            }
        else:
            # Separate high BER values (>= 0.1) from normal values
            high_ber_mask = values >= 0.1
            high_ber_count = high_ber_mask.sum()
            normal_values = values[~high_ber_mask]

            if normal_values.empty:
                # All values are high BER
                stats[lane] = {
                    "min": None,
                    "max": None,
                    "avg": None,
                    "sample_count": len(values),
                    "high_ber_count": int(high_ber_count),
                }
            else:
                stats[lane] = {
                    "min": float(normal_values.min()),
                    "max": float(normal_values.max()),
                    "avg": float(normal_values.mean()),
                    "sample_count": len(values),
                    "high_ber_count": int(high_ber_count),
                }

    return stats


def count_by_status(
    df: pd.DataFrame,
    status: str,
    lane_columns: List[str],
) -> Dict[str, int]:
    """Count occurrences of specific test_status per lane.

    This function counts rows where test_status matches the given status
    and the lane has a non-null value (indicating the lane was tested).

    Args:
        df: DataFrame with test data
        status: Test status to count (e.g., "BER_THRESHOLD_EXCEEDED", "TRAINING_FAIL")
        lane_columns: List of lane column names

    Returns:
        Dictionary mapping lane column name to count of matching rows

    Example:
        {
            "acc_ber_lane0": 12,
            "acc_ber_lane1": 8,
            ...
        }
    """
    # Filter to matching status
    status_df = df[df["test_status"] == status]

    counts = {}

    for lane in lane_columns:
        if lane not in status_df.columns:
            logger.warning(f"Lane column {lane} not found in DataFrame")
            counts[lane] = 0
            continue

        # Count non-null values (lanes that were actually tested)
        count = status_df[lane].notna().sum()
        counts[lane] = int(count)

    return counts


def count_by_threshold(
    df: pd.DataFrame,
    threshold: float,
    lane_columns: List[str],
) -> Dict[str, int]:
    """Count occurrences where BER exceeds threshold.

    This function counts rows where the BER value is greater than the
    specified threshold, independent of test_status.

    Args:
        df: DataFrame with BER data
        threshold: BER threshold value
        lane_columns: List of lane column names

    Returns:
        Dictionary mapping lane column name to count of rows exceeding threshold

    Example:
        {
            "acc_ber_lane0": 5,
            "acc_ber_lane1": 3,
            ...
        }
    """
    counts = {}

    for lane in lane_columns:
        if lane not in df.columns:
            logger.warning(f"Lane column {lane} not found in DataFrame")
            counts[lane] = 0
            continue

        # Count values exceeding threshold (non-null only)
        count = (df[lane] > threshold).sum()
        counts[lane] = int(count)

    return counts


def calculate_variance_indicator(min_ber: float, avg_ber: float, max_ber: float) -> str:
    """Calculate variance indicator symbol based on max/avg ratio.

    Args:
        min_ber: Minimum BER value (currently unused, reserved for future)
        avg_ber: Average BER value
        max_ber: Maximum BER value

    Returns:
        Unicode symbol representing variance level:
        - "●" (U+25CF): Very consistent (max/avg < 2)
        - "◆" (U+25C6): Consistent (2 ≤ max/avg < 10)
        - "▲" (U+25B2): Moderate variance (10 ≤ max/avg < 100)
        - "■" (U+25A0): High variance (100 ≤ max/avg < 1000)
        - "✕" (U+2715): Extreme spikes (max/avg ≥ 1000)

    Note:
        Returns "●" for edge cases where avg_ber is 0 or None,
        or where max_ber is 0 or None.
    """
    # Edge cases
    if avg_ber is None or max_ber is None:
        return "●"
    if avg_ber == 0 or max_ber == 0:
        return "●"

    # Calculate ratio
    ratio = max_ber / avg_ber

    # Return symbol based on ratio thresholds
    if ratio < 2:
        return "●"  # Very consistent
    elif ratio < 10:
        return "◆"  # Consistent
    elif ratio < 100:
        return "▲"  # Moderate variance
    elif ratio < 1000:
        return "■"  # High variance
    else:
        return "✕"  # Extreme spikes


def calculate_percentile(
    df: pd.DataFrame,
    lane_columns: List[str],
    percentile: float,
) -> Dict[str, float]:
    """Calculate specified percentile for each lane.

    Args:
        df: DataFrame with BER data
        lane_columns: List of lane column names
        percentile: Percentile to calculate (0-100)

    Returns:
        Dictionary mapping lane column name to percentile value
    """
    percentiles = {}

    for lane in lane_columns:
        if lane not in df.columns:
            logger.warning(f"Lane column {lane} not found in DataFrame")
            percentiles[lane] = None
            continue

        values = df[lane].dropna()

        if values.empty:
            percentiles[lane] = None
        else:
            percentiles[lane] = float(values.quantile(percentile / 100.0))

    return percentiles


def calculate_histogram(
    df: pd.DataFrame,
    lane_column: str,
    bins: List[float],
) -> Dict[str, int]:
    """Calculate histogram of BER values for a single lane.

    Args:
        df: DataFrame with BER data
        lane_column: Single lane column name
        bins: List of bin edges (e.g., [0, 1e-12, 1e-10, 1e-8, float("inf")])

    Returns:
        Dictionary mapping bin range to count

    Example:
        {
            "0-1e-12": 100,
            "1e-12-1e-10": 50,
            "1e-10-1e-8": 10,
            "1e-8-inf": 2
        }
    """
    if lane_column not in df.columns:
        logger.warning(f"Lane column {lane_column} not found in DataFrame")
        return {}

    values = df[lane_column].dropna()

    if values.empty:
        return {}

    # Use pandas cut to bin the values
    bin_counts, _ = pd.cut(values, bins=bins, retbins=True, include_lowest=True)
    counts = bin_counts.value_counts().to_dict()

    # Format bin labels
    histogram = {}
    for i in range(len(bins) - 1):
        low = bins[i]
        high = bins[i + 1]

        # Format label
        if high == float("inf"):
            label = f"{low}-inf"
        else:
            label = f"{low}-{high}"

        # Find matching count
        count = 0
        for interval, cnt in counts.items():
            if interval.left == low and interval.right == high:
                count = cnt
                break

        histogram[label] = int(count)

    return histogram
