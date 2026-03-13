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
  Green:  < 1.0e-08   Yellow: < 1.0e-07   Orange: < 5.0e-07   Red: >= 5.0e-07

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

Interactive Detail View (optional enhancement):
  01:00.0/ETH07/lane4: avg=4.5e-10 ● | min=2.1e-13 | max=8.2e-07 | samples=15 | max/avg=1822x
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

### Phase 1: Extend Variance Calculation (statistics.py)

**File**: `src/bh_glx_data/system_analysis/statistics.py`

Add variance calculation helper:

```python
def calculate_variance_indicator(min_ber: float, avg_ber: float, max_ber: float) -> str:
    """Calculate variance indicator symbol based on max/avg ratio."""
    if avg_ber == 0 or max_ber == 0:
        return "●"  # No variance if zero values

    ratio = max_ber / avg_ber

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

### Phase 2: Enhance HeatMapRenderer (visualization.py)

**File**: `src/bh_glx_data/system_analysis/visualization.py`

**Changes needed:**

1. **Add new metric option** to `render_ber_heatmap()`:
   - Current: `metric: str = "avg"` (accepts "min", "max", "avg")
   - New: Also accept `metric="combined"` or `metric="variance"`

2. **Create new rendering method**:

   ```python
   def _render_terminal_ber_variance_heatmap(
       self,
       stats: BERStatistics,
       console: Console
   ) -> None:
       """Render BER heatmap with variance indicators."""
       # Group lanes by (bus_id, eth_id)
       # For each lane:
       #   - Get avg_ber value
       #   - Calculate variance_symbol from min/max/avg
       #   - Apply color based on avg_ber
       #   - Format as: f"[{color}]{avg_ber:.1e} {variance_symbol}[/]"
       # Render with proper spacing (12-14 chars per lane)
   ```

3. **Update legend generation**:
   - Show BER color thresholds (existing)
   - Add variance indicator legend
   - Include interpretation tips

### Phase 3: Update CLI Interface (cli.py)

**File**: `src/bh_glx_data/system_analysis/cli.py`

**Option 1**: Add new `--metric` argument:

```python
stats_parser.add_argument(
    "--metric",
    choices=["min", "max", "avg", "combined"],
    default="avg",
    help="Metric to display in heatmap (combined shows avg with variance indicators)"
)
```

**Option 2**: Add new `--show-variance` flag (simpler, recommended):

```python
stats_parser.add_argument(
    "--show-variance",
    action="store_true",
    help="Show variance indicators in heatmap (displays avg with consistency symbols)"
)
```

Update handler to pass through to renderer:

```python
if args.format == "heatmap":
    metric = "combined" if args.show_variance else "avg"
    renderer = HeatMapRenderer(ber_color_scheme=color_scheme)
    output = renderer.render_ber_heatmap(result, metric=metric)
```

### Phase 4: Testing

**New test file**: `tests/unit/test_variance_visualization.py`

Test cases:

1. `test_variance_indicator_calculation()` - All 5 variance levels
2. `test_variance_heatmap_rendering()` - Format and spacing
3. `test_variance_legend_generation()` - Legend content
4. `test_cli_variance_flag()` - CLI argument handling
5. `test_combined_color_and_variance()` - Integration

### Phase 5: Documentation

**Update**: `docs/user_guides/bh-analyze-systems.md`

Add section:

- "Understanding BER Variance Indicators"
- Example commands with `--show-variance`
- Interpretation guide with diagnostic patterns
- Real-world troubleshooting examples

## Critical Files

- `src/bh_glx_data/system_analysis/statistics.py` - Add variance calculation
- `src/bh_glx_data/system_analysis/visualization.py` - New heatmap renderer
- `src/bh_glx_data/system_analysis/cli.py` - CLI argument handling
- `tests/unit/test_variance_visualization.py` - New test file
- `docs/user_guides/bh-analyze-systems.md` - Documentation update

## Verification Plan

### Manual Testing

```bash
# 1. Test basic variance heatmap
bh-analyze-systems stats all --format heatmap --show-variance

# 2. Test with different color schemes
bh-analyze-systems stats all --format heatmap --show-variance --color-scheme sensitive

# 3. Test specific lanes
bh-analyze-systems stats 01:00.0/ETH07 --format heatmap --show-variance

# 4. Compare with standard heatmap
bh-analyze-systems stats all --format heatmap  # Without --show-variance

# 5. Test with filtered data
bh-analyze-systems stats all --speed 200 --format heatmap --show-variance

# 6. Verify table format still works
bh-analyze-systems stats all --format table
```

### Expected Outcomes

1. **Visual clarity**: Easy to spot problematic lanes at a glance
2. **Diagnostic value**: Distinguish persistent vs. intermittent issues
3. **Backward compatibility**: Existing commands work unchanged
4. **Performance**: No significant slowdown (variance calc is O(n))
5. **Consistency**: Matches existing color schemes and formatting

### Edge Cases to Verify

- Zero or missing BER values (should show "N/A" or skip)
- Single sample (ratio calculation with n=1)
- Very wide terminal (column alignment)
- Very narrow terminal (graceful truncation)
- Mixed train speeds in dataset
- Systems with partial data

## Design Rationale

### Why This Approach?

1. **Single-glance diagnostics**: Color + symbol conveys both magnitude and consistency
2. **Terminal-friendly**: Uses Unicode symbols that render well in modern terminals
3. **Familiar patterns**: Builds on existing heatmap structure
4. **Actionable insights**: Directly supports troubleshooting workflows
5. **Backward compatible**: Opt-in via flag, doesn't change existing behavior

### Alternative Approaches Considered

1. **Stacked display** (min/avg/max on separate rows): Too verbose, loses at-a-glance value
2. **Inline format** (avg/max in single cell): Hard to read, loses min value
3. **Bar charts** (Unicode blocks): Loses precision, harder to compare
4. **Dual-color approach**: Too complex visually, cognitive overload

### Trade-offs

**Pros:**

- Compact representation
- Clear diagnostic value
- Easy to learn (5 symbols)
- Works in all terminals

**Cons:**

- Requires legend reference initially
- Some symbols may not render in all terminals (fallback to ASCII)
- Max/avg ratio may not capture all variance patterns (e.g., bimodal distributions)

### Future Enhancements (Out of Scope)

- Interactive detail view (click/hover to see exact min/max values)
- Customizable variance thresholds
- Statistical measures (std dev, percentiles) instead of simple ratio
- Historical trend indicators (↗ ↘ for improving/worsening lanes)
- Export variance data to Excel with conditional formatting

## Success Criteria

✅ User can identify consistently high BER lanes in one glance
✅ User can identify lanes with occasional spikes in one glance
✅ Visualization fits in standard terminal width (80-120 columns)
✅ All existing functionality remains unchanged
✅ Documentation clearly explains interpretation
✅ Tests cover all variance levels and edge cases
