"""Jira client wrapper for authenticated access."""

import logging
from typing import Optional

from jira import JIRA
from jira.exceptions import JIRAError

from bh_glx_data.core.exceptions import JiraAuthenticationError, JiraConnectionError
from bh_glx_data.core.models import JiraConfig

logger = logging.getLogger(__name__)


class JiraClient:
    """Wrapper for JIRA client with authentication and error handling.

    This class provides a simplified interface to the JIRA API with
    proper error handling and logging.

    Attributes:
        config: JiraConfig with server URL and credentials
        client: Underlying JIRA client instance
    """

    def __init__(self, config: JiraConfig):
        """Initialize Jira client with configuration.

        Args:
            config: JiraConfig object with server URL and credentials

        Raises:
            JiraAuthenticationError: If authentication fails
            JiraConnectionError: If connection to Jira fails
        """
        self.config = config
        self._client: Optional[JIRA] = None
        self._connect()

    def _connect(self):
        """Establish connection to Jira server.

        Raises:
            JiraAuthenticationError: If authentication fails
            JiraConnectionError: If connection fails
        """
        try:
            self._client = JIRA(
                server=self.config.server_url,
                basic_auth=(self.config.email, self.config.api_key),
            )
            logger.info(f"Successfully authenticated with Jira at {self.config.server_url}")
        except JIRAError as e:
            if e.status_code == 401:
                raise JiraAuthenticationError(
                    "Authentication failed. Check your email and API key.",
                    email=self.config.email,
                )
            elif e.status_code == 403:
                raise JiraAuthenticationError(
                    "Access forbidden. Check your permissions.",
                    email=self.config.email,
                )
            else:
                raise JiraConnectionError(
                    f"Failed to connect to Jira: {e}",
                    server_url=self.config.server_url,
                )
        except Exception as e:
            raise JiraConnectionError(
                f"Unexpected error connecting to Jira: {e}",
                server_url=self.config.server_url,
            )

    @property
    def client(self) -> JIRA:
        """Get the underlying JIRA client.

        Returns:
            Authenticated JIRA client instance

        Raises:
            JiraConnectionError: If client is not connected
        """
        if self._client is None:
            raise JiraConnectionError("Jira client is not connected")
        return self._client

    def get_issue(self, ticket_key: str):
        """Retrieve a Jira issue by key.

        Args:
            ticket_key: The ticket key (e.g., 'SYS-123')

        Returns:
            Jira Issue object, or None if not found

        Raises:
            JiraConnectionError: If retrieval fails
        """
        try:
            issue = self.client.issue(ticket_key)
            logger.info(f"Retrieved ticket {ticket_key}: {issue.fields.summary}")
            return issue
        except JIRAError as e:
            if e.status_code == 404:
                logger.warning(f"Ticket {ticket_key} not found (404)")
                return None
            else:
                logger.error(f"Error retrieving ticket {ticket_key}: {e}")
                raise JiraConnectionError(
                    f"Failed to retrieve ticket {ticket_key}: {e}",
                    server_url=self.config.server_url,
                )
        except Exception as e:
            logger.error(f"Unexpected error retrieving ticket {ticket_key}: {e}")
            raise JiraConnectionError(
                f"Unexpected error retrieving ticket {ticket_key}: {e}",
                server_url=self.config.server_url,
            )

    def download_attachment(self, attachment) -> bytes:
        """Download attachment content.

        Args:
            attachment: Jira attachment object

        Returns:
            Bytes content of the attachment

        Raises:
            JiraConnectionError: If download fails
        """
        try:
            return attachment.get()  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f"Error downloading attachment {attachment.filename}: {e}")
            raise JiraConnectionError(
                f"Failed to download attachment {attachment.filename}: {e}",
                server_url=self.config.server_url,
            )

    def close(self):
        """Close the Jira client connection."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Jira client connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
