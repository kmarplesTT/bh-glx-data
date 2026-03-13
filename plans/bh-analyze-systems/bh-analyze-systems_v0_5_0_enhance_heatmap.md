# Plan: Enhanced BER Statistics Heatmap with Variance Indicators

## Problem Statement

Current BER heatmaps in `bh-analyze-systems` show only ONE metric at a time (min, max, or avg), making it difficult to identify:

1. **Consistently high BER lanes** (high average, low variance)
2. **Occasionally high BER lanes** (low average, but high max - indicating spikes)

Users must run multiple commands or switch to table format to see all three metrics together.

## Proposed Solution: Dual-Indicator Heatmap

Show **both magnitude and consistency** in a single heatmap by combining:

1. **Primary value & color**: Average BER (colored using existing schemes)
2. **Variance symbol**: Visual indicator of the spread between min/max
3. **Compact format**: One line per port, eight lanes per line

### Variance Classification

The variance symbol is determined by the `max/avg` ratio:

| Ratio Range | Symbol | Meaning | Example Scenario |
|-------------|--------|---------|------------------|
| < 2 | ● | Very consistent | avg=1e-12, max=1.5e-12 |
| 2-10 | ◆ | Consistent | avg=1e-11, max=5e-11 |
| 10-100 | ▲ | Moderate variance | avg=1e-10, max=5e-9 |
| 100-1000 | ■ | High variance (spikes) | avg=1e-11, max=5e-9 |
| ≥ 1000 | ✕ | Extreme spikes | avg=1e-12, max=1e-8 |

### Example Visualization

```
BER Statistics Heatmap (Average with Variance Indicators)
Train Speed: 200 Gbps | Systems: 3 | Tests: 45

Legend (BER Color Thresholds):
  Green:  < 1.0e-08   Yellow-Green: < 5.0e-08   Yellow: < 1.0e-07   Orange: >= 5.0e-07   Red: >= 1.0e-06

Variance Indicators:
  ●  Very Consistent (max/avg < 2)      ◆  Consistent (2-10)
  ▲  Moderate Variance (10-100)        ■  High Variance (100-1000)
  ✕  Extreme Spikes (≥ 1000)

Bus ID    ETH    Lane0         Lane1         Lane2         Lane3         Lane4         Lane5         Lane6         Lane7
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
01:00.0   ETH00  1.2e-12 ●    1.5e-12 ●    1.3e-12 ●    1.4e-12 ●    1.6e-12 ●    1.3e-12 ●    1.7e-12 ●    1.5e-12 ●
01:00.0   ETH01  2.3e-11 ◆    2.5e-11 ◆    2.1e-11 ◆    2.8e-11 ◆    2.2e-11 ◆    2.6e-11 ◆    2.4e-11 ◆    2.7e-11 ◆
01:00.0   ETH07  1.5e-10 ▲    3.2e-10 ■    1.8e-10 ▲    1.6e-10 ▲    4.5e-10 ✕    1.7e-10 ▲    1.9e-10 ▲    2.1e-10 ▲
05:00.0   ETH00  5.2e-07 ●    5.8e-07 ◆    6.1e-07 ◆    5.5e-07 ●    5.9e-07 ●    6.3e-07 ◆    5.7e-07 ●    6.0e-07 ●
05:00.0   ETH07  1.2e-06 ■    1.5e-06 ✕    9.8e-07 ▲    1.1e-06 ■    1.8e-06 ✕    1.3e-06 ■    1.0e-06 ▲    1.4e-06 ■
```

### Interpretation Guide

**Color coding** (with ANSI colors in terminal):

- 🟢 Green values: Good BER (< 1e-8)
- 🟡 Yellow values: Marginal BER (1e-8 to 1e-7)
- 🟠 Orange values: Poor BER (1e-7 to 1e-6)
- 🔴 Red values: Bad BER (≥ 1e-6)

**Reading the heatmap:**

- `1.2e-12 ●` (green) = Consistently excellent BER
- `2.3e-11 ◆` (green) = Consistently good BER with minor variation
- `1.5e-10 ▲` (yellow) = Marginal average with moderate spikes
- `3.2e-10 ■` (orange) = Poor average with high variance
- `4.5e-10 ✕` (orange) = Good average BUT extreme occasional spikes (⚠️ investigate!)
- `5.2e-07 ●` (red) = Consistently bad BER (persistent problem)
- `1.2e-06 ■` (red) = Bad average with high variance (very problematic)

**Key diagnostic patterns:**

- Green/Yellow ● ◆ = Healthy, stable lanes
- Orange/Red ● ◆ = Persistent issues (requires hardware investigation)
- Any ✕ symbol = Investigate for intermittent issues (cable, power, temperature)
- Specific lane patterns (e.g., lane4 consistently worse) = Possible serdes lane issue

