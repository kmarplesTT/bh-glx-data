# Cable Configuration Guide

This guide explains how to create and use cable configuration files with the `bh-topology` tool.

## Overview

Cable configuration files define how external cables connect QSFP ports on the BH Galaxy platform. When a cable configuration is provided, the `bh-topology` tool can trace the complete device-to-device path through cable connections, showing the full signal path from source device through QSFP ports to destination device.

## Configuration File Format

Cable configurations are YAML files that define QSFP-to-QSFP connections for each UBB.

### Basic Structure

```yaml
UBB1:
  - QSFP-X <> QSFP-Y
  - QSFP-A <> QSFP-B

UBB2:
  - QSFP-X <> QSFP-Y
  - QSFP-A <> QSFP-B

UBB3:
  - ...

UBB4:
  - ...
```

### Format Rules

1. **UBB Sections**: Top-level keys must be `UBB1`, `UBB2`, `UBB3`, or `UBB4`
2. **Connection Format**: Each connection must follow the format `QSFP-X <> QSFP-Y`
   - Use `<>` as the connection operator (not `->` or other symbols)
   - QSFP port numbers must be between 1 and 14
   - Case insensitive: `QSFP-7` or `qsfp-7` both work
   - Whitespace is flexible: `QSFP-1<>QSFP-2` and `QSFP-1 <> QSFP-2` both work
3. **Bidirectional**: All connections are automatically bidirectional
   - If you specify `QSFP-1 <> QSFP-2`, queries work in both directions
4. **Empty UBBs**: If a UBB has no cable connections, you can omit it or use `UBB2:` with no list

## Example Configuration: QC3

The QC3 test configuration connects QSFP ports in pairs for loopback testing:

```yaml
# QC3 Cable Configuration
# QSFP port connections for UBB test setup

UBB1:
  - QSFP-1 <> QSFP-2
  - QSFP-3 <> QSFP-5
  - QSFP-4 <> QSFP-6
  - QSFP-7 <> QSFP-8
  - QSFP-9 <> QSFP-10
  - QSFP-11 <> QSFP-12
  - QSFP-13 <> QSFP-14

UBB2:
  - QSFP-1 <> QSFP-2
  - QSFP-3 <> QSFP-5
  - QSFP-4 <> QSFP-6
  - QSFP-7 <> QSFP-8
  - QSFP-9 <> QSFP-10
  - QSFP-11 <> QSFP-12
  - QSFP-13 <> QSFP-14

UBB3:
  - QSFP-1 <> QSFP-2
  - QSFP-3 <> QSFP-5
  - QSFP-4 <> QSFP-6
  - QSFP-7 <> QSFP-8
  - QSFP-9 <> QSFP-10
  - QSFP-11 <> QSFP-12
  - QSFP-13 <> QSFP-14

UBB4:
  - QSFP-1 <> QSFP-2
  - QSFP-3 <> QSFP-5
  - QSFP-4 <> QSFP-6
  - QSFP-7 <> QSFP-8
  - QSFP-9 <> QSFP-10
  - QSFP-11 <> QSFP-12
  - QSFP-13 <> QSFP-14
```

This configuration is included in the repository as `cables/qc3.yaml`.

## Using Cable Configurations

### Named Configurations

Named configurations are searched in standard directories:
1. `~/.config/bh-glx-data/cables/`
2. `./cables/` (relative to current directory)

To use a named configuration:

```bash
# Uses qc3.yaml from search paths
bh-topology 01:00.0 ETH10 qc3

# With JSON output
bh-topology 01:00.0 ETH10 qc3 --json
```

### File Path Configurations

You can also specify an explicit path to a configuration file:

```bash
# Relative path
bh-topology 01:00.0 ETH10 ./my-cables.yaml

# Absolute path
bh-topology 01:00.0 ETH10 /path/to/cable-config.yaml
```

## Output Examples

### Without Cable Configuration

Shows only the QSFP port mapping:

```bash
$ bh-topology 01:00.0 ETH10
UBB1/U1 (01:00.0) ETH10 -> UBB1 QSFP-7
```

### With Cable Configuration

Shows the complete device-to-device path through cables:

```bash
$ bh-topology 01:00.0 ETH10 qc3
01:00.0 ETH10 -> QSFP-7 <-> QSFP-8 -> 05:00.0 ETH10
```

