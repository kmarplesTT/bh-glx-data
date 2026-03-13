# bh-topology User Guide

A command-line tool for querying BH Galaxy platform topology. This tool provides information about Ethernet port connectivity between chips, QSFP port mappings for external cables, and complete device-to-device signal paths through cable configurations.

**Version:** 0.3.0
**Purpose:** Query platform connectivity, QSFP port mappings, and cable paths for hardware debugging and failure analysis

---

## Quick Start

Get started in 5 minutes:

```bash
# 1. Query platform connection between chips
bh-topology 01:00.0 ETH07

# 2. Query QSFP port for cable connector
bh-topology 01:00.0 ETH10

# 3. Query full cable path with configuration
bh-topology 01:00.0 ETH10 qc3

# 4. Show all connections for a device
bh-topology 01:00.0 --all

# 5. Get JSON output for scripting
bh-topology 01:00.0 ETH07 --json
```

---

## Installation

The tool is included in the BH Galaxy Data Analysis Tool package. Follow the installation instructions in the main [README.md](../../README.md).

After installation, the `bh-topology` command will be available in your PATH when the virtual environment is activated:

```bash
source .venv/bin/activate
bh-topology --help
```

---

## Basic Concepts

### Platform Structure

BH Galaxy platforms consist of:

- **4 UBBs** (Unit Baseboards) numbered 1-4
- **8 Chips per UBB** (U1-U8)
- **14 ETH ports per chip** (ETH00-ETH13)
- **32 Bus IDs total** (01:00.0 through 1C:00.0 or 20:00.0)

### Bus ID Format

Bus IDs use PCIe format: `BB:DD.F`
- Examples: `01:00.0`, `05:00.0`, `1C:00.0`
- Maps to physical chip positions
- Tool accepts variations: `01:00.0`, `1:0.0`, `0100.0`

### ETH Port Types

Ports fall into different categories:

**1. Platform Connected Ports**
- Connected to other chips within the platform
- Example: `01:00.0 ETH07` → `05:00.0 ETH00`

**2. Cable Connector Ports**
- Connect to external cables via QSFP ports
- Example: `01:00.0 ETH10` → QSFP-7
- Require cable configuration to trace to destination

**3. Unused Ports**
- Not used in platform design
- Example: ETH05, ETH08

**4. Unconnected Ports**
- Not connected in current configuration
- Example: ETH12, ETH13

### QSFP Port Mapping

Each UBB has 14 QSFP ports (QSFP-1 through QSFP-14):
- Each QSFP port carries 8 serdes lanes
- Maps to 2 ETH ports (4 lanes each)
- Cable connector ETH ports map to specific QSFP ports
- Mapping varies by chip position (U1-U8)

### Cable Configuration

Cable configurations define how QSFP ports connect across systems:
- YAML format specifying QSFP-to-QSFP connections
- Supports bidirectional lookup
- Enables complete device-to-device path tracing
- Can be named configs or file paths

---

## Command Reference

### Basic Usage

Query platform connection:
```bash
bh-topology <bus_id> <eth_port> [cable_config] [OPTIONS]
```

Show all connections:
```bash
bh-topology <bus_id> --all [OPTIONS]
```

### Arguments

**Required:**

- `bus_id` - PCIe bus ID (e.g., `01:00.0`, `1:0.0`, `0100.0`)
- `eth_port` - Ethernet port (e.g., `ETH07`, `eth07`, `ETH7`, `7`)

**Optional:**

- `cable_config` - Cable configuration name or file path (for QSFP ports)

### Options

**Output Control:**

- `--all` - Show all connections for the device
- `--json` - Output in JSON format for scripting
- `--bidirectional` - Show reverse connection as well

**Logging:**

