"""Jira integration module for downloading CSV attachments.

This module provides functionality to:
- Authenticate with Jira
- Retrieve tickets
- Find and download CSV attachments
"""

from bh_glx_data.jira_integration.client import JiraClient
from bh_glx_data.jira_integration.retriever import (
    download_attachments,
    find_csv_attachments,
    process_tickets,
)

__all__ = [
    "JiraClient",
    "find_csv_attachments",
    "download_attachments",
    "process_tickets",
]