## Implementation Plan

### Step 1: Add Variance Calculation Function (statistics.py)

**File**: `src/bh_glx_data/system_analysis/statistics.py`

**What to add:**

```python
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
```

**Where to add it:** After existing helper functions, before any class definitions.

**Testing approach:**
- Test all 5 variance levels with realistic BER values
- Test edge cases: None values, zero values, equal min/max/avg
- Test extreme ratios (very large and very small)

---

### Step 2: Add Variance Legend Helper (visualization.py)

**File**: `src/bh_glx_data/system_analysis/visualization.py`

**What to add:**

Add a new method to the `HeatMapRenderer` class:

```python
def _format_variance_legend(self) -> str:
    """Format variance indicator legend.

    Returns:
        Formatted legend string explaining variance symbols
    """
    return (
        "Variance Indicators:\n"
        "  ●  Very Consistent (max/avg < 2)      ◆  Consistent (2-10)\n"
        "  ▲  Moderate Variance (10-100)        ■  High Variance (100-1000)\n"
        "  ✕  Extreme Spikes (≥ 1000)"
    )
```

**Where to add it:** After the existing `_format_ber_legend()` method (around line 580).

---

### Step 3: Modify _render_terminal_ber_heatmap Method (visualization.py)

**File**: `src/bh_glx_data/system_analysis/visualization.py`

**Current location:** Lines 429-523 (the `_render_terminal_ber_heatmap` method)

**What to modify:**

1. **Update the method signature** (no changes needed - already accepts `metric` parameter)

2. **Add import** at the top of the file:
   ```python
   from bh_glx_data.system_analysis.statistics import calculate_variance_indicator
   ```

3. **Add variance mode handling** in the metric value extraction section (currently lines 454-467):

   ```python
   # Get metric value (existing code for min/max/avg/high_ber)
   if metric == "min":
       value = lane_stat.min_ber
   elif metric == "max":
       value = lane_stat.max_ber
   elif metric == "avg":
       value = lane_stat.avg_ber
   elif metric == "variance":  # NEW
       value = lane_stat.avg_ber  # Use avg for coloring
       # Calculate variance indicator for later use
       variance_symbol = calculate_variance_indicator(
           lane_stat.min_ber,
           lane_stat.avg_ber,
           lane_stat.max_ber
       )
   else:  # high_ber
       value = lane_stat.high_ber_count

   key = (bus_id, eth_id)
   if key not in grouped:
       grouped[key] = {}

   # Store both value and variance symbol if in variance mode
   if metric == "variance":
       grouped[key][lane_num] = (value, variance_symbol)
   else:
       grouped[key][lane_num] = value
   ```

4. **Update title generation** (currently line 469):
   ```python
   if metric == "variance":
       title = "BER Statistics - VARIANCE Heatmap (Average with Consistency Indicators)"
   else:
       title = f"BER Statistics - {metric.upper()} Heatmap"
   ```

5. **Modify the rendering loop** (currently lines 476-506) to handle variance tuples:

   ```python
   # Render each port
   for (bus_id, eth_id), lane_values in sorted(grouped.items()):
       port_line = f"{bus_id}/{eth_id}  "

       # Render 8 lanes
       for lane_num in range(8):
           lane_data = lane_values.get(lane_num)

           # Handle variance mode (tuple) vs regular mode (single value)
           if metric == "variance" and lane_data is not None:
               value, variance_symbol = lane_data
           else:
               value = lane_data
               variance_symbol = None

           if value is None:
               if is_count_metric:
                   value_str = "   0"
                   color = self._get_color_for_value(0, self.count_colors)
                   style = color
               else:
                   value_str = "  -  "
                   style = "dim"
           elif is_count_metric:
               value_str = f"{int(value):4d}" if value < 1000 else "999+"
               color = self._get_color_for_value(value, scheme)
               style = color
           else:
               # For BER values
               value_str = f"{value:.1e}"
               color = self._get_color_for_value(value, scheme)
               style = color

               # Append variance symbol if in variance mode
               if variance_symbol:
                   value_str = f"{value_str} {variance_symbol}"

           # Apply style to output
           port_line += f"[{style}]{value_str}[/]  "

       lines.append(port_line)
   ```

6. **Update legend display** (currently lines 509-511):
   ```python
   # Add legend
   lines.append("")
   if metric == "variance":
       # Show both BER color legend and variance legend
       lines.append(self._format_ber_legend(scheme))
       lines.append("")
       lines.append(self._format_variance_legend())
   else:
       lines.append(self._format_ber_legend(scheme))
   ```