- `--verbose, -v` - Enable verbose logging
- `--log-level LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**Help:**

- `--help` - Show help message and exit

---

## Examples

### Example 1: Query Platform Connection

Check platform connectivity between chips:

```bash
bh-topology 01:00.0 ETH07
```

**Output:**
```
UBB1/U1 (01:00.0) ETH07 -> UBB1/U5 (05:00.0) ETH00
```

**What this means:**
- Source: UBB1, Chip U1, Bus ID 01:00.0, Port ETH07
- Destination: UBB1, Chip U5, Bus ID 05:00.0, Port ETH00
- These are directly connected on the platform

### Example 2: Query QSFP Port Mapping

Check which QSFP port a cable connector uses:

```bash
bh-topology 01:00.0 ETH10
```

**Output:**
```
UBB1/U1 (01:00.0) ETH10 -> UBB1 QSFP-7
```

**What this means:**
- Port ETH10 on chip 01:00.0 connects to QSFP-7
- QSFP-7 is the external cable connector
- Need cable configuration to trace further

### Example 3: Query Complete Cable Path

Trace complete path through cable configuration:

```bash
bh-topology 01:00.0 ETH10 qc3
```

**Output:**
```
01:00.0 ETH10 -> QSFP-7 <-> QSFP-8 -> 05:00.0 ETH10
```

**What this means:**
- Source: 01:00.0 ETH10
- Connects to QSFP-7 on source UBB
- Cable connects QSFP-7 to QSFP-8
- QSFP-8 connects to 05:00.0 ETH10 on destination

This is the complete signal path from device to device.

### Example 4: Show All Connections for Device

Display all port connections for a chip:

```bash
bh-topology 01:00.0 --all
```

**Output:**
```
Connections for 01:00.0 (UBB1/U1):

Platform Connections:
  ETH00 -> 05:00.0 ETH01
  ETH01 -> 05:00.0 ETH02
  ETH02 -> 05:00.0 ETH03
  ETH03 -> 05:00.0 ETH04
  ETH04 -> 05:00.0 ETH06
  ETH06 -> 05:00.0 ETH07
  ETH07 -> 05:00.0 ETH00
  ETH09 -> 09:00.0 ETH00

Cable Connectors (QSFP):
  ETH10 -> QSFP-7
  ETH11 -> QSFP-7

Unused Ports:
  ETH05, ETH08

Unconnected Ports:
  ETH12, ETH13
```

### Example 5: JSON Output for Scripting

Get machine-readable output:

```bash
bh-topology 01:00.0 ETH07 --json
```

**Output:**
```json
{
  "source": {
    "bus_id": "01:00.0",
    "eth_port": "ETH07",
    "ubb": 1,
    "chip": "U1"
  },
  "destination": {
    "bus_id": "05:00.0",
    "eth_port": "ETH00",
    "ubb": 1,
    "chip": "U5"
  },
  "connection_type": "platform"
}
```

**With cable configuration:**
```bash
bh-topology 01:00.0 ETH10 qc3 --json
```

**Output:**
```json
{
  "source": {
    "bus_id": "01:00.0",
    "eth_port": "ETH10",
    "qsfp_port": 7,
    "ubb": 1,
    "chip": "U1"
  },
  "cable": {
    "source_qsfp": 7,
    "dest_qsfp": 8,
    "source_ubb": 1,
    "dest_ubb": 1
  },
  "destination": {
    "bus_id": "05:00.0",
    "eth_port": "ETH10",
    "qsfp_port": 8,
    "ubb": 1,
    "chip": "U5"
  },
  "connection_type": "cable"
}
```

### Example 6: Bidirectional Lookup

Check both forward and reverse connections:

```bash
bh-topology 01:00.0 ETH07 --bidirectional
```

**Output:**
```
Forward: 01:00.0 ETH07 -> 05:00.0 ETH00
Reverse: 05:00.0 ETH00 -> 01:00.0 ETH07
```

### Example 7: Flexible Input Formats

The tool accepts various input formats:

```bash
# Standard format
bh-topology 01:00.0 ETH07

# Shortened bus ID
bh-topology 1:0.0 ETH07

# Compact bus ID
bh-topology 0100.0 ETH07

# Lowercase port
bh-topology 01:00.0 eth07

# Shortened port
bh-topology 01:00.0 ETH7

# Just port number
bh-topology 01:00.0 7

# All produce same result:
# UBB1/U1 (01:00.0) ETH07 -> UBB1/U5 (05:00.0) ETH00
```

---

## Cable Configuration

### Overview

Cable configurations define how external cables connect QSFP ports. This enables tracing complete signal paths through cable connections.

### Configuration Locations

Cable configurations can be specified as:

**1. Named Configurations**

Searched in standard directories:
- `~/.config/bh-glx-data/cables/`
- `./cables/`

Example:
```bash
bh-topology 01:00.0 ETH10 qc3
# Looks for: qc3.yaml in standard directories
```

**2. File Paths**

Explicit file paths (relative or absolute):
```bash
# Relative path
bh-topology 01:00.0 ETH10 ./cables/custom.yaml

