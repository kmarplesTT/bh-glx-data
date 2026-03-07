"""
Main script to retrieve CSV attachments from Jira tickets.
Authenticates with Jira, retrieves tickets, finds CSV attachments, and downloads them.
"""

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from jira import JIRA
from jira.exceptions import JIRAError

import config

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def initialize_jira_client():
    """
    Initialize and return a Jira client with basic authentication.

    Returns:
        JIRA: Authenticated Jira client instance

    Raises:
        ValueError: If configuration is invalid
        JIRAError: If authentication fails
    """
    config.validate_config()

    try:
        jira = JIRA(server=config.JIRA_SERVER_URL, basic_auth=(config.EMAIL, config.API_KEY))
        logger.info(f"Successfully authenticated with Jira at {config.JIRA_SERVER_URL}")
        return jira
    except JIRAError as e:
        logger.error(f"Failed to authenticate with Jira: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error initializing Jira client: {e}")
        raise


def retrieve_ticket(jira_client, ticket_key):
    """
    Retrieve a Jira ticket by its key.

    Args:
        jira_client: Authenticated Jira client instance
        ticket_key (str): The ticket key (e.g., 'PROJ-123')

    Returns:
        Issue: Jira issue object, or None if ticket not found
    """
    try:
        issue = jira_client.issue(ticket_key)
        logger.info(f"Retrieved ticket {ticket_key}: {issue.fields.summary}")
        return issue
    except JIRAError as e:
        if e.status_code == 404:
            logger.warning(f"Ticket {ticket_key} not found (404)")
        else:
            logger.error(f"Error retrieving ticket {ticket_key}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error retrieving ticket {ticket_key}: {e}")
        return None


def find_csv_attachments(issue):
    """
    Find all CSV attachments on a Jira issue.

    Args:
        issue: Jira issue object

    Returns:
        list: List of attachment objects that are CSV files
    """
    csv_attachments = []
    if not hasattr(issue.fields, "attachment") or not issue.fields.attachment:
        return csv_attachments

    for attachment in issue.fields.attachment:
        if attachment.filename.lower().endswith(".csv"):
            csv_attachments.append(attachment)
            logger.info(f"Found CSV attachment: {attachment.filename} on {issue.key}")

    return csv_attachments


def download_csv_attachment(jira_client, issue, attachment, output_dir):
    """
    Download a CSV attachment from a Jira issue.

    Args:
        jira_client: Authenticated Jira client instance
        issue: Jira issue object
        attachment: Attachment object to download
        output_dir (Path): Directory to save the file

    Returns:
        Path: Path to the downloaded file, or None if download failed
    """
    try:
        # Create filename: {TICKET_KEY}_{ATTACHMENT_NAME}.csv
        safe_filename = attachment.filename.replace(" ", "_")
        output_filename = f"{issue.key}_{safe_filename}"
        output_path = output_dir / output_filename

        # Download the attachment
        with open(output_path, "wb") as f:
            f.write(attachment.get())

        logger.info(f"Downloaded {attachment.filename} to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error downloading attachment {attachment.filename} from {issue.key}: {e}")
        return None


def process_ticket(jira_client, ticket_key):
    """
    Process a single ticket: retrieve it, find CSV attachments, and download them.

    Args:
        jira_client: Authenticated Jira client instance
        ticket_key (str): The ticket key to process

    Returns:
        dict: Summary of processing results
    """
    result = {
        "ticket_key": ticket_key,
        "found": False,
        "csv_count": 0,
        "downloaded": 0,
        "errors": [],
    }

    # Retrieve ticket
    issue = retrieve_ticket(jira_client, ticket_key)
    if not issue:
        result["errors"].append(f"Ticket {ticket_key} not found or could not be retrieved")
        return result

    result["found"] = True

    # Find CSV attachments
    csv_attachments = find_csv_attachments(issue)
    result["csv_count"] = len(csv_attachments)

    if not csv_attachments:
        logger.warning(f"No CSV attachments found on ticket {ticket_key}")
        result["errors"].append(f"No CSV attachments found on ticket {ticket_key}")
        return result

    # Download attachments in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all download tasks
        future_to_attachment = {
            executor.submit(
                download_csv_attachment, jira_client, issue, attachment, config.OUTPUT_DIR
            ): attachment
            for attachment in csv_attachments
        }

        # Process completed downloads
        for future in as_completed(future_to_attachment):
            attachment = future_to_attachment[future]
            try:
                downloaded_path = future.result()
                if downloaded_path:
                    result["downloaded"] += 1
                else:
                    result["errors"].append(f"Failed to download {attachment.filename}")
            except Exception as e:
                logger.error(f"Exception downloading {attachment.filename}: {e}")
                result["errors"].append(f"Exception downloading {attachment.filename}: {e}")

    return result


