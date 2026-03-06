"""Command-line interface for Jira CSV retrieval."""

import argparse
import logging
import sys
from pathlib import Path

from bh_glx_data.core.config import ConfigManager
from bh_glx_data.core.exceptions import (
    ConfigurationError,
    JiraAuthenticationError,
    JiraConnectionError,
    ValidationError,
)
from bh_glx_data.jira_integration.client import JiraClient
from bh_glx_data.jira_integration.retriever import process_tickets

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Retrieve CSV attachments from Jira tickets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Use tickets from config.yaml
  %(prog)s --tickets SYS-2826           # Process a single ticket
  %(prog)s --tickets SYS-2826 SYS-2827  # Process multiple tickets
  %(prog)s --output-dir /path/to/dir    # Custom output directory
        """,
    )

    parser.add_argument(
        "--tickets",
        nargs="*",
        help="Jira ticket key(s) to process (e.g., SYS-2826). If not provided, uses tickets from config.yaml",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for downloaded CSV files (default: csv_data/)",
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file (default: searches for config.yaml)",
    )

    parser.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="Maximum number of parallel downloads (default: 5)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


def print_summary(result, output_dir: Path):
    """Print download summary.

    Args:
        result: DownloadResult object
        output_dir: Output directory path
    """
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)

    print(f"CSV files downloaded: {result.total_downloads}")
    print(f"Failed tickets: {len(result.failed_tickets)}")
    print(f"Success: {'Yes' if result.success else 'No'}")

    if result.failed_tickets:
        print("\nFailed tickets:")
        for ticket in result.failed_tickets:
            print(f"  - {ticket}")

    if result.error_message:
        print(f"\nErrors: {result.error_message}")

    print(f"\nDownloaded files saved to: {output_dir.absolute()}")


def main():
    """Main entry point for the Jira CSV retrieval CLI."""
    args = parse_arguments()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load configuration
    try:
        config_manager = ConfigManager()

        # Build CLI overrides
        cli_overrides = {}
        if args.output_dir:
            cli_overrides["output_dir"] = args.output_dir

        config = config_manager.load(
            config_file=args.config,
            cli_overrides=cli_overrides,
        )

        # Ensure output directory exists
        config_manager.ensure_directories()
        output_dir = config.data.input_dir  # Jira downloads go to input_dir

    except (ConfigurationError, ValidationError) as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Determine ticket keys
    if args.tickets:
        ticket_keys = args.tickets
        logger.info(
            f"Using {len(ticket_keys)} ticket(s) from command-line: {', '.join(ticket_keys)}"
        )
    else:
        # Load tickets from config file
        try:
            config_file = args.config or config_manager._find_config_file()
            if not config_file:
                logger.error(
                    "No config file found and no --tickets provided. "
                    "Either provide --tickets or create config.yaml with ticket list."
                )
                sys.exit(1)

            yaml_config = config_manager._load_yaml_config(config_file)
            ticket_keys = config_manager.load_tickets(yaml_config)
            logger.info(
                f"Using {len(ticket_keys)} ticket(s) from config.yaml: {', '.join(ticket_keys)}"
            )
        except ValidationError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)

    # Initialize Jira client
    try:
        jira_client = JiraClient(config.jira)
    except (JiraAuthenticationError, JiraConnectionError) as e:
        logger.error(f"Failed to initialize Jira client: {e}")
        sys.exit(1)

    # Process tickets
    try:
        result = process_tickets(
            jira_client=jira_client,
            ticket_keys=ticket_keys,
            output_dir=output_dir,
            max_workers=args.max_workers,
        )

        # Print summary
        print_summary(result, output_dir)

        # Exit with appropriate code
        if not result.success:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error during processing: {e}")
        sys.exit(1)
    finally:
        jira_client.close()


if __name__ == "__main__":
    main()
