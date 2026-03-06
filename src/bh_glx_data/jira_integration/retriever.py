"""CSV attachment retrieval logic for Jira tickets."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, List, Optional

from bh_glx_data.core.exceptions import JiraConnectionError
from bh_glx_data.core.models import DownloadResult
from bh_glx_data.jira_integration.client import JiraClient

logger = logging.getLogger(__name__)


def find_csv_attachments(issue) -> List:
    """Find all CSV attachments on a Jira issue.

    Args:
        issue: Jira issue object

    Returns:
        List of attachment objects that are CSV files
    """
    csv_attachments: List[Any] = []

    if not hasattr(issue.fields, "attachment") or not issue.fields.attachment:
        return csv_attachments

    for attachment in issue.fields.attachment:
        if attachment.filename.lower().endswith(".csv"):
            csv_attachments.append(attachment)
            logger.info(f"Found CSV attachment: {attachment.filename} on {issue.key}")

    return csv_attachments


def download_attachment(
    jira_client: JiraClient,
    issue,
    attachment,
    output_dir: Path,
) -> Optional[Path]:
    """Download a single CSV attachment.

    Args:
        jira_client: Authenticated JiraClient instance
        issue: Jira issue object
        attachment: Attachment object to download
        output_dir: Directory to save the file

    Returns:
        Path to the downloaded file, or None if download failed
    """
    try:
        # Create filename: {TICKET_KEY}_{ATTACHMENT_NAME}.csv
        safe_filename = attachment.filename.replace(" ", "_")
        output_filename = f"{issue.key}_{safe_filename}"
        output_path = output_dir / output_filename

        # Download the attachment
        content = jira_client.download_attachment(attachment)
        with open(output_path, "wb") as f:
            f.write(content)

        logger.info(f"Downloaded {attachment.filename} to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error downloading attachment {attachment.filename} from {issue.key}: {e}")
        return None


def download_attachments(
    jira_client: JiraClient,
    issue,
    attachments: List,
    output_dir: Path,
    max_workers: int = 5,
) -> List[Path]:
    """Download multiple attachments in parallel.

    Args:
        jira_client: Authenticated JiraClient instance
        issue: Jira issue object
        attachments: List of attachment objects to download
        output_dir: Directory to save files
        max_workers: Maximum number of parallel downloads

    Returns:
        List of paths to successfully downloaded files
    """
    downloaded_files: List[Path] = []

    if not attachments:
        return downloaded_files

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all download tasks
        future_to_attachment = {
            executor.submit(
                download_attachment,
                jira_client,
                issue,
                attachment,
                output_dir,
            ): attachment
            for attachment in attachments
        }

        # Process completed downloads
        for future in as_completed(future_to_attachment):
            attachment = future_to_attachment[future]
            try:
                downloaded_path = future.result()
                if downloaded_path:
                    downloaded_files.append(downloaded_path)
            except Exception as e:
                logger.error(f"Exception downloading {attachment.filename}: {e}")

    return downloaded_files


def process_ticket(
    jira_client: JiraClient,
    ticket_key: str,
    output_dir: Path,
    max_workers: int = 5,
) -> dict:
    """Process a single ticket: retrieve, find CSV attachments, and download.

    Args:
        jira_client: Authenticated JiraClient instance
        ticket_key: The ticket key to process
        output_dir: Directory to save downloaded files
        max_workers: Maximum number of parallel downloads per ticket

    Returns:
        Dictionary with processing results:
        {
            'ticket_key': str,
            'found': bool,
            'csv_count': int,
            'downloaded': int,
            'downloaded_files': List[Path],
            'errors': List[str]
        }
    """
    result: dict = {
        "ticket_key": ticket_key,
        "found": False,
        "csv_count": 0,
        "downloaded": 0,
        "downloaded_files": [],
        "errors": [],
    }

    # Retrieve ticket
    try:
        issue = jira_client.get_issue(ticket_key)
    except JiraConnectionError as e:
        logger.error(f"Failed to retrieve ticket {ticket_key}: {e}")
        result["errors"].append(f"Connection error: {e}")
        return result

    if not issue:
        result["errors"].append(f"Ticket {ticket_key} not found")
        return result

    result["found"] = True

    # Find CSV attachments
    csv_attachments = find_csv_attachments(issue)
    result["csv_count"] = len(csv_attachments)

    if not csv_attachments:
        logger.warning(f"No CSV attachments found on ticket {ticket_key}")
        result["errors"].append(f"No CSV attachments found on ticket {ticket_key}")
        return result

    # Download attachments
    downloaded_files = download_attachments(
        jira_client,
        issue,
        csv_attachments,
        output_dir,
        max_workers=max_workers,
    )

    result["downloaded"] = len(downloaded_files)
    result["downloaded_files"] = downloaded_files

    # Record any download failures
    if result["downloaded"] < result["csv_count"]:
        failed_count = result["csv_count"] - result["downloaded"]
        result["errors"].append(f"Failed to download {failed_count} attachment(s)")

    return result


def process_tickets(
    jira_client: JiraClient,
    ticket_keys: List[str],
    output_dir: Path,
    max_workers: int = 5,
) -> DownloadResult:
    """Process multiple tickets in parallel.

    Args:
        jira_client: Authenticated JiraClient instance
        ticket_keys: List of ticket keys to process
        output_dir: Directory to save downloaded files
        max_workers: Maximum number of parallel ticket processing tasks

    Returns:
        DownloadResult with summary of all downloads
    """
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    downloaded_files = []
    failed_tickets = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all ticket processing tasks
        future_to_ticket = {
            executor.submit(
                process_ticket,
                jira_client,
                ticket_key,
                output_dir,
                max_workers=3,  # Limit concurrent downloads per ticket
            ): ticket_key
            for ticket_key in ticket_keys
        }

        # Process completed tickets
        for future in as_completed(future_to_ticket):
            ticket_key = future_to_ticket[future]
            try:
                result = future.result()
                results.append(result)
                logger.info(f"Completed processing ticket {ticket_key}")

                # Track downloaded files
                downloaded_files.extend(result.get("downloaded_files", []))

                # Track failed tickets
                if not result["found"] or result["downloaded"] == 0:
                    failed_tickets.append(ticket_key)

            except Exception as e:
                logger.error(f"Exception processing ticket {ticket_key}: {e}")
                failed_tickets.append(ticket_key)
                results.append(
                    {
                        "ticket_key": ticket_key,
                        "found": False,
                        "csv_count": 0,
                        "downloaded": 0,
                        "downloaded_files": [],
                        "errors": [f"Exception processing ticket: {e}"],
                    }
                )

    # Calculate summary
    total_downloaded = len(downloaded_files)
    success = total_downloaded > 0

    # Prepare error message if any
    error_message = None
    if failed_tickets:
        error_message = (
            f"Failed to download from {len(failed_tickets)} ticket(s): {', '.join(failed_tickets)}"
        )

    return DownloadResult(
        downloaded_files=downloaded_files,
        failed_tickets=failed_tickets,
        total_downloads=total_downloaded,
        success=success,
        error_message=error_message,
    )
