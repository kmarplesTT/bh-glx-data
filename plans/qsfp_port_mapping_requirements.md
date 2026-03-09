# QSFP Port Mapping

Add a new feature to the `bh-topology` tool that maps ETH ports that are connected to cable connectors to QSFP port numbers.
These ports are not mapped anywhere in the `platform_topology.py` so it currently returns "No connection for <bus_id> <eth_id>: Port is connecte to external cable connector"

## Prerequisite Info

- "U#", where # is the second number in the bus_id. For example, U3 refers to 03:00.0, 43:00.0, c3:00.0, or 83:00.0
- Each QSFP port represents 8 serdes lanes (i.e., 2 ETH ports that are 4 serdes lanes each)

## QSFP to ETH port mapping

- (U5 ETH02, U5 ETH03) -> QSFP-1
- (U1 ETH02, U1 ETH03) -> QSFP-2
- (U1 ETH00, U1 ETH01) -> QSFP-3
- (U2 ETH00, U2 ETH01) -> QSFP-4
- (U3 ETH00, U3 ETH01) -> QSFP-5
- (U4 ETH00, U4 ETH01) -> QSFP-6
- (U1 ETH10, U2 ETH10) -> QSFP-7
- (U5 ETH10, U6 ETH10) -> QSFP-8
- (U3 ETH10, U4 ETH10) -> QSFP-9
- (U7 ETH10, U8 ETH10) -> QSFP-10
- (U1 ETH11, U2 ETH11) -> QSFP-11
- (U5 ETH11, U6 ETH11) -> QSFP-12
- (U3 ETH11, U4 ETH11) -> QSFP-13
- (U7 ETH11, U8 ETH11) -> QSFP-14

### Example usage

`bh-topology 01:00.0 ETH10` returns `UBB1/U1 (01:00.0) ETH10 -> UBB1 QSFP-7`