**Key considerations:**
- Preserve existing behavior for all non-variance metrics
- Handle None values gracefully
- Ensure proper spacing (variance display adds ~2 characters per cell)
- Use Rich console's color formatting consistently

---

### Step 4: Update CLI to Support Variance Statistic (cli.py)

**File**: `src/bh_glx_data/system_analysis/cli.py`

**Current location:** Lines 129-134 (the `--statistic` argument definition)

**What to modify:**

```python
stats_parser.add_argument(
    "--statistic",
    choices=["avg", "min", "max", "high_ber", "variance"],  # Add "variance"
    default="max",
    help="Statistic to display in heatmap (variance shows avg with consistency symbols)",
)
```

**No other CLI changes needed** - the handler already passes `args.statistic` to the renderer.

---

### Step 5: Add Comprehensive Tests (tests/unit/test_variance_visualization.py)

**File**: `tests/unit/test_variance_visualization.py` (NEW FILE)

**Test cases to implement:**

```python
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
        """Test boundary at ratio = 1000."""
        result = calculate_variance_indicator(1e-12, 1e-10, 1e-7)
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
```

**Where to save:** `tests/unit/test_variance_visualization.py`

---

### Step 6: Update Documentation (docs/user_guides/bh-analyze-systems.md)

**File**: `docs/user_guides/bh-analyze-systems.md`

**What to add:** Add a new section after the existing heatmap visualization section:

```markdown
### Variance Heatmap Visualization

The variance heatmap combines BER magnitude (color) with consistency indicators (symbols) to show both average performance and variability in a single view.

#### Usage

```bash
# Show variance heatmap for all lanes
bh-analyze-systems stats all --format heatmap --statistic variance

# Filter by speed
bh-analyze-systems stats all --format heatmap --statistic variance --speed 200

# Specific ports
bh-analyze-systems stats 01:00.0/ETH07 --format heatmap --statistic variance

# Use different color schemes
bh-analyze-systems stats all --format heatmap --statistic variance --color-scheme sensitive
```

#### Understanding the Variance Heatmap

Each cell displays:
- **BER value**: Average BER across all test runs
- **Color**: Indicates BER magnitude (green=good, red=bad)
- **Symbol**: Indicates consistency/variance

**Variance Symbols:**
- `●` Very Consistent (max/avg < 2) - Stable, predictable performance
- `◆` Consistent (max/avg 2-10) - Minor fluctuations
- `▲` Moderate Variance (max/avg 10-100) - Noticeable spikes
- `■` High Variance (max/avg 100-1000) - Significant intermittent issues
- `✕` Extreme Spikes (max/avg ≥ 1000) - Severe occasional failures

#### Diagnostic Patterns

**Healthy Lanes:**
- Green `●` or `◆` = Excellent and consistent
- Yellow `●` or `◆` = Good and consistent

**Problem Lanes:**
- Orange/Red `●` or `◆` = Persistent hardware issues (consistent failures)
- Green/Yellow `■` or `✕` = Intermittent issues (cable, power, thermal)
- Orange/Red `■` or `✕` = Severe and unstable (critical problem)

**Troubleshooting Tips:**
- `✕` symbol → Investigate environmental factors (cables, power, temperature)
- Consistent `●`/`◆` symbols with high BER → Hardware fault (replace component)
- Pattern on specific lanes → Serdes lane issue
- Pattern on specific ports → Port or connector issue

#### Example

```
01:00.0   ETH07  1.2e-12 ●    1.5e-10 ▲    1.8e-10 ▲    4.5e-10 ✕    1.7e-10 ▲
```

Interpretation:
- Lane 0: Excellent and very consistent (`●`)
- Lanes 1-2: Marginal with moderate spikes (`▲`) - monitor
- Lane 3: Good average BUT extreme spikes (`✕`) - investigate cables/environment
- Lane 4: Marginal with moderate spikes (`▲`) - monitor
```

---

## Verification Plan

### Unit Tests

```bash
# Run variance visualization tests
pytest tests/unit/test_variance_visualization.py -v

# Run all unit tests to ensure no regressions
pytest tests/unit/ -v
```

**Expected results:**
- 20+ tests passing
- Coverage > 90% for new code
- No regressions in existing tests

### Manual Testing

