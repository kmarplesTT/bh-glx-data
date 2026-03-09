"""Command-line interface for platform topology queries."""

import argparse
import json
import logging
import sys
from pathlib import Path

from bh_glx_data.hardware.platform_topology import (
    CABLE_CONNECTOR_PORTS_BY_CHIP,
    PLATFORM_TOPOLOGY,
    format_device_info,
    get_all_connections_for_device,
    get_chip_from_bus_id,
    get_connected_port,
    get_port_status,
    get_qsfp_port,
    get_ubb_from_bus_id,
    normalize_bus_id,
    normalize_eth_port,
)

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Query Blackhole Galaxy Platform Topology - ETH port connectivity between chips",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query a specific connection
  %(prog)s 01:00.0 ETH07
  %(prog)s 01 7              # Shorthand format

  # Show all connections for a device
  %(prog)s 01:00.0 --all
  %(prog)s 01 --all          # Shorthand format

  # JSON output for programmatic use
  %(prog)s 01:00.0 ETH07 --json

  # Bidirectional lookup
  %(prog)s 05:00.0 ETH00 --bidirectional

ETH Port Categories:
  Each chip has 14 ports (ETH00-ETH13). Port purposes vary by chip position:
  - ETH05, ETH08: Unused (not physically present) on all chips
  - ETH12, ETH13: Unconnected (not used) on all chips
  - Platform connections and cable connectors vary by chip (U1-U8):
    * U1: ETH04,06,07,09 (platform), ETH00,01,02,03,10,11 (cable)
    * U2-U4: ETH02,03,04,06,07,09 (platform), ETH00,01,10,11 (cable)
    * U5: ETH00,01,04,06,07,09 (platform), ETH02,03,10,11 (cable)
    * U6-U8: ETH00,01,02,03,04,06,07,09 (platform), ETH10,11 (cable)
        """,
    )

    parser.add_argument("bus_id", help="Bus ID of the source device (e.g., '01:00.0' or '01')")
    parser.add_argument(
        "eth_port", nargs="?", help="ETH port to query (e.g., 'ETH07' or '7'). Omit to use --all"
    )
    parser.add_argument(
        "--all", "-a", action="store_true", help="Show all connections for the device"
    )
    parser.add_argument("--json", "-j", action="store_true", help="Output in JSON format")
    parser.add_argument(
        "--bidirectional",
        "-b",
        action="store_true",
        help="Also show reverse connection (what connects to the result)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    return parser.parse_args()


def main():
    """Main entry point for the platform topology CLI."""
    args = parse_arguments()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Normalize inputs
    try:
        bus_id = normalize_bus_id(args.bus_id)
    except Exception as e:
        print(f"Error: Invalid bus_id format '{args.bus_id}': {e}", file=sys.stderr)
        sys.exit(1)

    # Check if bus_id exists in topology
    device_exists = any(src_bus == bus_id for src_bus, _ in PLATFORM_TOPOLOGY.keys())
    if not device_exists:
        print(f"Error: Device {bus_id} not found in topology", file=sys.stderr)
        sys.exit(1)

    if args.all:
        # Show all connections for device
        connections = get_all_connections_for_device(bus_id)

        if args.json:
            output = {
                "bus_id": bus_id,
                "device": format_device_info(bus_id),
                "connections": {
                    port: {
                        "bus_id": dest_bus,
                        "eth_port": dest_port,
                        "device": format_device_info(dest_bus),
                    }
                    for port, (dest_bus, dest_port) in connections.items()
                },
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"All connections for {format_device_info(bus_id)} ({bus_id}):")
            for src_port, (dest_bus, dest_port) in sorted(connections.items()):
                print(f"  {src_port} -> {format_device_info(dest_bus)} ({dest_bus}) {dest_port}")

    elif args.eth_port:
        # Query specific connection
        try:
            eth_port = normalize_eth_port(args.eth_port)
        except Exception as e:
            print(f"Error: Invalid eth_port format '{args.eth_port}': {e}", file=sys.stderr)
            sys.exit(1)

        connected = get_connected_port(bus_id, eth_port)

        if not connected:
            # Determine why no connection was found and provide informative message
            port_status = get_port_status(bus_id, eth_port)

            if port_status == "invalid":
                print(
                    f"Error: Invalid ETH port '{eth_port}'. Valid ports are ETH00-ETH13.",
                    file=sys.stderr,
                )
                sys.exit(1)
            elif port_status == "unused":
                print(
                    f"No connection for {bus_id} {eth_port}: Port is unused (not physically present).",
                    file=sys.stderr,
                )
                print("  Note: ETH05 and ETH08 are not present on the hardware.", file=sys.stderr)
                sys.exit(1)
            elif port_status == "unconnected":
                print(
                    f"No connection for {bus_id} {eth_port}: Port is unconnected (not used).",
                    file=sys.stderr,
                )
                print("  Note: ETH12 and ETH13 are not connected on the platform.", file=sys.stderr)
                sys.exit(1)
            elif port_status == "cable_connector":
                # Check if this port has a QSFP mapping
                qsfp_port = get_qsfp_port(bus_id, eth_port)
                if qsfp_port:
                    # Display QSFP connection
                    ubb = get_ubb_from_bus_id(bus_id)
                    if args.json:
                        output = {
                            "source": {
                                "bus_id": bus_id,
                                "eth_port": eth_port,
                                "device": format_device_info(bus_id),
                            },
                            "destination": {
                                "qsfp_port": qsfp_port,
                                "ubb": ubb,
                                "description": f"UBB{ubb} QSFP-{qsfp_port}",
                            },
                        }
                        print(json.dumps(output, indent=2))
                    else:
                        print(
                            f"{format_device_info(bus_id)} ({bus_id}) {eth_port} -> UBB{ubb} QSFP-{qsfp_port}"
                        )
                    sys.exit(0)
                else:
                    # Cable connector but no QSFP mapping (shouldn't happen)
                    chip_num = get_chip_from_bus_id(bus_id)
                    cable_ports = sorted(CABLE_CONNECTOR_PORTS_BY_CHIP.get(chip_num, set()))
                    print(
                        f"No connection for {bus_id} {eth_port}: Port is connected to external cable connector.",
                        file=sys.stderr,
                    )
                    print(
                        f"  Note: Chip U{chip_num} cable connector ports: {', '.join(cable_ports)}",
                        file=sys.stderr,
                    )
                    sys.exit(1)
            else:
                # Should be in topology but isn't - this is unexpected
                print(f"Error: No connection found for {bus_id} {eth_port}", file=sys.stderr)
                print("  This may indicate missing topology data.", file=sys.stderr)
                sys.exit(1)

        dest_bus, dest_port = connected

        if args.json:
            output = {
                "source": {
                    "bus_id": bus_id,
                    "eth_port": eth_port,
                    "device": format_device_info(bus_id),
                },
                "destination": {
                    "bus_id": dest_bus,
                    "eth_port": dest_port,
                    "device": format_device_info(dest_bus),
                },
            }

            if args.bidirectional:
                # Look up reverse connection
                reverse = get_connected_port(dest_bus, dest_port)
                if reverse:
                    output["reverse"] = {
                        "bus_id": reverse[0],
                        "eth_port": reverse[1],
                        "device": format_device_info(reverse[0]),
                    }

            print(json.dumps(output, indent=2))
        else:
            print(
                f"{format_device_info(bus_id)} ({bus_id}) {eth_port} -> {format_device_info(dest_bus)} ({dest_bus}) {dest_port}"
            )

            if args.bidirectional:
                reverse = get_connected_port(dest_bus, dest_port)
                if reverse:
                    rev_bus, rev_port = reverse
                    print(
                        f"Reverse: {format_device_info(dest_bus)} ({dest_bus}) {dest_port} -> {format_device_info(rev_bus)} ({rev_bus}) {rev_port}"
                    )

    else:
        print("Error: Either specify an eth_port or use --all", file=sys.stderr)
        print("Run with --help for usage information", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