def parse_arguments():
    """
    Parse command-line arguments.

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
        """,
    )
    parser.add_argument(
        "--tickets",
        nargs="*",
        help="Jira ticket key(s) to process (e.g., SYS-2826). If not provided, uses tickets from config.yaml",
    )
    return parser.parse_args()


def main():
    """
    Main entry point for the script.
    Reads ticket keys from command-line arguments or config.yaml file.
    """
    # Deprecation warning
    import warnings

    warnings.warn(
        "\n" + "=" * 80 + "\n"
        "DEPRECATION WARNING: Direct script execution is deprecated.\n"
        "Please use the new command: 'bh-jira-retrieve'\n"
        "Example: bh-jira-retrieve --tickets SYS-123 SYS-456\n"
        "See documentation for migration guide: docs/migration_guide.md\n"
        "This script will be removed in version 1.0.0\n" + "=" * 80,
        DeprecationWarning,
        stacklevel=2,
    )

    # Parse command-line arguments
    args = parse_arguments()

    # Determine ticket keys: use CLI args if provided, otherwise use config.yaml
    if args.tickets:
        ticket_keys = args.tickets
        logger.info(
            f"Using {len(ticket_keys)} ticket(s) from command-line arguments: {', '.join(ticket_keys)}"
        )
        # Still validate Jira connection config, but skip ticket validation
        try:
            # Only validate Jira connection settings, not ticket keys
            if not config.JIRA_SERVER_URL:
                raise ValueError("JIRA_SERVER_URL is missing")
            if not config.EMAIL:
                raise ValueError("EMAIL is missing")
            if not config.API_KEY:
                raise ValueError("API_KEY is missing")
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)
    else:
        # Validate configuration (includes checking for ticket keys in config.yaml)
        try:
            config.validate_config()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)
        ticket_keys = config.JIRA_TICKET_KEYS
        logger.info(
            f"Using {len(ticket_keys)} ticket(s) from config.yaml: {', '.join(ticket_keys)}"
        )

    # Initialize Jira client
    try:
        jira_client = initialize_jira_client()
    except Exception as e:
        logger.error(f"Failed to initialize Jira client: {e}")
        sys.exit(1)

    # Process tickets in parallel using ThreadPoolExecutor
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all ticket processing tasks
        future_to_ticket = {
            executor.submit(process_ticket, jira_client, ticket_key): ticket_key
            for ticket_key in ticket_keys
        }

        # Process completed tickets
        for future in as_completed(future_to_ticket):
            ticket_key = future_to_ticket[future]
            try:
                result = future.result()
                results.append(result)
                logger.info(f"Completed processing ticket {ticket_key}")
            except Exception as e:
                logger.error(f"Exception processing ticket {ticket_key}: {e}")
                results.append(
                    {
                        "ticket_key": ticket_key,
                        "found": False,
                        "csv_count": 0,
                        "downloaded": 0,
                        "errors": [f"Exception processing ticket: {e}"],
                    }
                )

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total_found = sum(1 for r in results if r["found"])
    total_csv = sum(r["csv_count"] for r in results)
    total_downloaded = sum(r["downloaded"] for r in results)
    total_errors = sum(len(r["errors"]) for r in results)

    print(f"Tickets processed: {len(results)}")
    print(f"Tickets found: {total_found}")
    print(f"CSV attachments found: {total_csv}")
    print(f"CSV files downloaded: {total_downloaded}")
    print(f"Errors encountered: {total_errors}")

    if total_errors > 0:
        print("\nErrors:")
        for result in results:
            if result["errors"]:
                print(f"  {result['ticket_key']}:")
                for error in result["errors"]:
                    print(f"    - {error}")

    print(f"\nDownloaded files saved to: {config.OUTPUT_DIR.absolute()}")


if __name__ == "__main__":
    main()