This output shows:
- Source device `01:00.0` port `ETH10`
- Maps to `QSFP-7`
- Cable connects `QSFP-7` to `QSFP-8`
- `QSFP-8` maps to destination device `05:00.0` port `ETH10`

### JSON Output with Cable Configuration

```bash
$ bh-topology 01:00.0 ETH10 qc3 --json
{
  "source": {
    "bus_id": "01:00.0",
    "eth_port": "ETH10",
    "qsfp_port": 7,
    "ubb": 1
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
    "ubb": 1
  }
}
```

## Creating Custom Configurations

To create a custom cable configuration:

1. **Create a YAML file** with your cable connections:

```yaml
UBB1:
  - QSFP-1 <> QSFP-2
  - QSFP-3 <> QSFP-4
# Add more connections as needed

UBB2:
  - QSFP-1 <> QSFP-2
# ... etc
```

2. **Save to a standard location** (optional):
   - User-specific: `~/.config/bh-glx-data/cables/my-config.yaml`
   - Project-specific: `./cables/my-config.yaml`

3. **Use the configuration**:

```bash
# If saved in standard location
bh-topology 01:00.0 ETH10 my-config

# Otherwise use explicit path
bh-topology 01:00.0 ETH10 ./path/to/my-config.yaml
```

## Understanding QSFP Port Mapping

Each QSFP port on the platform corresponds to 2 ETH ports (8 serdes lanes total). The mapping is based on chip position (U1-U8) and is consistent across all UBBs:

- **QSFP-1**: U5 ETH02, ETH03
- **QSFP-2**: U1 ETH02, ETH03
- **QSFP-3**: U1 ETH00, ETH01
- **QSFP-4**: U2 ETH00, ETH01
- **QSFP-5**: U3 ETH00, ETH01
- **QSFP-6**: U4 ETH00, ETH01
- **QSFP-7**: U1 ETH10, U2 ETH10
- **QSFP-8**: U5 ETH10, U6 ETH10
- **QSFP-9**: U3 ETH10, U4 ETH10
- **QSFP-10**: U7 ETH10, U8 ETH10
- **QSFP-11**: U1 ETH11, U2 ETH11
- **QSFP-12**: U5 ETH11, U6 ETH11
- **QSFP-13**: U3 ETH11, U4 ETH11
- **QSFP-14**: U7 ETH11, U8 ETH11

When querying a cable path, the tool:
1. Maps the source ETH port to its QSFP port
2. Looks up the cable connection in the configuration
3. Maps the destination QSFP port back to ETH ports
4. Returns the complete path information

## Error Handling

### Configuration Not Found

```bash
$ bh-topology 01:00.0 ETH10 nonexistent
Error loading cable configuration: Named cable config 'nonexistent' not found in: ...
```

### Invalid YAML Format

```bash
$ bh-topology 01:00.0 ETH10 invalid.yaml
Error loading cable configuration: Error parsing YAML file 'invalid.yaml': ...
```

### Invalid Connection Format

```bash
Error loading cable configuration: Invalid connection format: 'QSFP-1 -> QSFP-2'. Expected format: 'QSFP-X <> QSFP-Y'
```

### Invalid QSFP Port Number

```bash
Error loading cable configuration: Invalid QSFP port: 15. Must be 1-14
```

## Programmatic Usage

You can also use cable configurations programmatically:

```python
from bh_glx_data.hardware.cable_config import CableConfigManager
from bh_glx_data.hardware.platform_topology import get_cable_path

# Load configuration
config = CableConfigManager()
config.load("qc3")  # Load named config
# OR
config.load("./my-config.yaml")  # Load from file

# Query cable path
path = get_cable_path("01:00.0", "ETH10", config)
print(f"Cable connects {path['source']['bus_id']} to {path['destination']['bus_id']}")

# Query specific QSFP connection
dest = config.get_connected_qsfp(ubb_num=1, qsfp_port=7)
print(f"UBB1 QSFP-7 connects to UBB{dest[0]} QSFP-{dest[1]}")
```

## Validation

Cable configurations are validated when loaded:

1. **Structure**: Must be valid YAML dictionary with UBB sections
2. **UBB Names**: Must be UBB1, UBB2, UBB3, or UBB4
3. **Connection Format**: Must match `QSFP-X <> QSFP-Y` pattern
4. **Port Numbers**: QSFP ports must be 1-14
5. **Bidirectional Consistency**: Automatically ensures connections work in both directions

Validation errors are reported immediately when loading the configuration, before any queries are attempted.