# Absolute path
bh-topology 01:00.0 ETH10 /path/to/config.yaml
```

### Configuration Format

Cable configurations use YAML format:

```yaml
UBB1:
  - QSFP-1 <> QSFP-2
  - QSFP-7 <> QSFP-8
  - QSFP-13 <> QSFP-14

UBB2:
  - QSFP-1 <> QSFP-2
  - QSFP-7 <> QSFP-8
  - QSFP-13 <> QSFP-14

UBB3:
  - QSFP-1 <> QSFP-2
  - QSFP-7 <> QSFP-8

UBB4:
  - QSFP-1 <> QSFP-2
  - QSFP-7 <> QSFP-8
```

**Format rules:**
- One section per UBB (UBB1, UBB2, UBB3, UBB4)
- Each line defines a cable connection: `QSFP-X <> QSFP-Y`
- QSFP port numbers: 1-14
- Bidirectional (QSFP-1 <> QSFP-2 same as QSFP-2 <> QSFP-1)

### Creating Custom Configurations

Create a custom cable configuration:

```bash
# Create directory
mkdir -p ~/.config/bh-glx-data/cables/

# Create configuration file
cat > ~/.config/bh-glx-data/cables/my_config.yaml <<EOF
UBB1:
  - QSFP-1 <> QSFP-2
  - QSFP-3 <> QSFP-4
  - QSFP-7 <> QSFP-8

UBB2:
  - QSFP-1 <> QSFP-2
  - QSFP-7 <> QSFP-8
EOF

# Use it
bh-topology 01:00.0 ETH10 my_config
```

### Built-in Configurations

**qc3** - Standard QC3 test configuration

Location: `./cables/qc3.yaml`

Used for Quanta QC3 test setups with standard cable connections.

---

## Common Workflows

### Workflow 1: Debugging Link Failures

Trace connectivity for failed links:

```bash
# Failure on 01:00.0 ETH07

# 1. Check platform connection
bh-topology 01:00.0 ETH07

# Output: 01:00.0 ETH07 -> 05:00.0 ETH00

# 2. Check reverse connection
bh-topology 05:00.0 ETH00

# Output: 05:00.0 ETH00 -> 01:00.0 ETH07

# 3. Verify both sides in test data
# Both 01:00.0 ETH07 and 05:00.0 ETH00 should show failures
```

### Workflow 2: Analyzing Failure Patterns

Identify systematic failure patterns:

```bash
# Multiple failures on same chip

# 1. Show all connections for the chip
bh-topology 01:00.0 --all

# 2. Identify which failures are:
#    - Platform connected (internal issue)
#    - Cable connected (cable issue)
#    - Pattern matches specific destination chip

# 3. Check connected chips
bh-topology 05:00.0 --all

# 4. Look for correlation:
#    - All failures to one chip? -> Chip issue
#    - All failures on cable ports? -> Cable/connector issue
#    - Random distribution? -> Signal integrity issue
```

### Workflow 3: Cable Path Verification

Verify cable connections are correct:

```bash
# Using cable configuration

# 1. Check expected cable path
bh-topology 01:00.0 ETH10 qc3

# Expected: 01:00.0 ETH10 -> QSFP-7 <-> QSFP-8 -> 05:00.0 ETH10

# 2. Verify both ends show same connection
bh-topology 05:00.0 ETH10 qc3

# Expected: 05:00.0 ETH10 -> QSFP-8 <-> QSFP-7 -> 01:00.0 ETH10

# 3. If mismatch, cable configuration or physical cables are wrong
```

### Workflow 4: Scripting with JSON Output

Automate topology queries:

```bash
#!/bin/bash
# check_failures.sh

# Read failures from CSV
failures=$(cut -d',' -f1,2 failures.csv | tail -n +2)

while IFS=',' read -r bus_id eth_port; do
    # Query topology
    result=$(bh-topology "$bus_id" "$eth_port" --json)

    # Extract destination
    dest_bus=$(echo "$result" | jq -r '.destination.bus_id')
    dest_port=$(echo "$result" | jq -r '.destination.eth_port')

    echo "Failure: $bus_id $eth_port connects to $dest_bus $dest_port"

    # Check if destination also failed
    # grep "$dest_bus,$dest_port" failures.csv
done <<< "$failures"
```

### Workflow 5: QSFP Port Mapping

Map all QSFP ports for a UBB:

```bash
# Check all chips on UBB1 (01:00.0 through 04:00.0)

