# Per-UBB Analysis User Guide

A comprehensive guide to using per-UBB position analysis in bh-analyze-systems v0.7.0.

**Version:** 0.7.0
**Feature:** Per-UBB Position Analysis

---

## Table of Contents

- [Overview](#overview)
- [Understanding UBB Structure](#understanding-ubb-structure)
- [Why Per-UBB Analysis](#why-per-ubb-analysis)
- [Usage Examples](#usage-examples)
- [Understanding the Output](#understanding-the-output)
- [Comparison Examples](#comparison-examples)
- [Best Practices](#best-practices)
- [Integration with Excel Export](#integration-with-excel-export)
- [Troubleshooting](#troubleshooting)

---

## Overview

Per-UBB position analysis is a powerful feature that enables you to aggregate test data from equivalent chip positions across all four UBBs on a system. This approach effectively 4x's your sample size for pattern detection, making it ideal for identifying PCB-level issues that affect the same chip position regardless of which UBB it's on.

**Key Benefits:**

- **4x Sample Size** - Aggregates data from chips at the same position across all 4 UBBs
- **PCB-Level Pattern Detection** - Identifies issues related to physical board layout and trace routing
- **Statistical Significance** - Larger sample sizes enable more confident conclusions about hardware patterns
- **Faster Root Cause Analysis** - Quickly distinguish between PCB design issues and system-specific problems

**When to Use:**

- Investigating potential PCB trace or layout issues
- Analyzing serdes lane patterns that might be board-design related
- Identifying if failures correlate with specific chip positions
- Building statistical confidence for pattern analysis across multiple systems

**When NOT to Use:**

- Debugging system-specific issues (use standard per-system analysis)
- Investigating cable or environmental problems (these are system-specific)
- Analyzing issues known to be unique to specific systems

---

## Understanding UBB Structure

### System Architecture

Each BH Galaxy system consists of:

- **4 UBBs** (Universal Blackhole Boards) - Identical PCBs
- **8 chips per UBB** - Each chip occupies a specific position (U1-U8)
- **32 total chips per system** - 4 UBBs × 8 chips

### Bus ID Mapping

The bus IDs follow a pattern where the first digit identifies the UBB:

| UBB | Bus ID Pattern | Example Chip Positions |
|-----|----------------|------------------------|
| UBB 1 | `0x:00.0` | `01:00.0` (U1), `02:00.0` (U2), ... `08:00.0` (U8) |
| UBB 2 | `4x:00.0` | `41:00.0` (U1), `42:00.0` (U2), ... `48:00.0` (U8) |
| UBB 3 | `cx:00.0` | `c1:00.0` (U1), `c2:00.0` (U2), ... `c8:00.0` (U8) |
| UBB 4 | `8x:00.0` | `81:00.0` (U1), `82:00.0` (U2), ... `88:00.0` (U8) |

### Chip Position Equivalence

Since all UBBs use identical PCB designs, chips at the same position share:

- **Identical PCB Traces** - Same high-speed serdes lane routing
- **Same Physical Layout** - Connectors, power delivery, thermal characteristics
- **Equivalent Signal Paths** - Same trace lengths, impedances, and coupling

**Example:** Chips `01:00.0`, `41:00.0`, `c1:00.0`, and `81:00.0` all represent the **U1 position** across the four UBBs. If all U1 chips show similar BER patterns on ETH10 lane 4, it suggests a PCB design characteristic at that chip position.

---

## Why Per-UBB Analysis

### Traditional Per-System Analysis

**Standard approach:**
- Analyzes `01:00.0/ETH10/lane4` as a single data point per system
- If you have 5 systems, you get 5 samples for this lane
- Useful for system-specific troubleshooting

**Limitation:**
- Small sample sizes make it harder to distinguish patterns from noise
- PCB-level patterns are diluted across different bus IDs

### Per-UBB Position Analysis

**UBB-based approach:**
- Treats `01:00.0`, `41:00.0`, `c1:00.0`, `81:00.0` as **four samples of U1/ETH10/lane4**
- If you have 5 systems, you get 20 samples for this chip position (5 systems × 4 UBBs)
- Each chip position is analyzed independently: U1, U2, U3, ... U8

**Advantage:**
- **4x the data** for each chip position
- Enables statistical pattern detection
- Quickly identifies if issues correlate with chip position (PCB design) vs. specific systems

### Real-World Use Case

**Scenario:** You notice occasional BER spikes on ETH10 lane 4 in your fleet.

**Question:** Is this a PCB design issue affecting chip position U1, or a system-specific problem?

**Traditional Analysis:**
```bash
bh-analyze-systems stats 01:00.0/ETH10/4 --speed 200
# Result: 5 samples (one per system) - not enough to be confident
```

**Per-UBB Analysis:**
```bash
bh-analyze-systems stats U1/ETH10/4 --speed 200 --by-ubb-position
# Result: 20 samples (5 systems × 4 UBBs) - statistically significant

bh-analyze-systems stats U2/ETH10/4 --speed 200 --by-ubb-position
# Result: 20 samples for U2 position

# If U1 shows high BER but U2-U8 are clean → PCB design issue at U1
# If all positions show high BER → Likely a different root cause
# If only specific systems show issues → System-specific problem
```

---

## Usage Examples

### Basic Command Structure

Add the `--by-ubb-position` flag to any analysis command:

```bash
bh-analyze-systems <command> <chip-position-spec> --by-ubb-position [OPTIONS]
```

### Chip Position Syntax

When using `--by-ubb-position`, specify chip positions instead of bus IDs:

| Syntax | Description | Example |
|--------|-------------|---------|
| `U1/ETH07` | Chip position U1, all lanes on ETH07 | Aggregates 01:00.0, 41:00.0, c1:00.0, 81:00.0 |
| `U1/ETH07/4` | Chip position U1, ETH07 lane 4 only | Single lane across all UBBs |
| `U1/*` | All ports on chip position U1 | All ports at U1 across 4 UBBs |
| `*/ETH07` | ETH07 on all chip positions | ETH07 on U1-U8 across all UBBs |
| `*/ETH07/4` | Lane 4 on ETH07 across all positions | Lane 4 at all positions |
| `all` | All chip positions, all ports | Complete dataset aggregated by position |

**Important:** You can still use traditional bus_id syntax (e.g., `01:00.0/ETH07`) with `--by-ubb-position` - the tool automatically maps it to the chip position (U1).

### Stats Command Examples

1. **Query BER statistics for specific chip position:**

```bash
bh-analyze-systems stats U1/ETH07 --speed 200 --by-ubb-position
```

**Output:**
```
┌─────────────────┬───────────┬───────────┬───────────┬──────────┬─────────┐
│ Lane            │ Min       │ Avg       │ Max       │ High BER │ Samples │
├─────────────────┼───────────┼───────────┼───────────┼──────────┼─────────┤
│ U1/ETH07/lane0  │ 1.23e-12  │ 2.34e-11  │ 4.56e-10  │ 5        │ 180     │
│ U1/ETH07/lane1  │ 8.90e-13  │ 1.87e-11  │ 3.21e-10  │ -        │ 180     │
│ U1/ETH07/lane2  │ 1.45e-12  │ 2.89e-11  │ 5.23e-10  │ -        │ 180     │
│ U1/ETH07/lane3  │ 9.87e-13  │ 2.12e-11  │ 3.78e-10  │ 2        │ 180     │
└─────────────────┴───────────┴───────────┴───────────┴──────────┴─────────┘

Tests: 180  Systems: 5  Chip Positions: U1  Speeds: 200
Note: Data aggregated by UBB position (4 UBBs per system)
```

**Interpretation:** 180 samples = 5 systems × 4 UBBs × 9 tests per UBB

2. **Compare with standard analysis:**

```bash
# Standard per-system analysis
bh-analyze-systems stats 01:00.0/ETH07 --speed 200

# Per-UBB position analysis
bh-analyze-systems stats U1/ETH07 --speed 200 --by-ubb-position
```

3. **Heatmap visualization for all chip positions:**

```bash
bh-analyze-systems stats all --speed 200 --format heatmap --by-ubb-position
```

**Output:**
```
BER Statistics (Max) - 200G Train Speed
Per-UBB Position View

Chip Position: U1
  ETH00 [████████] 1.2e-12  1.5e-12  1.8e-12  2.1e-12  ...
  ETH01 [████████] 1.3e-12  1.6e-12  1.9e-12  2.2e-12  ...
  ETH07 [████████] 3.4e-10  2.1e-11  1.8e-11  5.6e-10  ...

Chip Position: U2
  ETH00 [████████] 1.1e-12  1.4e-12  1.7e-12  2.0e-12  ...
  ETH01 [████████] 1.2e-12  1.5e-12  1.8e-12  2.1e-12  ...
  ETH07 [████████] 1.3e-12  1.6e-12  1.9e-12  2.2e-12  ...

[... U3 through U8 ...]
```

4. **Single lane analysis across all positions:**

```bash
bh-analyze-systems stats */ETH10/4 --speed 200 --by-ubb-position
```

### Threshold Command Examples

1. **Check threshold violations by chip position:**

```bash
bh-analyze-systems threshold U1/* --speed 200 --by-ubb-position
```

2. **Heatmap of threshold violations:**

```bash
bh-analyze-systems threshold all --speed 200 --format heatmap --by-ubb-position
```

### Custom Threshold Examples

```bash
# Custom threshold for specific chip position
bh-analyze-systems custom U1/ETH10 1e-10 --speed 200 --by-ubb-position

# Custom threshold across all positions
bh-analyze-systems custom all 1e-11 --speed 200 --format heatmap --by-ubb-position
```

### Training Failures Examples

```bash
# Training failures by chip position
bh-analyze-systems training U1/* --speed 200 --by-ubb-position

# Heatmap of training failures across all positions
bh-analyze-systems training all --speed 200 --format heatmap --by-ubb-position
```

### Histogram Examples

1. **BER distribution for specific chip position and lane:**

```bash
bh-analyze-systems histogram U1/ETH10/4 --speed 200 --by-ubb-position
```

**Output:**
```
BER Histogram - U1/ETH10/lane4 (Per-UBB Position)

  < 1e-12   ████████████████████████████ 72
  1e-12-11  ██████████████ 35
  1e-11-10  ████████ 18
  1e-10-9   ████ 8
  1e-9-8    ██ 3
  >= 1e-8    1

Total Samples: 137  |  Systems: 5  |  Chip Positions: U1  |  Speeds: 200
Note: Aggregated from 4 UBBs per system
```

2. **Compare histograms across chip positions:**

```bash
# U1 histogram
bh-analyze-systems histogram U1/ETH10/4 --speed 200 --by-ubb-position

# U2 histogram
bh-analyze-systems histogram U2/ETH10/4 --speed 200 --by-ubb-position

# If U1 shows more high-BER samples than U2-U8 → potential U1 position issue
```

### Advanced Statistics Examples

```bash
# Per-system stats for U1 position with fleet aggregation
bh-analyze-systems advanced-stats U1/ETH10/4 --speed 200 --by-ubb-position
```

**Output:**
```
Per-System Statistics - U1/ETH10/lane4 (Per-UBB Position)
┌────────────────┬──────────┬──────────┬──────────┬─────────┐
│ System         │ Min BER  │ Avg BER  │ Max BER  │ Samples │
├────────────────┼──────────┼──────────┼──────────┼─────────┤
│ bh-glx-c02u02  │ 1.00e-12 │ 2.00e-11 │ 3.00e-10 │ 36      │
│ bh-glx-c03u02  │ 5.00e-13 │ 1.00e-11 │ 5.00e-10 │ 36      │
│ bh-glx-c04u02  │ 8.00e-13 │ 1.50e-11 │ 4.00e-10 │ 36      │
└────────────────┴──────────┴──────────┴──────────┴─────────┘

Note: Each system's stats aggregate 4 UBBs (9 samples per UBB = 36 samples per system)

Statistics of System Statistics
┌───────────┬──────────┬──────────┬──────────┐
│ Metric    │ Minimum  │ Average  │ Maximum  │
├───────────┼──────────┼──────────┼──────────┤
│ MIN       │ 5.00e-13 │ 7.67e-13 │ 1.00e-12 │
│ AVG       │ 1.00e-11 │ 1.50e-11 │ 2.00e-11 │
│ MAX       │ 3.00e-10 │ 4.00e-10 │ 5.00e-10 │
└───────────┴──────────┴──────────┴──────────┘

Systems: 3  |  Total Samples: 108  |  Chip Positions: U1  |  Speeds: 200
```

### Interactive Shell Examples

```bash
# Start shell
bh-analyze-systems shell

# Use per-UBB analysis in shell
bh-analyze> stats U1/ETH07 --speed 200 --by-ubb-position
bh-analyze> stats U2/ETH07 --speed 200 --by-ubb-position
bh-analyze> training all --speed 200 --format heatmap --by-ubb-position
bh-analyze> histogram U1/ETH10/4 --speed 200 --by-ubb-position
bh-analyze> advanced-stats */ETH10/4 --speed 200 --by-ubb-position
```

---

## Understanding the Output

### Lane ID Format Changes

The lane identifier format changes when using `--by-ubb-position`:

**Standard Analysis:**
```
01:00.0/ETH07/lane4
```

**Per-UBB Position Analysis:**
```
U1/ETH07/lane4
```

**Format:** `<CHIP_POSITION>/<ETH_PORT>/lane<N>`

Where chip position is one of: U1, U2, U3, U4, U5, U6, U7, U8

### Sample Count Differences

**Key Difference:** Sample counts are approximately 4x larger in per-UBB mode:

**Example with 5 systems, 9 test runs each:**

| Mode | Lane Spec | Expected Samples | Calculation |
|------|-----------|------------------|-------------|
| Standard | `01:00.0/ETH07/4` | 45 | 5 systems × 9 tests |
| Per-UBB | `U1/ETH07/4` | 180 | 5 systems × 4 UBBs × 9 tests |

**Why the difference matters:**

- Larger sample sizes → More statistical confidence
- Better pattern detection → Easier to identify outliers
- Improved variance analysis → Distinguish real patterns from noise

### Heatmap Interpretation

**Standard Heatmap Rows:**
```
01:00.0   ETH07  [values for lanes 0-7]
41:00.0   ETH07  [values for lanes 0-7]
c1:00.0   ETH07  [values for lanes 0-7]
81:00.0   ETH07  [values for lanes 0-7]
```

**Per-UBB Heatmap Rows:**
```
Chip Position: U1
  ETH07  [aggregated values for lanes 0-7 from 01:00.0, 41:00.0, c1:00.0, 81:00.0]

Chip Position: U2
  ETH07  [aggregated values for lanes 0-7 from 02:00.0, 42:00.0, c2:00.0, 82:00.0]

[... U3 through U8 ...]
```

**Reading the heatmap:**

- Each chip position (U1-U8) gets its own section
- Within each section, rows represent ETH ports
- Columns represent individual serdes lanes (lane 0-7)
- Colors indicate BER levels or failure counts (same color scheme as standard mode)

### Metadata Footer

**Standard Mode:**
```
Tests: 45  Systems: 5  Speeds: 200
```

**Per-UBB Mode:**
```
Tests: 180  Systems: 5  Chip Positions: U1  Speeds: 200
Note: Data aggregated by UBB position (4 UBBs per system)
```

The footer includes:

- **Tests** - Total number of test samples (4x larger in per-UBB mode)
- **Systems** - Number of unique systems in dataset
- **Chip Positions** - Which chip position(s) are included in the result
- **Speeds** - Train speed filter (if applied)
- **Note** - Reminder that data is aggregated by UBB position

---

## Comparison Examples

### Side-by-Side: Standard vs Per-UBB

**Scenario:** Analyze ETH10 lane 4 for chip position U1

1. **Standard Analysis**

```bash
bh-analyze-systems stats 01:00.0/ETH10/4 --speed 200
```

**Output:**
```
┌───────────────────────┬───────────┬───────────┬───────────┬──────────┬─────────┐
│ Lane                  │ Min       │ Avg       │ Max       │ High BER │ Samples │
├───────────────────────┼───────────┼───────────┼───────────┼──────────┼─────────┤
│ 01:00.0/ETH10/lane4   │ 1.23e-12  │ 2.34e-11  │ 4.56e-10  │ 2        │ 45      │
└───────────────────────┴───────────┴───────────┴───────────┴──────────┴─────────┘

Tests: 45  Systems: 5  Speeds: 200
```

**Interpretation:**
- 45 samples from 5 systems
- Only looking at bus_id 01:00.0 (UBB 1 chip position U1)
- Limited sample size for statistical analysis

2. **Per-UBB Position Analysis**

```bash
bh-analyze-systems stats U1/ETH10/4 --speed 200 --by-ubb-position
```

**Output:**
```
┌─────────────────┬───────────┬───────────┬───────────┬──────────┬─────────┐
│ Lane            │ Min       │ Avg       │ Max       │ High BER │ Samples │
├─────────────────┼───────────┼───────────┼───────────┼──────────┼─────────┤
│ U1/ETH10/lane4  │ 1.23e-12  │ 2.45e-11  │ 4.56e-10  │ 8        │ 180     │
└─────────────────┴───────────┴───────────┴───────────┴──────────┴─────────┘

Tests: 180  Systems: 5  Chip Positions: U1  Speeds: 200
Note: Data aggregated by UBB position (4 UBBs per system)
```

**Interpretation:**
- 180 samples = 45 samples/UBB × 4 UBBs
- Aggregates 01:00.0, 41:00.0, c1:00.0, and 81:00.0
- 4x more data for better statistical confidence

**Key Differences:**

| Metric | Standard | Per-UBB | Difference |
|--------|----------|---------|------------|
| Lane ID | `01:00.0/ETH10/lane4` | `U1/ETH10/lane4` | Format change |
| Samples | 45 | 180 | 4x increase |
| Avg BER | 2.34e-11 | 2.45e-11 | Slightly different (more data) |
| High BER | 2 | 8 | 4x increase (proportional) |

### Interpreting the Differences

**When averages are similar (standard ≈ per-UBB):**
- Suggests consistent behavior across all UBBs at this chip position
- Validates that PCB design is uniform across UBBs

**When averages differ significantly:**
- May indicate variability across UBBs
- Could suggest environmental or system-specific factors
- Warrants deeper investigation with `advanced-stats`

**Example investigation workflow:**

```bash
# 1. Compare standard vs per-UBB averages
bh-analyze-systems stats 01:00.0/ETH10/4 --speed 200
bh-analyze-systems stats U1/ETH10/4 --speed 200 --by-ubb-position

# 2. If averages differ, check per-system breakdown
bh-analyze-systems advanced-stats U1/ETH10/4 --speed 200 --by-ubb-position

# 3. Look at distribution
bh-analyze-systems histogram U1/ETH10/4 --speed 200 --by-ubb-position
```

### Multi-Position Comparison

**Compare all chip positions to find PCB-related patterns:**

```bash
# Check each chip position separately
for pos in U1 U2 U3 U4 U5 U6 U7 U8; do
  echo "=== Chip Position: $pos ==="
  bh-analyze-systems stats ${pos}/ETH10/4 --speed 200 --by-ubb-position
done
```

**Example Result Pattern:**

```
=== Chip Position: U1 ===
U1/ETH10/lane4  │ 1.23e-12  │ 2.45e-11  │ 4.56e-10  │ 8  │ 180

=== Chip Position: U2 ===
U2/ETH10/lane4  │ 1.15e-12  │ 1.89e-11  │ 3.21e-10  │ 1  │ 180

=== Chip Position: U3 ===
U3/ETH10/lane4  │ 1.18e-12  │ 1.92e-11  │ 3.45e-10  │ 2  │ 180
```

**Interpretation:**
- U1 position shows higher average BER and more high BER samples
- U2 and U3 positions are cleaner
- Suggests potential PCB trace issue at U1 position, not a systemic problem

---

## Best Practices

### When to Use Per-UBB Analysis

**Good Use Cases:**

1. **PCB Trace Analysis**
   - Investigating potential board-level design issues
   - Analyzing if specific chip positions consistently underperform
   - Identifying trace routing problems

2. **Pattern Detection Across Fleet**
   - Building statistical confidence for patterns
   - Distinguishing hardware design issues from environmental factors
   - Validating if issues are position-specific or systemic

3. **Sample Size Augmentation**
   - When you have limited systems but need more data
   - Improving confidence intervals for statistical analysis
   - Enabling meaningful histogram distributions

4. **Design Validation**
   - Verifying PCB design consistency across UBBs
   - Checking if all chip positions perform equivalently
   - Qualifying new board revisions

**Example Workflow for PCB Analysis:**

```bash
# 1. Start with heatmap to get overview of all positions
bh-analyze-systems stats all --speed 200 --format heatmap --by-ubb-position

# 2. Identify problematic chip positions visually

# 3. Deep dive into specific position
bh-analyze-systems stats U1/* --speed 200 --by-ubb-position

# 4. Check histogram for distribution patterns
bh-analyze-systems histogram U1/ETH10/4 --speed 200 --by-ubb-position

# 5. Compare with other positions
bh-analyze-systems histogram U2/ETH10/4 --speed 200 --by-ubb-position
bh-analyze-systems histogram U3/ETH10/4 --speed 200 --by-ubb-position
```

### When NOT to Use Per-UBB Analysis

**Avoid Per-UBB Analysis For:**

1. **System-Specific Debugging**
   - Known issues on specific systems
   - Cable-related problems (cables are system-specific)
   - Environmental issues (temperature, power)
   - Intermittent failures on particular systems

2. **Cable Configuration Analysis**
   - Cable connections differ between systems
   - Per-UBB aggregation obscures cable-specific patterns

3. **System Performance Comparison**
   - Comparing two specific systems head-to-head
   - Tracking down which system has a problem
   - System-level qualification testing

**Example: Wrong use of per-UBB for cable issues**

```bash
# DON'T: Use per-UBB for cable analysis
bh-analyze-systems stats U1/ETH10 --speed 200 --by-ubb-position

# DO: Use standard analysis with cable topology
bh-analyze-systems stats 01:00.0/ETH10 --speed 200
# Then correlate with cable configuration for that specific system
```

### Combining Standard and Per-UBB Analysis

**Best Practice:** Use both approaches complementarily:

**Step 1: Per-UBB for pattern detection**
```bash
# Find patterns across chip positions
bh-analyze-systems stats all --speed 200 --format heatmap --by-ubb-position
```

**Step 2: Standard analysis for system identification**
```bash
# If U1 position shows issues, find which system(s)
bh-analyze-systems stats 01:00.0/ETH10/4 --speed 200
bh-analyze-systems stats 41:00.0/ETH10/4 --speed 200
bh-analyze-systems stats c1:00.0/ETH10/4 --speed 200
bh-analyze-systems stats 81:00.0/ETH10/4 --speed 200
```

**Step 3: Advanced stats to verify**
```bash
# Check if issue is widespread or isolated
bh-analyze-systems advanced-stats U1/ETH10/4 --speed 200 --by-ubb-position
```

### Sample Size Considerations

**Rule of Thumb:**

- **< 30 samples** - Limited statistical confidence, use per-UBB to increase sample size
- **30-100 samples** - Moderate confidence, per-UBB helps for pattern detection
- **> 100 samples** - Good confidence, both modes are viable

**Example:**

```bash
# Small fleet (2 systems) - standard analysis limited
bh-analyze-systems stats 01:00.0/ETH10/4 --speed 200
# Output: 18 samples (2 systems × 9 tests) - LOW CONFIDENCE

# Use per-UBB to increase sample size
bh-analyze-systems stats U1/ETH10/4 --speed 200 --by-ubb-position
# Output: 72 samples (2 systems × 4 UBBs × 9 tests) - BETTER CONFIDENCE
```

### Statistical Interpretation

**Variance Analysis:**

Per-UBB mode affects variance interpretation:

**Standard mode variance:**
- Reflects system-to-system variability
- Includes environmental and cable differences

**Per-UBB mode variance:**
- Reflects UBB-to-UBB variability within systems
- More focused on PCB-level consistency
- Lower variance expected if PCBs are identical

**Example:**

```bash
# Standard analysis
bh-analyze-systems stats 01:00.0/ETH10 --speed 200 --format heatmap --statistic avg
# High variance symbols (■, ✕) → system or environmental variability

# Per-UBB analysis
bh-analyze-systems stats U1/ETH10 --speed 200 --format heatmap --statistic avg --by-ubb-position
# High variance symbols (■, ✕) → UBB-to-UBB variability within systems
#   → Might indicate marginal PCB design or manufacturing variation
```

---

## Integration with Excel Export

All per-UBB analysis commands support Excel export with the `--excel-output` option.

### Excel Export Examples

1. **Export stats to Excel:**

```bash
bh-analyze-systems stats U1/ETH10 --speed 200 --by-ubb-position --excel-output ubb_analysis.xlsx
```

2. **Export heatmap with cell colors:**

```bash
bh-analyze-systems stats all --speed 200 --format heatmap --by-ubb-position --excel-output ubb_analysis.xlsx
```

3. **Export histogram with chart:**

```bash
bh-analyze-systems histogram U1/ETH10/4 --speed 200 --by-ubb-position --excel-output ubb_analysis.xlsx
```

4. **Build comprehensive analysis workbook:**

```bash
# Create multi-worksheet Excel file comparing all positions
for pos in U1 U2 U3 U4 U5 U6 U7 U8; do
  bh-analyze-systems stats ${pos}/ETH10/4 --speed 200 --by-ubb-position \
    --excel-output chip_position_analysis.xlsx
done

# Add histograms
for pos in U1 U2 U3 U4 U5 U6 U7 U8; do
  bh-analyze-systems histogram ${pos}/ETH10/4 --speed 200 --by-ubb-position \
    --excel-output chip_position_analysis.xlsx
done

# Add overall heatmap
bh-analyze-systems stats all --speed 200 --format heatmap --by-ubb-position \
  --excel-output chip_position_analysis.xlsx

# Result: Excel file with 17 worksheets (8 stats + 8 histograms + 1 heatmap)
```

### Excel Worksheet Naming

Worksheets include chip position in the name:

**Standard Mode:**
- `Stats - 01:00.0/ETH10/4`
- `Histogram - 01:00.0/ETH10/4`

**Per-UBB Mode:**
- `Stats - U1/ETH10/4 (per-UBB)`
- `Histogram - U1/ETH10/4 (per-UBB)`

The `(per-UBB)` suffix helps distinguish per-UBB worksheets from standard analysis worksheets in the same workbook.

### Excel Metadata Section

Per-UBB exports include additional metadata:

```
Summary:
  Total Samples: 180
  Systems Analyzed: 5
  Chip Positions: U1
  Train Speeds: 200G
  Analysis Mode: Per-UBB Position (aggregates 4 UBBs per system)
```

### Comparison Workflow with Excel

**Create side-by-side comparison:**

```bash
# Export standard analysis
bh-analyze-systems stats 01:00.0/ETH10/4 --speed 200 --excel-output comparison.xlsx

# Export per-UBB analysis to same file
bh-analyze-systems stats U1/ETH10/4 --speed 200 --by-ubb-position --excel-output comparison.xlsx

# Result: Excel file with two worksheets for easy comparison
#   - Stats - 01:00.0/ETH10/4
#   - Stats - U1/ETH10/4 (per-UBB)
```

Open `comparison.xlsx` and compare the two worksheets to see the sample size difference and statistical impact.

---

## Troubleshooting

### Invalid Chip Position Specification

**Problem:**
```
ERROR: Invalid chip position: U9/ETH10
```

**Solution:**
Chip positions are U1 through U8 only. Use one of: U1, U2, U3, U4, U5, U6, U7, U8.

```bash
# Correct:
bh-analyze-systems stats U1/ETH10 --speed 200 --by-ubb-position

# Incorrect:
bh-analyze-systems stats U9/ETH10 --speed 200 --by-ubb-position
```

### Sample Count Lower Than Expected

**Problem:**
Expected 180 samples (5 systems × 4 UBBs × 9 tests) but only got 150.

**Possible Causes:**

1. **Incomplete data for some UBBs**
   - Not all systems have data for all 4 UBBs
   - Some UBB data was filtered out (status filter)

2. **Test failures excluded**
   - Training failures have no BER data (excluded from stats)
   - High BER (>= 0.1) excluded from min/avg/max calculations

**Solution:**
Check database info and filter settings:

```bash
# Check total data in database
bh-analyze-systems info

# Verify what data exists for this chip position
bh-analyze-systems stats U1/ETH10/4 --speed 200 --by-ubb-position --format table
# Look at "Samples" column

# Check training failures separately
bh-analyze-systems training U1/ETH10/4 --speed 200 --by-ubb-position
```

### No Data Returned

**Problem:**
```
No data found for chip position U5/ETH12
```

**Possible Causes:**

1. **Port is unused or unconnected**
   - ETH05, ETH08, ETH12, ETH13 are not used on all chips
   - Check platform topology documentation

2. **No test data collected for this port**
   - Verify CSV files include this ETH port
   - Check if port was tested on this chip position

**Solution:**

```bash
# Check which ports have data
bh-analyze-systems stats U5/* --speed 200 --by-ubb-position

# Verify database contents
bh-analyze-systems info
```

### Confusing Standard vs Per-UBB Results

**Problem:**
Not sure when to use standard vs per-UBB mode.

**Solution:**

Use this decision tree:

```
Is the issue related to:
├─ Specific system? → Use STANDARD mode (01:00.0/ETH10)
├─ Cable configuration? → Use STANDARD mode (cable configs are system-specific)
├─ PCB design or chip position? → Use PER-UBB mode (U1/ETH10)
├─ Need more sample size? → Use PER-UBB mode (4x data)
└─ Not sure? → Run BOTH and compare
```

**Example Comparison:**

```bash
# Run both modes
bh-analyze-systems stats 01:00.0/ETH10/4 --speed 200 > standard_result.txt
bh-analyze-systems stats U1/ETH10/4 --speed 200 --by-ubb-position > per_ubb_result.txt

# Compare results
diff standard_result.txt per_ubb_result.txt
```

### Misinterpreting Chip Position Labels

**Problem:**
Confused about U1 vs 01:00.0 vs bus_id.

**Solution:**

**Mapping Reference:**

| Chip Position | UBB 1 | UBB 2 | UBB 3 | UBB 4 |
|---------------|-------|-------|-------|-------|
| U1 | 01:00.0 | 41:00.0 | c1:00.0 | 81:00.0 |
| U2 | 02:00.0 | 42:00.0 | c2:00.0 | 82:00.0 |
| U3 | 03:00.0 | 43:00.0 | c3:00.0 | 83:00.0 |
| U4 | 04:00.0 | 44:00.0 | c4:00.0 | 84:00.0 |
| U5 | 05:00.0 | 45:00.0 | c5:00.0 | 85:00.0 |
| U6 | 06:00.0 | 46:00.0 | c6:00.0 | 86:00.0 |
| U7 | 07:00.0 | 47:00.0 | c7:00.0 | 87:00.0 |
| U8 | 08:00.0 | 48:00.0 | c8:00.0 | 88:00.0 |

**Remember:**
- **Chip position (U1-U8)** = Physical location on the UBB PCB
- **Bus ID (01:00.0, 41:00.0, etc.)** = System-level identifier for specific chip on specific UBB

### Excel Export Shows Unexpected Results

**Problem:**
Excel heatmap doesn't show chip positions correctly.

**Solution:**

1. **Verify per-UBB flag was used:**
   - Check worksheet name includes `(per-UBB)` suffix
   - Check metadata section shows "Analysis Mode: Per-UBB Position"

2. **Check row headers:**
   - Should show `U1/ETH10`, not `01:00.0/ETH10`
   - If showing bus IDs, the `--by-ubb-position` flag may not have been applied

3. **Re-export with correct flag:**

```bash
# Ensure flag is present
bh-analyze-systems stats U1/ETH10 --speed 200 --format heatmap \
  --by-ubb-position --excel-output corrected.xlsx
```

---

## Summary

Per-UBB position analysis is a powerful technique for:

- **Increasing sample sizes** by 4x (critical for small fleets)
- **Detecting PCB-level patterns** across chip positions
- **Distinguishing design issues from system-specific problems**
- **Building statistical confidence** for pattern analysis

**Key Takeaways:**

1. **Use `--by-ubb-position` flag** to enable per-UBB analysis
2. **Chip position syntax (U1-U8)** replaces bus IDs in per-UBB mode
3. **Sample counts increase 4x** due to UBB aggregation
4. **Best for PCB analysis**, not for system-specific debugging
5. **Combine with standard mode** for comprehensive analysis

**Quick Reference:**

```bash
# Standard analysis (per-system)
bh-analyze-systems stats 01:00.0/ETH10/4 --speed 200

# Per-UBB analysis (per-chip-position)
bh-analyze-systems stats U1/ETH10/4 --speed 200 --by-ubb-position

# Compare all chip positions
bh-analyze-systems stats all --speed 200 --format heatmap --by-ubb-position

# Export to Excel
bh-analyze-systems stats U1/ETH10/4 --speed 200 --by-ubb-position \
  --excel-output analysis.xlsx
```

---

**Last Updated:** 2026-03-31
**Tool Version:** 0.7.0