```bash
# 1. Test basic variance heatmap
bh-analyze-systems stats all --format heatmap --statistic variance

# 2. Compare with standard metrics
bh-analyze-systems stats all --format heatmap --statistic max
bh-analyze-systems stats all --format heatmap --statistic avg
bh-analyze-systems stats all --format heatmap --statistic min

# 3. Test with different color schemes
bh-analyze-systems stats all --format heatmap --statistic variance --color-scheme sensitive
bh-analyze-systems stats all --format heatmap --statistic variance --color-scheme tolerant

# 4. Test specific lanes
bh-analyze-systems stats 01:00.0/ETH07 --format heatmap --statistic variance

# 5. Test with filtered data
bh-analyze-systems stats all --speed 200 --format heatmap --statistic variance

# 6. Verify table format still works
bh-analyze-systems stats all --format table

# 7. Test that all existing functionality works (regression testing)
bh-analyze-systems threshold all --format heatmap
bh-analyze-systems training all --format heatmap
bh-analyze-systems custom all 1e-10 --format heatmap
```

### Expected Outcomes

1. **Visual clarity**: Easy to spot problematic lanes at a glance
2. **Diagnostic value**: Distinguish persistent vs. intermittent issues
3. **Backward compatibility**: All existing commands work unchanged
4. **Performance**: No significant slowdown (variance calc is O(n))
5. **Consistency**: Matches existing color schemes and formatting

### Edge Cases to Verify

- Zero or None BER values (should show "-" or handle gracefully)
- Single sample (ratio calculation with n=1)
- All lanes with same BER (all `●` symbols)
- Very wide terminal (column alignment maintained)
- Very narrow terminal (graceful truncation)
- Mixed train speeds in dataset
- Systems with partial data
- All 5 variance levels in same display

---

## Critical Files Summary

| File | Changes | Type |
|------|---------|------|
| `src/bh_glx_data/system_analysis/statistics.py` | Add `calculate_variance_indicator()` function | New function |
| `src/bh_glx_data/system_analysis/visualization.py` | Add `_format_variance_legend()` method | New method |
| `src/bh_glx_data/system_analysis/visualization.py` | Modify `_render_terminal_ber_heatmap()` method | Enhancement |
| `src/bh_glx_data/system_analysis/cli.py` | Add "variance" to `--statistic` choices | Simple change |
| `tests/unit/test_variance_visualization.py` | Comprehensive test suite | New file |
| `docs/user_guides/bh-analyze-systems.md` | Add variance heatmap documentation | New section |

---

## Design Rationale

### Why This Approach?

1. **Minimal Changes**: Leverages existing infrastructure (--statistic option, render_ber_heatmap method)
2. **Single-glance Diagnostics**: Color + symbol conveys both magnitude and consistency
3. **Terminal-friendly**: Uses Unicode symbols that render well in modern terminals
4. **Familiar Patterns**: Builds on existing heatmap structure users already understand
5. **Actionable Insights**: Directly supports troubleshooting workflows
6. **Backward Compatible**: Opt-in via statistic choice, doesn't change existing behavior
7. **Data Already Available**: Uses existing min/max/avg values from LaneBERStats

### Alternative Approaches Considered

1. **Separate --show-variance flag**: Would work but adds another CLI option
2. **Stacked display** (min/avg/max on separate rows): Too verbose, loses at-a-glance value
3. **Inline format** (avg/max in single cell): Hard to read, loses min value
4. **Bar charts** (Unicode blocks): Loses precision, harder to compare
5. **Dual-color approach**: Too complex visually, cognitive overload

### Trade-offs

**Pros:**
- Compact representation
- Clear diagnostic value
- Easy to learn (5 symbols)
- Works in all terminals
- No new data structures needed
- Minimal code changes

**Cons:**
- Requires legend reference initially
- Some symbols may not render in very old terminals
- Max/avg ratio may not capture all variance patterns (e.g., bimodal distributions)
- Adds ~2 characters per cell (may affect narrow terminal layouts)

### Future Enhancements (Out of Scope for v0.5.0)

- Interactive detail view (click/hover to see exact min/max values)
- Customizable variance thresholds via config file
- Statistical measures (std dev, percentiles) instead of simple ratio
- Historical trend indicators (↗ ↘ for improving/worsening lanes)
- Export variance data to Excel with conditional formatting
- ASCII fallback symbols for legacy terminals (*, +, ^, #, X)

---

## Success Criteria

✅ User can identify consistently high BER lanes in one glance
✅ User can identify lanes with occasional spikes in one glance
✅ Visualization fits in standard terminal width (80-120 columns)
✅ All existing functionality remains unchanged (backward compatible)
✅ Documentation clearly explains interpretation
✅ Tests cover all variance levels and edge cases
✅ No performance degradation
✅ Code follows existing patterns and style

---

**Implementation Time Estimate:** 4-6 hours for experienced developer

**Testing Time Estimate:** 2-3 hours (unit tests + manual verification)

**Documentation Time Estimate:** 1 hour

**Total Estimate:** 7-10 hours end-to-end