echo "UBB1 QSFP Mapping:"
for bus_id in 01:00.0 02:00.0 03:00.0 04:00.0; do
    echo "Chip $bus_id:"
    bh-topology "$bus_id" --all | grep "QSFP"
done

# Output shows which chips connect to which QSFP ports
# Useful for physical cable tracing
```

### Workflow 6: Integration with Failure Analysis

Correlate failures with topology:

```bash
# 1. Extract failures
bh-filter-failures data_test_results.csv

# 2. For each failure, check topology
# Example: Failure on 01:00.0 ETH10

# 3. Check connection type
bh-topology 01:00.0 ETH10

# If platform connection:
#   - Check if destination also failed
#   - Indicates internal platform issue

# If cable connection (QSFP):
#   - Check cable path with config
#   - Indicates cable or connector issue

# 4. Pattern analysis
# - All failures on cable ports? Cable/connector problem
# - All failures to one chip? Destination chip problem
# - Mixed? Signal integrity or systematic issue
```

---

## Troubleshooting

### Invalid Bus ID Format

**Problem:**
```
ERROR: Invalid bus ID format: 1:0
```

**Solution:**

Use proper PCIe format with function number:
```bash
# Correct formats:
bh-topology 01:00.0 ETH07
bh-topology 1:0.0 ETH07
bh-topology 0100.0 ETH07

# Incorrect:
bh-topology 1:0 ETH07  # Missing function
bh-topology 01:00 ETH07  # Missing function
```

### Invalid ETH Port Format

**Problem:**
```
ERROR: Invalid ETH port format: E07
```

**Solution:**

Use proper ETH port format:
```bash
# Correct formats:
bh-topology 01:00.0 ETH07
bh-topology 01:00.0 eth07
bh-topology 01:00.0 ETH7
bh-topology 01:00.0 7

# Incorrect:
bh-topology 01:00.0 E07
bh-topology 01:00.0 07
bh-topology 01:00.0 port7
```

### Port Not Found in Topology

**Problem:**
```
WARNING: Port 01:00.0 ETH12 not found in platform topology
```

**Solution:**

This is informational. ETH12 is typically an unconnected port.

Check port status:
```bash
bh-topology 01:00.0 --all
```

Look in "Unconnected Ports" section.

### Cable Configuration Not Found

**Problem:**
```
ERROR: Cable configuration not found: myconfig
```

**Solution:**

1. Check configuration exists:
   ```bash
   ls ~/.config/bh-glx-data/cables/myconfig.yaml
   ls ./cables/myconfig.yaml
   ```

2. Use file path instead of name:
   ```bash
   bh-topology 01:00.0 ETH10 ./cables/myconfig.yaml
   ```

3. Create configuration if needed (see Cable Configuration section)

### Invalid Cable Configuration

**Problem:**
```
ERROR: Invalid cable configuration: Invalid QSFP port number: 15
```

**Solution:**

QSFP port numbers must be 1-14. Check configuration file:
```bash
cat cables/myconfig.yaml
```

Fix invalid port numbers or connection format.

### No QSFP Mapping for Port

**Problem:**
```
01:00.0 ETH07 -> 05:00.0 ETH00
# (Expected QSFP mapping)
```

**Solution:**

This is correct. ETH07 is a platform-connected port, not a cable connector.

Only certain ports map to QSFP connectors (varies by chip position).

Use `--all` to see which ports are cable connectors:
```bash
bh-topology 01:00.0 --all
```

---

## Tips and Best Practices

### Bus ID Reference

Quick reference for bus ID to UBB/Chip mapping:

**UBB1:**
- U1: 01:00.0, U2: 02:00.0, U3: 03:00.0, U4: 04:00.0
- U5: 05:00.0, U6: 06:00.0, U7: 07:00.0, U8: 08:00.0

**UBB2:**
- U1: 09:00.0, U2: 0A:00.0, U3: 0B:00.0, U4: 0C:00.0
- U5: 0D:00.0, U6: 0E:00.0, U7: 0F:00.0, U8: 10:00.0

**UBB3:**
- U1: 11:00.0, U2: 12:00.0, U3: 13:00.0, U4: 14:00.0
- U5: 15:00.0, U6: 16:00.0, U7: 17:00.0, U8: 18:00.0

**UBB4:**
- U1: 19:00.0, U2: 1A:00.0, U3: 1B:00.0, U4: 1C:00.0
- U5: 1D:00.0, U6: 1E:00.0, U7: 1F:00.0, U8: 20:00.0

### Port Categories

**Platform Connected** (most ports):
- ETH00-ETH04, ETH06-ETH07, ETH09
- Connect to other chips within platform
- No external cables

**Cable Connectors** (varies by chip):
- Typically ETH10-ETH11
- Map to specific QSFP ports
- Require external cables

**Unused**:
- ETH05, ETH08
- Not used in design

**Unconnected**:
- ETH12, ETH13
- Not connected in current platform

### Using with Failure Analysis

**Correlation patterns to look for:**

1. **Both ends fail** - Platform connection issue or signal integrity
2. **One end fails** - Transmit or receive issue on one side
3. **All cable ports fail** - Cable or connector problem
4. **All ports to one chip fail** - Destination chip issue
5. **Random distribution** - Systematic or environmental issue

### JSON Output

Use JSON output for:
- Scripting and automation
- Parsing in other tools
- Database import
- Correlation analysis

Example parsing:
```bash
# Extract destination bus ID
bh-topology 01:00.0 ETH07 --json | jq -r '.destination.bus_id'
# Output: 05:00.0
```

### Cable Configuration Management

**Organizing configurations:**

```
~/.config/bh-glx-data/cables/
├── qc3.yaml          # Standard QC3 config
├── production.yaml   # Production system config
├── test_rack_1.yaml  # Test rack 1 config
├── test_rack_2.yaml  # Test rack 2 config
└── custom.yaml       # Custom test config
```

**Best practices:**
- One config per physical setup
- Name configs descriptively
- Document cable connections in config
- Version control cable configs
- Validate configs after creation

### Performance

- **Fast queries** - Topology data is in-memory, queries are instant
- **No external dependencies** - Pure Python, no database needed
- **Lightweight** - Minimal memory footprint
- **Safe** - Read-only, never modifies system

---

## Understanding Platform Topology

### Physical Layout

```
Platform: 4 UBBs
Each UBB: 8 Chips (U1-U8)
Each Chip: 14 ETH ports (ETH00-ETH13)

UBB1      UBB2      UBB3      UBB4
U1 U2     U1 U2     U1 U2     U1 U2
U3 U4     U3 U4     U3 U4     U3 U4
U5 U6     U5 U6     U5 U6     U5 U6
U7 U8     U7 U8     U7 U8     U7 U8
```

### Connectivity Patterns

**Within UBB** - Chips connect to other chips on same UBB
**Across UBBs** - Chips can connect to chips on different UBBs
**External** - Cable connectors link to external systems via QSFP

### Signal Path Types

**1. Simple Platform Path**
```
01:00.0 ETH07 -> 05:00.0 ETH00
[One hop within platform]
```

**2. Cable Path (with config)**
```
01:00.0 ETH10 -> QSFP-7 <-> QSFP-8 -> 05:00.0 ETH10
[Through external cable]
```

**3. Multi-Hop Path** (not currently supported)
```
Future: Chain multiple platform/cable hops
```

---

## Getting Help

### Command Help

```bash
# Show help message
bh-topology --help
```

### Verbose Logging

Enable detailed logging for troubleshooting:

```bash
bh-topology 01:00.0 ETH07 --verbose

# Or set specific log level
bh-topology 01:00.0 ETH07 --log-level DEBUG
```

### Common Questions

**Q: How do I find which chip has a failure?**
A: The bus_id in your test data corresponds directly. Use the bus ID reference in Tips section.

**Q: How do I know if a port uses cables?**
A: Use `--all` to see port categories. Cable connectors are listed in "Cable Connectors (QSFP)" section.

**Q: Can I query by chip name (U1) instead of bus ID?**
A: No, use bus ID. See Bus ID reference to map chip names to bus IDs.

**Q: What if the tool says "not found in topology"?**
A: The port is likely unused or unconnected. Use `--all` to see all port categories.

**Q: How do I create a cable configuration?**
A: See "Cable Configuration" section for format and examples.

### Additional Resources

- Main README: [README.md](../../README.md)
- Project overview: [CLAUDE.md](../../CLAUDE.md)
- Cable configuration documentation: [docs/cable_configuration.md](../cable_configuration.md)
- Failure filtering: [bh-filter-failures.md](bh-filter-failures.md)
- System analysis: [bh-analyze-systems.md](bh-analyze-systems.md)

---

**Last Updated:** 2026-03-12
**Tool Version:** 0.3.0
